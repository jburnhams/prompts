# GitHub Copilot Chat (VS Code)

- **Type**: Coding agent (VS Code Copilot Chat's "agent mode"), plus Copilot
  CLI
- **License**: MIT
- **Source**: https://github.com/microsoft/vscode-copilot-chat — **archived/
  read-only as of 2026-05-20**
- **Retrieved from**: `main` branch,
  `src/extension/prompts/node/agent/` (2026-07-10)

Microsoft open-sourced the VS Code Copilot Chat extension in mid-2025.
Prompts are written as `.tsx` components using Microsoft's `@vscode/prompt-tsx`
library (JSX-like templating for prompt composition) rather than plain
strings. Like OpenCode and Roo Code, the actual instructions vary by model
family — this repo has the most granular per-model split of any source in
this collection.

This is the **complete** contents of `agent/` and `agent/openai/` — every
file in both directories. Not included: the separate prompt trees for
`panel/`, `inline/`, `notebook/`, `devcontainer/`, etc. one level up, which
back distinct chat features (non-agentic chat, inline completions, notebook
cells...) rather than the core coding agent, plus the `agent/test/`
directory (test fixtures, not real prompts).

## Files

### Core assembly
- `agentPrompt.tsx` — the main agent-mode system prompt assembly.
- `allAgentPrompts.ts` / `promptRegistry.ts` — registry mapping models to
  their prompt implementation.
- `defaultAgentInstructions.tsx` — the default persona/rules/tone shared
  across models absent a more specific variant.
- `copilotCLIPrompt.tsx` — the prompt used by the separate Copilot CLI tool.

### Conversation/history handling
- `agentConversationHistory.tsx` — formats prior turns for inclusion in the
  prompt.
- `summarizedConversationHistory.tsx` / `simpleSummarizedHistoryPrompt.tsx`
  — condensed/summarized history variants (for long conversations).
- `backgroundSummarizer.ts` — prompt for the background summarization pass
  itself.

### Sub-agents & misc instructions
- `executionSubagentPrompt.tsx` — prompt for a delegated "execute this step"
  sub-agent.
- `searchSubagentPrompt.tsx` — prompt for a delegated codebase-search
  sub-agent.
- `fileLinkificationInstructions.tsx` — output formatting rules for turning
  file references into clickable links.

### Per-model-family variants
- `anthropicPrompts.tsx` — Claude models.
- `geminiPrompts.tsx` — Gemini models.
- `xAIPrompts.tsx` — Grok models.
- `zaiPrompts.tsx` — Zhipu/Z.ai models.
- `minimaxPrompts.tsx` — MiniMax models.
- `familyHPrompts.tsx` — an internal/codenamed "family H" model.
- `vscModelPrompts.tsx` — Microsoft's own VS Code-hosted models.

### OpenAI model variants (`openai/`)
- `defaultOpenAIPrompt.tsx` — fallback for OpenAI models without a more
  specific variant.
- `gpt5Prompt.tsx`, `gpt5CodexPrompt.tsx` — GPT-5 and GPT-5-Codex.
- `gpt51Prompt.tsx`, `gpt51CodexPrompt.tsx` — GPT-5.1 and GPT-5.1-Codex.
- `gpt52Prompt.tsx`, `gpt53CodexPrompt.tsx` — GPT-5.2 and GPT-5.3-Codex.
- `gpt54Prompt.tsx`, `gpt54ConcisePrompt.tsx`, `gpt54LargePrompt.tsx` —
  GPT-5.4, plus concise/large context-window variants.
- `hiddenModelBPrompt.tsx` — prompt for an unannounced/codenamed model
  ("Model B") gated behind an internal flag.

## Tool surface

The richest IDE-integrated tool set in the "kitchen sink" archetype
(leaked Windsurf's is richer overall, but leans toward browser
automation and product features rather than IDE/LSP integration). All
tool references in `defaultAgentInstructions.tsx` are conditional on
`this.props.availableTools` — the prompt text adapts to whichever tools
are actually enabled for that session/user, rather than assuming a fixed
set.

- **Shell — two tiers**: `CoreRunInTerminal` (raw terminal), but the
  prompt pushes the model toward a separate `ExecutionSubagent` for
  "most execution tasks and terminal commands... to get relevant
  portions of the output instead of using `CoreRunInTerminal`," reserving
  the raw terminal tool "for rare cases when you want the entire output
  of a single command without truncation." A summarizing wrapper around
  shell execution, not just the shell itself — similar idea to Crush's
  two-tier `fetch`/`agentic_fetch` split, applied to terminal output
  instead of web fetches.
- **Search**: `Codebase` (semantic search — "if you don't know exactly
  the string or filename pattern you're looking for"), `FindFiles`
  (glob-equivalent), `FindTextInFiles` (grep-equivalent),
  `SearchWorkspaceSymbols` (LSP-backed symbol search — a step beyond the
  plain "list code definitions" capability seen in Cline/Roo Code, since
  it can leverage the editor's actual language server), and a
  `SearchSubagent` delegate for open-ended exploration.
- **Editing**: `EditFile`, `ReplaceString`/`MultiReplaceString`
  (old/new-string based, with a batch variant), and `ApplyPatch` — the
  only source in this collection besides Codex CLI to expose a named
  patch-style tool alongside a string-replace tool rather than choosing
  one family.
- **Notebooks — a dedicated triad**: `EditNotebook`, `RunNotebookCell`,
  `GetNotebookSummary` (cell IDs, types, languages, execution state,
  output mimetypes). Explicitly forbidden to use `EditFile` or run
  `jupyter` CLI commands in the terminal for notebook work — "Never...
  execute Jupyter related commands in the Terminal to edit notebook
  files." No other source in this collection treats notebooks as a
  first-class, separately-tooled surface.
- **Diagnostics/VCS awareness**: `GetErrors` (linter/diagnostic state —
  same idea as leaked Cursor's `read_lints`) and `GetScmChanges` (reads
  git/source-control state directly through a tool rather than shelling
  out to `git diff`).
- **Planning**: `CoreManageTodoList`.
- **Browser/web**: `FetchWebPage` — a plain fetch tool; no
  browser-automation/screenshot tool referenced in this file (contrast
  Windsurf's/Cline's vision-based browser control).
- **Multimodal**: not addressed beyond notebook output mimetypes.
- **Sandbox/isolation**: not specified — runs in the user's actual VS
  Code workspace.

## Sub-agents

The only source in this collection where the **sub-agent's complete
system prompt is captured verbatim as its own file** — not just the
orchestrator-side tool description that triggers delegation. Two
purpose-built sub-agents, each swapping in "custom execution instructions
instead of the default agent system prompt" (per both files' own doc
comments):

- **`ExecutionSubagentPrompt`** (`executionSubagentPrompt.tsx`) — the
  wrapper `CoreRunInTerminal`'s tool description tells the orchestrator
  to prefer (see "Tool surface" above). Its system prompt is a **complete
  persona swap**: "You are an AI coding research assistant that runs a
  series of terminal commands to perform a small execution-focused
  task," free to adapt the literal commands given ("if you are asked to
  `make` a project but there is no Makefile, you might instead run `cmake
  . && make`"). Bounded by `maxExecutionTurns`, with a hard cutoff
  message injected on the last allowed turn ("OK, your allotted
  iterations are finished. Show the `<final_answer>`.") and a mandated
  output format — a `<final_answer>` block listing each command run plus
  a one-line summary, nothing else.
- **`SearchSubagentPrompt`** (`searchSubagentPrompt.tsx`) — same
  turn-budget/forced-cutoff structure, different persona and output
  contract: "an AI coding research assistant that uses search tools to
  gather information," required to return `<final_answer>` as a bare
  list of `path:line-start-line-end` references, explicitly "ONLY" that
  tag with nothing else.
- **Protocol**: both inherit the orchestrator's full tool-calling
  machinery (`ChatToolCalls`, same `toolCallRounds`/`toolCallResults`
  plumbing as the main agent) rather than a separate lightweight
  execution path — the sub-agent is a real, complete tool-calling loop,
  just under a different system prompt, a hard turn cap, and a
  constrained output grammar. The forced-final-turn nudge ("OK, your
  allotted iterations are finished...") is a distinctive reliability
  mechanism not seen elsewhere in this collection — most other sources
  just trust the sub-agent to wrap up in time.
- **Result handling**: not shown in these two files (they only render
  the sub-agent's own conversation), but structurally the constrained
  `<final_answer>` format exists specifically to make the result cheap
  and unambiguous for the orchestrator to fold back into its own
  context — a tighter contract than Claude Code's free-text "concise
  summary" report.

## Compaction

Already fully captured in this folder's files, not previously written
up as its own section — `summarizedConversationHistory.tsx`,
`simpleSummarizedHistoryPrompt.tsx`, `backgroundSummarizer.ts`. See
[`agent-context-compaction.md`](../agent-context-compaction.md) for the
cross-source comparison this feeds into.

- **A structured 8-section prompt**, more elaborate than most other
  sources surveyed: Conversation Overview → Technical Foundation →
  Codebase Status → Problem Resolution → Progress Tracking → Active
  Work State → Recent Operations → Continuation Plan, each with its
  own sub-bullets, wrapped in explicit `<analysis>`/`<summary>` tags (a
  private reasoning pass before the structured output, same idea as
  Gemini CLI's `<scratchpad>`). A dedicated "Recent Context Analysis"
  section specifically captures the last agent commands/tool results
  that triggered the summarization — not just the conversation in
  general.
- **Two independent tiers, not one strategy**: "Full" mode is the real
  LLM summarization call (tools attached with `tool_choice: 'none'` so
  the model can still see what's available without invoking anything);
  "Simple" mode is a **non-LLM structural fallback** — no summarization
  call at all, just packing as much raw history as fits into a
  priority-ordered list (first message pinned highest priority, large
  tool results/arguments truncated). Simple mode is used when Full mode
  itself fails or would exceed budget — a fallback *for the
  summarizer*, not just for the underlying task.
- **Foreground vs. background summarization as an explicit, tracked
  distinction**: `BackgroundSummarizer` is a small state machine
  (Idle → InProgress → Completed/Failed) letting summarization run
  concurrently with the agent continuing other work, rather than
  always blocking the turn — the source/foreground-vs-background
  distinction is even carried into telemetry.
- **An inline-summarization mode as a third option**: instead of a
  separate LLM call, the compaction instruction can be appended
  directly into the ongoing agent loop as a user message, with the
  model's next response expected to contain *only* a summary wrapped
  in `<summary>` tags (parsed with a multi-level fallback: clean tags →
  open tag with no close → give up and fall back to a separate call).
- **Per-model-family quirk handling baked directly into the
  summarization path**: Anthropic-family models get tool-search
  messages stripped (the summarization call doesn't have tool search
  enabled, so leaving them in causes an API rejection); Gemini-family
  models get orphaned tool calls stripped (a strict function-call/
  function-response pairing requirement); Claude Opus specifically gets
  an explicit "do NOT call any tools" reinforcement.
- **A `PreCompact` hook runs before summarization starts**, letting hook
  scripts archive the transcript or perform cleanup — the same named
  hook-point concept as Claude Code's own `PreCompact` hook.
- **Recovery pointer to the full transcript**, same pattern as Claude
  Code: when a session transcript is being tracked, the summary text
  gets a trailing hint — "If you need specific details from before
  compaction... use the ReadFile tool to look up the full uncompacted
  conversation transcript at: `<path>`" — with the transcript's current
  line count included, frozen into the summary text at compaction time
  specifically so it doesn't change on later renders (preserving prompt
  cache stability for the summary message itself).
- **Cache breakpoints are explicitly stripped from the summarization
  request** before it's sent — the summarization call is deliberately
  excluded from the normal prompt-caching path rather than trying to
  make it cache-compatible.
- **Budget**: an optional hard cap on summary size —
  `min(sizing.tokenBudget, maxSummaryTokens)` — with the summarization
  attempt itself failing (`'Summary too large'`) if the model's output
  exceeds that effective budget, rather than truncating it after the
  fact. Rich per-attempt telemetry (prompt/cache/completion token
  counts, duration, which mode ran, how many rounds since the last
  summarization) is sent regardless of outcome.
