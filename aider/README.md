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

## Tool surface

Aider is structurally different from most of this collection: it's not
built around a model-driven tool-calling loop at all. The model just
writes SEARCH/REPLACE blocks (or whichever edit format the active Coder
uses) in its chat response; Aider's own Python code parses that text and
applies it to disk — there's no `edit_file`/`write_file` tool the model
invokes.

- **Shell**: no bash/execute tool. `base_prompts.py` defines
  `shell_cmd_prompt`/`shell_cmd_reminder` hook points (empty by default,
  populated from a separate `aider/coders/shell.py` module not fetched
  for this collection) that — per Aider's own docs — let it *suggest*
  shell commands after making changes, which the user can choose to run;
  this is opt-in, not an autonomous tool call.
- **Search**: none built into the prompt — the human decides which files
  to "add to the chat" (`editblock_prompts.py`: "you *MUST* tell the user
  their full path names and ask them to add the files to the chat").
  Aider has no equivalent of the codebase-search/grep tools every other
  source in this collection gives the model.
- **Code execution**: none.
- **Browser/web**: not addressed in the prompts collected here.
- **Multimodal**: not addressed here (Aider does support image
  attachments in later/other parts of the product per its own docs, not
  confirmed in the prompt files in this collection).
- **Sandbox/isolation**: none — edits are applied straight to the user's
  local files by the CLI process itself.
- **Distinctive**: this file-selection-by-the-human model (rather than
  agent-driven exploration) is the sharpest architectural outlier
  in this collection's coding-agent set — everything else assumes the
  model can freely explore and pick its own files.
