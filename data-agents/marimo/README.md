# marimo

- **Type**: reactive Python notebook with an embedded agent · **Vendor**:
  marimo · **Licence**: Apache-2.0
- **Source**: https://github.com/marimo-team/marimo — `main` @ `1793fe5`
  (2026-09-11)
- **Retrieved**: 2026-09-12

The best available answer to **"what does it mean for an agent to work
inside a live notebook the user is also using?"** — because marimo's
reactive model forces the question to be answered precisely rather than
by convention.

Two things here that exist nowhere else in this collection:

- A **transactional agent API** over a running kernel: a scratchpad
  namespace where the agent's bindings are discarded, and an explicit
  context manager that queues durable changes and applies them only on
  clean exit.
- An agent that can **screenshot its own rendered output** — headless
  Chromium against the live notebook page, per cell, at 2× DPI.

## Files

| File | Upstream path | What it is |
|---|---|---|
| [`modes-and-prompts.md`](./modes-and-prompts.md) | `marimo/_server/ai/prompts.py` | The four copilot modes and their capability/limitation blocks, the per-language rules, and how kernel state is rendered into context |
| [`marimo-pair-skill.md`](./marimo-pair-skill.md) | `marimo/_server/ai/skills/marimo-pair/SKILL.md` | The code-mode skill: scratchpad semantics, the `cm` transaction, the graph contract, and the deferred capabilities |

## Four modes, graded by what tools can do

`_get_mode_intro_message` switches on `CopilotMode`:

| Mode | Tools | The stated limitation |
|---|---|---|
| `manual` | none | "You do NOT have access to any external tools, plugins, or APIs." |
| `ask` | read-only | "All tool use is strictly read-only. You may not perform write, edit, or execution actions." |
| `agent` | read + write | "You are encouraged to edit existing cells in the notebook or add new cells." |
| `code_mode` | one: `execute_code` | "you have access to the notebook's kernel and can execute code." |

The ladder is a **permission mode expressed to the model**, and the
alignment with the harness is exact: in `ask` mode the write tools are
not registered, and the prompt says so. This is the cheapest correct
version of the pattern `../../agent-permissions-approval.md` argues for —
the model's description of its own powers is generated from the same
switch that grants them.

`agent` mode also carries a verification loop as prose:

> - You should do the following things after editing the notebook:
>   1. Use the lint notebook tool to check for errors and lint issues
>   2. Run stale cells tool to run the code
>   3. If there are errors in cells you have added, edit the existing cell.
>      **Don't add new cells to correct errors.**
> - If you say you're about to do something, actually do it in the same turn
>   (run the tool call right after).
> - Group code into logical cells, eg. functions should be in separate cells
>   and all the calls will be in one cell.

*"Don't add new cells to correct errors"* is notebook-specific and
important: the natural LLM repair move — append a corrected version — is
exactly wrong in a document that a human will read top-to-bottom and
re-run. It is the notebook analogue of "edit the file, don't write
`file_v2.py`".

## Code mode: one tool, and a private API behind it

```python
async def execute_code(code: str) -> CodeExecutionResult:
    """Run Python inside the running notebook's kernel scratchpad.

    Use this for all notebook mutations via `marimo._code_mode`.
    """
```

One tool. Everything — inspection, testing, cell creation, cell editing,
package installation, setting a UI widget's value, taking a screenshot —
happens as Python inside it, against a private module (`cm`). This is
the **Code Mode** position that
[`../../deepseek-harness/`](../../deepseek-harness) states as a thesis
and [`../../openclaw/`](../../openclaw)'s Swarm states as *"the program
is the orchestration"*, applied to a notebook: the tool surface is an
API, not a protocol.

The trade it buys is real. A tool-per-operation surface would need
`create_cell`, `edit_cell`, `delete_cell`, `run_cell`, `move_cell`,
`set_ui_value`, `add_package`, `screenshot`, `get_graph` — nine schemas,
nine descriptions, nine round-trips to do a five-step edit. Here it is
one `execute_code` with a `help(cm)` call to discover the rest. Compare
[`../jupyter-mcp/`](../jupyter-mcp)'s eighteen tools over the same
substrate: both work; the token costs and the failure modes differ.

The trade it pays is discoverability, and the skill handles that with a
mandatory first move:

> ## Required First Kernel Command
>
> Start every code-mode session with this dedicated `execute_code` call:
>
> ```python
> import marimo._code_mode as cm
> help(cm)
> ```
>
> 1. Run only the inspection command above.
> 2. Wait for successful `help(cm)` output.
> 3. Use `cm.get_context()` or another `cm` API in a later `execute_code` call.
>
> Do not combine the inspection with task-specific code, and do not use another
> `cm` API before the inspection succeeds. **This verifies the private, unstable
> API exposed by the marimo version in the user's active kernel.**

That last sentence is the justification, and it is a good one: the API is
versioned with the user's install, not with the prompt. Rather than
freezing a tool schema against a moving target, the agent is told to read
the docstring of whatever it actually attached to. **Runtime
introspection as the tool schema.**

## Deferred capabilities

```python
gotchas_capability: Capability = Capability(
    id="gotchas",
    description="Name redefinition, cached module proxies, and other notebook traps.",
    instructions=load_reference("gotchas"),
    defer_loading=True,
)
```

Three of them — `gotchas`, `notebook-improvements`, `rich-representations`
— each a description in the prompt and a body loaded on request, with a
blunt instruction not to route around the mechanism:

> Load these with the `load_capability` tool when you need deeper
> guidance. **Do not read reference files from disk.**

Same shape as Data Formulator's `load_skill` and Claude Code's skills,
and the same reason. The "do not read from disk" line exists because an
agent with a `Read` tool and a visible path will bypass the loader,
losing whatever the loader does (here: attribution of what was loaded,
and the version-matched copy).
