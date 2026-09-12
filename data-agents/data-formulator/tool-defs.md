# Data Formulator — the inspection tool schemas

`py-src/data_formulator/analyst/tools.py`, effectively in full (151
lines). The module docstring and the function docstrings are the design
rationale, so they are kept.

```python
"""Inspection tools for the analyst agent.

Tools are parallel-safe, internal, side-effect-free capabilities the agent may
call freely within a turn to gather information before committing to a single
user-visible action. See ``design-docs/35`` §4.1.

  - ``execute_python_script`` — run a general-purpose Python script in the
    sandbox to inspect/compute (stdout returned).
  - ``inspect_source_data`` — schema + stats + sample rows for source tables.
  - ``load_skill`` — pull a skill's ``SKILL.md`` body into context, unlocking
    its gated actions (progressive disclosure; reading a doc is read-only).

``inspect_chart`` is a skill-private tool used by report-style skills and is
contributed by those skills rather than living in the always-on tool set.
"""
```

## `execute_python_script`

```python
EXECUTE_PYTHON_SCRIPT_TOOL: dict[str, Any] = {
    "type": "function",
    "function": {
        "name": "execute_python_script",
        "description": (
            "Execute a general-purpose Python script in the sandbox. Here you "
            "use it to inspect data, compute statistics, or verify assumptions "
            "before you act — print() to stdout, which is returned to you and is "
            "not shown to the user. pandas, numpy, duckdb, sklearn, scipy are available."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "purpose": {
                    "type": "string",
                    "description": "One-sentence description of what this script does and why (shown to user as progress).",
                },
                "code": {
                    "type": "string",
                    "description": "Python script to execute. Use print() to surface output.",
                },
            },
            "required": ["purpose", "code"],
        },
    },
}
```

**`purpose` is a required argument whose only consumer is the UI.** The
script's *output* is invisible to the user; the *intent* is rendered as a
progress line. This is a neat resolution of a real tension: the user
should be able to follow what the agent is doing without being shown
twenty stdout dumps. Making it required rather than optional means the
progress feed never has gaps.

It is also the cheapest possible form of the "narrate before you act"
rule that several prompts in this collection state in prose (marimo's
*"You must always explain to the user why you are using a tool before
invoking it"*) — here it is a schema field, so it cannot be skipped.

## `inspect_source_data`

```python
INSPECT_SOURCE_DATA_TOOL: dict[str, Any] = {
    "type": "function",
    "function": {
        "name": "inspect_source_data",
        "description": (
            "Get a detailed summary of one or more source tables — schema, "
            "field-level statistics, and sample rows.  Cheaper than explore() "
            "for basic data inspection."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "table_names": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of workspace table names, as listed in the available-tables context, to inspect.",
                },
            },
            "required": ["table_names"],
        },
    },
}
```

Batched by design (`table_names` is an array, not a string) — one call
for the whole join, not one per table. The stale `explore()` reference in
the description is a real artefact of the source at this commit and is
left as-is.

## `load_skill`, built per run

```python
def build_load_skill_tool(skill_names: list[str]) -> dict[str, Any]:
    """Build the ``load_skill`` tool, constraining ``name`` to known skills.

    Loading a skill pulls its ``SKILL.md`` body into context and unlocks the
    gated actions it declares. Reading a doc is read-only and idempotent, so
    this is a tool (parallel-safe) rather than a serialized action.
    """
    name_schema: dict[str, Any] = {
        "type": "string",
        "description": "The skill to load (unlocks the actions it declares).",
    }
    if skill_names:
        name_schema["enum"] = list(skill_names)
    return {
        "type": "function",
        "function": {
            "name": "load_skill",
            "description": (
                "Load a skill's instructions into context so you can use the "
                "actions it unlocks. Call this BEFORE emitting a gated action "
                "(e.g. load_skill('report') before write_report)."
            ),
            "parameters": {
                "type": "object",
                "properties": {"name": name_schema},
                "required": ["name"],
            },
        },
    }
```

The `enum` is built from the skills actually available this run — the
same runtime-constrained-enum move as Open Interpreter's `language`
field, and for the same reason.

## Assembling the surface

```python
def build_tools(
    skill_names: list[str],
    extra_tools: list[dict[str, Any]] | None = None,
    action_tools: list[dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    """Assemble the tool set exposed to the LLM each turn.

    Three groups share the one function-calling surface (see ``design-docs/36``):

      * **inspection tools** (``explore`` / ``inspect_source_data`` / a loaded
        skill's own tools) — contributed by the always-on ``core`` skill and any
        loaded skills, arriving via ``extra_tools``. Parallel-safe, non-committing.
      * **``load_skill``** — the progressive-disclosure switch, added here with
        its ``name`` enum built from ``skill_names`` (the loadable/gated skills).
      * **action tools** — the committing surfaces a turn may end with
        (``visualize`` / ``delegate`` always;
        ``write_report`` once the report skill is loaded). Passed via
        ``action_tools``; the agent partitions a response by which tool names
        are committing actions and enforces the one-per-turn cardinality guard.

    Inspection tools are listed first, then ``load_skill``, then the committing
    actions. De-duplicates by function name as a safety net (a clash is also
    warned at registry-build time).
    """
```

Three facts worth carrying:

1. **The tool list is rebuilt every turn** from the loaded skill set. The
   model's capability surface is a function of its own prior calls.
2. **Ordering is deliberate** — inspection first, `load_skill` next,
   actions last. Position in a tool list is a weak prior, and this one
   points the right way.
3. **The one-action cardinality guard lives in the agent loop**, not in
   the schema: the response is partitioned by whether a called name is in
   the action set, the first action runs and the rest are discarded. The
   system prompt discloses exactly this. There is no protocol-level way
   to say "these tools are mutually exclusive and at most one per turn",
   which is why every harness in this folder that wants the rule enforces
   it after the fact and tells the model it did.
