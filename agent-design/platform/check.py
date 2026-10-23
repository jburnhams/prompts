#!/usr/bin/env python3
"""Validate the platform examples against the schemas, then run the
publish-time rules from platform.md §11 that a JSON Schema cannot express.

    python3 -I agent-design/platform/check.py

Needs jsonschema>=4.18 and PyYAML. Exits 1 on any error.
"""

import json
import pathlib
import re
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
HARNESS_NAMES = {"Complete", "AskUser", "HandOff", "Expand", "Task", "Narrate"}
# A $param is allowed under these grant-bearing sections only as a fixed tool argument.
FIXED_ARG = re.compile(r"^/(tools/groups/\d+/tools/\d+|completion/finishers/\d+/action)/params/[^/]+/fixed$")

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


def validate(where, ref, instance):
    v = Draft202012Validator({"$ref": BASE + ref}, registry=REGISTRY, format_checker=FormatChecker())
    for e in sorted(v.iter_errors(instance), key=lambda e: list(e.absolute_path)):
        path = "/" + "/".join(str(p) for p in e.absolute_path)
        err(where, f"schema {ref} at {path}: {e.message[:300]}")


# --- resolution: extends and saved groups --------------------------------------

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
    """Return (params, spec) with every ancestor merged in."""
    parent_ref = template.get("extends")
    if not parent_ref:
        return template.get("params", {}), template["spec"]
    key = (parent_ref["name"], parent_ref["version"])
    if key in seen:
        raise ValueError(f"extends cycle through {key}")
    parent = templates.get(key)
    if parent is None:
        raise ValueError(f"extends unknown template {key}")
    params, spec = flatten(parent, templates, seen + (key,))
    return merge(params, template.get("params", {})), merge(spec, template["spec"])


def saved_tools(ref, saved, stack=()):
    key = (ref["name"], ref["version"])
    if key in stack:
        raise ValueError(f"saved group include cycle at {key}")
    group = saved.get(key)
    if group is None:
        raise ValueError(f"unknown saved tool group {key}")
    tools, servers = list(group["tools"]), list(group.get("servers", []))
    for inc in group.get("include", []):
        t, s = saved_tools(inc, saved, stack + (key,))
        tools += t
        servers += s
    return tools, servers


def resolve_groups(spec, saved):
    """Inline saved groups the way :publish does, so every later rule sees one shape."""
    tools_spec = spec.get("tools")
    if not tools_spec:
        return spec
    groups, servers = [], list(tools_spec.get("servers", []))
    for g in tools_spec.get("groups", []):
        if "ref" not in g:
            groups.append(g)
            continue
        tools, extra = saved_tools(g["ref"], saved)
        group = saved[(g["ref"]["name"], g["ref"]["version"])]
        inline = {"id": g.get("id", g["ref"]["name"]), "tools": tools}
        if "visibility" in group:
            inline["visibility"] = group["visibility"]
        groups.append(inline)
        servers += [s for s in extra if s["id"] not in {x["id"] for x in servers}]
    return {**spec, "tools": {**tools_spec, "groups": groups, "servers": servers}}


# --- helpers ------------------------------------------------------------------

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
    groups = {g["id"]: g for g in (spec.get("tools") or {}).get("groups", [])}

    def expand(gid, stack=()):
        if gid in stack:
            raise ValueError(f"tool group include cycle at {gid}")
        tools = list(groups[gid].get("tools", []))
        for inc in groups[gid].get("include", []):
            tools += expand(inc, stack + (gid,))
        return tools

    return groups, {gid: expand(gid) for gid in groups}


def tool_name(ref):
    return ref.get("alias") or ref["tool"].split("/", 1)[1]


def carry_inputs(spec):
    return {i["source"]["carry"] for i in spec.get("inputs", []) if "carry" in i["source"]}


def handoff_reasons(spec):
    handoff = (spec.get("hatches") or {}).get("handoff")
    return {r["id"] for r in handoff["reasons"]} if handoff else set()


def check_constrained(where, path, pname, p):
    if p["trust"] in INPUT_ONLY_TRUST:
        err(where, f"R4 {path}: param {pname} has trust {p['trust']} and may bind to an input only")
    if p["type"] != "boolean" and not any(k in p for k in ("enum", "pattern", "subset_of", "maximum", "max_tier")):
        err(where, f"R4 {path}: config-bound param {pname} must be constrained (enum, pattern, subset_of, maximum or max_tier)")


# --- template rules -----------------------------------------------------------

def check_spec(where, params, spec):
    roles = spec["roles"]
    orch = roles["orchestrator"]
    groups, tools_by_group = group_tools(spec)
    declared_servers = {s["id"] for s in spec.get("tools", {}).get("servers", [])}
    declared_tools = {t["tool"] for tools in tools_by_group.values() for t in tools}

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
        if role_name != "orchestrator":
            for kind in role.get("kind_grants", {}):
                if kind not in role.get("spawn_kinds", []):
                    err(where, f"R3 role {role_name} kind_grants {kind} not in spawn_kinds")

    # R4 params: declared, bound by trust, constrained when config-bound
    for path, pname in walk_params(spec):
        if pname not in params:
            err(where, f"R4 {path} binds undeclared param {pname}")
            continue
        at_input = path.startswith("/inputs/") and path.endswith("/source/param")
        grant_bearing = path.startswith(("/system_prompt", "/tools", "/roles", "/completion", "/hatches", "/authority", "/monitors")) or path == "/model/max_tier"
        if grant_bearing and not FIXED_ARG.match(path):
            err(where, f"R4 {path} is not bindable")
        if not at_input:
            check_constrained(where, path, pname, params[pname])
    for inp in spec.get("inputs", []):
        if "param" in inp["source"] and inp["source"]["param"] not in params:
            err(where, f"R4 input {inp['name']} reads undeclared param {inp['source']['param']}")

    # R5 completion form text is the bare form
    comp = spec["completion"]
    if comp.get("form") == "text":
        for k in ("report_schema", "checks", "spinoffs", "finishers"):
            if comp.get(k):
                err(where, f"R5 completion.form text forbids {k}")
        if comp["statuses"] != ["done"]:
            err(where, "R5 completion.form text allows statuses [done] only")

    # R6 HandOff reasons are exits; harness triggers name real ones
    reasons = handoff_reasons(spec)
    for ht in spec.get("monitors", []):
        target = ht["action"].get("handoff") or ht["action"].get("skip_to")
        if target and target not in reasons:
            err(where, f"R6 monitor {ht['id']} names unknown handoff reason {target}")

    # R7 continuations (self only): required params bound, carries accepted
    conts = spec.get("outputs", {}).get("continuations", [])
    for c in conts:
        missing = sorted(set(c.get("carry", [])) - carry_inputs(spec) - {"artifacts"})
        if missing:
            err(where, f"R7 continuation {c['id']} carries {missing} but the template has no such carry input")
        for pname, p in params.items():
            if p.get("required") and "default" not in p and pname not in c.get("params", {}):
                err(where, f"R7 continuation {c['id']} does not bind required param {pname}")
        for pname in c.get("params", {}):
            if pname not in params:
                err(where, f"R7 continuation {c['id']} binds undeclared param {pname}")
        if c["on"].get("spinoff") and (not comp.get("spinoffs") or c.get("via") != "task" or not spec.get("ledger")):
            err(where, f"R7 spinoff continuation {c['id']} needs completion.spinoffs, via task and ledger")
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
    revealable |= {ht["action"]["reveal"] for ht in spec.get("monitors", []) if "reveal" in ht["action"]}
    granted_anywhere = {gid for r in roles.values() for gid in r.get("grant", [])}
    for gid, g in groups.items():
        if g.get("visibility") == "hidden" and gid in granted_anywhere and gid not in revealable:
            warn(where, f"R8 group {gid} is granted and hidden with no Expand or trigger to reveal it")

    # R9 a read-only workspace grants no write tools
    ws = spec.get("workspace", {"kind": "none"})
    writable = ws["kind"] == "checkout" and ws.get("writable")
    if not writable:
        for role_name, role in roles.items():
            for gid in role.get("grant", []):
                hits = {t["tool"] for t in tools_by_group.get(gid, [])} & WRITE_TOOLS
                if hits:
                    err(where, f"R9 role {role_name} is granted {sorted(hits)} on a read-only workspace")

    # R10 tiers
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

    # R11 tool names unique per role, including generated ones
    finishers = comp.get("finishers", [])
    for role_name, role in roles.items():
        names = {}
        for gid in role.get("grant", []):
            for t in tools_by_group.get(gid, []):
                n = tool_name(t)
                if names.setdefault(n, t["tool"]) != t["tool"]:
                    err(where, f"R11 role {role_name} sees two tools named {n}")
        if role_name == "orchestrator":
            for f in finishers:
                if f["name"] in names or f["name"] in HARNESS_NAMES:
                    err(where, f"R11 finisher name {f['name']} collides with another tool")
                names[f["name"]] = f["id"]

    # R13 argument overrides
    for gid, tools in tools_by_group.items():
        for t in tools:
            for arg, o in t.get("params", {}).items():
                if "fixed" in o and any(k in o for k in ("default", "enum", "description", "required")):
                    warn(where, f"R13 {t['tool']} argument {arg} is fixed, so its other overrides are never shown")

    # R14 finishers
    if comp.get("complete") is False and not finishers:
        err(where, "R14 completion.complete is false but there are no finishers")
    opens_pr = False
    for f in finishers:
        if f["status"] not in comp["statuses"]:
            err(where, f"R14 finisher {f['id']} ends with status {f['status']}, not in completion.statuses")
        if f.get("report") and not comp.get("report_schema"):
            err(where, f"R14 finisher {f['id']} takes a report but there is no report_schema")
        action = f["action"]
        if "tool" in action and action["tool"] not in declared_tools:
            err(where, f"R14 finisher {f['id']} wraps {action['tool']}, which tools.groups does not declare")
        if action.get("harness") == "open_pull_request":
            opens_pr = True
            if not writable or ws.get("git_writes") != "on_finish":
                err(where, f"R14 finisher {f['id']} opens a PR but the workspace is not writable with git_writes on_finish")
    if ws.get("git_writes") == "on_finish" and not opens_pr:
        err(where, "R14 git_writes on_finish without an open_pull_request finisher")


def r12(where, run_as, tool_addresses, servers):
    """Service credentials plus write tools plus user principals need a harness entitlement check."""
    if "user" not in run_as:
        return
    for address, annotations in tool_addresses:
        src = address.split("/", 1)[0]
        server = servers.get(src[4:]) if src.startswith("mcp:") else None
        if server is None:
            continue
        auth = server["auth"]
        if auth["mode"] == "service" and not annotations.get("read_only") and auth.get("entitlement_check") != "harness_policy":
            err(where, f"R12 {address} writes with a service credential in something users can run, and {server['id']} has no harness_policy entitlement check")


def check_server_auth(where, spec, servers):
    _, tools_by_group = group_tools(spec)
    by_address = {t["tool"]: t.get("annotations", {}) for tools in tools_by_group.values() for t in tools}
    used = {gid for role in spec["roles"].values() for gid in role.get("grant", [])}
    addresses = [(t["tool"], t.get("annotations", {})) for gid in used for t in tools_by_group.get(gid, [])]
    addresses += [(f["action"]["tool"], by_address.get(f["action"]["tool"], {})) for f in spec["completion"].get("finishers", []) if "tool" in f["action"]]
    r12(where, spec.get("authority", {}).get("run_as", []), addresses, servers)


# --- pipeline rules -----------------------------------------------------------

def check_pipeline(where, pipe, flat_specs, params_by_template, servers, base_templates):
    stages = pipe["stages"]
    pparams = pipe.get("params", {})
    if pipe["entry"] not in stages:
        err(where, f"P1 entry {pipe['entry']} is not a stage")
    for e in pipe["edges"]:
        for end in ("from", "to"):
            if e[end] not in stages:
                err(where, f"P1 edge {e['id']} {end} unknown stage {e[end]}")
    blob = json.dumps(pipe)
    for ref in sorted(set(re.findall(r"pipeline\.params\.([a-z][a-z0-9_]*)", blob))):
        if ref not in pparams:
            err(where, f"P1 expressions read pipeline.params.{ref}, which is not declared")

    specs = {}
    for sid, st in stages.items():
        tname = st["template"]["name"]
        if tname in base_templates:
            err(where, f"P1 stage {sid} uses base template {tname}, which cannot run")
        elif tname not in flat_specs:
            warn(where, f"P1 stage {sid} uses {tname}, not among the examples")
        else:
            specs[sid] = (tname, flat_specs[tname])

    # P2 every exit used is real, and every HandOff reason is wired
    for sid, (tname, spec) in specs.items():
        out = [e for e in pipe["edges"] if e["from"] == sid]
        wired = {e["on"].get("handoff_reason") for e in out if e["on"]["terminal"] == "handoff"}
        for r in sorted(handoff_reasons(spec) - wired):
            err(where, f"P2 stage {sid} ({tname}) has HandOff reason {r} with no edge")
        finisher_ids = {f["id"] for f in spec["completion"].get("finishers", [])}
        for e in out:
            r = e["on"].get("handoff_reason")
            if r and r not in handoff_reasons(spec):
                err(where, f"P2 edge {e['id']} uses HandOff reason {r}, which {tname} does not declare")
            f = e["on"].get("finisher")
            if f and f not in finisher_ids:
                err(where, f"P2 edge {e['id']} uses finisher {f}, which {tname} does not declare")
            bad = set(e["on"].get("status", [])) - set(spec["completion"]["statuses"])
            if bad:
                err(where, f"P2 edge {e['id']} waits for status {sorted(bad)}, which {tname} never ends with")

    # P3 carry, P4 params
    for e in pipe["edges"]:
        if e["to"] not in specs:
            continue
        tname, spec = specs[e["to"]]
        missing = sorted(set(e.get("carry", [])) - carry_inputs(spec) - {"artifacts"})
        if missing:
            err(where, f"P3 edge {e['id']} carries {missing} but {tname} has no such carry input")
    for sid, (tname, spec) in specs.items():
        tparams = params_by_template[tname]
        bound_sets = []
        incoming = [e for e in pipe["edges"] if e["to"] == sid]
        base = set(stages[sid].get("params", {}))
        if sid == pipe["entry"]:
            bound_sets.append(("entry", base))
        for e in incoming:
            bound_sets.append((f"edge {e['id']}", base | set(e.get("params", {}))))
        for label, bound in bound_sets:
            for pname in sorted(bound - set(tparams)):
                err(where, f"P4 stage {sid} via {label} binds {pname}, which {tname} does not declare")
            for pname, p in tparams.items():
                if p.get("required") and "default" not in p and pname not in bound:
                    err(where, f"P4 stage {sid} via {label} does not bind required param {pname} of {tname}")

    # P5 tiers within the pipeline's ceiling
    if "max_tier" in pipe:
        for sid, (tname, spec) in specs.items():
            tier = spec["model"]["tier"]
            if isinstance(tier, str) and TIER_ORDER[tier] > TIER_ORDER[pipe["max_tier"]]:
                err(where, f"P5 stage {sid} runs at {tier}, above the pipeline's max_tier")

    # P6 reachable, acyclic, within max_hops
    succ = {sid: [e["to"] for e in pipe["edges"] if e["from"] == sid] for sid in stages}
    depth, longest = {}, 0

    def visit(sid, d, path):
        nonlocal longest
        if sid in path:
            err(where, f"P6 cycle through {sid}")
            return
        depth[sid] = max(depth.get(sid, 0), d)
        longest = max(longest, d)
        for nxt in succ.get(sid, []):
            visit(nxt, d + 1, path | {sid})

    if pipe["entry"] in stages:
        visit(pipe["entry"], 0, frozenset())
    for sid in sorted(set(stages) - set(depth)):
        err(where, f"P6 stage {sid} is unreachable from the entry")
    if longest > pipe.get("max_hops", 3):
        err(where, f"P6 the longest path is {longest} hops, above max_hops {pipe.get('max_hops', 3)}")

    # P7 every stage can run as the same principal type
    kinds = None
    for sid, (tname, spec) in specs.items():
        ra = set(spec.get("authority", {}).get("run_as", []))
        kinds = ra if kinds is None else kinds & ra
    if kinds is not None and not kinds:
        err(where, "P7 no principal type every stage allows")

    # P8 sink tools are the pipeline's own declaration
    groups, tools_by_group = group_tools(pipe)
    declared = {t["tool"]: t.get("annotations", {}) for tools in tools_by_group.values() for t in tools}
    declared_servers = {s["id"] for s in (pipe.get("tools") or {}).get("servers", [])}
    for addr in declared:
        if addr.startswith("mcp:") and addr.split("/", 1)[0][4:] not in declared_servers:
            err(where, f"P8 {addr} names a server the pipeline does not declare")
    used = []
    for s in pipe.get("sinks", []):
        if s["kind"] == "tool":
            if s["tool"] not in declared:
                err(where, f"P8 sink {s['id']} calls {s['tool']}, which the pipeline does not declare")
            else:
                used.append((s["tool"], declared[s["tool"]]))
    r12(where, sorted(kinds or []), used, servers)


# --- main ---------------------------------------------------------------------

def check_openapi():
    openapi = yaml.safe_load((HERE / "openapi.yaml").read_text())
    refs = set()

    def collect(node):
        if isinstance(node, dict):
            if isinstance(node.get("$ref"), str):
                refs.add(node["$ref"])
            for v in node.values():
                collect(v)
        elif isinstance(node, list):
            for v in node:
                collect(v)

    collect(openapi)
    for ref in sorted(refs):
        file, _, pointer = ref.partition("#")
        if file:
            target = (HERE / file).resolve()
            if not target.exists():
                err("openapi.yaml", f"missing file {file}")
                continue
            node = json.loads(target.read_text())
        else:
            node = openapi
        for part in pointer.lstrip("/").split("/") if pointer else []:
            node = node.get(part) if isinstance(node, dict) else None
        if node is None:
            err("openapi.yaml", f"dangling {ref}")


def main():
    for path in sorted(SCHEMAS.glob("*.schema.json")):
        Draft202012Validator.check_schema(json.loads(path.read_text()))
    check_openapi()

    docs = {p.name: json.loads(p.read_text()) for p in sorted(EXAMPLES.glob("*.json"))}
    templates, servers, saved, pipelines = {}, {}, {}, {}
    kinds = [
        (".template.json", "template.schema.json"),
        (".pipeline.json", "pipeline.schema.json"),
        (".tool-group.json", "tools.schema.json#/$defs/SavedToolGroup"),
        (".trigger.json", "trigger.schema.json#/$defs/Trigger"),
        (".mcp-server.json", "tools.schema.json#/$defs/McpServer"),
        ("delegation.json", "principal.schema.json#/$defs/Delegation"),
        ("deployment.json", "deployment.schema.json"),
    ]
    for fname, doc in docs.items():
        if fname.startswith("run-request"):
            validate(fname, "run.schema.json#/$defs/RunRequest", doc)
            continue
        ref = next((r for suffix, r in kinds if fname.endswith(suffix)), None)
        if ref is None:
            err(fname, "no rule says what this example is")
            continue
        validate(fname, ref, doc)
        if fname.endswith(".template.json"):
            templates[(doc["name"], doc["version"])] = doc
        elif fname.endswith(".pipeline.json"):
            pipelines[doc["name"]] = doc
        elif fname.endswith(".tool-group.json"):
            saved[(doc["name"], doc["version"])] = doc
        elif fname.endswith(".mcp-server.json"):
            servers[doc["id"]] = doc

    flat_specs, params_by_template = {}, {}
    base_templates = {name for (name, _), t in templates.items() if t.get("runnable") is False}
    for (tname, version), t in templates.items():
        where = f"{tname}@{version}"
        if tname in base_templates:
            continue  # a base template is checked only through the templates that extend it
        try:
            params, spec = flatten(t, templates)
            spec = resolve_groups(spec, saved)
        except ValueError as e:
            err(where, str(e))
            continue
        validate(where, "agent-spec.schema.json", spec)
        flat_specs[tname] = spec
        params_by_template[tname] = params
    for (tname, version), t in templates.items():
        if tname in flat_specs:
            where = f"{tname}@{version}"
            check_spec(where, params_by_template[tname], flat_specs[tname])
            check_server_auth(where, flat_specs[tname], servers)
            if handoff_reasons(flat_specs[tname]) and not any(st["template"]["name"] == tname for p in pipelines.values() for st in p["stages"].values()):
                warn(where, "R6 declares HandOff reasons but no pipeline wires them; run alone it has no HandOff")
    for name, p in pipelines.items():
        check_pipeline(f"{name}@{p['version']}", p, flat_specs, params_by_template, servers, base_templates)

    targets = {**{t: params_by_template[t] for t in params_by_template}, **{f"pipeline:{n}": p["params"] for n, p in pipelines.items()}}
    for fname, doc in docs.items():
        if not (fname.endswith(".trigger.json") or fname.startswith("run-request")) or "adhoc" in doc:
            continue
        key = f"pipeline:{doc['pipeline']['name']}" if "pipeline" in doc else doc["template"]["name"]
        tparams = targets.get(key)
        if key in base_templates:
            err(fname, f"targets base template {key}, which cannot run")
            continue
        if tparams is None:
            warn(fname, f"targets {key}, not among the examples")
            continue
        for p in doc.get("params", {}):
            if p not in tparams:
                err(fname, f"binds {p}, which {key} does not declare")
        for pname, p in tparams.items():
            if p.get("required") and "default" not in p and pname not in doc.get("params", {}):
                err(fname, f"does not bind required param {pname} of {key}")
        if doc.get("run_as", {}).get("mode") == "invoker" and doc["source"]["kind"] != "manual":
            err(fname, "run_as invoker is for manual sources only")

    for w in warnings:
        print("warn ", w)
    for e in errors:
        print("error", e)
    print(f"{len(templates)} templates ({len(base_templates)} base), {len(pipelines)} pipelines, {len(saved)} saved tool groups, {len(docs)} examples, {len(errors)} errors, {len(warnings)} warnings")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
