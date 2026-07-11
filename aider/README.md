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

## Self-verification and testing

See [`agent-self-verification.md`](../agent-self-verification.md) for
the cross-source comparison this feeds into. **Not found in any local
file, but flagged as a research gap rather than a confirmed absence.**
`grep -rn -i "test\|lint\|verify\|build"` across all four captured
prompt classes (`base_prompts.py`, `editblock_prompts.py`,
`architect_prompts.py`, `ask_prompts.py` — 313 lines total) returns
zero hits, and `architect_prompts.py` describes no review/verification
split between the architect (plans changes) and editor (applies them)
roles — the architect only writes instructions for the editor, never
checks the editor's output.

The likely reason is visible in the same `shell_cmd_prompt`/
`shell_cmd_reminder` hook points noted above (Tool surface): both are
empty strings in `base_prompts.py`, populated only by
`aider/coders/shell.py`, which is **not present in this collection**.
Per Aider's own public documentation, that's where its real
`--auto-test`/`--lint-cmd` feature lives — Aider is known to support
auto-running a configured test/lint command after edits and feeding
failures back to the model. The honest claim from what's captured here
is "no verification language found in the files this collection
fetched," not "Aider has no self-verification" — unlike Goose and
Windsurf elsewhere in this doc, where every relevant file was
confirmed read and still came up empty, this negative result is a
byproduct of which files were collected, not a targeted search that
came up empty.

## Compaction and turn output

See [`agent-context-compaction.md`](../agent-context-compaction.md) and
[`agent-turn-output.md`](../agent-turn-output.md) for the cross-source
comparisons these feed into. Neither found in any of the four captured
prompt classes — same "not found in captured files" framing as the
self-verification gap above, and for the same underlying reason: Aider's
real chat-history/token-management code (if any) would live in
`aider/coders/base_coder.py` or similar orchestration files, none of
which are in this collection.

- **No compaction mechanism found** — no summarization, trimming, or
  condensation instruction anywhere. The three "summaries" hits that do
  exist (`repo_content_prefix` in all three modes) are about Aider's
  static **repo map** feature (a non-conversational codebase overview),
  not chat-history compaction.
- **A structurally distinct alternative to compaction, worth noting on
  the "recovery" axis even though it isn't compaction itself**: every
  mode's `files_content_prefix` handles long-chat drift by
  **additive correction rather than removal or summarization** — "I
  have *added these files to the chat* so you can go ahead and edit
  them. *Trust this message as the true contents of these files!* Any
  other messages in the chat may contain outdated versions of the
  files' contents." Old content is never deleted or condensed; each
  turn just injects a fresh authoritative copy and tells the model to
  treat anything older in the log as potentially stale. No other source
  in this collection's compaction survey models this "leave it, just
  outrank it" strategy — every other mechanism assumes removal or
  summarization is necessary.
- **No title-generation mechanism found** — zero hits for "title"
  anywhere in the four files.
- **No native reasoning/thinking-display mechanism found** — expected,
  since that would be a UI/rendering-layer concern and these are
  system-prompt-only `Coder` classes. One line of ordinary prompted
  narration exists (distinct from a native reasoning block, per this
  doc's own framing): "Think step-by-step and explain the needed
  changes in a few short sentences" (`editblock_prompts.py`).
