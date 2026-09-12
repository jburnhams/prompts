# Data Formulator (Microsoft Research)

- **Type**: chart-first data-analysis agent with a canvas UI · **Vendor**:
  Microsoft Research · **Licence**: MIT
- **Source**: https://github.com/microsoft/data-formulator — `main` @
  `5477f0e`, version `0.8b1` (2026-08-15)
- **Retrieved**: 2026-09-12

The single most useful source in this folder for **Forge's actual
questions**, because it answers three of them explicitly and in prompt
text rather than in architecture diagrams:

1. One general tool or many focused ones? — **both, split by what the
   call commits.**
2. How does an artifact get created? — **the model emits code plus a
   declarative spec; the harness renders. The model is forbidden from
   drawing.**
3. What unlocks extra capability? — **a `load_skill` tool that gates
   actions, not just instructions.**

## Files

| File | Upstream path | What it is |
|---|---|---|
| [`analyst-system-prompt.md`](./analyst-system-prompt.md) | `py-src/data_formulator/analyst/agent.py` | The `SYSTEM_PROMPT`, verbatim, with its tools-vs-actions taxonomy |
| [`core-skill.md`](./core-skill.md) | `py-src/data_formulator/analyst/skills/core/SKILL.md` | The always-on skill: the `visualize` and `ask_user` action contracts, the execution rules, and the chart-type reference |
| [`tool-defs.md`](./tool-defs.md) | `py-src/data_formulator/analyst/tools.py` | The three inspection tool schemas and the assembly function, with its commentary |
| [`sandbox.md`](./sandbox.md) | `py-src/data_formulator/sandbox/` | The three sandbox backends and the `addaudithook` technique |

## The taxonomy, which is the whole contribution

> Everything you do is a function/tool call, but calls come in two kinds and
> keeping them straight is essential:
>
> - **Inspection tools** (internal — for gathering information) … Their
>   results return to you and are **not** shown to the user. They commit
>   nothing and are **independent** — none depends on another's result — so
>   call as many as you need, across as many rounds as you need, until you
>   have enough to act.
> - **Actions** (committing — shown to the user) … Each renders a
>   user-visible surface, and its result is returned to you just like a tool
>   result so you can react to it.
>
> **Actions are sequential — take exactly one, then wait for its result.**

Four distinctions are being collapsed into one clean line, and they
happen to coincide here:

| | Inspection tool | Action |
|---|---|---|
| Commits state? | no | yes |
| User sees it? | no | yes |
| Parallel-safe? | yes | no |
| Result feeds back to model? | yes | **yes** |

The last row is the subtle one. An action is *not* a turn-ender: its
result comes back like any tool result *"so you can react to it"*. What
makes it sequential is not the protocol but the epistemics, and the
prompt argues it rather than asserting it:

> each action's result shapes your next decision — the chart you'd draw
> next depends on what this one reveals — so choosing two at once would
> make the second a blind guess, decided before you've seen the first's
> outcome.

And then backs the argument with a mechanism, disclosed:

> (If you do emit several actions at once, only the first runs and the
> rest are discarded — batching only loses work.)

Telling the model the enforcement exists is what makes the rule stick
without an error round-trip. Compare the same shape in
[`../jupyter-mcp/`](../jupyter-mcp) (`execute_code` vs
`insert_execute_code_cell`) and [`../marimo/`](../marimo) (scratchpad vs
`cm` context): three teams, three products, one boundary.

## Termination is by absence

> **To finish, reply with plain text and no action.** Plain text is your
> **closing answer** — the run is over and you expect nothing further (the
> user's next message starts a fresh turn). …
> There is no separate "stop" or "summary" action: you stop by simply not
> acting.

No `Complete` tool, no `final_answer`. Against the rest of this
collection that is unusual — SWE-agent, smolagents, Forge and Claude Code
all use an explicit terminal call — and it is bought by having a
*separate* pausing primitive:

> **Whenever you expect the user to reply … use the `ask_user` action
> instead.** It renders a question widget and pauses the run for their
> reply, so the conversation resumes in the same turn. … Plain text never
> asks for input; `ask_user` always does.

So the two terminal states are distinguished by *which channel carries
them*, not by an argument to one call: text ends, `ask_user` suspends.
That is exactly the distinction Forge draws between `Complete` and
`AskUser` in [`../../agent-design/formats.md`](../../agent-design/formats.md),
reached independently and with one fewer tool.

## Skills gate actions, not just context

> Your baseline capabilities come from the **core** skill, which is
> **always loaded automatically** … extra capabilities are packaged as
> **extension skills** — each one unlocks an additional action (and
> sometimes extra tools), but only after you load it …
> Calling an extension skill's action **before** loading the skill will
> not execute — you'll be asked to load it first.

This is progressive disclosure with teeth. In Claude Code's skills the
gate is advisory — the instructions load, and nothing stops you acting
without them. Here `write_report` is *not in the tool list* until
`load_skill("report")` has run, and the tool-assembly function
(`build_tools`) rebuilds the surface each turn from the loaded set. The
reason `load_skill` is a *tool* and not an *action* is stated:

> Loading a skill pulls its `SKILL.md` body into context and unlocks the
> gated actions it declares. **Reading a doc is read-only and
> idempotent**, so this is a tool (parallel-safe) rather than a
> serialized action.

The taxonomy is doing real work: membership follows from the properties,
not from a category judgement.

## Budget as a ceiling, not a target

> - You have a budget of **{max_iterations} actions** for this run — a
>   **hard ceiling, not a target**.
> - Match the response depth to the user's request. Create charts that
>   materially contribute to the answer, and stop when the answer is
>   sufficient.

The parenthetical matters. A numeric budget stated without it reliably
reads as a quota to fill — the same failure mode as "generate 5 findings"
in review prompts (`../../code-review-approaches.md` §6).

## Also here: a routing agent worth stealing

`agents/agent_simple.py` holds a one-word classifier that routes a chart
edit between two very different pipelines:

> The test: does the request change the set of fields bound to chart
> encodings (x, y, color, size, shape, row, column, facet, theta, etc.)?
>
> **STYLE** — encoding fields are unchanged … filter / sort / top-N /
> limit (even on fields not currently encoded, as long as the field
> already exists in the data) … any visual change: theme, colors, fonts,
> legend, axes, mark size/opacity, donut hole, tooltip text
>
> **DATA** — encoding fields change, or a new field must be
> computed/joined …
>
> Requests may be in any language. Reply with one word: STYLE or DATA.

A good example of a **cheap model call replacing a policy argument**: the
expensive path (re-run code against the data) is only taken when a
crisply-stated test says it must be. The test is falsifiable — "does the
set of encoded fields change" — rather than a vibe, which is what makes
it a classifier rather than a coin flip.
