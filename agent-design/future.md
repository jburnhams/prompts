# Future considerations

Everything here is a documented, well-precedented pattern from this
repo's research — left out of v1 for leanness, not because it's a bad
idea. Nothing here should influence a v1 implementation; it exists so
these ideas are tracked instead of forgotten or silently re-litigated
later. See `README.md` for the v1 design itself.

Two shapes of deferred work:

- **Deferred entirely** — v1 has no mechanism in this area at all.
- **Escalation triggers** — v1 ships a simple mechanism on purpose, with
  a named, more expensive upgrade to reach for only if the simple
  version proves insufficient in practice.

## Deferred entirely

- **Typed sub-agent registry beyond three types.** Coding mode has one
  delegate type; review mode has two (`reviewer`, `validator`). Claude
  Code, Gemini CLI, and Amp all show the next step (named, narrower
  types for specific jobs) once there's a concrete need.
- **Addressable/resumable sub-agents.** Codex CLI's `spawn_agent`/
  `send_input`/`wait_agent`/`close_agent` and OpenCode's queue-onto-a-
  running-job model (`agent-subagent-architectures.md` §2) are the
  natural upgrade once a coding task needs to steer a sub-agent
  mid-flight rather than fire-and-forget it. Recursive delegation
  (`general-purpose` calling `Task` itself, currently disallowed —
  `tools.md`) is the same underlying question one level deeper.
- **Numeric confidence scoring for review findings.** The validator
  pass here is binary (confirmed / not confirmed), matching Anthropic's
  own skill. TuringMind's 0-100 rubric or BMAD's 4-bucket triage
  (`code-review-approaches.md` §6) are richer but add real tuning
  surface — worth adding once false-positive rate is actually measured.
- **`MultiEdit`, `NotebookEdit`, `WebFetch`/`WebSearch`, browser/deploy
  tooling.** None are load-bearing for "implement a Jira ticket" or
  "review a diff."
- **Memory-file conventions (`AGENTS.md`/`CLAUDE.md`-equivalent).**
  Reading a project's own convention file is just a `Read` call in the
  coding-mode prompt's workflow, not a dedicated tool — no need to
  invent one.
- **A tiered permission/approval subsystem.** Codex CLI's five
  cooperating subsystems and Gemini CLI's policy engine
  (`agent-permissions-approval.md`) are the eventual ceiling; v1 gets a
  single hard rule (destructive git operations and anything outside the
  task's declared `mode` require `AskUser`) rather than a graded system.
- **Context compaction.** A run that outgrows its budgets ends via the
  final-turn nudge with an honest partial report (`formats.md` §7)
  rather than summarizing and continuing — compaction is a genuine
  subsystem (`agent-context-compaction.md`) and the natural v2 lever if
  budget-exhausted runs turn out to be common.
- **An LLM judge over completed work.** Claude Code's internal
  adversarial verification subagent is the ceiling
  (`agent-self-verification.md` §3); v1's completion-integrity story is
  deterministic only (checklist gate + harness `git status`
  cross-check), which can't be prompt-injected or talked out of firing.
- **Diff-as-file instead of diff-in-prompt-thrice.** The review
  orchestrator currently carries the diff in its envelope *and* copies
  slices into each specialist's `Task` prompt. Having the harness also
  write the diff to a scratch-dir file and letting sub-agents `Read` it
  would cut the duplication for large PRs — at the cost of sub-agents
  starting cold on what they should read. Worth measuring before
  adopting. (Also the fix that removes the specialist-fan-out
  duplication multiplier from `formats.md`'s large-diff threshold math.)
- **Double-coverage on the bugs lens.** Anthropic's `/code-review` skill
  runs *two* bug-finder agents in parallel for recall and lets
  validation handle the overlap; Forge runs one specialist per lens.
  Cheap to add later if recall measures low — the validator + dedup
  machinery already handles the duplicate-findings consequence.
- **Turn caps for sub-agents.** Copilot Chat's `isLastTurn` nudge (the
  same mechanism `formats.md` §7 uses for the whole run) applied one
  level down, to individual `Task` calls. The run-level budget is
  enough for v1; a runaway sub-agent still terminates when the parent
  run's own budget is hit.
- **A cap on `AskUser` suspend/resume cycles.** A task can suspend and
  resume more than once with no built-in limit in v1 (`formats.md` §5).
  A real deployment would likely want one (e.g. "escalate instead of
  asking a third time") — left unspecified rather than picking a number
  with no concrete reason behind it.

## Escalation triggers (v1 ships simple; upgrade only if needed)

- **PR-Agent-style per-hunk line-number injection**, if mis-anchored
  review comments show up in practice. V1 bakes a plain unified diff
  and validates anchors after the fact, degrading a bad anchor to a
  visible `file:line`-prefixed general comment rather than silently
  mis-posting (`formats.md` §1b, `README.md`'s "Comment anchoring"
  decision-log row). PR-Agent's custom `__new hunk__`/`__old hunk__`
  format with line numbers injected per hunk (`code-review-approaches.md`
  §3) removes the hunk-arithmetic step that causes mis-anchoring in the
  first place, at the cost of a less lean diff format.
- **Command-level `Bash` permission filtering**, once destructive- or
  out-of-scope-command risk from the prompt-only read-only-git rule
  becomes a real problem. `Bash` stays wired in read-only modes for
  legitimate read-only commands; its no-write rule is prompt-enforced
  only in v1 because command-level filtering is a real permission
  engine (`tools.md`) — the natural first instance of the tiered
  permission/approval subsystem above, scoped down to just this one
  tool.
