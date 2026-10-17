# Risk assessment: deciding how much human attention an agent's work needs

A drill-down alongside
[`agent-permissions-approval.md`](./agent-permissions-approval.md) and
[`code-review-approaches.md`](./code-review-approaches.md). Those two ask
*may this action run?* and *what is wrong with this diff?*. This document
asks the question both now feed into: **how much human attention does
this piece of agent work need, from whom, and for how long does that
judgment stay true?**

Written 2026-10-17. A third pass the same day added learned risk
prediction (Meta's DRS and RADAR, §6), rule engines (gitStream, §7) and
the hosted products' risk signals (CodeRabbit, Cursor Approval Agents,
CodeScene, §8). The first two passes came from source reads of Codex Guardian
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

Five patterns, from least to most robust:

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
4. **A learned model trained on outcomes.** Meta's DRS (§6) predicts
   incident probability from the diff and its history, and gates by
   percentile threshold. It is the only pattern here with a published
   calibration curve, and the only one that needs incident or revert
   labels to exist.
5. **Two tiers with a cheap predictor gating an expensive judge.**
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

## 6. Predicting change risk from history: Meta's DRS and RADAR

*Added 2026-10-17 (third pass).* Every source above judges a change by
reading it. Meta has run the other approach for over two years: **predict
the risk of a diff from what similar diffs did in production**, and gate
on the prediction. It is the only change-risk system with published
calibration numbers, and it answers several of §7's open questions.

**Diff Risk Score (DRS).** DRS predicts whether a diff will cause a
**SEV** (a severe production incident). The labels are SEV root causes
identified by domain experts; the papers contrast this with the noisier
bug-fix-commit labels typical of academic defect prediction. SEV-causing
diffs are under 1% of all diffs. Two generations are described:

- A **logistic regression** in production for more than nine months by
  2024. It used about a dozen features chosen from roughly 100: diff size
  and spread, author experience, file criticality, prior SEVs in the file
  or folder, complexity, language. It trains in minutes on CPU and its
  features are actionable.
- **Fine-tuned LLMs** ([arXiv 2410.06351](https://arxiv.org/abs/2410.06351)).
  The best was a 13B CodeLlama variant further pre-trained on Meta's
  historical diffs ("change-aware") and then fine-tuned to emit 0 or 1,
  with the score read from those two tokens' probabilities. Its input is
  the diff title, test plan and unified diff, with no hand-built
  features. Frozen embeddings with a separate classifier did *worse* than
  the logistic regression, as did a RoBERTa model. Task fine-tuning was
  what mattered, and diff-specific pre-training added more.

**The metric is "share of incidents caught for share of diffs gated".**
Gating a random X% of diffs catches about X% of SEVs, so a model's value
is how far above that line it sits. On about 181,000 test diffs with 305
SEVs:

| Gate the riskiest… | Logistic regression catches | Best LLM catches |
|---|---|---|
| 5% (weekend gating) | 18.7% of SEVs | about 26% (1.40×) |
| 10% (medium-impact periods) | 27.9% | about 42% (1.52×) |
| 50% (high-impact periods, e.g. Black Friday) | 84.6% | about 89% (1.05×) |

On another organisation's diffs with no code overlap, the LLM caught
21.9% / 39.4% / 88.8% against the regression's 11.9% / 26.3% / 84.4%.
The model carried over to code it hadn't seen.

**How it is used.**
- **Code freezes became "code chill".** Instead of blocking every diff
  during a sensitive period, only diffs above a threshold are gated. The
  rest land. Over 10,000 diffs that a blanket freeze would have blocked
  landed during one 2024 event "with minimal production impact".
- **Gated diffs are shown in review** with the score, the reasons and
  suggested actions. The author can wait or escalate with a standard
  reason.
- **One score feeds many features.** Meta's
  [engineering post](https://engineering.fb.com/2025/08/06/developer-tools/diff-risk-score-drs-ai-risk-aware-software-development-meta/)
  counts 19 (the RADAR paper says about 20) built on a shared Risk
  Awareness Platform: build and test selection, reviewer selection for
  risky diffs, release risk, cherry-pick risk, refactoring prioritisation.

**RADAR: automatically reviewing and landing low-risk diffs.**
([arXiv 2605.30208](https://arxiv.org/abs/2605.30208).) The motivation is
the same as Anthropic's. Lines per human-landed diff grew about 106% year
on year, diffs per developer grew 51% (over 80% of that growth from
agentic AI), and the share of diffs reviewed promptly fell. RADAR is a
**layered funnel**, and a diff must pass every layer:

1. **Classify by authorship and source.** Human; deterministic codemod;
   AI codemod; operational runbook.
2. **Eligibility gates.**
   - Deterministic codemods whose *generator* was vetted skip per-diff
     review.
   - AI codemods and runbooks need per-diff checks. Runbooks also need a
     **clean 60-day track record** (no production incidents, low revert
     and rejection rates, a minimum volume), daily caps and a denylist.
   - Human authors need an eligible role, tenure and on-call membership.
     WIP, RFC, previously rejected and code-freeze diffs are excluded.
   - Open-source, SOX-scoped and extra-review code is always excluded.
3. **Static heuristics**: blocklisted code phrases and file
   prefix/suffix lists.
4. **DRS threshold, by percentile and by source.** P5 for human diffs
   (only the safest 5% are eligible), P20 for most bot sources, P50 for
   allow-listed runbooks. Organisations choose their own thresholds.
   Raising one threshold from P25 to P50 raised the approve rate to 60%.
5. **LLM review against safe and risk signal lists.** Safe: behaviour-
   preserving refactors, dead-code removal, logging, formatting, docs,
   import cleanup, test additions, static resources. Risk: high review
   effort, substantial structural change, suspected bugs, performance or
   security issues. Approval needs confidence ≥ 8/10 **and every change in
   a safe category**. Any risk signal sends the diff to a human.
6. **Deterministic validation**: CI state, caps, landing windows.
7. **Land after a delay**, during which a human reviewer can still reject
   it. The author keeps the choice to ship on the RADAR approval, wait for
   a human, or put the diff back to "Needs Review".

Results over 535,000+ reviewed and 331,000+ landed diffs: reverts about a
third of the non-RADAR rate, production incidents about a fiftieth, and
median review wall time down 35%. The comparison is observational with
difference-in-differences, and the populations aren't random (RADAR
diffs are pre-selected to be low-risk). The authors note two further
things: none of the incidents that did occur would have been caught by a
human reviewer, and automating review may cost knowledge transfer.

**What carries over to a smaller team.**
- **The evaluation metric**, "share of bad outcomes (reverts, or follow-up fixes where a team fixes forward) caught for
  share of PRs given extra attention", is the right calibration test for
  any tier. It needs nothing more than outcome labels on
  past PRs.
- **The feature set** (size, spread, author experience with *this* code,
  file criticality, prior incidents in these files, complexity) is cheap
  to compute from git and an incident tracker. An open-source replication,
  [DRS-OSS](https://arxiv.org/abs/2511.21964) (Llama 3.1 8B fine-tuned on
  the public ApacheJIT defect dataset, MIT,
  [repo](https://github.com/Ali-Sayed-Salehi/drs-llm)), reports ROC-AUC
  0.895. Flagging its riskiest 30% catches 86% of defect-inducing
  commits, and it ships as a GitHub app.
- **Different thresholds by source** (P5 for humans, P50 for proven
  runbooks) is a precise version of "trust depends on who or what wrote
  it", earned through a track record rather than declared.
- **Per-diff review is skipped only for vetted generators.** For an
  agent-written PR, the comparable thing would be an agent configuration
  (prompt, model, task type) with a measured clean history.

## 7. Rule engines: gitStream

[gitStream](https://github.com/linear-b/gitstream) (LinearB,
Apache-2.0) is the purely deterministic end: per-repo `.cm` YAML/Jinja
rules that label, route, require approvals and **auto-approve**. Its
automation library is a catalogue of what teams treat as "safe" and
"needs more":

- `approve-safe-changes`: approve when every change is formatting only,
  or every file is docs, tests or images.
- `review_sensitive_files`: any match against a path list adds the
  security team and sets required approvals to 2.
- `additional_review_for_large_pr`: estimated review time ≥ 30 minutes
  *and* ≥ 10 files *and* touching `src/` → 2 approvals.
- `provide_estimated_time_to_review` labels every PR with an **estimated
  review time** in minutes (green < 5, yellow < 20, red ≥ 20). The
  estimate comes from a hosted ML model over additions and deletions *by
  type of change* (code, data, configuration) plus PR metadata.

The point is not the rules themselves, which are simple. **Review effort
is a different quantity from risk**, and gitStream, CodeRabbit (§8),
PR-Agent and RADAR's risk signals all estimate it separately. A
five-minute change can be high risk, and an hour-long one can be safe.

## 8. Hosted products: what is shown and what is hidden

**CodeRabbit Triage cards** (`docs.coderabbit.ai/triage/your-triage-view`)
show separate signals, each tied to the reviewed commit:

| Signal | Values | On a new push |
|---|---|---|
| Change type | Bugfix / Feature / Refactor | hidden until re-reviewed |
| Review guidance | Quick / Standard / Deep / **Review later** | kept |
| Risk (**residual**, after CodeRabbit's review) | Low / Medium / High / **Unknown** ("not that the risk is low") | kept |
| Security risk | Minimal → Critical (with the security product) | hidden until re-reviewed |
| Blast radius | Low / Medium / High | hidden until re-reviewed |
| Issue severity | High / Medium / Low, "not an overall risk judgment" | hidden until re-reviewed |
| Review effort | Low / Medium / High, with a percentage on hover | kept |

- **Residual versus inherent risk.** CodeRabbit labels its risk as what
  is *left* after its review. That is a different quantity from Forge's
  floor (§3 of `risk.md`), which is about what the change touches before
  anyone has looked. Both are worth showing, and conflating them is how
  a reviewed sensitive change ends up looking "low".
- **Blast radius is a graph built from evidence first.** Changed
  components, upstream dependencies, downstream consumers ("potentially
  impacted", possibly outside the diff), related tests, supporting
  context, joined by typed edges (call, import, read, write, publish,
  subscribe, test), each with confidence and source ranges. The generated
  names and summaries come afterwards and "cannot add unsupported
  components, connections, or relationship directions". The graph is
  capped ("Showing N of M"). How it becomes Low/Medium/High is not
  published.
- **Some signals survive a push and some don't.** Effort, guidance and
  residual risk are kept across pushes; severity, blast radius and
  security risk are hidden until a re-review. That is a partial version
  of Guardian-style binding (§4), applied per signal.

**Cursor Approval Agents** (`cursor.com/docs/approval-agents`) are the
auto-approve product most like Forge's §6 gate:
- An optional **risk score** with a **maximum risk threshold** for
  approval.
- Bugbot and Security Agent findings count as inputs, and any finding
  needing human review blocks approval.
- **`APPROVAL_POLICY.md` files resolved per directory** (nearest file
  wins, ancestors still apply), plus a routing file mapping product areas
  to policies.
- It **never approves a PR that changes the approval policies themselves
  to loosen them**. It reads the base-branch version, and requires a human
  if that can't be determined.
- On a policy conflict, "the stricter instruction".
- Reviewers are routed by ownership and commit history.

Risk levels and criteria are undocumented. GitHub's rule that the same
actor can't both create and approve a PR stops it approving PRs made by
other Cursor automations, which is accidental but useful separation of
duties.

**CodeScene delta analysis** scores a change set against the repository's
own risk profile. It flags PRs touching top-ranked **hotspots** (files
with high change frequency and low code health) and warns on **absent
change coupling**: files that historically change together, where only
one changed this time. That second check is a risk signal no LLM reviewer
in this collection uses, and it comes straight from git history.

## 9. Open questions

- **Calibration.** *(Partly answered by the third pass.)* Meta publishes
  incident capture against share of diffs gated (§6), which is the only
  real calibration curve in the field. Everyone else still publishes
  nothing on how often a level was later wrong. Guardian's Decisions
  shadow and Anthropic's guardrail are measurement *designs*. Atlassian's
  code-resolution rate measures findings, not risk. What remains open is
  whether a smaller organisation has enough incidents to train or even
  validate a model: Meta's test set had 305 SEVs in 181,000 diffs. Reverts
  are more frequent, but a team that fixes forward hardly ever reverts.
  The practical label there is the **follow-up fix**, found SZZ-style by
  blaming fix-intent changes back to the PRs that introduced the lines
  (`agent-design/risk.md` §8a).
- **Reading versus predicting.** Meta's best-performing system *predicts*
  from history and then has an LLM *read* the diff against safe and risk
  signal lists (RADAR). Every other source only reads. Nobody has
  published a comparison of the two on the same PRs, or of the
  combination against either alone.
- **How much to trust a model's "low".** Guardian lets a cheap `low`
  approve within strict binding. ClawSweeper retired automerge entirely.
  Anthropic merges low-tier PRs without humans. The field hasn't settled
  this.
- **Domain taxonomies don't transfer.** ClawSweeper's eight categories
  fit a messaging gateway (`message-delivery`, `session-state`). Every
  deployment needs its own list, and none of the sources says how to
  derive one. The best candidate is mining past follow-up fixes and incidents by
  category, which is also what §8 of `risk.md` proposes to collect.
