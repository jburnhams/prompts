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

Only a representative subset of the ~30 files in this directory tree is
included here (core assembly + one file per major model family); the
directory also has provider variants not copied (e.g. more OpenAI
sub-variants), plus entirely separate prompt trees for `panel/`, `inline/`,
`notebook/`, `devcontainer/`, etc. that aren't part of the core coding-agent
prompt.

## Files

- `agentPrompt.tsx` — the main agent-mode system prompt assembly.
- `allAgentPrompts.ts` / `promptRegistry.ts` — registry mapping models to
  their prompt implementation.
- `defaultAgentInstructions.tsx` — the default persona/rules/tone shared
  across models absent a more specific variant.
- `copilotCLIPrompt.tsx` — the prompt used by the separate Copilot CLI tool.
- `anthropicPrompts.tsx` — variant for Claude models.
- `geminiPrompts.tsx` — variant for Gemini models.
- `xAIPrompts.tsx` — variant for Grok models.
- `zaiPrompts.tsx` — variant for Zhipu/Z.ai models.
- `minimaxPrompts.tsx` — variant for MiniMax models.
- `familyHPrompts.tsx` — variant for an internal/codenamed "family H" model.
- `vscModelPrompts.tsx` — variant for Microsoft's own VS Code-hosted models.
- `openai/defaultOpenAIPrompt.tsx` — default OpenAI-model variant.
- `openai/gpt5Prompt.tsx` / `openai/gpt5CodexPrompt.tsx` /
  `openai/gpt51CodexPrompt.tsx` / `openai/gpt54Prompt.tsx` /
  `openai/gpt54ConcisePrompt.tsx` — GPT-5-generation model-specific variants.
