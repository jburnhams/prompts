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
