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

**Methodology note**: twenty-plus sources are covered in real depth, plus
brief cross-references from four more (SWE-agent, Augment SWE-bench
Agent, mini-swe-agent, Live-SWE-agent) whose relevant material was
already documented elsewhere in this collection during earlier research
phases. A first pass covered nine sources in depth (Claude Code, Codex
CLI, and Microsoft Agent Framework required fresh live-source
investigation and turned up the richest findings); a second pass added
eleven more — five open-source (Cline, Aider, Copilot Chat, Goose,
Crush) and six leaked (Cursor, Devin, Windsurf, Warp, Replit, Factory/
Droid) — all read from local files already in this collection, no live
fetching needed. That second pass roughly doubled the size of the
"prompted-only" bucket (§7) and surfaced several genuinely new patterns
not fitting the original typology at all (§9, §10) — a reminder that
this doc's own "Absences" section undersells how much is left
unchecked.

## Sources covered

**First pass**: SWE-agent, mini-swe-agent, Live-SWE-agent, Augment
SWE-bench Agent (shared workflow lineage, §1), Roo Code, Claude Code
(leaked, via `leaked/claude-code/architecture-notes.md`), Codex CLI,
OpenCode, Gemini CLI, OpenHands, Microsoft Agent Framework (via
`codeact-hyperlight/`), Jules (leaked).

**Second pass**: Cline, Aider, Copilot Chat, Goose, Crush, Cursor
(leaked), Devin (leaked), Windsurf (leaked), Warp (leaked), Replit
(leaked), Factory/Droid (leaked).

**Third pass**: Google Antigravity (leaked) — see §10 for a
severity-gated retry policy and a persistent "artifact-as-verification-
record" pattern, both candidate additions to the typology below. Zed
(genuinely open source) — `diff_judge.hbs`, a clean §3 instance: a
dedicated separate-LLM-call prompt that scores a diff 0-100 against a
list of assertions with a required per-assertion `<analysis>` line
before the `<score>`, though the surrounding retry/gating logic that
calls it isn't captured. GitHub Copilot CLI (leaked) — a §7
prompted-only baseline, but with an Autopilot-mode named-checklist gate
close to §10's rhetorical-escalation pattern, plus two sub-agents
(`code-review`, a §4 conflation-trap instance; `rubber-duck`, a §3
advisory judge with a three-tier severity taxonomy not matched
elsewhere) — see the new subsection added to each of those sections
below.

**Fourth pass**: Grok Build (leaked) — mostly an ordinary §7
prompted-only "green-run" instance, but with a genuinely new §2
candidate: a harness-enforced gate on ending a turn at all while any
todo is open, not on one specific completion tool (see §2 below).

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

**The same shape resurfaces independently outside the SWE-bench-harness
world.** Copilot Chat's `AlternateGPTPrompt` (a GPT-4.1-era variant,
`defaultAgentInstructions.tsx`) spells out an almost identical loop —
"Implement the fix incrementally... Test frequently. Run tests after
each change to verify correctness... Iterate until the root cause is
fixed and all tests pass... Reflect and validate comprehensively...
remember there are hidden tests that must also pass before the solution
is truly complete" — "hidden tests" is functionally the same claim as
SWE-agent/mini-swe-agent's "I've already taken care of all changes to
any of the test files... you DON'T have to modify the testing logic."
Copilot Chat's Grok/xAI-family prompt converges on the same idea from a
different angle, framed as mandatory rather than descriptive: "After
any substantive change, run the relevant build/tests/linters
automatically... Don't end a turn with a broken build if you can fix
it. If failures occur, iterate up to three targeted fixes." Devin
independently carries the lineage's most specific single rule
verbatim in spirit: "never modify the tests themselves, unless your
task explicitly asks you to... Always first consider that the root
cause might be in the code you are testing rather than the test
itself." None of these three share literal prompt text with the four
SWE-bench-harness sources in the table above — this looks like
convergent design (the same lesson learned independently by different
teams) rather than a shared common ancestor, worth distinguishing from
this collection's confirmed cases of actual shared lineage (e.g. Augment
SWE-bench Agent and SWE-agent both forking Anthropic's reference
implementation, per `augment-swebench-agent/README.md`).

## 2. Deterministic, non-LLM completion gates

Mechanisms that block a "done" signal on a structural precondition —
no model judgment involved.

| Mechanism | Sources |
|---|---|
| **A canned checklist re-injected as ordinary tool output, gating repeated submission** | SWE-agent's `review_on_submit_m` bundle — `submit` is wrapped so that, on its first call, it prints a fixed checklist (rerun the reproduction script, delete it, revert any modified test files) as the *next turn's observation* instead of actually submitting; only a second `submit` call (or an internal `-f`/force flag never shown to the model) lets the real submission through. Purely deterministic string templating — no separate model call, and nothing automatically blocks submission if the agent ignores the checklist and just calls `submit` again with only one configured stage. |
| **A structural precondition check on the completion tool itself** | Roo Code's `AttemptCompletionTool.ts` — blocks `attempt_completion` outright if a tool call failed earlier in the same turn, and (behind a `preventCompletionWithOpenTodos` setting) blocks it if any todo item isn't marked `"completed"`. No model judgment; a code-level guard on one specific tool. |
| **A gate on ending the turn at all, not on one named completion tool** — the broadest-scoped mechanism in this table | Grok Build (leaked), `<task_completion_discipline>`'s "End-of-turn todo gate": "Before ending a turn (= producing a content-only assistant message with no tool calls), re-read your current todo list. If any item is `pending` or `in_progress` AND that item is not backed by a live background subagent, monitor, or background command, the turn may NOT end... The harness enforces this: if you try to end a turn with unbacked pending/in_progress todos, you will receive a system-reminder and be forced into another turn." Unlike Roo Code's `preventCompletionWithOpenTodos` (which blocks calling one specific tool, `attempt_completion`), this blocks the act of ending a turn with *no tool call whatsoever* while work remains open — a structurally broader gate, since it applies regardless of which (if any) completion-signaling tool the model tries to use. Three explicit exceptions are carved out (a live background subagent/command still running, a destructive operation awaiting authorization, or a hard external blocker with todos marked `cancelled`), each requiring the model to state the exception rather than just going quiet. |

Both are cheap, both are easy to bypass in principle (the model could
just not report a todo as incomplete, or ignore SWE-agent's checklist
text), and neither actually inspects whether the *changes* are correct
— they check procedural completeness (did you follow the checklist; are
all todos marked done), not correctness.

**A useful negative comparison**: Cline's `attempt_completion` tool
looks superficially similar — its description says the tool "CANNOT be
used until you've confirmed from the user that any previous tool uses
were successful" and instructs the model to ask itself in `<thinking>`
tags whether that's true before calling it. But this is pure prompting,
not a code-level gate like Roo Code's — no structural check in
`system.ts`/`responses.ts` was found blocking the call, and the
"success" being confirmed is *tool-call success* (did the file write
go through), not code correctness. Same surface shape as §2, weaker
enforcement than either row in the table above.

**Factory (Droid)'s leaked prompt** describes a checklist-shaped gate
in the same MANDATORY/BLOCKING register as this table, but ties it to
an external, human-visible artifact instead of an internal tool call:
"Create a non-draft PR ONLY when: Dependencies successfully installed...
All code quality checks green with evidence; Clean worktree except
intended changes. If any item is missing, do NOT create a non-draft
PR." Only the system prompt was captured for this source, so — unlike
SWE-agent's and Roo Code's confirmed code-level implementations —
whether anything actually enforces this at the code level is unknown;
see §10 for why this is filed separately as a "prompt-simulated" gate
rather than added to the table above.

## 3. Separate-LLM-call judge/reviewer patterns

The most substantive category: a genuinely separate model call
evaluating completed work, distinct from the agent that produced it.

| Design | Sources |
|---|---|
| **Ensemble generate-then-judge over whole independent task attempts** — not partial delegation, N full separate agent runs judged after the fact | SWE-agent's `RetryAgentConfig`/`sweagent/agent/reviewer.py`: `ScoreRetryLoop` runs a `Reviewer` LLM call (own system/instance prompts, own cost accounting) that assigns a numeric acceptance score to each complete attempt, optionally sampled multiple times for self-consistency; `ChooserRetryLoop` runs several attempts to exhaustion, then a separate `Chooser` call (optionally preceded by a `Preselector`) picks the best. Augment SWE-bench Agent's `ensembler_prompt.py`/`majority_vote_ensembler.py` — a separate model (o1) shown N candidate diffs side by side, picking a majority-vote winner. Both are the *same underlying shape* (generate multiple, judge separately), arrived at independently — one scores/retries, the other majority-votes over a fixed batch. |
| **A general single-agent "run until done" loop with an optional LLM judge**, checked against the original request text | Microsoft Agent Framework's `AgentLoopMiddleware.with_judge()` (`agent_framework/_harness/_loop.py`) — a fully separate chat-client call returns a structured `JudgeVerdict` (`answered: bool`, `reasoning: str`), checked against the *original user request*, not a todo list; failure produces a nudge (the judge's own reasoning fed back as a new user turn), not a restart; capped tighter than a non-judge loop (5 iterations vs. 10) specifically because judge calls are "costly and probabilistic"; never wired in by default, one of several interchangeable strategies alongside non-LLM alternatives (`todos_remaining()`, `background_tasks_running()`) in the same file. |
| **A dedicated adversarial verification subagent, structurally unable to trust the implementer** | Claude Code (leaked, **internal-only — see the caveat in §7**) — `src/tools/AgentTool/built-in/verificationAgent.ts`: a separate LLM instance with no file-write access, required to gather command-output evidence for every check rather than accept the implementer's claims, run the build and full test suite ("failing tests are an automatic FAIL"), run linters/type-checkers, and perform mandatory "adversarial probes" (concurrency, boundary values, idempotency) before issuing a PASS/FAIL/PARTIAL verdict the implementer "cannot self-assign." |
| **A minimal, rubric-scored judge prompt — the mechanism in isolation, without the surrounding retry/gating logic** | Zed (genuinely open source) — `diff_judge.hbs`: a separate call scores a `{{diff}}` 0-100 against a list of `{{assertions}}`, required to emit a one-line `<analysis>` per assertion before the final `<score>` — auditable per-criterion rather than a single opaque verdict, but this template alone doesn't reveal what calls it or what happens on a low score. |
| **An advisory, non-gating judge with a three-tier named severity taxonomy per issue, rather than one score or verdict for the whole attempt** | GitHub Copilot CLI (leaked) — its `rubber-duck` sub-agent: "Call this agent for any non-trivial task to get a second opinion — the best time is after planning but before implementing," with each finding classified "Blocking," "Non-Blocking," or "Suggestion." Distinct from every other judge in this table's output shape — SWE-agent's Reviewer emits one numeric score, Microsoft Agent Framework's judge emits one boolean, Zed's emits one 0-100 score — here severity is assigned per-issue rather than to the attempt as a whole. Explicitly non-directive about consequence: "It is not your role to give an overall recommendation on what the agent does with your feedback... let the agent decide how to proceed" — even a "Blocking" verdict is advisory, with no automatic retry or gate tied to it, unlike SWE-agent's `ScoreRetryLoop` or Claude Code's verification subagent. |

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

**Three sources have something literally named "review" that is *not*
an autonomous self-check gate, and it's easy to mistake it for one from
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
- **GitHub Copilot CLI's `code-review` sub-agent** (leaked): the same
  shape again — a dedicated, high-signal-only reviewer ("finding your
  feedback should feel like finding a $20 bill in your jeans after
  doing laundry"), explicitly barred from editing code ("You Must
  NEVER Modify Code... access to all tools for investigation purposes
  only") and gated on `git diff`/`git log` inspection. Reachable via the
  general `task` delegation tool like any other sub-agent, with nothing
  in the captured prompt auto-chaining it after an edit turn — a third
  independent instance of "a general diff-reviewer the orchestrator can
  optionally point at its own work," not a completion gate.

**Why this matters**: all three are architecturally identical to
reviewing someone else's PR — the same mechanism, just optionally
pointed at your own diff instead of someone else's. None is a
completion gate, none runs automatically, and none is what SWE-agent's
`review_on_submit_m` or Roo Code's `attempt_completion` guard are (§2)
— those actually sit in the completion path and (attempt to) block
finishing. A source having a "/review" command or `code-review`
sub-agent is not evidence it has self-verification in the sense this
doc is otherwise surveying.

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
- **Crush**: the densest §7 instance by volume — testing/verification
  language recurs at nearly every structural checkpoint of
  `coder.md.tpl` (a top-level "TEST AFTER CHANGES" critical rule, a
  per-edit "after each change: run tests" workflow step, a separate
  "Before finishing" checklist, a dedicated `<task_completion>` block,
  and a `<testing>` block that's the one place in this entire
  collection using the literal term "self-verification" — "write unit
  tests, add output logs, or use debug statements to verify your
  solutions"). No code-level enforcement confirmed in these prompt-only
  files; see `crush/README.md` for the full breakdown.
- **Cursor** gets visibly more rigorous release over release rather
  than staying flat, useful as a small case study in how one product's
  §7 instructions evolve: earliest versions have only a bounded
  linter-fix cap (3 tries, then ask); by the 2025-09-03 (GPT-5) and CLI
  (2025-08-07) versions it's grown an unconditional "ensure a green
  test/build run" requirement before closing a goal, plus the
  retroactive self-correction clause covered in §10. The "green run"
  phrasing is a second data point (alongside Claude Code's leaked
  "never fake a green result") for that idiom circulating across
  vendors rather than being one company's internal phrasing.
- **Copilot Chat is really N different policies, not one** — prompts
  are selected per model family, so the strength of self-verification
  language a session gets depends entirely on which model is backing
  it: the Anthropic/Claude-family prompt and the GLM prompt are thin
  (one line each, no test-running specifics); the base `GenericEditingTips`
  shared across several families adds a bounded 3-try-then-ask pattern
  keyed to linter diagnostics surfaced automatically in tool output;
  the OpenAI GPT-5.1/5.2/5.4 prompts carry text close to verbatim with
  Codex CLI's "Validating your work" section (both are OpenAI-authored,
  plausibly sharing an internal style guide — a cross-product lineage
  worth flagging on its own); an experimental `gpt54LargePrompt.tsx`
  variant formalizes a hypothesis-before-edit / validate-after-edit
  loop more granular than end-of-task verification but short of Jules's
  true per-write mandate; and the Gemini-family prompt has zero
  verification language at all (confirmed via full-file grep) — the
  same absence found independently in Gemini CLI itself, a different
  product from the same model family. See §10 for the richest single
  instance (`vscModelPrompts.tsx`'s "iron law" block).
- **Devin**: see §10 for its mandatory-checkpoint-tool variant — the
  verification content itself ("Make sure you completed all
  verification steps... such as linting and/or testing") is ordinary
  §7 prose; what's structurally distinctive is that a specific tool
  call is required at that point in the task. **This is specific to
  Devin's autonomous/background web product** — a second, later-mirrored
  capture (`leaked/devin/CLI Prompt.md`, "an interactive command line
  agent from Cognition") has no mandatory checkpoint tool at all: its
  "Verification" section is ordinary prompted-only prose ("Before
  considering a task complete, verify your work... Self-critique: review
  changes for edge cases"), the same shape as the thinner §7 examples
  elsewhere in this doc, with no tool call required to reach it. When
  citing Devin's checkpoint-gated verification, specify the
  background/web variant — see `leaked/devin/README.md`'s CLI-variant
  section for the full comparison.
- **Cline**: one of the thinner instances surveyed — no TESTING/
  VALIDATION section, no bounded-retry pattern, no "hidden tests"
  language anywhere in any of its three system-prompt variants. What
  exists is narrower: `attempt_completion`'s self-report gate (§2 above,
  a procedural "did the last tool call succeed" check, not a
  correctness check) and an optional, browser-only verification path —
  "if you want to test your work, you might use browser_action to
  launch the site... [and check] screenshots" — conditional on browser
  support and phrased as optional, not mandatory.
- **GitHub Copilot CLI** (leaked): ordinary §7 baseline instructions in
  both captures — "Always validate that your changes don't break
  existing behavior," "Run the repository linters, builds and tests to
  understand baseline, then after making your changes" — plus a
  `task_completion` block requiring evidence a background process
  actually started ("verify it is running and responsive (e.g., test
  with `curl`, check process status)"). No SWE-bench-lineage
  reproduce-script echo, no bounded-retry cap. Its Autopilot mode goes
  further, close to §10's rhetorical-escalation register though still
  purely prompted: "Verify before claiming success - Before calling
  `task_complete`, produce evidence the work satisfies the request: run
  the relevant tests/build/lint, reproduce the original symptom and
  confirm it's gone," paired with an explicit negative checklist —
  "When NOT to call `task_complete`: ...Tests, build, or lint are
  failing in code you just changed and you haven't fixed them... You
  wrote code but never ran or otherwise validated it." See §10 for why
  this is filed as prompt-simulated rather than a confirmed code-level
  gate, and §3/§4 for its `rubber-duck` and `code-review` sub-agents.
- **Grok Build** (leaked): an ordinary "green-run" instance —
  `<making_code_changes>`: "Before reporting a task complete, verify it
  actually works: run the test, execute the script, check the output...
  If you can't verify (no test exists, can't run the code), say so
  explicitly rather than claiming success" — the same idiom already
  documented for Claude Code's "never fake a green result" and Cursor's
  "ensure a green test/build run," another data point for that phrase
  circulating cross-vendor rather than being one company's wording. Two
  smaller, structurally distinct additions worth noting alongside it:
  `update_goal`'s `blocked_reason` field states its own bounded-retry
  threshold directly in the tool's JSON Schema description ("Set only
  when truly stuck after 3+ consecutive failed attempts") rather than
  as prose elsewhere in the prompt, and its harness-enforced
  "End-of-turn todo gate" (see §2) is a broader-scoped deterministic
  gate than anything else in this bucket. See
  `leaked/grok-build/README.md` for the full section.

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

## 9. Verification authority handed to the user, not the model

Two leaked sources place the actual accept/reject decision outside the
model entirely — a third pole beyond "self-report" (§7) and "separate
LLM judge" (§3), and structurally distinct from either.

- **Replit's "feedback tools"** — `web_application_feedback_tool`,
  `shell_command_application_feedback_tool`, `vnc_window_application_feedback`
  — all follow the same shape: the agent runs/observes the app, captures
  objective evidence (a screenshot, logs, command output) automatically,
  then asks the user one targeted question and *waits*. Completion
  itself is explicitly deferred: `report_progress`'s description reads
  "Call this function once the user explicitly confirms that a major
  feature or task is complete. Do not call it without the user's
  confirmation." This is neither a deterministic gate (nothing blocks
  the tool from running; it just displays results) nor an LLM judge
  (the judge is a human) — call it **automated evidence-gathering paired
  with a mandatory human-confirmation gate**. One tool in the same
  family, `suggest_deploy`, undercuts its own rigor slightly: "Use this
  tool once you've validated that the project works as expected...
  there is no need to do any follow up steps or verification" —
  "you've validated" is asserted by the model, not mechanically checked
  by the tool that follows it.
- **Warp** inverts the usual §7 shape rather than adding a new one:
  where every other prompted-only source *instructs* the agent to
  verify on its own initiative, Warp's "Task completion" section makes
  verification something the agent must ask permission to even attempt:
  "don't automatically assume the user wants to run the build right
  after finishing an initial coding task... it is also acceptable to
  ask the user if they'd like to lint or format the code." This sits in
  direct tension with the same prompt's general instruction to "bias
  toward action... don't ask for confirmation first" — verification is
  carved out as the one deliberate exception to an otherwise
  action-biased default.

Both differ from §5's `Stop` hooks in the same way: a hook is a
mechanism the *scaffold* exposes and the *user* configures once,
running the same way every time; these two are per-task, conversational,
and require the user's live attention at exactly the moment the agent
would otherwise declare victory.

## 10. Prompt-simulated gates — borrowing the language of enforcement without the code

A pattern that only became visible once enough §7 (prompted-only)
sources were compared side by side: several prompts use categorical,
checklist-style, "MANDATORY"/"BLOCKING"/"no exceptions" language that
*reads* like §2's deterministic gates, while remaining — as far as the
captured system-prompt text shows — pure natural-language instruction
with no confirmed code-level enforcement. Worth naming as its own
pattern because the rhetorical form is doing real work (it's a stronger
ask of the model than an ordinary "please verify your work" sentence)
even though the underlying mechanism is identical to every other §7
entry.

- **Copilot Chat's `vscModelPrompts.tsx` (variants C and D only —
  confirmed absent from variants A and B in the same file, a deliberate
  per-model-variant choice)** carries the most elaborate instance found
  in this whole collection, a named `verification-before-completion`
  principle: "Iron law: NO COMPLETION CLAIMS WITHOUT FRESH VERIFICATION
  EVIDENCE... Gate (must complete all, in order): 1) identify the exact
  command that proves the claim; 2) run the FULL command now... 3) read
  full output, check exit code, count failures; 4) if output confirms
  success, state the claim WITH evidence... 5) only then express
  satisfaction... Rationalizations to reject: 'should work now', 'I'm
  confident', 'just this once'... No exceptions: different words do not
  bypass the rule." It even numbers its own steps as a "Gate" — the
  vocabulary of §2, none of the code.
- **Factory (Droid)'s PR draft/non-draft gate** (§2 above) belongs here
  too: "CODE QUALITY VALIDATION (MANDATORY, BLOCKING)" is checklist
  language tied to an external artifact (PR state) rather than an
  internal tool call, but nothing in the captured prompt confirms
  anything actually enforces it in code.
- **Cursor's 2025-09-03 (GPT-5) prompt** adds a temporally distinct
  variant — a self-correction obligation applied *retroactively*, one
  turn late, rather than a pre-completion gate: "If you report code
  work as done without a successful test/build run, self-correct next
  turn by running and fixing first." This doesn't gate anything before
  the false claim happens; it only asks the model to notice and fix it
  after the fact — a genuinely different temporal shape from every other
  mechanism in this document.
- **Devin's mandatory-checkpoint variant** sits between a rhetorical
  gate and a real one: its `<think>` scratchpad tool has a *required*
  (not merely suggested) trigger before completion — "Before reporting
  completion to the user. You must critically ex[a]mine your work...
  Make sure you completed all verification steps that were expected of
  you, such as linting and/or testing." What's actually enforced (as
  far as the leaked prompt shows) is that the `<think>` tool gets
  called at that point — a real, nameable checkpoint — not that its
  contents constitute a genuine check; the verification itself is still
  unchecked prose inside an unchecked tool call. **Product-surface
  caveat**: this is Devin's autonomous/background web product
  specifically — the separately-captured interactive CLI variant
  (`leaked/devin/CLI Prompt.md`) has no `<think>` tool and no mandatory
  checkpoint at all, just ordinary prompted §7-style verification prose.
  See `leaked/devin/README.md`'s CLI-variant section.
- **GitHub Copilot CLI's Autopilot-mode gate** belongs here too, and is
  closer to Copilot Chat's "iron law" than to Devin's checkpoint-tool
  variant in shape — it's a named negative checklist, not a required
  tool call: "**Verify before claiming success** - Before calling
  `task_complete`, produce evidence the work satisfies the request: run
  the relevant tests/build/lint, reproduce the original symptom and
  confirm it's gone," with an explicit "When NOT to call `task_complete`"
  list (failing tests left unfixed, code "never run or otherwise
  validated"). Nothing in the captured prompt confirms `task_complete`
  itself refuses to fire if the checklist wasn't actually followed —
  the enforcement, as far as this leak shows, is entirely rhetorical,
  the same gap as every other row in this section.

**The common thread**: all five escalate the *rhetoric* of §7 without
crossing into §2's territory (a structural precondition) or §5's (a
user-configured hook actually wired into the agent loop). Whether the
escalation changes model behavior in practice is an empirical question
this doc can't answer from prompt text alone — but it's a measurably
different level of prompt-engineering investment than a source that
just says "please test your changes," and worth tracking as its own
axis of comparison.

## 11. Two more candidate patterns from Google Antigravity

Two findings that don't cleanly fit any of §1–§10, surfaced during a
third research pass on this leaked source (`planning-mode.txt` and
`CLI Prompt.md`, which share the same template near-verbatim).

- **A severity-gated retry/escalation policy tied to a task-mode state
  machine**: "If you find minor issues or bugs during testing, stay in
  the current TaskName, switch back to EXECUTION mode... Only create a
  new TaskName if verification reveals fundamental design flaws that
  require rethinking your entire approach — in that case, return to
  PLANNING mode." Not §1's flat reproduce-fix-verify loop (no
  reproduce-script mechanic, no explicit "consider edge cases" step),
  not §2's deterministic gate, not §3's separate-LLM judge — a
  two-tier branch on *what kind* of failure was found, each routed to
  a different recovery mode (patch-in-place vs. restart planning).
  Every retry-on-failure mechanism elsewhere in this doc (SWE-agent's
  `ScoreRetryLoop`, Augment's ensembler) treats all failures the same;
  this is the only source that classifies the failure itself before
  deciding how to recover from it.
- **"Artifact-as-verification-record"**: a required, persistent
  Markdown file (a "Walkthrough," `<appDataDir>/brain/
  <conversation-id>/walkthrough.md`) documenting "Changes made / What
  was tested / Validation results," with embedded screenshots/
  recordings as evidence, explicitly *updated* rather than recreated
  on related follow-up work. The closest existing entry is Jules's
  Playwright-screenshot-as-proof mechanism (§6/leaked/jules/README.md)
  — both tie verification to a generated artifact rather than a text
  assertion — but Jules's screenshot is submitted as a single
  completion-time proof, while Antigravity's Walkthrough is a durable,
  cumulative, cross-session document that persists and gets amended,
  closer to a lab notebook than a one-shot piece of evidence. This
  whole mechanism is scoped to complex/planned work only — trivial,
  investigatory, or minor-follow-up edits are explicitly told to skip
  it entirely ("you continue your work WITHOUT making a plan or
  requesting user review"), so it coexists with, rather than replaces,
  an ordinary no-verification path for small changes.

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
- **Goose**: the cleanest confirmed absence in the whole survey — every
  one of the folder's ten prompt files was read in full and a targeted
  keyword search across all of them turns up nothing. This is stronger
  than "prompted-only with no enforcement" (§7): those sources at least
  *instruct* verification; Goose's captured prompts don't instruct it
  at all. The sub-agent prompt's only completion-adjacent line is a
  reporting instruction ("Clearly indicate when your task is complete"),
  never a checking instruction. Standard caveat applies: this
  collection holds prompt text only, so it's possible test-running
  logic lives in Goose's surrounding Rust orchestration code, not
  captured here.
- **Windsurf**: confirmed absence, and a striking contrast given this
  is by a wide margin the richest tool surface in the whole collection
  (30 tools, full browser automation, deployment integration). The
  closest thing to relevant content is debugging advice ("add test
  functions and statements to isolate the problem") — diagnostic, not
  a check that a fix is correct — and an instruction to *demonstrate*
  a change by running it for the user, not to verify it worked. No
  test-runner tool, no lint-checking tool (only a passive labeling
  parameter on the edit tool), no bounded-retry cap, no review command.
- **Aider**: not a confirmed absence, unlike the two above — a real
  research gap worth distinguishing from a checked-and-empty result.
  All four local prompt files return zero hits for test/lint/verify/
  build language, but `base_prompts.py` defines empty hook points
  (`shell_cmd_prompt`, `shell_cmd_reminder`) meant to be populated by a
  separate `aider/coders/shell.py` module — not fetched into this
  collection — that per Aider's public documentation is where its real
  `--auto-test`/`--lint-cmd` feature lives. The honest claim here is
  "not found in the files this collection captured," not "Aider has no
  self-verification."
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
  completely different mechanism layered alongside it. The second
  research pass found the same underlying lesson ("verify before
  claiming done," "don't touch the tests") converging independently in
  general-purpose IDE assistants (Copilot Chat's `AlternateGPTPrompt`
  and Grok prompt, Devin) that share no lineage with the four
  SWE-bench-harness sources — this looks like the field re-deriving the
  same idea repeatedly, not one convention spreading by copying.
- **Within the "prompted-only" bucket (§7) there is a whole second
  spectrum, from nothing to elaborate rhetoric, that a binary
  has-it/doesn't-have-it framing would flatten.** At one end: Goose and
  Windsurf have no verification instruction of any kind, despite Windsurf
  having the richest tool surface surveyed anywhere in this collection —
  more tooling doesn't imply more verification discipline. In the
  middle: thin, single-line instructions (Cline, Copilot Chat's
  Anthropic and GLM variants). At the dense end: Crush repeats
  verification language at nearly every structural checkpoint of its
  prompt, and Copilot Chat's `vscModelPrompts.tsx` (§10) escalates to
  numbered "Gate," "No exceptions" language that borrows §2's rhetorical
  form while remaining, as far as any of this collection's captured
  prompts show, unenforced by code. None of that escalation moves a
  source out of §7 — it's still purely instructional — but treating
  "has prompted verification text" as one undifferentiated category
  would miss a real and measurable difference in how much a vendor
  invested in the wording.
- **A third pole exists beyond "the model self-reports" and "a separate
  LLM judges"**: handing the accept/reject call to the human user
  instead (§9). Replit's feedback tools gather evidence mechanically
  (screenshots, logs, command output) and then require the user to
  answer a direct question before the agent proceeds — neither a
  deterministic gate nor an LLM judge, but a third architecture with
  its own tradeoff: it can't be fooled by either a dishonest model
  self-report or a manipulable judge call, at the cost of requiring the
  user's live attention at exactly the moment automation is usually
  most valuable. Warp's inversion (verification requires *asking*
  before running, rather than running and then asking) shows the same
  human-authority instinct taken to an extreme where even attempting
  the check isn't the agent's default move.
