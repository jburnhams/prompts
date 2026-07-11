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
- **Correction — a sub-agent system prompt is captured after all, by
  reading the live source**: `codebase_investigator` (defined in
  `packages/core/src/agents/codebase-investigator.ts`) has its own
  distinct persona ("a hyper-specialized AI agent" instructed to build
  a mental model, find key modules, understand *why* code is written
  that way, foresee ripple effects), not the main orchestrator persona
  with a restricted toolset — read-only tool access (`LS`/`Read`/
  `Glob`/`Grep`), a preview-Flash model config, and hard
  `maxTurns: 50`/`maxTimeMinutes: 10` limits enforced in code, plus
  structured JSON output (`SummaryOfFindings`/`ExplorationTrace`/
  `RelevantLocations`) rather than free text.
- **`codebase_investigator` is one of several named built-ins, not the
  only one**: `cli_help` (own persona as "an expert on Gemini CLI,"
  single docs tool, maxTurns 10/maxTimeMinutes 3), `generalist`
  (inherits the orchestrator's own model config and full tool registry
  — the closest analog to Claude Code's `general-purpose` type),
  `browser_agent` (Chrome DevTools MCP wrapper, disabled by default,
  enforces its own single-instance concurrency lock — "Cannot launch a
  concurrent browser agent"), and a background, non-interactive
  `confucius`/"Skill Extractor" agent invoked at session boundaries
  (not mid-task delegation) to mine past transcripts for reusable
  memories. Custom agents are also loadable from `.gemini/agents/`
  (project) and `~/.gemini/agents/` (user) via YAML, plus
  `RemoteAgentDefinition`s reached over the **A2A (Agent2Agent)
  protocol** for external, non-Gemini-CLI agent services — a
  federation capability with no equivalent yet documented for any
  other source in this collection.
- **The default calling protocol is Claude-Code-style blocking
  one-shot** (`LocalSubagentInvocation`/`RemoteAgentInvocation`: one
  call, one internally-run turn loop, one final `ToolResult`) — but the
  codebase already contains a fully-built, **experimental** stateful
  alternative (`LocalSessionInvocation`/`RemoteSessionInvocation`,
  gated behind `experimental.adk.agentSessionSubagentEnabled`, default
  `false`, requires a restart) that persists session state across calls
  and supports `session.send()`/`session.abort()` — architecturally
  closer to the addressable Codex/OpenCode/OpenHands designs elsewhere
  in this collection, though even this experimental path enforces
  single-stream semantics (can't send while a stream is active), so
  it's resumable-sequential rather than true concurrent mid-run
  interrupt.
- **Recursion prevention is a code-level guard, not just a prompt
  instruction**: in the local executor, any tool of `kind ===
  Kind.Agent` (i.e. the delegation tool itself) is stripped from a
  spawned sub-agent's own tool registry before it runs — "We do not
  allow agents to call other agents," enforced structurally even
  against a wildcard tool grant, a stronger guarantee than most
  sources' prompt-level recursion rules (see
  `agent-subagent-architectures.md` §6).
- **No general numeric concurrency cap found** comparable to Codex's
  `AgentControl` or OpenHands's `max_children`; the only concrete
  concurrency guard confirmed is the browser agent's own single-instance
  lock. The file-conflict-safety *instruction* quoted above is real, but
  (like Claude Code's) it's a prompt-level rule the model could in
  principle ignore, not an enforced limit.
- **Policy-engine integration**: Gemini CLI's TOML-based policy engine
  treats `agent_name` as a "virtual tool alias" — rules can allow/deny
  specific named sub-agents, and can further scope a rule to calls
  *originating from within* a given sub-agent. Plan Mode's policy
  file explicitly allowlists only `codebase_investigator` and
  `cli_help` by name.
