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
