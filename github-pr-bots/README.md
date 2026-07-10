# GitHub PR bots

A fourth category: the automated bots/GitHub Actions each major vendor
offers that review pull requests directly on GitHub (as opposed to the
`skills/` folder's Claude-Code-specific slash commands, or the top-level
folders' full standalone CLI/IDE agents). The question this folder is
trying to answer for each vendor: **how does it turn a PR into a model
request** — diff format, what context besides the diff gets pulled in,
how existing comments are handled, and how the response gets turned back
into GitHub comments/suggestions.

## Sources

| Folder | Vendor | Status |
|---|---|---|
| [`claude-code-action/`](./claude-code-action) | Anthropic | Genuinely open source (MIT), and what actually runs |
| [`gemini-code-review/`](./gemini-code-review) | Google | Genuinely open source (Apache-2.0), and what actually runs |
| [`codex-review/`](./codex-review) | OpenAI | OpenAI's own **published reference implementation**, explicitly *not* the real hosted service — see that folder's README |

## Copilot: nothing found

GitHub's actual hosted "Copilot code review" (the bot that leaves inline
comments as a real PR check) is closed-source, server-side infrastructure
— no diff-formatting or prompt-construction logic is published anywhere.
Two things exist that are *not* that, and weren't added here to avoid
implying otherwise:

- A [`/review-code` prompt file](https://docs.github.com/en/copilot/tutorials/customization-library/prompt-files/review-code)
  from GitHub's own docs — an optional, user-installable prompt for
  Copilot Chat's editor-side review of *selected code*, unrelated to the
  hosted PR-review bot's mechanics (no diff/PR formatting logic at all).
- `microsoft/vscode-copilot-chat`'s `src/extension/prompts/node/github/`
  folder (already excluded from `../copilot-chat/`, which does include the
  rest of that repo's agent-mode prompts) — only contains
  `pullRequestDescriptionPrompt.tsx` (PR *description* generation), not
  review/diff-formatting logic.

Worth re-checking if GitHub ever open-sources the actual review service.
