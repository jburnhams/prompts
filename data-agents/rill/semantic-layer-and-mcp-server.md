# Rill: the metrics layer and the MCP server

*Read from `rilldata/rill` at `516bc91` (2026-11-11). Paths are under
`runtime/` unless stated.*

## 1. Metrics views: the semantic layer

A **metrics view** is a YAML resource on top of one OLAP table (DuckDB,
ClickHouse, Druid and others), described by Rill's own developer
instructions (`ai/instructions/data/resources/metrics_view.md`) as
"what other business intelligence tools call a 'semantic layer' or
'metrics layer'". It declares:

| Part | What | Why it matters to an agent |
|---|---|---|
| `model:` | the one table it is built on | **no joins at query time**; the join, if any, was done upstream in a SQL model |
| `timeseries:` + `smallest_time_grain`, `first_day_of_week`, `first_month_of_year` | the primary time column and calendar | time ranges and grains are first-class query fields, not SQL |
| `dimensions:` | name, display name, description, column or expression, type | what can be grouped and filtered |
| `measures:` | name, display name, description, **aggregate expression**, `format_preset` or `format_d3`, `valid_percent_of_total`, optional `exact_expression` | the agent asks for `total_revenue` and never writes `SUM(revenue)`; formats travel with the number |
| `security:` | `access` (an expression over user attributes), `row_filter` (SQL templated with `{{ .user.* }}`), `exclude` (hide named fields under a condition) | the same policy applies to dashboards, APIs and every AI tool |
| `ai_instructions:` | free text per metrics view (inherited by derived views) | a place for meaning, alongside the project-wide `ai_instructions` in `rill.yaml` |
| `annotations:`, `rollups:`, `cache:`, `tags:` | overlays, pre-aggregated tables, caching, labels | not used by the AI tools read here |

`exact_expression` is a small idea with a prompt consequence. A measure
can default to a fast approximation (`approx_count_distinct`) with an
exact variant, and `query_metrics_view`'s description says: "Set
'exact: true' on such a measure only when the user explicitly asks for
exact, precise or reconciled numbers; exact queries are much slower.
Tell the user which precision was used."

**Derived metrics views** select a subset of a parent's dimensions and
measures, which is how one table is exposed at different grain or to
different audiences.

**Skills** are `SKILL.md` files in the project, parsed into catalog
resources (`parser/parse_skill.go`), with `description`,
`metrics_views` (scope), `agents` (`analyst`, `developer`) and
`always_apply`. A skill that fails reconciliation (for example, scoped
to a metrics view that does not exist) is skipped "so that the
validation actually keeps invalid instructions away from the agents".
A project skill replaces a built-in of the same name.

**Generating a metrics view** (`runtime/server/generate_metrics_view.go`,
needs `EditRepo`). A model is asked for "up to 10 suggested metrics"
from a table's columns and types: "valid SQL aggregation expressions
that use only the COUNT, SUM, MIN, MAX, and AVG functions. Do not use
any complex aggregations and do not use WHERE or FILTER". The model's
YAML supplies only measures (name, display name, expression,
description). The time dimension, dimensions, format preset
(`humanize`) and connector are filled in by code. Each measure is
validated against the database, and invalid ones are dropped, in up to
three passes. After a 30-second timeout or on error, a non-AI generator
writes `COUNT(*)` plus a `SUM` per float column. One defect: the
name-collision guard's condition is inverted
(`if _, ok := columns[measure.Name]; !ok { measure.Name += "_measure" }`),
so it renames measures that do *not* collide with a column, once per
validation pass.

This is the shape `../../agent-data-analysis.md` §8 attributed only to
closed products (Snowflake Cortex Analyst, Databricks Genie): logical
fields with business meaning over a physical table, written and
reviewed as code. What Rill does not have is the other half of that
section, a **verified-query repository** of human-curated
question/query pairs; skills are the nearest thing, as prose.

## 2. The query surface an analyst gets

An analyst never writes SQL. `query_sql` (raw SQL against a connector)
is gated by `checkDeveloperAccess` and is not on the analyst's list.
Every number comes from one tool, `query_metrics_view`, whose input is a
**structured query** (`metricsview.QueryJSONSchema`): measures
(optionally computed: `comparison_delta`, `comparison_ratio`,
`comparison_value`), dimensions (optionally `time_floor` at a grain),
`time_range` (absolute, or an expression such as
`"1M as of latest/D offset -1M"`), `comparison_time_range`, `where` (an
expression tree with `cond` / `op` / `exprs`, `name`, `val`), `sort`,
`limit`, `exact`.

The resolver (`runtime.Resolve` with `Resolver: "metrics"`) applies the
caller's claims, so row filters and field exclusions hold. Limits on AI
queries, from instance config (`drivers/registry.go` defaults):

| Setting | Default | Effect |
|---|---|---|
| `rill.ai.default_query_limit` | 25 rows | applied when the model sets no `limit` |
| `rill.ai.max_query_limit` | 250 rows | a larger `limit` is cut to this |
| `rill.ai.require_time_range` | true | a query with no time range is rejected |
| `rill.ai.max_time_range_days` | 0 (none) | caps the range; the error names the env var |
| `rill.ai.max_message_size_bytes` | 200 KiB | a tool call's args or result over this fails |
| (in code) | 2 min | per-query timeout |

When the system's limit cut the rows, the result carries a
`truncation_warning`: "The system truncated the result to 25 rows; to
fetch more rows, explicitly set a limit (max allowed limit: 250)". Rows
come back inline as `schema` + `data` arrays, so **query results do
enter the model's context**, capped at 250 rows.

Each result also carries:

- `resolved_time_range` and `resolved_comparison_time_range`: the
  absolute ranges a relative expression resolved to, recorded "for this
  tool call" so a later reader knows exactly which period was meant;
- `open_url`: a link to this tool call in the Rill UI, which replays the
  query into a dashboard. The tool description says "Always cite the
  source of quantitative claims by including 'open_url' as a markdown
  link", and the in-app analyst prompt makes it a requirement for every
  quantitative claim (§3 of [`agents-and-prompts.md`](./agents-and-prompts.md)).

Two hygiene notes on the description, which is long (six worked
examples): one example ends its range at `2025-05-31T23:59:59Z` right
after the rule that ranges are end-exclusive, and two examples are not
valid JSON (a trailing comma, a missing quote on `expression"`). Models
copy examples.

## 3. The MCP server

`ai/mcp.go`. One server per client connection, scoped to the session's
claims ("Using a separate MCP server for each client enables tailoring
the server's instructions and available tools to the end user's
claims"). Two endpoints serve it: the runtime's own (`/mcp`, one
project) and the **unified** Rill Cloud endpoint (`admin/server/mcp.go`,
`/v1/mcp`), which adds a `project` argument to every forwarded tool's
schema, strips it and forwards the call as plain JSON-RPC to that
project's runtime, deriving a per-project session ID with UUIDv5. The
unified server forwards only tools that do not need `EditRepo`, "which
is only granted for editable deployments, and a project's primary
deployment is never editable".

### Server instructions (verbatim)

```markdown
# Rill MCP Server
This server exposes APIs for querying **metrics views**, which represent Rill's metrics layer.

## Workflow Overview
1. **List metrics views:** Use "list_metrics_views" to discover available metrics views in the project.
2. **Get metrics view spec:** Use "get_metrics_view" to fetch a metrics view's specification. This is important to understand all the dimensions and measures in a metrics view.
3. **Query the summary:** Use "query_metrics_view_summary" to obtain the available time range for a metrics view and sample values with their data types for each dimension. This provides a richer context for understanding the data.
4. **Query the metrics:** Use "query_metrics_view" to run queries to get aggregated results.

In the workflow, do not proceed with the next step until the previous step has been completed. If the information from the previous step is already known (let's say for subsequent queries), you can skip it.
If a response contains an "ai_instructions" field, you should interpret it as additional instructions for how to behave in subsequent responses that relate to that tool call.

## Skills
Projects may define **skills**: instruction files that teach agents project-specific analysis or development practices, such as analysis playbooks and business glossaries:
- Use "list_skills" early in a session to discover the project's skills.
- Before doing work that a skill's description covers, use "load_skill" to fetch its full instructions and follow them.
- Load any skill marked "always_apply" up front and treat its instructions as always in effect.

## Project Development
If you have edit access, the server also exposes tools for inspecting and editing the project's source code, which consists of YAML and SQL files:
- **List files:** Use "list_files" to browse the files in the project.
- **Search files:** Use "search_files" to find files by name or content.
- **Read a file:** Use "read_file" to read the contents of a file.
- **Write a file:** Use "write_file" to create, update or delete a file. If the file declares a Rill resource, it returns the resource's status and any errors encountered after reconciliation.
```

Note the line "If a response contains an 'ai_instructions' field, you
should interpret it as additional instructions". That makes a field in a
tool **result** an instruction channel, by design, for the project
owner's text and the always-apply skills (`list_metrics_views` appends
them for external clients, up to a 32 KiB skills budget). It is a
trusted channel only because the project owner is the only writer;
nothing marks it as such to the host.

### Tools (`ai/ai.go` `NewRunner`)

Every tool has a `CheckAccess` against the session's claims and flags,
and the server registers only those that pass. Grouped:

| Group | Tools | Access |
|---|---|---|
| Agents (in-app only) | `router_agent`, `analyst_agent`, `developer_agent`, `feedback_agent` | Rill's own clients |
| Metrics | `list_metrics_views`, `get_metrics_view`, `query_metrics_view_summary`, `query_metrics_view`, `get_canvas` | `ReadObjects` / `ReadMetrics` |
| Charts | `create_chart`, `chart_data` (app-only) | `ReadMetrics` and the chart flags ([`charts-and-mcp-app.md`](./charts-and-mcp-app.md)) |
| Skills and memory | `list_skills`, `load_skill`, `update_memory` | `UseAI`; memory when enabled |
| External MCP | `search_external_tools` | loads tools of MCP servers the project connects to, by name or keyword ("stay available for the rest of the conversation") |
| Development | `develop_file`, `list_files`, `search_files`, `read_file`, `write_file`, `project_status`, `query_sql`, `list_tables`, `show_table`, `list_buckets`, `list_bucket_objects` | developer access; `EditRepo` for writes |
| Browser (in-app only) | `navigate`, `click_ui` | Rill's own client; `click_ui` only when the page exposed actions |

Every read tool carries the full annotation set (`readOnlyHint`,
`idempotentHint`, `destructiveHint: false`, `openWorldHint: false`) and
ChatGPT's `openai/toolInvocation/invoking` / `invoked` strings.
`get_metrics_view` returns "resource not found" when the policy denies
access, so a denied view is indistinguishable from a missing one.

### Three server details worth copying

- **Tolerant argument decoding, as a retry only.** Some clients send
  object or array arguments as JSON-encoded strings (the comment cites
  `anthropics/claude-code#25865`). A middleware waits for the SDK's
  schema validation to fail, then decodes string values where the
  schema expects an object or array, and retries once. "Calls that
  validate as-is are never rewritten", and it fails open to the normal
  error.
- **Client identity is recorded, not trusted.** The `initialize`
  client info updates the session's user agent and logs whether the
  client declared the UI extension, but a client name that would pass
  for Rill's own is prefixed `mcp/` (`MCPUserAgent`).
- **Errors the model can act on.** The unified server returns
  routing failures as tool results (`mcpToolErrorf`: "presented to the
  model as a result it can act on"), and `ai.InternalError` separates
  server faults from user errors so the middleware does not blame the
  model for a crash.

## 4. Where Rill's data overview comes from

Lens gives its model a "data overview, one line per source" in the
first message and `DescribeSource` / `Expand` for more. Rill's
equivalent is three calls the model makes itself, in an order the
server instructions fix: `list_metrics_views` (names, plus
`ai_instructions` and always-apply skills for external clients),
`get_metrics_view` (the full spec: fields, descriptions, formats,
`ai_instructions`), `query_metrics_view_summary` (the available time
range and "sample values and data types for each dimension", with the
note "All subsequent queries of the metrics view should be constrained
to this time range"). The in-app analyst gets the dashboard's metrics
views, time range, filters and selected fields pushed into its user
prompt instead ([`agents-and-prompts.md`](./agents-and-prompts.md) §2).
