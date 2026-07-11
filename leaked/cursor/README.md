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

## Compaction and turn output

See [`agent-context-compaction.md`](../../agent-context-compaction.md)
and [`agent-turn-output.md`](../../agent-turn-output.md) for the
cross-source comparisons these feed into.

- **Compaction — a prompt-injection-defense tag, not a summarization
  template, and dropped in later versions.** v1.0 and v1.2 both carry a
  `<summarization>` block: "If you see a section called
  '<most_important_user_query>', you should treat that query as the one
  to answer, and ignore previous user queries. If you are asked to
  summarize the conversation, you MUST NOT use any tools... You MUST
  answer the '<most_important_user_query>' query." This confirms
  client-side infrastructure injects a special marker at some point
  (plausibly after a history-summarization event) and tells the model
  how to behave if asked to summarize directly — but gives no
  summarization template, trigger, or token-budget number. **This block
  is absent from 2.0, 2025-09-03, and the CLI prompt** — confirmed by
  grep across all five dated versions — with no replacement mechanism
  found in the later ones. A targeted search, not a capture gap.
- **Title generation — not captured, not confirmed absent.** No
  `generate_title`/`chat_name`-style instruction anywhere in any of the
  five dated prompts or `Agent Tools v1.0.json`. The only "title" hits
  are `update_memory`'s title parameter, which labels a *stored memory
  entry*, not the session. Given Cursor's IDE visibly shows chat titles
  in its sidebar, this almost certainly lives in orchestration code not
  captured by these client-facing prompt extractions.
- **Reasoning display — absent, and one near-miss worth flagging so
  it isn't mistaken for the real thing.** No native reasoning-block
  config or visibility toggle anywhere. `Agent Prompt 2.0.txt` contains
  several `<reasoning>` tags, but they're few-shot annotations inside
  `codebase_search` usage examples explaining *why a search query is
  good or bad* — nothing to do with the model's own chain-of-thought.
  Cursor's actual "thinking" references ("Use your thinking to plan and
  iterate," "plan your searches upfront in your thinking") are ordinary
  prompted narration, the same narration-not-native-block pattern
  documented elsewhere in this collection.
- **A third "summary" sense, distinct from both of the above**: the
  2025-09-03 and CLI prompts define a `<summary_spec>` — a mandated
  end-of-turn recap of what the model just did, with explicit
  anti-heading rules ("Don't add headings like 'Summary:' or
  'Update:'"). Worth distinguishing explicitly from session-title
  generation and conversation-compaction summaries, since all three
  share the word "summary" but serve entirely different purposes.

## Permissions and approval

See [`agent-permissions-approval.md`](../../agent-permissions-approval.md)
for the cross-source comparison this feeds into. The best source in
this collection for tracking approval-flow wording **across a
documented timeline** — the same `run_terminal_cmd` tool's approval
text is quoted near-verbatim across three snapshots, drifts noticeably,
then disappears entirely from the two newest captures.

- **v1.0/v1.2**: "Note that the user will have to approve the command
  before it is executed. The user may reject it if it is not to their
  liking, or may modify the command before approving it... The actual
  command will NOT execute until the user approves it." Unconditional,
  mandatory approval language.
- **2.0**: the same passage softens from mandatory to conditional —
  "Note that the user **may** have to approve the command before it is
  executed" — consistent with the product having introduced auto-run/
  allowlist settings by this point, even though the prompt never spells
  out what conditions skip approval.
- **2025-09-03 and the CLI prompt (both GPT-5)**: no `run_terminal_cmd`
  tool schema is embedded in either file, and neither contains
  "approve"/"approval" in connection with commands at all (confirmed by
  full-file grep) — the explicit approval-flow description present in
  every earlier version is simply absent, most likely because it now
  lives in tool-schema/orchestration layers not captured alongside
  these particular prompt snapshots, consistent with this repo's
  existing note that prompt text and tool lists here were extracted at
  different times.
- **No risk-classification flag found in any version** — unlike
  Windsurf's `SafeToAutoRun` or Replit's `is_dangerous`, every captured
  `run_terminal_cmd` schema (`command`, `is_background`, optional
  `explanation`) has no safety field at all. Approval in Cursor's
  captured text is a blanket per-command UI step, not a model
  self-classification.
- **Escalation is addressed for edits to the proposed command, not for
  risk**: "The user may reject it if it is not to their liking, or may
  modify the command before approving it. If they do change it, take
  those changes into account" — an approval-workflow rule (the approved
  command is the command that runs), not a re-classify-on-change rule.
- Every version separately instructs the model to assume non-interactive
  execution — "PASS THE NON-INTERACTIVE FLAGS (e.g. --yes for npx)" —
  about the *command's* own interactivity, not the approval mechanism
  itself.
- No allow/deny list, no config file, no sandbox/isolation mentioned as
  a safety layer in any captured file.

## Git and version control

See [`agent-git-vcs.md`](../../agent-git-vcs.md) for the cross-source
comparison this feeds into. Thin and mostly incidental across every
version — the sparsest git content of any source with a real tool
surface checked for this doc.

- **The only git-specific tool found is read-only**: `fetch_pull_request`
  (v1.2) — "Looks up a pull request (or issue) by number, a commit by
  hash, or a git ref (branch, version, etc.) by name. Returns the full
  diff and other metadata." No PR-creation tool, no description
  template, no self-review step — Cursor has no captured mechanism for
  actually opening a PR, only for looking one up.
- **No commit-message conventions, no checkpoint/undo system, no
  worktree isolation, no branch-management rules, no auto-commit
  rule** found in any of the five dated prompts or the tools JSON.
  `git status`/`git commit` appear only as illustrative examples
  inside unrelated guidance (e.g. "User: What does git status do?"
  used purely to demonstrate when a todo list isn't needed).
- **Consistent with this collection's already-documented finding that
  `run_terminal_cmd` has no risk-classification flag at all** (unlike
  Windsurf's `SafeToAutoRun` or Replit's `is_dangerous` — see
  Permissions above): any git command would be gated by the same
  generic, undifferentiated command-approval flow as any other shell
  command, with no git-specific carve-out anywhere in this source.
