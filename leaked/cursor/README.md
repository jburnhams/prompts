# Cursor

- **Type**: Coding agent (IDE) · **Vendor**: Anysphere · **Status**: closed source (leaked)
- **Mirror source**: https://github.com/x1xhlol/system-prompts-and-models-of-ai-tools/tree/main/Cursor%20Prompts (2026-07-10)

Multiple dated versions are kept side by side — useful for seeing how
Cursor's prompt evolved over roughly a year.

## Files
- `Agent Prompt v1.0.txt`, `Agent Prompt v1.2.txt`, `Agent Prompt 2.0.txt`,
  `Agent Prompt 2025-09-03.txt` — successive versions of the main agent
  system prompt.
- `Agent CLI Prompt 2025-08-07.txt` — prompt for Cursor's CLI mode.
- `Agent Tools v1.0.json` — tool/function definitions.
- `Chat Prompt.txt` — non-agentic chat-mode prompt.

## Tool surface

Per the extracted `Agent Tools v1.0.json`: `codebase_search`,
`read_file`, `run_terminal_cmd`, `list_dir`, `grep_search`, `edit_file`,
`search_replace`, `file_search`, `delete_file`, `reapply`, `web_search`,
`create_diagram`, `edit_notebook`.

- **Shell**: `run_terminal_cmd`.
- **Search**: `codebase_search` (semantic — matches the 2025-09-03 prompt
  text's framing of it as "your MAIN exploration tool," to be run with
  multiple differently-worded queries before trusting the results) plus
  plain `grep_search` and `file_search`/`list_dir`.
- **Editing — two tools, not one**: `edit_file` and `search_replace`
  side by side, plus a distinctive `reapply` tool — presumably for
  retrying an edit that failed to apply cleanly, a recovery mechanism not
  named explicitly in any other source's tool list in this collection.
- **Diagrams**: `create_diagram` — the only dedicated diagram-generation
  tool (almost certainly Mermaid) found anywhere in this collection.
- **Notebooks**: `edit_notebook`.
- **Browser/web**: `web_search`; no browser-automation/screenshot tool in
  this extraction (contrast leaked Windsurf's full Puppeteer-style
  suite).
- **Diagnostics**: the 2025-09-03 prompt text separately references a
  `read_lints` tool (linter-error checking folded into the edit loop) not
  present in this particular tools JSON snapshot — a reminder that the
  prompt text and tool list here were extracted at (probably) different
  times and may not be perfectly consistent with each other.
- **Multimodal**: not indicated.
- **Sandbox/isolation**: not indicated — runs in the user's actual
  editor/workspace.
