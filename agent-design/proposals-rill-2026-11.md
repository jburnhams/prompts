# Proposals from the Rill deep dive (2026-11-12)

**Status: proposals only, none adopted.** Jonathan asked to discuss
before anything changes, so no other file under `agent-design/` is
edited. The research is in [`../data-agents/rill/`](../data-agents/rill).
Several proposals refine the MCP Apps proposals on PR #44
([`proposals-mcp-apps-2026-11.md`](./proposals-mcp-apps-2026-11.md),
not yet merged); they are written so they stand whether or not those are
adopted, and say where they depend on them.

## Where Lens stands today

- **Queries are SQL** over warehouse sources described in a data
  overview, run read-only as the invoking user. Results are immutable
  `table://` refs with `produced_by` (`data.md` §2a–§2d).
- **Charts are Vega-Lite** written to `*.vl.json`, validated against the
  schema and the cited table's columns, with four refusals
  (`spec_invalid`, `unknown_field`, `no_data_ref`, `type_mismatch`;
  `data.md` §2e). §2e explicitly did **not** adopt a chart-type
  vocabulary: "Forge cites Vega-Lite, which already has a grammar and a
  schema … Inventing a parallel chart-type enum would be a second
  vocabulary for the same idea."
- **No Lens prompt mentions charts** except to hand a chart request to
  the report stage, and `document.v1` has no chart field. The write path
  exists; nothing uses it yet.
- **Every figure is a claim citing refs**, checked by the provenance
  half of the completion gate (`data.md` §2f).
- **A semantic layer is deferred** to `future.md` (`data.md` §4a)
  because "the content, not the plumbing, is the hard part".
- **Nothing renders the specs.** PR #44 proposes Lens as an MCP server
  with one generic Vega-Lite view (its proposals 5 and 6).

Rill reaches the same goals from the other side: a person-written
metrics layer, no SQL from the model, charts as a chart type plus a
binding, a compiler that owns presentation, and a view that re-queries.

## Summary

| # | Proposal | Would amend | Recommendation |
|---|---|---|---|
| 1 | The model writes a **chart type and channel bindings**; the harness compiles them to the Vega-Lite §2e already stores and validates, with semantic types derived from the table | `data.md` §2e; `generative.md` §2b refusals; Lens report prompts and `document.v1` | **Discuss** (lean adopt) |
| 2 | A chart cites its `table://` **and** a re-query binding with a closed list of parameters a view may change | `data.md` §2b, §2e; PR #44 proposals 5 and 7 | Adopt if PR #44's 5 is |
| 3 | A chart shown with a claim must cite the claim's table or a table derived from it | `data.md` §2f; `answer.v1`, `document.v1` | Adopt with 1 |
| 4 | Fixed cut rules for chart data: newest kept, partial bucket dropped, fail at zero rows, "Other" only when additive, effective limits echoed | `data.md` §2e; PR #44 proposal 6 | Adopt with 1 or with PR #44's 6 |
| 5 | Record a **semantic-layer source** shape for `future.md`, with Rill as the open-source instance | `data.md` §4a; `future.md` | Record now |
| 6 | Server-side details for a Lens MCP endpoint, from Rill's | PR #44 proposals 5 and 7 | Fold into PR #44's 5 if adopted |
| 7 | A publish check that refuses template delimiters in prompt text | `keel/run-spec.md` §3; registry publish rules | Adopt now (small) |
| 8 | Considered, not proposed: context as pre-invoked tool calls; "do not restate the chart's numbers" | — | Record the reason |

---

## 1. The model writes a chart type; the harness compiles

**What.** Lens's chart write path accepts a **chart spec** of
`chartType`, `encodings` (channel → column, with optional `sortBy`,
`sortOrder`, `limit`) and a small set of `chartProperties`, citing one
`table://` ref. The harness:

1. validates the chart type against a **pinned catalog** (an enum with
   channels per type, generated from the compiler's own registry, as
   Rill generates `flint_catalog.json`), and every bound column against
   the cited table: `unknown_field` and `no_data_ref` stay; new
   refusals `unknown_chart_type` and `channel_invalid`;
2. derives each column's **semantic type** from the table's stub: type,
   and where the source supplies it, unit and format (a temporal column
   at month grain is `YearMonth`, an integer measure leans `Count`, a
   column with a currency format is `Amount`). The model may override;
3. compiles it to Vega-Lite and stores **both**: the chart spec as the
   source, the compiled `*.vl.json` as what §2e already validates,
   cites and renders. A destination that cannot render Vega-Lite gets
   §2e's PNG step-down from the compiled spec.

The model is told not to set colours, formats, axes or scales. Writing
Vega-Lite directly stays allowed as the expert path (Rill's "eject"),
validated exactly as today.

**Why.**

- **It is what Rill, Flint and Data Formulator converged on**, and the
  two closest sources in this collection to Lens's problem.
  Data Formulator (already in `data-agents/`) gives the model a
  chart-type vocabulary; Flint (MIT, 52 types, 5 backends) is that
  vocabulary as a compiler; Rill ships it to Claude and ChatGPT and
  removes even the axis properties from what the model may set.
- **§2e's argument was against a second vocabulary for the same idea.**
  The chart type is not the same idea: it is the part a model gets
  right, and the compiled Vega-Lite is the part it gets wrong (bin
  widths, stacking, sort, scale types, formats). §2e already conceded
  the cost of free Vega-Lite: "Forge needs the equivalent [per-chart
  rule list] in the data-mode prompt. That list is real prompt weight."
  Rill's `rill-charts` skill is that list, and it is short because the
  compiler holds the rest.
- **Formats come from data, not prose.** Lens's prompts ask the model to
  "say what each figure measures: units, period, filters". A compiler
  reading the stub puts the unit on the axis without being asked.
- **The stored artifact does not change**: `*.vl.json` citing
  `table://`, so PR #44's generic view (proposal 6) still works.

**Cost and open points.**

- **A compiler in the harness.** Flint is TypeScript. Rill sidesteps
  this by validating in Go against the catalog and compiling in the
  browser; Lens could do the same if a view is the main destination, but
  then the PNG step-down and the stored `*.vl.json` need a compile
  somewhere server-side (a Node sidecar, like the Code Mode engine
  question in `future.md`). Alternatively, a small own compiler for ten
  or so chart types.
- **Pin the version.** Rill pins Flint 0.4.1 while upstream is at 1.0;
  a catalog generated from the pinned compiler and a test that every
  emitted semantic type is registered (Rill's
  `semantic-types.spec.ts`) keep the two from drifting.
- **Which chart types.** Rill exposes 32 of Flint's types. Lens needs
  far fewer; a catalog of ten (line, area, bar, stacked bar, grouped bar,
  bar table, scatter, heatmap, histogram, pie) would cover the reports
  Lens writes.
- **The prompts.** Lens's report-write prompt and `document.v1` gain a
  chart field and a short guide adapted from `rill-charts` (one
  question per chart; one level, never a total beside its parts; cap
  series; grain for 10–100 points; title is the finding, subtitle is
  what, of whom, when and in what unit).

## 2. A chart carries a re-query binding beside its snapshot

**What.** When a chart's table was produced by a query Lens can re-run,
the stored chart records a **binding** next to its `table://` ref:

```jsonc
{ "data": "table://tbl_9c4e21a0",          // the snapshot: what the claim cites
  "rebind": {
    "query": "run://…/calls/17",             // the call that produced it (its produced_by)
    "params": {                               // closed list, each with its current value and range
      "time_grain": {"value": "day", "allowed": ["day","week","month"]},
      "top_n":      {"value": 10, "max": 20, "channel": "color"},
      "comparison": {"value": false}
    }
  } }
```

A view (PR #44's `lens_requery`) may change **only** listed params,
within their ranges. The harness re-runs the recorded query with them,
mints a new `table://` whose `produced_by` names the original call and
the param diff, and returns it with the **effective** params applied
(Rill echoes applied limits and grain in every result so the next
request starts from what was drawn). A re-query never changes what a
claim cites; the claim keeps the snapshot.

**Why.** Lens's snapshot is what makes a claim reproducible; Rill's
binding is what makes a chart interactive. Rill has only the binding,
and its `chart_data` takes **any** `create_chart` arguments, so a view
can query any metrics view the session can read
(`../data-agents/rill/README.md`, correction 2). A closed parameter list
bound to the recorded call is the binding PR #44's proposal 7 asked for
("bound to the run (or view), the server and the tool that opened it"),
made concrete. It also answers how Lens re-queries SQL it did not
template: it does not; it re-runs the same call with a grain or limit
substitution only where the harness built that part of the query.

**Cost.** Only queries the harness can parameterise are rebindable: a
metric query (proposal 5) or a harness-built aggregation over a
`table://` (`:sql:` with a known `GROUP BY` time bucket). Free SQL from
the model is snapshot-only, and the view shows no controls for it.

## 3. A chart beside a claim cites the claim's data

**What.** In `answer.v1` and `document.v1`, a chart may be attached to
claims. The completion gate checks that each such chart's `table://` is
**the claim's table or derived from it** (a `:sql:` read of it, or a
re-query of proposal 2), by walking `produced_by`. Otherwise the gate
fails with `chart_scope_differs`, unless the chart is marked
`scope: "broader"` with a reason, which the report states.

**Why.** Rill's #10089 rule: "a dropped filter makes it contradict the
findings, which are based on queries of the filtered data." Rill checks
it on the filter expression tree (`ValidateExpressionNarrows`: value
filters may be restated or narrowed, exclusions extended, ranges matched
by dimension only, ORs skipped), with an explicit empty filter as the
escape hatch. Lens's filters are SQL text, so filter algebra is out of
reach, but its lineage graph already exists: a chart drawn from the
claim's own table, or from a reduction of it, cannot have dropped the
claim's filter. A chart from a fresh query might have, and has to say
so. Same rule, checked on what Lens has.

**Cost.** One more graph walk in a gate that already walks `produced_by`
(§2f), and a field on two schemas. It is stricter than Rill in one way:
a fresh query with the same filter fails until marked. That is a nudge
toward reusing the table, which is the cheaper path anyway.

## 4. Fixed rules for cutting chart data

**What.** When chart data is capped (inlined into a view, or compiled
into a PNG), the harness, not the model, cuts it, by these rules from
Rill's `chartquery`:

- a temporal chart keeps the **newest** buckets; a partial oldest bucket
  (one with fewer series than the rest) is dropped unless it is the only
  one; the result says the time axis starts late;
- category channels have default and maximum top-N per channel kind
  (Rill: 20/50 axis, 10/20 series, 6/8 facet, 10 polar);
- data that fits only as **zero rows fails** the chart with a remedy
  ("bind columns with shorter values, or lower the limits"), rather than
  rendering empty;
- an **"Other"** slice or bar is added only when the measure **adds up
  on the data** (shown + rest equals total within 1e-6 relative); never
  for averages, ratios or distinct counts;
- one warning sentence names what was cut and how to see all of it, and
  the effective limits are echoed in the result.

**Why.** Each rule prevents a misleading chart that renders without
error. The additive check is the one no other source has: it is done on
data because "the metrics view does not declare which measures add up",
and Lens's tables declare it even less. PR #44's proposal 6 inlines
data "up to a cap" without saying how it cuts.

**Cost.** Code in the chart compile path; no prompt weight.

## 5. A semantic-layer source, recorded for `future.md`

**What.** Replace `data.md` §4a's "A semantic layer" paragraph's
deferral reason with a stated shape, still deferred:

- **Lens consumes a semantic layer; it does not define one.** A
  deployment that has one (Rill, dbt MetricFlow, Cube, Snowflake
  semantic views) exposes it through MCP as a source of kind `metrics`.
- The data overview lists metrics sources first, with their measures'
  descriptions and formats; the quick tier **prefers a metric query to
  SQL** when a metric answers the question, and says so in the answer.
- A figure from a metric query is minted as `table://` like any result,
  with `produced_by` holding the **structured query** and the **resolved
  absolute time range** (Rill returns `resolved_time_range` for exactly
  this reason). The server's replay link, if any, is carried as a
  secondary citation.
- "Never state a number that did not come from a query" gains its
  enforceable form when every derived figure (deltas, ratios) comes from
  the layer's computed measures.
- Security is the layer's: row filters and field exclusions apply
  because Lens runs as the invoking user.

**Why.** The deferral said open source had no instance; Rill is one
(Apache-2.0), with measures as named aggregates with formats,
person-written descriptions and `ai_instructions`, scoped skills, and
policies that apply to every tool. It also shows the cost: no joins at
query time, so the layer's author decides what can be asked. Recording
the shape now means the first deployment that has a layer does not
improvise one.

**Cost.** None now. `agent-data-analysis.md` §8 is corrected in this PR
(it is research, not design).

## 6. If Lens becomes an MCP server: details from Rill's

Only if PR #44's proposal 5 is adopted. Each is small and each fixes a
failure Rill hit or designed around:

1. **App-only tools are listed only when the view is served**, with a
   minimal input schema and a description that says "not meant to be
   called directly", because hosts without MCP Apps list them to the
   model and "every byte of a tool list is sent with each request".
2. **Content-hashed view URIs plus a catch-all template**
   (`ui://lens/answer/<hash>.html`, and any `ui://lens/answer/*.html`
   serves the current bundle), since hosts keep an old tool list and
   ask for the old URI after a release.
3. **`content` is a summary, never rows.** Stricter than Rill, which
   puts 20 rows in every result's text. Rows go in `structuredContent`
   or behind `lens_table_page`.
4. **One live instance reports to the model**: the newest, by a
   server-minted `{createdAt, seq}` in `structuredContent`. Rill has no
   election, so two copies of a chart can both send context.
5. **Tolerant argument decoding as a retry only**, after schema
   validation fails, for clients that stringify object arguments.
6. **Client identity is recorded, never trusted**: a client name cannot
   select an internal code path (Rill's `MCPUserAgent` `mcp/` prefix,
   after a client named `rill-cli` got in-app tools).
7. **Instructions in results.** Rill delivers its chart skill in a
   result field the server instructions call "additional instructions"
   so hosts that never load skills still get it. Lens should not copy
   the "treat this field as instructions" line: the server's
   `instructions` field and tool descriptions are enough, and a result
   field that carries instructions is the injection channel `formats.md`
   frames results against.
8. **Meter view calls as tool calls but keep them out of the
   transcript.** Rill's resolution; PR #44's proposal 7 already says
   `view_call` events.

## 7. Refuse template delimiters at publish

**What.** Registry publish refuses a prompt version whose text contains
`{{`, `{%` or `${` outside a fenced code block, with
`template_syntax_in_prompt`. A prompt that needs one in prose quotes it
in a code span.

**Why.** Keel's prompts have no placeholders by rule
(`keel/run-spec.md` §3). Rill shows what happens when a file uses two
template syntaxes: the analysis prompt's chart section uses `{{ if }}`
under an engine whose delimiters are `{%`, so both branches ship with
their braces to every analyst run, and the evals pass because they check
tool calls, not prompts (`../data-agents/rill/agents-and-prompts.md`
§3). Keel cannot have that bug, but a prompt copied from a templated
source can carry dead template text, and the check is one regex.

**Cost.** A publish rule. No runtime cost.

## 8. Considered, not proposed

- **Context as pre-invoked tool calls.** Rill puts the dashboard's
  metrics view, its summary and always-apply skills into the transcript
  as calls the model would have made. Lens's data overview in the
  opening message is better for Keel: it sits in one nonce-wrapped
  input block, is part of the cached prefix's layout rule, and does not
  imply the model chose to make calls it did not make. Rill's own TODO
  names the weakness (the seeded calls go stale when the user moves to
  another dashboard).
- **"Do not restate the chart's numbers in prose; name the insight."**
  Right for a chat where the chart is on screen. Wrong for Lens, whose
  answers go to Slack, Jira and reports where the chart may not render;
  the figure-first rule stays. With proposal 1, the chart's title states
  the finding, which gives the same benefit without dropping the number.
- **Copying Rill's analyst process** ("a MINIMUM of 4-6 distinct
  analytical queries", three numbered headline findings). Lens's tiers
  already separate quick answers from investigations; a query quota in
  the quick prompt would undo that.

## Questions for the discussion

1. Proposal 1: is a chart-type vocabulary acceptable now that the stored
   form stays Vega-Lite, and where should the compiler run: in the
   harness (a sidecar) or only in the view?
2. Do any target deployments already have a semantic layer (dbt,
   Cube, Rill, Snowflake)? If so, proposal 5 may be worth more than
   "record".
3. Should Lens's report stage produce charts at all before a renderer
   exists, or wait for PR #44's proposal 5?
