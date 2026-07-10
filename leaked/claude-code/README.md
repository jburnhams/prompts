# Claude Code (leaked extraction)

- **Type**: Coding agent · **Vendor**: Anthropic · **Status**: closed source
- **Mirror source**: https://github.com/x1xhlol/system-prompts-and-models-of-ai-tools/tree/main/Anthropic/Claude%20Code (2026-07-10)

Included for comparison purposes even though this collection is itself
built using Claude Code — a leaked extraction may differ from (and lag
behind) the real thing, so treat this as a data point, not a spec.

## Files
- `Prompt.txt` — extracted system prompt.
- `Tools.json` — extracted tool/function definitions.

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
