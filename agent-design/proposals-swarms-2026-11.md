# Proposals from the agent swarms deep dive (2026-11-28)

**Status: proposals only, none adopted.** Proposals 13-15 and the campaign stages in
proposal 10 were added the same day from the case studies (`../agent-swarms.md` §9a). Jonathan asked to see proposals before
anything changes, so no other file under `agent-design/` is edited. The research
is in [`../agent-swarms.md`](../agent-swarms.md); section references (§3, §8c)
are to that file unless they name another.

**Evidence level.** Each proposal says what it rests on and how that was read
(code, paper, abstract, docs, secondary), and marks our own inference.

**Words.** The `prompts` glossary's heading words, plus six with requests open in
`jburnhams/taxonomies` (swarm, topology, fan-out, board, vote, debate; defined in
`../agent-swarms.md`). If the intake picks other words, these proposals change
with them.

## Where Keel stands today

Keel already has much of what the field converged on:

- **Briefs in, typed reports out.** `Task` with a `scope`, `spawn_args` and a
  `report_schema` the harness validates (`keel/tools-and-agents.md` §4c).
- **Reports are data**, carrying the lowest trust of anything the sub-agent read.
- **Siblings, not chains; no recursion in v1; `clamp_to_parent`; a model tier per
  agent.** Matches Anthropic's Opus-lead/Sonnet-worker split and Cursor's model per
  role.
- **One budget ledger** for a run and its children, checked at every admission
  point including spawn (`keel/run-spec.md` §3), and a lifetime spawn cap
  (`budgets.subagents_total`).
- **Fan-out as harness code** for review (`review.md` §11h): ArcticSwarm's "model
  proposes, harness disposes", reached in October.
- **Frozen acceptance criteria and a completion gate** for plan → implement.

What it lacks, against §11:

- **Writers can run in parallel.** `forge.implement`'s `general-purpose` sub-agent
  holds `core.write` and `core.shell`; the only guard is a prompt line in `Task`'s
  description (`tools.md`, "Never launch two sub-agents in the same turn if their
  write targets could overlap").
- **No join semantics**: no deadline for a fan-out, no rule for a missing or failed
  part, no critical-path measure.
- **No acceptance check per delegated task**, only per run.
- **No shared channel** between sub-agents, for the few cases where one helps.
- **No campaign shape**: work too large for one run that an oracle could split.
- **No rule for adopting a multi-agent shape**: `eval.md` does not require a
  matched-spend comparison.

## Proposals

### 1. One writer per workspace, enforced by the harness

**What.** At most one agent in a run holds write tools (`core.write`, and
`core.shell` unless the sandbox makes it read-only) on the run's workspace at a
time. A template may give a sub-agent write tools only with `workspace: branch`
(its own worktree, proposal 2) or `workspace: share` with an exclusive write lease
the harness grants on spawn and releases on report. Two `share` writers in flight
is a validation error at publish (a P-rule) or a refused spawn at run time, never a
prompt instruction. `forge.implement`'s `general-purpose` drops to read and shell
in a read-only sandbox by default, keeping write only under `branch`.

**Why.** It is the clearest negative result read: Claude Code on SWE-bench Verified
fell from 83.0% to 59.0% with concurrent sub-agents in one workspace, the main
failure cause being shared state (arXiv 2610.10263, paper). The C compiler's 16
agents overwrote each other's fixes (docs); Claude Code's teams docs warn that two
teammates on one file "leads to overwrites" (docs); Bun's port saw agents in one
checkout run `git stash` and `reset --hard` against each other about two minutes in,
and had to forbid every git command but committing a named file (docs, §9a);
Cognition's 2026 rule is
"writes stay single-threaded" (docs). A prompt rule asks the model to know its
children's file sets in advance, which it cannot.

**Cost.** A grant check at spawn, and one field (proposal 2). Forge loses parallel
in-place edits, which no source read showed to help.

**Rests on:** paper, three docs; the enforcement is our inference.

### 2. A `workspace` mode for sub-agents: `inherit`, `branch`, `share`

**What.** `SubAgentDef` gains `workspace`: `inherit` (the default: the parent's
workspace, read-only unless the agent holds the lease from proposal 1), `branch`
(a fresh git worktree from the parent's current tree; the report carries the diff
as an artifact reference, and only the orchestrator applies it), or `share`
(read-write under the lease). Applying a `branch` diff is an ordinary write by the
orchestrator, so conflicts surface where one agent decides.

**Why.** Antigravity's Dynamic Workflows made exactly this a parameter
(`inherit`, `branch`, `share`) on 2026-11-13, and its `/swarm` gives each worker
"its own working copy" when several edit; a removed worker must "land its changes
first" (docs). Cursor's and the C compiler's git-as-channel designs are the
multi-run version. It turns "alternative attempts", one of the three cases where
concurrency helped (2610.10263), into something Forge can do safely: two
implementations in two worktrees, one kept.

**Cost.** Worktree creation per spawn (cheap in Keel's container), a diff
artifact type, and an `ApplyDiff` path for the orchestrator.

**Rests on:** docs (Antigravity), paper; the diff-as-artifact shape is inference.

### 3. Join rules for a fan-out: a deadline, and what a missing part means

**What.** A template's fan-out (review's specialists and validators now, any
`Task` batch later) declares `join`: `deadline_seconds`, and `on_missing`, one of
`fail` (the run cannot finish without it), `proceed_flagged` (the orchestrator
carries on and the report names the missing part) or `retry_once`. The harness
delivers a fixed `<subagent_report status="missing" reason="deadline|failed|budget">`
for each part it gives up on, so the orchestrator never waits on a part that will
not come and never mistakes silence for "nothing found". Forge review uses
`proceed_flagged` for specialists and `fail` for validators (a finding is not
posted unvalidated).

**Why.** ArcticSwarm's answer check waits 300 seconds and then its conditions
"become advisory" (paper); MAST's "premature termination" and "unaware of
termination conditions" are 18.6% of failures (paper); Claude Code's
`<task-notification>` already distinguishes `completed|failed|killed|blocked`
(`../agent-subagent-architectures.md` §7c). Keel defines what a run does at its
budget, not what an orchestrator does when one child is late.

**Cost.** A schema object and a fixed report form.

**Rests on:** paper, leaked prompt; the three-way rule is inference.

### 4. An acceptance check per delegated task

**What.** `Task` gains an optional `accept` list (criteria fixed at spawn, like the
plan's frozen `acceptance_criteria`), and a sub-agent's `report_schema` gains a
`criteria` array accounting for each, as `formats.md` §3c does for runs. The
harness rejects a report that does not account for every criterion (a format
failure, retried once with the fixed note), and a template may name a checker
sub-agent (Forge's `validator` pattern) to grade reports before the orchestrator
sees them.

**Why.** The systems with the best results check each part before integrating it:
AutoSwarm's task units carry "acceptance conditions" and a supervising agent, and
removing supervisory review cost 12.8 points (paper); ArcticSwarm's integration
gate needs a builder's and an independent reviewer's `Verified` (−5.9 points
without it, paper); Antigravity adds a `@verifier` "for every two to four workers"
(docs). MAST's verification failures are 23.5% of all (paper). Keel's completion
gate already does this for a run; this applies it one level down.

**Cost.** Schema fields and the existing gate logic reused.

**Rests on:** two papers, docs.

### 5. Measure the critical path, and record each orchestration decision

**What.** `Usage` gains `critical_steps` and `critical_wall_ms`: the orchestrator's
steps plus, for each parallel batch, the longest child's. `RunEvent` gains
`spawn` (who, which sub-agent, brief size, workspace mode), `report` (status,
size, criteria result) and `join` (batch id, parts, missing) so the five
orchestration decisions (when to spawn, whom, how to communicate, how to aggregate,
when to stop) can be read from one run's events. Exported per the telemetry
proposals' mapping as nested `invoke_agent` spans.

**Why.** Kimi measures its swarm by `CriticalSteps` because total steps are the
bill and the critical path is what a person waits for (paper). The orchestration-
trace survey frames every system by those five decisions (paper). Without them
Keel cannot answer the questions proposal 9 asks: did the fan-out shorten the run,
and what did it cost.

**Cost.** Counters and three event types.

**Rests on:** paper (Kimi), paper (survey); `proposals-telemetry-2026-11.md` §2.

### 6. Spawn rules against serial collapse and spurious parallelism

**What.** Two harness limits and one prompt rule. `budgets.subagents_total` (exists)
gets a per-template default (Forge implement 4, review its specialist count plus one
validator per candidate, Lens investigate 6) instead of unset; a new
`max_parallel` caps children in flight (default 4). The orchestrator prompts gain
Anthropic's scaling rule in Keel's words: one sub-agent for a fact-finding
question, two to four for a comparison, more only when the parts are independent
and each has its own check.

**Why.** Kimi names both failures: **serial collapse** (doing everything itself)
and **spurious parallelism** (spawning without real decomposition), and needed
reward terms for each (paper). Anthropic's early agents spawned "50 subagents for
simple queries" until given scaling rules (docs). SwarmBench: "a higher
parallelism rate does not necessarily lead to higher parallelism gain" (paper).
Claude Code teams advise starting with 3-5 (docs).

**Cost.** Defaults and a prompt paragraph. Numbers are a starting guess for eval to
move.

**Rests on:** paper, docs; the defaults are inference.

### 7. No debate, and no vote that drops a finding

**What.** A design rule, recorded in `review.md` §6a and `../agent-design/README.md`'s
decision log: Keel templates do not use multi-round debate as a quality method, and
no aggregation step drops a candidate because most agents disagree with it. Where
several agents produce candidates, they are unioned and each is checked on its
evidence (Forge's validator, Lens's recomputation). Votes are allowed only to
*rank* when a check is impossible, and the rank is shown.

**Why.** At matched budget debate ties or loses to a vote (2609.35875, abstract;
"nearly all of debate's benefit comes from the first exchange"), and a vote assumes
independent errors that models do not have: in about one split case in four the
minority is right (2606.29270, abstract). The best results read (Lean-checked
proofs, CI-gated builds, ArcticSwarm) aggregate by check, not agreement. Forge's
review already unions specialists and validates; this keeps a future change from
adding a vote.

**Cost.** None now.

**Rests on:** two abstracts, papers; the rule is inference.

### 8. Isolation first, then a board: a run-scoped board for research and discovery

**What.** For templates whose fan-out is a search (Lens investigate, a Forge plan
run's research), an optional run-scoped **board**: an append-only list of typed
posts (`claim`, `evidence`, `challenge`, `verified`) that sub-agents post to with a
harness tool, the orchestrator reads, and every post is a `RunEvent`. Each spawn
says `board: none | post | read_post`. The default for the first batch is `post`
(may post, may not read), so first drafts are independent; a second batch may be
`read_post` to challenge or extend. No peer messages: the board is the only
channel, as Codex's `disable_direct_message` makes it.

**Why.** ArcticSwarm's isolation-then-collaboration gate cut keeping a wrong first
candidate from 32.2% to 22.3% of runs and is worth 3.8 points alone (paper);
DeepMind's quantum teams worked independently and shared only Lean-verified ideas in
a notebook (docs); Codex, Antigravity and Agensh all moved coordination to one
observable board (source, docs, abstract). Keel has no channel at all between
sub-agents, which is right for review and wrong for open search.

**Cost.** One harness tool, one event type, a spawn field. Off unless a template
opts in.

**Rests on:** paper, docs, source.

### 9. A matched-spend rule for adopting any multi-agent shape

**What.** `eval.md` gains a rule: a template change that adds a sub-agent, a
fan-out or a board ships only if, on the suite, it beats both (a) the single-agent
template at the same token budget and (b) a vote or best-of-N over N single runs at
that budget, compared **per task, more than once**, with flips listed. The ship log
records critical-path time and cost beside quality.

**Why.** The scaling study's mean multi-agent change was −0.3% with an interval
from −58.7% to +77.2%, and above a 45% single-agent score returns went negative
(paper). Debate's gains disappeared against a budget-matched vote (abstract).
Anthropic's folding article asks for per-task flips over repeated runs
(`../agent-subagent-architectures.md` §7e). Review's specialists-versus-one-finder
question is already open in `eval.md`; this gives it a rule.

**Cost.** Two extra arms per comparison.

**Rests on:** paper, abstract, docs.

### 10. Forge: a campaign shape for work an oracle can split

**What.** For a ticket too large for one implement run (a migration, a framework
upgrade, a codemod across hundreds of files), a `forge.campaign` pipeline: a plan
stage finds an **oracle** that judges one unit alone (a test target, a module's CI,
a compiler or type check per file, a reference implementation) and writes the unit
list as an artifact; the harness fans out one implement run per unit, each on its
own branch (proposal 2), each gated by the oracle; a merge stage, owned by one run,
lands units in order and re-runs the oracle on the result. Units that fail N times
go back to the plan stage to be split or flagged, not retried forever. No oracle,
no campaign: the plan stage hands off instead.

The Bun port and Anthropic's migration guide (§9a, docs) give the stage list this proposal
would follow:

1. **Validate the oracle** before using it: it must pass on the original and fail
   on deliberately broken versions.
2. **A rulebook** (conventions for this migration) written with a person, reviewed
   by one sub-agent per failure category.
3. **A rehearsal** on three units, by two implementers with different briefs and a
   third agent that turns their diff into new rules; its output is discarded.
4. **The unit loop**: one implementer, two reviewers who see only the diff (not the
   implementer's reasoning) and a tie-breaker; a unit is done when its artifact
   exists and passes, so the queue resumes for free.
5. **Fix the loop, not the unit**: a finding that recurs across units becomes a
   rulebook rule, and the units it touched are re-queued; it is never patched unit
   by unit.
6. **One builder**: shared build, lockfile and generated code are owned by one
   harness process that batches units' changes, as Bun's build daemon did.
7. **Units that fail N times** go to a person or back to the plan stage, as
   Google's migration sends any file that fails its validation chain to a developer
   (paper).

**Why.** The two very large builds that worked (the C compiler, Cursor's browser)
both rested on an oracle that judged each piece, and both failed where it did not
(16 agents on one kernel bug, docs). LeanMarathon's "many local, recoverable,
parallel transactions" over a DAG is the same shape for proofs (abstract). Keel's
pipelines have "no parallel branches and no joins" (`keel/pipelines.md` §7e); this
is the one use case read that needs a bounded join, and `orchestration.md` §6's
spinoffs give it the record.

**Cost.** The largest proposal: a bounded fan-out edge in pipelines (fixed unit
list, fixed join), or campaign as harness code calling the existing templates.
Recorded for `future.md` if not v1.

**Rests on:** docs (two), abstract; the oracle precondition is inference.

### 11. Lens: discovery by volunteering over data sources

**What.** When a Lens question could be answered from several connected sources
(warehouses, MCP servers, semantic layers), Lens investigate posts the question to
the board (proposal 8) and spawns one cheap sub-agent per source, each granted only
that source; each posts `can_answer` with the tables, metrics or fields it would
use, or nothing. The orchestrator then queries only through sources that
volunteered, and the report cites which did. Each source agent's `scope` is its
source's catalogue, so the orchestrator never holds every schema.

**Why.** Google's blackboard data-discovery system lets agents that each own a
partition of a data lake volunteer, so the centre need not know who knows what, for
13-57% relative gains in end-to-end success (abstract, NeurIPS 2026). It fits
Keel's grant model exactly (a sub-agent can hold a server the orchestrator never
sees, R1) and keeps Lens's context small as sources grow.

**Cost.** Depends on proposal 8. One template variant.

**Rests on:** abstract; the mapping to Keel is inference.

### 12. A2A at the edge only, recorded

**What.** Record in `future.md`: Keel does not use A2A between its own agents.
If Keel later exposes a run to other vendors' agents, a run maps to an A2A `Task`
(states: queued → submitted, running → working, a gate or `AskUser` →
input-required, outcomes → completed, failed, canceled or rejected), the report and
artifacts to A2A `Artifact`s, and the template to an Agent Card.

**Why.** A2A 1.0 is stable and under the Linux Foundation's AAIF since 2026-08-27
(docs), and Kimi's Claw Groups shows cross-vendor coordination arriving (docs). No
source read uses A2A inside a swarm, and Keel's MCP-first decision stands.

**Cost.** A paragraph.

**Rests on:** docs.

### 13. Routing is not steered by what a sub-agent says about itself

**What.** Extend the "reports are data" rule (`keel/tools-and-agents.md` §4c) to
routing. A sub-agent's report cannot ask for, claim or be read as earning more work:
the `report_schema` has no free field for it, and the orchestrator prompt says that
which sub-agent gets the next task is decided by the task and the template's
`spawns`, never by a report's claims of competence, another agent's endorsement or
"history" in a report. The harness flags a run where one sub-agent's share of spawns
or tool calls jumps against its template's norm (an `anomaly` event), and memory
written by a run never records which sub-agent "is best at" something.

**Why.** The Show-Up attack (arXiv 2610.27574, paper, §9a) had a malicious
sub-agent win extra routing from supervisors up to 93% of the time, mostly by
claiming peer endorsement, and the effect survived 17 tasks through memory.
Restricting channels alone was "insufficient"; successful attacks made 4.43 extra
tool calls against 0.58. Keel's current rule stops a report being obeyed, not a
report being believed about who should do the next thing.

**Cost.** A prompt paragraph, a schema review, one event. Keel's fixed `spawns`
already limit who can be chosen.

**Rests on:** paper; the remedies are inference.

### 14. Lens: report the spread, cite every statement, mark synthesis

**What.** When a Lens run fans out analysts over the same question (proposal 11's
sources, or several hypotheses), the answer reports the spread of their results (a
small specification table: the choices each made and the estimate it got) instead of
one number, unless every analyst agrees within a stated tolerance. Every statement in
a Lens report cites the query or notebook that produced it, and a statement that
combines several results is marked as **synthesis** and held to the answer gate's
stricter check.

**Why.** About 5,000 analyst runs on the same data gave "substantial dispersion in
effect sizes, p-values, and conclusions", with reversals, and filtering to compliant
runs did not remove it (arXiv 2602.18710, paper). Kosmos cites every statement and
still found synthesis statements right only 57.9% of the time, against 85.5% for
data-analysis statements (arXiv 2511.02824, paper).

**Cost.** A report section and a statement type.

**Rests on:** two papers.

### 15. Forge: ask whether a change should exist

**What.** Forge's completion gate and review validator gain one fixed question per
changed file or finding: "is this change needed for the task at all?" A `no`
removes the change (implement) or the finding (review) before anything else is
checked. In a campaign (proposal 10) it is the first check in each unit's chain.

**Why.** Google's migration pipeline runs this check, "Punt", before build and tests
on every file (arXiv 2504.09691, paper); it is cheaper than a build and catches
changes that work but should not be there. Forge's gates ask whether work is
correct and complete, not whether each part belongs.

**Cost.** One schema-checked question.

**Rests on:** paper; the placement is inference.

## Not proposed

- **Peer messaging between sub-agents** (Claude Code teams, Codex
  `send_message`): the board in proposal 8 covers the cases, observably.
- **Recursion.** Cursor's sub-planners and Cognition's manager Devins are
  campaigns across runs, which proposal 10 handles with runs, not nested agents.
  `spawns` stays `maxItems: 0`.
- **Training an orchestrator** (Kimi's PARL): Keel uses provider models.
- **Tournaments and Elo** (co-scientist): an auto-evaluation "not based on an
  independent ground truth" by its own account; no Keel use case ranks open-ended
  hypotheses.
- **Personas for diversity**: they lowered accuracy (abstract).

## Open questions for the discussion

1. **Proposal 1's default for `forge.implement`**: drop sub-agent writes
   entirely, or keep them under `branch` only?
2. **Proposal 10**: is a campaign worth a bounded join in pipelines, or should it
   be harness code over existing templates?
3. **Proposal 8**: is a board worth building before Lens has more than one data
   source in use?
4. **Order**: 1, 3, 4, 9, 13 and 15 are small and stand alone; 2 enables 10; 8 enables 11;
   5 depends on the telemetry proposals. Is that the right order?
