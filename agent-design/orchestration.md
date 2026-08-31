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

**Status:** §2–§8 are specified. §10 is an open deployment question.
The v1 slice is small and named in §9: one new `Complete` field and
one harness-side table.

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
      "status": "done | planned | skipped | failed | blocked | lease_lost",
      "summary": "string — the run's Complete.summary, or the failure reason" }
  ],
  "budget": { "max_attempts": 3, "max_run_seconds": 0, "attempts_used": 0 },

  "outcome": {
    "target_branch": "string | null",
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
       │   accepted                └─────────┘
       │        │
       │   ┌────▼───┐
       └──►│  done  │            parked ◄──► ready   (wake predicate)
           └────────┘            abandoned            (§7 give-up)
```

Two states differ from what a naive port of a Kanban board would give,
and both differences are ours rather than borrowed.

**`handoff`, not `review`.** This design never commits, pushes, or opens
a PR (`README.md`'s decision log). A coding run's deliverable is a
working tree plus a report, and something downstream turns that into a
commit and a PR. `handoff` is the state where that has happened and the
task is out of the agent's hands but not yet finished. It matters
because §4's concurrency rule counts it as occupied: an owner with
un-landed work should not be handed more.

**`parked` holds a task, not a run.** `medium.md` §4c's suspension
mechanism keeps a *run* alive across an event — envelope, transcript
and wake condition all preserved — because it assumed the accumulated
context had to survive. A parked task keeps only the record. When the
predicate fires, a fresh run picks it up with a fresh budget and the
previous attempt's report in its envelope. That is strictly cheaper and
it is the right default; §12 says what run-suspension narrows to.

`abandoned` is a real terminal state, distinct from `done` and from
`blocked`. A task the ledger gave up on has a recorded reason and does
not silently rot in `ready`. This is the point `future.md` deferred as
"when to give up, how to hand off to a human"; §7 makes it a query.

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
has a task in `running` *or* `handoff`. This is adapted from OpenClaw's
Workboard rule, which is expressed per agent id; we have no agent
identities, so `owner` defaults to the **(repository, ticket assignee)**
pair. Two reasons, and they are different reasons:

- *Working-tree contention.* Two `implement` runs on the same repository
  cannot share a checkout, and the design has no worktree management.
- *Reviewer attention.* The `handoff` half is the one worth arguing for:
  an assignee with an un-landed branch has a review coming back, and
  that review may itself dispatch an `implement` run against the same
  code (`medium.md` §1b). Filling their queue in the meantime
  guarantees a merge conflict with the agent's own earlier work.

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

**Approval.** `future.md` asks who approves a split. The ledger's answer:
a spun-off task is `filed`, and whether `filed → ready` needs a human is
one deployment policy, exactly parallel to the plan → implement gate
(`formats.md` §6) that this design also deliberately left open. Gated and
auto-chained are both valid; §11 caps apply either way.

---

## 7. Health without an overseer

Everything an overseer agent would notice, expressed as a query over
stored fields. All of these run against tasks nobody is executing, which
is the property that matters — a model-based supervisor can only reason
about what it is shown, and a stalled task shows nothing.

| Check | Condition | Action |
|---|---|---|
| `stranded` | `ready` and not dispatched for longer than a threshold | surface; usually an owner-concurrency stall (§4) |
| `lease_expired` | `running` with a lease past its deadline | reclaim, record `lease_lost` attempt |
| `repeated_failure` | ≥2 attempts ending `failed` | `blocked` — a human reads the attempt summaries |
| `budget_exhausted` | `attempts_used == max_attempts` | `abandoned`, with the last attempt's reason |
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

Both halves are things this design lacks. `formats.md` §7's run bounding
has the budget half (the final-turn nudge) but treats exhaustion as a
degraded completion rather than as its own outcome; and nothing anywhere
tells a hands-off run how long to persist before declaring itself
blocked, which is precisely the judgment an unsupervised run is worst at
and most consequential about. The three-consecutive-turns rule is a good
shape because it is checkable from the transcript rather than from
introspection. Both belong in `system-prompts.md` and `formats.md` §7 as
a follow-up, not here.

---

## 9. What changes elsewhere, and the v1 slice

The whole of §2–§8 is not a v1. The slice that is:

**v1 — one field and one table.**

- `formats.md` §3a: `Complete.report` gains `spun_off` (§6). Runs may
  file follow-up work; nothing else changes about how they run.
- A harness-side task table with `id`, `state`, `depends_on`,
  `spun_off_from`, `attempts`, `scope`, `owner`, `outcome`. States
  `filed` / `ready` / `running` / `handoff` / `done` / `blocked`.
- A dispatch pass implementing §4 steps 1, 3 and 5, plus the
  `budget_exhausted` and `repeated_failure` queries from §7.
- `tools.md`: no new tools. `Complete`'s description gains one sentence
  about `spun_off` and the "file, do not stretch" rule.
- `system-prompts.md`: coding mode gains the rule that work outside the
  run's `paths` is filed rather than done — which is the *first* thing
  in this design that makes "keep tasks focussed" structural instead of
  aspirational.

**Deferred within this document**, in rough order of when they will be
wanted: `parked` and wake predicates (§3), which need `medium.md` §1's
trigger sources first; the `handoff` state (§3), which needs a
downstream committer to hand off *to*; `kinds` on a spinoff (§6), which
needs `context-files.md`'s narrowing to be live; and a mid-run
`ProposeTask` tool (§6), on the trigger named there.

---

## 10. Where the ledger lives — open

The honest question this document does not settle: **is this table just
Jira with an agent-owned status field?**

The case that it is: Jira is already the task store for this deployment.
`issue_key` is already in the envelope. A parent/child link, a status,
an assignee and a comment history all exist there, are already visible
to humans, and already survive everything. Building a second store means
two places to look and a reconciliation problem.

The case that it is not: nothing in §2 outside `state`, `depends_on` and
`priority` maps onto a tracker field without abuse. A lease with a
deadline, an attempt list with run ids, a frozen `scope` with an
authority token, and per-task budgets are agent-execution state, not
project-management state, and putting them in a tracker's custom fields
is how integrations become unmaintainable. Tracker writes are also a
permission surface this design does not currently have at all — the
decision log keeps `AddComment` as the only outward channel, and
`WriteJira` is explicitly deferred to `medium.md` §5b.

**The shape that is probably right, stated as a hypothesis rather than a
decision:** the ledger owns execution state in its own store and holds
`issue_key` as a reference; the tracker stays the human-facing record and
receives *projections* — a comment when a task is filed, blocked or
abandoned — through the existing `AddComment` path. That keeps tracker
writes at their current privilege level and keeps humans looking at one
place, without pretending a lease is a Jira field. It needs a real pass
before it is settled, including what happens when a human closes the
ticket underneath a running task.

---

## 11. Safety

A ledger is the point where a hands-off system starts scheduling its own
work. Three constraints, all needed in the same pass as the feature —
`future.md` already flagged the approval question as open, and the
ledger makes it live rather than theoretical.

**Caps, enforced by the dispatcher.**

- Maximum spun-off tasks per run. A small number; the failure this
  prevents is a badly-scoped ticket fragmenting into dozens of
  fragments, each of which files more.
- Maximum spinoff *depth*: a task spun off from a task spun off from a
  task. Tracked via `spun_off_from`; past the limit, a run's spinoffs
  are recorded on the task and surfaced to a human instead of filed.
- Maximum total tasks per originating `issue_key`, which catches
  fan-out that the per-run cap misses because it is spread across
  attempts.

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
