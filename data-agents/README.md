# Data-analysis agents

A fifth category, alongside the top-level coding-agent folders,
[`leaked/`](../leaked), [`skills/`](../skills) and
[`github-pr-bots/`](../github-pr-bots): harnesses whose task is **answering
a question about data**, not editing a repository.

The question this folder is trying to answer for each source: **what does
the agent actually get to do with the data** — one general `execute(code)`
or a set of focused tools, which language, whether execution state
persists between calls, how results get back into context without
drowning it, and where the rendered output (a chart, a table, a report)
comes from.

The synthesis lives in
[`../agent-data-analysis.md`](../agent-data-analysis.md); what Forge takes
from it is in [`../agent-design/data.md`](../agent-design/data.md).

## Sources

| Folder | What it is | Licence | Read |
|---|---|---|---|
| [`open-interpreter/`](./open-interpreter) | The archetype: one `execute(language, code)` tool over ten language backends. Read at `v0.4.2`, the last Python release — **`main` is now a Rust coding agent**, which is itself a finding | AGPL-3.0 (`v0.4.2`) | 2026-09-12 |
| [`jupyter-mcp/`](./jupyter-mcp) | 18 MCP tools over a live Jupyter server. The most carefully built result/resource layer in the collection — cells and *individual outputs* are addressable resources | BSD-3-Clause | 2026-09-12 |
| [`data-formulator/`](./data-formulator) | Microsoft Research's chart-first analyst. Splits its surface into **inspection tools** and **committing actions**, and forbids the model from drawing anything | MIT | 2026-09-12 |
| [`marimo/`](./marimo) | A reactive notebook with four AI modes and a **code-mode** agent that drives the user's live kernel through a transactional private API — and can screenshot its own cell output | Apache-2.0 | 2026-09-12 |
| [`vanna/`](./vanna) | Text-to-SQL, rebuilt in 2.0 as an agent framework. Its `run_sql` tool is the clearest worked example of *write the result to a file, hand the model a ref plus a preview, hand the UI a component* | MIT | 2026-09-12 |
| [`metagpt-di/`](./metagpt-di) | MetaGPT's Data Interpreter: plan-then-execute in one Jupyter kernel, with per-task-type prompt fragments and a generated "check the data" cell that re-derives kernel state into context | MIT | 2026-09-12 |
| [`lida/`](./lida) | Microsoft's visualization pipeline: summarise → goals → **fill in a code scaffold** → self-evaluate on a six-dimension rubric → repair | MIT | 2026-09-12 |
| [`e2b/`](./e2b) | The sandbox behind several of the above. Notable for two custom Jupyter MIME types that carry a DataFrame and a *deconstructed matplotlib figure* as data | Apache-2.0 / MIT | 2026-09-12 |
| [`pandasai/`](./pandasai) | A typed result contract: generated code must assign `result = {"type": ..., "value": ...}`, and a wrong type gets a corrective re-prompt | MIT (core) | 2026-09-12 |
| [`postgres-mcp/`](./postgres-mcp) | A database MCP server where the access mode changes the **tool description and the MCP annotations**, not just the driver | MIT | 2026-09-12 |
| [`matlab-mcp/`](./matlab-mcp) | MathWorks' own MCP server. Session lifecycle as tools, a disciplined annotation taxonomy, and user-declared custom tools over MATLAB functions | Apache-2.0 | 2026-09-12 |
| [`btw/`](./btw) | Posit's R toolkit: introspection tools by default, `run_r` **off** by default, and four named projections of a data frame with stated selection criteria | MIT | 2026-09-12 |
| [`positron/`](./positron) | Not an agent — the **Data Explorer OpenRPC protocol**, i.e. what a data viewer exposes as a machine surface, including `convert_to_code` | Elastic-2.0 | 2026-09-12 |

## Read but not stored as folders

- **smolagents** (`huggingface/smolagents`, Apache-2.0, `30bb116`,
  2026-08-22) — CodeAct with a *custom AST-walking interpreter* rather
  than `exec`: `authorized_imports`, `MAX_OPERATIONS = 10_000_000`,
  `MAX_WHILE_ITERATIONS = 1_000_000`, a 30 s wall clock and a 50,000-char
  print cap. Covered in
  [`../agent-data-analysis.md`](../agent-data-analysis.md) §4c; the
  code-as-action idea itself is already in
  [`../codeact-hyperlight/`](../codeact-hyperlight).
- **Snowflake Cortex Analyst** and **Databricks Genie** — closed, but the
  *semantic-model YAML + verified-query repository* shape is documented
  and is the main thing the open sources here lack. §7b.
- **Jupyter AI** (`jupyterlab/jupyter-ai`, `c961b89`) — the repo is now a
  thin shell over submodules; nothing prompt-bearing was retrievable in
  this pass. Worth re-checking.
- **Positron Assistant** — the extension that implements
  `positron.ai.generateAssistantPrompt` is **no longer in the OSS
  repository**. Only the call site
  (`extensions/copilot/src/extension/prompts/node/base/positronAssistant.tsx`)
  remains. See [`positron/`](./positron).

## The one-line version

Every source here answers the same five questions, and the answers
cluster much more tightly than the product surfaces suggest:

1. **One tool or many?** Both. A general `execute` plus a small number of
   focused tools whose justification is always *cost*, never capability.
2. **Which language?** Python as the host, SQL reached *through* it far
   more often than beside it. R and MATLAB are served by session-attached
   servers, not by a second code tool.
3. **Does state persist?** This is the real fork in the road, and it is
   not a implementation detail — see §3.
4. **How do results come back?** A ref plus a shape, essentially
   everywhere that has thought about it.
5. **Who draws the chart?** Increasingly, not the model.
