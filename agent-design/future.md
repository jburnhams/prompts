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
  (`agent-permissions-approval.md`) are the eventual ceiling; v1 gets
  structural mode wiring, the git-write blocklist, and one hard prompt
  rule (anything outside the task's declared `mode` requires `AskUser`)
  rather than a graded system. If this is ever built, the field's most
  interesting converged pattern is worth knowing about up front: three
  vendors independently arrived at "a second, cheaper LLM judges the
  first model's proposed actions" (Gemini CLI's Conseca, Codex's
  Guardian, Claude Code's internal-only `yoloClassifier`), always
  layered *on top of* a static rule engine that keeps working without
  it, and failing closed on error (`agent-permissions-approval.md` §2).
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
- **Per-role model selection.** V1 runs every orchestrator and
  sub-agent on one model. The precedent for varying it per role is
  strong and specific: Anthropic's own `/code-review` skill assigns
  Haiku to triage, Sonnet to conventions checks, and Opus to bug-finding
  and validation; Amp pins its `oracle` to a different vendor's model
  entirely; GitHub Copilot CLI pins a model per sub-agent YAML with one
  (`rubber-duck`) deliberately inheriting the user's live choice
  (`agent-subagent-architectures.md` §3). A cheap-model triage pass and
  an expensive-model validator are the natural first split once cost
  per review run is measured.
- **A hard write-protect on the project-conventions file.** V1 defends
  the conventions file (instruction to every future run, so a
  self-instruction-poisoning target) with a prompt rule plus a post-run
  harness flag on any diff touching it (`formats.md` §3a). The
  structural upgrade is Roo Code's `RooProtectedController`
  (`agent-permissions-approval.md` §3): `.roorules*`/`AGENTS.md` and
  kin are write-protected in code "regardless of autoapproval
  settings" — the only source in the collection that hard-protects the
  agent's own instruction files from the agent. For Forge that would
  mean the harness rejecting `Edit`/`Write` calls targeting the
  conventions path unless the run was dispatched with an explicit
  this-ticket-may-edit-conventions flag. Deferred because the post-run
  flag already makes the failure visible rather than silent; upgrade if
  flagged violations actually occur.
- **Repo-file content sanitization.** The envelope/FetchJira sanitizer
  (`formats.md` §1) deliberately does not touch file contents returned
  by Read/Grep — mangling source bytes would break Edit's exact-match
  contract. A malicious file in a reviewed PR could therefore still
  carry invisible-Unicode payloads to a `reviewer` sub-agent that Reads
  it. A display-layer-only strip (sanitize what the model sees, keep
  the on-disk bytes canonical for Edit) is the plausible fix if this
  ever shows up in practice; no source in the collection does it today.

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
- **General command-level `Bash` permission filtering**, beyond the
  narrow git-write blocklist v1 does ship (`tools.md`). The v1
  blocklist covers exactly one command family (git write subcommands),
  because Augment SWE-bench Agent's precedent shows that specific check
  is a few lines of code; everything else about Bash — read-only-mode
  no-write rules, destructive non-git commands, network use — remains
  prompt-enforced in v1, because filtering *arbitrary* commands
  correctly (compound commands, subshells, `xargs`, script files) is a
  real permission engine: OpenCode's tree-sitter AST parsing of
  bash/PowerShell and Gemini CLI's per-sub-command redirection
  detection (`agent-permissions-approval.md` §2-3) are the field's
  benchmarks for doing it properly, and both are whole subsystems. The
  natural first instance of the tiered permission/approval subsystem
  above, scoped down to just this one tool.
- **Read-only-git `Bash` for `reviewer`/`validator` sub-agents**, if
  pre-existing-vs-introduced misjudgments show up in posted findings.
  V1 gives review sub-agents no `Bash` at all (`tools.md`), so a
  validator's only view of the pre-change code is the diff's own `-`
  lines and context — it can't `git show base_sha:file`. The validator
  prompt tells it to reject when that view is insufficient, which
  trades recall for safety. Granting a git-inspection allowlist
  (agent37/TuringMind's shape, `code-review-approaches.md` §10) is the
  upgrade, but it depends on the command-level filtering entry above
  existing first — without it, "read-only git only" would be
  prompt-enforced, exactly what the structural-gates principle rejects.
- **Batched review delivery via GitHub's pending-review flow**, if
  per-finding notification noise draws complaints. V1's pipeline posts
  one `AddComment` per finding, which means N findings = N separate
  notification events for the PR author. `gemini-code-review` is the
  collection's precedent for the alternative (create pending review →
  add comments → submit once, event type locked to `COMMENT` —
  `code-review-approaches.md` §9): one notification, atomic delivery,
  and a natural place to hard-lock "never APPROVE/REQUEST_CHANGES" at
  the API layer. Harness-side change to how `AddComment` calls are
  flushed, not a schema change — the tool surface Forge sees can stay
  identical.
