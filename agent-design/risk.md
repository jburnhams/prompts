# Attention and risk: the review's second output

The single authority for **how much human attention a pull request
needs**, which review mode states alongside its findings and the
harness turns into a merge requirement. `review.md` owns what reaches the
model and `formats.md` owns the wire shapes. This document adds one block
to the review-mode `Complete` report (§2), one pre-fan-out step (§4), and
one harness-side gate (§6), and says how all of it is measured before it
is allowed to gate anything (§8).

Written 2026-10-17 from the pass recorded in
[`../code-review-approaches.md`](../code-review-approaches.md) §12. Read
that first for the sources; this document is the design they lead to.

---

## 1. Why a second output

Forge's review pipeline answers *what is wrong with this diff*, and
answers it well: verbatim briefs, independent validation, dedup,
convergence rules. It does not answer the question its humans actually
face at the merge button: **how carefully do I need to look at this, and
does it need someone else too?** At present a reader has to infer that
from the findings, and the findings are the wrong evidence for it:

- **No findings isn't safety.** A review that found nothing on a change
  to the authentication path should still send that change to an
  attentive human. Inferring attention from findings lowers it in exactly
  the case where the reviewer missed something. Claude Code Review, Bugbot
  and CodeRabbit all now say so in their own docs (§12, pattern 1).
- **Risk is mostly about what the change touches.** Blast radius and how
  hard it is to reverse depend on *what* the change touches: a schema
  migration, a permission check, CI configuration, a public API, the
  agent's own instructions. A bug hunt doesn't measure that.
- **The measure that matters is downstream.** Anthropic's target is the
  least human review time that doesn't increase reverts or incidents
  (§12). Findings can't be calibrated against that; a tier can.

So review mode gains a second output, the **attention block**. It is
separate from findings and computed partly without the model.

**What doesn't change:** Forge never approves, requests changes or merges
(`system-prompts.md` §2a constraints). The attention block is a statement
about the PR. Whether that statement relaxes or tightens a merge
requirement is decided by the harness's policy (§6), which an
administrator owns and the PR cannot edit.

---

## 2. The attention block

Added to the review-mode `Complete` report (`formats.md` §3b) as
`attention`:

```json
"attention": {
  "tier": "low | medium | high",
  "floor": "low | medium | high",
  "bound_to": {
    "head_sha": "string", "base_sha": "string",
    "policy_rev": "string — review-policy blob at base", "conventions_rev": "string",
    "model": "string", "prompt_rev": "string"
  },
  "drivers": [
    { "source": "path_rule | triage | finding | unverified | convergence | author_declared",
      "dimension": "blast_radius | reversibility | authority | product_worth | proof | provenance | trajectory | evidence",
      "domain": "string — one of the repo's risk domains (§11b), e.g. 'compatibility', 'data', 'auth'",
      "reason": "string — one line, e.g. 'adds a database migration'",
      "paths": ["string, ..."],
      "rule": "string — the policy rule id, for path_rule; null otherwise",
      "raises_to": "low | medium | high" }
  ],
  "required_decisions": [
    { "kind": "product_direction | security_boundary | proof_sufficiency | release_inclusion | merge_risk",
      "question": "string — the one thing a human must decide",
      "options": [ { "category": "fix_before_merge | accept_risk | pause_or_close", "action": "string" } ] }
  ],
  "effort_minutes": 0,
  "proof": {
    "status": "shown | tests_only | none | not_applicable",
    "path": "shipped_entry_point | in_process_harness | unit_only | none"
  },
  "reversibility": "flagged | revertable | hard_to_reverse",
  "look_here": [
    { "file": "string", "line": 0, "line_end": 0,
      "why": "string — what a human must judge here that the review could not" }
  ],
  "mechanical": ["string — paths whose change is mechanical (rename, generated, formatting) and needs no line-by-line read"],
  "unverified": [
    { "what": "string — e.g. 'package-lock.json elided; 3 dependency versions changed'",
      "paths": ["string, ..."] }
  ],
  "failure_modes": [
    { "what": "string", "where": "file:symbol", "trigger": "string",
      "detected_by": "string — a named test, alert or signal, or 'nothing'",
      "covered_in_this_pr": false }
  ],
  "round": 1
}
```

Field by field, with where each came from:

- **`tier`** is the only field the gate reads (§6). **`floor`** is what
  the deterministic path rules alone produced (§3a), so a reader can see
  how much the model added. The invariant `tier >= floor` is checked by
  the harness, not trusted.
- **`drivers`** list *every* reason the tier is what it is, each with
  where it came from. A tier without drivers is invalid. This is the same
  "nothing silently disappears" accounting the report already applies to
  `filtered`. CodeRabbit puts a reason on every priority for the same
  reason: an unexplained rank is one people learn to ignore.
- **`reversibility`**: `flagged` means behind a feature flag that can be
  turned off without a deploy; `hard_to_reverse` means a data or schema
  migration, a published API or wire format, a deleted resource, or an
  external side effect. Anthropic's low tier is defined partly by this
  ("additive changes behind a flag"), and its PR template asks for a
  rollback plan.
- **`look_here`** is the most useful field for a reviewer: the few line
  ranges where a human has to use judgment, each with what they're
  judging. Everything else is either `mechanical` or already covered by
  the findings. This puts into practice the shift Anthropic's
  source-control post describes, from reading every line to checking
  intent. PR-Agent's `review_priority_files` is the file-level version of
  the same idea. Ours is line-level, because Forge already holds line
  anchors.
- **`unverified`** names what the review could not check: elided files
  (`review.md` §2), a hand edit in a generated-file path, a lockfile with
  version changes, a binary, a gate stale against Head SHA. Anything in
  this list counts as a driver (§3c). An unverified change is never
  treated as a safe one.
- **`failure_modes`**, at most three, adopted almost unchanged from
  PR-Agent (§12). It asks how this would break *after merge* and **what
  would detect it**. `detected_by: "nothing"` on a `hard_to_reverse`
  change is exactly what a human should see.
- **`round`** counts review sessions on this PR (`review.md` §7). It is
  there so non-convergence can raise the tier (§3c).

The block is required on every review run except `Complete(skipped)`,
**including runs with zero findings**. That is the case the block exists
for.

---

## 3. How the tier is computed: a floor, then escalation only

Three contributors, combined with `max`. None of them can lower the tier
another one set.

### 3a. The floor: path and kind rules (deterministic, harness)

The harness evaluates a **review policy**: an ordered list of rules, each
matching changed paths or change kinds and naming a minimum tier. It is
read from **harness configuration, or the base SHA's copy of a
repository file, never the head's** (`context-files.md` §5). A rule that
would *lower* a tier, such as an exemption for docs-only paths, is
honoured only from harness configuration or from a base branch the
harness has confirmed is protected. Claude Code Review applies the same
asymmetry to `REVIEW.md`, and Bugbot to `bugbot.yaml` (§12, pattern 3). A
PR that edits the review policy file is itself a `high` driver.

Default kinds, applied before any repository rule:

| Kind | Default floor | Matched by |
|---|---|---|
| Schema/data migration | high | migration directories, `*.sql` DDL, ORM migration files |
| CI / build / deploy configuration | high | `.github/workflows/`, `bitbucket-pipelines.yml`, `Jenkinsfile`, IaC directories |
| Auth, permission and secret handling | high | repository rule (no reliable default glob, so this is the first rule a team should write) |
| The agent's own instructions | high | conventions files, review policy, prompt/skill directories, `CODEOWNERS` |
| Dependency manifest with a version change | medium | manifests and lockfiles where a version string changed, not just a hash |
| Public API / wire format | medium | repository rule (OpenAPI/proto directories by default) |
| Docs, comments and copy only | low | every changed file matches docs globs **and** the diff is comment- or string-only |

**Paths are a first-class rule input.** CodeRabbit's admin rules
deliberately cannot match file paths or CODEOWNERS (§12). For a floor
that is the wrong way round. "What the change touches" is the most
reliable risk signal there is, and paths are how a team says what it
considers sensitive. Codex's own repository did this as review prose
("highlight new individual items that can cross >1k tokens as P0. These
need an additional manual review", [`../codex/repo-review-skills.md`](../codex/repo-review-skills.md)).
A path rule says the same thing in a form the harness can check.

**Matched by touch, not by finding.** A rule fires when the change
touches its paths, whatever the review found there. That is the
difference between a floor and a severity.

### 3b. Triage: the model's read before fan-out (one cheap context)

A new pipeline step, **1½ (triage)**, between "warranted?" and context
gathering (`system-prompts.md` §2a). One small context reads the
envelope's PR block, description, changed-file list and diff, plus the
floor and its drivers. It returns a proposed tier at or above the floor,
the `reversibility`, draft `look_here` and `mechanical` lists, and
drivers for anything it raised. It does not find bugs, and it is told so.
Its only question is what a human needs to look at here and how careful
they need to be.

The triage tier **chooses the run shape** (§5). That is its main job, and
it's why triage runs before fan-out rather than after.

### 3c. Escalation after validation (orchestrator, deterministic rules)

After validation (pipeline step 5) the orchestrator applies fixed rules.
They are written in the prompt as a table, and the harness checks the
result:

| Condition | Raises tier to at least |
|---|---|
| Any confirmed `blocking` defect | medium |
| Any confirmed defect from the `security` role | high |
| Any `unverified` entry | medium |
| `reversibility: hard_to_reverse` | medium |
| `round > 3` (non-convergence) | one tier above the previous session's tier |
| A finding was withdrawn after the author disputed it (`review.md` §7b) | no change. A dispute is a conversation, not a risk signal |

The `round > 3` rule turns Anthropic's convergence finding (§12, pattern
6: a three-round cap, after which the author reconsiders the approach)
into an attention signal. A PR still producing findings on round four is
telling a human something the fifth round won't.

### 3d. What the author may declare

A Forge `implement` run's `Complete` report already carries
`risks_and_assumptions` for plan mode. Implement mode gains the same
`touches` / `reversibility` declaration, which the harness forwards into
the review envelope as `author_declared` drivers. They can **only
raise**: an author, human or agent, saying "this is low risk" is ignored,
while "this touches billing" is recorded. A coding agent may have every
reason to under-declare. A review that trusted it would be grading its
own homework.

---

## 4. Pipeline changes (multi- and single-stage alike)

Against `system-prompts.md` §2a:

1. **Step 1 (warranted?)** is unchanged. A skip still produces no
   attention block.
2. **Step 1½ (triage)** is new (§3b). The harness has already put the
   floor and its drivers in the envelope as a `<review_policy>` block,
   harness-authored, so it carries no nonce.
3. **Steps 2–6** are unchanged, except that the orchestrator's `<focus>`
   for each specialist may name the `look_here` ranges triage produced.
   Direction, not data; `review.md` §4's rule holds.
4. **Step 6½ (escalate)** is new (§3c).
5. **Step 7 (report)** adds the attention block. A report without one is
   rejected by the harness's schema check, so the run can't end without
   it.

Nothing here posts a PR comment. The agent still posts **findings only**
(`system-prompts.md` §2a step 6). The attention block reaches people
through the harness (§6), for the same reason a no-findings run posts
nothing: the agent's PR voice is reserved for claims about code.

---

## 5. The tier chooses the run shape

`review.md` §6 currently picks single-stage versus multi-stage by
"typically a changed-lines threshold". Size is the wrong axis: a
three-line change to a permission check deserves the deep pass more than
a two-thousand-line rename. Anthropic sets review depth by the cost of a
missed bug, not by size (§12, pattern 5). Replacing the threshold:

| Triage tier | Run shape | Lenses |
|---|---|---|
| low | single-stage (`all` lens) | — |
| medium | multi-stage | bugs, security, conventions (if a file is scoped), visual (if triggered) |
| high | multi-stage | as medium, plus the security lens **always** runs, and the bugs lens is sampled twice (the `medium.md` §3c double-coverage option, enabled here first) |

Size still matters, through the existing per-file and run-level budget
caps (`review.md` §2, `formats.md` §1b). Everything those caps elide goes
into `unverified`, so a large PR raises its own tier through §3c rather
than through a threshold.

---

## 6. The gate: harness policy, never the agent

The harness publishes the tier as a **commit status bound to Head SHA**
(Bitbucket build status / GitHub commit status, key `forge-attention`)
and enforces the human requirement through it. Behaviour is copied from
Anthropic's open-source
[`agent-approval-check`](../github-pr-bots/agent-approval-check) wherever
it applies:

- **Requirement by tier, set by an administrator.** The defaults below
  are the shadow-phase ones (§8). Anthropic's 0 / 1 / 2 is the target
  once calibrated.

  | Tier | Human approvals required (v1) | After calibration (§8) |
  |---|---|---|
  | low | 1 | 0 once green, for trusted authors only |
  | medium | 1 | 1 |
  | high | 2 | 2 |

- **SHA-bound.** An approval counts only for the head it was given on. A
  push re-evaluates, and approvals on the old head go stale, as with
  `/approve <sha>` in `agent-approval-check`.
- **Agents never count.** Forge's identity, and any other configured agent
  identity, is excluded from the count.
- **The prompter counts once.** For a Forge-authored PR, the person who
  filed or assigned the originating ticket is a required reviewer from
  `medium` up and counts as one approval. This is Anthropic's rule that
  the person who prompted an agent change is a required reviewer.
- **Fail closed.** A review that errored, timed out, was superseded, or
  returned no attention block leaves the status pending. **A missing
  tier means unknown, never low.** Claude Code Review's machine-readable
  output works the same way: a missing count line is "no verdict", not
  zero.
- **Sibling-SHA guard.** A status attaches to a commit, not a PR, so the
  harness withholds `success` while another open PR to a protected base
  shares that head.
- **One-way human override.** Any user with write access can raise the
  tier with a comment (`forge: human-review`). Lowering it needs an
  administrator. ClawSweeper's `stop` → `human-review` label works the
  same way (§12).
- **The status text carries `look_here`.** The status description gives
  the tier and its top driver, and links to a harness-rendered page with
  the full attention block. People reach the "where to look" list from
  the merge button, not from a PR comment.

---

## 7. Interaction with existing decisions

- **The validator stays single-question** (`formats.md` §4). It still
  judges only "is this real". It never sets severity, and it never sets
  attention.
- **Pre-existing findings stay out of scope.** Copilot now reports
  "previously missed" issues in its overview only. If Forge ever wants
  that, it belongs in the attention block's `unverified` or a sibling
  field, not as a posted finding.
- **Learnings may inform triage and may never lower the floor.** The same
  rule as for findings (`README.md` decision log, "What a learning may do
  to a finding"). A learning can teach triage that `scripts/` is
  low-stakes in this repo. Only an administrator's policy rule can make
  that a floor.
- **The conventions-file rule extends.** A diff touching a conventions
  file is already a finding, not an instruction (`context-files.md` §5).
  It is now also a `high` driver.

---

## 8. Measure before it gates: shadow, then calibrate

A tier that relaxes a human requirement is the most consequential output
anywhere in this design, so it ships in **shadow**. It is computed,
recorded and shown, but the gate (§6) uses the v1 column, where `low`
still needs a person. That follows the secure-SDLC post's rule that a new
AI reviewer runs in shadow mode until trust is established.

What has to be measured, extending `medium.md` §3e (finding-outcome
telemetry) from findings to PRs:

- **PR outcomes:** reverted within 14 days; linked to an incident;
  review rounds; human comments; time from first review to merge.
- **Resolution reasons on findings** (Copilot's *Addressed / Won't fix /
  Incorrect*, §12) where the platform has them. Otherwise inferred, as
  §3e already plans: anchored lines changed in a later commit means
  addressed, resolved without a change means won't-fix-or-incorrect. The
  inferred version is Atlassian's **code resolution rate**, the one
  production metric in the field with a published human baseline (§12,
  pattern 7).
- **The calibration test:** revert and incident rates by tier. The low
  tier earns its relaxed column only when its revert rate over a sustained
  window is no worse than the v1 baseline for comparable PRs. That makes
  Anthropic's guardrail ("without increasing reverts") an explicit
  threshold.
- **Evaluation sets** (`eval.md`): a **known-clean PR set**, scored for
  findings that shouldn't exist and for tiers that are too high; and a
  **reverts-and-incidents set**, the PRs that went wrong, scored for
  whether the tier would have been `medium` or above. Both run on every
  change to the triage prompt, the review policy defaults or the model.

---

## 9. Considered and not adopted

- **The model's risk self-report as the tier** (PR-Agent's
  `risk_level`). Adopted as an input (triage, §3b), rejected as the
  answer: one pass, defined by findings, with nothing stopping it from
  going down.
- **Rules that can't see paths** (CodeRabbit's admin rules). See §3a.
- **Risk from authorship alone** (`agent-approval-check`'s trigger). That
  gate fires on *who* wrote the change. Ours fires on *what* changed, with
  authorship coming in only through §6's prompter rule. Anthropic runs
  both internally, and the two compose. A team that wants the
  authorship gate too can run the open-source action alongside, unchanged.
- **Auto-merge.** CodeRabbit's "merge low-risk changes" rule and
  ClawSweeper's automerge are real precedents. Forge's hands-off design
  already leaves merging to the external process. Even after calibration,
  the most §6 does is drop the human requirement for `low`, and a merge
  still happens through the platform's own button or queue.
- **An actionability classifier in place of the validator.** Atlassian's
  result, a trained classifier beating an LLM judge, is the strongest new
  evidence about filtering in this pass. It needs months of labelled
  outcomes, which §8 starts collecting. Tracked in `future.md`, gated on
  that data; it would sit *after* the validator as a noise filter and
  never replace the is-it-real question.

---

## 10. Phasing

| Capability | v1 | Phase 2 | Later |
|---|---|---|---|
| Attention block in `Complete` | Required; `tier`, `floor`, `drivers`, `reversibility`, `look_here`, `mechanical`, `unverified` | + `failure_modes`, `round` | — |
| Floor (§3a) | Harness review policy with the default kinds | Repository policy file at base SHA, with the protected-base check for relaxations | — |
| Triage (§3b) | Folded into the orchestrator's step 1 reading, no separate context | Separate step 1½ context; tier picks the run shape (§5) | — |
| Escalation (§3c) | All rules except `round` | + `round > 3` (needs `review.md` §7 sessions) | — |
| Gate (§6) | Commit status, v1 column, SHA-bound, fail-closed | Prompter rule, sibling guard, human-review override | Calibrated column for `low` |
| Measurement (§8) | PR outcomes recorded | Resolution reasons; both eval sets | Actionability classifier (`future.md`) |
| Snapshot binding (§11a) | `bound_to` recorded; mismatch treated as missing | Floor recomputed on push; base policy changes invalidate open tiers | — |
| Typed drivers (§11b) | `dimension` fixed list; default domain set | Repo-defined domains in the review policy | Domains derived from mined reverts and incidents |
| Required decisions (§11c) | `product_direction`, `security_boundary` | All five kinds, with `options` | — |
| Proof axis (§11d) | `proof.path` reported | Proof rules raise tier | — |
| Authority lens (§11e) | — | Authority-chain `<focus>` on `authority` drivers | — |


---

## 11. Second pass: what Guardian and ClawSweeper changed (2026-10-17)

A deeper reading of the two most complete open-source systems
([`../codex/guardian-mechanics.md`](../codex/guardian-mechanics.md),
[`../clawsweeper/`](../clawsweeper)) and the cross-source synthesis
([`../agent-risk-assessment.md`](../agent-risk-assessment.md)) found
five gaps in the first draft. The §2 schema already includes the fields
below. The rules are here.

### 11a. A tier is bound to a snapshot, and anything unreviewed invalidates it

Guardian's cached `low` is valid only under an identical authorization
snapshot and within two tool calls, and by default any unscored action
invalidates it (`guardian-mechanics.md` §3). The first draft bound the
gate's *approvals* to a SHA but left the *tier* unbound. Now:

- `bound_to` records head, merge-base, review-policy and conventions blob
  revisions at base, model, and triage/reviewer prompt revision.
- The harness treats a tier whose `bound_to` doesn't match current state
  as **missing**, and a missing tier is `high` for gating (§6, fail
  closed). It is never a stale `low`.
- On a new push, the floor (§3a, deterministic and cheap) is recomputed
  at once. Until a review session completes against the new head, the
  status shows `max(new floor, previous tier)` and stays pending. A
  rebase that changes nothing is still a new head; only a fresh session
  can re-bind.
- A policy or conventions change on the base invalidates every open PR's
  tier the same way. That is Guardian's "authorization changed" applied
  to the rules themselves.

### 11b. Drivers are typed by dimension and by a repo-defined domain

ClawSweeper's eight merge-risk domains (compatibility, message-delivery,
session-state, auth-provider, security-boundary, availability,
automation, other) each tell a human *what kind* of breakage to look for.
A tier alone doesn't. Forge's drivers now carry:

- a **dimension** from the cross-source list (`agent-risk-assessment.md`
  §2), fixed;
- a **domain** from a **repository-defined taxonomy** in the review
  policy, each with a one-line definition the model sees. The defaults
  are `compatibility`, `data` (migrations, persisted state),
  `security-boundary`, `availability`, `automation` (CI, deploy, the
  agent's own config) and `other`.

As in ClawSweeper, **one domain is hard-wired**: any `security-boundary`
driver puts the PR at `high`, and no learning, triage or policy
relaxation can change that. The others inform the human and the options.

### 11c. Required decisions, with options, are separate from the tier

ClawSweeper separates *how risky* from *what a human must decide*
(`maintainerDecision.kind`), and hands each unresolved risk to a
maintainer with 1–3 typed options (`mergeRiskOptions`). Forge adopts
both as `required_decisions`:

- A **`product_direction`** decision is raised when triage finds a
  behaviour change the ticket didn't ask for, a new configuration
  option, default or public API inside a fix, or a reversal of
  deliberately built behaviour. ClawSweeper's rule that "a correct patch
  alone is not worth merging" carries over directly. For Forge-authored
  PRs it is aimed at the ticket's author, who is already a required
  reviewer (§6).
- A non-empty `required_decisions` makes the tier at least `medium`,
  whatever else is true. "Nobody decided this should exist" is a reason
  for a human.
- `options` follow ClawSweeper's three categories. `accept_risk` is
  offered only where an owner could reasonably own the risk.

### 11d. Proof is its own axis

ClawSweeper treats real-behaviour proof as separate from correctness:
"Tests … and CI support proof and never replace it". Forge reviews
without running anything, so it can't produce proof. It can *report*
whether proof exists:

- `proof.path` is set from what the PR shows: a run of the shipped entry
  point (attached output or screenshots, or a linked artifact), a harness,
  unit tests only, or none.
- `proof.status: none` on any `hard_to_reverse` change, or `tests_only`
  on a change with an `authority` driver, raises the tier to at least
  `medium` and adds a `proof_sufficiency` decision. The failure mode
  `failure_modes.detected_by: "nothing"` is how a reviewer argues it.

### 11e. The authority lens at high tier

When triage records an `authority` driver (the change creates, persists,
transfers or consumes something that decides *who may cause what*), the
`security` specialist's brief gains ClawSweeper's authority-chain
procedure as its `<focus>`:

1. Follow the value from every producer to its final effect.
2. Invert the success claim against the nearest forbidden principal.
3. Check stale, revoked or reassigned authority and any queued or
   replayed decision.
4. Require rejection to be shown *before* the final effect.

A concrete violation is a blocking finding. A material but unproven one
becomes a `security_boundary` decision. "Author role is no evidence about
the changed surface" applies to Forge-authored PRs in particular.

### 11f. Smaller adoptions

- **Repetition counts (Guardian's circuit breaker).** Besides `round > 3`
  (§3c), a blocking finding that reappears at the same location after its
  thread was marked fixed raises the tier one step.
- **"I missed this" is recorded (ClawSweeper's `lateFinding`).** A new
  finding on code unchanged since an earlier reviewed head is flagged as
  late in the report, and it counts against the reviewer in telemetry
  (`medium.md` §3e), not against the author.
- **Shadow comparison on live traffic (Guardian's Decisions).** During
  the shadow phase (§8), a candidate triage prompt or model can run beside
  the current one on the same envelope, recorded and never published.
  This is how a triage change gets evaluated against real PRs before it
  replaces the live one.
- **Never cut a restriction to fit.** Elide the diff before the review
  policy. A policy rule, a `human-review` label or a required decision is
  never dropped for budget, matching Guardian's "never truncate a
  restriction out of a grant".

---

## 12. Third pass: learned prediction, effort, and residual risk (2026-10-17)

From [`../agent-risk-assessment.md`](../agent-risk-assessment.md) §6–8:
Meta's DRS and RADAR, gitStream, CodeRabbit's Triage signals, Cursor
Approval Agents and CodeScene. Seven changes.

### 12a. A history-based predictor as an input, not a replacement

Meta's experience is that a model trained on which past diffs caused
incidents catches 3–5× its gating share at strict thresholds (18.7–42%
of incidents for 5–10% of diffs), and that a *logistic regression on a
dozen cheap features* got most of the way. Forge gains an optional
**`predicted` driver source**:

- **Features**, computed by the harness from git and the incident/revert
  tracker, never by the model: lines and files changed, number of
  directories, the author's prior commits to these files, each file's
  revert history and change frequency (CodeScene's hotspots), and
  **absent change coupling**, meaning files that historically change
  together where only some changed this time.
- **Output** is a percentile against the repository's own history,
  stored in the driver (`dimension: trajectory`, `reason: "riskier than
  92% of this repo's PRs"`).
- **It may only raise the tier**, like every other input (§3). Above a
  configured percentile (default P90) it raises to `medium`. A
  low-percentile prediction never lowers anything.
- **Phase:** later. It needs labels, which §8's telemetry starts
  collecting. Until a repository has a few hundred reverts it stays off,
  and the harness reports "insufficient history" rather than a number.

### 12b. Calibrate by "share of bad outcomes caught for share of PRs escalated"

Meta's metric replaces the vaguer "revert rate by tier" in §8. For each
tier boundary, report **the share of later-reverted (or incident-linked)
PRs that sat at or above it** next to **the share of all PRs at or above
it**. Escalating 20% of PRs should catch well over 20% of reverts. If it
doesn't, the tier is no better than chance, and `low` may not relax
anything (§6). This curve goes into `eval.md`'s ship log on every policy,
prompt or model change.

### 12c. The `low` tier gets RADAR's stricter definition

RADAR auto-approves only when the LLM puts **every** change in a named
safe category with confidence ≥ 8/10 and finds no risk signal. A single
risk signal sends it to a human. Forge's triage (§3b) adopts this as the
**only** route to `low`:

- **Safe categories:** behaviour-preserving refactor, dead-code removal,
  logging, formatting, docs, import cleanup, test-only additions, static
  resources, dependency patch bumps inside a lockfile-only change.
- **Every changed hunk** must be assigned to one, and the assignments are
  recorded in `mechanical`. A hunk that fits no category, or any risk
  signal (structural change, suspected bug, performance, security, high
  review effort), keeps the tier at `medium` or above.
- gitStream's `approve-safe-changes` (all formatting, docs, tests or
  images) is the deterministic version, and it is how the floor (§3a)
  reaches `low` without any model.

### 12d. Track record per agent configuration (RADAR's runbook rule)

RADAR skips per-diff review only for **vetted generators**, and holds AI
sources to a 60-day clean record, daily caps and a denylist. Forge's own
PRs come from configurations: a prompt version, a model and a task type.
The harness keeps a **per-configuration record** (reverts, incident
links, rejections, volume). Only a configuration with a clean record
above a minimum volume is eligible for the calibrated `low` relaxation
in §6. A new prompt or model version starts with no record. This
replaces the vaguer "trusted authors only" in §6.

### 12e. Effort is not risk, and residual risk is not inherent risk

- **Effort** (estimated human review minutes, gitStream-style, from
  additions and deletions by change type) is reported separately in
  `attention.effort_minutes`. It never feeds the tier. It helps humans
  plan, and an `effort_minutes` far above the PR's tier is itself a hint
  to split the PR (Codex's `code-review-change-size` lens).
- **Residual risk** (CodeRabbit's "after review" label) is what the tier
  becomes once findings exist. Forge's `floor` is the inherent risk.
  Both are already in the block (`floor`, `tier`), and the status text
  should show both when they differ: "inherent high; no blocking
  findings". Then a reviewed sensitive change is never presented as
  simply "low".

### 12f. A blast-radius graph built from evidence, never from prose

When an `authority` or `compatibility` driver is present at `high`,
`look_here` gains **downstream consumers**: the call sites, imports and
subscribers of changed symbols, found by Grep/Read, each with its source
range. CodeRabbit's rule carries over: the model may *name and summarise*
nodes that tool evidence found, and **may not add a consumer or an edge
the evidence didn't show**. A consumer outside the diff is "potentially
impacted", never a finding by itself.

### 12g. Approval policy files and the stricter rule

Cursor's `APPROVAL_POLICY.md`, resolved per directory (nearest wins,
ancestors still apply), is the user-facing shape for §3a's review
policy. Forge adopts two of its rules: **a PR that loosens a policy file
is never eligible for relaxation** (the base-branch copy applies, and a
human is required if it can't be read), and **when two policies
conflict, the stricter applies**.

| Capability | v1 | Phase 2 | Later |
|---|---|---|---|
| Calibration curve (12b) | Recorded from day one | Gates the `low` relaxation | — |
| Safe-category `low` (12c) | Deterministic floor only | Triage assignment of every hunk | — |
| Per-configuration record (12d) | Recorded | Required for relaxation | — |
| Effort, residual vs inherent (12e) | `effort_minutes`; both shown | — | — |
| Evidence-only blast radius (12f) | — | On `high` with authority/compatibility drivers | — |
| History-based predictor (12a) | — | Features computed and logged | Driver enabled once labels suffice |
