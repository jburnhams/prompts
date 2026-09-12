# Data Formulator — the `core` skill

`py-src/data_formulator/analyst/skills/core/SKILL.md`, 314 lines,
always loaded. Excerpted to the parts that carry design decisions; the
chart-type reference (two tables, ~30 chart types) and the semantic-type
reference are summarised rather than reproduced.

## Frontmatter: capabilities are declared data

```yaml
---
name: core
description: >-
  The analyst's built-in capabilities: data-inspection tools and the
  always-available actions (visualize and ask_user).
when_to_use: Always loaded by default — this is the agent's baseline.
always_on: true
tools:
  - execute_python_script
  - inspect_source_data
actions:
  - visualize
  - ask_user
---
```

A skill declares **which tools and which actions it contributes**, and
`build_tools()` assembles the turn's surface from the union of loaded
skills. The taxonomy is in the data model, not just the prose.

## The stateless-execution rule

> - **execute_python_script(code)** — run a general-purpose Python script to
>   inspect data, compute stats, transform tables, or verify assumptions. Its
>   stdout is returned to you (use `print()`); the script is for *your* analysis
>   and its output is never shown to the user. pandas, numpy, duckdb, sklearn,
>   scipy are available. **Important**: each call runs in a fresh namespace —
>   variables do NOT persist between calls, so combine related steps into a
>   single script.
> - **inspect_source_data(table_names)** — get schema, stats, and sample rows for
>   source tables (cheaper than `execute_python_script` for basic inspection).

Two things here are the opposite of the notebook harnesses.

**No persistent namespace.** Every script starts fresh. The prompt draws
the exact opposite conclusion from Open Interpreter's: *combine related
steps into a single script*, where OI says *"it's critical not to try to
do everything in one code block"*. Both are correct for their execution
model. This is the fork in the road, and the guidance has to follow the
mechanism — a harness that changes one and not the other gets a model
that writes ten-line scripts assuming `df` survives.

**`inspect_source_data` justified purely by cost.** It does nothing
`execute_python_script` could not; the description says it is *cheaper*.
That is the honest form of the general-vs-focused trade: a focused tool
earns its place by saving the model a code round-trip on the single most
common operation, not by unlocking anything.

Also worth noting: the initial context already carries sample rows and
statistics, and the skill says so —

> The initial context already includes sample rows and statistics for each
> table. If the data is straightforward, go straight to the action without
> calling tools.

— which is the pre-loaded version of the same saving, and makes
`inspect_source_data` a top-up rather than a first move.

## `visualize`: the model does not draw

The action contract, abridged:

> Run code that produces a DataFrame and render it as a chart. You then
> observe the result and decide your next move.
>
> - `display_instruction` — ≤12 words; the question/hypothesis the chart
>   investigates (don't recap x/y/color — those are visible). …
> - `title` — a concise, neutral analytical heading naming the subject,
>   measure, and analytical lens … Prefer a stable description of the view
>   over a takeaway claim or narrated trend. Do not mention the chart type,
>   imply causality, or editorialize. …
> - `code` — Python producing a DataFrame assigned to `output_variable`.
> - `output_variable` — snake_case name the code assigns.
> - `chart` — `{chart_type, encodings:{x,y,…}, config:{}}` …
> - `input_tables` — workspace table names … that the code reads.
> - `field_metadata` — field → semantic annotation. Include units, index
>   baselines, intrinsic domains, and ordinal order when supported by the
>   data; **never invent a unit**. Distinguish percentages from percentage
>   points and identifiers from quantities.
> - `field_display_names` — field → concise human-readable label …

And the enforcement, from the execution rules:

> - **Allowed libraries:** pandas, numpy, duckdb, math, datetime, json,
>   statistics, collections, re, sklearn, scipy, random, itertools,
>   functools, operator, time
> - **Not allowed:** matplotlib, plotly, seaborn, requests, subprocess, os,
>   sys, io, or any other library not listed above.
> - File system access (open, write) and network access are also forbidden.

**The model is structurally unable to produce a picture.** It produces a
DataFrame plus a declarative chart spec; a Vega-Lite-class renderer on
the other side produces the picture. Everything follows from that:

- The chart is **re-styleable without re-running code** (hence the
  STYLE/DATA router).
- The chart is **inspectable as data** — `inspect_chart` exists as a
  skill-private tool for the report skill.
- There is **one house style**, enforced by the renderer, not by asking
  the model to remember a colour palette.
- `field_metadata` is where units, percentage-vs-percentage-points and
  ordinal orderings live — semantics the model knows and the renderer
  needs. *"never invent a unit"* is the only honesty constraint the
  renderer cannot check for itself.

The instruction to classify before choosing is stated as an internal
step:

> Silently classify the analytical intent before choosing a chart:
> comparison, trend, distribution, relationship, composition, deviation,
> ranking, uncertainty, or spatial pattern. Choose encodings and chart type
> from that intent and the data shape. Set ordering deliberately:
> chronological for time, semantic order for ordinal fields, and measure
> order for rankings.

## The chart-type reference, and its two tiers

~30 chart types in two tables, **Everyday** (10: scatter, regression, bar
family, grouped bar, line, area, histogram/density, boxplot, pie,
heatmap) and **Specialized** (20: connected scatter, ranged dot, violin,
strip, ECDF, bump, slope, streamgraph, range area, rose, pyramid, radar,
bar table, KPI card, candlestick, map, choropleth…). Each row carries its
legal `encodings`, its `config` keys, and a "when to use" hint. The
selection policy is stated:

> **Choosing a chart — prefer simple, escalate when it fits.** Reach for the
> **Everyday** set first … But when the data or question genuinely fits a
> **Specialized** type … prefer it — a well-matched specialized chart is more
> insightful than forcing a generic one. **Don't pick a specialized type for
> novelty; use it because its "when to use" condition is met.**

Then a "Critical chart rules" list, which is almost entirely composed of
**things the model must NOT compute in Python**, because the renderer
does them:

> - **Regression**: trend line is automatic — do NOT compute regression
>   coefficients/predictions in Python.
> - **Histogram**: do NOT pre-bin in Python — pass the raw quantitative
>   field on `x` and the chart bins automatically. Pre-aggregating gives
>   wrong bin widths.
> - **ECDF Plot**: pass the RAW quantitative field on `x` — the chart
>   computes the cumulative curve; do NOT pre-compute it.
> - **Bar Table**: Don't sort in Python — the template sorts.
> - **KPI Card**: The `value` column must already contain the final number
>   to display (aggregate upstream in the Python step).

This is the **division-of-labour section**, and it is the part a design
doc would forget. Once the harness owns rendering, "who aggregates" stops
being obvious and has to be specified per chart type — and getting it
wrong is silent (a pre-binned histogram renders, and is wrong).

The statistical guide extends the same split: regression → the chart;
forecasting → Python, distinguished with `strokeDash`; clustering →
Python, cluster id on `color`.

## `ask_user`: a bounded question widget

> - `questions` — 1–3 items, each something the user **acts on**: a choice
>   (`single_choice` with `options`) or an open question they type an answer
>   to (`free_text`). Put your reasoning, rationale, and context in your reply
>   text — **not** here. Never add a `questions` item that only states a
>   rationale or explanation with nothing for the user to answer or click.
> - each question: … `options` (plain-text choices, **at most 3** — just the
>   most likely answers; the user can always type a freeform reply, so don't
>   enumerate every case).
>
> This is **terminal**: the run pauses after it and resumes when the user
> replies.

Caps at every level (≤3 questions, ≤3 options each) and an explicit ban
on the failure mode — a "question" that is really a paragraph of
exposition with nothing to click. The `required` flag distinguishes
*the run depends on this* from *optional follow-up*, which is the
difference between a blocking question and a nudge.

## SQL and pandas in the same script

> - You can use BOTH DuckDB SQL and pandas operations in the same script
> - **Prefer plain pandas** for most tasks — it's simpler and more readable.
> - Only use DuckDB when the dataset is very large and you need efficient SQL
>   aggregations, filtering, joins, or window functions.
> - You can combine both: DuckDB for initial loading/filtering on large files,
>   then pandas for complex operations.

No SQL tool. SQL is a library call inside the Python sandbox, with a
stated preference order and a stated reason to escalate (size). The
DuckDB notes that follow are the accumulated scar tissue of running
model-written SQL — quote escaping, no Unicode escapes, explicit date
casts, and:

> If a table/column name contains non-ASCII characters (e.g. Chinese,
> Japanese, Korean, Cyrillic, etc.), spaces, or punctuation, you MUST wrap
> it in double quotes … Never output placeholder identifiers like
> your_table_name, your_column, your_condition.

The last clause is the one to remember: a model that has not been given
the schema writes `your_table_name`, and the failure looks like a SQL
error rather than a missing-context error.

## Files are addressed by path, and the path is authoritative

> Each table in [CONTEXT] has a **file path** (e.g. `student_exam.parquet`,
> `sales.csv`). Use EXACTLY that path to load data … **IMPORTANT:** Use the
> exact filename from the context — do NOT change the file extension or
> assume all files are parquet.

Parquet, CSV, JSON, XLSX and TXT each get their loader named. The
"don't assume parquet" warning is there because the context names tables
and the disk holds files, and a model that has seen ten parquet
workspaces will write `read_parquet` on the eleventh.
