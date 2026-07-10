# Aider

- **Type**: Coding agent (terminal-based pair programmer)
- **License**: Apache-2.0
- **Source**: https://github.com/Aider-AI/aider
- **Retrieved from**: `main` branch, `aider/coders/` (2026-07-10)

Aider uses a "Coder" class per editing strategy, each with its own prompt
class. A handful of representative modes are included here; the repo has
many more (`udiff_prompts.py`, `patch_prompts.py`, `wholefile_prompts.py`,
etc.) under the same directory.

## Files

- `base_prompts.py` — shared base class other prompt classes inherit from.
- `editblock_prompts.py` — default "SEARCH/REPLACE block" editing prompt.
- `architect_prompts.py` — the "architect" mode prompt (plans changes, hands
  editing off to a separate editor model).
- `ask_prompts.py` — read-only Q&A mode prompt (no code edits).
