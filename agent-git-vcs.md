# Git and version control: how a scaffold touches the repo's history

The last of the drill-downs alongside [`agent-context-compaction.md`](./agent-context-compaction.md),
[`agent-turn-output.md`](./agent-turn-output.md),
[`agent-self-verification.md`](./agent-self-verification.md), and
[`agent-permissions-approval.md`](./agent-permissions-approval.md):
when does a coding agent commit, and what does it write? Does anything
snapshot the working tree before a risky edit, and can that snapshot
actually be restored? Does the scaffold isolate parallel work in
separate git worktrees, or does everyone share one checkout? What
happens when it's time to open a pull request? The answers turn out to
range from "nothing at all — git is just another shell command" all
the way to a fully-automatic, per-turn, git-based undo system wired
into a real `/undo` feature.

**Methodology note**: twenty-five sources are covered. Three required
fresh live-source clones (Codex CLI, OpenCode, Gemini CLI) and turned
up this doc's richest findings by a wide margin — OpenCode's and
Gemini CLI's independently-built shadow-git checkpoint systems in
particular are more sophisticated than anything this collection's
other synthesis docs found for their respective topics. Twenty-two
more were read from local files already in this collection, including
two brand-new leaked sources (GitHub Copilot CLI, Grok Build) and a
sixth, differently-provenanced Cursor capture that overturned this
doc's original "no worktree isolation" finding for that source. This
doc's own recurring finding is unusually sharp here: sources whose only
prior mention in this collection was a tool-surface note about
`apply_patch` or a diff-based submission format turned out, once
checked specifically for VCS behavior, to have entire git-based
subsystems (automatic checkpointing, worktree services, GitHub Action
bots) with zero prior trace anywhere else in this collection.

## Sources covered

**With rich, code-confirmed mechanisms** (live-source investigated):
Codex CLI, OpenCode, Gemini CLI.

**With confirmed prompt-text-level mechanisms**: Claude Code (leaked,
plus this session's own live tool-schema for worktrees), Cline, Roo
Code, Aider, OpenHands, Copilot Chat, Crush, Devin (leaked), Jules
(leaked), Factory/Droid (leaked), Augment SWE-bench Agent (the one
source with a code-level, not merely prompted, git restriction), Zed
(genuinely open source — no commit/branch/PR conventions, but a
hardcoded sandbox-level protection on `.git` metadata; see §7), Cursor
(leaked — thin across its five original x1xhlol-sourced captures, but a
sixth, differently-provenanced capture, `Agent Prompt (asgeirtj
capture).md`, adds a real commit/PR workflow and this doc's only
confirmed Cursor worktree-isolation finding; moved out of the absence
bucket below on that basis — see §4 and §6), GitHub Copilot CLI
(leaked — a fixed commit-trailer convention identical across both its
captures, but a confirmed, checked *absence* of the near-universal
"don't commit unless asked" convention; see §1/§2), Grok Build
(leaked — its `run_terminal_command` git-safety guidance is a
near-verbatim match to Claude Code's own leaked Bash-tool guidance,
already stored in this collection, but with no commit-message
convention or "don't commit unless asked" rule carried over alongside
it; see §1/§2/§4 and `leaked/grok-build/README.md`).

**Confirmed near-total or total absence**: Goose, Pi, Windsurf
(leaked), Warp (leaked), Replit (leaked), SWE-agent, mini-swe-agent's
base config (its benchmark-tuned config is rich — see §3).

---

## 1. Commit message conventions

| Convention | Sources |
|---|---|
| **A required trailer/attribution format, evolving over time within one product** | Claude Code (leaked) — the Bash tool's "# Committing changes with git" section requires a concise, "why"-not-"what" message via HEREDOC; the trailer text itself has visibly changed between the leaked snapshot ("🤖 Generated with [Claude Code](https://claude.ai/code)\n\nCo-Authored-By: Claude <noreply@anthropic.com>") and this live session's own Bash tool description (model-version-specific author name, a session-URL trailer, the emoji line dropped) — a real, dated convention change, not a discrepancy between two captures. |
| **An explicit instruction to imitate the repo's own historical style, not a fixed template** | Gemini CLI — the only one of the three CLI-shaped sources investigated in depth for this doc to mandate `git log -n 3` "to match the existing commit-message style (verbosity, formatting, signature line, etc.)" before drafting a commit. |
| **A fixed co-author trailer with a concrete fallback identity policy** | OpenHands — "add Co-authored-by: openhands \<openhands@all-hands.dev\> to any commits messages you make. if a git config doesn't exist use 'openhands' as the user.name and 'openhands@all-hands.dev' as the user.email by default." OpenCode's GitHub Action bot does the same for its own automated commits (`Co-authored-by: <actor>@users.noreply.github.com`), and Codex's internal git-baseline mechanism carries its own trailer (`Co-authored-by: Codex <noreply@openai.com>`) — but only on its own internal bookkeeping repo, never the user's project. GitHub Copilot CLI (leaked) belongs here too, with the trailer stated identically, word for word, in both of its captures despite a real version gap between them (`v1.0.39` vs. `1.0.44`): "always include the following Co-authored-by trailer at the end of the commit message: `Co-authored-by: Copilot <223556219+Copilot@users.noreply.github.com>`" — no character limit, no "why not what" guidance, and (see §2) no attached "don't commit unless asked" rule of any kind, unlike every other source in this row. |
| **A concrete character-limited format, explicitly separated from a "git-agnostic" task title** | Jules (leaked) — "a short subject line (50 chars max), a blank line, and a more detailed body if necessary," with `submit`'s `title`/`description` parameters required to be "git-agnostic" and kept structurally separate from the actual `commit_message` parameter — no other source in this survey draws that line as explicitly. |
| **A named template pointed to but not itself captured** | Crush — "follow the `<git_commits>` format from the bash tool description exactly, including any configured attribution lines" — the template lives in a file not present in this collection, a real capture gap rather than a confirmed absence. |
| **Generic "descriptive commits" guidance, no format specified** | Factory/Droid (leaked) — "Implement changes in small, logical commits with descriptive messages," no subject-line limit, no trailer, no worked example. Devin (leaked) similarly has no enforced format, only a fixed committer identity ("Devin AI" / `devin-ai-integration[bot]@users.noreply.github.com`) with an explicit don't-change-it rule. |
| **A process (gather-then-draft-then-commit), no format spec** | Cursor (leaked) — but only in a sixth, differently-provenanced capture (`Agent Prompt (asgeirtj capture).md`, see `leaked/cursor/README.md`), not in any of Cursor's five other captured prompts: "Run git status, git diff, and git log in parallel," "Analyze all staged changes and draft a commit message," "Always pass commit messages via HEREDOC" — a real process description with explicit prohibitions (no config changes, no destructive commands, no skipped hooks), but no character limit, no trailer/attribution format, and no worked example, so it lands here rather than in the more fully-specified rows above. |
| **Procedural git-safety guidance that's a near-verbatim match to a different source's own trailer-format row, with the trailer itself dropped** | Grok Build (leaked) — `run_terminal_command`'s git guidance ("Prefer creating a new commit rather than amending an existing commit... Before running destructive operations... Never skip hooks (--no-verify) or bypass signing (--no-gpg-sign) unless the user has explicitly asked for it") is a clause-for-clause match to Claude Code's own leaked Bash-tool guidance (row above, and `leaked/claude-code/claude-code-2.1.172-opus-4.6.md`) — everything **except** the HEREDOC template and the `Co-Authored-By`/session-URL trailer that sits right next to it in Claude Code's version. The safety-procedure text was carried over; the commit-message-formatting convention next to it wasn't — see `leaked/grok-build/README.md` for the full side-by-side quote. |
| **No convention found; commit messages aren't the agent's concern at all** | Aider — commits happen automatically via the surrounding harness, not something the model is instructed to phrase (see §2). SWE-agent, mini-swe-agent, Augment SWE-bench Agent — none of these ever produce a commit at all (see §2, §3). |
| **Not addressed / capture gap** | Cline, Roo Code (both publicly known to have git-adjacent "Checkpoints" features but silent in the captured prompt-assembly layer), Goose, Pi, Windsurf, Warp, Replit. Five of Cursor's six captures also belong here (see the row above for the sixth). |

## 2. When (and whether) the agent commits

The sharpest, most consistent finding across this whole doc: **"don't
commit unless explicitly asked" is close to a universal default**
among sources that address the question at all — with real variation
in how strictly that default is enforced, and one striking exception
that inverts it entirely.

- **Unconditional, hardcoded prompt-level prohibition, independent of
  any configurable permission system**: Claude Code (leaked) — "NEVER
  commit changes unless the user explicitly asks you to. It is VERY
  IMPORTANT to only commit when explicitly asked, otherwise the user
  will feel that you are being too proactive." No settings-file key or
  environment variable was found anywhere in this collection's
  permissions research that toggles this specifically — file edits and
  bash commands get the full six-mode permission machinery; committing
  is gated by one separate, non-configurable rule layered independently
  on top of whatever mode is active.
- **The same line, verbatim, in an unrelated codebase** — OpenCode's
  base persona prompt: "NEVER commit changes unless the user explicitly
  asks you to. It is VERY IMPORTANT to only commit when explicitly
  asked, otherwise the user will feel that you are being too
  proactive" is word-for-word identical to Claude Code's leaked prompt
  text. Given this collection's existing finding that OpenCode's
  compaction/turn-output prompts show other signs of Claude-Code
  lineage influence, this is a striking, precisely-quotable data point
  for that pattern rather than a coincidence.
- **The same default, restated per model family with real strictness
  variation within a single product**: OpenCode's `beast.txt`
  (o-series/reasoning models) makes it an absolute prohibition even
  with prior permission ("You are NEVER allowed to stage and commit
  files automatically"); `kimi.txt` goes further still with the
  strictest per-call re-confirmation requirement found in this whole
  survey — "Ask for confirmation each time when you need to do git
  mutations, **even if the user has confirmed in earlier
  conversations**," explicitly defeating session-level standing
  approval. Copilot Chat shows the same family-by-family split:
  non-Codex OpenAI prompts state "Do not `git commit` your changes or
  create new git branches unless explicitly requested" verbatim across
  six files; Anthropic-family gets a broader reversibility-based
  policy naming git actions as examples rather than a blanket gate;
  Gemini/xAI/GLM/MiniMax/Family H prompts have no git-specific content
  at all.
- **A gate with an unusually loose trigger — confidence OR request,
  not request alone**: Jules (leaked) — `submit` fires "when you are
  confident the code changes are complete by running all relevant
  tests and ensuring they pass OR when the user asks you to commit,
  push, submit, or otherwise finalize the code" — the only source in
  this survey where the agent's own self-assessed confidence is a
  sufficient condition on its own, not just a necessary one alongside
  explicit request.
- **A code-level, not merely prompted, ban** — Augment SWE-bench
  Agent: `bash_tool.py`'s `banned_command_strs = ["git init", "git
  commit", "git add"]`, enforced by substring match before the command
  reaches the shell. The only confirmed non-prompted git restriction
  in this entire survey — every other "don't commit" rule examined
  here is text the model could, in principle, ignore.
- **The one genuine inversion of the universal default**: Aider — every
  AI-made edit becomes its own git commit automatically, with no
  model instruction or configurability visible in the captured prompt
  text at all. The decision and the act both belong to the surrounding
  harness; the model has no say in whether to commit. (Aider's real
  `--auto-commits`/`--no-auto-commits` CLI flag, per public docs, lives
  outside what's captured here.)
- **A softer default — conditional on task judgment, not gated behind
  explicit request** — OpenHands: "Use `git status`... Use `git commit
  -a` whenever possible," paired with a don't-commit-junk rule
  (respect `.gitignore`, ask if unsure) — commits happen when the
  agent judges it's appropriate mid-task, a real middle ground between
  Claude Code's absolute prohibition and Aider's absolute automaticity.
- **A confirmed, checked absence of the rule entirely — not a softer
  version of it, just nothing** — GitHub Copilot CLI (leaked): a
  targeted search of both captures for `commit`/`branch`/`push`/
  `worktree`/`PR` turns up exactly one git-timing-adjacent instruction
  anywhere, and it governs *format* (the mandatory `Co-authored-by`
  trailer, §1), not *whether or when* to commit. Neither file's
  `code_change_instructions`, `tips_and_tricks`, nor `task_completion`
  sections say anything about commit permission or timing. Distinct
  from OpenHands's softer conditional default above — this isn't a
  looser version of "don't commit unless asked," it's the absence of
  any stated policy on the question at all, in a source that otherwise
  invests real prompt-engineering effort in adjacent areas (its `bash`
  tool's sync/async/detach state machine, its SQL-based todo system).
- **A second, more pointed instance of the same absence — pointed
  because the surrounding procedural git-safety text is otherwise a
  near-verbatim match to a source that *does* state the rule** — Grok
  Build (leaked): the `run_terminal_command` git guidance quoted in §1
  reproduces Claude Code's own leaked Bash-tool safety text almost word
  for word, but Claude Code's adjacent, separately-stated "NEVER commit
  changes unless the user explicitly asks you to" prohibition (this
  section's opening bullet) has no counterpart anywhere in Grok Build's
  captured prompt. Whatever governs *when* Grok Build may commit isn't
  the general git-safety procedure it otherwise closely mirrors — a
  concrete illustration that copying (or converging on) one vendor's
  procedural text doesn't imply copying its policy text alongside it.
- **Push and PR-creation get an even stricter default than committing,
  almost everywhere it's addressed**: OpenHands ("Do not push to the
  remote branch and/or start a pull request unless explicitly asked to
  do so"), Gemini CLI ("Never push changes to a remote repository
  without being asked explicitly"), Crush ("NEVER PUSH TO REMOTE"),
  Devin ("Never force push, instead ask the user for help if your push
  fails" — the strongest, most explicit force-push prohibition found
  in this survey), Warp (a named exception carved out of its otherwise
  strong bias-toward-action stance specifically for commit/push).

## 3. Checkpoint and undo systems

The axis with the widest spread of sophistication in this whole doc —
from nothing, through single-file undo stacks, to a fully automatic,
git-based, session-integrated `/undo` feature.

| Design | Sources |
|---|---|
| **A fully automatic, git-based checkpoint system, triggered every LLM step, wired into a real session-level undo/redo feature** | OpenCode — a shadow git repository (`--git-dir`/`--work-tree`, separate from `.git`), seeded from the real repo's object database specifically to avoid re-hashing cost on huge checkouts, capturing state before every LLM step starts (a code comment explains the precise timing requirement: tool calls can execute before the event handler fires). A second, parallel implementation captures bare content-addressed git *trees* per step instead of commit objects. `SessionRevert.Service` walks a session's message history to a target point and restores the filesystem (full restore, or selective per-file revert batching up to 100 files per `git checkout` call), plus a mirror-image `unrevert()` (redo). On by default (opt-out, not opt-in), auto garbage-collected hourly. |
| **A hidden shadow-repo checkpoint system snapshotting code and conversation history together as one unit** | Gemini CLI — a `GitService` shadow repo with a from-scratch `.gitconfig` ignoring the user's global config entirely, gated to file-*editing* tool calls only, firing **before the user even approves the edit** — commit message always `Snapshot for ${toolCall.name}`, `--no-verify` to skip the user's own hooks. The resulting commit hash and the full conversation history at that point are written together as one JSON checkpoint file; restore reverts the working tree (`git restore --source <hash> .` + `git clean -fd`) *and* reloads the saved conversation history into the session in one operation. Off by default, requires a restart to enable, surfaced via `/restore [checkpoint-name]`. |
| **A repo-wide, explicitly non-git "restore to original state" primitive** | Jules (leaked) — `reset_all()`/`restore_file()` (renamed `reset_file` in a later snapshot), framed entirely as "restore to task-start state," never described in git terms — consistent with `submit`'s own "git-agnostic" framing, this reads as a sandbox/VM-snapshot or diff-tracking mechanism abstracted away from git rather than literal `git checkout`/`git reset`. The cleanest repo-wide reset primitive in this survey — simpler than every single-file alternative, and unlike them, works at both file and whole-repo scope. |
| **A per-file undo stack that exists specifically because git write access is locked out** | Augment SWE-bench Agent — `str_replace_tool.py` maintains `_file_history = defaultdict(list)`, pushing pre-edit content onto a per-path stack before every mutating command; `undo_edit` pops and restores the most recent entry. Held in the Python process's own memory, doesn't survive tool re-instantiation — the *only* undo mechanism available precisely because `git commit`/`git add`/`git init` are code-level banned (§2), an unusual case where the absence of git access causes a bespoke non-git undo mechanism to exist rather than the two being unrelated design choices. |
| **A single-file, editor-integrated undo, unrelated to git** | Devin (leaked) — `undo_edit` "Reverts the last change that you made to the file at the specified path." Replit (leaked) — `str_replace_editor`'s `undo_edit` command, structurally identical in shape. Neither is git-based, neither is codebase-wide. |
| **Automatic, in-memory reversion on two specific failure paths, narrower than the product's own public branding implies** | Cline — if a task resumes after an interrupted `replace_in_file`/`write_to_file`, or a SEARCH/REPLACE block fails to match, the harness automatically restores the pre-edit file content it already holds in memory. No stash/shadow-commit language anywhere, and the mechanism only fires on those two failure paths — narrower than what Cline's publicly-documented "Checkpoints" feature implies; that feature is named once in the captured prompt (a bare docs-sub-page label) but never mechanically specified. |
| **Confirmed absent in the captured prompt-assembly layer, with an unusually strong methodological precedent for treating this as a capture gap** | Roo Code — no `taskResumption`-equivalent function exists in its version of `responses.ts`, despite sharing Cline's lineage and even some function names; this collection's own prior research on Roo Code found its Tool-surface and Sub-agents sections were originally wrong when based only on these same prompt-assembly files, corrected only after a live fetch of the tool-implementation layer — the same caveat should apply here, especially since Roo Code (like Cline) is publicly known to ship a "Checkpoints" feature. |
| **No checkpoint/undo system found, and the harness explicitly forbids the agent from creating one via `git revert`** | Crush — "DON'T REVERT CHANGES: Don't revert changes unless they caused errors or the user explicitly asks" governs when the *agent itself* may undo its own work; it is not a snapshot-and-restore mechanism. |
| **No checkpoint system; the deliverable is a diff, so nothing needs reverting** | SWE-agent, mini-swe-agent, Augment SWE-bench Agent (beyond its own per-file undo stack above) — none of these commit at all; a `git checkout -- <path>` targeted revert exists in SWE-agent's submission checklist only to strip forbidden test-file edits before scoring, not as a general rollback tool. |
| **Not found / capture gap** | Goose, Pi (both plausible capture gaps — see each source's own README for the specific caveat), Aider (its per-edit auto-commit *is* its checkpoint system — see §2), Cursor, Windsurf, Warp, Replit (beyond the editor-level `undo_edit` above), Factory/Droid, OpenHands, Copilot Chat. |

**The headline finding of this whole doc**: OpenCode and Gemini CLI
**independently arrived at the same core idea** — a hidden shadow git
repository, structurally separate from the user's real `.git`, used
purely as a checkpoint engine — but landed on materially different
designs. OpenCode's captures bare trees per step, fully automatic, on
by default, with a real selective per-file revert/unrevert wired into
session history. Gemini CLI's captures full commits only before
file-edit proposals specifically, off by default, and — the one
property that distinguishes it structurally from OpenCode's — bundles
the **conversation history** into the same checkpoint as the code
state, restoring both together. Codex has the identical "shadow git
repo used purely as a diff primitive" building block (`baseline.rs`)
but points it at its own memory-writing subsystem, never at
user-code checkpointing — making Codex the one source of the three
CLI-shaped products investigated in depth with **no user-facing
checkpoint/undo system at all**.

## 4. Worktree isolation

- **A shipped, documented, user-facing feature explicitly framed for
  parallel-session isolation** — Gemini CLI: "When working on multiple
  tasks at once, you can use Git worktrees to give each Gemini session
  its own copy of the codebase... This prevents changes in one session
  from colliding with another." `--worktree`/`-w [name]` (behind an
  `experimental.worktrees` setting) creates a fixed `worktree-<name>`
  branch. Cleanup on exit is conditional, not the unconditional
  "never auto-delete" its own docs page alone might suggest — a
  completely unmodified worktree *is* auto-removed; only one with
  actual changes is preserved.
- **A dedicated service with the same shape, a different branch
  prefix, and an added bootstrap step** — OpenCode: `Worktree.Service`
  creates `git worktree add --no-checkout -b opencode/<name>
  <directory>`, with up to 26 collision-retry attempts and an optional
  **startup script** so each worktree can bootstrap its own dev
  server/dependencies after creation. Gated behind the same
  experimental background-sub-agents flag this collection's Sub-agents
  research already documented — not yet the default path for the
  `task` tool.
- **User/project-invoked session-mode-switching, not a background
  parallelism primitive** — Claude Code: `EnterWorktreeTool`/
  `ExitWorktreeTool` (confirmed via this live session's own current
  tool schemas and independently corroborated by a richer leaked
  prompt capture — see `leaked/claude-code/README.md`) are explicitly
  gated to avoid being confused with ordinary branch work — "Use this
  tool ONLY when explicitly instructed to work in a worktree... Never
  use this tool unless 'worktree' is explicitly mentioned." Creates a
  real `git worktree` inside `.claude/worktrees/`, with a pluggable
  non-git fallback outside a git repo ("delegates to
  WorktreeCreate/WorktreeRemove hooks for VCS-agnostic isolation").
  Composes with sub-agent isolation (works from agents whose cwd was
  pinned at launch). A `path` parameter enters an already-*existing*
  worktree rather than always creating a new one, with its own
  concurrency rule (can't create a new worktree while already in one,
  but switching into an existing one via `path` is fine). Fail-closed
  removal: refuses to remove a worktree with uncommitted changes
  unless explicitly told to discard them, and never removes one
  silently on session exit — the two dispositions (`keep`/`remove`)
  also govern any tmux session running inside the worktree, left
  running for reattachment on `keep`, killed on `remove`.
- **Worktree-*aware*, never worktree-*creating***: Codex CLI — no
  mechanism anywhere in the codebase creates a `git worktree` for
  parallel tasks or sub-agents (`spawn_agent`'s schema has no
  directory parameter at all — sub-agents share the parent's working
  directory). Two places acknowledge worktrees exist without creating
  them: a doc comment admitting `get_git_repo_root` doesn't detect
  worktrees created externally (workaround: `--allow-no-git-exec`),
  and hook-config resolution that explicitly branches on "is this a
  git repo, a git worktree, or just a cwd" when the user is already
  inside one. Codex Cloud's background tasks don't create client-side
  worktrees either — isolation there happens entirely server-side.
- **Gated behind a sub-agent role, not a directly-callable primitive,
  and framed around ensembling rather than concurrency** — Cursor
  (leaked): a sixth, differently-provenanced capture (`Agent Prompt
  (asgeirtj capture).md`, mirrored from a different aggregator than
  Cursor's other five captures — see `leaked/cursor/README.md`) names
  a `best-of-n-runner` sub-agent type, reachable only through the
  `Task` tool's `subagent_type` parameter, whose entire specification
  is one line: **"Run a task in an isolated git worktree."** This is
  the first confirmed worktree-isolation mechanism found anywhere in
  Cursor's captured material — none of Cursor's other five dated
  prompts or its tools JSON mention worktrees at all. Two things set
  it apart from the three creating implementations above rather than
  simply joining them: (1) there is no visible model-facing tool that
  creates, enters, or removes a worktree directly — the main agent can
  only reach the mechanism by delegating to this specific sub-agent
  role, unlike Claude Code's/OpenCode's/Gemini CLI's directly-callable
  worktree tools/flags; and (2) the name itself — "best-of-n," sampling
  terminology for generating N independent candidate solutions and
  selecting the best — implies the isolation exists to support running
  **multiple parallel attempts at one task** for later comparison,
  rather than isolating concurrent *different* tasks or sessions the
  way every other row in this section does. No branch-naming
  convention, subdirectory location, cleanup policy, or
  winner-selection mechanism is captured — the one-line spec is all
  there is, making this the thinnest of the four worktree findings in
  this section by a wide margin, and a real capture gap rather than a
  confirmed "that's all it does."
- **A second sub-agent-gated instance, with the opposite framing from
  Cursor's** — Grok Build (leaked): `spawn_subagent`'s `isolation`
  parameter (`"none"` default vs. `"worktree"`, "isolated git
  worktree," mutually exclusive with an explicit `cwd`) is likewise
  reachable only through delegation, not a directly-callable primitive
  for the main conversation the way Gemini CLI's/OpenCode's/Claude
  Code's worktree tools are. But where Cursor's `best-of-n-runner`
  frames worktree isolation around *ensembling* (N attempts at the same
  task, later compared), Grok Build's framing is ordinary task
  isolation — protecting a delegated task's edits from the parent
  session's working tree, the same concurrency-isolation purpose as the
  three directly-callable implementations, just gated one level deeper.
  No branch-naming convention, subdirectory location, or cleanup policy
  is captured for either sub-agent-gated variant.
- **The three fully-specified creating implementations converge on the
  same shape**: a fixed subdirectory under a tool-branded path
  (`.gemini/worktrees/`, `~/.local/share/opencode/worktree/`,
  `.claude/worktrees/`) and a fixed branch-naming prefix
  (`worktree-<name>`, `opencode/<name>`, unnamed-but-new-branch for
  Claude Code) — three independent teams landed on structurally
  identical designs. Cursor's `best-of-n-runner` is deliberately *not*
  folded into this convergence claim: its one-line capture gives no
  subdirectory or branch-naming detail to compare, and its
  ensembling-not-concurrency framing (above) may make it a
  conceptually different feature rather than a fourth data point for
  the same one — a real "maybe," not a confirmed fourth convergence.
- **Confirmed absent everywhere else checked**: every remaining source
  in this survey — no worktree-isolation concept was found in any of
  the other sources' captured files, and for several (Windsurf, Warp,
  Devin, Factory) this is a targeted, confirmed negative rather than a
  capture gap, since git content was otherwise present and thoroughly
  searched.

## 5. Branch management rules

- **A dedicated timestamp-based naming template, with an explicit
  default-if-unspecified clause**: Devin (leaked, autonomous/background
  web product) — "Default branch name format:
  `devin/{timestamp}-{feature-name}`. Generate timestamps with `date
  +%s`. Use this if the user or do not specify a branch format." **Not
  present in Devin's separately-captured interactive CLI variant**
  (`leaked/devin/CLI Prompt.md`) — its git section has no branch-naming
  convention at all, a confirmed omission (full-prompt read) rather than
  a capture gap. See `leaked/devin/README.md`'s CLI-variant section.
- **Fixed, tool-branded prefixes, no timestamp component** — Gemini
  CLI (`worktree-<name>`), OpenCode (`opencode/<name>`, both for its
  worktree service and its GitHub Action bot's `opencode/issue<id>-
  <timestamp>` / `opencode/<type>-<hex6>-<timestamp>` conventions).
- **Descriptive-but-unstructured naming, with an explicit branch-reuse
  rule for follow-up work**: Jules (leaked) — "Use a short, descriptive
  branch name... If you are given a new, unrelated task after
  submitting, you should start a new plan and use a new branch name.
  If the new request is a follow-up to the same task, you may continue
  using the same branch."
- **A name-keyed heuristic standing in for real branch-protection
  detection** — OpenHands: "work within the current branch... unless...
  the current branch is 'main', 'master', or another default branch
  where direct pushes may be unsafe" — a prompt-only proxy keyed
  purely off branch name, not any actual protection-rule lookup.
- **An explicit, repeated prohibition on committing to default
  branches, paired with a strict environment-setup gate before branch
  creation is even allowed** — Factory/Droid (leaked): "Create the
  branch only AFTER successful git sync + frozen/locked install +
  validation," and "never commit directly to default branches,"
  stated twice.
- **Branch creation bundled into the same gate as committing, so no
  separate naming convention exists** — the non-Codex OpenAI-family
  Copilot Chat prompts: "Do not `git commit` your changes or create
  new git branches unless explicitly requested" — since branches
  aren't created without being asked, there's nothing to name by
  convention.
- **No naming convention, no force-push policy, no protected-branch
  language found at all** — Cline, Roo Code, Crush, Cursor, Windsurf,
  Warp, Replit, Goose, Pi, Aider, SWE-agent, mini-swe-agent, Augment
  SWE-bench Agent (none of the last three ever create a branch — the
  deliverable is a diff).
- **Force-push is addressed explicitly in exactly one source**: Devin
  (leaked, autonomous/background web product) — "Never force push,
  instead ask the user for help if your push fails." Every other source
  in this survey is silent on force-push specifically (some address
  `git reset --hard`/`git push --force` together as generically
  "destructive," e.g. Copilot Chat's Anthropic-family
  `operationalSafety` tag and its OpenAI Codex-family "dirty worktree"
  section, but none singles out force-push with its own dedicated rule
  the way Devin does). **Devin's separately-captured interactive CLI
  variant** (`leaked/devin/CLI Prompt.md`) folds force-push into a
  general "Destructive Operations" confirm-before-acting list instead of
  giving it its own absolute, unconditional prohibition — and also drops
  the background variant's "never use `git add .`" rule entirely. See
  `leaked/devin/README.md`'s CLI-variant section.

## 6. PR and push workflow

- **A literal, fully-specified PR template, with a parallel-gather-
  then-analyze research step first** — Claude Code (leaked): gathers
  `git status`/`diff`/`log`/upstream-tracking state in parallel, reads
  the *entire* branch's commit history since divergence ("NOT just the
  latest commit"), then `gh pr create --title "..." --body "$(cat
  <<'EOF' ## Summary <1-3 bullets> ## Test plan [checklist] EOF)"`. No
  distinct self-review-before-opening step — the model analyzes the
  diff/history to draft the summary, but isn't told to critique it for
  bugs first.
- **A structured content *set* rather than a section-by-section
  template, tied to a draft/non-draft decision tree** — Factory/Droid
  (leaked): a non-draft PR requires evidence of successful dependency
  install, all quality checks green, and a clean worktree; PR contents
  must "Mark it **Droid-assisted**. Include summaries/logs showing
  installs and all quality checks passed. Provide a brief rationale
  and reference relevant issue/ticket."
- **Session-hygiene rules for an already-open PR, not seen phrased
  this way elsewhere** — OpenHands: "create only ONE per session/issue
  unless explicitly instructed otherwise," "update it with new commits
  rather than creating additional PRs for the same issue," "preserve
  the original PR title and purpose, updating description only when
  necessary." OpenCode's GitHub Action bot implements the same
  discipline at the infrastructure level — it dedupes PR creation
  against an already-open PR for the same head→base pair.
- **A per-comment review-thread tracking primitive, not a full
  checklist generator** — Devin (leaked): `gh_pr_checklist` lets the
  model mark individual PR review comments `done`/`outdated` one at a
  time, functioning as a manual todo-list over review threads. Jules
  (leaked) has the closest analog — `read_pr_comments`/
  `reply_to_pr_comments`, replying to individual comments as a JSON
  array of `{comment_id, reply}` objects — closing the loop between
  the agent's own work and a human reviewer's feedback after the PR is
  already up.
- **A full first-party automation bot, the only one of its kind found
  among the CLI-shaped products investigated directly** — OpenCode's
  GitHub Action (`opencode-agent[bot]`): generates its own commit
  message and PR title via a dedicated cheap LLM call, verifies real
  commits exist between base and head before calling the PR-create API
  (working around a documented GitHub 422 edge case in shallow
  clones), retries transient API failures once with backoff, and —
  distinctively — detects when the underlying agent has already taken
  independent git action mid-session and stands down rather than
  double-pushing.
- **A maintainer-only skill bundle, richer than anything shipped to
  ordinary users of the same product** — Codex CLI's `.codex/skills/`
  (for working on the Codex repo itself): `babysit-pr/SKILL.md` polls
  CI, classifies failures as branch-related (auto-fix) vs. flaky
  (bounded retry), restricts itself to published comments from trusted
  authors, and enforces a strict mutation policy (never close/reopen
  PRs, never toggle draft status, always prefixes bot replies with
  `[codex]`); `codex-pr-body/SKILL.md` gives PR-description-writing
  guidance including explicit Sapling-SCM stacked-PR support. Neither
  skill is confirmed to be part of what ordinary Codex CLI users get —
  this is dogfooding tooling, not a general product feature.
- **A structurally novel, confirmed-parsed-but-not-confirmed-executed
  mechanism**: Codex CLI's model-emitted inline "git action
  directives" (`::git-stage{...}`, `::git-create-pr{... isDraft="true"}`,
  etc.) embedded in the assistant's own markdown and stripped before
  the user sees them — only the `CreateBranch` directive is actually
  acted on (re-syncing a UI-tracked branch name); `Stage`/`Commit`/
  `Push`/`CreatePr` are parsed but have no confirmed call site that
  executes them anywhere in the public repo. Flagged as a known-
  unknown (plausibly wired up in a separate client not present in this
  repo), not a verified feature.
- **No PR-creation tooling found at all** — Gemini CLI (a branch-name
  hook exists purely for UI display), Cline, Roo Code, Crush, Goose,
  Pi, Windsurf, Warp (reads PR/issue info via `gh` but never creates
  one), Replit, Copilot Chat (no PR-description template or "search for
  a PR template" instruction found anywhere — PR mechanics are left
  entirely to whatever GitHub MCP/extension tools happen to be
  available at runtime). GitHub Copilot CLI (leaked) belongs in this
  row too, with its own stated preference for how to reach the
  read-only tools it does have: "For GitHub operations (issues, pull
  requests, repositories, workflow runs, etc.), prefer the `gh` CLI via
  bash over MCP tools" — the same `gh`-over-MCP framing as Warp, plus
  read-only `github-mcp-server/*`/`github/*`-prefixed tools
  (`get_pull_request`, `list_branches`, `pull_request_read`, etc.)
  wired into its `explore`/`research` sub-agents, with no create/merge/
  push-adjacent tool named in either capture. **Cursor is a partial
  exception, on correction**: five of its six captures still fit this
  row exactly
  (only the read-only `fetch_pull_request` lookup tool — no creation,
  no template, no self-review step), but the sixth, differently-
  provenanced `Agent Prompt (asgeirtj capture).md` (see
  `leaked/cursor/README.md`) has a real, process-level commit-and-PR
  workflow: gather `git status`/`diff`/`log` (and, for PRs, remote-
  tracking state) in parallel, draft a message/summary, then commit or
  "push to remote and create PR using `gh pr create`" — with explicit
  prohibitions on config changes, destructive commands, and skipping
  hooks, and a HEREDOC formatting rule for commit messages. No
  character limit, trailer/attribution format, or worked PR-body
  template is given, so it's still thinner than Claude Code's or
  Factory/Droid's fully-specified content — but "no PR-creation tooling
  found at all" no longer holds across Cursor's full captured corpus,
  only across five-sixths of it.
- **No self-review-before-PR step confirmed anywhere in this survey**
  — every source with a PR workflow at all either skips a distinct
  self-critique step or defers to a separately-invoked, never-auto-
  chained review mechanism (Codex's `ReviewTask`, OpenCode's `/review`
  — both already documented in `agent-self-verification.md`'s §4
  conflation-trap section). PR creation and self-verification remain
  two mechanisms that don't talk to each other in every source checked.

## 7. Absences and confirmed non-findings

Worth stating explicitly since several of these run against strong
public branding for the product in question — these are genuine
findings, not just gaps in what was checked.

- **Goose, Pi**: no git/VCS content of any kind in the captured
  files, in both cases with a specific, evidenced capture-gap
  explanation (Goose's tools are entirely extension-supplied and
  unread; Pi's `bash` tool description is passed in from outside this
  collection) — not confirmed product-level absences.
- **Cline, Roo Code**: both publicly known to ship a "Checkpoints"
  feature, and both show zero trace of it in the captured
  prompt-assembly layer — Cline names the feature once as a bare docs
  link, Roo Code doesn't mention it at all. This collection's own
  prior research on Roo Code found two other sections (Tool surface,
  Sub-agents) were wrong for exactly this reason (prompt-assembly-only
  search) before a live-source fetch corrected them — the same
  caveat applies here with at least as much force.
- **Replit**: despite the product's well-known "Checkpoints" branding,
  genuinely near-zero git/VCS content in either captured file — the
  cleanest "not found" case in this survey for a source with strong
  public feature claims to the contrary.
- **Windsurf, Warp, Google Antigravity**: all three have real,
  substantial tool surfaces and permission architectures documented
  elsewhere in this collection, yet essentially no git-specific policy
  beyond what falls out of their general command-approval mechanisms —
  a genuine, confirmed thinness, not an oversight in this research
  pass. Antigravity's case is the most pointed: its IDE prompt's full
  23-tool schema has zero git-specific tools among them, and its own
  "checkpoint" references turn out to mean a conversation/session
  save-point, not a git-based code checkpoint — worth explicitly
  distinguishing from this doc's §3 (OpenCode's and Gemini CLI's
  actual shadow-git checkpoint systems), since the terminology overlap
  invites exactly that confusion. **Cursor previously belonged in this
  bullet and no longer does, on correction**: five of its six captures
  are still exactly this thin, but the sixth (`Agent Prompt (asgeirtj
  capture).md` — see §4 and §6 above, and `leaked/cursor/README.md`)
  has a real commit/PR process, a worktree-isolation mechanism, and a
  named approval-mode taxonomy (`agent-permissions-approval.md` §1) —
  enough that Cursor is better read as an inconsistently-captured
  source (thin in five extractions, substantive in a sixth) than as a
  confirmed thin source across the board, the same distinction this
  doc draws for Antigravity between its IDE and CLI prompts elsewhere.
- **Zed**: no commit-message convention, no branch-naming rule, no
  PR/push workflow, and no checkpoint/undo or worktree-isolation
  system — but not a thin source overall (it has this doc's richest
  sandbox description, §6 of `agent-permissions-approval.md`), and
  that sandbox is where its one real git-relevant finding lives: `.git`
  metadata is hardcoded-protected across every platform branch of the
  sandbox, and any operation that needs to write it (commit, checkout,
  merge, etc.) requires the full `unsandboxed: true` escape hatch —
  meaning ordinary git usage is structurally treated as a *higher-
  trust* operation than regular file edits, not simply gated by the
  same prompted "ask first" convention every other source in this doc
  uses. The prompt's own "worktrees" terminology refers to the
  project's already-open root directories, not a git-worktree creation
  mechanism — worth flagging so it isn't confused with §4's actual
  worktree-isolation services.
- **GitHub Copilot CLI** (leaked): a real, checked absence of "don't
  commit unless asked" (§2) sitting alongside the collection's usual
  fixed-trailer convention (§1) — worth reading as a genuine gap rather
  than a capture artifact, since both files are otherwise dense with
  operational detail on adjacent topics (tool-usage discipline,
  session-state management). No branch-naming convention, no
  worktree-isolation mechanism, and no PR-creation tooling or template
  in either capture (§6). One real terminology trap worth flagging
  explicitly, the same one this doc's §7 already documents for Google
  Antigravity: its `session_store`'s `checkpoints` table
  (`checkpoint_number`/`title`/`overview`/`work_done`/`next_steps`) is
  a **conversation checkpoint**, not a git checkpoint — see
  `agent-context-compaction.md` for that mechanism — and shouldn't be
  miscounted as evidence of a shadow-git/undo system in the sense
  OpenCode's or Gemini CLI's (§3) actually are.
- **SWE-agent, mini-swe-agent's base config, Augment SWE-bench Agent**:
  no checkpoint, no worktree, no branch rules, no PR/push workflow —
  by design, not by omission. All three submit a diff for external
  scoring; there is no live remote to push to or PR to open in the
  benchmark-harness architecture they share.

---

## Design takeaways

- **"Don't commit unless asked" is the closest thing to a universal
  convention found in this entire collection, on any axis, in any of
  the eight synthesis docs so far** — more consistent than the
  SWE-bench workflow template in `agent-self-verification.md`, more
  consistent than any trigger model in `agent-context-compaction.md`.
  Where it's stated at all, it's stated the same way: an absolute or
  near-absolute default-off, with explicit user request as the
  unlock. Aider is the sole confirmed exception, and it inverts the
  rule by architecture (every edit *is* a commit) rather than by
  choosing a looser policy — there's no source in this survey that
  simply decided a moderate "commit reasonably often" policy was fine.
- **Grok Build's git-safety guidance sharpens this doc's existing
  cross-vendor-text-match finding (OpenCode's word-for-word "don't
  commit unless asked" line, §2) into a much larger-scale instance, and
  changes what kind of pattern it looks like.** One sentence matching
  verbatim across two unrelated codebases is consistent with either
  direct copying or a shared internal style guide circulating
  informally; a full paragraph of procedural git-safety text — amend-
  vs-new-commit guidance, the exact `git reset --hard`/`git push
  --force`/`git checkout --` example list, the `--no-verify`/
  `--no-gpg-sign` hook-skipping clause, in the same order — matching
  clause-for-clause between Grok Build (xAI) and Claude Code
  (Anthropic), *while the adjacent commit-message-trailer convention
  and the "don't commit unless asked" policy line do not carry over*,
  reads differently: as one company's procedural tool-description text
  ending up, largely intact, inside a competitor's product, with the
  policy-level instructions authored independently around it. See
  `leaked/grok-build/README.md` for the full quote set, which extends
  well beyond git guidance into several other tool descriptions.
- **The two richest findings in this whole doc — OpenCode's and
  Gemini CLI's shadow-git checkpoint systems — are a genuine
  independent-convergence case, the same signal this collection's
  other docs have repeatedly flagged for sub-agent protocols,
  compaction pipelines, and permission-classifier LLMs**: two
  unrelated engineering teams solved "how do we let a coding agent
  edit files freely without real risk" with the same core idea (a
  hidden git repo used purely as a checkpoint engine) and diverged
  only on the details that reflect each product's own priorities —
  OpenCode optimizes for granular, low-cost, high-frequency capture
  wired into a real undo/redo UI feature; Gemini CLI optimizes for
  bundling code and conversation state together so a restore is a
  complete return to a prior moment, not just a file-state rollback.
  Codex has the identical building block (a shadow git repo as a diff
  primitive) but never pointed it at user-code checkpointing at all —
  a genuine product-philosophy gap between Codex and its two closest
  CLI-shaped peers, not just a documentation gap.
- **Worktree isolation is real, shipped, and independently converged
  on the same shape by three separate teams (Gemini CLI, OpenCode,
  Claude Code)** — a fixed tool-branded subdirectory and a fixed
  branch-naming prefix, in every case gated behind an explicit
  opt-in (a flag, a setting, or the word "worktree" appearing in the
  user's own request) rather than ever happening silently. Codex CLI
  is the clean counter-example: worktree-*aware* in two separate
  places in its codebase, but never worktree-*creating* anywhere —
  worth reading as a deliberate scope decision (leave multi-checkout
  orchestration to Codex Cloud's server-side isolation) rather than an
  oversight, given how much of the rest of Codex's permission/sandbox
  architecture (`agent-permissions-approval.md`) is unusually
  sophisticated. **A fourth data point exists (Cursor's
  `best-of-n-runner`, §4) but is deliberately not counted as a fourth
  convergence on the same design**: its one-line capture gives no
  subdirectory or branch-prefix detail to compare against the other
  three, and its name implies a different *purpose* entirely — worktree
  isolation in service of running N competing attempts at one task and
  picking a winner, not isolating concurrent distinct tasks or sessions
  the way Gemini CLI, OpenCode, and Claude Code all do. Read it as a
  fourth *source* with worktree isolation, not necessarily a fourth
  team that independently arrived at the *same* design — the evidence
  needed to tell those apart (directory layout, branch naming, cleanup
  policy, and — distinctively for this one — a result-selection
  mechanism) simply isn't in the capture. **A fifth data point, Grok
  Build's `spawn_subagent` `isolation: "worktree"` parameter (§4),
  shares Cursor's "gated behind a sub-agent, not directly callable"
  shape but not its ensembling framing** — its purpose reads as
  ordinary task isolation, the same purpose as the three directly-
  callable implementations, just reached one level of indirection
  deeper. Two unrelated vendors (Anysphere, xAI) independently landing
  on "worktree isolation, but only through a sub-agent" — as opposed to
  a directly-callable tool for the main session — is a modest second
  data point for that specific *access pattern*, even though neither
  capture has enough detail to say whether the underlying worktree
  mechanics themselves converge with the other three.
- **A code-level git restriction (Augment SWE-bench Agent's banned-
  command-string check) is rare enough in this survey to be
  the only one found** — every other "don't commit"/"don't push"
  rule examined across twenty-three sources is prompted text the model
  could, in principle, disregard. This mirrors `agent-permissions-
  approval.md`'s own §2 finding that mechanical, non-LLM gates are
  unglamorous but structurally stronger than prompted instructions —
  here it shows up as a single, narrow, three-string substring check
  rather than a general-purpose policy engine, but the same principle
  applies: it can't be talked out of firing.
- **The "self-review before opening a PR" gap (§6) is a real,
  cross-cutting finding worth reading alongside `agent-self-
  verification.md`'s own §4 "review-as-a-general-tool" conflation
  trap**: sources with a genuine review mechanism (Codex's
  `ReviewTask`, OpenCode's `/review`) never auto-chain it into PR
  creation, and sources with a real PR workflow (Claude Code, Factory/
  Droid, OpenHands) never wire in a distinct self-critique step before
  opening one. The two capabilities exist independently in several
  sources' architectures but are never connected to each other
  anywhere in this survey — a specific, concrete instance of the
  broader pattern that self-verification and PR/git workflow: are
  designed as separate concerns industry-wide, not because connecting
  them would be hard, but because nobody has yet.
- **The "publicly-branded feature, prompt-text-silent" pattern
  (Cline's and Roo Code's Checkpoints, Replit's Checkpoints) is worth
  flagging as its own category of finding, distinct from a simple
  capture gap**: in each case, the product's own marketing confirms a
  real feature exists, and the captured system-prompt text gives the
  model no operational knowledge of it at all — meaning (per this
  collection's own repeated finding that harness-level mechanisms are
  frequently invisible to the model, first established at scale in
  `agent-permissions-approval.md`'s §7) these are very likely genuine
  harness-side features the model neither controls nor is told about,
  not features this research pass simply failed to find.
