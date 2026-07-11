# Claude Code (leaked extraction)

- **Type**: Coding agent · **Vendor**: Anthropic · **Status**: closed source
- **Mirror source**: https://github.com/x1xhlol/system-prompts-and-models-of-ai-tools/tree/main/Anthropic/Claude%20Code (2026-07-10)

Included for comparison purposes even though this collection is itself
built using Claude Code — a leaked extraction may differ from (and lag
behind) the real thing, so treat this as a data point, not a spec.

## Files

**Original extraction** (thin, dated):
- `Prompt.txt` — extracted system prompt.
- `Tools.json` — extracted tool/function definitions.
- [`architecture-notes.md`](./architecture-notes.md) — a synthesized
  summary of Claude Code's internal architecture (agentic loop,
  permission system, multi-agent "Team" coordination, plugins/skills,
  feature flags, MCP integration, memory) drawn from a separate, much
  larger alleged leak of the **full TypeScript source** (not just the
  prompt) at
  [`tanbiralam/claude-code`](https://github.com/tanbiralam/claude-code).
  Not stored here as source — see that file for provenance, caveats
  (unverified authenticity, confirmed stub code in security-sensitive
  areas), and methodology.

**A dramatically richer, later capture**, from a different, actively-
maintained aggregator (`asgeirtj/system_prompts_leaks`, retrieved
2026-07-11) — see "A richer capture" below for full provenance and
authenticity notes:
- `claude-code-2.1.172-opus-4.6.md` — the single most valuable file
  here: a versioned build (2.1.172), and — per direct comparison
  against this live session's own system prompt — a **near-verbatim
  match** to a real, current Claude Code harness prompt (same section
  order, same Git Safety Protocol bullets, same worked examples in the
  `Agent` tool description). Treat this one as strong corroborating
  evidence for everything else in this folder, not just "another
  capture."
- `claude-code-2.1.172-opus-4.8.md` — same build, a different,
  visibly newer and more condensed prompt rewrite (`# Harness` /
  `# Session-specific guidance` / `# Environment` / `# Context
  management` headers) not yet seen in the live session used for
  comparison — apparently a preview of an in-progress rewrite.
- `claude-code-2.1.172-fable-5.md` — ~98% identical to the opus-4.8
  capture (only model-identity strings differ), *except* for one
  additional autonomy-mode block (see the README's Sub-agents section
  below) — kept specifically for that diff, not for general
  redundancy.
- `claude-code-docs-assistant.md` — a different product: the docs-site
  "Ask AI" chat assistant, not the CLI's own system prompt. Kept for
  completeness, tangential to the rest of this collection.
- `deferred-tools.md` — the catalog of tools loaded on-demand rather
  than always-present (23 tools: `Cron{Create,Delete,List}`,
  `Enter/ExitPlanMode`, `Enter/ExitWorktree`, `Monitor`, `NotebookEdit`,
  `PushNotification`, `RemoteTrigger`, `ScheduleWakeup`, `SendMessage`,
  `Task{Create,Get,List,Output,Stop,Update}`, `Team{Create,Delete}`,
  `WebFetch`, `WebSearch`) — confirmed, tool-for-tool almost exactly,
  against this live session's own deferred-tool list.
- `bundled-skills/` — 18 of Claude Code's actual internal skill
  prompts (`init.md`, `compact.md`, `verify.md`, `security-review.md`,
  `keybindings-help.md`, `loop.md`, `code-review.md`, `schedule.md`,
  `batch.md`, `fewer-permission-prompts.md`, and others — see below).
  Two files (`claude-api.md`, `update-config.md`) are large reference
  docs (500KB+/140KB) matching skills already loaded in this session;
  truncated here to a representative excerpt rather than stored in
  full, since the bulk is reference material rather than
  agent-architecture content.

**Two files from the same batch were excluded as likely unreliable**:
`glob-tool.md` and `grep-tool.md` were written in a polished-tutorial
register (comparison tables, "Tips & gotchas" sections) that matches
no other genuine capture in this collection and doesn't match this
live session's own terse, four-bullet `Glob`/`Grep` tool descriptions
— probable fabrication or heavy embellishment rather than a real
extraction, so they weren't kept. `bundled-skills/review.md` was kept
but should be read with a caveat: it references `docs/agents/
issue-tracker.md` and a slash command `/setup-matt-pocock-skills`,
naming that suggests a third-party/community skill rather than an
Anthropic-authored one — the aggregator's "bundled skills" folder
appears to mix genuine built-ins with marketplace skills from the same
captured session.

## Tool surface

Per the extracted `Tools.json`: `Task` (sub-agent delegate), `Bash`,
`Glob`, `Grep`, `LS`, `ExitPlanMode`, `Read`, `Edit`, `MultiEdit`,
`Write`, `NotebookEdit`, `WebFetch`, `TodoWrite`, `WebSearch`,
`BashOutput`, `KillBash`.

- **Shell**: `Bash`, with `BashOutput`/`KillBash` as separate tools for
  polling a background command's output and terminating it — the same
  async-shell capability seen via a single flag in Gemini CLI
  (`SHELL_PARAM_IS_BACKGROUND`) or a dedicated status tool in Windsurf
  (`command_status`), here split into two distinct named tools.
- **Search**: `Glob` + `Grep` (no semantic/AST-aware search tool
  extracted here, unlike leaked Cursor's `codebase_search`).
- **Editing**: `Edit` (single old/new-string replace) and `MultiEdit`
  (batch variant) — same split as Copilot Chat's
  `ReplaceString`/`MultiReplaceString`.
- **Notebooks**: `NotebookEdit` — a dedicated tool, though (unlike
  Copilot Chat) no separate run-cell or get-summary tool in this
  extraction.
- **Browser/web**: `WebFetch` and `WebSearch` as two distinct tools
  (fetch a known URL vs. search generally) — no browser-automation tool.
- **Planning**: `TodoWrite`, `ExitPlanMode` (a dedicated mode-transition
  tool, same idea as Gemini CLI's `ENTER_PLAN_MODE_TOOL_NAME`/
  `EXIT_PLAN_MODE_TOOL_NAME`).
- **Multimodal**: not indicated by the tool names alone.
- **Sandbox/isolation**: not indicated.

As with the prompt text itself, treat this tool list as one dated
snapshot, not a guaranteed-current spec.

## Sub-agents

The full `Task` tool description in `Tools.json` is the most detailed
sub-agent specification captured anywhere in this collection — worth
reading as the reference case other sources' briefer mentions can be
compared against.

- **Typed agent registry, not a free-form delegate**: the description
  enumerates named agent types with their own tool scopes —
  `general-purpose` (`Tools: *`), `statusline-setup` (`Tools: Read,
  Edit`), `output-style-setup` (`Tools: Read, Write, Edit, Glob, LS,
  Grep`) — and the caller must pass a `subagent_type` parameter picking
  one. A sub-agent's tool access is narrower than the orchestrator's by
  design for anything other than `general-purpose`.
- **Explicit "when NOT to use" guidance**: reading a known file path,
  searching for an exact class name, or searching within 2-3 known
  files should go through `Read`/`Glob` directly instead — the Task
  tool is reserved for genuinely open-ended, multi-round work, framed
  as a speed/cost tradeoff, not a blanket "always delegate" rule.
- **Protocol is strictly one-shot, stateless, and opaque mid-flight**:
  "Each agent invocation is stateless. You will not be able to send
  additional messages to the agent, nor will the agent be able to
  communicate with you outside of its final report." The orchestrator
  never sees intermediate tool calls the sub-agent makes — only the
  single final message.
- **Result handling is the orchestrator's job, not automatic**: "The
  result returned by the agent is not visible to the user. To show the
  user the result, you should send a text message back to the user
  with a concise summary" — the sub-agent's report is folded into the
  orchestrator's own next turn as ordinary tool-result content, then
  the orchestrator decides what (if anything) to surface.
- **The calling prompt must front-load everything**: since there's no
  back-and-forth, "your prompt should contain a highly detailed task
  description... and you should specify exactly what information the
  agent should return." The sub-agent has no access to the user's
  original intent unless the orchestrator explicitly restates it,
  including whether it's expected to write code or just research.
- **Trust posture**: "The agent's outputs should generally be
  trusted" — stated as an explicit instruction, not left implicit.
- **Concurrency**: "Launch multiple agents concurrently whenever
  possible... use a single message with multiple tool uses" — the same
  batched-parallel-tool-call convention used for ordinary tools (see
  `coding-agent-approaches.md` §4), applied to sub-agent fan-out too.
- **No system prompt shown for the sub-agent side**: unlike Goose's
  `subagent_system.md` or Copilot Chat's `ExecutionSubagentPrompt`/
  `SearchSubagentPrompt`, this extraction only shows the *tool
  description* the orchestrator sees — what system prompt (if any) the
  spawned agent itself runs under isn't captured here. See
  `agent-subagent-architectures.md` for the cross-source comparison.
- **Correction from the richer, later capture**: `Task` has since been
  renamed `Agent` (all three versioned files use `Agent`, not `Task`)
  — the sub-agent contract itself (stateless, one-shot, "trust but
  verify," concurrent-batch launch) is unchanged in substance, just the
  tool name. The richer capture also adds a real named agent registry
  in place of the generic `general-purpose`/`statusline-setup`/
  `output-style-setup` trio above: `claude`, `claude-code-guide`,
  `Explore`, `general-purpose`, `Plan`, `statusline-setup` — see
  `architecture-notes.md`'s Multi-agent section for the full current
  list and everything else this capture adds (a real, tool-confirmed
  `TeamCreate`/`TeamDelete`/`SendMessage` schema promoting that
  section from "inferred from source" to "confirmed via captured
  prompt," plus an entirely new `Workflow` orchestration tool).
- **A session-mode-dependent prompt axis not previously documented**:
  diffing the `fable-5` capture against `opus-4.8` (same build,
  different model) turns up one extra block present only in `fable-5`:
  an "operating autonomously, the user is not watching in real time"
  section. This means the system prompt is parameterized by session
  mode (interactive vs. autonomous/background), not just by model
  identity and CLAUDE.md content — a third independently-gated
  prompt-assembly axis alongside the two `architecture-notes.md`
  already documents (CLAUDE.md loading, git-status injection).

## Bundled skills

18 real skill files captured in `bundled-skills/` (see Files above for
which two were excluded). One-line summary of each:

| Skill | Does |
|---|---|
| `init.md` / `init-new.md` | Generate/refresh `CLAUDE.md`; `init-new.md` is a richer, phased version with `AskUserQuestion`-driven scope selection (project vs. personal CLAUDE.md, skills, hooks) |
| `debug.md` | Enable/read Claude Code's own debug log, for troubleshooting the session itself |
| `loop.md` | Drives `/loop` autonomous recurring-check behavior via `ScheduleWakeup` |
| `artifact-design.md` | Design-system guidance for Artifacts |
| `simplify.md` | 4 parallel cleanup-angle agents (reuse/simplification/efficiency/altitude), then applies fixes — quality only, not bug-hunting |
| `fewer-permission-prompts.md` | Mines transcripts for read-only tool calls, proposes a settings.json allowlist |
| `batch.md` | Plan-mode-gated large-scale parallel refactor: decomposes into worktree-isolated background workers |
| `code-review.md` | 8-angle parallel finder + 1-vote recall-biased verifier, ≤10 findings, CLAUDE.md-conventions-aware |
| `compact.md` | The actual `/compact` summarization prompt — matches `architecture-notes.md`'s existing 9-section description exactly, plus one addition: an explicit instruction to preserve "security-relevant instructions or constraints" verbatim through compaction |
| `schedule.md` | Drives `RemoteTrigger` to manage claude.ai cloud "Routines" |
| `security-review.md` | The built-in `/security-review` — diff-scoped, confidence-scored, hard-exclusion-listed (DoS, secrets-on-disk, rate-limiting-by-design). A **second, functionally distinct mechanism** from the hook-based, automatic `skills/anthropic/security-guidance/` plugin already in this collection — this one is manually invoked and multi-agent (find → parallel false-positive filter), not hook-triggered; document both, don't conflate them |
| `verify.md` / `run.md` | A much more opinionated self-verification doctrine than `architecture-notes.md`'s brief existing section — "verification is runtime observation... don't run tests, don't typecheck" — plus app-launching patterns by project type |
| `keybindings-help.md` | A full keybinding customization system (`~/.claude/keybindings.json`, contexts, chords, `/doctor` validation) — a genuinely new UI mechanism with zero prior overlap in this collection |
| `review.md` | Two-axis (Standards/Spec) PR review via parallel sub-agents — possibly third-party, see the authenticity caveat above |
| `claude-api.md` (truncated here) | Reference skill for building Claude-API apps |
| `update-config.md` (truncated here) | Settings.json configuration skill |
