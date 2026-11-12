# Hex's semantic layer, and how a query is bound to what the user sees

*Read 2026-11-12. Tags as in [`README.md`](./README.md).*

A word clash first. Hex's **semantic views** are curated subsets of a
semantic model. They are not MCP Apps views, and not views in the SQL
sense. This file says "semantic view" for Hex's and "rendered view" for
anything a user looks at.

## 1. Where models come from

"Semantic Models provide shared definitions for metrics, dimensions, and
relationships inside Hex", authored in Hex's Modeling Workbench or
imported from Cube, dbt MetricFlow, Snowflake Semantic Views,
Databricks Unity Catalog metric views or Apache Ossie. [docs]

- Authoring is "public beta", Admin or Manager only, organised as
  **semantic projects** tied to one data connection. [docs]
- Publishing opens a preview with **Changes** (with validation),
  **References** ("where the model is used in your workspace"), and test
  tabs to try the change in an Explore cell or a Thread **before
  publishing**. [docs]
- **History** keeps drafts, published versions "and agent-generated
  checkpoints". [docs]
- Sync from git is one-way, git into Hex. The CLI can `pull` a project's
  source files out (changelog 2026-08-18). The old sync action "publishes
  changes without the chance to first preview them" and is deprecated
  for the preview-then-publish flow. [docs]
- **View References** (2026-04-14) lists "every project and cell that
  uses" a model, for safe deprecation. [changelog]

## 2. The model format

[docs: "YAML specification", marked beta, "Minor changes may be made".]
One YAML document per resource, `type: model` or a view.

```yaml
id: users
type: model
base_sql_table: public.users
dimensions:
  - id: email
    type: string
    unique: true
measures:
  - id: total_users
    func: count
relations:
  - id: organizations
    type: many_to_one
    join_sql: org_id = ${organizations}.id
```

- **Source**: `base_sql_table` or `base_sql_query`.
- **Dimensions**: a column, `expr_sql`, or `expr_calc` (Hex's own
  formula language).
- **Measures**: `func` (`count`, `count_distinct`, `sum`, `avg`,
  `median`, `min`, `max`, `stddev`, `variance` and population variants)
  over `of`, with optional `filters` that are themselves boolean
  dimensions; or `func_sql` ("`SUM(price) * 0.9`"); or `func_calc`
  ("`revenue - costs`", composing other measures).
- **Semi-additive measures**: `semi_additive.over` a dimension with
  `pick: min | max` and optional `groupings`, for snapshot tables where
  "the total of all account balances is the sum of balances only on the
  latest date". Limited to one dimension.
- **Relations**: `many_to_one`, `one_to_many`, `one_to_one`, with
  `join_sql` using `${relation_id}`.
- **Visibility**: `public`, `internal`, `private`; hiding a model behind
  a view is the stated use.
- **Semantic views**: "Views are presentational only - they don't affect
  underlying query logic", selecting and renaming fields into groups for
  an audience.

Two properties matter for an agent [inference]:

1. **Cardinality is declared**, so fan-out on a `one_to_many` join is a
   known risk the query engine can account for rather than something the
   model has to notice. This is the trap at the top of
   `../../agent-design/eval.md` Suite 4's stratum T, removed by data
   rather than by prompt.
2. **Measures are closed under aggregation**: in queries, "Modeled
   measures are already aggregates, so expressions like
   `sum(total_revenue)` are invalid". A model cannot double-aggregate a
   governed measure, because the grammar won't let it.

## 3. Semantic queries in Hex 4.0: queries as files

Hex 4.0 (public beta, changelog 2026-11-10) makes projects "defined
entirely by code. The code lives in a file directory, which both the Hex
agent and external agents read from and write to". [docs] Semantic
queries are one kind of file in it. [docs: "Semantic querying in Hex 4.0
reference"]

The project's `hexdag.yaml` declares connections and semantic projects
by alias. "The Hex agent adds this declaration automatically when it
first queries a semantic project."

```yaml
databases:
  analytics:
    type: hex.dataconnection
    db_id: 2f1b665d-...
    name: Analytics
    connection_type: snowflake

semantic_projects:
  commerce:
    id: 0b6a3c1e-...
    database: analytics
```

A query lives in `dataflow/<name>.query.yml`, and "Each file produces a
table named after the file" (`monthly_revenue.query.yml` produces
`monthly_revenue`):

```yaml
semantic_project: commerce
base: orders
transforms:
  - aggregate:
      - measure: total_revenue
        alias: revenue
      - expr: "countdistinct(customer_id)"
        alias: customers
    group_by:
      - dimension: created_at
        time_unit: month
      - dimension: region
        model: customers
    where:
      - expr: "status = 'complete'"
```

- Three required keys: `semantic_project`, `base` (a model, or
  `{view: …, reference_by: name}`), `transforms`. "Unrecognized keys at
  any level cause validation errors."
- Transforms are ordered `aggregate` or `select` steps with `where`
  (before grouping, "even when it appears after `group_by`"),
  `having`, `order_by`, `limit`/`offset`, `detail`, `time_unit`,
  `binning`, and `lump` for "Top N with 'Other'" via window functions.
- Querying a semantic view uses display paths (``Sales.`Gross.Total` ``),
  and "Renaming a field or group changes its path".
- Expressions are Hex Calc, "not warehouse SQL". `{{name}}` references
  project parameters "as typed values"; "Changes to referenced values
  trigger query reruns".
- "Semantic queries cannot read other project tables. Combine results in
  subsequent SQL or Python steps."

When the agent can answer from a model, "it generates a semantic query,
which Hex translates into SQL and runs against your data warehouse."
[docs] The 4.0 roadmap marks "Semantic models in the agent" shipped on
October 20. [docs] Before 4.0, the agent answered from a model by
building an **Explore cell**; Hex's skill uses that as the test that a
semantic-first policy worked: "you know it worked when the agent answers
by building an **Explore cell** off the model (no SQL query shown)
rather than writing a SQL cell." [source]

The query file is a closed, validated, declarative spec with the
semantic project as its namespace. It is what
`../../agent-design/data.md` §2c's "three selectors, and one of them is
SQL" would look like with a fourth selector over governed measures.
[inference]

## 4. The binding chain: from a measure to a pixel

This is the question the MCP Apps pass left open: how does Hex tie what
a user sees to the query behind it? Pieced together from the 4.0 docs,
the Threads docs and the MCP docs.

```
semantic model ─┐
  (measure,     │   .query.yml          named table        chart / table     app element
   dimension,   ├─► (base, transforms) ─► (file name) ─────► cell ──────────► in a published
   relation)    │                                            ▲                 or generative app
warehouse table ┘   SQL cell ──────────► dataframe ──────────┘
                                                                      ▲
                     Inspect walks this right-to-left ────────────────┘
```

| Link | How it is bound | Tag |
|---|---|---|
| model → query | the query names `semantic_project` (an alias in `hexdag.yaml` resolving to a project ID and connection) and a `base` model or view | [docs] |
| query → table | file name; one file, one table | [docs] |
| SQL cell → dataframe | the cell's `outputDataframe` name; SQL cells may query other cells' results instead of a connection | [docs] |
| table → chart | a chart cell takes a dataframe or a semantic model directly as its source ("Create a Chart cell … then select a semantic model as the source") | [docs] |
| cells → each other | "The agent isn't just writing arbitrary code files, it specifies every dependency, the full DAG"; a change "only reruns what it affects. Everything else stays cached." | [blog] |
| chart → app element | the app is laid out from cells; 4.0 adds a Graph and a Lineage view over the cells | [docs] |
| app element → back | "Click any number or chart in an app and choose **Inspect** to see the logic behind it, which resources it used (like a semantic model), and how it connects to the rest of the analysis" | [changelog] |
| Thread answer → cells | "Selecting a cell reference in one of the agent's responses will take you directly to that cell in the Notebook" | [docs] |
| Thread chart → MCP client | `get_thread` "reports the cell ID of each chart"; `get_cell_image` renders it by draft or static ID | [docs] |

What follows from the chain [inference]:

- **The binding unit is a cell with a stable ID, not a query string and
  not a row set.** A chart is a reference to a cell, and the cell is a
  reference to a query or a dataframe, so there is always one more hop
  back to the definition. `list_cells` returns both a draft `id` and a
  `staticId`; the static ID is what survives edits.
- **The view never holds the data.** In Hex the app re-runs cells; in
  Claude the carousel shows cells from the Thread's project. The 24-hour
  widget expiry fits a view that fetches from Hex rather than carrying
  the data.
- **Provenance is structural, not cited.** Hex does not attach a
  citation to a number. A number is an output of a cell in a DAG, and
  Inspect is a graph walk. Lens's design instead makes the model *write*
  `claims[].refs` and has a gate check they resolve
  (`../../agent-design/data.md` §2f). Both work; Hex's cannot be
  forgotten by the model, and Lens's survives outside a Hex-like
  runtime.
- **Semantic view ≠ access control.** Views are "presentational only",
  and Governed mode "isn't a security control", so Hex never claims the
  semantic layer limits what can be read.

## 5. What Hex tells teams to do with it

From Hex's own skill, `context-architect.md` [source]:

> Build one when answers must be exact and the lighter assets aren't
> enough, when a metric needs one definition everywhere (revenue, churn,
> active users), or when the DB is complex with recurring joins. …
> Don't treat a model as a data-cleaning shortcut — say so honestly.

and the "semantic-first" stance, a policy written into `hex.md`:

> *"Always answer from the `<project>` semantic project first. Never
> hand-write SQL for a question the models can answer. If the models
> can't answer, say so explicitly, offer in-model alternatives, and only
> query raw source tables with your explicit approval."*

with the instruction to **slim the guides** once models exist, because
"duplication *tempts* the agent into raw SQL. A semantic-forward guide
becomes a router: which view answers this domain, the pre-built
measures available, and interpretation notes only." [source]

The approval clause is the interesting part. Hex's answer to "the model
might not cover this question" is neither "refuse" nor "fall back
silently", but **ask before leaving the governed layer**. [inference]
