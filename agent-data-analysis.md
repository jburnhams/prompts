# Data-analysis agents: harnesses, tools and techniques

Read from source across thirteen harnesses in
[`data-agents/`](./data-agents), plus the coding agents already in this
collection. The question behind it: **this repo's design
([`agent-design/`](./agent-design)) covers coding and review. What would
it take to cover data analysis in the same framework — and what, if
anything, is genuinely different?**

The short answer is that less is different than expected, and the
differences are sharper than expected. A data agent is not a coding agent
with pandas in the prompt. Four things change, and they change together:

1. **The agent's work product is not a diff.** It is an answer, a chart,
   a table, a report — an *artifact* that has to be rendered by something
   and looked at by someone. Coding agents can pretend their output is
   text; data agents cannot.
2. **The interesting state lives in a running process, not on disk.** A
   coding agent's world is the working tree, which it can re-read at any
   time. A data agent attached to a kernel has a namespace it cannot see,
   which drifts from its own transcript every turn.
3. **The data is too big to look at, always.** A repository fits in a
   context window if you're selective. A table does not fit, ever, at any
   level of selectivity — so every read is a *projection*, and choosing
   the projection is the main skill.
4. **Correctness is not checkable by running it.** Code that runs can
   still be wrong; analysis that runs *and produces a plausible number*
   is the normal failure. There is no test suite.

Everything below is organised around those.

**Contents**

- [§1 What the category actually is](#1-what-the-category-actually-is)
- [§2 The UX surfaces, and what each demands](#2-the-ux-surfaces-and-what-each-demands)
- [§3 The fork in the road: persistent state](#3-the-fork-in-the-road-persistent-state)
- [§4 One `execute` or many tools](#4-one-execute-or-many-tools)
- [§5 Languages: Python, SQL, R, MATLAB](#5-languages-python-sql-r-matlab)
- [§6 Getting data back without drowning](#6-getting-data-back-without-drowning)
- [§7 Who draws the chart](#7-who-draws-the-chart)
- [§8 Grounding: schema, semantics, verified queries](#8-grounding-schema-semantics-verified-queries)
- [§9 Verification, and what "wrong" looks like](#9-verification-and-what-wrong-looks-like)
- [§10 Safety and permissions](#10-safety-and-permissions)
- [§11 MCP as a data transport, and the artifact question](#11-mcp-as-a-data-transport-and-the-artifact-question)
- [§12 What nobody has solved](#12-what-nobody-has-solved)

---

## 1. What the category actually is

[`agent-archetypes.md`](./agent-archetypes.md) sorts this collection's
coding agents into six archetypes on two axes (who drives the loop; how
fixed the role structure is). The data agents do not land in new
archetypes — they land in the *same* ones, which is the first useful
finding:

| Archetype | Coding example | Data example |
|---|---|---|
| 1 · interactive kitchen-sink assistant | Claude Code, Cursor | [marimo](./data-agents/marimo) `agent` mode, [btw](./data-agents/btw), [jupyter-mcp](./data-agents/jupyter-mcp) in an editor |
| 2 · task-to-completion solver | SWE-agent, OpenHands | [Data Formulator](./data-agents/data-formulator)'s analyst, [MetaGPT DI](./data-agents/metagpt-di) |
| 3 · minimalist scaffold | mini-swe-agent | [Open Interpreter](./data-agents/open-interpreter) `v0.4.2` |
| 4 · multi-role pipeline | agent teams | [LIDA](./data-agents/lida) (summarise→goal→generate→evaluate→repair) |
| 5 · review specialist | PR-review bots | LIDA's `VizEvaluator` |
| 6 · app/UI generator | Bolt, v0 | — |

What changes is not the loop shape but **what sits on the other end of
the tools**. Which is why the right way to think about a data mode in a
unified framework is *a different tool surface and a different set of
result contracts under the same orchestrator*, not a different agent.

Two pieces of ecological context before the mechanics, because they
affect how much of this is readable at all:

- **Open Interpreter — the archetypal "chat with your data by running
  code" project — is now a Rust coding agent.** `main` at `2885d0d`
  (2026-09-08) is a Codex-derived harness optimised for low-cost models.
  The Python code interpreter last shipped in `v0.4.2` (2024-10-24).
- **Positron Assistant left the open-source tree.** The Positron repo now
  contains only the call site
  (`positron.ai.generateAssistantPrompt(request)`); the extension that
  implements it is not in the OSS tree at `340c418`.

Both moved *away* from open data-analysis agents in the same window that
Microsoft Research shipped two (LIDA, Data Formulator) and Datalayer,
E2B, marimo and MathWorks shipped infrastructure. The centre of gravity
has moved from "an agent that does analysis" to "a substrate an agent can
do analysis on" — which is, conveniently, exactly the layer a framework
like Forge wants to consume.

---

## 2. The UX surfaces, and what each demands

Five distinct surfaces appear in the sources. They are not
interchangeable: each one makes a different promise to the user, and the
promise determines the tool surface.

### 2a. The notebook

*Sources: [jupyter-mcp](./data-agents/jupyter-mcp),
[marimo](./data-agents/marimo), [MetaGPT DI](./data-agents/metagpt-di).*

The agent writes cells into a document the user will read top-to-bottom
and re-run. Three consequences, all of which show up as prompt rules:

**The notebook must stay reproducible.** jupyter-mcp's `execute_code`
description forbids imports and assignments *"that affect subsequent
Notebook execution"* — not for safety, but because a notebook whose
state was established off-document is a lie. marimo makes the same point
structurally: the scratchpad discards top-level bindings.

**Repair is in-place.** marimo: *"If there are errors in cells you have
added, edit the existing cell. **Don't add new cells to correct
errors.**"* The natural LLM move — append a corrected version — produces
a document with three versions of the same cell and no indication which
one ran.

**Cells are addressed by identity.** jupyter-mcp uses nbformat 4.5 cell
ids and its error message teaches why: *"An index is a position in a
document somebody else is editing."* This is the stale-line-number
problem from [`agent-tool-implementations.md`](./agent-tool-implementations.md)
§4, in a document with a second concurrent writer.

marimo goes furthest because its reactive model forces it to. A cell is a
node in a DAG; edits are transactional (`async with cm.get_context()`,
queue on success, discard on raise); deletes are destructive and the
skill tells the agent to query `ctx.graph.descendants(cid)` first. That
**blast-radius query before a destructive operation** is the single most
portable idea in the notebook section, and nothing in this collection's
coding agents has an equivalent.

### 2b. The chart canvas

*Source: [Data Formulator](./data-agents/data-formulator).*

The user's artifact is a set of charts, not a document. The agent's
committing action is `visualize`, which takes code *and* a declarative
chart spec *and* field semantics; the harness renders. The whole design
follows from the model being unable to draw (§7).

What the canvas buys: re-styling without re-running (the STYLE/DATA
router), one house style enforced by the renderer, and charts that are
*queryable objects* rather than pictures — so a later "write a report"
step can embed chart `id`s rather than re-deriving them.

### 2c. Chat with a viewer

*Source: [Positron](./data-agents/positron)'s `data_explorer` protocol.*

Nobody in this collection actually ships this, but Positron publishes the
contract it would need: `get_schema`, `search_schema`,
`get_column_profiles` (batched, async, six named profile types),
`set_row_filters` (eleven enumerated filter types, no expressions),
`get_data_values`, and — the load-bearing one — `convert_to_code`, which
turns the current filter/sort state into pandas, polars, data.table or
dplyr.

`convert_to_code` is the answer to the thing that makes "chat with a
dashboard" hard: **direct manipulation produces no artifact**. A user who
filters a grid has expressed a precise predicate that the agent cannot
see and cannot reproduce. Converting the view to code makes the
interaction legible in both directions — the agent can read what the user
did, and the user can take what the agent did into a notebook.

The `variables.view` method completes it: "show me `df`" becomes a
protocol operation that promotes a variable into a grid, so an agent can
put a viewer in front of the user *without generating code*.

### 2d. The file-browser / uploads-and-outputs convention

*Source: the leaked Claude.ai tool corpus
([`leaked/anthropic/`](./leaked/anthropic)), and
[jupyter-mcp](./data-agents/jupyter-mcp)'s `list_files`.*

The simplest surface, and the most widely deployed. Three directories
with fixed meanings:

> 1. USER UPLOADS (files the user mentions): every file in context is
>    also on disk at `/mnt/user-data/uploads`. …
> 2. CLAUDE'S WORK: `/home/claude`. Create all new files here first. Users
>    can't see this directory; use it as a scratchpad.
> 3. FINAL OUTPUTS: `/mnt/user-data/outputs`. Copy completed files here;
>    it's how the user sees Claude's work. ONLY final deliverables.

plus `present_files` to surface them, and read-only mounts on uploads and
skills. The three-way split — *theirs (read-only) / mine (invisible) /
ours (published)* — is the filesystem version of Data Formulator's
inspection/action distinction and marimo's scratchpad/`cm` split. **Four
independent designs, one boundary**: work is invisible until the agent
explicitly publishes it.

jupyter-mcp's `list_files` adds the detail every implementation of this
needs and most forget: `max_depth` is bounded in the *schema*
(`ge=0, le=3`). A recursive listing of a data-science working directory
is a context bomb — `.ipynb_checkpoints`, virtualenvs, a partitioned
`data/` tree with 40,000 files — and the only reliable fix is to make the
unbounded request unexpressible.

### 2e. Inline widgets and artifacts

*Sources: [Vanna](./data-agents/vanna), [`librechat/`](./librechat), the
leaked Claude.ai Visualizer tool.*

The chat-native surface: the tool result carries a component the client
renders inline. Vanna's `ToolResult` is the clearest version —
`result_for_llm` (a string), `ui_component.rich_component` (a
`DataFrameComponent`: sortable, filterable, paginated, exportable),
`ui_component.simple_component` (a text fallback), and `metadata`. Four
projections of one call, produced together, consumed separately.

The leaked Claude.ai corpus shows the same split done as *separate
tools*: `present_files` for deliverables, and a Visualizer
(`visualize:read_me`, `visualize:show_widget`) that *"streams inline SVG
diagrams, illustrations, and HTML interactive widgets into the
conversation — not files"*, with a per-kind design module (`diagram`,
`mockup`, `interactive`, `chart`, `art`) loaded before generating. Same
progressive-disclosure mechanism as Data Formulator's `load_skill`,
applied to output rather than capability.

### 2f. What the surface choice actually determines

| | Notebook | Canvas | Viewer | Files | Widgets |
|---|---|---|---|---|---|
| Durable artifact | the `.ipynb`/`.py` | chart set | none (view state) | files on disk | the transcript |
| Agent's commit op | insert/edit cell | `visualize` | `set_*_filters` | copy to outputs | tool result |
| Needs persistent state? | **yes** | no | yes (the open dataset) | no | no |
| Who renders | the notebook front end | the harness | the grid | the client | the client |
| Reproducible by default | yes | yes (code + spec stored) | **no** — until `convert_to_code` | only if the code is kept | **no** |

The bottom row is the one to design against. A surface that produces
answers without producing the code that made them is a surface that
cannot be audited, and every source that takes the problem seriously has
a mechanism for it.

---

## 3. The fork in the road: persistent state

This is the decision everything else hangs off, and the sources split
cleanly in two.

**Stateful.** A long-lived kernel or session. Variables persist across
calls. Open Interpreter, jupyter-mcp, marimo, MetaGPT DI, MATLAB MCP,
btw's `run_r`.

**Stateless.** Each execution gets a fresh namespace; anything that must
survive is written to a file or returned as a value. Data Formulator,
smolagents' default, LIDA's per-goal `plot(data)`.

The prompts follow the mechanism, and they say *opposite* things:

> **Open Interpreter** (stateful): for *stateful* languages … **it's
> critical not to try to do everything in one code block.** You should try
> something, print information about it, then continue from there in tiny,
> informed steps.

> **Data Formulator** (stateless): each call runs in a fresh namespace —
> variables do NOT persist between calls, so **combine related steps into a
> single script**.

Both are right. A harness that changes one and not the other gets a model
writing ten-line probes that assume `df` survives — which fails silently,
because `NameError` looks like a coding mistake rather than a model
mismatch.

### 3a. What stateful buys, and what it costs

**Buys:** incremental exploration at the natural granularity of thought;
expensive loads done once; a notebook that is a real document; the
ability to hold an object (a trained model, an open connection, a 4 GB
frame) that has no serialisation.

**Costs:** the agent's context and the kernel's namespace diverge, and
*the agent cannot see the divergence*. This is the defining problem of
the stateful design, and there are exactly four answers in the sources:

| Answer | Source | Cost | Fails when |
|---|---|---|---|
| Harness introspects and injects every turn | marimo (`## Available variables from other cells:` — name, `value_type`, `preview_value`, private names filtered) | tokens per turn | the harness can't reach into the runtime |
| Model probes on demand | jupyter-mcp (`execute_code` with `print(x)`, `df.head()`) | a round-trip, when it remembers | the model doesn't remember |
| Harness prompts a second model call to *write* a probe cell, runs it, injects the output | MetaGPT DI's `CHECK_DATA_PROMPT` | an extra LLM call **and** an extra cell per task | the model prints the wrong things |
| Don't have the problem | Data Formulator | re-computation | the state is genuinely expensive |

MetaGPT's is the most expensive and least reliable — and the only one
that works when the harness *cannot* introspect the runtime, which is the
general case for a remote sandbox, a warehouse session, or a Spark
cluster. Its escape hatch is important: *"Return an empty string if you
think there is no important data to check."*

marimo's is the best when available, and its detail is worth copying:
**private (`_`-prefixed) names are filtered out**. The same rule the
dataflow graph uses for what is notebook-level decides what the model is
told about. The agent sees the public surface of the namespace.

### 3b. The scratchpad: a third position

marimo's `execute_code` runs in **a shallow copy of the kernel globals**.
Notebook variables are readable by name; new top-level bindings and
rebindings are discarded after the call. Persisting requires an explicit
transaction:

```python
async with cm.get_context() as ctx:
    cid = ctx.create_cell("x = df.head()")
    ctx.run_cell(cid)
```

> Each call queues an operation for marimo to apply when the context exits
> normally. **If the block raises, the queue is discarded.**

This is the cleanest answer in the collection to *how does an agent
explore a live environment without corrupting it*: **read at full
fidelity, write only through a transaction.** And the skill is honest
about the leak — *"In-place mutations to notebook-owned objects can
persist because those names still reference live objects"* — which
matters, because `df.drop(..., inplace=True)` inside a "read-only" probe
changes the user's data.

Set the four side by side and the convergence is striking:

| Harness | Ephemeral surface | Durable surface | Boundary enforced by |
|---|---|---|---|
| jupyter-mcp | `execute_code` | `insert_execute_code_cell` | **a prompt rule** |
| marimo | scratchpad | `cm.get_context()` | **the namespace** |
| Data Formulator | inspection tools | actions | **the tool partition + a cardinality guard** |
| Claude.ai container | `/home/claude` | `/mnt/user-data/outputs` + `present_files` | **the filesystem convention** |

Four teams, four products, one boundary: **probe freely and invisibly;
commit deliberately and visibly.** Two of the four enforce it with a
mechanism and two with a sentence, and the two with mechanisms are the
two that could.

---

## 4. One `execute` or many tools

### 4a. The convergent answer

Every source that has thought about it ships **both**, and the focused
tools are always justified by *cost*, never by capability.

Data Formulator states it outright: `inspect_source_data` is *"Cheaper
than `explore()` for basic data inspection"*. It does nothing
`execute_python_script` could not do. It exists because schema-and-samples
is the single most common operation and paying a code round-trip for it
every time is waste.

Postgres MCP Pro is the strongest case for focused tools, and its ratio is
the argument: **eight discovery/diagnosis tools and one execution tool**.
`list_schemas`, `list_objects`, `get_object_details`, `explain_query`,
`analyze_workload_indexes`, `analyze_query_indexes`, `analyze_db_health`,
`get_top_queries` — all read-only, all things an agent would otherwise do
by writing `information_schema` queries badly.

MATLAB MCP generalises it: ship `evaluate_matlab_code`, *and let the
deployment declare its own focused tools* over domain functions, with the
model-facing schema and the binding kept in separate sections of one
file:

```json
{
  "tools":      [ { "name": "greet_user", "description": "...", "inputSchema": {...} } ],
  "signatures": { "greet_user": { "function": "greet_user", "input": { "order": ["name", "age"] } } }
}
```

That split is the right shape for any framework: **the team that knows
the domain writes the tool schemas; the harness vendor ships the general
escape hatch.**

The rule that falls out, and it is testable:

> A focused tool earns its place when the general tool would need
> **more than one round-trip**, or would get it **wrong in a way the
> model can't detect**. Not when it would merely be tidier.

`inspect_source_data` passes on the first clause. `list_schemas` passes
on both. A `filter_dataframe` tool passes on neither, which is why nobody
ships one.

### 4b. What the general tool looks like

Four flavours, and the differences matter more than the similarities:

| | Open Interpreter | Data Formulator | marimo code mode | smolagents |
|---|---|---|---|---|
| Signature | `execute(language, code)` | `execute_python_script(purpose, code)` | `execute_code(code)` | code blob in the response |
| State | Jupyter kernel | fresh namespace | kernel scratchpad (shallow copy) | a `state` dict across steps |
| Sandbox | none (runs on your machine) | audit hook / Docker | none — it *is* the user's kernel | custom AST interpreter |
| Returns | console text + image blocks | `{'status', 'content': DataFrame}` | stdout/stderr + reactive cell output | printed output; `final_answer(x)` to terminate |
| Rich output | yes (MIME bundle) | no (the DataFrame *is* the output) | yes (+ `ctx.screenshot()`) | typed `AgentImage`/`AgentAudio` |

Data Formulator's `purpose` argument is the small idea worth stealing: a
**required** one-sentence description whose only consumer is the UI
progress feed. The script's output is invisible to the user; the intent
is not. It is the cheapest enforceable version of the "narrate before you
act" rule that marimo states as prose (*"You must always explain to the
user why you are using a tool before invoking it"*) — a schema field
cannot be skipped.

Open Interpreter's runtime-populated `language` enum is the other: the
model's choice set is exactly the set of backends installed on this
machine. Data Formulator does the same for `load_skill`'s `name`.
**Constrain enums at runtime from what actually exists** is nearly free
and prevents a whole class of wasted turn.

### 4c. Sandboxing, four ways

*A general `execute` tool is a sandbox question. The sources answer it at
four different levels, and the honest ones say which.*

**Nothing.** Open Interpreter runs on the user's machine, and the prompt
asserts consent (*"The user has given you full and complete permission"*).
btw's `run_r` runs in the global environment and its documentation says
so:

> the code is executed in the global environment and does not have any
> sandboxing or R code limitations applied … At this time, we do not
> recommend that you enable this tool in a publicly-available environment
> without strong safeguards in place.

btw's answer is to ship it **disabled by default**, behind four separate
opt-in paths. That is a defensible position — twenty-five introspection
tools on, one execution tool off — and it is the R ecosystem's answer to
the whole question.

**CPython audit hooks.** Data Formulator's `local_sandbox.py`: a
subprocess with `sys.addaudithook`, blocking writes, confining reads to
the workspace (via `os.path.realpath`, so symlinks can't walk out), and
blocking `subprocess.*` / `shutil.*` / `os.system` / `os.exec*` /
`os.fork` / `os.putenv`. Three techniques worth lifting:

- **Pre-import before arming.** scipy/sklearn need `dlopen`; pandas
  lazily imports `pyarrow.parquet` inside `read_parquet()`. Both are
  warmed into `sys.modules` *before* the hook goes on. This detail is the
  difference between a sandbox that ships and one that gets disabled.
- **Scrub the environment first**, on a name pattern
  (`KEY|SECRET|TOKEN|PASSWORD|CREDENTIAL|CONNECTION_STRING`), with a
  stated justification: *"Legitimate sandbox code (pandas/numpy
  transforms) never needs these."*
- **Block by prefix, with a documented exception.** `os.*` is not blocked
  wholesale because pandas needs `os.listdir`/`os.scandir`/`os.stat`; the
  dangerous members are enumerated. The comment explaining the omission
  is what stops someone "fixing" it later.

**A custom interpreter.** smolagents does not call `exec`. It walks the
AST itself, with `authorized_imports`, `MAX_OPERATIONS = 10_000_000`,
`MAX_WHILE_ITERATIONS = 1_000_000`, `MAX_EXECUTION_TIME_SECONDS = 30`, and
a 50,000-character print cap. Strongest isolation of the three, at the
cost of implementing a subset of Python — and the caps are the part
generalisable to any design: *an agent-written loop that does not
terminate is a normal event, not an exceptional one.*

**A container.** Data Formulator's `docker_sandbox.py`; E2B, Modal,
Daytona, CoreWeave as pluggable backends under jupyter-mcp. The real
answer for anything multi-tenant.

And the honesty marker: Data Formulator's third backend is named
`not_a_sandbox.py`. A file called `local_sandbox.py` and a file called
`unsafe_local.py` get chosen differently in a hurry.

Note that the *prompt-level* allowlist and the *enforcement-level* one
are deliberately not identical. Data Formulator's prompt bans matplotlib;
the audit hook does not. The ban on drawing is a product decision, not a
security one, and conflating them would make both harder to reason about.

### 4d. The focused tools that keep recurring

Across all thirteen sources, the tools that appear more than twice:

| Tool | Appears in | Why it survives |
|---|---|---|
| describe/profile a table | Data Formulator, btw, Positron, LIDA, marimo | the most common operation, and easy to do badly |
| list schemas / tables / files | Postgres MCP, jupyter-mcp, Data Formulator | discovery, and the place unbounded results come from |
| run SQL | Postgres MCP, Vanna, PandasAI (as an injected function) | see §5 |
| static check without executing | MATLAB MCP `check_matlab_code`, marimo's lint tool | cheaper than a failed run, and side-effect-free |
| explain / plan a query | Postgres MCP | the only *counterfactual* tool in the collection |
| load a skill / capability | Data Formulator, marimo, Claude.ai Visualizer | progressive disclosure |
| session lifecycle | MATLAB MCP, jupyter-mcp (`use_notebook`, `restart_notebook`) | stateful runtimes need explicit lifecycle |

The last row is easy to miss and is a real cost of the stateful design: if
state persists, *starting and ending* it become operations the agent has
to reason about. jupyter-mcp has `use_notebook` / `unuse_notebook` /
`restart_notebook`; MATLAB MCP has `start_matlab_session` /
`stop_matlab_session` / `list_available_matlabs`. Stateless harnesses have
none of these.

---

## 5. Languages: Python, SQL, R, MATLAB

### 5a. Python is the host, and it is not close

Every source uses Python as the language the agent writes, including the
two whose *subject* is another language (Vanna's agent writes SQL inside
a Python framework; PandasAI's generated code calls SQL). The exceptions
are btw (R, because it *is* an R package) and MATLAB MCP (MATLAB, because
it is a vendor bridge).

This is not a preference, it is a consequence: Python has the kernel
protocol, the dataframe libraries, and the MIME bundle. §4b's table shows
what rides on that — rich output, images, structured results — and
Open Interpreter shows what happens without it. Its Python backend gets a
real `jupyter_client` kernel; its R, Ruby, Shell, JavaScript, PowerShell,
AppleScript and Java backends get `SubprocessLanguage`, which rewrites
the model's code line by line:

```python
for i, line in enumerate(lines, 1):
    processed_lines.append(f'cat("##active_line{i}##\\n");{line}')
processed_code = f"""
tryCatch({{
{processed_code}
}}, error=function(e){{ cat("##execution_error##\\n", conditionMessage(e), "\\n"); }})
cat("##end_of_execution##\\n");
"""
```

It buys a progress cursor, an error channel and a completion sentinel. It
pays: line numbers in errors no longer match the model's source, a `cat`
in user code can forge a marker, `tryCatch` changes program semantics —
and **it can never return a plot**, because there is no channel for one.

**The rule: "can the agent speak language X?" is really "is there a
kernel for X?"** Where there is (Python, and R via IRkernel or via btw's
in-process tools), rich output is free. Where there isn't, you get text,
and a chart has to become a file path.

### 5b. SQL is reached *through* Python far more often than beside it

Four distinct answers in the sources:

| Approach | Sources | The tell |
|---|---|---|
| SQL as a first-class tool | Postgres MCP, Vanna | tool annotations, statement validation, access modes |
| SQL as a library call in the sandbox | Data Formulator (DuckDB), marimo (`mo.sql`) | "prefer plain pandas… only use DuckDB when the dataset is very large" |
| SQL as a pre-provided function injected into the code environment | PandasAI | `def execute_sql_query(sql_query: str) -> pd.DataFrame` declared in the prompt |
| SQL as a string inside a script the model writes end-to-end | Open Interpreter's Postgres profile | ten lines of prompt telling it to get the schema first |

The third is the tidiest and composes best: the result lands as a
DataFrame in the model's own namespace, so joining a query result to a
CSV is ordinary pandas rather than a tool-chaining problem. It is also
what Code Mode generalises — the pattern
[`deepseek-harness/`](./deepseek-harness) states as *"intermediate tool
results never enter the conversation"*.

The first is the right answer when the database is the *subject* rather
than a source: production, permissions, cost, and a schema too large to
paste. Postgres MCP's read-only enforcement is the reference
implementation (§10b).

Both camps state some version of the **push-down rule**:

> **PandasAI:** Use only relevant table for query and do aggregation,
> sorting, joins and grouby through sql query
>
> **Data Formulator:** Prefer plain pandas for most tasks — it's simpler
> and more readable. Only use DuckDB when the dataset is very large and you
> need efficient SQL aggregations, filtering, joins, or window functions.

Same rule, thresholds set differently — which is correct, because they
are describing different data sizes.

### 5c. R

Two live approaches, and they are complementary:

**btw** (Posit): ~26 tool families, all introspection, `run_r` disabled by
default. The philosophy is that an LLM needs *context about your R
environment* more than it needs to execute in it, and the tools reflect
that: describe environment, describe data frame, package help, vignettes,
NEWS, session info, installed packages, devtools, covr. Where it does
execute, the return is a typed list of `ellmer::Content` objects
capturing *"text output, plots, messages, warnings, and errors"* — the
rich return that Open Interpreter's R backend cannot produce, available
because the harness is written *in* R.

**Positron's comms**: language-neutral OpenRPC, generated into Python, R
and Rust. `convert_to_code` emits `pandas`, `polars`, `data.table` or
`dplyr` from the same view state, and `suggest_code_syntax` picks per
session. This is the correct architecture for a multi-language data
agent: **one protocol, one interaction model, the idiom chosen at the
edge.**

btw's data-frame tool also contains the best single piece of guidance in
the collection about what "show me the data" means (§6a).

### 5d. MATLAB

MathWorks ships an official MCP server (Go, Apache-2.0) with
`evaluate_matlab_code`, `run_matlab_file`, `run_matlab_test_file`,
`check_matlab_code` (Code Analyzer, read-only), `detect_matlab_toolboxes`,
plus multi-session lifecycle tools and a JSON-declared custom-tool
mechanism.

Three things transfer beyond MATLAB:

- **`detect_matlab_toolboxes` is capability discovery as a tool.**
  Functionality is licensed per toolbox, so what the model can write
  depends on this machine's licence. Rather than guessing, it asks. The
  Python equivalent — "which libraries are available" — is universally
  answered by a static allowlist in the prompt, which is a static answer
  to a dynamic question.
- **The self-referential warning.** *"Do not use `restoredefaultpath` as
  it will remove the MCP server functions from the path and break this
  tool's ability to communicate with MATLAB."* Every harness that injects
  itself into the runtime it controls has such a command; almost none
  name it.
- **The annotation discipline** (§10a).

And the limitation: the return is *"the command window output"*, i.e.
text. A MATLAB function that produces a figure has no channel. Same
asymmetry as Open Interpreter's R backend, same cause.

---

## 6. Getting data back without drowning

A repository fits in a context window if you are selective. **A table
never fits**, so every read is a projection and choosing it is the skill.

### 6a. The projections of a dataframe, and when each is right

btw is the only source that makes this a model-facing decision with
stated criteria:

> - `"skim"` is the most information-dense format … the same information
>   as `skimr::skim()` but formatted as a JSON object
> - To glimpse the data column-by-column, use `"glimpse"`. This is
>   particularly helpful … **when pairings of entries in individual rows
>   aren't particularly important**.
> - To just print out the data frame, use `print()`.
> - To get a json representation of the data, use `"json"` … particularly
>   helpful **when the pairings among entries in specific rows are
>   important to demonstrate**.

The distinction is exactly the right one and is almost never surfaced:

- **Column summaries** answer *what is in this table* — type,
  missingness, quantiles, top categories, a distribution sketch. Size is
  O(columns), independent of `nrow`. Right for almost every question.
- **Rows** answer *what does a record look like* — with co-occurrence
  between fields intact. Needed when the question is about relationships
  within a row, and almost never needed at volume.

What the others do:

| Source | Projection | Choice? |
|---|---|---|
| btw | `skim` / `glimpse` / `print` / `json`, `max_rows=5`, `max_cols=100` | **model's, with guidance** |
| Data Formulator | schema + field stats + sample rows | fixed |
| marimo | name, `value_type`, `preview_value` per variable; name/type/sample-values per column | fixed |
| LIDA | computed stats + LLM-annotated `semantic_type`; **never rows** | fixed |
| Positron | six named profile types, batched per column | **caller's, per column** |
| Vanna | 1,000 chars of CSV + a file ref + exact `row_count`/`columns` in metadata | fixed |

Positron's is the most precise (ask for `null_count` on forty columns and
nothing else); btw's is the best documented; Vanna's is the best shape for
an agent (§6c).

LIDA's two-stage summarisation is worth extracting on its own:
**deterministic statistics first, semantics second.** `dtype` normalised
to `number`/`boolean`/`date`/`category`/`string` (category by a
cardinality *ratio*, `nunique/len < 0.5`, not a fixed threshold), then a
model pass that adds `dataset_description`, per-field descriptions and a
one-word `semantic_type` (`company`, `city`, `zip code`, `longitude`…).
Stats are cheap and exact; semantics cost a call. Only the summary ever
reaches the downstream prompts.

### 6b. Truncation, and what the notice should say

Open Interpreter truncates to **the last** 2,800 characters. Tail, not
head — correct for a REPL, where the traceback and the final `print` are
at the end, and wrong for a file read. A harness with both needs both
policies, keyed on the tool.

Three details from `truncate_output` worth copying:

- **The notice names a recovery action**, not just the loss: *"You should
  try again and use `computer.ai.summarize(output)` over the output, or
  break it down into smaller steps."*
- **The notice is idempotent** — it strips a previous notice before
  adding one, so re-truncated content does not accumulate banners.
- **The paging offer is dead code, and the comment says why**: *"This
  won't work because truncated code is stored in interpreter.messages"* —
  the full output was never retained, so the offer to page back cannot be
  honoured. **Paging requires the harness to keep what it elided**, which
  is the entire argument for a ref-and-store design over truncate-in-place.

Vanna's notice goes one better and tells the model what *not* to do:

> (Results truncated to 1000 characters. **FOR LARGE RESULTS YOU DO NOT
> NEED TO SUMMARIZE THESE RESULTS OR PROVIDE OBSERVATIONS. THE NEXT STEP
> SHOULD BE A VISUALIZE_DATA CALL**)

A model handed 1,000 characters of CSV will narrate it; the narration is
worthless when the next step renders the same data as a table. Almost no
truncation notice in this collection does this.

### 6c. The preview-plus-handle pattern

Vanna's `RunSqlTool` is the reference implementation of the whole idea:

```python
file_id = str(uuid.uuid4())[:8]
filename = f"query_results_{file_id}.csv"
await self.file_system.write_file(filename, df.to_csv(index=False), context, overwrite=True)

results_preview = csv_content[:1000] + "\n(Results truncated…)"
result = f"{results_preview}\n\nResults saved to file: {filename}\n\n**IMPORTANT: FOR VISUALIZE_DATA USE FILENAME: {filename}**"

metadata = {"row_count": row_count, "columns": columns, "query_type": query_type,
            "results": results_data, "output_file": filename}
```

**The tool wrote the artifact.** The model asked for SQL and got back a
file it never created, at a name it never chose, plus enough of the
content to answer trivial questions without a second call, plus the exact
shape in metadata.

Why both halves are needed: a bare handle costs a round-trip for *"what
were the top three?"*; a bare preview cannot be chained. Together they
cover both, and the exact `row_count` in metadata means the harness knows
the result was 40,000 rows even though the model saw ten.

jupyter-mcp does the same at the protocol level (§11), and its comment is
the clearest statement of the principle anywhere in this collection:

> A tool result says an output exists, how big it is and what type it is.
> An agent that needs the bytes asks for them here; an agent that only
> needed to know the cell succeeded does not pay for them. A cell that
> printed a megabyte otherwise spends a megabyte of context every time
> anybody reads it.

### 6d. Typed returns

Three sources make the execution tool's return value *typed*, and this is
under-appreciated as a technique:

**Data Formulator**: `{'status': 'ok', 'content': <DataFrame>}` — the
success value is a live object, lifted out of the namespace by the
`output_variable` name the model declared.

**PandasAI**: the generated code must end with
`result = {"type": ..., "value": ...}`, where `type` is one of
`string`/`number`/`dataframe`/`plot`, and the caller can *pin* the
expected type per call. Violations get a **dedicated corrective
re-prompt** — one repair prompt per violated invariant, rather than a
generic "it failed":

> Fix the python code above and return the new python code but the result
> type should be: {{output_type}}

**E2B**: a `Result` record with a field per MIME type (`text`, `html`,
`markdown`, `svg`, `png`, `jpeg`, `pdf`, `latex`, `json`, `javascript`,
`data`, `chart`, `extra`), `formats()` to enumerate what's populated, and
`is_main_result` to distinguish the cell's value from its `display()`
calls. Notably, E2B **does not choose** — it hands the caller everything
and lets selection happen where the context is known. That is the right
split for a service: the sandbox does not know whether the model on the
other end has vision.

### 6e. Special values

Only Positron addresses it:

> Non-special values are returned formatted as strings. Special values such
> as `NULL`, `NA`, etc. are encoded with integer codes … NULL: 0, NA: 1,
> NaN: 2, NaT: 3, None: 4, +INF: 10, -INF: 11

Once every value is a formatted string, `"NA"` is ambiguous — a country
code, a missing value, or the literal string. Out-of-band codes remove
the ambiguity without a parallel null-mask array, and the gap between 4
and 10 leaves room to grow. Every harness that serialises a frame to CSV
or JSON for a model has this problem; none of the others address it. The
distinction matters diagnostically too: `NaN` vs `None` vs `NaT` says
*how* the data is broken.

---

## 7. Who draws the chart

The most consequential design decision in the category, and the sources
span the entire spectrum.

| Position | Model emits | Harness controls | Sources |
|---|---|---|---|
| **Free code** | a whole program | nothing | Open Interpreter, jupyter-mcp, marimo, MetaGPT DI |
| **Scaffold** | only the blanks | imports, entry point, title, return value, the call line | LIDA |
| **Declarative spec + data** | a DataFrame + encodings + field semantics | the entire rendering | Data Formulator |
| **Reversed figure** | (code, then) the harness deconstructs the result | the extraction | E2B `e2b/chart` |

### 7a. Free code

The default, and it works. The cost is that there is no house style, no
guarantee, and no way to re-style without re-running. Every harness in
this camp carries library-quirk rules in the prompt:

- Open Interpreter forces the `Agg` backend — *"Use Agg, which bubbles
  everything up as an image. Not perfect (I want interactive!) but it
  works."* An interactive backend opens a window on the user's machine
  and emits nothing to IOPub.
- marimo: *"For matplotlib: use `plt.gca()` as the last expression
  instead of `plt.show()`. For plotly: return the figure object directly.
  For altair: return the chart object directly."*

Both are the same fact — **in an agent context, a plot must become a
value, not a side effect** — stated once per library per harness.

### 7b. The scaffold (under-used)

LIDA returns a partial program and lets the model fill `<imports>` and
`<stub>`:

```python
import matplotlib.pyplot as plt
import pandas as pd
<imports>
# plan -
def plot(data: pd.DataFrame):
    <stub> # only modify this section
    plt.title('{goal.question}', wrap=True)
    return plt;

chart = plot(data) # data already contains the data to be plotted. Always include this line. No additional code beyond this line.
```

> Solve the task carefully by completing ONLY the `<imports>` AND `<stub>`
> section … **DO NOT WRITE ANY CODE TO LOAD THE DATA. The data is already
> loaded and available in the variable data.**

Five libraries get a scaffold, each with its own return contract. This
keeps the model's full expressive power inside `<stub>` while making the
*contract* unbreakable — signature, data variable, title, return value,
and the guarantee that nothing runs after `chart = plot(data)`. It is the
cheapest way to get a predictable artifact out of free-form code
generation, and it composes with an existing plotting library instead of
requiring a renderer.

### 7c. The declarative spec

Data Formulator's `visualize` takes `code` (producing a DataFrame),
`output_variable`, `chart` (`{chart_type, encodings, config}`),
`input_tables`, `field_metadata`, `field_display_names`, `title`,
`subtitle`, `display_instruction` — and the sandbox **bans matplotlib,
plotly and seaborn**. The model is structurally unable to produce a
picture.

What that buys is not mainly consistency, though it buys that. It buys
**a chart that is an object**: re-styleable without re-running, queryable
by a later step, and embeddable by id in a report. The STYLE/DATA router
exists precisely to exploit it — a filter, a colour change, a top-N or
an added trend line never touches the data pipeline.

It also forces a division-of-labour section that free-code harnesses
never have to write, and getting it wrong is silent:

> - **Regression**: trend line is automatic — do NOT compute regression
>   coefficients/predictions in Python.
> - **Histogram**: do NOT pre-bin in Python — pass the raw quantitative
>   field on `x`. **Pre-aggregating gives wrong bin widths.**
> - **ECDF Plot**: pass the RAW quantitative field on `x` — do NOT
>   pre-compute it.
> - **KPI Card**: The `value` column must already contain the final number
>   (aggregate upstream in the Python step).

Once the harness owns rendering, "who aggregates" stops being obvious and
must be specified per chart type. A pre-binned histogram renders happily
and is wrong.

And it puts **semantics on the wire**: `field_metadata` carries units,
index baselines, intrinsic domains, ordinal order, with one honesty
constraint the renderer cannot check — *"never invent a unit"* — and one
distinction that most chart code loses: *"Distinguish percentages from
percentage points and identifiers from quantities."*

### 7d. The reversed figure

E2B registers two custom Jupyter MIME types:

- **`e2b/data`** — a DataFrame as `{column: [values]}`, columnar, with
  `Timestamp` normalised to ISO strings.
- **`e2b/chart`** — a matplotlib `Figure` *deconstructed back into data*:
  `ChartType`, `title`, `x_label`/`y_label`, `x_unit`/`y_unit` (parsed
  out of the label with `r"\s\((.*?)\)|\[(.*?)\]"`), `x_ticks`,
  `x_tick_labels`, `x_scale` (`linear`/`log`), and `elements` carrying
  every plotted point or bar with its series label.

This is the idea the rest of the collection has been circling. The
Jupyter display protocol already has an open extension point — a MIME
bundle with arbitrary keys — and E2B uses it for types that are neither
text nor pixels.

Sending a chart to a model otherwise has two bad options: a PNG (a vision
model reads it approximately; *"what was the value in March?"* is a
guess) or the source code (which says what was *requested*, not what was
*rendered* — a filter that silently dropped rows is invisible).
`e2b/chart` is a third: the chart as a queryable object. *"Which series
peaks first"* becomes exact, cheap, and vision-free.

### 7e. Screenshot as the complement

marimo's `ctx.screenshot(cell_id)` drives headless Chromium against the
live notebook page (1440×1000, `deviceScaleFactor` 2.0, 90 s readiness
budget, warm browser reused) and returns a PNG data URL.

This is not an alternative to `e2b/chart`; it is the other half.
**`e2b/chart` tells you what the numbers were; the screenshot tells you
whether the legend collided.** The class of defect a spec cannot express
— overlapping labels, a colour scale illegible in dark mode, an axis that
overflows its container, a widget that didn't render — is only visible in
the render.

It is also the answer to LIDA's limitation. LIDA's `VizEvaluator` scores
the chart on six dimensions including "aesthetics" *from the source code*,
which cannot work for anything that depends on the actual data and the
actual renderer. Seven years later, marimo can look.

### 7f. The recommendation that falls out

For a framework that wants to cover the whole range:

- **Default to a declarative spec** where the harness can own a renderer.
  It is the only position that makes the chart an object, and the object
  is what a report, a re-style, and a dashboard all need.
- **Keep free code as the escape hatch**, with the library-quirk rules,
  because the chart type you didn't enumerate will come up.
- **Consider a scaffold for the escape hatch** rather than free code.
  It costs one template per library and removes an entire class of
  contract failure.
- **Where you must accept a picture, extract it as well** — E2B's
  reversal is ~400 lines and turns an opaque PNG into something a text
  model can answer questions about.
- **Screenshot for verification, not for transport.**

---

## 8. Grounding: schema, semantics, verified queries

The failure mode a data agent has that a coding agent does not: it can
write *syntactically valid, successfully-executing* code against columns
that mean something other than what it assumed.

Four grounding mechanisms in the sources, in increasing strength:

**1. Schema in context.** Everyone. marimo's
`## Available schema:` with sample values per column; Data Formulator's
`[CONTEXT]` with file paths; PandasAI's `<tables>` block.

The rules that accompany it are the interesting part, because they encode
the observed failures:

> **Data Formulator:** Never output placeholder identifiers like
> `your_table_name`, `your_column`, `your_condition`.
>
> **Open Interpreter's Postgres profile:** Get the schema of `{db_name}`
> before writing any other SQL commands … **Only use real column names.**
>
> **LIDA:** THE VISUALIZATION MUST REFERENCE THE EXACT COLUMN FIELDS FROM
> THE SUMMARY … Each goal MUST mention the exact fields from the dataset
> summary above *(stated three times in one paragraph)*.

A model that has not been given the schema writes `your_table_name`, and
the failure presents as a SQL error rather than as a missing-context
error.

**2. Semantic types.** LIDA's per-field one-word `semantic_type`
(`company`, `city`, `zip code`, `longitude`, `email`…); Data Formulator's
larger closed taxonomy (Temporal: `DateTime`/`Date`/`Year`/`YearMonth`/…;
Monetary: `Amount`/`Price`; Signed: `Profit`/`PercentageChange`/
`Sentiment`/`Correlation`; Geographic: `Latitude`/`Country`/`ZipCode`;
`ID`; `Rank`; `Score`; `Range`; `Unknown`) with selection guidance:

> Use **Amount** for summed monetary totals, **Price** for per-unit prices,
> **Profit** for values that can be negative. Use **Temperature** (not
> Quantity) for temperature — it has special diverging behavior. Use
> **Year** (not Number) for columns like "year" with values 2020, 2021.

Semantic types are how the renderer learns that `longitude` is not a
quantity to average, that `profit` needs a diverging colour scale
centred on zero, and that `year` is not a number to format with thousands
separators. They are cheap (one model pass over the schema) and they are
the difference between a chart that is right and a chart that is
defensible.

**3. Personas.** LIDA only, and no other source has it: goal generation
is parameterised by who is asking, defaulting to *"A highly skilled data
analyst who can come up with complex, insightful goals about data"*. The
same summary yields different goals for a CFO, a supply-chain analyst and
a journalist. It is a cheap, honest handle on *what question is worth
asking*, which is otherwise the least tractable part of autonomous
analysis.

**4. A semantic layer with verified queries.** No open source in this
folder, but it is the state of the art in the closed products
(Snowflake Cortex Analyst, Databricks Genie) and it is the thing this
folder most conspicuously lacks. The shape: a YAML model declaring
logical tables, columns, relationships and business terms on top of the
physical schema, plus a **verified query repository** — question/SQL
pairs curated by humans, retrieved and used to ground new questions, with
the requirement that verified SQL be written against the *logical* names.

That is retrieval-augmented generation with a human-curated corpus, and
the thing that makes it work is not the retrieval — it is that someone
had to write down what "active customer" means. Vanna 1.x was open-source
RAG over exactly this shape; Vanna 2.0 moved to a general agent framework
and the semantic layer became a deployment concern.

The framework consequence: **a data mode needs a place to put
organisation-specific meaning, and it is not the system prompt.** It is a
repo-resident, reviewable artifact — the same argument
[`agent-context-file-loading.md`](./agent-context-file-loading.md) makes
for `AGENTS.md`, applied to column semantics. btw's `btw.md` is the
closest open instance, and it carries tool configuration rather than data
semantics.

---

## 9. Verification, and what "wrong" looks like

A coding agent can run the tests. A data agent has three verification
signals, all weak, and the sources use them unevenly.

### 9a. It ran

The weakest. `df.groupby('region').revenue.mean()` succeeds whether or
not `region` is the column the question was about, whether or not nulls
were dropped silently, and whether or not the join fanned out.

The sources' answer is to make *specific* silent failures into rules,
which is why MetaGPT's task-type guidance is worth reading as a catalogue
of what actually goes wrong:

- **Leakage.** *"Do NOT make any changes to the label column"*; *"Do NOT
  use the label column to create features"*; *"Each feature engineering
  operation performed on the train set must also apply to the dev/test
  separately at the same time."* These are the errors that produce 0.99
  validation accuracy and no value.
- **State continuity.** *"Use the data from previous task result if
  exist, **do not mock or reload data yourself**"* — appears in three of
  six task types. A model that cannot see the kernel's namespace will
  helpfully re-read the CSV and discard four steps of preprocessing.
- **Aliasing.** *"Always copy the DataFrame before processing it"* — in
  two. An in-place mutation in step 4 changes what step 2 produced, and
  nothing says so.

All three are invisible in the output. That is what distinguishes them
from coding bugs.

### 9b. A second model looks at it

LIDA's `VizEvaluator`: six dimensions (bugs, transformation, compliance,
type, encoding, aesthetics), 1–10 with rationale, JSON out, then
`VizRepairer` regenerates under the same scaffold.

The two score-forcing clauses are the mechanism, and they are the same
move as requiring a severity label to be justified in
[`code-review-approaches.md`](./code-review-approaches.md):

> If ANY bug exists, the bug score MUST be less than 5.
>
> If a different visualization type is more appropriate, the score MUST be
> less than 5.

LLM judges regress to 7/10. Pinning specific findings to specific score
ranges is what makes a score usable as a gate rather than as decoration.

Structurally this is a review agent for charts — generate, evaluate,
repair, with the evaluator seeing the goal and the code but not the
author's reasoning. It is the specialist/validator split
[`agent-design/review.md`](./agent-design/review.md) uses, applied to a
visualization.

### 9c. Someone looks at the render

marimo's screenshot, and nothing else. §7e.

### 9d. What is missing

No source in this folder does any of:

- **Re-deriving a number by a second method** and comparing (the analyst's
  own basic discipline: does the total match the sum of the parts?).
- **Asserting on the shape**: row counts before and after a join, null
  counts after a merge, whether a groupby produced the expected
  cardinality. These are cheap, mechanical, and catch the most common
  silent failure in analysis — a join that fanned out or dropped rows.
- **Recording provenance** from an answer back to the query that produced
  it, in a form a human can re-run.

The third is the one a framework can just *do*: if every artifact carries
the code that produced it and the refs of its inputs, provenance is
free. The first two are prompt-level disciplines that nobody has written
down, and the closest analogue in this collection is
[`agent-self-verification.md`](./agent-self-verification.md)'s treatment
of "how does the agent know it's done".

---

## 10. Safety and permissions

### 10a. Annotations, used properly

MCP's four tool-annotation flags (`readOnlyHint`, `destructiveHint`,
`idempotentHint`, `openWorldHint`) are widely ignored. Two sources here
take them seriously and both are worth copying.

**jupyter-mcp** declares all four on all eighteen tools and the values are
*reasoned*: `move_cell` is destructive but closed-world; `clear_cell_output`
is destructive but idempotent; the three execution tools are the only
open-world ones — the flag tracking "can this reach the network", which is
what it is for.

**MATLAB MCP** factors the sixteen possible combinations into four named
constructors:

```go
// NewReadOnlyAnnotations …tools that perform inspection or query operations
//     without modifying state or executing user code.
// NewDestructiveAnnotations …tools that execute code, modify state, or
//     interact with external services.
// NewIdempotentWriteAnnotations …tools that write or overwrite local state
//     but produce the same result when called repeatedly …
// NewReadOnlyOpenWorldAnnotations …tools that query external services without
//     modifying any state (local or remote). Do not use this for tools that
//     mutate remote state: the read-only hint tells hosts they may skip user
//     confirmation, so misusing it lets writes through silently.
```

with all fields required (`bool`, not `*bool`, because MCP's SDK makes
"false" and "unspecified" different) and the type unexported so you cannot
hand-roll one. The final sentence is the whole argument for treating
annotations as a safety surface: **a wrong `readOnlyHint` doesn't mislead
a reader, it skips a confirmation.**

### 10b. Read-only SQL, done right and done wrong

**Done right** — Postgres MCP's `SafeSqlDriver` parses with `pglast`
(Postgres's own parser) and validates against an allowlist of *statement
node types* — `SelectStmt`, `ExplainStmt`, `VariableShowStmt`,
`VacuumStmt`, `DeclareCursorStmt`, `FetchStmt`, `ClosePortalStmt`,
`PrepareStmt`, `DeallocateStmt`, `CreateExtensionStmt` — **plus an
allowlist of functions**, because `SELECT pg_read_file('/etc/passwd')` is
a perfectly good `SelectStmt`. Plus a 30-second timeout, because
read-only is not the same as harmless on a shared warehouse.

**Done less right** — PandasAI's `is_sql_query_safe` matches
`[r"\bINSERT\b", r"\bUPDATE\b", r"\bDELETE\b", r"\bDROP\b", …]`. A
blocklist of keywords must anticipate every dangerous construct; an
allowlist of node types enumerates the safe ones, which is a much shorter
and much more stable list.

**And Vanna's dispatch is not a safety mechanism at all**:
`args.sql.strip().upper().split()[0]` decides whether to render rows or a
row count. Fine for shaping a response, wrong for anything else — a
leading comment or a `WITH … SELECT` defeats it. Worth being explicit
about which path a heuristic is on.

The third position, and it is defensible: **enumerate the operations
instead of accepting SQL.** Positron's `row_filter_type` enum has eleven
members and no expression anywhere, so there is nothing to inject into.
The cost is expressiveness; anything the vocabulary can't say has to
become code.

### 10c. Consent, asserted

btw's `btw_tool_ide_read_current_editor` takes a `consent` boolean that
the *model* sets, gating a read of the user's open editor — with the
weakness admitted in the same docstring:

> The tool definition includes language to induce LLMs to confirm with the
> user before calling the tool. **Not all models will follow these
> instructions.** Users can also include the string `@current_file` to
> induce the tool.

A model asserting that the user consented is a self-signed attestation,
not evidence. This is the consent-assertion problem
[`openclaw/`](./openclaw) surfaced, in a data tool. What btw has that most
don't is the honest annotation and a second, real path (`@current_file`,
typed by the user) so the mechanism degrades to a genuine signal when
someone uses it.

### 10d. Credentials

Two patterns ship side by side in Open Interpreter's profiles, and the
contrast is instructive:

- `llama31-database.py` interpolates the **DSN, including any password,
  into the system message** — so it is in every request, every log and
  any transcript.
- `snowpark.yml` teaches the model to read credentials **from the
  environment inside the executed code**.

Data Formulator goes further and scrubs the sandbox's environment before
accepting code, on a name pattern, with a stated justification. That is
the right default: the code that legitimately needs a secret is not the
code the model wrote.

---

## 11. MCP as a data transport, and the artifact question

[`agent-tool-result-transport.md`](./agent-tool-result-transport.md) §5
and §7 established the general picture: base64 must never reach the model
as text, and six artifact mechanisms exist across four groups. This
section adds what the data sources contribute, because they stress the
transport harder than anything read before.

### 11a. What MCP actually supports, checked

Confirmed against the specification (revision `2025-06-18`, re-read
2026-09-12) — a tool result's `content` may contain:

- `{"type": "text", "text": …}`
- `{"type": "image", "data": <base64>, "mimeType": …}`
- `{"type": "audio", "data": <base64>, "mimeType": …}`
- `{"type": "resource_link", "uri": …, "name": …, "description": …, "mimeType": …, "annotations": {...}}`
- `{"type": "resource", "resource": {"uri": …, "mimeType": …, "text": … | "blob": <base64>, "annotations": {...}}}`

plus `structuredContent` (a JSON object) validated against the tool's
optional `outputSchema`.

So: **binary is expressible** — as a base64 `blob` in an embedded
resource, or as `image`/`audio` — and the premise "MCP has no binaries"
is not quite right. But it is right in the way that matters. Base64 in a
tool result costs 2.5–3.6× the underlying bytes *if the client renders it
as text*, and §3f of the transport doc is the finding that **the server
cannot know whether it will**. A 40 MB parquet file as a base64 blob is
not a transport, it is an accident.

The right primitive is already there and is the one two of seven client
projections silently drop: **`resource_link`**.

### 11b. It already works, and jupyter-mcp is the proof

The user's idea — *an MCP tool creates the artifact directly (a binary, a
database table, a parquet file) and returns the ref plus metadata* — is
not speculative. jupyter-mcp ships it, inside plain MCP, with no
extensions:

```
notebook://{name}
notebook://{name}/cells/{cell_id}
notebook://{name}/cells/{cell_id}/outputs/{index}
```

Reading a cell returns its outputs **listed, not inlined**:

```json
{
  "id": "…", "index": 3, "cell_type": "code", "source": "…",
  "execution_count": 7,
  "outputs": [
    {"index": 0, "mimeType": "image/png",  "uri": "notebook://nb/cells/abc/outputs/0"},
    {"index": 1, "mimeType": "text/plain", "uri": "notebook://nb/cells/abc/outputs/1"}
  ]
}
```

Every element of the pattern is present:

| Element | jupyter-mcp's answer |
|---|---|
| The handle | a `notebook://` URI, resolved by `resources/read` |
| The metadata | `mimeType` per output, and a listing rather than a payload |
| Who mints it | the server — the model never names a URI it invented |
| Lifetime / freshness | `_meta["io.modelcontextprotocol/cache"]` with `ttlMs` and `cacheScope` (5 s for a notebook, 60 s for an output, `private` not `session`) |
| Who it's for | `annotations.audience` — outputs are `["assistant"]` only, because *"a person reads outputs in their notebook, where they are rendered, not through a URI"* |
| Change notification | `resources/subscribe` / `resources/unsubscribe` |

Two further details matter for the design question.

**`_meta` namespacing.** Protocol concerns go on the protocol's key
(`io.modelcontextprotocol/cache`); the server's own go under
`io.jupyter-mcp/`, because *"a bare `cell_id` would be a collision waiting
to happen."*

**The wire shape is built in exactly one file**, and the reason is the
best-argued paragraph on MCP transport in this collection:

> A server cannot know which of the two a client puts in front of the
> model, and the Core Primitives Working Group is redesigning that contract
> for exactly that reason. Content annotations (`audience`, `priority`) are
> in the same discussion, and may be deprecated outright if nobody adopts
> them. So the shape is built here and nowhere else. When the redesign
> lands, or annotations go, this file changes and the eighteen tools do not.

### 11c. What a *data* ref needs that a blob ref doesn't

This is the extension the data sources force, and it is the part the
existing artifact design does not yet have.

A file ref answers *where are the bytes*. A **table** ref must answer
more, because the consumer's next question is never "give me the bytes":

| Property | Why the model needs it |
|---|---|
| **Schema** — column names and types | to write the next query at all |
| **Row count** (exact) | to decide between "show me" and "aggregate first" |
| **A preview** — a handful of rows, or column summaries | to answer trivial questions without a round-trip (§6c) |
| **Physical format** — parquet / csv / a live table | to pick the reader, and to know whether it's cheap to re-scan |
| **Provenance** — the code/query that produced it, and its input refs | to re-run, to audit, and to explain (§9d) |
| **Partition or sort order**, where it exists | to avoid a full scan for a top-N |

And the operations on it should be **relational, not byte-range**.
`Read(ref, offset, limit)` is right for a log and wrong for a table: the
question is `SELECT … WHERE … GROUP BY`, and the natural implementation
is that the ref is *registerable as a table* in whatever engine the agent
is using. DuckDB reading a parquet file by path is the existence proof —
Data Formulator's sandbox and marimo's `mo.sql` both rely on exactly this,
and it is why parquet-on-a-path is a better artifact format than any
JSON envelope.

Which yields the concrete recommendation for the user's idea:

> **An MCP data tool should write its result to a store as parquet, return
> a `resource_link` whose `mimeType` names the format, and carry the
> schema, exact row count, preview and provenance in `structuredContent`
> against a declared `outputSchema`.**

That uses only specified MCP: `resource_link` for the handle,
`structuredContent` + `outputSchema` for the typed metadata (so clients
validate it), `annotations.audience` to say the bytes are for the
assistant and the preview is for both, and `_meta` on a namespaced key
for anything vendor-specific. Nothing needs extending. The one thing to
be careful about is the spec's own backwards-compatibility note — *"a tool
that returns structured content SHOULD also return the serialized JSON in
a TextContent block"* — which for a large preview means paying for it
twice; keep the preview small enough that this is acceptable, or accept
that older clients see less.

**The one genuinely missing piece** is negotiation: the server has no way
to learn that this client renders `resource_link` and that one drops it,
or that the model on the other end has vision. E2B's answer — return
*every* representation and let the caller choose — is the pragmatic
workaround and does not fit MCP's single-result model. Until that lands,
the defensive shape is jupyter-mcp's: **a `resource_link` plus a text
line that says what it is**, so a client that drops the link still leaves
the model something actionable.

### 11d. The MIME-type escape hatch

E2B's `e2b/data` and `e2b/chart` show that the *Jupyter* side of the
problem has an open extension point that nobody else is using. A harness
that controls its kernel can register a formatter for any type it likes —
including one whose payload is a **handle**:

```
app/vnd.<vendor>.table-ref+json  →  {"uri": "artifact://tbl_04d1", "schema": [...], "rows": 1840293}
```

A `DataFrame` that is the value of a cell would then emit, alongside
`text/plain` and `text/html`, a reference to a materialised parquet file
— *automatically, for every cell, with no cooperation from the model*.
That is the cleanest available route from "the agent computed something
big" to "the agent has a ref to something big", and as far as this pass
found, nobody has built it.

---

## 12. What nobody has solved

Recorded as open problems, not as gaps in any particular source.

**1. Shape assertions.** No harness checks row counts across a join,
null counts after a merge, or groupby cardinality against expectation.
These are cheap, mechanical, and catch the most common silent failure in
analysis. The nearest thing is MetaGPT's prose rules.

**2. Cost as a first-class concern.** Not one source here reasons about
what a query *costs*. Postgres MCP has `explain_query` and
`get_top_queries` — the ingredients — but no harness makes the agent look
before it runs, and nothing tracks spend across a session. For an agent
pointed at a cloud warehouse this is the difference between a tool and an
incident.

**3. Big data.** Everything here assumes the data fits on one machine.
The moment it is Spark, BigQuery or a lakehouse, "return a DataFrame"
stops being a contract and the ref has to be a table in the engine rather
than a file on disk. The ref design in §11c anticipates this; nothing in
the sources implements it.

**4. Incremental/streaming results.** `get_column_profiles` is async with
a `callback_id`, and jupyter-mcp streams execution progress. Nobody
streams *partial answers* — first 100 rows now, the rest if you want
them. MCP has no result pagination at all
([`agent-tool-result-transport.md`](./agent-tool-result-transport.md) §6).

**5. Provenance.** §9d. Nobody records the chain from answer to query to
inputs in a form a human can re-run. It is the cheapest thing on this
list to add and the most valuable for trust.

**6. Multi-user notebooks.** jupyter-mcp addresses the racing pointer
(cell ids, explicit `notebook_name`); marimo addresses the stale read
(*"another editor may change a cell between scratchpad calls"*). Nobody
addresses two agents, or an agent and a human, editing concurrently with
any guarantee.

**7. The semantic layer.** §8. Open source has schema; the closed
products have meaning. The gap is not technical, it is that someone has
to write it down — which makes it a repo-resident, reviewable artifact
problem, and therefore exactly the kind of thing this collection's
context-file work already knows how to think about.

---

## Where this goes

[`agent-design/data.md`](./agent-design/data.md) takes the transferable
parts into Forge: a data mode alongside coding and review, the
inspection/action split promoted to a design rule, table refs as a scheme
in the existing address space, and the chart-as-spec contract. It admits
items under the same rule the rest of the design uses — *an item earns a
place only if it changes a contract the design already has*.
