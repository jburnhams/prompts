#!/usr/bin/env python3
"""Validate the platform examples against the schemas, then run the
publish-time rules from platform.md §11 that a JSON Schema cannot express.

    python3 -I agent-design/platform/check.py

Needs jsonschema>=4.18 and PyYAML. Exits 1 on any error.
"""

import json
import pathlib
import sys

import yaml
from jsonschema import Draft202012Validator, FormatChecker
from referencing import Registry, Resource

HERE = pathlib.Path(__file__).resolve().parent
SCHEMAS = HERE / "schemas"
EXAMPLES = HERE / "examples"
BASE = "https://forge.example/schemas/"

TIER_ORDER = {"economy": 0, "standard": 1, "strong": 2}
INPUT_ONLY_TRUST = {"principal", "external"}
WRITE_TOOLS = {"builtin/Edit", "builtin/Write"}

errors = []
warnings = []


def err(where, msg):
    errors.append(f"{where}: {msg}")


def warn(where, msg):
    warnings.append(f"{where}: {msg}")


# --- schema loading ---------------------------------------------------------

def load_registry():
    resources = []
    for path in sorted(SCHEMAS.glob("*.schema.json")):
        schema = json.loads(path.read_text())
        resources.append((schema["$id"], Resource.from_contents(schema)))
    return Registry().with_resources(resources)


REGISTRY = load_registry()


def validator(ref):
    return Draft202012Validator(
        {"$ref": BASE + ref}, registry=REGISTRY, format_checker=FormatChecker()
    )


def validate(where, ref, instance):
    for e in sorted(validator(ref).iter_errors(instance), key=lambda e: list(e.absolute_path)):
        path = "/" + "/".join(str(p) for p in e.absolute_path)
        err(where, f"schema {ref} at {path}: {e.message[:300]}")


# --- extends ----------------------------------------------------------------

def merge(parent, child):
    """Objects deep-merge, arrays replace, null deletes (template.schema.json)."""
    if not isinstance(parent, dict) or not isinstance(child, dict):
        return child
    out = dict(parent)
    for key, value in child.items():
        if value is None:
            out.pop(key, None)
        elif key in out:
            out[key] = merge(out[key], value)
        else:
            out[key] = value
    return out


def flatten(template, templates, seen=()):
    parent_ref = template.get("extends")
    if not parent_ref:
        return template["spec"]
    key = (parent_ref["name"], parent_ref["version"])
    if key in seen:
        raise ValueError(f"extends cycle through {key}")
    parent = templates.get(key)
    if parent is None:
        raise ValueError(f"extends unknown template {key}")
    return merge(flatten(parent, templates, seen + (key,)), template["spec"])


# --- publish-time rules -----------------------------------------------------

def walk_params(node, path=""):
    """Yield (json_path, param_name) for every {"$param": ...} in node."""
    if isinstance(node, dict):
        if set(node) == {"$param"}:
            yield path, node["$param"]
            return
        for k, v in node.items():
            yield from walk_params(v, f"{path}/{k}")
    elif isinstance(node, list):
        for i, v in enumerate(node):
            yield from walk_params(v, f"{path}/{i}")


def group_tools(spec):
    groups = {}
    for g in spec.get("tools", {}).get("groups", []):
        if "id" in g:
            groups[g["id"]] = g
    flat = {}

    def expand(gid, stack=()):
        if gid in stack:
            raise ValueError(f"tool group include cycle at {gid}")
        g = groups[gid]
        tools = list(g.get("tools", []))
        for inc in g.get("include", []):
            tools += expand(inc, stack + (gid,))
        return tools

    for gid in groups:
        flat[gid] = expand(gid)
    return groups, flat


def carry_inputs(spec):
    return {i["source"]["carry"] for i in spec.get("inputs", []) if "carry" in i["source"]}


def check_spec(name, template, spec, flat_specs, params_by_template):
    where = name
    params = template.get("params", {})
    roles = spec["roles"]
    orch = roles["orchestrator"]
    groups, tools_by_group = group_tools(spec)
    declared_servers = {s["id"] for s in spec.get("tools", {}).get("servers", [])}

    # R1 grants come only from the job's declaration
    for role_name, role in roles.items():
        grants = set(role.get("grant", []))
        for extra in role.get("kind_grants", {}).values():
            grants |= set(extra)
        for gid in sorted(grants - set(groups)):
            err(where, f"R1 role {role_name} grants undeclared group {gid}")

    # R2 every MCP tool names a declared server
    for gid, tools in tools_by_group.items():
        for t in tools:
            src = t["tool"].split("/", 1)[0]
            if src.startswith("mcp:") and src[4:] not in declared_servers:
                err(where, f"R2 group {gid} uses {t['tool']} but tools.servers lacks {src[4:]}")

    # R3 spawn graph
    for role_name, role in roles.items():
        for child in role.get("spawns", []):
            if child not in roles or child == "orchestrator":
                err(where, f"R3 role {role_name} spawns unknown role {child}")
    for role_name, role in roles.items():
        if role_name != "orchestrator":
            for kind in role.get("kind_grants", {}):
                if kind not in role.get("spawn_kinds", []):
                    err(where, f"R3 role {role_name} kind_grants {kind} not in spawn_kinds")

    # R4 params: declared, bound by trust, constrained when config-bound
    for path, pname in walk_params(spec):
        if pname not in params:
            err(where, f"R4 {path} binds undeclared param {pname}")
            continue
        p = params[pname]
        at_input = path.startswith("/inputs/") and path.endswith("/source/param")
        if path.startswith(("/system_prompt", "/tools", "/roles", "/completion", "/hatches", "/authority", "/harness_triggers")) or path == "/model/max_tier":
            err(where, f"R4 {path} is not bindable")
        if not at_input and p["trust"] in INPUT_ONLY_TRUST:
            err(where, f"R4 {path}: param {pname} has trust {p['trust']} and may bind to an input only")
        if not at_input and p["type"] != "boolean" and not any(k in p for k in ("enum", "pattern", "subset_of", "maximum", "max_tier")):
            err(where, f"R4 {path}: config-bound param {pname} must be constrained (enum, pattern, subset_of, maximum or max_tier)")
    for inp in spec.get("inputs", []):
        if "param" in inp["source"] and inp["source"]["param"] not in params:
            err(where, f"R4 input {inp['name']} reads undeclared param {inp['source']['param']}")

    # R5 completion form text is the bare form
    comp = spec["completion"]
    if comp.get("form") == "text":
        for k in ("report_schema", "gates", "spinoffs"):
            if comp.get(k):
                err(where, f"R5 completion.form text forbids {k}")
        if comp["statuses"] != ["done"]:
            err(where, "R5 completion.form text allows statuses [done] only")

    # R6 HandOff reasons and continuations match one to one
    conts = spec.get("outputs", {}).get("continuations", [])
    handoff = (spec.get("hatches") or {}).get("handoff")
    reasons = {r["id"] for r in handoff["reasons"]} if handoff else set()
    wired = {c["on"].get("handoff_reason") for c in conts if c["on"]["terminal"] == "handoff"}
    for r in sorted(reasons - wired):
        err(where, f"R6 handoff reason {r} has no continuation")
    for r in sorted(wired - reasons):
        err(where, f"R6 continuation for handoff reason {r} but hatches.handoff does not declare it")
    for ht in spec.get("harness_triggers", []):
        target = ht["action"].get("handoff") or ht["action"].get("skip_to")
        if target and target not in reasons:
            err(where, f"R6 harness trigger {ht['id']} names unknown handoff reason {target}")

    # R7 continuations: target exists, required params bound, carries accepted
    for c in conts:
        tname = name.split("@")[0] if c["target"]["template"] == "self" else c["target"]["template"]
        target = flat_specs.get(tname)
        if target is None:
            warn(where, f"R7 continuation {c['id']} targets {tname}, not among the examples")
            continue
        missing = sorted(set(c.get("carry", [])) - carry_inputs(target) - {"artifacts"})
        if missing:
            err(where, f"R7 continuation {c['id']} carries {missing} but {tname} has no such carry input")
        tparams = params_by_template[tname]
        for pname, p in tparams.items():
            if p.get("required") and "default" not in p and pname not in c.get("params", {}):
                err(where, f"R7 continuation {c['id']} does not bind required param {pname} of {tname}")
        for pname in c.get("params", {}):
            if pname not in tparams:
                err(where, f"R7 continuation {c['id']} binds {pname}, which {tname} does not declare")
        if c["on"].get("spinoff"):
            if not comp.get("spinoffs") or c.get("via") != "task" or not spec.get("ledger"):
                err(where, f"R7 spinoff continuation {c['id']} needs completion.spinoffs, via task and ledger")
        tier = target["model"]["tier"]
        if isinstance(tier, str) and TIER_ORDER[tier] > TIER_ORDER[spec["model"]["max_tier"]]:
            err(where, f"R7 continuation {c['id']} lands on tier {tier} above max_tier")
    ask = (spec.get("human") or {}).get("ask_user")
    if ask and "approve" in ask["kinds"]:
        if not any(c["on"]["terminal"] == "suspend" and c["on"].get("answer") == "approve" for c in conts):
            err(where, "R7 ask_user allows approve but no continuation handles answer approve")

    # R8 Expand reveals only what the orchestrator is granted
    expand = (spec.get("hatches") or {}).get("expand")
    if expand:
        for gid in expand.get("reveals", []):
            if gid not in orch["grant"]:
                err(where, f"R8 Expand reveals {gid}, outside the orchestrator's grant")
        growth = expand.get("array_growth")
        if growth and growth["bundle"] not in expand.get("reveals", []):
            err(where, "R8 array_growth.bundle must be one of expand.reveals")
    revealable = set(expand.get("reveals", [])) if expand else set()
    revealable |= {ht["action"]["reveal"] for ht in spec.get("harness_triggers", []) if "reveal" in ht["action"]}
    for gid, g in groups.items():
        if g.get("visibility") == "hidden" and gid not in revealable:
            warn(where, f"R8 group {gid} is hidden with no Expand or trigger to reveal it")

    # R9 a read-only workspace grants no write tools
    ws = spec.get("workspace", {"kind": "none"})
    if ws["kind"] == "none" or not ws.get("writable"):
        for role_name, role in roles.items():
            for gid in role.get("grant", []):
                hits = {t["tool"] for t in tools_by_group.get(gid, [])} & WRITE_TOOLS
                if hits:
                    err(where, f"R9 role {role_name} is granted {sorted(hits)} on a read-only workspace")

    # R10 tiers: a literal tier never exceeds max_tier; clamped children never exceed the parent
    max_tier = spec["model"]["max_tier"]
    top = spec["model"]["tier"]
    if isinstance(top, str) and TIER_ORDER[top] > TIER_ORDER[max_tier]:
        err(where, f"R10 model.tier {top} exceeds max_tier {max_tier}")
    for role_name, role in roles.items():
        t = (role.get("model") or {}).get("tier")
        if not isinstance(t, str):
            continue
        if TIER_ORDER[t] > TIER_ORDER[max_tier]:
            err(where, f"R10 role {role_name} tier {t} exceeds max_tier {max_tier}")
        if role_name != "orchestrator" and role["model"].get("clamp_to_parent", True) and isinstance(top, str) and TIER_ORDER[t] > TIER_ORDER[top]:
            warn(where, f"R10 role {role_name} asks for {t} but is clamped to its parent's {top}")

    # R11 aliases unique per role
    for role_name, role in roles.items():
        names = {}
        for gid in role.get("grant", []):
            for t in tools_by_group.get(gid, []):
                n = t.get("alias") or t["tool"].split("/", 1)[1]
                if names.setdefault(n, t["tool"]) != t["tool"]:
                    err(where, f"R11 role {role_name} sees two tools named {n}")


def check_server_auth(name, spec, servers):
    """R12 service credentials plus write tools plus user principals need a harness entitlement check."""
    if "user" not in spec.get("authority", {}).get("run_as", []):
        return
    _, tools_by_group = group_tools(spec)
    granted = set()
    for role in spec["roles"].values():
        granted |= set(role.get("grant", []))
    for gid in granted:
        for t in tools_by_group.get(gid, []):
            src, tool = t["tool"].split("/", 1)
            if not src.startswith("mcp:"):
                continue
            server = servers.get(src[4:])
            if server is None:
                continue
            auth = server["auth"]
            if auth["mode"] == "service" and not t.get("annotations", {}).get("read_only") and auth.get("entitlement_check") != "harness_policy":
                err(name, f"R12 {t['tool']} writes with a service credential in a template users can run, and {server['id']} has no harness_policy entitlement check")


# --- main ---------------------------------------------------------------------

def main():
    for path in sorted(SCHEMAS.glob("*.schema.json")):
        Draft202012Validator.check_schema(json.loads(path.read_text()))

    openapi = yaml.safe_load((HERE / "openapi.yaml").read_text())
    refs = set()

    def collect(node):
        if isinstance(node, dict):
            if "$ref" in node and isinstance(node["$ref"], str):
                refs.add(node["$ref"])
            for v in node.values():
                collect(v)
        elif isinstance(node, list):
            for v in node:
                collect(v)

    collect(openapi)
    for ref in sorted(refs):
        if ref.startswith("#/"):
            node = openapi
            for part in ref[2:].split("/"):
                node = node.get(part) if isinstance(node, dict) else None
            if node is None:
                err("openapi.yaml", f"dangling {ref}")
        else:
            file, _, pointer = ref.partition("#")
            target = (HERE / file).resolve()
            if not target.exists():
                err("openapi.yaml", f"missing file {file}")
                continue
            node = json.loads(target.read_text())
            for part in pointer.lstrip("/").split("/") if pointer else []:
                node = node.get(part) if isinstance(node, dict) else None
            if node is None:
                err("openapi.yaml", f"dangling {ref}")

    docs = {p.name: json.loads(p.read_text()) for p in sorted(EXAMPLES.glob("*.json"))}
    templates, servers = {}, {}
    for fname, doc in docs.items():
        if fname.endswith(".template.json"):
            validate(fname, "template.schema.json", doc)
            templates[(doc["name"], doc["version"])] = doc
        elif fname.endswith(".trigger.json"):
            validate(fname, "trigger.schema.json#/$defs/Trigger", doc)
        elif fname.endswith(".mcp-server.json"):
            validate(fname, "tools.schema.json#/$defs/McpServer", doc)
            servers[doc["id"]] = doc
        elif fname == "delegation.json":
            validate(fname, "principal.schema.json#/$defs/Delegation", doc)
        elif fname == "run-request.json":
            validate(fname, "run.schema.json#/$defs/RunRequest", doc)
        elif fname == "deployment.json":
            validate(fname, "deployment.schema.json", doc)
        else:
            err(fname, "no rule says what this example is")

    flat_specs, params_by_template = {}, {}
    for (tname, version), t in templates.items():
        where = f"{tname}@{version}"
        try:
            spec = flatten(t, templates)
        except ValueError as e:
            err(where, str(e))
            continue
        validate(where, "agent-spec.schema.json", spec)
        flat_specs[tname] = spec
        params_by_template[tname] = t["params"]
    for (tname, version), t in templates.items():
        if tname in flat_specs:
            check_spec(f"{tname}@{version}", t, flat_specs[tname], flat_specs, params_by_template)
            check_server_auth(f"{tname}@{version}", flat_specs[tname], servers)

    for fname, doc in docs.items():
        if fname.endswith(".trigger.json"):
            tparams = params_by_template.get(doc["template"]["name"])
            if tparams is None:
                warn(fname, f"targets {doc['template']['name']}, not among the examples")
                continue
            for p in doc.get("params", {}):
                if p not in tparams:
                    err(fname, f"binds {p}, which the template does not declare")
            for pname, p in tparams.items():
                if p.get("required") and "default" not in p and pname not in doc.get("params", {}):
                    err(fname, f"does not bind required param {pname}")
        if fname == "run-request.json":
            tparams = params_by_template[doc["template"]["name"]]
            for pname in doc["params"]:
                if pname not in tparams:
                    err(fname, f"unknown param {pname}")

    for w in warnings:
        print("warn ", w)
    for e in errors:
        print("error", e)
    print(f"{len(templates)} templates, {len(docs)} examples, {len(errors)} errors, {len(warnings)} warnings")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
