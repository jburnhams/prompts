# Rill: `create_chart`, Flint and the MCP Apps chart

*How a chart gets from a model's tool call to an interactive view in
Claude or ChatGPT, read from `rilldata/rill` at `516bc91`
(2026-11-11). Most of it landed in PR #10016 (`3f25106`, merged
2026-11-07); the dashboard-filter rule in #10089 (`80a505e`,
2026-11-03).*

## 1. One tool, two shapes

`create_chart` is registered once (`runtime/ai/create_chart.go`) and
advertises a different definition depending on who is calling:

| Caller | Definition | Arguments | Who queries | Result carries |
|---|---|---|---|---|
| Rill's own chat (`isRillUserAgent`, user agent starts with `rill`) | `Spec()` | Rill's in-app chart spec (`chart_type` + `spec`, schema `metricsview.ChartsJSONSchema`) | **the browser**, through the same component code dashboards use | widget mode, chart type, spec, a message. **No data** |
| An external MCP client | `MCPSpec()` | a **Flint** `chart_spec` plus a `data` binding (§2) | **the server**, before returning (§3) | the effective input, rows, field metadata, semantic types, theme, an `open_url` |

The in-app result "carries no data and never reaches the widget". The
external result has to carry data because "External clients cannot
query Rill, so run the chart's queries for them." The same session type
serves both; the user agent picks the branch, and `MCPUserAgent`
prefixes any external client whose name starts with `rill` with `mcp/`
so it cannot claim the in-app branch (a bug fixed in #10016: a client
named `rill-cli` got in-app tools and every request after `initialize`
returned 500).

## 2. What the model writes: a Flint spec and a binding

The external input schema (`flintChartsInputSchema`, `chart_flint.go`):

```json
{
  "chart_spec": {
    "chartType": "Bar Chart",
    "title": "Bids by advertiser",
    "encodings": {
      "x": {"field": "advertiser_name", "limit": 10, "sortBy": "y", "sortOrder": "descending"},
      "y": "total_bids",
      "color": "device_os"
    },
    "chartProperties": {"cornerRadius": 2}
  },
  "data": {
    "metrics_view": "bids_metrics",
    "time_range": {"start": "2024-01-01T00:00:00Z", "end": "2024-02-01T00:00:00Z"},
    "time_grain": "TIME_GRAIN_DAY"
  }
}
```

- `chartType` is an **enum of 32 names** from an embedded catalog
  (`chartquery/flint_catalog.json`, generated from the installed
  `flint-chart` 0.4.1). Upstream Flint has 52 types and is at 1.0
  (2026-10-19); Rill takes the subset it can express over a metrics view.
- `encodings` maps a **channel** to a field name, an object
  (`field`, `sortBy`, `sortOrder`, `limit`, `type`, `aggregate`,
  `scheme`) or an array. A `detail` channel sets the row grain without
  being drawn, which is how scatter plots, histograms and box plots get
  one row per observation from an aggregating layer.
- `data` is the **binding**: `metrics_view` and `time_range` required;
  `comparison_time_range`, `where` (the same expression tree as
  `query_metrics_view`) and `time_grain` optional. Its description ends
  "Rill runs the query; never pass rows."
- `semantic_types` is an optional override; normally Rill derives them.

The tool description is generated from the catalog: one line per chart
type listing its channels, a hand-written note for each (`flintChartNotes`, 32 entries;
e.g. "Grouped Bar Chart: side-by-side bars: the
clustering dimension goes on group, not on color"), and the tunable
`chartProperties` keys **minus the axis settings Rill derives**
(`independentYAxis`, `logScale_*`, `includeZero_*`, `xAxisType`,
`yAxisType` are filtered out in `propertyKeys`). Its opening paragraph:

> Query the data with query_metrics_view first, then describe the chart:
> the chart type and which field goes on which channel. Rill runs the
> query, derives scales, axes, number formats, sorting, stacking, colors
> and layout, and returns the rows. Do not pass colors, formats or axis
> settings, and reference only measures, dimensions and the time
> dimension of the metrics view.

The schema also drops Rill's own in-app `$defs` (`ChartSpec`,
`FieldConfig`) because "every byte of the schema is sent with each tool
list".

**Validation** (`parseFlintChartRequest` → `chartquery.ParseFlintSpec`)
happens against the metrics view **the caller can see** (security
policy applied in `loadMetricsView`), with each field classified as
measure, dimension or time. Time includes the time dimension, any
`TIME` dimension, and dimensions whose data type is `DATE` or
`TIMESTAMP` ("the metrics view types a date column as categorical
unless it is the time dimension, but a chart still draws it as time").
#10016's last commit lists what is refused: comparisons the widget
cannot draw, a measure on `x` of time and series charts, partial
comparison ranges, a `where` without `cond`, and a `sortBy` that names
no bound field.

## 3. The query planner: `chartquery`

`runtime/ai/chartquery` is a pure package: it turns a parsed Flint spec
into metrics-view queries and runs them through a caller-supplied
`Runner`, which the AI layer implements on top of the metrics resolver
**with the session's claims** (`metricsQueryRunner`). The plan
(`build.go`):

1. a **top-N pre-query per dimension** on an axis, series or facet
   channel, which selects the values and their order;
2. a **main query** grouped by every bound dimension (time floored to
   the grain), filtered to the selected values;
3. for pie and donut charts, a **total** query and an **"Other"** query
   for the values the top-N cut.

Budgets, with the reason in the code:

| Constant | Value | Why |
|---|---|---|
| `MaxNominalValues` | 50 | values of a dimension on an axis |
| `MaxColorValues` | 20 | on a series channel (color, group, shape, strokeDash) |
| `MaxFacetValues` | 8 | on a facet (column, row) |
| defaults | 20 axis, 10 series, 6 facet, 10 polar | "Small multiples stay small, and so does the angular axis of a polar chart" |
| `MaxRows` | 1,500 | main query |
| `MaxDataBytes` | 100 KiB | rows plus domain values; "Claude writes one over about 150,000 characters to a file, which the widget never receives" |
| query timeout | 2 min | across all of a chart's queries |

Three rules in `execute.go` are worth copying exactly:

- **Temporal charts are queried newest first**, so the row cap and byte
  budget drop the *oldest* buckets; then "the oldest bucket may be
  partial (a time series with a color split has several rows per
  bucket), so it is dropped unless it is the only one", and rows are
  returned ascending. `rows_truncated` tells the renderer the time axis
  is incomplete at the start.
- **Data that does not fit even as one row fails the chart**: "no cut
  makes it fit, and a chart without rows would misrepresent the data."
  The error tells the model to bind dimensions with shorter values or
  lower their limits.
- **An "Other" slice only when the measure adds up**, checked on the
  data: the value over the cut values must equal total minus shown
  slices within a relative 1e-6. "A sum or a count does; an average, a
  ratio or a distinct count generally does not, and a remainder of it
  would size a meaningless slice." The check runs on the data "since
  the metrics view does not declare which measures add up."

Every truncation produces one `truncation_warning` sentence: "The chart
data is incomplete: … To see the complete picture, …" with a remedy.

**Semantic types are derived, not written** (`chart_semantics.go`, a Go
port of `web-common/.../flint/semantic-types.ts`; "keep the two in
sync"). A time field takes `Year`, `YearQuarter`, `YearMonth`,
`YearWeek` or `Date` from the grain, `DateTime` below a day. A measure
takes `Amount`, `Percentage`, `Duration`, `Count` or `Number` from its
format preset, d3 format and type (integers lean to `Count`). Anything
else is `Category`. The time field is displayed as "Time". Comparison
values are `<measure>_prev`, typed like the measure and labelled
"(previous period)". "Only the strings in Flint's own registry do
anything — anything else silently degrades to nominal/plain", so a unit
test asserts every emitted value is registered.

## 4. The result: what the model sees and what the view sees

`CreateChartResult` (external branch):

| Part | Contents |
|---|---|
| `content` (text) | `chartMarkdown`: `**<type>: <title>** (<start> to <end>[, vs …])`, a Markdown table of **the first 20 rows** (cells capped at 100 runes), "_N of M rows shown_", the truncation warning, and "Open the interactive chart in Rill: <url>" |
| `structuredContent` | `widget: "chart"`, `chart_type`, `input` (the **effective** input: the spec with the top-N limits actually applied filled in per channel, the data block with the resolved grain, the caller's `semantic_types`), `title`, `metrics_view` (name, display name, time dimension, smallest grain), `data` (all rows, keyed by field, `[]` when empty so "a renderer can tell an empty chart from a result without data"), `fields` (kind, display name, description, type, format preset, d3 format and locale, `lower_is_better`), `semantic_types`, `field_display_names`, `domain_values`, `totals`, resolved time ranges, truncation flags, `theme` (the project's theme spec), `open_url` |

The `content` is the same whether or not the host renders views: the
server does not gate on the client's UI capability (§6). **So up to 20
rows reach the model on every host**, as a fallback table. That is a
deliberate trade (a text-only host still gets an answer) and it is less
than `query_metrics_view`'s default of 25 rows, which the model will
usually have run first anyway (the analysis prompt says "create a chart
after running query_metrics_view").

The title is generated when the model gives none (`flintTitle`):
"<measures> over Time", "<measures> by <dimension>", "… split by
<series>", or "<x> vs <y>" for two measures on the axes.

`open_url` is `<frontend>/-/ai/<session>/message/<call>/-/open`: a link
to **the recorded tool call**, which the Rill UI replays into an Explore
dashboard ("'Open in Rill' maps Flint-shaped calls into an Explore").
The citation is the call, not a copy of the data.

## 5. `chart_data`: the app-only re-query tool

`runtime/ai/chart_data.go`. Called by the widget when the user changes
grain, top-N or comparison:

- `_meta.ui.visibility: ["app"]`, so MCP Apps hosts hide it from the
  model. It is **only advertised when the widget is served**, by both
  the runtime endpoint and the unified admin endpoint.
- The input schema is deliberately minimal (three `object` properties
  described "As in create_chart"), "since hosts without MCP Apps list
  the tool to the model, which should not call it, and every byte of a
  tool list is sent with each request." Its description says "not meant
  to be called directly: use create_chart to show a chart."
- It takes **the arguments of a `create_chart` call**, validated the
  same way, and returns the data section plus the effective input.
  Authority is the session's claims: nothing binds a `chart_data` call
  to the chart that opened the view, so a view could ask for any metrics
  view the session can read. Read-only, same budgets.
- Its `content` is one line ("Chart data: N rows." plus any truncation
  warning), replacing the SDK default that "repeats all of
  structuredContent".
- Calls are **not persisted** in the AI session ("widget plumbing rather
  than conversation"; a sessionless call creates no session), but **are
  counted in the `tool_call` metric**, the fix for the reviewer's
  unmetered-query objection. No rate limit was added.

## 6. The widget and the MCP Apps plumbing

Server side, `runtime/ai/mcpapp/` (its README is the best single
document on the feature):

- **Capability**: `extensions["io.modelcontextprotocol/ui"] =
  {"mimeTypes": ["text/html;profile=mcp-app"]}` in the server's
  capabilities whenever the widget is served. "The server does not gate
  on it because the stateless transport does not carry the client's
  capabilities on later requests, and the extension is harmless to
  hosts that ignore it." It does record, per `initialize`, the client's
  name, version, protocol version and whether it declared the UI
  extension, as an activity event.
- **Resource**: one self-contained HTML file at
  `ui://rill/widget/<first 12 hex of sha256>.html`. Hosts cache by URI,
  so a new build gets a new URI; **a resource template also serves the
  current bundle under any `ui://rill/widget/*.html`**, because hosts
  keep the old tool list and request the old URI after a release.
- **CSP**: no `connectDomains`, no `frameDomains`; the only external
  origin is `https://assets.claude.ai` in `resourceDomains`, for the
  host's font. Everything is inlined (`vite-plugin-singlefile`); the
  build fails over a 650 KiB gzip budget (`scripts/check-size.mjs`), "comfortably below Claude's tool-result limits and mobile WebView comfort".
- **Protocols**: `2026-07-28` (no initialize handshake) and four older
  revisions, on `modelcontextprotocol/go-sdk` v1.8.0. ChatGPT's
  `openai/*` `_meta` keys are added beside the standard ones.
- **No tokens in the result or the widget**; "data flows only through
  the host's MCP bridge."

Client side, `web-mcp-app/` (Svelte 5, `@modelcontextprotocol/ext-apps`
^2.0.3, `flint-chart` 0.4.1, Vega):

- The widget **compiles the Flint spec in the browser** with the shared
  `web-common/src/features/custom-viz/flint/compile.ts`, the same
  compiler Rill's canvas custom charts use, and renders the Vega-Lite it
  produces with Rill's theme and measure formatters. "Flint is a
  compiler, not a renderer."
- **Data controls** (grain, top-N, comparison) go to `chart_data`,
  debounced, with a sequence number so stale responses are dropped
  (`requestSeq`). A refresh that would produce an empty or failed chart
  keeps the previous data and shows a notice instead.
- **Presentation controls** (chart type within a compatible set, layout,
  curve) are recompiled locally with no call. Fullscreen only.
- After each settled change it calls `updateModelContext` with one
  sentence (`describeView`, `lib/controls.ts`), marked
  "text for the model, not shown to the user":

  ```
  Chart now shows ${title}: ${chartType} with ${channel = field, …}; time grain ${grain}, top ${n} values, comparison ${on|off}, ${time range}.
  ```

  There is **no newest-instance election**: every mounted copy of a
  chart can send this after its own refresh. There is also no state
  persistence: presentation edits are lost on remount.
- "Open in Rill" is `ui/open-link` to `open_url`.
- A harness page (`npm run harness`) and Playwright tests drive the
  widget without a host.

**Gating (final shape).** `chat_charts` turns charts on in every chat,
Rill's own included; `mcp_charts` turns them off for external clients
alone. Together they enable `create_chart` for external clients,
`chart_data`, the widget and the `rill-charts` skill. The unified Rill
Cloud endpoint (`admin/server/mcp.go`) cannot evaluate per-project
flags, so it serves the widget unconditionally and the runtime rejects
`create_chart` for projects with charts off. #10016's history shows
three earlier flags (`mcp_apps`, an `mcp_apps_enabled` annotation,
`RILL_ADMIN_MCP_APPS_ENABLED`) collapsed into these, which was one of
the reviewer's objections.

## 7. A chart must keep the filters of what it illustrates

From #10089 (`checkDashboardFilter`, in-app branch). When the analyst
is working from a dashboard the user is viewing, a chart's `where`
**must narrow the dashboard's filter**
(`metricsview.ValidateExpressionNarrows`), or the call fails with:

> the chart has no 'where' filter, but the dashboard the user is viewing
> filters "…" by: <SQL>. Charts must apply the same filters as the data
> they visualize. Keep the dashboard's filters in the chart's 'where'
> (narrowing them further is fine), or set 'where' to
> {"cond":{"op":"and","exprs":[]}} to chart unfiltered data on purpose

The reason, in the comment: "The chart is rendered to the user as-is, so
a dropped filter makes it contradict the findings, which are based on
queries of the filtered data." An explicit empty filter is the escape
hatch, so dropping a filter is always a visible choice. The analysis
prompt states the same rule ("A chart visualizes the query it follows,
so give it the same `where` filter, `time_range` and
`comparison_time_range` as that query … A chart that drops a filter
shows different data than your findings describe"), and the eval
`AnalystCharts/ChartWithDashboardContext` asserts the chart's time range
and `where` carry the dashboard's.

It is possible only because filters are **structured expressions**, not
SQL text: narrowing is checked on the tree.

## 8. The `rill-charts` skill

`runtime/ai/instructions/data/charts.md`, served as a built-in,
always-apply skill to external clients only ("Rill's own agents carry
the same guidance in their prompts"), "distilled from Flint's authoring
skill and tied to Rill's `create_chart` arguments". It reaches the host
model **inside the `ai_instructions` field of the `list_metrics_views`
result**, so it works on hosts that never load skills; it is also
served by `list_skills` / `load_skill`, and `rill init --agent` writes
it to disk. Always-apply skills share a 32 KiB budget in that field; a
skill over it is skipped with a log line and must be loaded on demand.
A project skill of the same name replaces it.

Verbatim:

````markdown
## Charts with create_chart

The `create_chart` tool draws a chart from a metrics view. You describe the chart (`chart_spec`: a chart type and which field goes on which channel) and what to query (`data`: the metrics view, time range, grain and filter); Rill runs the query, formats the measures and renders the chart. Never pass rows, colors or axis settings. The tool description lists the chart types, their channels and the argument shape.

### Before you chart

- Know the fields: use `get_metrics_view` for the measures, dimensions and the time dimension, and reference them by their exact names.
- Look at the data first with `query_metrics_view` whenever the shape matters: how many distinct values a dimension has, whether a measure is a count, an amount or a rate, and whether a dimension mixes a total with its parts. Chart one level, never a total next to its parts.
- One chart answers one question. Prefer fewer series: cap a dimension with `limit`, and split with `row` or `column` facets instead of piling categories onto `color`.
- Pick the grain that gives roughly 10 to 100 points for the range: days for a few weeks, weeks for a quarter, months for a year or more.

### Choosing a chart

- A trend over time: Line Chart, with several measures on `y` or a dimension on `color`; Area Chart to stack parts; Bump Chart for ranks; Slope Chart for two periods.
- A period against the previous one: `data.comparison_time_range` on a Line, Area, Bar, Grouped Bar, Lollipop or Slope Chart with one measure and nothing on `color` (or `group`); the previous period is drawn as a second series.
- Categories compared: Bar Chart for one measure; Stacked Bar Chart with the parts on `color`; Grouped Bar Chart with the clustering dimension on `group`; Bar Table for many categories with value labels; Lollipop Chart for a ranking.
- Share of a whole: Pie Chart with the measure on `size` and the dimension on `color`, `innerRadius` for a donut; only for a handful of values that add up to a whole.
- How a total changed: Waterfall Chart with the step on `x` and the signed change on `y`; leave `color` unbound, it is reserved for a start/delta/end type field.
- Two measures per category: Scatter Plot with the dimension on `detail`, optional `size` and `color`; Heatmap for two dimensions and one measure.
- A distribution: Histogram, Boxplot, Violin Plot or Density Plot need one row per observation, so put the finest dimension on `detail`.

### Titles

Set `title` to the finding in a sentence and `subtitle` to what is measured, of whom, when and in what unit, for example "Spend fell 18% after the March price change" over "Daily total spend by device, Jan–Apr 2024, USD". Axes and legends take their labels from the metrics view, so do not restate field names.

### Pitfalls

- Parts of a whole go on a Stacked Bar Chart with `color`; values compared side by side go on a Grouped Bar Chart with `group`. A Bar Chart with a second dimension on `color` stacks.
- Counts and amounts on one axis share a scale and the smaller one flattens; use `row` facets or separate charts.
- More than about ten values on `color` is unreadable; use `limit`, a Bar Table or facets.
- A dimension with a single value in the range gives one mark; choose another breakdown.
- A chart is a snapshot of its arguments: when the user asks for another period, grain or breakdown, create a new chart.
- Do not restate the chart's numbers in prose; name the insight. The chart shows its data and an "Open in Rill" link.
- When the result reports that values were cut, coarsen `time_grain` or lower the `limit`s and create the chart again.
````

Two lines stand out against Lens's prompts. "Set `title` to the finding
in a sentence" makes the chart a claim. "Do not restate the chart's
numbers in prose; name the insight" is the opposite of Lens's "Put the
figure … first", and only safe because the chart carries its own
numbers and a link back to its query.

## 9. Flint, and ejecting to Vega-Lite

**Flint** (`microsoft/flint-chart`, MIT, read at `a794557`,
2026-10-21) is "a visualization language for the AI era", hosted
under the Data Formulator domain: a spec of data, **semantic types** per field, a chart
spec (`chartType` + `encodings` + `chartProperties`) and optional theme
and interaction specs, compiled to Vega-Lite, ECharts, Chart.js, Plotly
or native Excel charts. Semantic types (`Rank`, `YearMonth`, `Delta`,
`Temperature`, …) drive parsing, scales, axes, formats and colours. It
ships its own MCP server (`flint-chart-mcp`, hosted at
`flint.data-formulator.ai/mcp`), but that one takes **data values in the
spec**: shape A in `mcp-apps/data-analysis.md` §1. Rill uses only the
compiler and keeps data out of the model's arguments.

Rill's canvas dashboards also accept a Flint spec in YAML
(`custom_chart.spec`), compiled by the same `compile.ts`. **Eject**
(`flint/eject.ts`) turns a compiled chart back into a parameterised
Vega-Lite spec for hand editing, "at the cost of losing the compiler's
data-driven adaptation", rewriting resolved values into template
references so the component stays reusable:

```
field name     -> {{ .params.<param> }}
display name   -> {{ .fields.<param>.display_name }}
formatter name -> {{ .fields.<param>.format_type }}
```

Field names are rewritten only in field-valued properties and `datum`
accesses, so an enum such as `aggregate: "count"` survives a field
called `count`. The two-level design is explicit: a short spec the
model can write reliably, compiled to a full grammar a person can edit.
