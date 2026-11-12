# Rill: a semantic layer with an MCP server and interactive charts

- **Type**: an open-source BI tool (Go runtime, Svelte front end) whose
  **metrics layer** is exposed to agents through an MCP server, its own
  in-app analyst and developer agents, and an **MCP Apps** chart view.
  Read for what a semantic layer does to a data agent's tool surface,
  prompts and provenance, and for the most complete data app found in
  [`../../mcp-apps/`](../../mcp-apps) (on PR #44).
- **Vendor**: Rill Data · **Licence**: Apache-2.0 · **Source**:
  `github.com/rilldata/rill`
- **Read**: 2026-11-12, at `516bc91` (2026-11-11). The chart work is PR
  #10016 (`3f25106`, merged 2026-11-07) and #10089 (`80a505e`,
  2026-11-03). Also `microsoft/flint-chart` at `a794557` (2026-10-21),
  the chart compiler Rill uses. Details in [`../../sources.md`](../../sources.md),
  "Rill (read 2026-11-12)".
- **Prompted by**: the MCP Apps deep dive (2026-11-12), which named Rill
  the best data app it found; Jonathan asked for a separate thread on it.

## The files

| File | What |
|---|---|
| [`semantic-layer-and-mcp-server.md`](./semantic-layer-and-mcp-server.md) | Metrics views (measures, dimensions, security policies, `ai_instructions`, skills); the structured query an analyst gets instead of SQL and its limits; the MCP server's instructions verbatim, its tools and access gating, the unified multi-project endpoint, and three server details worth copying |
| [`charts-and-mcp-app.md`](./charts-and-mcp-app.md) | `create_chart` end to end: a Flint `chart_spec` plus a `data` binding, the `chartquery` planner and its budgets, what reaches the model and what reaches the view, the app-only `chart_data` tool, the widget and `ui/update-model-context`, the filter-narrowing rule, the `rill-charts` skill verbatim, Flint and eject to Vega-Lite |
| [`agents-and-prompts.md`](./agents-and-prompts.md) | The router and analyst agents (agents as tools; context as pre-invoked tool calls), the analysis prompt's rules on queries, charts and citations, a template bug that ships both branches of a conditional, memory, `click_ui`, and recorded evals |

Proposals for Lens and Forge, **none adopted**, are in
[`../../agent-design/proposals-rill-2026-11.md`](../../agent-design/proposals-rill-2026-11.md).

## What Rill does, in one paragraph

A person writes **metrics views** in YAML: measures as aggregate
expressions with formats, dimensions, a time column, and security
policies. Every agent reads data only through them. An analyst asks
`query_metrics_view` for named measures by named dimensions over a time
range with a structured filter, never SQL, and gets back at most 250
rows, the absolute time range used, and an `open_url` that replays the
call in Rill, which the prompt requires as a citation for every
number. To chart, the model calls `create_chart` with a **chart type and
channel bindings** (a Flint spec) and **the same kind of binding**
(metrics view, range, filter, grain). The server plans and runs the
queries within fixed budgets, derives every field's semantic type and
format from the metrics view, and returns a 20-row Markdown table for
the model and the full payload for an MCP Apps view. The view compiles
the spec to Vega-Lite in the browser, re-queries through an app-only
tool when the user changes grain, top-N or comparison, and tells the
model what it now shows.

## Rill against Lens

Lens ([`../../agent-design/lens-on-keel/`](../../agent-design/lens-on-keel))
answers data questions with read-only SQL over warehouse sources,
mints results as immutable `table://` refs, writes charts as Vega-Lite
specs citing those refs (`data.md` §2e), and reports every figure as a
claim citing the ref and SQL behind it (`answer.v1`, `data.md` §2f).

| Question | Lens today | Rill | Read |
|---|---|---|---|
| What does the model query? | SQL over described sources; it chooses joins on documented keys | a structured query over a metrics view; **no SQL, no joins** | Rill trades reach for correctness: the join and the metric definition were made once by a person |
| Where does meaning live? | the data overview and `DescribeSource`; a semantic layer deferred (`data.md` §4a: "the content, not the plumbing, is the hard part") | metrics view YAML (descriptions, formats, `ai_instructions`), project `ai_instructions`, scoped skills | Rill is the open-source instance `agent-data-analysis.md` §8 said did not exist; it has no verified-query repository |
| How much data enters context? | `table://` stub plus a capped preview; selectors to read more | 25 rows by default, 250 maximum, inline; charts send 20 rows as a fallback table | Lens's ref model is stricter; Rill relies on aggregation keeping results small |
| What is the citation? | a `table://` ref with `produced_by` (SQL, row counts) | the recorded tool call, as an `open_url` that replays it | the same idea: the claim cites the query, not a copy of its rows |
| Who computes? | SQL, in the run | the metrics layer (`comparison_delta`, `comparison_ratio`); "NEVER perform manual calculations" | Lens's rule "never state a number that did not come from a query" is the same rule without a layer to enforce it |
| What does a chart cite? | a `table://` snapshot | a **live binding** (metrics view, range, filter, grain) re-run on every view change | a snapshot is reproducible; a binding is interactive. Proposal 2 keeps both |
| Who writes the chart? | the model writes Vega-Lite; the write path validates columns and refuses embedded rows | the model writes a chart type and channel bindings; a compiler derives scales, formats, sort, stack, colours and layout from semantic types | proposal 1 |
| What stops a chart contradicting the text? | nothing specific | a chart's filter must narrow the filter of the data the findings came from, checked on the expression tree | proposal 3 |
| Who renders? | "the destination", which Lens does not have yet (PR #44 proposals 5–6) | the MCP Apps widget in Claude, ChatGPT, Cursor, VS Code; a link out elsewhere | proposal 4 refines PR #44's |
| Authority | the invoking user's delegation | the session's claims, through metrics-view security policies, for every tool including the view's re-queries | the same; Rill does not bind a view's calls to the chart that opened it |

## Corrections to `mcp-apps/data-analysis.md` §2

That section (on PR #44) summarised Rill from the PR thread. Reading
the code changes four points:

1. **Rows do reach the model.** The `content` of every external
   `create_chart` result is a Markdown table of the first 20 rows,
   whether or not the host renders views, because the server does not
   gate on the client's UI capability. The model writes no rows, but
   it reads up to 20. Design rule 1 there ("never the rows") is
   stricter than Rill.
2. **`chart_data` is not bound to the chart.** It accepts any
   `create_chart` arguments, so a view can query any metrics view the
   session can read. The authority is the session's, not "the call that
   opened the view" (design rule 4).
3. **No newest-instance election and no remount state.** Every mounted
   copy of a chart sends `ui/update-model-context` after its own
   refresh, and presentation edits are lost on remount.
4. **The skill arrives in a result.** `rill-charts` is appended to the
   `ai_instructions` field of `list_metrics_views`, which the server
   instructions tell the model to treat as instructions. It is not in a
   tool's description.

The rest stands: spec plus binding, app-only re-query, metered by the
`tool_call` metric with no rate limit, text fallback with a link out,
narrow CSP with the bundle inlined.

## Things to take, whatever is decided

- **A chart type plus channels is what a model writes reliably; the
  compiler owns the rest.** Rill's tool description removes axis
  settings from the properties the model may set, and tells it not to
  pass colours or formats at all.
- **Semantic types come from the data layer, not the model.** Formats,
  units and time grains already in the metrics view decide how a field
  is drawn; the model may override, rarely.
- **Budgets with a stated cut rule.** Temporal data is cut from the
  oldest end, a partial oldest bucket is dropped, data that fits only as
  zero rows fails, and an "Other" slice is added only when the measure
  adds up on the data.
- **A chart cannot drop the filter of the findings it illustrates**,
  unless the model says so explicitly.
- **The effective input is echoed.** Every result says which limits and
  grain were actually applied, so the next call (by the model or the
  view) starts from what was drawn, not from what was asked.
- **Context as pre-invoked tool calls.** What the harness already knows
  (the dashboard's metrics view, its summary, always-apply skills) is
  put in the transcript as calls the model would have made.
- **A content-hashed view URI with a catch-all template**, so a host
  holding an old tool list still gets a working view after a release.
- **Tolerant decoding only as a retry** after schema validation fails,
  for clients that stringify object arguments.

## Not read

- The developer agent (`developer_agent.go`, `develop_file.go`) and its
  1,500-line canvas and resource instructions, beyond headings: the
  coding side is covered better elsewhere in this collection.
- The metrics executor (`runtime/metricsview/executor/`) beyond the
  query-limit enforcement and `ValidateExpressionNarrows`'s call site.
- `memory.go` beyond the tool description.
- PR #10016's review thread: summarised in `mcp-apps/data-analysis.md`
  §2 from the PR page; the code was read instead.
