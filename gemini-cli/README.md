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
