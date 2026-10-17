# ClawSweeper (OpenClaw's maintainer bot)

- **Type**: An autonomous repository maintainer. It reviews, closes,
  consolidates and repairs issues and PRs. A review agent plus a
  deterministic apply/merge lane, with an append-only action ledger.
- **License**: MIT
- **Source**: https://github.com/openclaw/clawsweeper
- **Retrieved from**: `main` at `7bcab82` (2026-10-17), read 2026-10-17
- **Size**: about 350,000 lines including proof artifacts. What matters
  here is `prompts/`, `instructions/`, `schema/clawsweeper-decision.schema.json`
  (1,105 lines), `src/clawsweeper-policy.ts`,
  `src/repair/exact-review-guard-labels.ts`,
  `src/clawsweeper-report-comment-helpers.ts`, and `docs/`
  (`review-authority.md`, `portable-review-receipt.md`,
  `agent-performance-metrics.md`)

The OpenClaw monorepo's [`clawsweeper` skill](../openclaw/clawsweeper-skill.md)
is the operator's view of this bot. This folder is the bot itself. It
matters to this collection because it is the most detailed public answer
to the question [`../agent-design/risk.md`](../agent-design/risk.md) asks:
**what should an agent reviewer tell a human about how much attention a
change needs, and what may automation do with that answer?**

## Files

| File | What it is |
|---|---|
| [`review-item.md`](./review-item.md) | The shared review prompt for any issue or PR: ground rules, the likely-owners hunt, the close policy, field discipline, public prose voice |
| [`review-item-pr.md`](./review-item-pr.md) | The PR section spliced into it: seven ordered passes, from product review to merge rating |
| [`review-close-reasons.md`](./review-close-reasons.md) | The closed set of close reasons |
| [`merge-policy.md`](./merge-policy.md) | `instructions/merge-policy.md`: when a merge is "safe-ish" and the `merge_preflight` proof every merge must carry |
| [`security-boundary.md`](./security-boundary.md) | What counts as security work and how it is quarantined from automation |
| [`low-signal-prs.md`](./low-signal-prs.md) | The low-signal PR close policy |

All verbatim, MIT. The JSON schema is not copied (1,105 lines); its
risk-bearing enums are tabulated below.

---

## 1. Stance: "abundant intelligence, scarce trust"

`VISION.md` states the design rule more plainly than any other source
here:

> Whenever behavior can be a model judgment with a clear prompt and an
> auditable output, prefer that over deterministic machinery. Code exists
> for the trust boundary only: authentication, idempotency, the
> append-only action ledger, spend limits, and destructive-action gates.

Everything below follows from that split. The **model decides** what a
change is, whether it is worth having, what could break, and how much
proof it has. **Code decides** who is allowed to cause what, when a
decision is too old to act on, and which labels block automation
outright. Out of scope by charter: "Merging without policy
authorization; releases; … any spend without a ledger entry." Quality
bar: "wrong closes must be revivable in one comment."

## 2. A review produces attention signals, not a verdict

A PR review returns one JSON decision. Leaving aside close/keep
bookkeeping and public prose, most of its fields exist to tell a
maintainer **what kind of attention** the PR needs. Grouped by the
question each answers:

**Should this exist at all?**
- `productReview.kind`: `bug_fix | preference | feature | refactor |
  performance | test_only | docs | maintenance`.
- `productReview.worthIt`: `yes | no | needs_maintainer`.

  The prompt puts this pass **first**, "with the most care", because
  "models write good code, product judgement is the weak point". A
  `preference` change "is never `yes` without an owner decision".

**Who must decide something?**
- `maintainerDecision.kind`: `product_direction | security_boundary |
  proof_sufficiency | release_inclusion | merge_risk | manual_review`.

  These are typed reasons a human is required, not one generic
  "needs review".

**What could merging break?**
- `mergeRiskLabels`, eight **domain-specific blast-radius** categories,
  each with a one-line definition (`src/clawsweeper-policy.ts`):
  `compatibility` (existing users, config, migrations, defaults,
  upgrades), `message-delivery`, `session-state`, `auth-provider`,
  `security-boundary` (sandboxing, authorization, credentials, sensitive
  data), `availability` (crashes, hangs, restart loops), `automation`
  (CI, automerge, proof capture, label sync), and `other`.
- `impactLabels` describe the *item's* user impact (`data-loss`,
  `crash-loop`, `ux-release-blocker`, …), not the merge's.

**What should a maintainer do about an unresolved risk?**
- `mergeRiskOptions`: 1–3 options, each categorised `fix_before_merge`,
  `accept_risk` ("when maintainers may own it") or `pause_or_close`.
  A risk is handed to a human *with the choices already laid out*.

**Is the change proven?**
- `realBehaviorProof.status`: `sufficient | missing | mock_only |
  insufficient | override`.
- `testingReview.proofPath`: `shipped_entry_point | in_process_harness |
  unit_only | none`.

**Does it override something deliberate?**
- `provenance[].verdict`: `respects | overrides_with_reason |
  overrides_without_reason | unknown`, computed from blame over the
  changed base lines and the PRs that introduced them.

**How good is it?**
- `prRating.{proofTier, patchTier, overallTier}`: `S A B C D F NA`.
  "Most PRs are B or C". `patchTier` D or F **blocks merge readiness in
  code** (`patchQualityBlocked`).

**What do the findings say?**
- `reviewFindings[]` with `priority` 0–3, each "an actual introduced
  trigger, its causal link, and the failing input and wrong result".
- `lateFinding: true` marks a concern that was already visible in an
  earlier reviewed head, and makes the reviewer admit it missed it.

`risks` is deliberately narrow: "only unresolved merge concerns none of
[the fields above] states, never a proof gap". The prompt's "one gap, one
place" rule keeps each concern in exactly one field, so a reader can
tell *kinds* of attention apart instead of reading one merged list.

## 3. The PR review procedure, in order

`review-item-pr.md` runs seven passes, and the order is the argument:

1. **Read the change**, starting with `.agents/maintainer-notes/` for the
   touched area: "maintainer decisions that stop well-intentioned
   reversions of intentional behavior". The introduced range is pinned
   (`merge-base..head`), and base drift is kept separate from the PR's
   own edits.
2. **Product review** (above).
3. **Provenance**: "Code that looks wrong often has a reason; find it
   before accepting a change to it." The host pre-blames the changed
   lines and finds each commit's PR, so the model reads *why* the old
   code was that way.
4. **Correctness**, Codex `/review` style, with typed change rules: one
   owner per decision, root cause over symptom patch, fixes in the shared
   owner, model judgement over regex, upgrade safety (changes to stored
   data models need migration proof before any pass), plugin-API changes
   flagged as `merge-risk: 🚨 compatibility`.
5. **Security**, including the **authority chain** (§4).
6. **Proof**: "Tests, harnesses, mocks, snapshots, lint, typechecks, and
   CI support proof and never replace it." For an external PR,
   real-behaviour proof gates merge unless every changed file is under
   `docs/`.
7. **Merge work and rating**: what goes in `risks`, `nextStep`,
   `mergeRiskOptions` and the tiers.

## 4. The authority chain: a risk analysis aimed at the exact thing that goes wrong

The security pass adds a section that runs **only when the diff
materially changes authority**: it "creates, persists, transfers, or
consumes an authority-bearing value that crosses a principal, account,
tenant, session, or trust boundary, can outlive or bypass the
authorization that established it, or changes which principals reach a
final side effect".

The method:

1. Follow each authority-bearing value from every producer to the
   **final effect** (network, provider, filesystem, process, queue).
2. **Invert the success claim** against "the nearest forbidden
   principal".
3. Where authority persists, check stale, revoked or reassigned
   authority, and any "queued, retried, replayed, recovered, or fallback
   decision that outlives its check".
4. "Rejection must be shown before the final effect, not only at an
   earlier layer or on the happy path."

Outcomes are tiered by how certain the risk is:
- **A concrete reachable violation** is a blocking finding.
- **A material but unproven** risk goes in `risks`, gets a merge-risk
  label, caps `patchTier` at C, and requires final-effect proof for both
  the allowed and the nearest-forbidden principal, *whatever the author's
  role*.
- **A low-impact uncertainty** gets a rank-up move and caps `patchTier`
  at B.

"Author role is no evidence about the changed surface." No other review
prompt in this collection says that as plainly.

## 5. What code enforces: labels, readiness and authority

The model's output is advisory until code acts on it. Three mechanisms:

- **Protected and blocking labels**
  (`src/repair/exact-review-guard-labels.ts`). `CLOSE_PROTECTED_LABEL_NAMES`
  covers `security`, `release-blocker`, `maintainer`, `impact:security`,
  `security-review-required`, `security-sensitive-changed`,
  `merge-risk: 🚨 security-boundary` and `needs-security-review`. Any of
  these blocks automated closing. `AUTOMERGE_BLOCKING_LABEL_NAMES` adds
  `human-review`, `manual-only`, `autogenerated`, `needs-maintainer-review`,
  `needs-product-decision` and `merge-ready`. Of the eight merge-risk
  labels, **only `security-boundary` is hard-wired into a gate**; the
  others inform maintainers and route through `mergeRiskOptions`.
- **Readiness computed from the report**
  (`pullRequestReviewReadinessFromReport`). A PR is blocked if the review
  didn't complete ("readiness is not known", never "ready"), proof is
  required and absent, `patchTier` is D or F, a maintainer decision is
  pending, or the report's head SHA, review time or review lease can't be
  validated. Every finding becomes a "needs-changes" item.
- **Merge preflight** (`merge-policy.md`). "Every merge action must
  include `merge_preflight` proving security clearance, resolved
  comments, resolved bot comments, passed Codex `/review`, addressed
  review findings, and validation commands. Missing proof blocks merge."
  Bot comments from Greptile, Codex, CodeRabbit, Copilot and others are
  named explicitly as things to resolve or block.
- **Review authority** (`docs/review-authority.md`, a classifier
  proposed but not yet wired in). Only effective repository `maintain` or
  `admin` qualifies as maintainer. "Labels and author association are not
  inputs." The PR author and the command requester are resolved
  separately: "A request from a maintainer does not change the author's
  role." Contradictory or stale evidence is `unknown`, and "A caller must
  not translate unknown into maintainer authority."

**Automerge has been retired.** The README now says the
`clawsweeper:autofix` / `automerge` labels "no longer change review
admission; they still protect an item from close proposals". The
OpenClaw-side skill captured in [`../openclaw/clawsweeper-skill.md`](../openclaw/clawsweeper-skill.md)
still describes the automerge loop, so the bot has moved past its
operator documentation. The merge gate described there (exact-head pass,
green checks, mergeable, no human-review label, two global switches) is
still the clearest statement of what an automerge would need. The bot
has stepped back from using it.

## 6. Smaller mechanisms worth knowing

- **A secret scan gates the review itself.** "Native reviews require
  host-owned TruffleHog admission before any model-backed checkout
  inspection or review." Scan errors, source drift, incomplete ancestry
  and LFS pointers **refuse** the review; nothing is "silently truncate[d]
  or bypass[ed]". A review that can't verify its input doesn't run.
- **One reviewer.** "You are the only reviewer: run no target-bundled
  autoreview helper or second reviewer, and claim none ran." A PR can't
  smuggle in a friendlier reviewer through its own repository.
- **A review receipt carries source identity only.**
  `portable-review-receipt.md` defines a small block a local review can
  attach to a PR body: repo, base, head, tool version, completion state.
  It certifies none of "body, instructions, configuration, model, policy,
  and review quality", and "grants no trusted execution claim, role,
  review exemption, or permission to bypass hosted review." `complete`
  "does not mean no findings, complete coverage, or approval."
- **Metrics refuse to become a quality score.** The agent dashboard
  measures run time, failure stages and repeated claims, and "does not
  turn claims or execution success into a correctness score". "Missing
  observations remain gaps, never zeros." The same instinct as
  CodeRabbit's "P3 is not 'looked at and fine'".
- **Security is quarantined per item, not per cluster.** A
  security-sensitive item gets a non-mutating `route_security` and
  nothing else (no close, merge, label, comment or fix PR), while
  unrelated items in the same cluster keep being processed. "False
  positives are still cheaper than accidentally routing security work
  through backlog-cleanup automation."

## 7. What this means for Forge

See [`../agent-risk-assessment.md`](../agent-risk-assessment.md) for the
cross-source view and [`../agent-design/risk.md`](../agent-design/risk.md)
§11 for what was adopted. In short:

- **Risk is typed by domain, not just tiered.** Eight merge-risk
  categories each say *what kind* of breakage to look for, and a reviewer
  who knows "session-state" knows where to look. Forge's attention
  drivers should carry a category from a repo-configurable taxonomy.
- **Hand a human options, not just a flag.** `mergeRiskOptions` turns
  "this is risky" into a choice: fix first, accept, or pause.
- **Product worth is its own attention reason**, and the one models are
  worst at. A PR can be correct, proven and low-risk and still need a
  human because nobody decided it should exist.
- **Proof is separate from correctness.** Whether the changed behaviour
  was shown running through the real entry point is its own axis. Forge's
  `failure_modes.detected_by` is the nearest thing to it.
- **Authority analysis is the high-tier lens.** A change that moves
  authority across a boundary deserves a procedure (follow to the final
  effect, invert against the nearest forbidden principal, check
  revocation), not just "the security lens looks harder".
- **Unknown is never promoted.** Not to maintainer, not to ready, not to
  low risk. This matches Guardian (`../codex/guardian-mechanics.md` §4)
  and `agent-approval-check`.
