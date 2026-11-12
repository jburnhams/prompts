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
- **Lens has no semantic layer.** `data.md` §4a deferred it: "the
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
| 2 | **A semantic layer as a fourth selector**: prefer a governed measure, cite the semantic query as provenance, and state (or ask) before leaving the governed layer | docs, source | `data.md` §2c, §4a; `lens-on-keel/prompts/`; `reports/answer.v1.schema.json` | **Discuss** |
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

## 2. A semantic layer as a fourth selector *(discuss)*

**What.** When a deployment's warehouse server exposes semantic models
(through a semantic-query tool, for dbt MetricFlow, Cube, Snowflake
Semantic Views, Databricks metric views, or Hex itself):

1. **A fourth selector beside SQL** in `data.md` §2c: a structured
   semantic query naming a project, a base model or view, measures,
   dimensions with grain, and filters. Shape it on Hex's `.query.yml`
   (`../data-agents/hex/semantic-layer.md` §3), which is a closed,
   validated spec: unknown keys are errors, and governed measures cannot
   be re-aggregated.
2. **Provenance**: a claim may cite the semantic query (and the SQL the
   layer compiled it to, when the server returns it) instead of
   hand-written SQL. `answer.v1`'s `claims[]` gains an optional
   `semantic` object; the provenance gate accepts either.
3. **A prompt rule for the quick and investigate prompts**: "If a
   governed measure answers the question, use it. If you write SQL for a
   question a governed measure covers, say why." And a policy switch,
   per deployment, for Hex's stricter stance: "only query raw source
   tables with your explicit approval", which in Keel is an `AskUser`
   suspension.
4. **Semantic sources sort first** in the overview, as endorsed sources
   do in proposal 1.

**Why.** Every agent Hex ships prefers semantic models, and Hex's skill
explains the failure the rule prevents: once models exist, guides that
repeat metric definitions "*tempt* the agent into raw SQL"
(`semantic-layer.md` §5). Declared relation cardinality removes the
fan-out trap at the source, which Suite 4's stratum T currently tests
for by prompt. And `data.md` §4a's reason for deferring, that someone
has to write down what "active customer" means, is answered by
deployments that already have, in tools Lens would read rather than
replace.

**Questions for the discussion.**

1. **Which layer first?** Hex imports five formats; Lens should probably
   target one tool contract and let each warehouse server translate. Is
   there a customer layer to aim at?
2. **Ask or state?** Hex's semantic-first policy asks before leaving the
   layer. A hands-off run cannot ask cheaply (`AskUser` suspends). Is
   "state why" enough for the quick path, with "ask" only in
   `investigate`?
3. **Does this reopen `data.md` §4a's deferral** or stay a deployment
   option? Recommendation: reopen it, scoped to *consuming* a layer;
   authoring one stays out.

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

1. Proposal 2: which semantic layer, if any, do Lens's first deployments
   have, and should "ask before raw SQL" be available as a policy?
2. Proposal 3: is a scheduled aggregation pipeline worth building before
   there is enough traffic to clear a two-user threshold?
3. Proposal 4: who writes stratum C, and is it scored against the same
   pass bar as the others or tracked as a hill-climb?
4. Proposal 1: should `excluded` be settable per deployment only, or
   also per run?
