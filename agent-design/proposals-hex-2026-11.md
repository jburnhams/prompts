# Proposals from the Hex deep dive (2026-11-12)

**Status: proposals only, none adopted.** Jonathan asked to discuss
before anything changes, so no other file under `agent-design/` is
edited. The research is in [`../data-agents/hex/`](../data-agents/hex).

**Evidence level.** Hex is closed source. Every proposal below rests on
Hex's documentation or on Hex's public skills repo, and each says which.
None rests on the secondary talk write-up alone. "Hex does X" here means
"Hex's docs say Hex does X"; nothing was exercised.

## Where Lens stands today, and what Hex has that it lacks

- **Lens already has the provenance half Hex makes structural.** Every
  claim in `answer.v1` cites refs, and `data.md` §2f's gate checks they
  resolve. Hex gets the same property differently: a Thread is a
  project, a number is a cell's output, and Inspect walks the DAG
  (`../data-agents/hex/semantic-layer.md` §4). Nothing to adopt; the
  comparison is recorded in proposal 7.
- **Lens's sources are a flat list.** The quick template lists up to 12
  sources from `mcp:warehouse/list_sources`, and the prompt says "Never
  guess a column name or a join key". There is no way to say which
  sources are trusted, which must never be used, or which a given
  surface may see.
- **Lens has no semantic layer, but Keel has the plumbing for one.**
  Keel has a query DSL that parses to and from SQL, with field mapping
  and policies (Jonathan, 2026-11-12; not yet in these docs). `data.md`
  §4a deferred the semantic layer: "the
  content, not the plumbing, is the hard part". Hex shows what the
  plumbing looks like once a customer has the content, and that most
  customers' content will arrive from dbt MetricFlow, Cube, Snowflake or
  Databricks rather than be written for Lens.
- **Lens's eval is one suite with five strata.** `eval.md` Suite 4 has
  the trap stratum (fan-out, null keys, period boundaries) but grades
  against fixed answers, and has no stratum for answers whose numbers
  are right and whose reasoning is wrong.
- **Lens has no route from a failed answer to a context fix.** The
  answer has `assumptions` and `not_checked`; nothing aggregates them,
  and `memory.md` §6's improvement requests (`ReportProblem`) are
  written by runs one at a time.

## Summary

| # | Proposal | Evidence | Would amend | Recommendation |
|---|---|---|---|---|
| 1 | Source flags the harness enforces: `excluded` is filtered out before the model sees it, `endorsed` is marked in the overview; a run-level `source_policy` labelled as steering | docs, source | `lens-on-keel/*.template.json` (`data_overview`); `keel/examples/warehouse.mcp-server.json`; `data.md` §2c | Adopt now |
| 2 | **A semantic layer on Keel's query DSL**: import semantic models into its field mapping, route all agent SQL through it so mapping and policy always apply, and cite the DSL query as provenance (revised after Jonathan's note on the DSL) | docs, source; Keel DSL from Jonathan | `data.md` §2c, §4a; `lens-on-keel/prompts/`; `reports/answer.v1.schema.json`; a new DSL spec page | **Discuss** |
| 3 | Context gaps as a typed field on the answer, aggregated into improvement requests with a distinct-user threshold | docs | `reports/answer.v1.schema.json`; `memory.md` §6 | Adopt the field; discuss the aggregation |
| 4 | Suite 4 grows SQL ground truth computed at grade time, method and answer judges, and an inference-trap stratum; context changes are gated by a preview run | docs, source | `eval.md` Suite 4, Metrics | Adopt now |
| 5 | If Lens's server is exposed to other hosts, use Hex's run-behind-a-tool shape and a per-surface source policy | docs | `proposals-mcp-apps-2026-11.md` proposals 6, 9 and 14 | Fold into MCP Apps 14 |
| 6 | Two cautions Keel already meets: a run handle must name one execution, and an edit must carry a precondition | docs | none | Record |
| 7 | Not now: projects as code-defined DAGs, provenance by structure, user memory as a nightly profile, "no routing" | docs, changelog | `future.md` | Record |

---

## 1. Source flags the harness enforces *(adopt now)*

**What.** Each source returned by the warehouse server's `list_sources`
may carry two flags, set by the deployment, not the model:

- **`excluded: true`** removes the source from the data overview *and*
  from `DescribeSource`, `Expand` and `RunSQL`'s allowed set. The model
  is never told it exists. A query that names it is refused with
  `source_excluded`.
- **`endorsed: true`** marks the source in the overview line (`★` or
  `endorsed`), and endorsed sources are listed first within
  `max_listed`.

A run spec (or template) may set `source_policy`: `all` (default),
`endorsed_only`, or a named set. Its documentation says plainly that it
**steers which sources the model is offered and is not a permission**,
because the run's delegation still decides what can be read.

**Why.** Hex's own skill gives the routing rule that motivates the first
flag: "Banning bad tables → **exclude from AI** (not text bans in
`hex.md`)", because "text bans are unreliable"
(`../data-agents/hex/agents-and-context.md` §2). A sentence in Lens's
context saying "don't use `raw_orders`" is the same text ban. Endorsement
is the cheap half: Hex reports agents "heavily prioritiz[e]" endorsed
sources, and its skill calls endorse-and-exclude "The fastest,
highest-leverage action". Governed mode's label is the third lesson:
Hex ships a source filter and says in a box of its own that it "isn't a
security control". Lens should ship the same filter with the same
label, so nobody mistakes it for one.

**Cost.** Two optional fields on a source and one filter in the
harness. The filter lives where the overview is built, so the quick
path's token cost does not change.

**Question.** Should `excluded` also hide the source from humans reading
the run record? Recommendation: no. The run record should show that a
source was filtered, by name, so a reviewer can tell an exclusion from
an absence.

## 2. A semantic layer on Keel's query DSL *(discuss)*

*Revised 2026-11-12 after Jonathan pointed out that **Keel already has a
query DSL that parses to and from SQL, with field mapping and
policies.** The design docs do not describe that DSL yet, so this
section says what it would need and asks what it already has. The first
version of this proposal invented a new "fourth selector" shaped on
Hex's `.query.yml`. That is no longer needed.*

**The reframe.** Most of what a semantic layer gives Hex, the DSL can
already give Keel, and in one respect it gives more:

| What Hex's semantic layer does | Where it lives in Hex | Where it would live in Keel |
|---|---|---|
| Logical names over physical columns (`Sales.Revenue`, a renamed dimension) | semantic model dimensions, semantic views ("presentational only") | **DSL field mapping** |
| Governed aggregations (`total_revenue`, cannot be re-aggregated) | model measures; the query grammar rejects `sum(total_revenue)` | a **measure** kind in the mapping, if the DSL can carry one (question 1) |
| Join paths with declared cardinality | model relations (`many_to_one`, …) | mapping-level joins, if the DSL has them (question 1) |
| Which sources the agent may use | Governed mode, which "isn't a security control" | **DSL policies**, which are enforced when the query compiles, so they *are* a control |
| A closed, validated query spec | `.query.yml`: unknown keys are errors | the DSL's parser |
| Provenance of a number | a cell in a DAG, walked back by Inspect | the DSL query on the claim, plus the SQL it compiled to |

The last-but-two row is the main gain. Hex has to tell admins that its
source filter is only steering, because the agent can still write SQL
against anything the user can read. In Keel, if every query the agent
writes goes through the DSL, mapping and policy apply on the way to SQL
whichever way the agent wrote it. That includes SQL the model wrote
directly, because the parser reads SQL back into the DSL.

**What we know about the DSL** (Jonathan, 2026-11-12, answering the
same questions in the Rill thread): it is **currently a subset of SQL**;
the agent writes **both** the DSL and SQL; field mappings and policies
are **metadata in MCP**, served alongside the tools; and he wants ideas
for extending it. The Rill proposals (`proposals-rill-2026-11.md`, PR
#45) cover extensions taken from Rill's query model (named measures,
time floor and grain, comparison ranges, deltas, relative time) and who
authors definitions. This section adds only what Hex's model has and
Rill's does not.

**Extensions from Hex's model** [docs; `../data-agents/hex/semantic-layer.md` §2]:

1. **Keep it SQL-shaped, so the round trip holds.** Because the DSL is a
   SQL subset and the agent writes both, a measure should look like SQL,
   not like a new clause language: a mapped measure is a virtual column
   used through a marker, for example
   `SELECT region, MEASURE(total_revenue) FROM orders GROUP BY region`.
   Databricks metric views use this `MEASURE()` form and Snowflake
   semantic views have their own clause; both are from prior knowledge,
   not read in this pass. Hex's YAML queries are the other option, and
   they break the "parse to and from SQL" property, which is the DSL's
   best feature.
2. **Measures are closed under aggregation.** `SUM(MEASURE(x))` is
   refused (`measure_reaggregated`), as Hex's grammar refuses
   `sum(total_revenue)`.
3. **Filtered and composed measures.** A measure can carry boolean
   filters (`revenue_from_us_deliveries` = `sum(price)` where
   `is_delivery` and `region = 'US'`) or be a formula over other measures
   (`profits` = `revenue - costs`). Both live in the mapping metadata,
   so the agent never re-derives them.
4. **Semi-additive measures.** For snapshot tables, a measure declares
   the dimension it must not be summed over and which value to pick
   (`over: date, pick: max`, optional `groupings: account_id`). Without
   this, "total balance" over a month is silently thirty times too big.
   It is the same failure as fan-out, and the mapping is the only place
   that can know it.
5. **Relations with cardinality.** The mapping declares joins between
   mapped tables as `many_to_one`, `one_to_many` or `one_to_one`, with
   the key condition. The compiler then picks the join path, so the
   agent names fields, not keys. When the agent aggregates a measure
   across a `one_to_many` join, the compiler either aggregates before
   joining or refuses (`fanout_risk`). This makes Suite 4's fan-out trap
   structural.
6. **Views as named subsets, which double as policy scope.** A Hex
   semantic view selects and renames fields for an audience and is
   "presentational only". In Keel the same subset can be what a policy
   grants: an invoker or deployment sees the `sales` view's fields and
   nothing else. That gives one object for both curation and access.
7. **Visibility on fields** (`public`, `internal`, `private`), so a
   helper dimension can feed a measure without being offered to the
   agent.
8. **Importers write MCP metadata.** Since mappings are MCP metadata,
   an importer for dbt MetricFlow, Cube, Snowflake Semantic Views or
   Hex's YAML turns a customer's existing models into that metadata,
   versioned, and a claim records the metadata version it compiled
   under. Hex runs five such importers.

**What, if the answers to the questions below allow it.**

1. **The agent's query surface is the DSL, with SQL accepted and parsed
   into it.** `RunSQL` keeps its name and contract, but the harness
   parses the SQL into the DSL, applies mapping and policy, and compiles
   back. SQL the parser cannot read is refused with a closed reason
   (`unparseable`, `policy_denied`, `unmapped_field`), the same pattern
   as `data.md` §2e's chart-spec refusals. The model may also write the
   DSL directly where that is shorter or clearer.
2. **Semantic models are imported into the mapping, not consumed through
   a vendor tool.** dbt MetricFlow, Cube, Snowflake Semantic Views and
   Hex's YAML all describe dimensions, measures and relations. A
   per-format importer writes them into the DSL's mapping for a
   deployment. Hex's own five importers show this is routine
   (`../data-agents/hex/semantic-layer.md` §1). Lens then has one query
   surface whatever the customer's layer is.
3. **The data overview lists logical names.** It shows mapped fields
   and measures, not physical tables, with measures listed first. That
   is what Hex means by "heavily prioritizes semantic models".
4. **Provenance cites the DSL query.** A claim in `answer.v1` carries the
   DSL query and the compiled SQL, plus the mapping and policy versions
   it compiled under. The DSL is the reviewable form, and the SQL is
   what ran.
5. **Proposal 1's flags become policies.** `excluded` is a deny policy,
   `endorsed` is overview metadata, and `source_policy` is a named
   policy set. The "steering, not a permission" label then applies only
   to endorsement.
6. **A prompt rule in the quick and investigate prompts**: "If a mapped
   measure answers the question, use it rather than re-deriving it from
   columns." If the DSL marks measures as closed under aggregation, the
   harness enforces this as well.

**Why.** Hex's skill names the failure this prevents: a model that
re-derives a governed metric in its own SQL drifts from the definition.
Hex's answer is policy text in `hex.md` plus an approval step
(`semantic-layer.md` §5). Keel can make it structural. Declared join
cardinality would also remove the fan-out trap at the source, which
Suite 4's stratum T now tests for by prompt. And `data.md` §4a deferred
the semantic layer because "the content, not the plumbing, is the hard
part". With the DSL, the plumbing exists and the content can be
imported.

**Questions still open.**

1. **Which of extensions 1–8 are worth it first?** Recommendation:
   relations with cardinality (5) and closed measures (2), because
   together they remove the fan-out and double-aggregation traps that
   Lens's quick path is most exposed to. Semi-additive measures (4)
   come next if any deployment has snapshot tables.
2. **Policies apply to both DSL and SQL**, per Jonathan. Does that hold
   for SQL outside the DSL subset (refused, or run under a coarser
   policy)? The answer decides whether `unparseable` is a refusal or a
   fallback.
3. **Where is the DSL specified?** A page in `agent-design/` (for
   example `keel/query-dsl.md`) would let Lens's prompts and schemas
   cite it. This should probably be written jointly with the Rill
   thread's extensions.

## 3. Context gaps on the answer, and an aggregation with a user threshold *(adopt the field; discuss the aggregation)*

**What.**

- `answer.v1` gains `context_gaps[]`, each `{kind, detail}` with `kind`
  one of `missing_definition` (a metric, population, join or rule the
  run had to assume) or `data_limitation` (coverage, a known gap, a
  caveat). These are Hex's *missing context* and *data limitation*
  warnings (`agents-and-context.md` §3). The prompt asks for one entry
  per assumption that a written definition would have removed.
- Hex's third kind, *user doubt*, is not the model's to report. The
  harness records it when the next turn in the same conversation
  disputes the answer, the way `memory.md` §0's output-feedback channel
  already treats ratings.
- **Aggregation (discuss):** a periodic job clusters gaps across runs
  into improvement requests (`memory.md` §6), raised only when **at
  least 2 distinct users, 2 runs and 3 signals** point at the same gap
  (Hex's defaults). Each request proposes one change (a definition, a
  description, an exclusion, an endorsement), and evidence links to the
  runs are visible only to roles that can read those runs.

**Why.** Lens's `assumptions` already captures what the run chose;
`context_gaps` captures what the *deployment* should fix, which is a
different addressee, which is `memory.md` §0's reason for separate
channels. Hex's distinct-user threshold is the part `memory.md` lacks:
one person asking the same confusing question five times is not a
workspace gap. Its role split on evidence is the part Keel's authority
model should want anyway.

**Cost.** One optional array in the schema and two prompt lines. The
aggregation is a new scheduled pipeline with its own model call; that is
the reason to discuss it separately.

## 4. Suite 4: ground truth at grade time, two judges, an inference-trap stratum *(adopt now)*

**What.** In `eval.md` Suite 4:

1. **Numeric ground truth as SQL run at grade time**, with a tolerance,
   alongside the fixed answer. Hex's `numeric_value` target
   `{sql, dataConnectionId}` and its skill's reason: it "recomputes each
   run and never goes stale" (`../data-agents/hex/evals.md` §1, §5). On
   a fixed fixture the value never moves; the point is that the same
   item runs against a customer warehouse unchanged.
2. **Two judge scopes**: one over the whole run (method: which source,
   whether it deduplicated) and one over the delivered answer only.
   Suite 4 scores "required disclosures"; the method judge is how the T
   stratum is graded when the figure is right by accident.
3. **Grading rules taken whole**: attempts tolerate one failure, an
   error in any attempt is an error and not a failure, `warn_only`
   rubrics that cannot fail an item, "refusal-correct cases get no
   numeric rubric", and one assertion per rubric.
4. **A new stratum C, inference traps**: questions where the data is
   easy and the inference is the trap (causal overreach, selection bias,
   aggregation flips, recommending an intervention from an observational
   cut), graded by rubrics written as **failure conditions**: "Fails if
   it presents X as settled causation without …". Right route: answer
   with the caveat. From Hex's eval-engineer, which calls these the
   cases that "find the model's ceiling" (`evals.md` §5).
5. **Context changes are gated.** A change to a deployment's Lens
   context (descriptions, exclusions, definitions) runs Suite 4's
   baseline items against the changed context before it is published,
   Hex's `--preview-id` loop. Lens's context already resolves at a ref
   (`context-files.md` §1b), so "a preview" is a run at the candidate
   ref.

**Why.** Each of these is a published, working rule from a team that
grades data-agent answers for a living. Stratum C covers the one
failure Lens's design has no defence against: a correct query, an
honest row count, and a wrong conclusion. Neither the provenance gate
nor the completion audit catches it.

**Cost.** One more stratum to write (Hex suggests ~90%-right answers
that fail on one step, which are slow to author) and judge calls per
item.

## 5. If Lens's server is exposed to other hosts *(fold into MCP Apps proposal 14)*

Hex is a worked example of `proposals-mcp-apps-2026-11.md` proposal 14
("the same servers in other hosts"), shipping in Claude, ChatGPT,
Cursor, Codex, Glean and Figma, with a view like proposal 6's
`ui://lens/progress` in front of a long run. If 14 is adopted, take
these from Hex (`../data-agents/hex/mcp-server.md`):

- **Three verbs on a handle**: start, get, continue. `get` returns
  status and a **wait hint** while running; `continue` is **refused
  while a run is in progress**. Proposal 6's sketch has a `run_status`
  app tool polling a task handle; add an explicit continue verb with
  that refusal.
- **Charts as stable references, an image tool as the fallback.** Hex's
  result names each chart's cell ID and a separate tool renders any of
  them as a PNG "for clients that don't support those widgets". Lens's
  equivalent is a chart ref plus an app-and-model tool that renders a
  `*.vl.json` to PNG.
- **A source policy per surface, fixed for the life of the run.**
  Sensitive sources are off by default for every external surface, and
  "If a Thread is started or continued through MCP, API, or CLI, this
  setting applies to the whole Thread". This belongs in MCP Apps
  proposal 9's authority rules and uses proposal 1's flags.
- **A server-side TTL on view content**, stated to the user (Hex: 24
  hours), rather than relying on the transcript to hold it.
- **Watch the host's tool cache.** Hex tells Claude users to "Refresh
  tools list" and Codex users to bypass the plugin, because hosts
  snapshot tool lists. Lens should version its tool surface additively
  and keep old names working.

Prefer the `2026-07-28` task extension to a polling tool where the host
supports it; Hex's polling tools work in every host, which is probably
why it chose them, and Lens can offer both.

## 6. Two cautions Keel already meets *(record)*

- **A run handle must name one execution.** Hex's docs warn that "The
  `runId` identifies the long-running draft session, not a single
  execution", and tell clients to compare start times. Keel's run IDs
  are per run; keep it that way when sessions or kernels arrive
  (`data.md` §4a's kernel-backed sessions).
- **An edit must carry a precondition.** Hex advises reading before
  writing and offers no version argument. Keel's edit path rejects
  stale hashes (`medium.md`). Recorded as validation.

## 7. Not now *(record in `future.md`)*

- **A report as a code-defined DAG.** Hex 4.0 projects are "defined
  entirely by code" with "every dependency, the full DAG" declared, so
  "A changed input only reruns what it affects" and any external agent
  can read and edit them. A Lens report could be the same thing: query
  files and chart specs with declared inputs, replayable, instead of a
  document whose claims cite refs. Bigger than Lens needs today.
- **Provenance by structure.** Hex never asks the model to cite; Inspect
  walks the graph. Lens's model-written `claims[].refs` plus a gate is
  the right choice for a runtime that is not a notebook. Worth
  revisiting if the DAG above happens.
- **User memory as a nightly profile.** Hex builds one per user, keeps
  it out of curated context "without replacing checks against schemas,
  endorsements, guides", and lets users view and disable it.
  `memory.md` already separates these channels; nothing new to adopt.
- **"No routing".** Hex's Auto "defaults to a single model … Hex does
  not do model routing", with small chart edits sent to a smaller model.
  Lens's economy-first start with `Expand` and `HandOff` is a deliberate
  difference (`models.md` §3); Hex's choice is a counterpoint, not
  evidence against it.

## Questions for the discussion

1. Proposal 2: which DSL extensions to take first (recommendation:
   relations with cardinality and closed measures), and where the DSL
   gets specified.
2. Proposal 3: is a scheduled aggregation pipeline worth building before
   there is enough traffic to clear a two-user threshold?
3. Proposal 4: who writes stratum C, and is it scored against the same
   pass bar as the others or tracked as a hill-climb?
4. Proposal 1: should `excluded` be settable per deployment only, or
   also per run?
