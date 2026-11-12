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

**Jonathan's answers (2026-11-12, second round):** the DSL expresses
"some" of this and is **currently a subset of SQL**, and he wants ideas
for extending it (§10). The agent writes **both** the DSL and SQL.
Field mappings and policies are **metadata in MCP**, so a definition
layer belongs there too (§11). Who writes metric definitions is open,
and he asked for ideas (§12).

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
| 10 | **Extending the DSL** beyond a SQL subset, in three tiers, each a thing the harness can check or compile and SQL text cannot | a new DSL page (`keel/query-dsl.md`) | **Discuss**; tier 1 is what 1–4 need |
| 11 | Metrics definitions are **MCP metadata** beside field mappings, pinned by digest in the server snapshot | `keel/tools-and-agents.md` §4a, §4b | Adopt with 1 |
| 12 | **Who writes definitions**: drafted by an agent and reviewed as a PR, grown from usage, imported where a layer exists, each with tests | `lens-on-keel/`; `keel/memory.md`; `eval.md` | **Discuss** |

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
    rollup: sum                      # how it may be re-aggregated (Hex §2 item 2; used by §6)
    description: "Net of refunds and VAT, in GBP"
  - name: active_customers
    expr: count_distinct(customer_id)
    approx_expr: approx_count_distinct(customer_id)
    rollup: none                     # distinct counts don't merge without a sketch
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
definition declares it (`rollup: sum`, or `semi_additive` across
non-time dimensions), and the data check stays as a
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

## 10. Extending the DSL beyond a SQL subset

The principle: **add to the DSL only what the harness can do something
with**, meaning check it, compile it, edit it or explain it, and what SQL
text either cannot say or says in too many ways to check. Everything
below exists in Rill's query (`runtime/metricsview/query.go`) or its
metrics view spec, read at `516bc91`. The SQL forms each extension
should parse from are given so that the "agent writes both" path keeps
working.

### Tier 1: what proposals 1–4 need

| Extension | Rill's form | Why the harness needs it | SQL it parses from |
|---|---|---|---|
| **Named measures**, referenced by name, re-aggregated only as their declared `rollup` allows | `measures: [{name: revenue}]` over a definition's `expression`; derived measures reference other measures (`type: derived`, `requires`) | the model cannot redefine revenue; formats, units and additivity travel with the number; "never compute" becomes enforceable | `MEASURE(revenue)` or a bare `revenue` column of a metrics relation, grouped by its dimensions; wrapping it (`SUM(MEASURE(revenue))`) is allowed only as its `rollup` permits: sum of sums, min of mins, averages and ratios rolled up from their parts, last value across time for semi-additive measures, nothing for distinct counts without a sketch (the rules in `proposals-hex-2026-11.md` §2 item 2) |
| **Time bucket** as a typed operation | `dimensions: [{name: ts, compute: {time_floor: {dimension: ts, grain: month}}}]`, with the definition's calendar (`first_day_of_week`, `first_month_of_year`) and a `time_zone` | grain becomes a parameter a view can change (proposal 4); fiscal calendars apply without the model knowing them; charts get a temporal semantic type at the right grain | `date_trunc('month', ts)`, `DATE_TRUNC`, `toStartOfMonth(ts)`, … each dialect's spelling normalised to one node |
| **Time range** as a typed field, with a **resolved** output | `time_range: {start, end}` or `{expression: "1M as of latest/D offset -1M"}`, `iso_duration`, `iso_offset`, `round_to_grain`; the result returns `resolved_time_range` | provenance can record the absolute range (proposal 2); narrowing can compare ranges (proposal 3); policies can cap range length (Rill's `max_time_range_days`) | `WHERE ts >= … AND ts < …` on the time field becomes the range; anything else on it stays a filter |
| **"As of latest"** anchoring | the `latest` anchor in Rill's time expressions resolves to the data's maximum time, not now | stale data does not silently return an empty "last 7 days"; the resolved range shows what "latest" was | none in SQL; DSL only |
| **Comparison range** and **computed comparison measures** | `comparison_time_range`, and measures computed as `comparison_value`, `comparison_delta`, `comparison_ratio`, `percent_of_total`; validated non-overlapping and of similar length (±20%) | period-over-period is the commonest data question and the commonest place for a model to make arithmetic or alignment errors; the layer computes it once | a self-join or a `CASE WHEN ts in period` pattern is too varied to parse reliably; **DSL only**, which is fine because the agent writes both |
| **Filter as a tree** with typed operators | `where: {cond: {op: and, exprs: [...]}}` with `eq`, `in`, `nin`, `lt`, `like`, … | proposal 3's narrowing check walks it; policies compose with it; a view's filter controls edit it | the `WHERE` clause, which a SQL-subset parser already produces |

### Tier 2: what makes results trustworthy

| Extension | Rill's form | Why |
|---|---|---|
| **Top-N with a remainder** | `chartquery`'s top-N pre-query per dimension, and an "Other" row added only when the measure adds up | one query shape for "top 10 and the rest" instead of a hand-written CTE; the additivity check lives in one place (proposal 6) |
| **Spine**: fill missing buckets | `spine: {time: {start, end, grain}}`, `treat_nulls_as` on the measure | a time series with gaps draws as a straight line across missing days; a spine makes the gap a zero or a null on purpose |
| **Exact or approximate** per measure | `exact_expression` beside `expression`; `exact: true` in the query; "Tell the user which precision was used" | approximate distinct counts are what make interactive queries cheap; the DSL records which one a figure used |
| **Query limits as policy** | `require_time_range`, `max_time_range_days`, default and maximum row limits, applied to AI queries only | these are policies Keel can attach per surface or principal, enforced before SQL is rendered, with Rill's one-line truncation warning |

### Tier 3: later, on demand

- **Window measures** (running totals, moving averages): Rill has
  `window` on measures, partitioned by time.
- **Pivot** (`pivot_on`) and **having** on measures.
- **Joins with declared cardinality**: Rill has none (one table per
  metrics view). Hex's semantic models do, and so does
  `proposals-hex-2026-11.md` §2 (PR #46). That section's "DSL extensions
  from Hex's model" also covers the `MEASURE()` marker this section
  uses, per-measure roll-up rules for wrapping a measure (sum, min/max, avg
  and ratio from their parts, semi-additive, none without a sketch),
  two-level aggregates with an explicit inner grain
  (`sparse_inner_grain`), filtered and
  composed measures, semi-additive measures, a `fanout_risk` refusal,
  views as a policy scope, field visibility, and importers. The two
  lists are written to fit together.

### What each extension costs the SQL path

Tier 1 and 2 extensions either parse from a recognisable SQL pattern
(`date_trunc`, a range on the time field, `MEASURE()`) or are DSL-only.
That is acceptable because the agent writes both: the prompt says "for
comparisons, top-N with a remainder and gap-filled series, use the
DSL". A canonical serialised form of the DSL also gives every query a
stable hash, which is what provenance, caching and the re-query binding
key on.

## 11. Definitions are MCP metadata, pinned like tool descriptions

**What.** A data server publishes its metrics definitions the way it
already publishes field mappings and policies (Jonathan: "metadata in
MCP"):

- as a **resource** per definition (for example
  `metrics://warehouse/orders`), listed at `:discover`, or as `_meta`
  on the query tool, whichever form the mapping metadata already uses;
- Keel **pins each definition by digest** in the server snapshot, so a
  changed definition is drift like a changed tool description
  (`keel/tools-and-agents.md` §4b; MCP Apps B2 does the same for view
  templates). A run records which definition versions its figures used
  (proposal 2's policy version, generalised);
- definitions' `instructions` and descriptions go into the opening
  message's context block under the server's trust tier, never as
  instructions in a result field (Rill's `ai_instructions` pattern is
  what not to copy);
- policies stay authoritative on the server side: a definition never
  widens access, it only names and describes.

**Why.** It keeps one place for "what this data means" that every
client of the server sees, Keel's agents, the Keel UI's views and third
party hosts (B14) alike, and it reuses snapshot pinning Keel already
has. Rill's equivalent is the metrics view YAML in the project, read
through `get_metrics_view`.

## 12. Who writes the definitions

Ideas, in the order they would pay off for a deployment that has none.

1. **An agent drafts them; a person merges them.** Rill's
   `GenerateMetricsViewFile` asks a model for "up to 10 suggested
   metrics" from a table's columns and types, restricted to "COUNT,
   SUM, MIN, MAX, and AVG" with no `WHERE` or `FILTER`, fills in the
   time dimension and dimensions **deterministically**, then validates
   each measure against the database and **drops the invalid ones**
   (up to three passes). On timeout (30 s) or error it falls back to a
   non-AI generator (`COUNT(*)` plus `SUM` of float columns). For Keel
   that is a `lens.define` template: read the mapping, the schema and
   column profiles, draft a definition, compile each measure through the
   DSL and run a probe query, and open the result as a pull request on
   the repo that holds the metadata, reviewed like Forge's output. The
   person supplies the meaning; the agent supplies the typing. (Rill's
   generator also shows why the validation pass matters: a measure-name
   collision check has its condition inverted, renaming every
   non-colliding measure. The validator caught bad SQL, not bad names.)
2. **Grown from usage.** Lens's run history already holds the queries
   people ask. A consolidation job (the `keel/memory.md` consolidator
   in `propose` mode) looks for the same aggregate over the same mapped
   field across runs, above a distinct-user threshold (the Hex thread's
   proposal 3 uses the same threshold for context gaps), and proposes it
   as a measure with the questions that used it as examples. Definitions
   then appear where people actually ask, not where a schema suggests.
3. **Promoted from accepted answers.** When a user accepts or reuses an
   answer, its DSL query becomes a **verified query** attached to the
   definition (the Cortex Analyst and Genie half that Rill lacks), and
   any ad-hoc aggregate in it becomes a candidate measure.
4. **Imported where a layer exists.** dbt MetricFlow, Cube, LookML,
   Snowflake semantic views. The Hex thread's proposal 2 covers
   importers; they write the same MCP metadata.
5. **Every definition carries tests.** A few example queries with
   expected results (or invariants: revenue is non-negative, sums of
   parts equal the total for additive measures), run when the
   definition changes and in `eval.md`'s Suite 4. A definition change
   that moves a test result is a reviewed change, not a silent one.

The recommendation is 1 with 5 to start, 2 once runs accumulate, and 4
when a customer brings a layer. All three write proposals for a person
to merge; none lets an agent change a definition in place.

## Questions for the discussion

Answered 2026-11-12: the DSL is a subset of SQL today; the agent writes
both; mappings and policies are MCP metadata; authoring is open.
Remaining:

1. **Which tier-1 extensions** in §10 are worth building first? Named
   measures and the time bucket unlock most of 1–4.
2. **In what form is the MCP metadata published today** (resources,
   `_meta` on tools, a custom method)? §11 should use the same.
3. **Which of §12's routes** fits the first deployments, and where does
   the metadata live as files (the data server's repo, a config repo)?
4. **Proposal 5**: is a chart-type vocabulary acceptable now that the
   stored form stays Vega-Lite and the Keel UI can compile in the view?
