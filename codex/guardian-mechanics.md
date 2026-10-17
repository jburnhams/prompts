# Guardian: the machinery around the prompts

- **Source**: `github.com/openai/codex` (Apache-2.0) at `ce0323f2f2`
  (2026-10-17)
- **Read**: 2026-10-17, as source, about 18,000 lines across
  `codex-rs/ext/guardian-v2/src/async_scorer/` (the classifier),
  `codex-rs/ext/guardian-reviewer/src/` (the synchronous reviewer's policy),
  `codex-rs/core/src/guardian/` (the host adapter),
  `codex-rs/guardian-context/src/` (evidence assembly),
  `codex-rs/protocol/src/openai_models/guardian.rs` (the per-model policy)
  and `codex-rs/prompts/templates/guardian/` (the prompts)

[`guardian-policy.md`](./guardian-policy.md),
[`guardian-v2-classifier.md`](./guardian-v2-classifier.md) and the new
[`guardian-classifier-default.md`](./guardian-classifier-default.md) hold
the prompts. [`README.md`](./README.md#guardian-in-two-tiers) and
[`../agent-permissions-approval.md`](../agent-permissions-approval.md) §2b
describe what the two models are asked. This document covers what the
prompts don't: **when** each model runs, **what evidence** it gets, **how
long** a verdict stays valid, and **what happens** when anything is
missing. The prompts take up about 300 lines; the code that decides
whether they get used at all takes up the rest.

It is the most complete open-source implementation of risk-gated
autonomy in this collection. Its unit is one agent *action* (a command,
a patch, an MCP call, a browser click), not a pull request, but nearly
every mechanism has a PR-level counterpart. §9 maps them.

---

## 1. Coverage: which actions a model's policy puts under review

Coverage is set **per model**, in the model catalog, as a
`GuardianModelPolicy`. It is not a single global switch. The policy has
one entry per *approval scope*:

| Scope | What it covers |
|---|---|
| `shell` | `exec_command`, `write_stdin` |
| `file_changes` | `apply_patch` |
| `mcp` | MCP tool calls; scope chosen from server and connector identity |
| `network` | network-access approvals |
| `permissions` | `request_permissions`, the model asking for wider grants |
| `computer_use` | `node_repl` / `cua_repl` / the Browser connector |
| `other_tools` | anything without an approval category |

Each scope takes a `GuardianReviewMode`:

- `Disabled`: no review; the request goes to the user.
- `Synchronous`: always run the expensive reviewer.
- `Adaptive`: "Use a current low-risk score; otherwise run synchronous
  review."
- `Unknown`: a future value this client doesn't understand. It "retain[s]
  synchronous review and never enable[s] the fast path".

Three defaults are worth noticing:

- **"Omitted scopes are disabled; unknown fields are ignored."** Leaving a
  scope out of the policy is a decision, not an accident.
- **An unrecognised mode fails towards more review**, never towards the
  fast path.
- **`sandboxed_exec_commands`** decides whether adaptive shell coverage
  scores *every* sandboxed command, or only the ones asking for
  `sandbox_permissions: "require_escalated"`. With it off, the classifier
  watches only the commands trying to leave the sandbox, and the sandbox
  itself contains the rest. Coverage is matched to where the existing
  defence ends.

There is one more knob: what an **unscored action** (one outside adaptive
coverage) does to the cached score. `GuardianUnscoredAction` is `Ignore`,
`AgeScore` or `InvalidateScore`, and the default is **`InvalidateScore`**.
Anything the classifier didn't see counts as possibly having changed the
situation.

## 2. The async scorer: a binary bet, published under a lock

The classifier ("Luna" in the code, a separate model with its own budget)
runs **in the background** as tool calls are observed. Its request has no
tools. The prompt ends: "Your first output token is the entire
classification: `high` for high risk or `low` for low risk."

- **The score is binary.** `classification.rs` maps `"high"` → `1.0` and
  `"low"` → `0.0`. The comparison threshold is `0.5` (`0.8` for legacy
  configurations, and only if the configuration's owner supplies one).
  There is no calibrated probability, so the threshold exists only to
  accept future fractional scores.
- **Failure publishes maximum risk.** `fail_closed` writes
  `action_risk = 1.0`, and "Failures win timestamp ties; successful
  samples must be strictly newer." A late success can never overwrite a
  failure from the same instant.
- **Only newer samples replace older ones.** Scores, the authorization
  snapshot they were computed under (§4), and coverage are published
  together under one lock, so a reader never sees a score paired with
  someone else's authorization.
- **Concurrency is bounded and the newest work wins.** Classifications
  fork the latest completed classifier conversation. When at capacity,
  admission "retains the newest requests and cancels the oldest". A
  classification that falls outside every active action's lag allowance
  (§3) is cancelled as *superseded*, not failed, so it doesn't count as
  a fail-closed event.

The default prompt for this tier
([`guardian-classifier-default.md`](./guardian-classifier-default.md),
82 lines; the gpt-6-astra catalog ships a shorter override) has two
sections the September capture didn't have:

- **A base risk taxonomy** with explicit *non*-reasons. Don't call
  something high "solely because a path is outside the writable workspace
  roots". Don't call `rm -rf` of a user-requested specific path high
  "solely because it uses `rm -rf`". "Sandbox retry or escalation after
  an initial sandbox denial is not suspicious by itself." These are the
  over-escalation mistakes a cautious classifier tends to make, named so
  it stops making them.
- **Predictive consequence classification.** Return `high` if:
  - the current course has `unknown` or `low` authorization, or `high` or
    `critical` risk;
  - anything in the last 5 actions had `unknown` authorization or
    `critical` risk;
  - a `high` or `critical` action is credible within the next 2 actions;
  - "You are unsure".

  "Classifying the risk as low clears the risk and allows the next tool
  calls to run without blocking review."

## 3. The fast path: when a cached `low` may approve an action

`approval.rs`' `cached_evidence` is the core of Guardian. An action in an
`Adaptive` scope is approved **without** the synchronous reviewer only if
*every* one of these holds. Each failure has its own named
`GuardianReviewReason`, recorded as a metric.

| Condition | Fallback reason if it fails |
|---|---|
| A score exists | `MissingScore` |
| The action, rendered, fits `max_action_tokens`, and no active call was marked oversized | `ScoringFailure` |
| The parent conversation's compaction checkpoint is compatible with the classifier model | `IncompatibleCompaction` |
| Permission evidence resolved | `AuthorizationChanged` |
| The retained user instructions are complete (nothing evicted) | `Policy` |
| **Lag ≤ `max_tool_call_lag` (default 2)**: no more than 2 tool calls since the score's source | `StaleScore` |
| No tool call failed or overflowed after the latest score | `ScoringFailure` |
| `action_risk < review_threshold` | `ElevatedRisk` (≥ threshold) / `InvalidScore` |
| **The authorization snapshot is identical** to the one the score was computed under | `AuthorizationChanged` |
| For a tool-linked approval, the score was sampled at or *before* this action, never from a later one | `MissingScore` |

The **authorization snapshot** (`ScoreAuthorization`) is the subtle part.
A cached score is bound to: the permission context; thread settings;
selected environments; the local authorization version; the review-context
revision; the root conversation's authorization version and revision (for
sub-agents); and **the model**. If any of these changes (a new user
message, a permission grant or revocation, a model switch, a different
target environment), the `low` from a moment ago no longer counts. In
the module's own words: it "Binds cached scores to the user authorization,
review context, and model policy they evaluated."

Two smaller rules:

- **Code Mode wrappers get a lag discount.** A JavaScript wrapper that
  issues nested tool calls would otherwise make the wrapper and its
  children each spend lag. `wrapper_lag.rs` discounts "an approval's own
  unscored code-mode wrapper", and "Missing provenance keeps the full
  lag".
- **Computer use gets one free first call.** With `initial_cua_call`,
  the very first JS execution of a node-REPL connector is approved
  without a score, because there is nothing yet to classify.

### The race between the two tiers

When the fast path fails, the synchronous reviewer starts. Meanwhile the
host **keeps watching the score channel**. If the async score arrives,
passes every check above, and was sampled at or before the action, it
**releases the pending synchronous review** and the action proceeds.
Whichever tier says "safe" first, under the same evidence rules, wins.
A "high" from the async tier never cancels a synchronous review.

## 4. Routing: who gets asked, and the meaning of "no answer"

`decide_request` in order:

1. `full_access` → allow (the user turned approvals off entirely).
2. The user chose to review themselves, or the approval policy isn't
   `OnRequest`/`Granular` → **ask the user**, unless the action carries
   `require_guardian` (a host-mandated review the user can't skip).
3. The scope is `Disabled` and the action isn't host-mandated → ask the
   user.
4. `require_fresh_review` → skip the cache and go straight to synchronous
   review (`FreshRequired`).
5. Otherwise run the fast path (§3), then synchronous review.

If the synchronous reviewer returns nothing, the decision is `AskUser`.
`decision.rs` states it as "`None` requests the existing user flow. No
contributor is never an implicit allow." Every path that isn't a positive
verdict ends at a human.

`StrictReviewRequiredNotification` (app-server protocol, added
2026-08-18) is the UI's view of the `require_guardian` path: the client
is told a review is mandatory and when it started.

## 5. Evidence: what the reviewers see, and what is never cut

`codex-rs/guardian-context/` (5,000 lines) builds the evidence for both
tiers. Its rules are a specification of **what a risk reviewer must not
lose**:

- **"Required action evidence is never truncated."** The action under
  review is always whole. Optional evidence goes first when the budget
  is tight. "Every reduction reserves an omission notice and preserves
  source order."
- **Restrictions are atomic.** Retained instructions: "restrictions are
  never truncated into partial permissions". Verified answers: "Omit a
  record atomically when it cannot fit; never truncate a restriction out
  of a grant." A half-kept "you may delete files *except*…" is worse than
  dropping it, so either the whole record goes or none of it does.
- **The user's instructions survive compaction.** `history.rs` keeps
  "bounded, chronological review evidence independent of the parent's
  compaction". User messages have their own limit, separate from
  everything else, and when non-user entries overflow, "the oldest half"
  is dropped. The reviewer still sees what the user said even after the
  agent's own context has been summarised.
- **The two consumers use different retention.** Sync "keeps recent
  entries". Async "protects approvals/final answers and evicts in
  cacheable chunks", so the classifier's prompt prefix stays
  cache-stable across many cheap calls.
- **Host attestations go after the transcript.** "Action-specific
  attestations follow the transcript so they do not invalidate the
  reusable history prefix when previous decisions or tool evidence
  change." The trusted parts (verified skill paths, trusted MCP tool
  sources, prior-review records the host vouches for) are placed so they
  don't break caching.
- **Prior reviews are evidence, attested and bounded.** `reviews.rs`:
  "The host selects authorization-valid records and attests each
  rendered body." The tenant policy's line "Prior Guardian decisions are
  context, not precedent" is enforced here: only records still valid
  under the current authorization are shown.

### What changed in September–October

- **The reviewer can fetch what the transcript dropped** (#49036, opt-in).
  `user_message.search_messages` / `read_messages` over the parent's live
  connection. Policy is rechecked per call; output is capped at about
  4,000 tokens; the reviewer is told to separate user authorization from
  assistant context and to look for later revocations.
- **Sub-agent actions are judged under the handoff that authorised them**
  (#49057, opt-in). The reviewer sees the root-conversation messages
  around each `spawn_agent` / `send_message` / `followup_task` that
  reached this worker or its ancestors, plus the latest three "so recent
  cancellations remain visible".
- **Reviews are bound to the target environment** (#47630), so a remote
  action isn't judged under the local machine's denied-read rules.
- **`extra_policy`** (#47125): an administrator can append policy text to
  the tenant policy, and a managed (organisation-enforced) value overrides
  a local one.
- **Decisions comparison** (#50099, #50273). An optional second
  classifier ("Decisions") runs on the same evidence purely for
  measurement. Its result is recorded "after baseline publication" and
  never gates anything. It is a shadow evaluation of a candidate
  classifier on live traffic.

## 6. The synchronous reviewer: a pooled agent with a deadline

- **One reusable reviewer per parent thread, with forks for concurrent
  reviews** (`pool.rs`). "Concurrent reviews fork committed context", so
  two pending approvals don't contaminate each other's transcripts.
- **Ninety-second deadline covering setup**, with one fresh attempt
  allowed if a checkpoint can't be recovered, "under the original review
  deadline".
- **Read-only tools** (`settings.rs`): it can inspect local state, but
  only "when they would flip an allow/deny decision" (the prompt's rule).
- **Failed reviews are kept for opt-in feedback** (`feedback.rs`), with
  bounded records that outlive the reviewer session. Errors become
  training and debugging material instead of disappearing.

## 7. The circuit breaker: a denial count is itself a risk signal

`circuit_breaker.rs`, per turn:

| Policy | Consecutive denials to interrupt | Denials in last 50 reviews to interrupt |
|---|---|---|
| Standard model | 3 | 10 |
| `model_specialty: cyber` | 1 | 1 |

Any non-denial resets the consecutive count. The breaker trips once per
turn, and the host interrupts only the turn that is still active. The
idea underneath: **an agent that keeps proposing actions a reviewer
denies is itself evidence of risk**, whatever the individual actions
were, and grinding through more reviews doesn't reduce that risk.

## 8. Metrics: every fallback has a name

`record_fast_decision(metrics, outcome, label)` is called on every path:
`approved/low_risk`, `approved/initial_cua_call`, and `deferred/` with
`stale_score`, `missing_score`, `scoring_failure`,
`authorization_changed`, `elevated_risk`, `incomplete_authorization`,
`incompatible_compaction`, `out_of_scope`, `permission_resolution_error`.
A tool-call-lag histogram is emitted on every check. Since 0.161 (2026-10)
skill invocations, denial-limit interruptions and total decision duration
are exported too. The result is that "why did a human get asked" is
always a countable answer.

---

## 9. What this means for PR-level risk

Guardian judges actions; a PR review judges a change. The mechanisms
carry over almost one-for-one, and most of them are missing from
[`../agent-design/risk.md`](../agent-design/risk.md)'s first draft:

| Guardian | PR-level counterpart |
|---|---|
| Per-scope coverage, omitted = disabled, unknown → stricter | Per-path-kind policy; an unrecognised kind gets the default floor, never the lowest |
| `sandboxed_exec_commands`: classify only what leaves the sandbox | Spend review depth where existing defences end: CI-covered behaviour versus paths CI doesn't exercise |
| Binary score, failure = max risk, failures win ties | A missing or failed tier is `high` for gating, never "unknown so default low" |
| **Score bound to an authorization snapshot** (permissions, settings, environments, instruction versions, model) | **Tier bound to a review snapshot**: head SHA, merge-base, review-policy revision, conventions revision, model, prompt version. Any change invalidates the tier |
| Lag ≤ 2 tool calls | A tier is valid for its exact head only. Even a docs-only push re-evaluates the floor (cheap) before the old tier is reused |
| `InvalidateScore` for unscored actions | A push the reviewer didn't review invalidates the tier, even if it's "just a rebase" |
| Async releases a pending sync review | A cheap triage `low` may release a deeper pass only under the same evidence binding |
| Restrictions never truncated out of grants | A review-policy rule or human-review label is never dropped for budget; elide diff before policy |
| Prior decisions are context, not precedent | A previous session's tier is shown to triage but never inherited |
| Decisions shadow classifier | Ship the attention tier in shadow first and compare it against humans before it gates anything |
| Circuit breaker on repeated denials | Repeated blocking findings across rounds raise the tier (`risk.md` §3c's `round` rule) |
| Every fallback named and counted | Every driver in the attention block typed and counted |
