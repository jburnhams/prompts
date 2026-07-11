# OpenCode

- **Type**: Coding agent (terminal-based, multi-provider)
- **License**: MIT
- **Source**: https://github.com/anomalyco/opencode (formerly `sst/opencode`;
  the GitHub org was renamed)
- **Retrieved from**: `dev` branch (the repo's default branch),
  `packages/opencode/src/session/` (2026-07-10)

OpenCode selects a different base system prompt per model family/provider
(see `system.ts`'s `provider()` function), then layers on repo-discovered
instructions (`AGENTS.md`/`CLAUDE.md` via `instruction.ts`), skills, MCP
context, and mode-specific reminders (e.g. plan mode).

## Files

- `system.ts` — provider → prompt-variant selection logic, plus environment
  block assembly (model, cwd, platform, date).
- `instruction.ts` — walks the filesystem for `AGENTS.md`/`CLAUDE.md` files
  and folds their contents into the prompt.
- `prompt/default.txt` — fallback system prompt (base "build" agent
  persona/rules/tone, used when no provider-specific variant matches).
- `prompt/anthropic.txt` — variant for Claude models.
- `prompt/gpt.txt` / `prompt/codex.txt` / `prompt/beast.txt` — variants for
  GPT-4/GPT-5/o1/o3/Codex models (`beast.txt` is used for the reasoning
  "o-series" models).
- `prompt/gemini.txt` — variant for Gemini models.
- `prompt/kimi.txt`, `prompt/trinity.txt`, `prompt/meta.txt`,
  `prompt/copilot-gpt-5.txt` — variants for Kimi, Trinity, and other
  provider/model families.
- `prompt/plan.txt`, `prompt/plan-mode.txt`, `prompt/plan-reminder-anthropic.txt`
  — prompts/reminders for the read-only "plan" agent mode.
- `prompt/build-switch.txt` — short reminder injected when switching from
  plan mode back into the "build" (editing) agent.

Not included: `prompt.ts` (~1600 lines) — the session/agentic-loop
orchestrator that wires prompts, tools, and streaming together. It's mostly
implementation code with only a small amount of embedded prompt text
(`MAX_STEPS_PROMPT` etc.), so it's out of scope for this collection.

## Tool surface

- **Shell**: `Bash` — non-trivial commands must be explained to the user
  before running, "especially important when... making changes to the
  user's system."
- **Search**: separate `grep` and `glob` tools (named explicitly in the
  worked example), plus a delegated `Task` tool "to reduce context usage"
  for open-ended search.
- **Code execution**: none beyond `Bash` — no dedicated Python/Node
  execution tool.
- **Browser/web**: `WebFetch`, but scoped narrowly in this prompt to
  self-documentation ("first use the WebFetch tool... from opencode
  docs") — not framed as a general research tool here.
- **Multimodal**: not addressed in `default.txt`.
- **Sandbox/isolation**: not in the prompt text; see
  [`../github-pr-bots/opencode-review/`](../github-pr-bots/opencode-review)
  for the GitHub Action's execution context.
- **Extensibility**: MCP support (`MCP.Service` in `system.ts`) and a
  skills system (`Skill.Service`), both conditionally injected only when
  something is actually configured/available — same "don't pad the prompt
  with unused capability text" instinct as Pi's dynamic tool listing.

## Sub-agents

**Correction to an earlier version of this doc**: this folder only
stores the prompt *text* files, and a first pass concluded the `Task`
tool's schema/protocol simply wasn't captured here. It's more than
uncaptured — reading the actual implementation directly
(`packages/opencode/src/tool/task.ts` and `packages/opencode/src/agent/`,
live on `openai/opencode`'s `dev` branch, not stored in this folder)
shows the Task tool is genuinely **more sophisticated than Claude
Code's stateless one-shot design**, closer in spirit to Codex CLI's
addressable `spawn_agent` family (see `codex/README.md`) but built on a
different primitive: a generic `BackgroundJob` state machine, not a
purpose-built agent-session protocol.

- **Tool ID is literally `"task"`.** Parameters: `description` (3-5
  word label), `prompt` (the task), `subagent_type`, an optional
  `task_id` ("resume a previous task... the task will continue the same
  subagent session as before instead of creating a fresh one"), and —
  gated behind an experimental flag — `background` ("Run the agent in
  the background. You will be notified when it completes. DO NOT sleep,
  poll, or proactively check on its progress").
- **Genuinely stateful, not just resumable-after-completion**: calling
  `task` again with an already-running `task_id` doesn't error or
  block — it gets **queued onto the still-live job** (`background.extend()`)
  and returns immediately. That's a real "send a follow-up to a running
  sub-agent" capability, the same category of thing as Codex's
  `send_input`, not documented anywhere a prompt-text-only read could
  have found it.
- **A race between completion and background-promotion**: by default,
  a `task` call races the job finishing against the job being
  *promoted* to background (`Effect.raceFirst`) — if the user interrupts
  a foreground task rather than killing it, it can detach and keep
  running, later injecting its result back into the parent session as a
  synthetic follow-up message rather than a tool result. Interrupting
  (not promoting) genuinely cancels the child.
- **Named agent registry with real tool-scope and prompt differences**
  (`agent/agent.ts`): built-ins are `build`/`plan` (primary agents, not
  delegates), `general` (subagent, no custom prompt — reuses the
  orchestrator's own base prompt, "execute multiple units of work in
  parallel"), and `explore` (subagent, its **own dedicated system
  prompt**, read-only permission set — grep/glob/list/bash/webfetch/
  websearch/read allowed, everything else denied). A sub-agent's
  `prompt` field, when set, **entirely replaces** rather than appends to
  the model-family base prompt (`session/llm/request.ts`); `general`
  (no custom prompt) falls through to the same base prompt the
  orchestrator uses.
- **Custom sub-agents via Markdown files** — `{agent,agents}/**/*.md`
  with YAML frontmatter, functionally the same convention as Claude
  Code's `.claude/agents/*.md`, confirmed intentional: a code comment in
  `config/markdown.ts` explicitly notes "other coding agents like claude
  code allow invalid yaml in their frontmatter."
- **Recursion denied by default, not silently allowed**:
  `subagent-permissions.ts`'s `deriveSubagentSessionPermission()` denies
  a spawned sub-agent's own `task` tool (and `todowrite`) by default
  unless its specific agent type's ruleset explicitly grants it — the
  `plan` agent, for instance, is allowed to spawn `general` but nothing
  else. A different, more granular position than either Goose's
  blanket "cannot spawn additional subagents" ban or Amp's apparently
  unrestricted recursion.
- **No hard concurrency/file-lock mechanism** — only a prompt-level
  instruction ("avoid working with the same files or topics") backing
  parallel Task-tool calls; safety comes from the permission-ask
  ruleset on individual file edits, not a same-file mutex across
  sub-agents.
- **The richer async/background protocol is explicitly experimental**
  (`OPENCODE_EXPERIMENTAL_BACKGROUND_SUBAGENTS`) — the tool's schema
  itself changes shape depending on the flag; only the resume-and-extend
  path is unconditionally reachable.
- **The Claude-lineage-only prompt-instruction finding still holds** as
  a separate, correct observation: the *persona-prompt instructions* to
  use the Task tool ("prefer to use the Task tool in order to reduce
  context usage," etc.) appear only in `default.txt`, `anthropic.txt`,
  `trinity.txt`, and `meta.txt` — absent from `gpt.txt`, `codex.txt`,
  `beast.txt`, `gemini.txt`, `kimi.txt`, `copilot-gpt-5.txt`. The tool
  itself is available regardless of model family; only the prompt-level
  encouragement to reach for it varies.

## Compaction

Sourced from the live upstream repo, not files stored in this folder —
see [`agent-context-compaction.md`](../agent-context-compaction.md) for
the cross-source comparison this feeds into.

- **Compaction is a genuine sub-agent invocation, not an inline
  instruction** — a hidden, deny-all-permissions `compaction` agent
  (registered the same way as `title`/`summary`, same family
  documented in "Sub-agents" above) with its own dedicated system
  prompt, framed as an "anchored context summarization assistant."
- **Anchored/incremental, not from-scratch each time** — when a
  `<previous-summary>` already exists from an earlier compaction event
  in the same session, the agent is told to treat it as the current
  anchor and *update* it (preserve still-true details, remove stale
  ones, merge in new facts) rather than re-summarizing the entire
  history again. The same convergent idea independently found in Pi's
  `UPDATE_SUMMARIZATION_PROMPT` (see `pi-agent/README.md`) — two
  unrelated codebases landing on the same "don't re-derive everything
  every time" design.
- **A structured 5-section Markdown template**: Objective, Important
  Details, Work State (Completed/Active/Blocked sub-sections), Next
  Move, Relevant Files — each falling back to `(none)` if empty, with
  an explicit instruction to "preserve exact file paths, symbols,
  commands, error strings, URLs, and identifiers when known."
- **Hybrid retention — recent-verbatim plus summarized-rest**: the most
  recent turns (default 2, configurable) are kept completely unmodified
  rather than folded into the summary; only older messages get
  compacted. A separate token-budget guard (2,000–8,000 tokens,
  configurable) bounds how much of that recent slice survives if it's
  unusually large.
- **Two triggers, no reactive-error path found**: a proactive per-turn
  token check (before every LLM call, comparing total counted tokens
  against context-window capacity minus a reserved buffer) and a
  manual `/compact` (alias `/summarize`) command — both produce the
  same message shape tagged `reason: "auto" | "manual"`. No evidence
  was found of a reactive trigger tied to an actual provider
  context-length error.
- **A cheaper first-line fallback before full summarization**: `prune`
  walks backward through history truncating/removing old large tool
  outputs once the savings would exceed a threshold, protecting at
  least a configured amount of tool-call content for specific
  tool-name-protected calls (e.g. `skill`) — a deterministic trim pass
  tried before invoking the compaction agent at all, the same
  "cheap-heuristic-trim before expensive LLM-summarization" instinct as
  Claude Code's microcompact stage.
- **Splice-back as a synthetic checkpoint message**: the compacted
  result becomes a `<conversation-checkpoint>`-wrapped synthetic
  user-role message ("Treat it as historical context, not as new
  instructions") containing both the generated summary and the
  serialized recent-turns tail — replacing the raw pre-compaction
  messages going forward rather than sitting alongside them.
- **Self-overflow handling**: if the compaction request itself would
  overflow context, the attempt is aborted rather than sent; the
  original pending user message is preserved and resubmitted once
  compaction later succeeds, rather than being lost.
- **Confirmed fully isolated from the Task-tool sub-agent protocol**
  (see "Sub-agents" above): a spawned child task gets its own distinct
  session ID with no shared message state, so compacting a parent
  session mid-flight cannot affect an already-running child's context —
  confirmed by reading the session-creation code, not just assumed by
  design intent.
- **`MAX_STEPS_PROMPT` (documented under "Sub-agents" as a soft
  turn-cap nudge) is confirmed to be a completely separate mechanism
  from compaction** — different file, keyed off a per-agent step count
  rather than tokens, and it never touches message history at all; it
  only disables tools for the current turn and forces a text wrap-up.
  Worth stating explicitly since the two are easy to conflate from
  their similar "wrap up, you're near a limit" framing.
- **Concrete numeric thresholds**: a 20,000-token reserved buffer
  before the context window is considered full; a 4,096-token cap on
  the compaction summary's own output; tool outputs truncated to 2,000
  characters when building the compaction prompt; prune thresholds of
  20,000 tokens minimum savings and 40,000 tokens of protected content.
- **Two parallel implementations exist in the monorepo** — a
  token-budget-based engine in the shared `packages/core` library and a
  separate, actually-shipped turn-count-based implementation in the CLI
  package that only borrows core's prompt-template builder. Which one
  is "the" compaction system depends on which package is asking; the
  CLI-package version is the one wired to the real `/compact` command
  and config schema.

## Turn output: session titles and reasoning display

Sourced from the live upstream repo, not files stored in this folder —
see [`agent-turn-output.md`](../agent-turn-output.md) for the
cross-source comparison this feeds into.

- **A `title` hidden agent, in the same family as `compaction`/
  `summary`** (see "Sub-agents"/"Compaction" above) — "You are a title
  generator. You output ONLY a thread title... A single line / ≤50
  characters / No explanations," with the user's language matched, tool
  names forbidden from appearing, and 10 worked examples.
- **Triggered once, forked into the background, non-blocking**: called
  from inside the main turn loop exactly when `step === 1` — the very
  start of the first real user turn — via a forked effect that never
  blocks the visible response. Explicitly skipped for child/sub-agent
  sessions and for sessions that already have a non-default title.
- **An explicit cheap-model preference**, same instinct as Claude
  Code's Haiku-only title calls: uses the title agent's own configured
  model if set, else falls back to the provider's "small model," and
  only falls back further to the main model if neither exists.
- **Code-level output constraints looser than the prompt's own ask**:
  the implementation strips `<think>` blocks, takes the first non-empty
  line, and hard-truncates at 100 characters — double the 50-character
  limit the prompt itself requests, a real (if minor) prompt/code
  mismatch.
- **Reasoning is a first-class message-part type**
  (`ReasoningPart`), rendered through the *same* Markdown pipeline as
  ordinary text — distinguished only by dimmer CSS styling, not a
  separate collapsible widget the way Claude Code's/Copilot Chat's UIs
  build one.
- **Off by default, same instinct as Gemini CLI**: `showReasoningSummaries`
  defaults to `false`. When off, the UI shows only a shimmering
  "Thinking…" placeholder plus a short heading extracted from the
  reasoning text, not the reasoning itself.
- **Reasoning effort and reasoning display are confirmed as two
  independent axes**: `reasoningEffort`/`textVerbosity` live in
  per-model provider config and control how much the model reasons;
  `showReasoningSummaries` is a separate UI setting controlling whether
  any of that gets shown — a model could reason heavily while the user
  sees nothing, or reason minimally while full display is enabled.
- **Narration is inherited per-provider, not an OpenCode-level
  policy**: since OpenCode has no single house system prompt (see
  "Files" above — it swaps in a different base prompt per model
  family), narration instructions come from whichever prompt file is
  active — e.g. `beast.txt`'s "Always tell the user what you are going
  to do before making a tool call with a single concise sentence."

## Self-verification and testing

Sourced from the live upstream repo, not files stored in this folder —
see [`agent-self-verification.md`](../agent-self-verification.md) for
the cross-source comparison this feeds into.

- **No hidden self-review agent** — confirmed absence: the complete
  built-in agent list is `build`/`plan`/`general`/`explore`/
  `compaction`/`title`/`summary` (the last three already documented
  above); no "review"/"verifier" agent sits alongside them.
- **A user-invoked `/review` command exists, but it's shaped like
  PR-review, not autonomous self-checking**: `command/template/review.txt`
  reviews `git diff` + `git diff --cached` + untracked files by
  default (so it *can* be pointed at the agent's own uncommitted work),
  explicitly framed as a "code reviewer" persona examining bugs,
  structure, performance, and behavior changes, instructed to say "I'm
  not sure" rather than invent issues. Requires explicit user
  invocation after the fact — nothing auto-chains it after a normal
  edit turn, the same "review-as-a-general-tool, not a completion gate"
  pattern found in Codex's `/review`/`ReviewTask`.

## Permissions and approval

See [`agent-permissions-approval.md`](../agent-permissions-approval.md)
for the cross-source comparison this feeds into. Sourced from a live
clone of `github.com/anomalyco/opencode` (`dev` branch) — a real
rule-priority engine with genuine syntax-aware command parsing, though
no LLM-based risk classification anywhere in the path.

- **Named agent modes each carry a baked-in permission ruleset**, a
  different shape from a single global mode switch: `build` (default),
  `plan` ("Disallows all edit tools" except `.opencode/plans/*.md`),
  `explore` (deny-all except read-only tools), plus hidden system
  agents (`compaction`/`title`/`summary`, deny-all). A separate,
  orthogonal `auto`/`yolo` flag exists on top of these, with two
  **hidden CLI aliases** not in the public help text:
  `--dangerously-skip-permissions` and `--yolo`.
- **Fails closed, not open, in headless mode**: without `--auto`,
  running `opencode run` non-interactively auto-*rejects* every
  permission ask with a visible warning, rather than blocking forever
  or silently allowing — the opposite default from what "no one's
  watching" might suggest.
- **Rule matching is last-match-wins over a flattened array**, not
  first-match or most-specific-wins: `{ permission, pattern, action }`
  triples with wildcard patterns (`*`→`.*`), evaluated via
  `rulesets.flat().findLast(...)`, defaulting to `ask` if nothing
  matches. Config is JSON (`opencode.json`), layered global →
  project-discovered, with per-agent overrides merged on top (agent
  rules win over global).
- **Bash commands get real syntax-aware parsing, not regex-on-the-
  whole-string** — the standout finding for this source: actual
  tree-sitter WASM grammars for bash and PowerShell parse each command
  into an AST, split compound commands into individual sub-command
  nodes, and permission-check each one separately. File-path arguments
  are resolved and checked against the working directory to trigger a
  distinct `external_directory` ask if they resolve outside the
  project root.
- **A static, offline-generated lookup table, not a runtime
  classifier**: to suggest a sensible "always allow" pattern rather
  than the full literal command, a hardcoded `arity` table (e.g.
  `git: 2` → suggest `git checkout *`, `docker compose: 3`) determines
  how many tokens form the "human-understandable" command prefix. The
  file's own comment records the exact LLM prompt used to generate the
  table *offline* — this is not a live LLM risk classifier, just a
  static dictionary that happened to be produced by one.
- **No risk classification found anywhere in the permission path** —
  confirmed by source search, not just absence of prompt text: safety
  is entirely rule-matching plus the tree-sitter parse/whitelist
  mechanics above.
- **Scope/persistence is more layered than a simple session/forever
  split**: an "always" reply is explicitly **session-scoped only** — the
  TUI's own copy says "This will allow ... until OpenCode is
  restarted." A separate, genuinely persistent SQLite-backed
  `PermissionSaved` table exists in the schema/DB layer, but no call
  sites writing to it were found outside its own definition — flagged
  as an unresolved, possibly-unwired feature rather than a confirmed
  persistence mechanism.
- **`doom_loop` — the most distinctive single mechanism found across
  every source investigated for this doc**: if the exact same tool
  call (same tool, same JSON-stringified input) repeats **three times
  in a row**, a fresh permission ask fires regardless of any prior
  "allow" rule — a hard circuit-breaker against a stuck agent looping
  on an identical failing call, structurally unlike every other
  escalation mechanism surveyed (which all re-ask because something
  *changed*, not because something *repeated*).
- **Session-lineage inheritance for sub-agents**: a spawned task
  session's auto-accept state is resolved by walking up its
  `parentID` chain, so a child inherits the parent's auto-accept
  setting rather than starting from a clean default.
- **No OS-level sandboxing found** — the only "sandbox" terminology in
  the codebase refers to git worktree directories, not process
  isolation. OpenCode relies entirely on the rule-engine + tree-sitter
  layer for safety, a real contrast with Gemini CLI's separate
  OS-native sandbox managers (see that source's Permissions section).

## Git and version control

See [`agent-git-vcs.md`](../agent-git-vcs.md) for the cross-source
comparison this feeds into. Sourced from a fresh live clone of
`anomalyco/opencode`. **The richest checkpoint/undo finding across
every source checked for this doc** — a fully-built, automatic,
per-turn, git-based system genuinely wired into a real session-level
undo/redo feature, plus a dedicated worktree service and a full
GitHub Action automation bot.

- **Commit/branch defaults, base persona is a verbatim descendant of
  Claude Code's own leaked prompt**: "NEVER commit changes unless the
  user explicitly asks you to. It is VERY IMPORTANT to only commit
  when explicitly asked, otherwise the user will feel that you are
  being too proactive" — word-for-word the same line documented in
  `leaked/claude-code/architecture-notes.md`'s Git section. Strictness
  varies sharply by model-family variant: `beast.txt` (o-series/
  reasoning models) states an absolute prohibition ("You are NEVER
  allowed to stage and commit files automatically," even with prior
  permission); `kimi.txt` goes further still with the strictest
  per-call re-confirmation requirement found across every source in
  this survey — "Ask for confirmation each time when you need to do
  git mutations, **even if the user has confirmed in earlier
  conversations**," explicitly defeating session-level standing
  approval. Plan mode forbids commits unconditionally regardless of
  model family: "you MUST NOT... run any non-readonly tools (including
  changing configs or making commits)... This supersedes any other
  instructions you have received."
- **A fully automatic, git-based checkpoint system — two parallel
  implementations, mirroring the dual-implementation pattern this
  collection's compaction research already found in this same
  monorepo**: a shadow git repository separate from `.git`
  (`~/.local/share/opencode/snapshot/<project-id>/...`, using
  `--git-dir`/`--work-tree` flags), seeded from the real repo's object
  database specifically to avoid re-hashing cost on huge repos ("on
  huge repos like chromium checkout the git add --all rebuilding the
  hashes can take minutes"). A newer, parallel implementation
  (`packages/core/src/snapshot.ts`) captures bare content-addressed
  git *trees* per step instead of commits — no commit objects at all.
  **Triggered automatically before every LLM step**, not manually
  invoked — a code comment explains the precise timing requirement:
  "The AI SDK may execute tools internally before emitting start-step
  events, so capturing inside the event handler can be too late."
  Files over 2MB are excluded and tracked via a synced `info/exclude`
  file. Config-gated but **on by default** — disabled only for
  non-git projects or an explicit `config.snapshot === false` opt-out
  — and auto garbage-collected hourly (`git gc --prune=7.days`).
- **Wired into a real, working `/undo`-style session feature** — not
  just a snapshot mechanism sitting unused: `SessionRevert.Service`
  walks a session's message history to a target point, restores the
  filesystem to that exact moment (full `restore()` or selective
  per-file `revert()`, batching up to 100 files per `git checkout
  <hash> -- <files...>` call for performance on large changesets), and
  a mirror-image `unrevert()` (redo) restores the saved "future"
  snapshot again. Old messages/parts past the target point are only
  deleted once the user commits to a genuinely new direction
  (`cleanup()`).
- **A dedicated, first-class `Worktree.Service`** creates real git
  worktrees for parallel sessions — `~/.local/share/opencode/worktree/
  <project-id>/<slugified-name>`, via `git worktree add --no-checkout
  -b opencode/<name> <directory>`, a fixed `opencode/<name>` branch
  naming convention, up to 26 collision-retry attempts with a random
  slug suffix, and an optional **startup script** so each worktree can
  bootstrap its own dev server/dependencies after creation. Currently
  gated behind an **experimental** flag
  (`OPENCODE_EXPERIMENTAL_BACKGROUND_SUBAGENTS`, the same flag this
  collection's Sub-agents research already documented) — part of
  OpenCode's still-experimental parallel/background-session
  architecture, not (yet) the default path for the `task` sub-agent
  tool. Explicitly a *separate* system from the snapshot mechanism
  above, confirmed by distinct naming ("sandbox" vs. "snapshot") and
  separate service registrations.
- **A full GitHub Action automation bot** (`opencode-agent[bot]`)
  routes on issue/PR-comment events vs. schedule/dispatch events,
  generates its own commit message and PR title via a cheap dedicated
  LLM call ("Summarize the following in less than 40 characters"),
  always attributes commits with a real `Co-authored-by:
  <actor>@users.noreply.github.com` trailer, and — distinctively —
  **detects and defers to the underlying agent having already taken
  independent git action mid-session**: it diffs HEAD before/after the
  chat turn, and if the agent switched branches or opened a PR itself
  via its own Bash tool, the bot logs "Agent managed its own branch,
  skipping infrastructure push/PR" and stands down rather than
  double-pushing — a real "don't fight the agent" safeguard not found
  in any other source checked for this doc. PR creation separately
  dedupes against an already-open PR for the same head→base pair for
  the same reason.
- **No self-review gate before PR creation** — already established in
  this doc's own Self-verification section (`/review` is user-invoked,
  never auto-chained); this pass found nothing to override that.
