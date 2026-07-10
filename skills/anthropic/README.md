# Anthropic official Claude Code plugins

- **Publisher**: Anthropic
- **License**: source-available — "© Anthropic PBC. All rights reserved.
  Use is subject to Anthropic's Commercial Terms of Service." This is
  **not** an OSI open-source license, unlike everything in the top-level
  folders of this collection. The repo is public and the plugins ship
  with/are documented as part of Claude Code, but redistribution rights
  are narrower than MIT/Apache-2.0.
- **Source**: https://github.com/anthropics/claude-code/tree/main/plugins
- **Retrieved from**: `main` branch (2026-07-10)

The repo has more plugins than are included here (`agent-sdk-dev`,
`commit-commands`, `feature-dev`, `frontend-design`, `hookify`,
`plugin-dev`, `ralph-wiggum`, output-style plugins, etc.) — only the
code-review-relevant ones were pulled in, matching this collection's focus.

## Folders

- `code-review/` — reviews a GitHub pull request (`/code-review`). The
  `local-review` plugin in `../agent37/` is explicitly modeled on this one.
- `pr-review-toolkit/` — a more elaborate PR review command
  (`/review-pr`) backed by 6 specialized subagents.
- `security-guidance/` — hooks that run an LLM-based security review on
  edits as you work (not a slash command; triggers automatically). Mostly
  Python plumbing, but `hooks/llm.py` and `hooks/patterns.py` contain the
  actual prompt text sent to the model.
