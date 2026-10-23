# Keel: pipelines

Template stages wired together, and the pipeline run as the durable record of work. Part of [Keel](./README.md). Section numbers are shared across Keel's files, so a reference like §7f means the same section everywhere; [the README](./README.md#files) lists which file holds each.

---

## 7e. Pipelines

[`pipeline.schema.json`](./schemas/pipeline.schema.json). A
pipeline is versioned like a template: `{name, version, params, entry,
stages, edges, sinks, tools, max_hops, max_tier}`.

- **Stages are templates, used unchanged.** A stage names a template
  (`version: "pinned"` resolves at publish) and binds its params from
  `pipeline.params`, `origin` and `principal`. An edge into a stage can
  add params from the previous `result`. For example, implement's
  `write_scope` comes from the plan's report. P4 checks every route into
  every stage binds its template's required params.
- **Edges wire exits.** `on` names exactly one exit of the `from` stage:
  a status, an ending tool, a HandOff reason, or a gate answer, plus an
  optional expression. P2 checks every exit named is one that template
  really has, and every HandOff reason is wired.
- **Pipeline sinks run once, when the pipeline ends**, with `stage` and
  `result` set to the last stage's. The Jira update in use case 0c and
  the chat answer in 0d are pipeline sinks, so whichever stage ends the
  pipeline, the person hears back once, in one place. A pipeline that
  calls tools in its sinks declares them in its own `tools`. That
  declaration is never granted to a stage (P8).
- **`announce`** posts a line to the origin channel when an edge is
  taken. This is `../models.md` §4c's "what the user sees" row ("Taking a
  closer look"), now on the edge that causes it.
- **A `PipelineRun`** is the durable record of the work (§7f): the
  principal, delegation, origin and subject, a record per stage entered,
  child runs, the final outcome and the deliveries. Each attempt at a
  stage is an ordinary `Run` with `pipeline_run_id`, `stage` and
  `attempt` set, and its own events stream.

**Not a workflow engine.** There are no loops, no parallel branches and
no joins. Each stage ends in one exit, and at most one edge fires, so
the run is always a path through the graph. Fan-out lives inside a run,
where Forge already has it (`Task`, the review team). Nothing in the
use cases needs more, and a join would have to answer what "both stages
done" means when one was gated and the other wasn't.

---

## 7f. Pipeline runs are the durable record

There is no ledger. Everything `../orchestration.md` designed a ledger
for is a property of a pipeline run. **Every run belongs to one**: a
template run on its own is a one-stage pipeline run named after the
template. The cost on the quick chat path is one row written before the
first turn, and the dispatcher starts the stage at once rather than on a
polling cycle.

**A template can say how it behaves as a stage.** Its `stage_defaults`
carry a `retry` policy and a `settle` wait, used when it runs alone and
whenever a pipeline stage leaves them unset. A pipeline stage that sets
its own `retry` or `settle` replaces that default as a whole. So
`coding.java`, which opens a PR as its ending, waits for the merge even
when nobody wrapped it in a pipeline.

**Platform defaults** (the deployment's `defaults.policy`), which
templates and pipelines override where they have a field:

| Policy | Default |
|---|---|
| gate expiry | 7 days |
| on expiry | the waiting stage is **blocked**, for a person to retry or abandon (`abandon` is the alternative a template may choose) |
| session delegation cap | 24 hours |
| `stranded` | a ready stage not started within 1 hour |
| `waiting_stale` | a stage waiting more than 3 days |
| retry on `failed` | off: a genuine failure blocks the stage for a human; a template or stage can opt in |

A pipeline run holds one **stage record** per stage it entered. Each
record has:

- `state`: `ready`, `running`, `waiting`, `settling`, `blocked`, `done`
  or `abandoned`;
- its frozen params;
- its **attempts**, each one run, with its cause (`entered`, `retry`,
  `resume`, `approved_action`, `dependency_cleared`), terminal, status
  and summary;
- `waiting_on`, when it's waiting;
- `links` written back from downstream;
- the last outcome, and the concurrency key it holds.

Where each ledger job now lives:

| `../orchestration.md` (ledger) | Pipeline run |
|---|---|
| `attempts`, `max_attempts`, retry with a raised budget on `budget_exhausted` | the stage's `retry`: `max_attempts`, which ending statuses retry (by default `budget_exhausted`, `infra_failure` and a lost lease, but not `failed`), `raise_budgets` multipliers capped by the params' maxima. The previous attempt's report rides in as `prior_attempt`, so the persistence rule still spans attempts |
| `handoff` until the PR merges or closes | the stage's `settle`. A `done` run moves the stage to `settling`. The committer links the PR (`POST …/stages/{stage}:link`); merged → `done`, closed unmerged → `abandoned`. The concurrency key is held throughout (`held_while_settling`). `link_within_s` flags the case where the committer never ran |
| `parked` with a wake predicate | `waiting_on`: a gate, a child pipeline run, a settle event, a concurrency key held elsewhere, or a timer |
| `depends_on` from a `blocks_this` spinoff | the spinoff is a **child pipeline run** of the same template. The parent stage waits on it, and when it's done the parent gets a new attempt with `spinoff_report` carried in. If the child is abandoned, the parent stage is blocked with `dependency_abandoned` |
| `follows_this` spinoff, gated | a child pipeline run that starts only after a `spinoff_approval` gate. The parent doesn't wait |
| caps: 2 per run, depth 0, 8 per ticket | `completion.spinoffs.max_per_run`, the pipeline's `limits.spinoff_depth` and `limits.runs_per_subject` |
| one task per owner, `handoff` occupied | the template's concurrency key, taken per stage and held while settling. Read-only stages declare none, so they never queue behind implementation |
| health as queries, not a supervisor | `GET /v1/pipeline-runs?health=`: `stranded`, `waiting_stale`, `unlinked`, `repeated_failure`, `orphan_dependency`. These are still stored-field checks: nothing reads task text and decides |
| lease taken by the harness, never by the run | unchanged. The run never sees its pipeline run, its stage record or a lease |
| tracker reconciliation (§10a: adopt, stop, say) | unchanged rules, applied to the pipeline run's `subject`. A ticket closed under a running stage lets the run finish, delivers its report, then abandons with `ticket_closed`. A reopened ticket starts a new pipeline run with `supersedes`, and the old one is never resurrected |
| tracker updates on four transitions | stage-timed pipeline sinks: `at: {stage, event: run_ended \| settled \| blocked \| abandoned}` |

Two things are **not** carried over. A pipeline run can't be filed by
hand as an empty obligation: work starts by running something. And the
"one task, many unrelated runs sharing a ticket key" picture is gone.
Retries are attempts at a stage, follow-on work is a child run, and both
are visible on one record.

The invariant stays exactly as it was, under its new subject: **a run
may file, propose or report; it may not act on what it oversees.** A
run proposes spinoffs in its report, and the pipeline starts them. A
run never sees, retries, settles or abandons its own pipeline run.
