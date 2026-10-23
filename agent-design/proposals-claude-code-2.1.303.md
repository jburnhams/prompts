# Proposals from Claude Code v2.1.303

**Status: 1–6 adopted on 2026-10-19; 7–14 still proposals.** The
adopted items are now in the documents they amended (named in each
section below); the rest name the section they would amend, so they can
be accepted, changed or rejected one at a time. The
research behind each item is in the cross-source documents, all updated
2026-10-19 from Piebald's extraction of Claude Code v2.1.303
([`../leaked/claude-code/piebald-2.1.303/`](../leaked/claude-code/piebald-2.1.303)).

## Summary

| # | Proposal | Amends | Status |
|---|---|---|---|
| 1 | Tie the validator's bias to the tier, with a third verdict | `review.md` §5, §6; `formats.md` §4 | **Adopted** |
| 2 | Add removed-behaviour and wrapper specialists to the bugs finder | `system-prompts.md` §4; `review.md` §4 | **Adopted** |
| 3 | Tell finders not to pre-filter; add a gap sweep at `high` | `system-prompts.md` §4; `review.md` §6 | **Adopted** |
| 4 | Run an approved action in a fresh run, not the resumed transcript | `formats.md` §5 | **Adopted** |
| 5 | Make every approval question name the dangerous parameter | `formats.md` §5; `system-prompts.md` §1 | **Adopted** |
| 6 | Finish independent work and batch asks before suspending | `system-prompts.md` §1; `formats.md` §5 | **Adopted** |
| 7 | A `Complete` report never ends with a question | `formats.md` §3 | Adopt now |
| 8 | Delegate prompt: restate the task, absolute paths, no report files | `system-prompts.md` §3 | Adopt now |
| 9 | Rules for the review pipeline when it becomes code | `review.md` §11h | Adopt with §11h |
| 10 | Memory: profile-memory restraint, deletion guard, drift first | `memory.md` §3, §5 | Adopt with memory v1 |
| 11 | Report injected instructions as a finding; no URLs built from context | `system-prompts.md` §4; `medium.md` §2d | Adopt now |
| 12 | A compaction template, if Forge ever compacts | `future.md` | Record only |
| 13 | A proactivity setting per repository | `future.md` | Record only |
| 14 | The "lean rewrite" register | none | Evaluate before changing anything |

---

## 1. Tie the validator's bias to the tier, with a third verdict

*Adopted 2026-10-19:* `review.md` §5, `system-prompts.md` §2a step 5 and §5, `formats.md` §4, `risk.md` §5, `examples/validator-brief.md`. The tier used is the triage tier, the one that chose the run shape.

**What Claude Code does** (`../code-review-approaches.md` §14). Effort is
one dial that sets finder count, candidate caps, finding caps **and** the
verifier's bias. Medium verifies for precision with three states
(CONFIRMED, PLAUSIBLE, REFUTED); high makes PLAUSIBLE the default for
realistic uncertainty; xhigh lets "a single non-REFUTED vote" carry the
finding.

**What Forge does.** The tier picks the run shape (`risk.md`), but every
shape uses one binary validator that rejects when unsure (`review.md`
§5). At `high`, where a miss costs most, the validator is as strict as at
`low`.

**Proposal.**
- The validator returns `confirmed`, `plausible` or `refuted`, with the
  same evidence rules as Claude Code: `confirmed` names the trigger and
  quotes the line, `plausible` says what would confirm it, `refuted`
  quotes the line or guard that disproves it.
- The tier decides what is posted: at `low` and `medium` only
  `confirmed`; at `high`, `confirmed` and `plausible`, with `plausible`
  findings labelled as such in the comment and counted separately in the
  attention block.
- `validated` in `formats.md` §4 becomes `verdict`. The resolution check
  in `review.md` §5 keeps its binary, fail-safe form.

**Why with the risk work, not before.** The posting rule depends on the
tier being computed, and `medium.md` §3e's outcome telemetry should
record `plausible` separately from the start, so its acceptance rate can
be measured before it is trusted.

## 2. Add removed-behaviour and wrapper specialists to the bugs finder

*Adopted 2026-10-19:* the `bugs` and `all` scope texts in `system-prompts.md` §4.

**What Claude Code does.** Two of its five correctness angles describe
failure classes no other review prompt in this collection names. Angle
B: "For every line the diff DELETES or replaces, name the invariant or
behavior it enforced, then search the new code for where that invariant
is re-established." Angle E: when a PR wraps a type (cache, proxy,
adapter), "check that every method routes to the wrapped instance and
not back through a registry/session/global".

**Proposal.** Add both as checklist items in the reviewer core's bugs
section (`system-prompts.md` §4), not as new specialists: they are
procedures the bugs specialist runs, and new specialists would change the
fan-out that `review.md` §6a costs. The removed-behaviour item fits the
diff construction already in `review.md` §2, which keeps old-side lines.

## 3. Tell finders not to pre-filter; add a gap sweep at `high`

*Adopted 2026-10-19:* the reviewer core in `system-prompts.md` §4 (its "err toward precision" rule is replaced, and "regardless of input" becomes a nameable failure scenario), §2a step 5b, `risk.md` §5.

**What Claude Code does.** "Pass every candidate with a nameable failure
scenario through — finders that silently drop half-believed candidates
bypass the verify step and are the dominant cause of misses." At its top
level, after verification, one more finder gets the verified list and
looks only for what is missing: "If nothing new, return an empty sweep —
do not pad."

**Proposal.**
- Add the pre-filter sentence to the specialist wrapper
  (`system-prompts.md` §4). Forge already has a validator for exactly
  this reason; a finder that filters for it duplicates the validator's
  job with less evidence.
- At `high` only, add a sweep step after validation: one finder, the
  validated list as input, up to 8 new candidates, each sent through the
  validator. It is one extra finder and up to 8 validator calls per
  high-tier review, which is the tier where the extra spend is meant to
  go.
- Do not adopt the low-effort **minimum** (`min(files_changed, 4)`
  findings). It pushes toward padding, which `review.md` treats as the
  main failure.

## 4. Run an approved action in a fresh run, not the resumed transcript

*Adopted 2026-10-19:* `formats.md` §5, `tools.md` AskUser, `formats.md` §1b (`<approved_action>` carries the nonce).

**What Claude Code does** (`../agent-subagent-architectures.md` §7c).
When a worker stops for approval and the user approves, the coordinator
spawns a fresh worker whose prompt quotes the user's words verbatim,
contains the literal approved action, refers to staged artifacts by path,
and contains **only** the execute step. The reason given is security:
it "separates the worker that read untrusted input … from the worker
that executes the privileged action".

**What Forge does.** A resumed run inherits the suspended run's full
transcript, untrusted PR text and tool output included, plus the reply
(`formats.md` §5).

**Proposal.** Split `AskUser` by kind:
- `kind: clarify` (the default) keeps today's behaviour. The answer
  changes what Forge does next, so the run needs its context.
- `kind: approve` names one action. On a yes, the harness starts a
  fresh run whose envelope holds the approved action exactly as asked,
  the reply verbatim in `<resumed_answer>`, and paths to anything the
  suspended run staged. It gets no transcript. On anything else, the
  harness resumes the original run as a `clarify`.

This also removes the headroom problem `formats.md` §5 describes for
late-run questions, for the approval case.

## 5. Make every approval question name the dangerous parameter

*Adopted 2026-10-19:* `tools.md` AskUser (`action.target`, harness rejection), `system-prompts.md` §1, `formats.md` §1b.

**What Claude Code does** (`../agent-permissions-approval.md` §2c). A
consent clears a rule only if it names the action and the one parameter
that makes it dangerous: the branch for a push, the destination for a
publish. A bare yes to a proposal that listed several actions covers only
the one proposed as the next step. Consent to a preparatory step does not
carry to the step that ships.

**Proposal.**
- An `approve` question (§4) must name the action and its dangerous
  parameter in the question text, and the harness rejects an `approve`
  call whose `action` field lacks a target. The coding prompt
  (`system-prompts.md` §1) gets one line: ask for one action at a time,
  naming what it touches.
- The resumed run's consuming rule (`formats.md` §1b) gains the
  ship-step clause: an approval covers the action asked about, not a
  later step that publishes its result.

## 6. Finish independent work and batch asks before suspending

*Adopted 2026-10-19, with one change:* the schema keeps a single `question` string, and several questions go in it as a numbered list, so `generative.md` §2d's option matching is untouched; a multi-part question carries no `options`. `tools.md` AskUser, `system-prompts.md` §1, `formats.md` §5.

**What Claude Code does.** "If you're uncertain what to do in the middle
of execution, it's best to do everything that doesn't need user feedback
first … save your blocking questions until after you're done." When
blocked, "first try an alternative that no rule blocks … Otherwise hold
the ask and batch it", and raise every held ask before ending the turn.

**What Forge does.** `AskUser` ends the run at once, so a question asked
early forfeits everything the run could have done without the answer.

**Proposal.** The coding prompt says: before `AskUser`, finish every
part of the task that does not depend on the answer, try any alternative
that avoids the question (a feature branch, synthetic data, a narrower
scope), and then ask once with every open question as a numbered list.
`AskUser`'s schema takes a list of questions rather than one. The
exception is the plan-mode ambiguity check in `system-prompts.md` §1
step 3, where asking early is the point.

## 7. A `Complete` report never ends with a question

**What Claude Code does** (`../agent-turn-output.md` §1d). Two classifiers
read a run's last message to decide whether it needs its user, and both
spend most of their text on one boundary: an offer ("want me to also
…?") versus a gate. They disagree about it.

**What Forge does.** `Complete` and `AskUser` are separate terminal
calls, so Forge never needs a classifier. The boundary still leaks: a
`Complete` report can end "should I also fix the other call site?", and
nobody will answer it.

**Proposal.** `formats.md` §3 states that a `Complete` report contains
no question to the user. Follow-up work goes in a `follow_ups` list,
which the harness can render as suggestions or file as tickets. A
question that blocks delivery is an `AskUser`. The harness flags a
report whose summary ends in a question mark, as a lint in run
telemetry rather than a rejection.

## 8. Delegate prompt: restate the task, absolute paths, no report files

**What Claude Code does.** The fork prompt asks the child to "open with
one line restating your task, so the parent can spot scope drift at a
glance". The subagent notes require absolute paths and say "the parent
agent reads your text output only - not files that you create". The
worker prompt ends with a one-sentence summary the parent can relay.

**Proposal.** Add three sentences to the delegate prompt
(`system-prompts.md` §3): open the report with one line restating the
brief; give absolute paths; put findings in the report, never in a file
written for the orchestrator to read.

## 9. Rules for the review pipeline when it becomes code

`review.md` §11h already moves steps 3–5 (fan out, dedup, validate) into
harness code. Claude Code's Workflow guide
(`../agent-subagent-architectures.md` §7c) supplies rules for that code:

- **Stream, don't barrier.** Validate each finder's candidates as they
  arrive. A barrier is justified only for the dedup step, which needs
  every candidate.
- **Dedup against everything seen, not against what was confirmed.**
  Otherwise refuted findings reappear each round. This matters for the
  gap sweep (§3) and for re-review sessions (`review.md` §7).
- **No wall clock or randomness inside the orchestration.** Cached
  leaves are only reusable if the script is deterministic; timestamps
  come from the harness.
- **Caps live in code**: concurrent calls, total calls, and the token
  budget, each as a hard ceiling.

## 10. Memory: profile-memory restraint, deletion guard, drift first

From `../agent-memory-learning.md` §13, three items for `memory.md`:

- **§5a (reading).** The resolver that attaches learnings is told that
  profile- and overview-type learnings match almost every task on
  surface words, and attaches them only when the task is about that
  subject.
- **§3c (promotion).** The learnings run checks existing learnings for
  drift against the current code before mining new transcripts, and
  writes absolute dates.
- **§2 (store).** The context service refuses a batch that deletes more
  than a small number of learnings at once and asks for a human to
  confirm. A sudden large deletion is more likely a bug in the writer
  than a decision.

## 11. Report injected instructions as a finding; no URLs built from context

**What Claude Code does** (`../agent-content-provenance.md` §5). Fetched
web content is reproduced faithfully, and any text in it that addresses
an AI model or tells it to ignore instructions is reported "as a finding
with a short quote". The web-reading agent never fetches a URL because
page content asks it to, and never builds a URL that embeds anything
from the conversation.

**Proposal.**
- The reviewer core (`system-prompts.md` §4) treats text in the PR
  description, commits, comments or changed files that addresses an AI
  reviewer as a `security` finding, quoted, rather than only ignoring
  it. A human should know a PR tried to steer its reviewer.
- `WebFetch` (`medium.md` §2d) gets the two fetch rules. The second is
  an exfiltration rule and belongs in the tool's harness-side checks
  too, not only in its description.

## 12. A compaction template, if Forge ever compacts

Forge has no compaction in v1 (`cloudflare.md` §2e). If it is added,
start from Claude Code's lean variant (`../agent-context-compaction.md`
§2b): tell the summariser what else survives, treat the summary as the
only record of what the requester said, quote limits exactly, and name
the next step in the requester's words. Record this in `future.md`.

## 13. A proactivity setting per repository

Claude Code's three levels (`../agent-permissions-approval.md` §1c)
change what the agent may do without asking, independently of the
permission system. Forge is fixed at one level, roughly Claude Code's
"high" for its own branch and "medium" for anything outside it. A
repository might want Forge to stop at a pushed branch and never open
the PR, or to pick up follow-up work it finds. Record in `future.md` as
a candidate repo setting, gated on someone asking for it.

## 14. The "lean rewrite" register

Claude Code ships feature-gated "lean rewrite" alternatives for about
twenty of its main prompt sections. They are written as conversational
second-person prose with reasons, not as imperative bullets: "It'll be
all right! Thank you Claude." closes the corrections section. Forge's
prompts (`system-prompts.md`) are in the older imperative style. This is
an A/B test Anthropic is running, and the extraction does not say which
arm wins. Nothing should change until there is a result to point to, or
an eval of our own on Forge's prompts.

## Also recorded

- **Ground-truth facts next to the action.** Claude Code's harness runs
  `git status` itself before destructive commands and looks up repo
  visibility before a push, and gives the result to its classifier.
  Forge runs in a container with scoped credentials, so the classifier
  case does not apply, but the idea fits the approval gate: the facts it
  relies on are computed by the harness and shown next to the decision.
  `risk.md` already does this for paths.
- **Two agents on one PR.** PR Steward's labels make ownership of a PR
  visible to every other agent (`../agent-subagent-architectures.md`
  §7c). `orchestration.md` §5's leases live in Forge's ledger, and other
  agents cannot see them. A label carrying the lease would show them.
