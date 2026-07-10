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
