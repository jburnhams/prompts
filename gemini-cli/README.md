# Gemini CLI

- **Type**: Coding agent (Google's terminal coding agent)
- **License**: Apache-2.0
- **Source**: https://github.com/google-gemini/gemini-cli
- **Retrieved from**: `main` branch,
  `packages/core/src/prompts/` (2026-07-10)

Not included: `packages/core/src/core/prompts.ts` — a thin, mostly-deprecated
wrapper (`getCoreSystemPrompt`/`getCompressionPrompt`) that just delegates to
`PromptProvider`, which lives in the files below.

## Files

- `promptProvider.ts` — assembles the final system prompt: picks between
  current/legacy snippets, injects hierarchical memory (`GEMINI.md` files),
  interactive-mode and topic-narration behavior, and the conversation
  compression prompt.
- `snippets.ts` — the current prompt content, built from named snippets
  referencing the CLI's actual tool names (glob, grep, read/write file,
  shell, plan mode, task-tracker, sub-agent, etc.) so the text stays in sync
  with the tool implementations.
- `snippets.legacy.ts` — an older version of the snippet set, kept for
  backward compatibility/fallback.

## Tool surface

Every tool name in the prompt text is imported from a shared
`tools/tool-names.js` constants module rather than hardcoded as a string
— the prompt literally cannot drift out of sync with the tool
implementations' actual names.

- **Shell**: `SHELL_TOOL_NAME`, with an explicit background-execution
  parameter (`SHELL_PARAM_IS_BACKGROUND`) — async/long-running command
  support baked into the tool schema, not just prompt instruction (same
  capability as Windsurf's `run_command`/`command_status` pair, via a
  single tool with a flag instead of two tools).
- **Search**: `GLOB_TOOL_NAME` + `GREP_TOOL_NAME` (with fine-grained
  params: match cap, include/exclude patterns, before/after context
  lines), plus a specialized `codebase_investigator` **sub-agent**
  reserved for "complex refactoring, codebase exploration or
  system-wide analysis" — a step up from plain grep/glob, distinct from
  the general-purpose `AGENT_TOOL_NAME` delegate.
- **Editing**: `EDIT_TOOL_NAME`, `old_string`/`new_string`-based (see
  `coding-agent-approaches.md` §5), plus `WRITE_FILE_TOOL_NAME` for new
  files.
- **Planning/tracking**: `WRITE_TODOS_TOOL_NAME`, plus a **separate**
  tracker tool family (`TRACKER_CREATE_TASK_TOOL_NAME`,
  `TRACKER_LIST_TASKS_TOOL_NAME`, `TRACKER_UPDATE_TASK_TOOL_NAME`) and
  dedicated `ENTER_PLAN_MODE_TOOL_NAME`/`EXIT_PLAN_MODE_TOOL_NAME` tools —
  planning is a first-class tool-mediated mode transition here, not just
  a prompt instruction to "make a plan."
- **User interaction**: `ASK_USER_TOOL_NAME` — a dedicated tool for
  asking the user a clarifying question, rather than just ending a turn
  with a question in prose.
- **Browser/web**: no web-fetch/search tool constant imported in
  `snippets.ts` — if Gemini CLI exposes one elsewhere in the product, it
  isn't referenced in this particular prompt-assembly file.
- **Multimodal**: not addressed in what's captured here.
- **Sandbox/isolation**: environment-conditional text for macOS Seatbelt
  vs. a generic sandbox container vs. no sandbox (see
  `coding-agent-approaches.md` §3) — the *description* of the sandbox is
  dynamic, though the sandboxing itself is enforced outside the prompt.
- **Extensibility**: `ACTIVATE_SKILL_TOOL_NAME` for its skills system,
  `UPDATE_TOPIC_TOOL_NAME` for narrating topic changes mid-session.

## Sub-agents

Framed explicitly as an **orchestration/context-management strategy**,
not just a search convenience — the "Available Sub-Agents" section opens
by naming the model's own context window as the resource being
protected: "Operate as a **strategic orchestrator**. Your own context
window is your most precious resource... use sub-agents to 'compress'
complex or repetitive work." When delegated, "the sub-agent's entire
execution is consolidated into a single summary in your history."

- **Named, specialized agents invoked by name** through `AGENT_TOOL_NAME`
  with an `agent_name` parameter — "You MUST delegate tasks to the
  sub-agent with the most relevant expertise" — rather than one
  general-purpose delegate. `codebase_investigator` is the one named
  explicitly, reserved for "complex refactoring, codebase exploration or
  system-wide analysis."
- **Concrete delegation triggers given, not left to judgment alone**:
  "Repetitive Batch Tasks" is defined quantitatively — "more than 3
  files or repeated steps" (e.g. "Add license headers to all files in
  src/", "Fix all lint errors in the project") — a rare case in this
  collection of a numeric threshold for *when to delegate*, not just
  when to skip planning (contrast Codex CLI's "skip the plan tool for
  the easiest 25%" framing, a similar quantified-threshold instinct
  applied to a different decision).
- **Explicit concurrency-safety mandate, phrased as a hard rule**: "You
  should NEVER run multiple subagents in a single turn if their
  abilities mutate the same files or resources... Only run multiple
  subagents in parallel when their tasks are independent... or if
  parallel execution is explicitly requested by the user." This is a
  file-conflict-aware version of the generic "batch independent tool
  calls" instruction most sources give for ordinary tools — here scoped
  specifically to write-safety across concurrently-running agents.
- **No sub-agent system prompt captured**: like leaked Claude Code, this
  file only shows the orchestrator-side tool/delegation instructions,
  not what system prompt (if any) `codebase_investigator` or other named
  sub-agents run under.
