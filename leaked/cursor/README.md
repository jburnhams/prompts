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

## Self-verification and testing

See [`agent-self-verification.md`](../../agent-self-verification.md) for
the cross-source comparison this feeds into. Prompted-only (§7 there) in
every version — no code-level gate, LLM-judge, or per-action check found
in any of the five dated prompt files — but the instruction gets
noticeably stronger and more structured across versions, worth reading
as its own mini-timeline:

- **v1.0/v1.2 (earliest)**: no test/build-verification instruction at
  all. The only quality gate is a bounded linter-fix loop: "DO NOT loop
  more than 3 times on fixing linter errors on the same file. On the
  third time, you should stop and ask the user what to do next" — a
  retry cap, not a correctness check.
- **2.0**: same 3x linter cap, plus a tool description that pointedly
  keeps verification *off* the visible plan: `todo_write`'s spec says
  "NEVER INCLUDE THESE IN TODOS: linting; testing; searching or
  examining the codebase" — testing is treated as ambient hygiene, not
  trackable work.
- **2025-09-03 (GPT-5)**: the richest version, and structurally novel.
  A `<completion_spec>` ties finishing to the todo list ("Confirm that
  all tasks are checked off... Reconcile and close the todo list");
  a `<non_compliance>` clause adds a genuinely new temporal shape not
  matching any other category in this collection — a *retroactive*
  self-correction obligation rather than a pre-completion check: "If
  you report code work as done without a successful test/build run,
  self-correct next turn by running and fixing first."
- **CLI mode (2025-08-07, GPT-5)**: the single strongest instruction
  found in any Cursor file, and unconditional (not gated behind an
  autonomy/approval mode the way Codex CLI's proactivity is):
  "After any substantive code edit or schema change, run tests/build;
  fix failures before proceeding or marking tasks complete" / "Before
  closing the goal, ensure a green test/build run." The "green run"
  phrasing echoes Claude Code's leaked "never fake a green result"
  language — a second data point for that phrase circulating across
  vendors, not just an internal Anthropic idiom.
- **Chat Prompt.txt**: no agentic tools at all in this non-agentic
  chat mode, so no verification content exists or could exist.
