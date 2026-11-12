# Proposals from the Rill deep dive (2026-11-12)

**Status: proposals only, none adopted.** Jonathan asked to discuss
before anything changes, so no other file under `agent-design/` is
edited. The research is in [`../data-agents/rill/`](../data-agents/rill).
Several proposals build on the MCP Apps proposals
([`proposals-mcp-apps-2026-11.md`](./proposals-mcp-apps-2026-11.md),
merged 2026-11-12, also not adopted); references like "B6" are to its
Part B.

**Revised the same day** after Jonathan said Keel already has a **query
DSL** that parses to and from SQL and carries **field mapping and
policies**. That moves the semantic layer from "record for later" to
the lead proposal: Keel has the lower half of what Rill's metrics views
are, and the rest of these proposals get easier on a structured query
than on SQL text. Nothing in `agent-design/` describes the DSL yet, so
what is assumed about it is stated in §0 and asked at the end.

## 0. Where Lens stands, and what the DSL changes

Today, per the design documents:

- **Lens's model writes SQL** over sources described in a data overview,
  run read-only as the invoking user. Results are immutable `table://`
  refs with `produced_by` (`data.md` §2a–§2d).
- **Charts are Vega-Lite** in `*.vl.json`, validated against the schema
  and the cited table's columns (`data.md` §2e), which explicitly
  rejected a chart-type vocabulary. No Lens prompt makes charts yet and
  `document.v1` has no chart field.
- **Every figure is a claim citing refs**, checked by the provenance
  half of the completion gate (`data.md` §2f).
- **A semantic layer is deferred** (`data.md` §4a): "the content, not
  the plumbing, is the hard part".
- **The Keel UI will be an MCP Apps host** with first-party Lens answer
  and chart views and a `lens_requery` app-only tool (B5, B6).

What Jonathan added (2026-11-12): **Keel has a query DSL, parsed to and
from SQL, with field mapping and policies.** Read against Rill, that
means:

| Rill metrics view | Keel query DSL (as described) | Gap |
|---|---|---|
| Logical field names over a physical table | field mapping | none |
| `security`: access, row filter, field exclusion, from user attributes | policies | none, if policies take principal attributes |
| A structured query (measures, dimensions, time range, filter tree, sort, limit) instead of SQL | the DSL | depends on whether it has aggregation, grouping and time bucketing |
| SQL from the model is impossible | SQL **parses into** the DSL | Keel is more permissive: the model may write SQL and still get mapping and policy |
| **Named measures**: an aggregate expression with a format, unit, description and an exact/approximate pair | not mentioned | the main gap |
| A **time dimension** with grains, calendar, comparison periods computed by the layer (`comparison_delta`, `comparison_ratio`) | not mentioned | second gap |
| Descriptions, `ai_instructions`, scoped skills | not mentioned | meaning, which is the hard part |

So the plumbing §4a deferred mostly exists. What is missing is a place
to write down **measures and their meaning** on top of the mapping.

## Summary

| # | Proposal | Would amend | Recommendation |
|---|---|---|---|
| 1 | **A metrics layer on the query DSL**: named measures, a time dimension and descriptions, defined over field mappings, enforced by the same policies; Lens queries through it | `data.md` §4a → a new `data.md` section; Lens prompts and data overview; `keel/` (wherever the DSL is specified) | **Discuss** (lean adopt) |
| 2 | **Provenance is the DSL query**: `produced_by` records the parsed query, the rendered SQL and the resolved absolute time range | `data.md` §2a, §2f; `answer.v1` | Adopt with 1 (or alone) |
| 3 | A chart beside a claim must **narrow the claim's filter**, checked on the DSL tree | `data.md` §2f; `answer.v1`, `document.v1` | Adopt with 2 |
| 4 | A chart's **re-query binding** is a closed set of DSL edits (grain, top-N, comparison) | `data.md` §2e; B6, B9 | Adopt with B6 |
| 5 | The model writes a **chart type and channel bindings**, compiled to the Vega-Lite §2e stores, with semantic types from measure definitions | `data.md` §2e; `generative.md` §2b; Lens report prompt and `document.v1` | Discuss |
| 6 | Fixed **cut rules** for chart data, with additivity declared on the measure | `data.md` §2e; B6 | Adopt with 5 or B6 |
| 7 | Details for first-party views and other hosts, from Rill's server | B6, B9, B14 | Fold into B6 and B14 |
| 8 | A publish check that refuses template delimiters in prompt text | `keel/run-spec.md` §3; registry publish | Adopt now (small) |
| 9 | Considered, not proposed | — | Record the reason |

---

## 1. A metrics layer on the query DSL

**What.** A **metrics definition** is a reviewed, versioned resource
(repo-resident like a context file, `context-files.md`) over one DSL
source:

```yaml
# metrics/orders.yaml
source: warehouse.orders            # a DSL source; its field mapping applies
time:
  field: order_ts
  grains: [day, week, month, quarter]
  calendar: {first_day_of_week: 1, first_month_of_year: 4}
dimensions:
  - {name: region, description: "Sales region of the billing address"}
  - {name: channel}
measures:
  - name: revenue
    expr: sum(net_amount)            # DSL expression over mapped fields
    unit: GBP
    format: currency
    additive: true                   # sums across any dimension (used by §6)
    description: "Net of refunds and VAT, in GBP"
  - name: active_customers
    expr: count_distinct(customer_id)
    approx_expr: approx_count_distinct(customer_id)
    additive: false
    description: "Customers with at least one order in the period"
instructions: |
  "Revenue" always means net revenue. Q1 starts in April.
```

- **Policies stay where they are**, on the DSL: a measure over a field
  the principal cannot see is not listed; row policies apply to every
  query through the layer. Rill gets this from its resolver
  (`get_metrics_view` answers "resource not found" when access is
  denied), Keel from the DSL.
- **Lens's data overview lists metrics first**: per definition, its
  measures (name, unit, description), dimensions, time grains and
  available range. `DescribeSource` on a metrics definition returns the
  full definition, like Rill's `get_metrics_view`.
- **A metric query** is a DSL query that names measures and
  dimensions, a time range, an optional comparison range and a filter.
  Comparison values (`revenue__prev`, `__delta`, `__ratio`) are
  computed by the layer, so the prompt rule "never state a number that
  did not come from a query" covers derived figures too: Lens never
  subtracts.
- **SQL stays available**, and keeps the mapping and policies because
  it parses into the DSL. The quick prompt prefers a metric query when a
  measure answers the question and says which it used; SQL is the path
  for questions no measure covers, as Rill's `query_sql` is for its
  developer agent.
- **Instructions are data, not instructions.** Rill's server tells the
  model to treat an `ai_instructions` result field as instructions.
  Keel puts a definition's `instructions` into the opening message's
  context block, under its trust tier, as it does for context files.

**Why.**

- §4a deferred a semantic layer because the content is the hard part.
  That is still true, but the content now has an obvious home next to
  field mappings that someone already maintains, and a format a person
  can review in a diff (Rill's metrics view YAML is exactly that).
- **It is the strongest correctness lever in the data sources read.**
  Rill's analyst never writes a join or an aggregate: the metric's
  definition was decided once by a person. DAB's failure analysis
  (`agent-data-analysis.md` §12a) puts most wrong answers in the
  computation over correctly selected data; a named measure removes
  that computation from the model.
- **It makes 2–6 cheap.** Every one of them is a check or an edit on a
  structured query, and most are hard on SQL text.

**Cost and open points.**

- **Who writes the definitions.** Not Lens. A deployment without them
  loses nothing: Lens falls back to the overview and SQL as today.
- **The DSL has to express it.** Aggregates, grouping, time bucketing
  and comparison ranges, or a thin layer that expands a metric query
  into DSL before rendering. Which is true is the first question below.
- **A verified-query repository** (Cortex Analyst, Genie) is the half
  Rill lacks too. Not proposed; definitions plus instructions first.

## 2. Provenance is the DSL query

**What.** Every `table://` minted from a query records, in
`produced_by`: the **parsed DSL query**, the **rendered SQL** actually
run, the **policy set** applied (by version), and the **resolved
absolute time range** when the query used a relative one. `answer.v1`'s
claim keeps `sql` and gains an optional `query` (the DSL form).

**Why.** Rill returns `resolved_time_range` on every result "so a later
reader knows exactly which period was meant", and cites the recorded
call rather than the SQL. A claim citing "last 30 days" is not
reproducible next week; a claim citing the resolved range is. Recording
the DSL form is what lets 3 and 4 work on a claim after the fact, and
recording the policy version answers "would another user see the same
number".

**Cost.** Fields on `produced_by`, and on the claim schema. Useful even
without proposal 1.

## 3. A chart beside a claim narrows the claim's filter

**What.** In `answer.v1` and `document.v1`, a chart may be attached to
claims. The completion gate checks that each attached chart's query
**narrows** each claim's query: every filter term the claim's query
requires is present in the chart's, restated or narrowed (Rill's rules:
value filters may be restated or narrowed to a subset; exclusions
restated or extended; range and pattern filters matched by field only;
`OR` and subquery terms skipped), and the time range is the same or
inside it. A chart drawn from the claim's own table passes trivially.
Otherwise the gate fails with `chart_drops_filter`, naming the dropped
term, unless the chart is marked `scope: "broader"` with a reason the
report states (Rill's explicit empty filter).

**Why.** Rill's #10089: "a dropped filter makes it contradict the
findings, which are based on queries of the filtered data." The
earlier draft of this proposal checked it by lineage, because Lens's
filters were SQL text. With SQL parsing into the DSL, the check can be
Rill's, on the tree, and it also catches a fresh query that silently
lost a filter, which lineage cannot.

**Cost.** A port of `ValidateExpressionNarrows` (160 lines of Go with comments)
to the DSL, and a field on two schemas.

## 4. A chart's re-query binding is a closed set of DSL edits

**What.** A chart records, beside its `table://` snapshot, the DSL
query that produced it and the **parameters a view may change**:

```jsonc
{ "data": "table://tbl_9c4e21a0",
  "rebind": {
    "query": "run://…/calls/17",
    "params": {
      "time_grain": {"value": "day", "allowed": ["day","week","month"]},
      "top_n":      {"value": 10, "max": 20, "channel": "color"},
      "comparison": {"value": false}
    } } }
```

`lens_requery` (B6) takes a param diff, not a query. The harness applies
it as an edit to the recorded DSL query, re-runs it under the run's
principal and policies (B9), mints a new `table://` whose
`produced_by` names the original call and the diff, and returns the
**effective** params (Rill echoes applied limits and grain so the next
request starts from what was drawn). The claim keeps citing the
snapshot.

**Why.** Rill's `chart_data` accepts any `create_chart` arguments, so a
view can query any metrics view the session can read
(`../data-agents/rill/README.md`, correction 2). B9's binding ("bound to
the run, the server and the tool that opened it") says what to check;
this says what the view may send. With a DSL, grain and top-N are node
edits rather than SQL rewriting, so any query Lens ran is rebindable,
not only harness-built ones.

**Cost.** Small once 2 exists.

## 5. The model writes a chart type; the harness compiles

**What.** Lens's chart write path accepts a chart spec of `chartType`,
`encodings` (channel → field, with optional `sortBy`, `sortOrder`,
`limit`) and a few `chartProperties`, citing one `table://` ref. The
harness validates the type against a pinned catalog (new refusals
`unknown_chart_type`, `channel_invalid`; `unknown_field` and
`no_data_ref` stay), **derives each field's semantic type** (from the
measure's unit and format under proposal 1, else from the column type
and grain), compiles to Vega-Lite, and stores both the chart spec and
the compiled `*.vl.json` that §2e validates and B6's `ui://keel/vega`
renders. The model is told not to set colours, formats, axes or scales.
Writing Vega-Lite directly stays allowed, validated as today (Rill's
"eject").

**Why.** Rill, Flint (MIT, 52 types) and Data Formulator converged on
it; Rill even removes axis properties from what the model may set. §2e
rejected a chart-type vocabulary as "a second vocabulary for the same
idea", but the chart type is the part a model gets right and the
compiled Vega-Lite is the part it gets wrong; §2e itself conceded that
free Vega-Lite needs a per-chart rule list "that is real prompt weight".
Under proposal 1 the semantic types are not guessed at all: `unit: GBP`
on the measure puts £ on the axis.

**Cost.** A compiler. Flint is TypeScript; Rill validates server side
against the catalog and compiles in the view. Keel can do the same now
that the Keel UI is the main destination (B5), with a server-side
compile only for the PNG step-down. Pin the compiler version and test
that every emitted semantic type is registered (Rill pins 0.4.1 while
upstream is at 1.0). A catalog of about ten types covers Lens's reports.
The report prompt gains a short guide adapted from `rill-charts`: one
question per chart; one level, never a total beside its parts; cap
series; a grain for 10–100 points; the title is the finding and the
subtitle is what, of whom, when and in what unit.

## 6. Cut rules for chart data

**What.** When chart data is capped (inlined into a view, or compiled
into a PNG), the harness cuts it by Rill's `chartquery` rules: keep the
newest buckets of a temporal chart and drop a partial oldest bucket;
default and maximum top-N per channel kind (Rill: 20/50 axis, 10/20
series, 6/8 facet); fail at zero rows with a remedy rather than render
empty; add an "Other" slice only for an **additive** measure; one
warning sentence with the remedy; effective limits echoed.

**Additivity.** Rill checks it on the data because "the metrics view
does not declare which measures add up". Under proposal 1 the
definition declares it (`additive`), and the data check stays as a
guard (shown plus rest equals total within 1e-6 relative).

**Why.** Each rule prevents a misleading chart that renders without
error. B6 inlines data "up to a cap" without saying how it cuts.

## 7. Details for first-party views and other hosts

From Rill's server, for B6 (first-party views) and B14 (other hosts):

1. **App-only tools have minimal schemas** and are listed only when a
   view is served: hosts without MCP Apps list them to the model, and
   "every byte of a tool list is sent with each request". B2 already
   keeps them out of Keel's own agents' grants.
2. **Content-hashed view URIs plus a catch-all template**
   (`ui://lens/answer/<hash>.html`, and any `ui://lens/answer/*.html`
   serves the current bundle), since other hosts keep an old tool list
   and ask for the old URI after a release. Inside Keel, B4's pinned
   digest covers this.
3. **`content` is a summary, never rows.** Stricter than Rill, which
   puts 20 rows in every chart result's text.
4. **Tolerant argument decoding only as a retry** after schema
   validation fails, for clients that stringify object arguments (B14).
5. **Client identity is recorded, never trusted**: a client name cannot
   select an internal code path (Rill's `mcp/` prefix after a client
   named `rill-cli` got in-app tools).
6. **Charts are metered in the same counter as queries** and kept out of
   the transcript (Rill's resolution; B9's `view_call` events).

B10's host supersession already covers what Rill lacks (several live
copies of a chart all updating the model).

## 8. Refuse template delimiters at publish

**What.** Registry publish refuses a prompt version whose text contains
`{{`, `{%` or `${` outside a fenced code block, with
`template_syntax_in_prompt`.

**Why.** Keel's prompts have no placeholders by rule (`keel/run-spec.md`
§3). Rill shows the failure: its analysis prompt's chart section uses
`{{ if }}` under an engine whose delimiters are `{%`, so both branches
reach every analyst run with their braces, and the evals pass because
they check tool calls, not prompts
(`../data-agents/rill/agents-and-prompts.md` §3). A prompt copied from a
templated source can carry the same dead text.

**Cost.** One regex at publish.

## 9. Considered, not proposed

- **Context as pre-invoked tool calls.** Rill seeds the dashboard's
  metrics view, its summary and always-apply skills as calls the model
  would have made. Lens's overview in the opening message is better for
  Keel: one nonce-wrapped block, cache-friendly, and it does not imply
  calls the model did not choose. Rill's own TODO names the weakness
  (stale when the user moves to another dashboard).
- **"Do not restate the chart's numbers in prose."** Right where the
  chart is always on screen; wrong for Lens answers that go to Slack,
  Jira or reports. Figure first stays; with proposal 5 the chart title
  states the finding.
- **Rill's query quota** ("a MINIMUM of 4-6 distinct analytical
  queries"). Lens's tiers already separate quick from investigate.
- **Treating a result field as instructions** (Rill's `ai_instructions`
  in `list_metrics_views`). See proposal 1: definitions' instructions go
  in the context block.

## Questions for the discussion

1. **The DSL.** Does it express aggregation, grouping, time bucketing
   and comparison ranges, or only selection and filtering? Is it
   model-facing (a tool the agent writes) or only the harness's internal
   form of the SQL the agent writes?
2. **Field mapping and policies.** Where are they defined (per source,
   per tenant, per deployment), and do policies take principal
   attributes (Rill's `{{ .user.domain }}`)?
3. **Who would write metrics definitions** in the first deployments,
   and do any already have them elsewhere (dbt MetricFlow, Cube, Looker,
   Snowflake semantic views) that could be imported?
4. **Proposal 5**: is a chart-type vocabulary acceptable now that the
   stored form stays Vega-Lite and the Keel UI can compile in the view?
