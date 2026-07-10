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
