# marimo — the `marimo-pair` skill

`marimo/_server/ai/skills/marimo-pair/SKILL.md`. Excerpted; the whole
file is ~275 lines.

## Frontmatter

```yaml
---
name: marimo-pair
description: >-
  Work inside the user's live marimo notebook from the code editor: run Python
  in the same kernel the user does, inspect live notebook state, and commit
  durable notebook changes through code mode. Use whenever you create, analyze,
  or improve the user's marimo notebook.
---
```

## The source of truth is the kernel, not the file

> marimo is a reactive Python runtime … The active runtime holds the kernel
> namespace, cell state, and dataflow graph. **The notebook (`.py` file) is the
> artifact the kernel writes from that state while a session is running.**
>
> **WARNING. The active runtime is the source of truth.** You are working inside
> the user's live notebook session. The kernel — not the `.py` file on disk —
> holds the truth about cells, variables, and the dataflow graph. Make every
> notebook change through `marimo._code_mode` (`cm`); **direct file edits WILL
> NOT reach the live kernel or user, and the kernel may overwrite them on save.**
> Reading disk is fine, but prefer `ctx.cells[...].code` for current cell code.
>
> **WARNING. Every notebook edit goes through code mode — no exceptions.** …
> There is no separate file-editing path — `execute_code` + `cm` is the only way
> to reach the user's running session. Running ad-hoc Python with `execute_code`
> to explore or test is fine; _persisting any change to the notebook_ is only
> ever done via `cm`.

This is the sharpest statement in the collection of a problem every
notebook-attached agent has and most ignore: **the agent has a `Write`
tool and a path to the `.py` file, and using them is silently wrong.**
The document on disk is a projection of live state, so editing it is
editing a cache. The warning is repeated twice, in bold, at the top,
which is the right weight for an instruction whose violation produces no
error — just lost work at the next save.

The generalisation for any harness attached to a live process: **name the
authority explicitly, and name the tool that looks like it would work but
doesn't.**

## The scratchpad: exploration that cannot leak

> `execute_code` evaluates Python in marimo's scratchpad: a temporary namespace
> with **a shallow copy of the kernel globals**. Notebook variables are available
> by name, but **new top-level bindings and rebindings are discarded after each
> call.** In-place mutations to notebook-owned objects can persist because those
> names still reference live objects.
>
> Each call reports stdout and stderr from the scratchpad, plus console output
> from notebook cells it causes to run, including reactive descendants.

```python
print(df.head())

x = 10
print(x)
```

> Here `df` comes from notebook globals, while `x` is a scratchpad-local binding.
> `x` exists for this call only and WILL NOT be added to notebook globals.

A **shallow copy** is the precise choice: the agent can read every
notebook object at full fidelity and cannot rebind any name, but it *can*
mutate an object in place. The skill says so rather than pretending the
isolation is total — which matters, because `df.drop(columns=[...],
inplace=True)` in a "read-only" probe would change the user's data.

This is the same boundary as jupyter-mcp's `execute_code` ("do not
perform variable assignments that affect subsequent Notebook execution")
— but enforced by the namespace rather than requested in a description.
**Mechanism where the other has a rule.**

## `cm`: a transaction

> `marimo._code_mode` is a PRIVATE, UNSTABLE agent API (note the leading
> underscore). It exists for tools like this skill to drive a live kernel from
> the scratchpad. DO NOT import it from notebook cells, library code, or
> anything a user would run …

```python
import marimo._code_mode as cm

async with cm.get_context() as ctx:
    cid = ctx.create_cell("x = df.head()")
    ctx.run_cell(cid)
```

> Inside the context, queued mutation methods are synchronous. Call them
> directly; do not `await` them. **Each call queues an operation for marimo to
> apply when the context exits normally. If the block raises, the queue is
> discarded.**
>
> On clean exit, marimo applies packages, validates and applies structural cell
> changes, runs queued cells, then may run dependents. **Validation is only
> structural since queued cell runs can still error.**

An honest-to-goodness transaction: queue, commit on clean exit, roll back
on raise — with the limit stated (structural validation only; a queued
cell can still throw at run time). And a stated ordering: packages →
structural changes → queued runs → reactive dependents.

The aliasing hazard is called out too, which is the sort of thing that
only shows up in production:

> After this block exits and the new cell runs, `x` is notebook state. Later
> scratchpad calls can read `x` by name. **Code later in the same scratchpad
> call should read `ctx.globals["x"]`, because the scratchpad namespace was
> copied before the cell ran.**

## The graph contract

> - **No cycles** - cells cannot depend on each other in a cycle.
> - **No public redefinitions across cells** - each name has one owning cell.
> - **No wildcard imports** - `import *` prevents static analysis of definitions.
>
> When `cm` submits a cell body, marimo parses its top-level definitions and
> references. A top-level name enters the graph unless it is private with a
> leading underscore. … **If a `cm` edit violates the contract, marimo rejects
> the structural change and returns the validation error.**

Rejection with a validation error, not best-effort application — so the
agent's mistake costs a round-trip rather than a broken notebook. The
skill then teaches the private-name escape hatch with a worked
before/after pair (a loop whose `i`, `value`, `total` leak into the graph
versus the same loop with `_i`, `_value`, `_total`), and immediately
closes the abuse:

> - **Reuse notebook imports** - if `np` already exists, use it or edit the
>   owning import cell. **DO NOT add `import numpy as _np` just to bypass the
>   graph.**

That pair — here is the escape hatch, here is the one use of it I know
you will attempt — is good prompt engineering. The model *will* reach for
`_np` the first time it hits `Multiply-defined names`.

## Reading the notebook: document view and graph view

```python
for cell in ctx.cells:
    cell  # .id, .code, .name, .config, .status, .errors

ctx.cells["setup"]         # by name
ctx.cells[0]               # by position
list(ctx.cells.keys())     # all IDs, in notebook order

for cid, impl in ctx.graph.cells.items():
    impl  # .defs, .refs   (sets of public names)

ctx.graph.descendants(cid)   # cells that re-run when this one changes
ctx.graph.ancestors(cid)     # cells this one depends on
```

> In marimo, deletes are _destructive_ so it can be useful to query the
> descendants prior to deleting to understand it's impact.

**Two views of the same object — `ctx.cells` is the document,
`ctx.graph` is the dataflow** — and a blast-radius query before a
destructive operation. That last is a pattern worth generalising well
beyond notebooks: where the harness knows the dependency graph, the agent
should be told to ask it what a delete will break.

## Durability guidance

> The graph contract keeps marimo able to run and save the notebook. **Passing
> those checks alone does not guarantee a useful artifact.** Committed cells
> should still be readable, rerunnable, and editable.
>
> Make durable edits that reuse the notebook's existing names, imports,
> dependencies, and UI model. **Don't be lazy. Avoid one-off workarounds that
> pass `cm` validation but leave a brittle notebook.**

> - **Read before replacing** - for now, another editor may change a cell between
>   scratchpad calls. Before `edit_cell`, read the current body from
>   `ctx.cells[...]` and submit the full replacement.
> - **Manage packages through `cm`** - use `ctx.packages.add()` or
>   `ctx.packages.remove()` instead of direct `uv` or `pip`; confirm
>   non-obvious dependency changes.
> - **Avoid transient paths** - persisted cells should not depend on `/tmp/...`
>   unless the work is intentionally transient.
> - **Delete deliberately** - deleting a cell removes globals it defines.

"Validation passing is not the same as the artifact being good" is the
notebook version of "the tests pass but the code is bad", and it is
stated rather than hoped for. `create_cell` defaults to
`hide_code=True`; the skill flags that as something the user may not
want, which is a nice instance of telling the model about a default it
would otherwise inherit silently.

## UI state has two update paths

> - **Set `mo.ui.*` through `cm`** - use `ctx.set_ui_value(element, value)` inside
>   `cm.get_context()`.
> - **Set anywidget traitlets directly** - synced traitlets are Python
>   attributes, for example `widget.value = 5`.

An agent driving a dashboard has to know which widgets round-trip through
the kernel's reactive machinery and which are plain synced attributes.
This is the smallest concrete example in the collection of *what "chat
with a dashboard" actually requires*: a typed handle on each interactive
element and a defined way to set it.

## Screenshots

`marimo/_code_mode/screenshot.py`:

```python
"""Headless Chromium screenshot session for cell outputs.

Lazily launches a browser connected to the running notebook server
in kiosk mode and reuses it across captures.
"""

_READINESS_TIMEOUT_MS = 90_000
_NETWORK_IDLE_TIMEOUT_MS = 10_000
_VIEWPORT_WIDTH = 1440
_VIEWPORT_HEIGHT = 1000
_DEVICE_SCALE_FACTOR = 2.0
_ATTACH_TIMEOUT_MS = 5_000       # fail fast if the cell container never attaches
_SELECTOR_PROBE_TIMEOUT_MS = 1_000
```

```python
class ScreenshotError(RuntimeError):
    """A cell screenshot could not be captured.

    Messages include actionable hints (available cell IDs,
    install commands, likely misconfigurations).
    """
```

`ctx.screenshot(cell_id)` drives Playwright against the *live kiosk page*
and returns a `data:image/png;base64,...`. Credentials for the callback
are stamped onto each control request's `meta` by the server
(`screenshot_meta.py`) — the kernel-side code never holds a token it
wasn't handed for that request.

Why this matters beyond marimo: it closes the verification loop for
visual output. Every other harness in this folder that produces a chart
either hands it to the user unseen, or renders it server-side and reasons
about the spec. Here the agent can look at **what the user will actually
see**, including CSS, theme, layout, widget state and overflow — the
class of defect a Vega-Lite spec cannot express and a matplotlib PNG does
not capture. It is the notebook-shaped version of the browser
verification loops in
[`../../agent-vision-multimodal.md`](../../agent-vision-multimodal.md),
and the timeouts show it is not free: 90 s readiness, 10 s network idle,
a warm browser reused across captures.

Two design details worth copying: **fail fast on the branch that cannot
succeed** (5 s to find the container, rather than letting a doomed
locator burn the caller's full timeout), and **errors carry the
recovery** (available cell IDs, the install command).
