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
- `Agent Prompt (asgeirtj capture).md` — a sixth, undated capture, mirrored
  from a different, independently-maintained aggregator
  (https://github.com/asgeirtj/system_prompts_leaks, retrieved
  2026-07-12) than the five files above (all from x1xhlol's repo). Uses a
  genericized `{model_name}` placeholder rather than a dated model name.
  Its tool surface and several full sections (git commit/PR workflow,
  tool-calling etiquette) are structurally closest to the *newest*
  x1xhlol-sourced material (2025-09-03/CLI, GPT-5-era) but with a
  materially different, apparently later tool roster — treat it as
  undated-but-late rather than placed confidently on the existing
  timeline. See the sections below for what's genuinely new in it.

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

**New from the asgeirtj capture — a materially different, apparently
later tool roster, not just a rename of the same six tools above.** This
file's own "Available Tools" list uses Claude-Code-style capitalized
names (`Shell`, `Glob`, `Grep`, `Read`, `Write`, `StrReplace`, `Delete`,
`EditNotebook`, `TodoWrite`) rather than `Agent Tools v1.0.json`'s
`snake_case` set, and several tool-calling/editing/git sections read as
near-verbatim matches to Claude Code's own publicly-known conventions
(see the callout at the end of this subsection) — worth treating
cautiously as a capture, but documenting at face value since it's
internally consistent throughout the file.

- **Fetch and search finally split into two tools** — `WebSearch` and
  `WebFetch` (fetch a specific URL, "readable markdown format") are
  separate tools here, correcting the standing finding above ("no
  fetch-a-known-URL tool distinct from `web_search`") — that gap only
  holds for the five x1xhlol-sourced captures, not for this one.
- **Image generation** — `GenerateImage` ("Generate an image file from a
  text description. Only use when the user explicitly asks for an
  image.") — a capability with no analog in any of the other five
  Cursor captures, and not common elsewhere in this collection either.
- **Structured multiple-choice user prompts** — `AskQuestion` ("Collect
  structured multiple-choice answers from the user... set
  allow_multiple when multi-select is appropriate") — a dedicated
  clarifying-question tool distinct from free-text turns, not present
  in any other Cursor capture.
- **A file-system-mediated MCP integration, a different shape from a
  normal function-calling MCP client**: `CallMcpTool` invokes any MCP
  tool by server/tool name plus arbitrary JSON args, but the model is
  told to discover the schema first by *reading JSON descriptor files
  on disk* (`{mcps_folder}/<server>/tools/tool-name.json`) rather than
  from schemas already present in its own context window, and is told
  this lookup is "NOT optional." `ListMcpResources`/`FetchMcpResource`
  mirror the same pattern for MCP resources. No other source in this
  collection's tool-surface research documents an MCP client that
  makes the model do its own filesystem-based schema discovery instead
  of receiving tool schemas inline.
- **`create_diagram` and `reapply` are both gone** in this capture —
  no diagram tool and no dedicated reapply-after-failed-edit tool are
  named anywhere in the file (superseded by a generic `StrReplace` with
  a `replace_all` flag, structurally closer to Claude Code's `Edit` than
  to the earlier `edit_file`/`search_replace`/`reapply` trio).
- **`SetActiveBranch`** — "Set active git branch metadata for the
  current conversation and client UI" — a UI-metadata tool, not a real
  git-mutating tool; see Git and version control below.
- **`AwaitShell`** — polls a backgrounded shell job, paired with the
  `Shell` tool's own `block_until_ms`/background-after-30s behavior — a
  bit more explicit about async command handling than the
  `run_terminal_cmd`/`is_background` shape in the other five captures.
- **A `SwitchMode` tool** exposing four named interaction modes (Agent/
  Plan/Debug/Ask) — see Permissions and approval below; this is new
  relative to every other Cursor capture, none of which name a mode
  taxonomy at all.
- **A `Task` tool with seven named sub-agent types** — see Sub-agents
  below; this directly contradicts this collection's standing
  cross-source finding (`agent-subagent-architectures.md`) that leaked
  Cursor has no delegation mechanism at all.

**The Claude-Code-convention overlap is close enough to name
explicitly, with appropriate caution.** Several passages in this file
are near-verbatim matches to Claude Code's own leaked/public system
prompt: the `tool_calling`/`no_thinking_in_code_or_commands` etiquette
("Do not use a colon before tool calls... 'Let me read the file.'
followed by a read tool call"), the `making_code_changes` comment
policy ("Do NOT add comments that just narrate what the code does...
'// Import the module'"), and — most strikingly — the entire "Git
Operations" section (see Git and version control below), which
reproduces Claude Code's "Committing Changes"/"Creating Pull Requests"
workflow structure almost exactly, down to the HEREDOC commit-message
instruction. Read this as either genuine evidence of an industry-wide
pattern of copying Claude Code's published prompt-engineering
conventions (already documented for OpenCode's near-identical
"NEVER commit... too proactive" line in `agent-git-vcs.md` §2), or as
a sign this particular capture blends/normalizes text from multiple
sources during aggregation — flagged here rather than silently folded
into the rest of this doc's findings.

## Sub-agents

See [`agent-subagent-architectures.md`](../../agent-subagent-architectures.md)
for the cross-source comparison this feeds into — **this section is new
in this README**; none of the five x1xhlol-sourced captures show any
delegation mechanism, which is why Cursor was previously profiled only
in that doc's "Absences" section.

- **A `Task` tool, described only at the one-line level** ("Launch a
  new agent to handle complex, multi-step tasks autonomously"), with
  seven named `subagent_type` values: `generalPurpose`, `explore`
  (read-only codebase exploration), `shell` (command-execution
  specialist), `browser-use` (browser testing/automation — the first
  hint of browser capability anywhere in Cursor's captured material,
  though only as a sub-agent role, not a tool available to the main
  agent), `cursor-guide` (reads Cursor's own product docs to answer
  "how Cursor works" questions), `best-of-n-runner`, and `codex-rescue`.
  No schema detail beyond the one-line description for any of them —
  materially thinner than this collection's other richly-documented
  sub-agent protocols (contrast Codex CLI's `spawn_agent` family or
  OpenCode's `Task` tool).
- **`best-of-n-runner`: "Run a task in an isolated git worktree."** See
  Git and version control below for the full worktree-isolation
  writeup this feeds into `agent-git-vcs.md` §4. The name itself is the
  most informative part of this one-line spec: "best-of-n" is sampling
  terminology (generate N independent candidate solutions, then select
  the best one), which implies this sub-agent type exists specifically
  to run **multiple parallel attempts at the same task**, each isolated
  in its own worktree so they can't collide with each other or the
  user's working tree — a different framing from every other captured
  worktree mechanism in this collection, all of which isolate *distinct
  tasks* running concurrently, not *N attempts at one task* competing
  for a single winner. Nothing in this one-line description says how
  results are compared or a winner selected (no scoring/judge mechanism
  is named), so that half of the "best-of-n" implication is inferred
  from the name, not confirmed by captured text.
- **`codex-rescue`: "Use when Claude Code is stuck, wants a second
  implementation or diagnosis pass."** Notable independent of the
  worktree finding: this is Cursor's own orchestration layer naming a
  *competitor product* ("Claude Code") by name as a trigger condition
  for delegating to a second opinion — not "when you are stuck," but
  specifically when *Claude Code* is stuck. Reads as evidence Cursor's
  agent harness is designed to be invoked as a rescue/second-opinion
  layer from within or alongside Claude Code sessions, not just
  standalone. No other source in this collection names a specific rival
  product as a sub-agent trigger condition.
- **No schema, protocol, or recursion-policy detail for any of the
  seven types** — unlike Codex CLI's `spawn_agent`/`send_input`/
  `wait_agent`/`close_agent` family or OpenCode's `Task` tool, there's
  no visible way here to confirm whether `Task` is a blocking
  call-and-report or an addressable child, whether sub-agents can
  themselves call `Task`, or what context they inherit — a real capture
  gap, not a confirmed "thin by design" architecture.

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

**New from the asgeirtj capture**:

- **A named mode taxonomy, absent from every other Cursor capture**:
  `SwitchMode` exposes four modes — **Agent Mode** ("Default
  implementation mode with full access to all tools for making
  changes"), **Plan Mode** ("Read-only collaborative mode for designing
  implementation approaches before coding"), **Debug Mode**
  ("Systematic troubleshooting mode — cannot switch to this mode
  directly"), and **Ask Mode** ("Read-only mode for exploring code and
  answering questions — cannot switch to this mode directly"). A
  separate `<mode_selection>` block instructs the model to proactively
  call `SwitchMode` itself when it judges another mode fits better
  ("Be proactive about switching to the optimal mode"), gated on task
  shape ("user asks for a plan, or the task is large/ambiguous or has
  meaningful trade-offs") rather than on any risk classification. This
  is a genuinely new data point for `agent-permissions-approval.md` §1
  ("Approval mode taxonomies") — Cursor wasn't previously listed in
  that table at all — though it's the "named agent/task modes" shape
  (closer to OpenCode's `build`/`plan`/`explore`) rather than a
  risk-tiered approval ladder: two of the four modes (Debug, Ask) are
  explicitly *not* reachable by the model's own `SwitchMode` call
  ("cannot switch to this mode directly"), a restriction with no
  stated mechanism for how they're entered instead.
- **No risk-classification flag here either** — a full-file grep for
  "risk"/"dangerous"/"approve"/"approval"/"permission" turns up zero
  hits, extending the standing "no risk field found in any Cursor
  version" finding to a sixth capture, and — combined with the
  2025-09-03/CLI prompts already having dropped all approval-flow
  language — now zero out of the three most-recent-looking Cursor
  captures mention command approval at all in the model-facing prompt
  text. Consistent with this doc's existing read: approval mechanics
  have moved fully into orchestration/client layers not captured
  alongside the prompt text, not that approval was removed as a
  feature.

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

**New from the asgeirtj capture — this single file overturns three of
the "not found in any Cursor capture" claims above.** All three
findings below are absent from the five x1xhlol-sourced files and
present only here; treat the bullets above as still accurate for those
five, not as superseded.

- **Worktree isolation, via a sub-agent type, not a directly-callable
  tool.** `best-of-n-runner`'s full one-line spec is: **"Run a task in
  an isolated git worktree."** This is the first and only confirmed
  worktree-isolation mechanism found anywhere in Cursor's captured
  material — `agent-git-vcs.md` previously listed Cursor under
  "Confirmed near-total or total absence" for worktree isolation
  alongside Windsurf, Warp, and Replit; that placement no longer holds
  for Cursor (see `agent-git-vcs.md` §4, now updated). The mechanism is
  reached through the `Task` tool's `subagent_type` parameter (see
  Sub-agents above), not a standalone worktree-management tool — there
  is no visible `CreateWorktree`/`EnterWorktree`-style primitive the
  main agent calls directly, unlike Claude Code's `EnterWorktreeTool`/
  `ExitWorktreeTool` or OpenCode's `Worktree.Service`. **What isn't
  captured**: branch-naming convention, subdirectory location, cleanup/
  removal policy, and whether the worktree is retained after the
  sub-agent finishes — all confirmed unspecified by a full-file grep
  (no other occurrence of "worktree" anywhere in the file). The name
  "best-of-n-runner" (see Sub-agents above) implies the isolation
  exists to support running **multiple parallel attempts at one task**
  side by side for later comparison — a distinct framing from Gemini
  CLI's/OpenCode's/Claude Code's worktree services, which isolate
  concurrent *different* tasks or sessions rather than N competing
  attempts at the same one.
- **A real commit-message and PR workflow, not "thin and incidental"
  for this capture.** A dedicated "## Git Operations" section (absent
  from every x1xhlol-sourced file) gives concrete process: for commits,
  "Run git status, git diff, and git log in parallel," then "Analyze
  all staged changes and draft a commit message," then "Add relevant
  files, commit, and verify success" — plus explicit prohibitions
  ("NEVER update the git config. NEVER run destructive/irreversible git
  commands unless explicitly requested. NEVER skip hooks," amend
  discouraged "unless specific conditions are met") and a formatting
  rule ("Always pass commit messages via HEREDOC"). For PRs: "Use the
  `gh` command for ALL GitHub-related tasks," gather `git status`/
  `diff`/remote-tracking/`log` in parallel, draft a summary, "Push to
  remote and create PR using `gh pr create`." No character limit, no
  trailer/attribution format, and no worked example are given — thinner
  than Claude Code's fully-specified template (`## Summary`/`## Test
  plan` sections, HEREDOC'd `gh pr create` body) that this section's
  *process* steps otherwise closely resemble — but this is nonetheless
  the first captured Cursor content addressing "when/how does the model
  commit" at all, correcting the standing "no commit-message
  conventions... found in any of the five dated prompts" finding for
  this specific capture.
- **A read-only git-metadata tool with no earlier analog**:
  `SetActiveBranch` — "Set active git branch metadata for the current
  conversation and client UI." Distinct from `fetch_pull_request`
  (v1.2's read-only PR/commit lookup tool, still the only git tool with
  a full schema captured) — this one only updates client-side UI state
  about which branch is "active," with no read or write effect on the
  repository itself, and no stated trigger for when the model should
  call it.

Net effect on this source's git thinness: still no risk-classification
carve-out for git commands specifically, and still no checkpoint/undo
system captured anywhere — but "no commit-message conventions, no
worktree isolation" no longer holds unqualified across Cursor's full
captured corpus, only across the five older files.
