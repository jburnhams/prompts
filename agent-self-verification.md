# Self-verification: how an agent checks its own work

A further drill-down alongside [`agent-context-compaction.md`](./agent-context-compaction.md)
and [`agent-turn-output.md`](./agent-turn-output.md): before a coding
agent declares a task done, does anything actually check that it's
right — and if so, what? This is deliberately **not**
[`code-review-approaches.md`](./code-review-approaches.md), which is
about reviewing someone *else's* pull request. It's the narrower,
different question of an agent checking its *own* just-completed work,
and it turns out to span a much wider range of designs than "the model
decides when it's done" — from nothing at all, through a shared
benchmark-lineage workflow template, through mechanical non-LLM
completion gates, up to a dedicated adversarial verification subagent
that can't trust the implementer's self-report.

**Methodology note**: nine sources are covered in real depth, plus
brief cross-references from four more (SWE-agent, Augment SWE-bench
Agent, mini-swe-agent, Live-SWE-agent, Jules) whose relevant material
was already documented elsewhere in this collection during earlier
research phases. Three sources — Claude Code, Codex CLI, and Microsoft
Agent Framework — required fresh live-source investigation and turned
up the richest findings.

## Sources covered

SWE-agent, mini-swe-agent, Live-SWE-agent, Augment SWE-bench Agent
(shared workflow lineage, §1), Roo Code, Claude Code (leaked, via
`leaked/claude-code/architecture-notes.md`), Codex CLI, OpenCode,
Gemini CLI, OpenHands, Microsoft Agent Framework (via
`codeact-hyperlight/`), Jules (leaked).

---

## 1. The shared SWE-bench-lineage workflow template

Four sources in this collection share visibly the same workflow text,
word-for-word in places, with real variations layered on top —
confirmed by reading all four config files directly, not inferred from
family resemblance.

| Step | SWE-agent | mini-swe-agent / Live-SWE-agent | Augment SWE-bench Agent |
|---|---|---|---|
| 1 | Find and read relevant code | Analyze the codebase by finding and reading relevant files | Explore the repo to familiarize yourself with its structure |
| 2 | Create a script to reproduce the error, run it to confirm | Create a script to reproduce the issue | Create a script to reproduce the error, run it to confirm |
| 3 | Edit the source to resolve the issue | Edit the source code to resolve the issue | **Use `sequential_thinking` to plan the fix** — reflect on 5-7 possible root causes, narrow to 1-2, add logs to validate before editing |
| 4 | Rerun the reproduce script, confirm the error is fixed | Verify your fix works by running your script again | Edit the source to resolve the issue |
| 5 | Think about edge cases, make sure the fix handles them | Test edge cases to ensure your fix is robust | Rerun the reproduce script, confirm the error is fixed |
| 6 | — | Submit via `echo COMPLETE_TASK_AND_SUBMIT_FINAL_OUTPUT` | Think about edge cases |
| 7 | — | — | **Run select tests from the repo to make sure the fix doesn't break anything else** |

All four explicitly tell the model it's already handled test-file
changes and should not modify tests — "I've already taken care of all
changes to any of the test files described in the PR description. This
means you DON'T have to modify the testing logic." Augment's version is
the most elaborate: it adds an explicit planning step via a
`sequential_thinking` tool before editing, and is the only one of the
four with a final "run the existing test suite" step rather than
stopping at the reproduce-script re-run — reproduce-script verification
alone (steps 2/4) proves the reported bug is fixed; a full test-suite
run (Augment's step 7) is a different, broader claim about not breaking
anything else.

**This is the baseline every other mechanism in this doc should be read
against**: reproduce → fix → verify-against-the-reproduction → consider
edge cases → (sometimes) run the broader test suite → submit. Every
source below either matches, extends, or replaces some part of this
shape.

## 2. Deterministic, non-LLM completion gates

Mechanisms that block a "done" signal on a structural precondition —
no model judgment involved.

| Mechanism | Sources |
|---|---|
| **A canned checklist re-injected as ordinary tool output, gating repeated submission** | SWE-agent's `review_on_submit_m` bundle — `submit` is wrapped so that, on its first call, it prints a fixed checklist (rerun the reproduction script, delete it, revert any modified test files) as the *next turn's observation* instead of actually submitting; only a second `submit` call (or an internal `-f`/force flag never shown to the model) lets the real submission through. Purely deterministic string templating — no separate model call, and nothing automatically blocks submission if the agent ignores the checklist and just calls `submit` again with only one configured stage. |
| **A structural precondition check on the completion tool itself** | Roo Code's `AttemptCompletionTool.ts` — blocks `attempt_completion` outright if a tool call failed earlier in the same turn, and (behind a `preventCompletionWithOpenTodos` setting) blocks it if any todo item isn't marked `"completed"`. No model judgment; a code-level guard on one specific tool. |

Both are cheap, both are easy to bypass in principle (the model could
just not report a todo as incomplete, or ignore SWE-agent's checklist
text), and neither actually inspects whether the *changes* are correct
— they check procedural completeness (did you follow the checklist; are
all todos marked done), not correctness.

## 3. Separate-LLM-call judge/reviewer patterns

The most substantive category: a genuinely separate model call
evaluating completed work, distinct from the agent that produced it.

| Design | Sources |
|---|---|
| **Ensemble generate-then-judge over whole independent task attempts** — not partial delegation, N full separate agent runs judged after the fact | SWE-agent's `RetryAgentConfig`/`sweagent/agent/reviewer.py`: `ScoreRetryLoop` runs a `Reviewer` LLM call (own system/instance prompts, own cost accounting) that assigns a numeric acceptance score to each complete attempt, optionally sampled multiple times for self-consistency; `ChooserRetryLoop` runs several attempts to exhaustion, then a separate `Chooser` call (optionally preceded by a `Preselector`) picks the best. Augment SWE-bench Agent's `ensembler_prompt.py`/`majority_vote_ensembler.py` — a separate model (o1) shown N candidate diffs side by side, picking a majority-vote winner. Both are the *same underlying shape* (generate multiple, judge separately), arrived at independently — one scores/retries, the other majority-votes over a fixed batch. |
| **A general single-agent "run until done" loop with an optional LLM judge**, checked against the original request text | Microsoft Agent Framework's `AgentLoopMiddleware.with_judge()` (`agent_framework/_harness/_loop.py`) — a fully separate chat-client call returns a structured `JudgeVerdict` (`answered: bool`, `reasoning: str`), checked against the *original user request*, not a todo list; failure produces a nudge (the judge's own reasoning fed back as a new user turn), not a restart; capped tighter than a non-judge loop (5 iterations vs. 10) specifically because judge calls are "costly and probabilistic"; never wired in by default, one of several interchangeable strategies alongside non-LLM alternatives (`todos_remaining()`, `background_tasks_running()`) in the same file. |
| **A dedicated adversarial verification subagent, structurally unable to trust the implementer** | Claude Code (leaked, **internal-only — see the caveat in §7**) — `src/tools/AgentTool/built-in/verificationAgent.ts`: a separate LLM instance with no file-write access, required to gather command-output evidence for every check rather than accept the implementer's claims, run the build and full test suite ("failing tests are an automatic FAIL"), run linters/type-checkers, and perform mandatory "adversarial probes" (concurrency, boundary values, idempotency) before issuing a PASS/FAIL/PARTIAL verdict the implementer "cannot self-assign." |

**A cross-cutting design question all four answer differently**: what
happens when the judge/reviewer says "not good enough"? SWE-agent's
`ScoreRetryLoop` and Augment's ensembler run *another full attempt*;
Microsoft Agent Framework's judge *nudges the same conversation* to
keep working; Claude Code's verification subagent (per its prompt)
issues a verdict the calling agent then has to act on, without a
prescribed retry mechanism visible in what was captured. Retry-a-whole-
attempt is more expensive but cleaner (no risk of the same broken
reasoning persisting); nudge-and-continue is cheaper but risks the
working agent repeating whatever mistake it already made.

## 4. Review-as-a-general-tool — the conflation trap

**Two sources have something literally named "review" that is *not* an
autonomous self-check gate, and it's easy to mistake it for one from
the name alone.**

- **Codex CLI's `ReviewTask`/`codex review`/`/review`**: confirmed by
  reading `codex-rs/core/src/tasks/review.rs` — spawns a fully separate,
  nested one-shot conversation with its own system prompt
  (`codex-rs/prompts/templates/review/rubric.md`, framed unconditionally
  as "You are acting as a reviewer for a proposed code change made by
  **another engineer**" — even when the target is the CLI's own
  uncommitted changes) that can target uncommitted changes, a
  base-branch diff, an arbitrary commit SHA, or free-text instructions.
  **Always explicitly invoked** — a CLI flag, a TUI popup, or an
  app-server request — never auto-chained after a normal edit turn. A
  targeted search for completion-gating patterns (SWE-agent's/Roo
  Code's style) found nothing tying `ReviewTask` to task completion at
  all.
- **OpenCode's `/review` command** (`command/template/review.txt`):
  same shape — reviews `git diff`/`git diff --cached`/untracked files
  by default (so it *can* point at the agent's own uncommitted work),
  explicitly framed as a "code reviewer" persona examining bugs,
  structure, performance, and behavior changes. Requires explicit user
  invocation after the fact.

**Why this matters**: both are architecturally identical to reviewing
someone else's PR — the same mechanism, just optionally pointed at
your own diff instead of someone else's. Neither is a completion gate,
neither runs automatically, and neither is what SWE-agent's
`review_on_submit_m` or Roo Code's `attempt_completion` guard are (§2)
— those actually sit in the completion path and (attempt to) block
finishing. A source having a "/review" command is not evidence it has
self-verification in the sense this doc is otherwise surveying.

## 5. Hook-based, user-configured verification gates

One source has a genuinely general-purpose mechanism for this, not
tied to any specific verification logic at all: Claude Code's `Stop`
hook (leaked source, but — unlike §3's verification subagent and §6's
plan-verification tool — **confirmed not gated behind the internal-only
flag**, consistent with Claude Code's publicly documented hook system).
A 26-member `HookEvent` union includes `Stop`, `StopFailure`,
`SubagentStop`, `PostToolUse`, `PostToolUseFailure`, `TaskCompleted`,
`TeammateIdle` alongside the already-documented `PreCompact`/
`PostCompact`. If a user-configured `Stop` hook returns
`preventContinuation: true`, the agent loop does not end — it keeps
running with the hook's stated reason surfaced as a message. This is
the concrete mechanism behind "wire up `npm test` on Stop, and block
the agent from finishing if it fails" — a real verification gate, just
one the *user* sets up rather than the agent choosing to use or the
scaffold building in by default.

## 6. Per-action mandatory verification (not just pre-submission)

Every mechanism above gates *task completion*. Jules's leaked prompt
(see `leaked/jules/README.md`) gates every single *write*: "After every
action that modifies the state of the codebase... you **must** use a
read-only tool... to confirm that the action was executed successfully
and had the intended effect. Do not mark a plan step as complete until
you have verified the outcome." Its `plan_step_complete()` tool
description reinforces this as a hard precondition. This is a
structurally different granularity from everything else surveyed —
verification happens continuously through the task, not as a discrete
gate at the end. The later-captured version of Jules's prompt adds a
`pre_commit_instructions` tool on top of this (deliberately hidden from
the user-facing plan text — "do not mention the tool... describe the
step's purpose as 'testing, verification, review, and reflection'"),
an explicit `request_code_review()` tool, and Playwright-generated
screenshots as proof of frontend verification — see the full writeup
for detail not repeated here.

## 7. Prompted-only instructions, no enforcement

The largest bucket: a system-prompt instruction to verify/test, with no
code-level gate found backing it up.

- **OpenHands** (`system_prompt.j2`, stored locally): a numbered
  TESTING/VERIFICATION pair — create tests before fixing bugs, consider
  TDD for new features, "test your implementation thoroughly, including
  edge cases" if the environment supports it. No enforcement confirmed.
- **Codex CLI**: "Validating your work" — "If the codebase has tests or
  the ability to build or run, consider using them to verify changes
  once your work is complete" — proactivity itself gated by *approval
  mode* (proactive in fully-autonomous mode, deferred to the user in
  interactive modes), but purely instructional either way.
- **Claude Code's non-ant-gated "Autonomous work" section**: frames
  running tests/checking types/running linters as a *permission*
  ("without asking"), plus a rhetorical self-check ("what would I want
  to verify before calling this done?") — softer than the ant-gated
  verification subagent, but present in ordinary builds.

**The critical caveat for Claude Code specifically**: nearly every
verification mechanism this research pass found for Claude Code —
the `VerifyPlanExecutionTool` wiring, the periodic plan-verification
nudge, the adversarial verification subagent, and two explicit
"verify before claiming done" / "never fake a green result" system
prompt lines — are gated behind `process.env.USER_TYPE === 'ant'`
(an Anthropic-employee-only flag) or a GrowthBook flag explicitly
commented "3P default: false — ant-only A/B," meaning they're dead-code-
eliminated out of ordinary external builds in this snapshot. What's
confirmed is Anthropic testing these mechanisms internally, not
necessarily what external Claude Code users get. One leaked code
comment discloses why this work exists at all: two of the gated
prompt lines are annotated "False-claims mitigation for Capybara v8
(29-30% FC rate vs v4's 16.7%)" — an internal model version reportedly
falsely claimed task completion roughly 3 times in 10, and this
specific mitigation was built and put under A/B test in response. Rare,
concrete, *measured* evidence that false-completion-claiming is a real
enough failure mode to justify dedicated engineering — treat the number
itself as an unverified leaked claim, but the underlying problem
statement as a useful data point regardless of source reliability.

## 8. An adjacent-but-different mechanism worth distinguishing

OpenHands's old-tag `security_risk_assessment.j2` prompt file's name
invites the assumption it's a self-review mechanism. Confirmed by
reading it in full: it isn't. It's a **pre-execution risk-classification
policy** — the agent tags each *proposed* tool call's `security_risk` as
LOW/MEDIUM/HIGH before running it, with different criteria depending on
CLI vs. sandboxed mode. This gates *proposed actions before they
execute*, the same family as permission/approval systems (a candidate
drill-down noted in the root README, not yet its own doc), not a check
on *completed* work. Worth naming explicitly since the file name alone
would suggest otherwise.

## Absences

- **OpenCode**: no hidden self-review agent (confirmed absence — the
  complete built-in agent list is known and has no fifth reviewer/
  verifier entry); only the general-purpose `/review` command (§4).
- **Roo Code**: no review mode or LLM-judge mechanism (confirmed
  absence across all five built-in modes); only the mechanical
  `attempt_completion` gate (§2).
- **Gemini CLI**: confirmed absence — no reviewer/verifier agent among
  the built-in agent set, no self-review/verify-before-finishing
  language found anywhere searched.
- **Every source outside the ones listed above** — the rest of this
  collection hasn't been checked for self-verification mechanisms at
  all. Given how often "not checked" has turned out to mean "actually
  quite sophisticated" elsewhere in this collection's research (Codex's
  sub-agents, OpenCode's Task tool, OpenHands's delegation system, Roo
  Code's Orchestrator mode), treat absence from this doc as exactly
  that — not checked — not as evidence the mechanism doesn't exist.

---

## Design takeaways

- **Verification granularity spans a real spectrum, not a binary
  has-it/doesn't**: per-action (Jules, every write) → per-completion-
  attempt (SWE-agent's checklist gate, Roo Code's todo gate, most
  system-prompt instructions) → per-whole-task-ensemble (SWE-agent's
  Reviewer/Chooser, Augment's ensembler, running N full attempts and
  judging afterward) → user-configured-and-arbitrary (Claude Code's
  `Stop` hooks, which could in principle be wired to check anything,
  including nothing). No source combines more than two or three points
  on this spectrum at once; most pick exactly one.
- **"Has a review command" and "has self-verification" are different
  claims, and conflating them is an easy mistake** (§4): Codex's
  `ReviewTask` and OpenCode's `/review` are both real, well-built
  features — but both are general "review a diff" utilities that
  happen to support pointing at your own work, explicitly invoked,
  never a completion gate. A source having a `/review` command is
  weaker evidence of self-verification discipline than SWE-agent's
  unglamorous deterministic checklist-on-submit gate.
- **The two richest findings in this survey (Claude Code's verification
  subagent, Microsoft Agent Framework's judge) both land on "separate
  LLM call checks the work," but differ sharply on trust posture**:
  Claude Code's is adversarial by design (must not trust the
  implementer, must gather its own evidence, issues a verdict the
  implementer can't self-assign); the Agent Framework's judge is
  cooperative (checks against the original request, feeds its reasoning
  back as a nudge to help the *same* agent improve, explicitly
  documents its own risk of becoming an injection vector via that
  feedback channel). Different answers to "how skeptical should the
  checker be of the thing it's checking."
- **Claude Code's internal-only gating is itself a significant finding,
  not just a caveat to skip past**: the most sophisticated
  self-verification machinery surveyed here is confirmed to exist in
  Anthropic's own codebase but confirmed *not* to ship to ordinary
  users in this snapshot. Combined with the leaked "29-30% false-claim
  rate" comment, this reads as evidence that even a well-resourced
  vendor treats reliable self-verification as a hard, still-experimental
  problem — not something solved and shipped, but something actively
  being A/B tested internally before wider release.
- **Mechanical, non-LLM gates (§2) are unglamorous but have a real
  advantage the LLM-judge approaches (§3) don't**: they can't be talked
  out of firing. A judge or reviewer subagent's verdict is itself a
  model output, subject to the same failure modes (including, per the
  Agent Framework's own documented concern, prompt injection via
  whatever content it's reviewing) as the work it's checking. SWE-agent's
  checklist and Roo Code's todo-completeness check are trivially
  bypassable in a different way (the agent can just ignore them or mark
  things done dishonestly) but at least don't add a second point where
  the *checking* mechanism itself can be fooled by adversarial content.
- **The shared SWE-bench workflow template (§1) is the closest thing to
  an industry-standard self-verification convention found in this whole
  survey** — four independently-maintained projects converged on
  reproduce-then-verify-against-reproduction as the baseline, differing
  mainly in whether they extend it (Augment's added planning step and
  full-test-suite run) or leave it minimal. Everything else in this
  document is either an elaboration on top of that baseline or a
  completely different mechanism layered alongside it.
