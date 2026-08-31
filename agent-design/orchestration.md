# Orchestration: the run ledger

Every run in this design is one-shot. It is dispatched with an envelope,
it works, it calls `Complete`, and it ends. Nothing in the design records
that the *task* existed — only that a run happened. That is the gap this
document closes.

Read after [`formats.md`](./formats.md) (task envelope, `Complete`
schema, AskUser suspend/resume) and
[`context-files.md`](./context-files.md) §1b (`paths`/`kinds` resolution
at dispatch). It supersedes three items that
[`future.md`](./future.md) tracked separately — see §12.

**Status:** specified throughout; the twelve decisions behind it are in
`README.md`'s decision log. The v1 slice is named in §9. What is
deliberately *not* settled is listed at the end of §9 and in §10's
closing paragraph (reconciliation between the ledger and the tracker).

---

## 1. Two layers, and which one is missing

This design already has in-run orchestration. Coding mode delegates
through `Task` — stateless one-shot sub-agents, model-decided, for
context conservation. Review mode fans out to a fixed specialist team
and a validator. Both live *inside* a run: the orchestrator's process
holds the children, and everything dies together when the run ends.
That layer is settled and this document does not touch it.

What is missing is the layer *above* the run: a durable record of a unit
of work that exists **between** runs, can be related to other units, can
be claimed and given up on, and outlives the process that created it.
Call it the **ledger**.

The distinction is easy to lose because both layers are "orchestration"
and both involve more than one agent. The test that separates them is
what happens when the process dies. In-run fan-out loses everything —
which is correct, because its children are context-conservation devices
with nothing worth keeping. A ledger entry survives, because the thing
it records is not a computation but an *obligation*.

**The evidence that this is one missing noun rather than three missing
features** is in `future.md` itself. Three separate items are each
blocked on part of the same object:

| `future.md` item | What it says it is waiting for | The ledger's answer |
|---|---|---|
| Task splitting | "a spinoff primitive with a dependency relationship … a policy for who approves the split … an answer to what the originating run does while it waits" | §6 |
| A standing PR-steward loop | "the orchestration layer over them, plus the lifecycle policy questions (when to give up, how to hand off to a human)" | §7 (give-up as a query), §3 (`parked` with a wake condition) |
| Generalized task suspension (`medium.md` §4c) | already has the right instinct — "prefer being woken over waiting" | §3: the ledger makes a parked *task* the default and narrows run-suspension to the case where a transcript must survive |

Each was being designed as its own subsystem. They are one table.

**Scope: coding runs, not review runs.** A review run is dispatched by an
event, posts everything it concludes, and terminates — it carries no
obligation that outlives the run, which is the entire reason the ledger
exists. So review runs stay outside it in v1. What *does* enter the
ledger is the review → implement handoff (`medium.md` §1b): a finding
that needs code becomes an ordinary **coding** task with
`source: "review_finding"`. That keeps the review pipeline unchanged and
keeps §8's "may file, may not dispatch" rule from having to be
re-answered for reviewers. `medium.md` §3f's stateful re-review sessions
are the case that will eventually pull review runs in; when they do, the
table already has the shape.

**Why this matters more for us than for an interactive agent.** In an
archetype-1 tool, *the human is the ledger*: they remember what is
outstanding, notice a stalled task, and decide what gets picked up next.
This design deliberately removed that human
([`README.md`](./README.md), "Why archetype 2, not archetype 1") and
nothing took over the job. OpenClaw is the field's clearest confirmation
— it ships a ledger (Workboard) **disabled by default**, because it is
archetype 1 by default and only needs one when the humans are turned
off.

---

## 2. The task record

Harness-side state. Not a model-facing object: no run reads or writes
a task record directly (§8 explains why, and §9 gives the one exception).

```json
{
  "id": "string — stable, ledger-assigned",
  "source": "jira | manual | review_finding | ci_failure | spinoff",
  "issue_key": "string | null — the originating ticket, when there is one",
  "repository": "owner/repo",
  "mode": "plan | implement | review",
  "state": "filed | ready | running | handoff | parked | blocked | done | abandoned",
  "owner": "string — the concurrency key; see §4",
  "priority": "low | normal | high | urgent",

  "scope": {
    "paths": ["string — the subtree this task may write in"],
    "kinds": ["string — validated against the context service"],
    "authority": "opaque — the dispatch authority this task was created under; see §11"
  },

  "depends_on": ["task id — this task is not ready until each is done"],
  "spun_off_from": "task id | null",
  "wake": { "kind": "reply | pr | build | jira | timer", "predicate": "…" },

  "attempts": [
    { "run_id": "string", "started_at": "…", "ended_at": "…",
      "status": "done | planned | skipped | failed | blocked | budget_exhausted | lease_lost",
      "summary": "string — the run's Complete.summary, or the failure reason" }
  ],
  "budget": { "max_attempts": 2, "max_run_seconds": 0, "attempts_used": 0 },
  "abandon_reason": "string | null — set only in the abandoned state; e.g. budget_exhausted, ticket_closed, pr_closed_unmerged",

  "outcome": {
    "target_branch": "string | null",
    "pull_request": "string | null — written back once by the committer; what the PR-event subscription watches",
    "report": "the last successful run's Complete.report, verbatim",
    "evidence": ["artifact id"]
  },

  "created_at": "…", "updated_at": "…"
}
```

Three fields deserve their reasons stated.

**`scope` is frozen at creation, not resolved at pickup.** A task
carries the `paths` and `kinds` it was filed with, and dispatch resolves
context against *those*, not against whatever the dispatcher happens to
believe when it picks the task up.
[`context-files.md`](./context-files.md) §1b already establishes that
context is resolved once at dispatch and that the model never chooses
its own scope mid-run; a persisted task extends the same rule across
time. The corollary in §11 is the load-bearing one: a task record must
never be able to *widen* the authority of whoever picks it up later.

**`attempts` is a list, not a counter.** The give-up rules in §7 are
queries over it, and a repeated-failure judgment needs to see what
failed, not just how often. It is also what makes a re-dispatch
legible: three runs against one task are three attempts on one record,
not three unrelated runs that happen to share a ticket key.

**`outcome.report` is the previous run's `Complete.report` verbatim.**
This is the same mechanism as the plan → implement handoff
(`formats.md` §6): context transfers between runs through a
structured artifact placed in the next envelope, never through shared
memory. The ledger adds no new channel; it stores the one that exists.

---

## 3. Lifecycle

```
                       ┌──────────┐
     filed ──────────► │  ready   │ ◄──── dependency satisfied
       │  deps met     └────┬─────┘        wake predicate fired
       │                    │ dispatch
       │               ┌────▼─────┐
       │               │ running  │
       │               └────┬─────┘
       │        ┌───────────┼───────────┬──────────────┐
       │        │           │           │              │
       │   Complete    Complete     Complete       lease lost
       │   (done)      (blocked)    (planned)      / crash
       │        │           │           │              │
       │   ┌────▼───┐  ┌────▼────┐ ┌────▼────┐    back to ready
       │   │handoff │  │ blocked │ │  filed  │    (attempt recorded)
       │   └────┬───┘  └─────────┘ │ (follow-│
       │        │                  │ up impl)│
       │  PR merged                └─────────┘
       │        │        PR closed unmerged ──► abandoned
       │   ┌────▼───┐
       └──►│  done  │            parked ◄──► ready   (wake predicate)
           └────────┘            abandoned            (§7 give-up,
                                                       ticket closed)
```

Two states differ from what a naive port of a Kanban board would give,
and both differences are ours rather than borrowed.

**`handoff`, not `review`.** This design never commits, pushes, or opens
a PR (`README.md`'s decision log). A coding run's deliverable is a
working tree plus a report, and **an external committer downstream turns
that into a commit and a PR** — a confirmed deployment fact, which is
what makes this a v1 state rather than a deferred one, and what gives
`suggested_commit_message` (`formats.md` §3a) a consumer. `handoff` is
the state where that has happened and the task is out of the agent's
hands but not yet finished. It matters because §4's concurrency rule
counts it as occupied.

**A task leaves `handoff` on a PR merged or closed event.** The
committer writes the PR reference back onto the task once, and from
there the ledger uses the **same PR-activity subscription
`medium.md` §1 already needs** for CI-failure and comment-responder
runs — no second integration, and the ledger sees human pushes to the
branch for free. Merged → `done`. Closed unmerged → `abandoned`, with
the PR reference kept: a closed PR is a decision, not a failure, and it
should not be retried. A task in `handoff` with no PR reference after a
threshold is a `stranded` case for §7, because it means the committer
never ran.

**`parked` holds a task, not a run.** `medium.md` §4c's suspension
mechanism keeps a *run* alive across an event — envelope, transcript
and wake condition all preserved — because it assumed the accumulated
context had to survive. A parked task keeps only the record. When the
predicate fires, a fresh run picks it up with a fresh budget and the
previous attempt's report in its envelope. That is strictly cheaper and
it is the right default; §12 says what run-suspension narrows to.

`abandoned` is a real terminal state, distinct from `done` and from
`blocked`. A task the ledger gave up on has a recorded reason
(`abandon_reason`) and does not silently rot in `ready`. This is the
point `future.md` deferred as "when to give up, how to hand off to a
human"; §7 makes it a query.

**When the ticket is closed underneath a task**, the ledger never kills
a run mid-flight. A run may be seconds from a useful report, and
cancelling it discards a working tree and a transcript for nothing. So:
the run finishes normally, the ledger records the outcome, and *then*
the task moves to `abandoned` with `abandon_reason: "ticket_closed"`.
The report is still posted to the ticket — work that happened should
not be invisible because the ticket closed while it happened. Two
details follow from the same reasoning:

- **Dependent spinoffs go to `blocked`, not `abandoned`.** A closed
  parent ticket says nothing about whether the spun-off work is still
  worth doing, and abandoning a chain on one human's ticket-hygiene
  click is a worse error than leaving it for someone to look at.
- **A task already in `handoff` is left alone.** There is a PR open; the
  PR's own merged/closed event is the authority, and a closed ticket
  with a landing PR is a human's contradiction to resolve, not the
  ledger's.

---

## 4. Dispatch

A dispatch pass is a **deterministic scheduler**, not a model call.
In order:

1. Promote `filed` tasks whose `depends_on` are all `done` to `ready`.
2. Fire `parked` tasks whose wake predicate is satisfied to `ready`.
3. Expire leases past their deadline; record a `lease_lost` attempt and
   return the task to `ready` (§5).
4. Apply the §7 give-up queries; move what qualifies to `blocked` or
   `abandoned`.
5. Select and dispatch, subject to the rules below.

**Ordering**: priority, then dependency depth (a task that unblocks
others first), then creation time. Stated so it is reproducible, not
because the order is subtle.

**One task per owner, and `handoff` counts as occupied.** A pass starts
at most one task for a given `owner`, and skips an owner that already
has a task in `running` *or* `handoff`. `owner` is the **(repository,
branch)** pair. This is adapted from OpenClaw's Workboard rule, which is
expressed per agent id — we have no agent identities, so the key names
the contended resource instead of the contending party.

The `handoff` half is the part worth arguing for, and the argument is
about the branch rather than about a person's queue: a review of the
handed-off PR can itself dispatch an `implement` run
(`medium.md` §1b), and that run targets **the same branch**. Starting
unrelated work there in the meantime guarantees a conflict with the
agent's own earlier output. Keying on the branch is also the honest
version of what the rule protects — an earlier draft keyed it on
(repository, ticket assignee) and justified it as reviewer attention,
which was a proxy for the resource rather than the resource.

**This rule has a substrate prerequisite, and it is met.** Two branches
can only be occupied at once if two runs can hold two checkouts at once.
The harness provisions **a worktree or clone per run** and checks out
`target_branch` before the run starts (`formats.md` §1a) — so parallel
runs in one repository are real, and (repository, branch) is
enforceable rather than aspirational. Where that does not hold, the rule
degrades correctly to repository-only: one live checkout is one branch.

Two consequences the design has to state rather than assume:

- **The agent still never creates or switches branches.** Checkout
  provisioning moves from "the harness has already checked out
  `target_branch`" to "the harness owns per-run checkouts", which is a
  larger job, not a different rule. The no-git-writes stance and its
  harness-side blocklist (`README.md`'s decision log) are unchanged.
- **A spun-off task needs a branch decided at dispatch.** A `follows_this`
  spinoff is ordinarily new work off the base branch; a `blocks_this`
  spinoff usually wants the *same* branch, since its output is what the
  parent will build on. The ledger records the intended branch on the
  task at file time and the dispatcher resolves it — the run does not
  choose. Where a `blocks_this` spinoff shares the parent's branch, the
  parent is `blocked` and therefore not occupying it, so the owner rule
  is satisfied by construction.

**Read-only runs do not occupy an owner.** A `plan` run and a review run
neither hold a working tree nor leave un-landed work, so counting them
against (repository, branch) would serialise investigation behind
implementation for no reason — and `plan` runs are exactly the work you
want to run several of at once while an implement task is in `handoff`.
The rule applies to `implement` tasks only. Stated because the naive
reading of §2's record — every task has an `owner`, therefore every task
competes — is wrong, and the failure it produces (a quiet throughput
collapse) is the kind nobody diagnoses.

**A per-pass start cap**, defaulting low. Its job is to make a
misconfigured dependency graph or a badly-decomposed ticket produce a
small visible mess rather than a large one.

**Deterministic run lanes.** A task's runs share a lane key derived from
its id, so a re-dispatch routes back to the same lane rather than
forking a new one. This is what makes `attempts` a coherent history
instead of scattered runs sharing a ticket key.

---

## 5. Leases, not claims

Workboard hands the *worker* a claim token: the worker calls
`workboard_claim`, receives a token, and every later mutation requires
it. That shape exists because its workers are ordinary chat agents that
must opt in to work they discovered themselves.

Our runs do not discover work — the harness dispatches them. So the
harness takes the **lease** before the run starts and settles it from
the `Complete` report afterwards. The agent never sees a token, never
claims, never heartbeats, and gets no ledger-mutation tools. That is
both leaner (the brief's rule) and one less injection surface: nothing a
run reads can talk it into releasing, reassigning, or completing a task
record.

A lease has a deadline. It is refreshed by the run's own liveness signal
— the harness already observes every tool call — not by a model-issued
heartbeat, because a model calling "I am still alive" proves only that
the model still has turns left.

**Recovery does not require the lease.** An expired or orphaned lease is
reclaimable by the next dispatch pass unconditionally. This mirrors the
one genuinely good asymmetry in Workboard's design: the token stops
*concurrent* mutation, but the recovery paths deliberately do not need
it, so no task can be permanently orphaned by a dead process. Ours gets
the property for free by keeping the lease harness-side.

---

## 6. Task splitting

`future.md`'s task-splitting item, resolved. The problem it states:

> A run whose fix reaches outside [its `paths`] scope is therefore
> working, for those files, without the conventions that govern them.

and its own preferred answer:

> a run that finds work outside its remit spins off a dependent task
> rather than stretching itself.

**The mechanism.** `Complete.report` gains a `spun_off` array. Each
entry is a *proposal* for a task record, not a task record:

```json
"spun_off": [
  {
    "relation": "blocks_this | follows_this",
    "title": "string — what needs doing",
    "rationale": "string — why this run did not do it",
    "paths": ["string — the subtree the work is in, as best the run knows"],
    "kinds": ["string — optional; omitted means the dispatcher decides"]
  }
]
```

Two relations, and the distinction is the whole point:

- **`follows_this`** — this run finished its own scope; something else
  also needs doing. The originating task goes to `handoff` as normal
  and the spinoff is filed depending on it.
- **`blocks_this`** — this run *cannot* finish without work outside its
  scope. The run completes with `status: "blocked"`, the spinoff is
  filed, and the originating task's `depends_on` gains it. When the
  spinoff completes, the originating task returns to `ready` and a
  fresh run picks it up with the spinoff's report in its envelope.

That second case is `future.md`'s open question — "what the originating
run does while it waits" — answered as **nothing**. It ends. No
transcript is held. The task waits, and a task costs nothing to hold.

**Why a `Complete` field and not a mid-run tool.** A `ProposeTask` tool
callable mid-run is the obvious shape and it is the wrong one for v1.
The behaviour we want is that a run which discovers out-of-scope work
*does not do it* — so the moment of discovery is the moment it decides
to stop or to carry on within scope, and either way the report is where
that decision belongs. A mid-run tool invites the run to file the
spinoff and then keep going anyway. It also keeps the tool surface at
its current size, which the brief asks for. Tracked as an upgrade in
§12, with the concrete trigger: a run that needs to file several
unrelated spinoffs discovered at different points and cannot hold them
all to the end.

**What this replaces.** v1's current answer is in `context-files.md`
§1b: record the out-of-scope write in the post-run report and let the
review entrypoint catch what the coding run could not. That stays as the
backstop — it catches the case where the run wandered without noticing,
which no spinoff mechanism can. Splitting handles the case where the run
*did* notice, which is the more common one and the one where the current
answer wastes a review cycle.

**Approval — asymmetric, and each half has its own reason.**
`future.md` asks who approves a split. The answer is that `filed → ready`
depends on the relation:

- **`blocks_this` auto-chains.** Its parent is *already stalled*. Gating
  it means two tasks wait on one human decision that nobody has been
  asked to prioritise, and the work is by construction a prerequisite of
  something already approved — the ticket. The caps in §11 are what bound
  it.
- **`follows_this` is gated.** This is new scope the run decided to
  invent. It is precisely where a human should look, and nothing is
  stalled while they do: the parent went to `handoff` normally.

The gate reuses the mechanism `formats.md` §6 already offers for
plan → implement — an approving reply on the ticket thread — rather than
adding a second approval channel. The two gates stay independent
decisions, but a deployment that has already chosen "gated" there will
find the same wiring here.

Note what the asymmetry is *not*: it is not a claim that blocking work is
safer. It is a claim that the cost of a wrong auto-dispatch is bounded by
§11's caps, while the cost of a wrong gate on a blocking task is an
indefinitely stalled ticket — and only one of those two failures is
self-limiting.

---

## 7. Health without an overseer

Everything an overseer agent would notice, expressed as a query over
stored fields. All of these run against tasks nobody is executing, which
is the property that matters — a model-based supervisor can only reason
about what it is shown, and a stalled task shows nothing.

| Check | Condition | Action |
|---|---|---|
| `stranded` | `ready` and not dispatched for longer than a threshold | surface; usually an owner-concurrency stall (§4) |
| `stranded_handoff` | `handoff` with no `outcome.pull_request` after a threshold | the committer never ran; surface, do not retry the coding work |
| `lease_expired` | `running` with a lease past its deadline | reclaim, record `lease_lost` attempt |
| `repeated_failure` | ≥2 attempts ending `failed` | `blocked` — a human reads the attempt summaries |
| `budget_exhausted` | `attempts_used == max_attempts` | `abandoned`, `abandon_reason: "budget_exhausted"` |
| `context_exhausted` | last attempt ended `Complete(budget_exhausted)` (§8) | retry with a raised budget — **does not** count toward `repeated_failure`. The retry's envelope carries the previous attempt's report, so an obstacle named there counts as already-seen for the persistence rule (§8) |
| `blocked_stale` | `blocked` and untouched for longer than a threshold | escalate |
| `unverified_done` | `done` with an empty `verification` array in `outcome.report` | flag on the handoff |
| `missing_regression` | `done`, the diff added a test file, `regression_evidence` is null | flag on the handoff |
| `dependency_cycle` | `depends_on` closure contains the task | reject at file time, not at dispatch |
| `orphan_dependency` | `depends_on` names an `abandoned` task | `blocked` — the thing it waited for is not coming |

`unverified_done` and `missing_regression` deserve a note: both are
already enforced *inside* a run — the first-call checklist gate and the
post-run cross-check (`tools.md`, `formats.md` §3a). Restating them as
ledger queries is not duplication. The in-run gates catch a run trying
to finish dishonestly; the ledger queries catch a *deployment* whose
gates were misconfigured or whose runs are systematically producing
weak evidence, which is a different failure and only visible across
tasks.

`budget_exhausted` is the give-up rule `future.md` deferred. It is
deliberately a count, not a judgment: three honest failures is a signal
worth acting on regardless of what the failures were, and any rule
smart enough to distinguish them is a rule that can be argued out of
firing.

---

## 8. Roles and oversight

**Position: the oversight function stays non-model. There is no
supervisor run.**

The temptation, once a ledger exists, is a periodic run that reads the
board and decides what is stuck, what to retry, and what to escalate.
It should be resisted, for four reasons:

1. **The judgments are cheap and deterministic.** Every entry in §7 is a
   query. Paying for a model call, plus its non-determinism, to
   re-derive `attempts_used == max_attempts` is a straight loss.
2. **A supervisor cannot see unclaimed work honestly.** It reasons over
   what is rendered into its context. A ledger with a thousand tasks
   gets summarised, and the summarisation is where a stalled task
   disappears. Queries have no such window.
3. **It is an injection surface pointed at the scheduler.** Task titles,
   rationales and attempt summaries are written by earlier runs, which
   in turn read ticket text, PR bodies and comments — all untrusted
   (`formats.md` §1). A supervisor that reads those to decide what runs
   next lets untrusted text choose the next run. Nothing else in this
   design gives untrusted content that reach.
4. **The field's own answer is the same.** OpenClaw ships a Workboard
   `orchestratorProfile` field and an `autoDecompose` board flag, and
   neither launches an orchestrator: `shouldAutoOrchestrate` only
   *marks* a triage card as a candidate, capped per board per pass, and
   the decomposition still happens when an ordinary run picks the card
   up. Its Codex supervision spec says outright, "There is no separate
   Supervisor plugin." Its swarm docs note it ships no built-in `worker`
   agent id at all. A large, mature system that had every reason to
   build an overseer did not.

### What roles this design has, and the invariant they share

We already have more role structure than OpenClaw, which has none in
code: `subagent_type` (`general-purpose` / `reviewer` / `validator`)
with the reviewer's lens as a second key
(`tools.md`; `context-files.md` §"Kinds"). The ledger adds no role. It
adds a *dispatcher*, which is not an agent.

What the ledger does add is a new actor with a new power — whatever
files a spun-off task — and that needs the invariant the existing roles
already satisfy stated explicitly:

> **A role may file, propose or report. It may not act on what it
> oversees.**

The validator does not post; it accepts or rejects a finding and the
orchestrator posts. A coding run does not commit. A `plan` run does not
implement. And now: **a run may file a follow-up task; it may not
dispatch one.** Filing goes into `filed`, and only the dispatcher —
under §4's rules, §11's caps and whatever `filed → ready` policy the
deployment sets — turns that into a run.

The same invariant read across five systems in OpenClaw is what
convinced me it is a rule rather than five coincidences: its Custodian
proposes config and a human applies it; its exec auto-reviewer can
allow or escalate but structurally cannot deny; its ClawSweeper review
bot "recommends with evidence, never executes the close"; its skill
reviewer emits pending proposals; its memory consolidation places
supplied entries but "never author[s] replacement prose". Every role in
that system is a shrunken tool surface plus a typed output contract,
and none of them can act on the thing it oversees.

### Self-oversight inside a run

One thing worth importing from OpenClaw at the run level rather than the
ledger level. Its session **goal** injects a line into every turn:

> advance; keep active until fully achieved; **block only after the same
> blocker on 3 consecutive turns**; after update_goal, provide the
> requested visible final

paired with an optional token budget whose exhaustion moves the goal to
`budget_limited` — a terminal state *distinct from failure*.

Both halves are things this design lacked, and **both are being taken**:

- **A persistence rule**, in `system-prompts.md`'s coding workflow: do
  not conclude `blocked` on the first occurrence of a blocker — only
  once the *same* blocker has recurred across turns, with the attempts
  in between named in the report. The shape is good because it is
  checkable from the transcript rather than from introspection; a run
  cannot satisfy it by feeling stuck.
- **`budget_exhausted` as its own `Complete` status**, distinct from
  `failed`. `formats.md` §7's run bounding already produces the
  situation — the final-turn nudge fires and the run reports what it
  has — but classifies the result as a degraded completion, which loses
  the one fact the ledger needs. "Ran out of room" and "genuinely could
  not do it" are different retry decisions: the first is worth a fresh
  run with a raised budget, the second is worth a human. §7's
  `repeated_failure` query counts only the second.

The retry asymmetry is the reason the status is worth a schema change
rather than a note in `summary`: with `max_attempts: 2` (§11), spending
an attempt on a run that merely ran out of context is expensive.

**The two rules interact, and the interaction improves both.** A nudged
run that has hit an obstacle once has not satisfied the persistence rule
and cannot honestly report `blocked`; `budget_exhausted` wins, and the
obstacle goes in the report body (`formats.md` §7). The ledger retries
with a raised budget, `outcome.report` reaches the retry's envelope
verbatim (§2), and an obstacle named there **counts as the first
occurrence** — so the persistence rule spans *attempts* rather than
turns.

That is where it belonged. A second look at an obstacle is only worth
having if it gets a real context window, and the within-a-run version
guaranteed the opposite: the second look happened at the exhausted tail
of the first. It also means the rule is cheap to satisfy honestly — a
run does not have to spend budget manufacturing a second failure to earn
the right to say it is stuck.

One consequence to keep in view: this is the design's only path where a
task's *effective* budget grows, and it is bounded by `max_attempts: 2`
rather than by a separate escalation policy. A task that exhausts
context twice is `abandoned` under `budget_exhausted`, not raised a
third time.

---

## 9. What changes elsewhere, and the v1 slice

The whole of §2–§8 is not a v1. The slice that is:

**In the design documents.**

- `formats.md` §3a: `Complete.report` gains `spun_off` (§6).
- `formats.md` §7 and `tools.md`: `Complete.status` gains
  **`budget_exhausted`**, distinct from `failed` (§8).
- `system-prompts.md`, coding mode: two rules — work outside the run's
  `paths` is **filed, not done** (the first thing in this design that
  makes "keep tasks focussed" structural rather than aspirational), and
  the **persistence rule** for declaring `blocked` (§8).
- `tools.md`: no new tools. `Complete`'s description gains a sentence on
  `spun_off` and one on `budget_exhausted`.

**In the harness.**

- A task table with `id`, `state`, `owner`, `depends_on`,
  `spun_off_from`, `attempts`, `budget`, `abandon_reason`, `scope`,
  `outcome`. States `filed` / `ready` / `running` / `handoff` / `done` /
  `blocked` / `abandoned` — everything except `parked`.
- Per-run checkout provisioning (§4), which the (repository, branch)
  owner key depends on.
- A dispatch pass implementing §4 steps 1, 3, 4 and 5, with §11's caps
  and the asymmetric `filed → ready` gate from §6.
- §7's queries: `lease_expired`, `repeated_failure`, `budget_exhausted`,
  `stranded`, `orphan_dependency`, `dependency_cycle`. The two
  evidence-quality queries (`unverified_done`, `missing_regression`) can
  follow.
- A PR-event subscription closing `handoff` (§3) — the same one
  `medium.md` §1 needs anyway — and the committer writing
  `outcome.pull_request` back once.
- Projection comments on the four transitions in §10.

**Deferred within this document**, in rough order of when they will be
wanted: `parked` and wake predicates (§3), which need `medium.md` §1's
trigger sources first; `kinds` on a spinoff (§6), which needs
`context-files.md`'s narrowing to be live; spinoff **depth 1** (§11),
which needs evidence about how often layered dependencies actually
occur; a mid-run `ProposeTask` tool (§6), on the trigger named there;
and review runs entering the ledger at all (§1), which
`medium.md` §3f's stateful re-review will force.

---

## 10. Where the ledger lives

**Decided: the ledger owns execution state in its own store and holds
`issue_key` as a reference; the tracker stays the human-facing record and
receives projections.**

The question this settles is whether the table is just Jira with an
agent-owned status field. It is not, and the reason is that only three
fields in §2 — `state`, `depends_on`, `priority` — map onto tracker
fields without abuse. A lease with a deadline, an attempt list with run
ids, a frozen `scope` carrying an authority token, and per-task budgets
are **agent-execution state**, not project-management state, and putting
them in custom fields is how integrations become unmaintainable. Tracker
writes are also a permission surface v1 does not have: the decision log
keeps `AddComment` as the only outward channel and `WriteJira` is
deferred to `medium.md` §5b, so a Jira-as-ledger design would have to
open that surface before the ledger did anything useful.

**Projections keep humans looking at one place.** The ledger posts
through the existing `AddComment` path — no new privilege, no new
channel — on exactly four transitions:

| Transition | Why it is worth a comment |
|---|---|
| A spinoff is `filed` | Someone has to see that the agent invented scope, especially a gated `follows_this` that is waiting for their reply |
| A task moves to `blocked` | The blocker is the thing a human can act on |
| A task moves to `abandoned` | Silence here is the failure mode the whole ledger exists to prevent |
| A `blocks_this` dependency completes and its parent returns to `ready` | Otherwise a ticket appears to sit dead for a day and then move on its own |

`done` is deliberately **not** on that list: the `Complete` report
already reaches the ticket through the existing path, and a second
"task done" comment on top of it is noise. Neither is `running` — a
comment per dispatch would make the ticket unreadable, and the state is
visible in the ledger.

**What this leaves open** is reconciliation, and it is a real cost of the
choice rather than an oversight: the ledger and the tracker can disagree,
because a human can move a ticket without telling the ledger. §3's
ticket-closed policy is the one case worked through; the general rule is
that **the tracker wins on intent and the ledger wins on execution
state**, and where they conflict the ledger projects a comment rather
than silently reconciling.

## 11. Safety

A ledger is the point where a hands-off system starts scheduling its own
work. Three constraints, all needed in the same pass as the feature —
`future.md` already flagged the approval question as open, and the
ledger makes it live rather than theoretical.

**Caps, enforced by the dispatcher.** Numbers, not placeholders — a cap
without a value is a cap nobody implemented:

| Cap | v1 value | What it prevents |
|---|---|---|
| Spun-off tasks per run | **2** | One run turning a badly-scoped ticket into a fan of fragments |
| Spinoff **depth** | **0** | A spun-off task spinning off further work — see below |
| Total tasks per originating `issue_key` | **8** | Fan-out spread across *attempts*, which the per-run cap cannot see |
| Attempts per task (`max_attempts`) | **2** | A task grinding through retries that are not converging |

**Depth 0 is the load-bearing one, and it is deliberately structural.**
A task with a non-null `spun_off_from` may not spin off further work at
all: its `Complete.report.spun_off` entries are **not filed as tasks**,
and no new field is needed to keep them — `outcome.report` already
stores the completing run's report verbatim (§2), and `spun_off` is part
of it. The dispatcher simply declines to act on the entries.

They still reach a human, through paths that already exist rather than a
fifth projection: a `blocks_this`-shaped overflow means the run could not
finish, so the task lands in `blocked` — which §10 *does* project — and
a `follows_this`-shaped one completes normally, so the report reaches the
ticket by the ordinary route. The only thing §10's four transitions would
otherwise miss is an overflow on a task that completed cleanly, and that
one is in the report a person is already reading. That kills runaway fan-out
by *shape* rather than by budget arithmetic, which matters most in a
first version, when nobody has calibration for what normal looks like —
a depth limit is checkable at file time, whereas a total-task budget is
only violated after the fact.

The cost is real and worth naming: a genuinely layered dependency (fix
the type, then its callers, then the tests) cannot decompose itself in
one pass. It arrives at a human as a recorded observation on the
first-level task, which is the right place for it while the mechanism is
new. Depth 1 is the obvious first relaxation once there is evidence
about how often that layering actually occurs, and it needs no schema
change — only a constant.

**Authority does not travel with the record.** A task stores the
authority it was filed under; at dispatch, the ledger intersects that
with the current dispatcher's authority and uses the narrower. A task
filed by a run with broad `paths` cannot hand those `paths` to a later,
narrower dispatch. This is Workboard's rule — *"a persisted card cannot
widen a later caller's access"* — and it is the specific hazard a ledger
introduces that in-run fan-out does not have, because in-run children
inherit a live parent's authority rather than a stored one.

**Task text is untrusted.** `title` and `rationale` are model-written by
a run that read ticket text and PR comments. They reach a later run's
envelope, so they get the same sanitiser and the same tag separation as
any other untrusted content (`formats.md` §1) — and, per §8, they are
never read by anything that decides what runs next.

---

## 12. What this supersedes

**Superseded in [`future.md`](./future.md):**

- *Task splitting* — specified here as §6. The three things it named as
  prerequisites are answered: the spinoff primitive with a dependency
  relationship (§6), the approval policy (§6, as a deployment choice
  parallel to the plan gate), and what the originating run does while it
  waits (nothing — it ends). Its sequencing note stands: this wants to
  land with `context-files.md`'s narrowing, and §9's v1 slice
  deliberately ships `paths` without `kinds` for that reason.
- *A standing PR-steward loop* — the lifecycle policy questions it
  deferred ("when to give up, how to hand off to a human") are §7's
  queries and the `abandoned` state. What remains of the steward is not
  an orchestration layer at all: it is a task whose `wake` predicate is
  a PR event and whose attempts are the runs `medium.md` §1 already
  specifies. It stops being its own design pass.

**Narrowed in [`medium.md`](./medium.md):**

- *§4c, generalized task suspension.* Its instinct — "prefer being woken
  over waiting" — is now the default rather than the advice, because a
  `parked` task is cheaper than a suspended run in every case where the
  transcript does not matter. `AwaitEvent` narrows to the case §4c
  itself identifies as its real purpose: "when *this* task's accumulated
  context must survive to the other side of the event." That case is
  rarer than the section assumed, and the prompt-guidance worry it
  raises ("every long task will end in a lazy suspend") largely
  dissolves, since the lazy option now costs a fresh run rather than a
  held transcript.
- `AskUser`'s suspend/resume protocol (`formats.md` §5) is **not**
  narrowed. A question mid-investigation is exactly the case where the
  transcript must survive, and the ledger changes nothing about it.

**Not addressed here:** `future.md`'s coordinated multi-repo changes.
A ledger with dependencies is a prerequisite for it and nothing more —
lockstep ordering, atomicity of intent and cross-repo rollback are a
separate subsystem, and that item's assessment that no source in the
collection touches it is unchanged.

---

## Sources

The ledger's shape is adapted from **OpenClaw's Workboard**
([`../openclaw/workboard.md`](../openclaw/workboard.md)), the only
durable claimable work board in this collection. What was taken:
dependency promotion, the one-per-owner dispatch rule with `review`
counting as occupied, deterministic per-task run lanes, attempts as a
record-level list, diagnostics computed from stored metadata, the
recovery-without-the-token asymmetry, and the frozen-authority rule.

What was deliberately not taken: its claim tokens and agent-facing
mutation tools (§5 — our runs are dispatched, not self-claiming); its
`specify`/`decompose` tools (we have `plan` mode, `formats.md` §6); its
own card store as a tracker substitute (§10); and its worker-reported
"proof" records, which its own docs concede are "not independent
verification" and which our validator pass already improves on.

The non-model-oversight position (§8) is argued from Workboard's unwired
`orchestratorProfile`, OpenClaw's Codex-supervision spec, and the
recommends-never-executes invariant read across five of its roles —
all recorded in [`../openclaw/README.md`](../openclaw/README.md).
The self-oversight material in §8 is its session-goal feature.

Prior art in this collection for the pieces: `agent-subagent-architectures.md`
§1–§2 for the in-run layer this document does not touch, and
`agent-permissions-approval.md` for the authority rules §11 depends on.
