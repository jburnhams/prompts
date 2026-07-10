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
