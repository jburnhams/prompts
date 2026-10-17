# Risk assessment: deciding how much human attention an agent's work needs

A drill-down alongside
[`agent-permissions-approval.md`](./agent-permissions-approval.md) and
[`code-review-approaches.md`](./code-review-approaches.md). Those two ask
*may this action run?* and *what is wrong with this diff?*. This document
asks the question both now feed into: **how much human attention does
this piece of agent work need, from whom, and for how long does that
judgment stay true?**

Written 2026-10-17 from source reads of Codex Guardian
([`codex/guardian-mechanics.md`](./codex/guardian-mechanics.md)),
ClawSweeper ([`clawsweeper/`](./clawsweeper)), Anthropic's
`agent-approval-check` and `pr-stamp-sweep`
([`github-pr-bots/agent-approval-check/`](./github-pr-bots/agent-approval-check)),
PR-Agent's assessment fields ([`pr-agent/`](./pr-agent)), and the hosted
services in `code-review-approaches.md` §12. The design that follows from
it is [`agent-design/risk.md`](./agent-design/risk.md).

---

## 1. Two granularities, one problem

| | Action risk | Change risk |
|---|---|---|
| Unit | One tool call: a command, patch, MCP call, click | One PR / merge |
| When decided | Before the action runs, often in seconds | Before merge, in minutes |
| Who acts on the answer | The harness: allow, or ask the user now | A merge gate: how many humans, which ones |
| Sources here | Codex Guardian, Claude Code's auto-mode classifier, OpenClaw's exec auto-reviewer (`agent-permissions-approval.md` §2–2b) | Anthropic's internal tiers, `agent-approval-check`, ClawSweeper, PR-Agent, Bugbot, CodeRabbit Triage |
| Typical output | allow / deny / ask, with risk and authorization levels | a tier, labels, required approvers, options |

They are the same problem at different time scales. The action-risk
systems are older and much more mechanised, and a PR-level design should
borrow from them most. The clearest example is Guardian's rule that a
`low` is valid only under the exact authorization snapshot it was
computed in (§4). Its PR-level equivalent is barely mentioned anywhere.

## 2. The dimensions sources actually assess

Collected from every source that writes them down. A source may combine
several of these into one score; listing them separately is what makes a
risk output explainable.

| Dimension | Question | Where it is explicit |
|---|---|---|
| **Intrinsic risk / blast radius** | If this is wrong, how much breaks and for whom? | Guardian's base taxonomy (low → critical, "meaningful but bounded blast radius"); ClawSweeper's eight merge-risk domains; CodeRabbit's "blast radius" fact |
| **Reversibility** | Can it be undone cheaply? | Guardian's "easy-to-reverse" / "costly-to-reverse"; Anthropic's "additive changes behind a flag"; ClawSweeper's upgrade-safety and data-model rules |
| **Authorization** | Did someone with standing ask for this, specifically? | Guardian's `user_authorization` (high / medium / low / unknown, "unknown" meaning drift or untrusted content); ClawSweeper's `maintainerDecision`; `agent-approval-check`'s prompter `/approve` |
| **Authority movement** | Does it change *who can cause what*? | ClawSweeper's authority chain; Guardian's computer-use rules on granting or expanding permissions |
| **Product worth** | Should this exist at all? | ClawSweeper's `productReview.worthIt`, run first "with the most care"; Anthropic "whether to build something" stays human |
| **Proof** | Has the changed behaviour been shown working, through the real entry point? | ClawSweeper's `realBehaviorProof` / `proofPath`; PR-Agent's `failure_modes.detected_by`; Anthropic's PR template asks for testing details and a rollback plan |
| **Provenance of intent** | Does it override something someone did on purpose? | ClawSweeper's `provenance` verdicts and maintainer notes; Forge's discussion rules (`agent-design/review.md` §4) |
| **Trajectory** | Where is this sequence of work heading? | Guardian's predictive classification (last 5 actions, next 2); the circuit breaker; Anthropic's three-round convergence cap |
| **Evidence completeness** | What could the assessor *not* see? | Guardian's truncation rules ("missing context should make you more cautious"); Bugbot's "not clean if all findings were filtered"; Forge's `unverified` |

No source uses all nine. The most common failure, visible in PR-Agent's
`risk_level` and in most findings-only bots, is **collapsing all of them
into "how bad are the bugs I found"**. That assesses only the first
dimension, and only for problems the reviewer happened to find.

## 3. Who sets the level

Four patterns, from least to most robust:

1. **Model self-report.** One pass returns a level (PR-Agent's
   `risk_level`, Bugbot's `riskScore`). Cheap and explainable, but it can
   go down as easily as up, and it inherits the reviewer's blind spots.
2. **Deterministic rules on what was touched.** Paths, kinds, authorship
   (`agent-approval-check` triggers on agent commits; Codex's removed repo
   skill escalated any new >1k-token context item). Can't be talked
   down, but can't see meaning.
3. **A floor plus escalate-only judgment.** Rules set a minimum and
   models can only raise it. Anthropic: a classifier plus "a second
   classifier can escalate". Guardian: unknown modes keep synchronous
   review, and failures publish maximum risk.
4. **Two tiers with a cheap predictor gating an expensive judge.**
   Guardian's async scorer decides whether the expensive reviewer runs at
   all, and either tier can release the action, but only under identical
   evidence binding. `pr-stamp-sweep` is the PR-level version: a reviewer
   recommends, and an adversarial verifier runs **only on the "less
   attention" recommendations**, because sending something to a human is
   already safe.

## 4. Mechanisms that recur across sources

**Binding: a judgment is valid only for what it judged.**
- Guardian binds a cached score to an authorization snapshot (permissions,
  settings, environments, instruction versions, model) and to a lag of at
  most 2 tool calls. Any unscored action invalidates it by default.
- `agent-approval-check` binds approvals to a head SHA, and a stale
  `/approve` is flagged.
- ClawSweeper validates the report's head SHA and review lease before
  computing readiness, and automerge required "the exact current head".
- Claude Code Review re-reviews on push. CodeRabbit removes a stale
  finding's severity contribution when a new commit arrives "until
  current evidence exists".

**Fail closed, and keep "unknown" separate from "low".**
- Guardian: "No contributor is never an implicit allow"; a failed score
  is 1.0.
- ClawSweeper: an incomplete review means "readiness is not known";
  `unknown` authority is never maintainer.
- `agent-approval-check`: errors leave the status pending, and more than
  100 commits counts as agent-authored.
- Claude Code Review: a missing severity line means "no verdict".
- CodeRabbit: P3 on an unreviewed PR means no signal raised it, not that
  it was checked.

**Asymmetric authority to relax.**
- Claude Code Review honours scope-reducing `REVIEW.md` rules only from a
  protected branch.
- Bugbot's repo file "can lower Autofix but never turn it on".
- ClawSweeper's `stop` comment adds `human-review`, while removing it
  needs a maintainer and an open gate.
- Guardian's managed `extra_policy` beats a local one.

**Protected categories that automation can't touch.**
- ClawSweeper routes security-sensitive items to a non-mutating
  `route_security` and keeps a protected-label list.
- Greptile never suppresses security findings.
- `pr-stamp-sweep` defines `securitySensitive` by touched surface.
- Guardian's cyber-specialty models trip the circuit breaker on the first
  denial.

**Never cut a restriction to fit a budget.**
- Guardian: required action evidence is never truncated, and restrictions
  are never truncated out of a grant.
- ClawSweeper: a secret scan that can't complete refuses the review rather
  than truncating its input.

**Measure in shadow first, and count every fallback.**
- Guardian's Decisions classifier runs on live traffic and gates nothing,
  and every fast-path fallback is a named metric.
- Anthropic's secure-SDLC post: new AI reviewers run in shadow until
  trusted, and a risk-weighted sample of automated approvals is
  re-reviewed by humans.
- ClawSweeper's metrics keep missing data as gaps, never zeros, and never
  turn execution success into a correctness score.

**Repetition is itself a signal.**
- Guardian's circuit breaker: 3 consecutive or 10 of 50 denials.
- Anthropic's three-round cap.
- ClawSweeper's repair caps (10 per PR, 1 per head) and `lateFinding`.

## 5. What a risk output should contain

Combining the above, a complete answer to "how much attention" has:

1. **A level**, valid for one exact snapshot (`tier` + `bound_to`).
2. **Typed reasons**: a dimension (§2) and a domain category for each
   (ClawSweeper's merge-risk domains, made repo-configurable).
3. **Who must decide what**: typed required decisions
   (`product_direction`, `security_boundary`, `proof_sufficiency`,
   `release_inclusion`, `merge_risk`), not just a count of approvals.
4. **Where to look**: line ranges plus what to judge there, and what is
   mechanical.
5. **What could not be checked**: evidence gaps, each raising the level.
6. **Options for each unresolved risk**: fix before merge / accept /
   pause or close.
7. **How a failure would surface**: detection per failure mode, and
   whether this change adds or proves that detection.

PR-Agent covers 1, 4 (files only) and 7. ClawSweeper covers 2, 3, 6 and
most of 5 and 7, but has no single level. Anthropic's internal system
(from the outside) covers 1 and a version of 3. No source covers all
seven, which is what `agent-design/risk.md` §11 attempts.

## 6. Open questions

- **Calibration.** Nobody publishes how often each level was later
  wrong. Guardian's Decisions shadow and Anthropic's guardrail ("without
  increasing reverts or incidents") are the only measurement designs
  stated. Atlassian's code-resolution rate is the only published
  production metric, and it measures findings, not risk.
- **How much to trust a model's "low".** Guardian lets a cheap `low`
  approve within strict binding. ClawSweeper retired automerge entirely.
  Anthropic merges low-tier PRs without humans. The field hasn't settled
  this.
- **Domain taxonomies don't transfer.** ClawSweeper's eight categories
  fit a messaging gateway (`message-delivery`, `session-state`). Every
  deployment needs its own list, and none of the sources says how to
  derive one. The best candidate is mining past reverts and incidents by
  category, which is also what §8 of `risk.md` proposes to collect.
