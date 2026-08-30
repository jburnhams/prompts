# Claude Code (leaked extraction)

- **Type**: Coding agent · **Vendor**: Anthropic · **Status**: closed source
- **Mirror source**: https://github.com/x1xhlol/system-prompts-and-models-of-ai-tools/tree/main/Anthropic/Claude%20Code (2026-07-10)

Included for comparison purposes even though this collection is itself
built using Claude Code — a leaked extraction may differ from (and lag
behind) the real thing, so treat this as a data point, not a spec.

## Files

**Original extraction** (thin, dated):
- `Prompt.txt` — extracted system prompt.
- `Tools.json` — extracted tool/function definitions.
- [`architecture-notes.md`](./architecture-notes.md) — a synthesized
  summary of Claude Code's internal architecture (agentic loop,
  permission system, multi-agent "Team" coordination, plugins/skills,
  feature flags, MCP integration, memory) drawn from a separate, much
  larger alleged leak of the **full TypeScript source** (not just the
  prompt) at
  [`tanbiralam/claude-code`](https://github.com/tanbiralam/claude-code).
  Not stored here as source — see that file for provenance, caveats
  (unverified authenticity, confirmed stub code in security-sensitive
  areas), and methodology.

**A dramatically richer, later capture**, from a different, actively-
maintained aggregator (`asgeirtj/system_prompts_leaks`, retrieved
2026-07-11) — see "A richer capture" below for full provenance and
authenticity notes:
- `claude-code-2.1.172-opus-4.6.md` — the single most valuable file
  here: a versioned build (2.1.172), and — per direct comparison
  against this live session's own system prompt — a **near-verbatim
  match** to a real, current Claude Code harness prompt (same section
  order, same Git Safety Protocol bullets, same worked examples in the
  `Agent` tool description). Treat this one as strong corroborating
  evidence for everything else in this folder, not just "another
  capture."
- `claude-code-2.1.172-opus-4.8.md` — same build, a different,
  visibly newer and more condensed prompt rewrite (`# Harness` /
  `# Session-specific guidance` / `# Environment` / `# Context
  management` headers) not yet seen in the live session used for
  comparison — apparently a preview of an in-progress rewrite.
- `claude-code-2.1.172-fable-5.md` — ~98% identical to the opus-4.8
  capture (only model-identity strings differ), *except* for one
  additional autonomy-mode block (see the README's Sub-agents section
  below) — kept specifically for that diff, not for general
  redundancy.
- `claude-code-docs-assistant.md` — a different product: the docs-site
  "Ask AI" chat assistant, not the CLI's own system prompt. Kept for
  completeness, tangential to the rest of this collection.
- `claude-desktop-code.md` — a fourth, structurally distinct capture:
  "Claude Code (Desktop App - Code Mode)," captured 2026-02-21 on Opus
  4.6, from the same `asgeirtj/system_prompts_leaks` aggregator
  (retrieved 2026-07-12). Unlike the three versioned CLI captures above,
  this one's own text states it's "running within the Claude Agent SDK"
  — a real, self-attested SDK-vs-CLI distinction, not just a filename
  guess. See "The Desktop/SDK capture" in `architecture-notes.md` for
  the full diff against `claude-code-2.1.172-opus-4.8.md`: it turns out
  to *not* be a near-duplicate — genuinely older/more-verbose git and
  planning-tool instructions, a smaller and differently-shaped tool
  surface (still `Task` not `Agent`, no Cron/RemoteTrigger/
  ScheduleWakeup/Monitor/worktree tools), and roughly 300 lines of an
  entirely separate browser-automation safety persona (prompt-injection
  defense, a three-tier action-permission model, privacy/copyright
  rules) triggered by the presence of Chrome/Preview/Playwright MCP
  tools that the CLI captures never show.
- `deferred-tools.md` — the catalog of tools loaded on-demand rather
  than always-present (23 tools: `Cron{Create,Delete,List}`,
  `Enter/ExitPlanMode`, `Enter/ExitWorktree`, `Monitor`, `NotebookEdit`,
  `PushNotification`, `RemoteTrigger`, `ScheduleWakeup`, `SendMessage`,
  `Task{Create,Get,List,Output,Stop,Update}`, `Team{Create,Delete}`,
  `WebFetch`, `WebSearch`) — confirmed, tool-for-tool almost exactly,
  against this live session's own deferred-tool list.
- `bundled-skills/` — 18 of Claude Code's actual internal skill
  prompts (`init.md`, `compact.md`, `verify.md`, `security-review.md`,
  `keybindings-help.md`, `loop.md`, `code-review.md`, `schedule.md`,
  `batch.md`, `fewer-permission-prompts.md`, and others — see below).
  Two files (`claude-api.md`, `update-config.md`) are large reference
  docs (500KB+/140KB) matching skills already loaded in this session;
  truncated here to a representative excerpt rather than stored in
  full, since the bulk is reference material rather than
  agent-architecture content.

**Two files from the same batch were excluded as likely unreliable**:
`glob-tool.md` and `grep-tool.md` were written in a polished-tutorial
register (comparison tables, "Tips & gotchas" sections) that matches
no other genuine capture in this collection and doesn't match this
live session's own terse, four-bullet `Glob`/`Grep` tool descriptions
— probable fabrication or heavy embellishment rather than a real
extraction, so they weren't kept. `bundled-skills/review.md` was kept
but should be read with a caveat: it references `docs/agents/
issue-tracker.md` and a slash command `/setup-matt-pocock-skills`,
naming that suggests a third-party/community skill rather than an
Anthropic-authored one — the aggregator's "bundled skills" folder
appears to mix genuine built-ins with marketplace skills from the same
captured session.

## Tool surface

Per the extracted `Tools.json`: `Task` (sub-agent delegate), `Bash`,
`Glob`, `Grep`, `LS`, `ExitPlanMode`, `Read`, `Edit`, `MultiEdit`,
`Write`, `NotebookEdit`, `WebFetch`, `TodoWrite`, `WebSearch`,
`BashOutput`, `KillBash`.

- **Shell**: `Bash`, with `BashOutput`/`KillBash` as separate tools for
  polling a background command's output and terminating it — the same
  async-shell capability seen via a single flag in Gemini CLI
  (`SHELL_PARAM_IS_BACKGROUND`) or a dedicated status tool in Windsurf
  (`command_status`), here split into two distinct named tools.
- **Search**: `Glob` + `Grep` (no semantic/AST-aware search tool
  extracted here, unlike leaked Cursor's `codebase_search`).
- **Editing**: `Edit` (single old/new-string replace) and `MultiEdit`
  (batch variant) — same split as Copilot Chat's
  `ReplaceString`/`MultiReplaceString`.
- **Notebooks**: `NotebookEdit` — a dedicated tool, though (unlike
  Copilot Chat) no separate run-cell or get-summary tool in this
  extraction.
- **Browser/web**: `WebFetch` and `WebSearch` as two distinct tools
  (fetch a known URL vs. search generally) — no browser-automation tool.
- **Planning**: `TodoWrite`, `ExitPlanMode` (a dedicated mode-transition
  tool, same idea as Gemini CLI's `ENTER_PLAN_MODE_TOOL_NAME`/
  `EXIT_PLAN_MODE_TOOL_NAME`).
- **Multimodal**: not indicated by the tool names alone.
- **Sandbox/isolation**: not indicated.

As with the prompt text itself, treat this tool list as one dated
snapshot, not a guaranteed-current spec.

## Sub-agents

The full `Task` tool description in `Tools.json` is the most detailed
sub-agent specification captured anywhere in this collection — worth
reading as the reference case other sources' briefer mentions can be
compared against.

- **Typed agent registry, not a free-form delegate**: the description
  enumerates named agent types with their own tool scopes —
  `general-purpose` (`Tools: *`), `statusline-setup` (`Tools: Read,
  Edit`), `output-style-setup` (`Tools: Read, Write, Edit, Glob, LS,
  Grep`) — and the caller must pass a `subagent_type` parameter picking
  one. A sub-agent's tool access is narrower than the orchestrator's by
  design for anything other than `general-purpose`.
- **Explicit "when NOT to use" guidance**: reading a known file path,
  searching for an exact class name, or searching within 2-3 known
  files should go through `Read`/`Glob` directly instead — the Task
  tool is reserved for genuinely open-ended, multi-round work, framed
  as a speed/cost tradeoff, not a blanket "always delegate" rule.
- **Protocol is strictly one-shot, stateless, and opaque mid-flight**:
  "Each agent invocation is stateless. You will not be able to send
  additional messages to the agent, nor will the agent be able to
  communicate with you outside of its final report." The orchestrator
  never sees intermediate tool calls the sub-agent makes — only the
  single final message.
- **Result handling is the orchestrator's job, not automatic**: "The
  result returned by the agent is not visible to the user. To show the
  user the result, you should send a text message back to the user
  with a concise summary" — the sub-agent's report is folded into the
  orchestrator's own next turn as ordinary tool-result content, then
  the orchestrator decides what (if anything) to surface.
- **The calling prompt must front-load everything**: since there's no
  back-and-forth, "your prompt should contain a highly detailed task
  description... and you should specify exactly what information the
  agent should return." The sub-agent has no access to the user's
  original intent unless the orchestrator explicitly restates it,
  including whether it's expected to write code or just research.
- **Trust posture**: "The agent's outputs should generally be
  trusted" — stated as an explicit instruction, not left implicit.
- **Concurrency**: "Launch multiple agents concurrently whenever
  possible... use a single message with multiple tool uses" — the same
  batched-parallel-tool-call convention used for ordinary tools (see
  `coding-agent-approaches.md` §4), applied to sub-agent fan-out too.
- **No system prompt shown for the sub-agent side**: unlike Goose's
  `subagent_system.md` or Copilot Chat's `ExecutionSubagentPrompt`/
  `SearchSubagentPrompt`, this extraction only shows the *tool
  description* the orchestrator sees — what system prompt (if any) the
  spawned agent itself runs under isn't captured here. See
  `agent-subagent-architectures.md` for the cross-source comparison.
- **Correction from the richer, later capture**: `Task` has since been
  renamed `Agent` (all three versioned files use `Agent`, not `Task`)
  — the sub-agent contract itself (stateless, one-shot, "trust but
  verify," concurrent-batch launch) is unchanged in substance, just the
  tool name. The richer capture also adds a real named agent registry
  in place of the generic `general-purpose`/`statusline-setup`/
  `output-style-setup` trio above: `claude`, `claude-code-guide`,
  `Explore`, `general-purpose`, `Plan`, `statusline-setup` — see
  `architecture-notes.md`'s Multi-agent section for the full current
  list and everything else this capture adds (a real, tool-confirmed
  `TeamCreate`/`TeamDelete`/`SendMessage` schema promoting that
  section from "inferred from source" to "confirmed via captured
  prompt," plus an entirely new `Workflow` orchestration tool).
- **A session-mode-dependent prompt axis not previously documented**:
  diffing the `fable-5` capture against `opus-4.8` (same build,
  different model) turns up one extra block present only in `fable-5`:
  an "operating autonomously, the user is not watching in real time"
  section. This means the system prompt is parameterized by session
  mode (interactive vs. autonomous/background), not just by model
  identity and CLAUDE.md content — a third independently-gated
  prompt-assembly axis alongside the two `architecture-notes.md`
  already documents (CLAUDE.md loading, git-status injection).

## Bundled skills

18 real skill files captured in `bundled-skills/` (see Files above for
which two were excluded). One-line summary of each:

| Skill | Does |
|---|---|
| `init.md` / `init-new.md` | Generate/refresh `CLAUDE.md`; `init-new.md` is a richer, phased version with `AskUserQuestion`-driven scope selection (project vs. personal CLAUDE.md, skills, hooks) |
| `debug.md` | Enable/read Claude Code's own debug log, for troubleshooting the session itself |
| `loop.md` | Drives `/loop` autonomous recurring-check behavior via `ScheduleWakeup` |
| `artifact-design.md` | Design-system guidance for Artifacts |
| `simplify.md` | 4 parallel cleanup-angle agents (reuse/simplification/efficiency/altitude), then applies fixes — quality only, not bug-hunting |
| `fewer-permission-prompts.md` | Mines transcripts for read-only tool calls, proposes a settings.json allowlist |
| `batch.md` | Plan-mode-gated large-scale parallel refactor: decomposes into worktree-isolated background workers |
| `code-review.md` | 8-angle parallel finder + 1-vote recall-biased verifier, ≤10 findings, CLAUDE.md-conventions-aware |
| `compact.md` | The actual `/compact` summarization prompt — matches `architecture-notes.md`'s existing 9-section description exactly, plus one addition: an explicit instruction to preserve "security-relevant instructions or constraints" verbatim through compaction |
| `schedule.md` | Drives `RemoteTrigger` to manage claude.ai cloud "Routines" |
| `security-review.md` | The built-in `/security-review` — diff-scoped, confidence-scored, hard-exclusion-listed (DoS, secrets-on-disk, rate-limiting-by-design). A **second, functionally distinct mechanism** from the hook-based, automatic `skills/anthropic/security-guidance/` plugin already in this collection — this one is manually invoked and multi-agent (find → parallel false-positive filter), not hook-triggered; document both, don't conflate them |
| `verify.md` / `run.md` | A much more opinionated self-verification doctrine than `architecture-notes.md`'s brief existing section — "verification is runtime observation... don't run tests, don't typecheck" — plus app-launching patterns by project type |
| `keybindings-help.md` | A full keybinding customization system (`~/.claude/keybindings.json`, contexts, chords, `/doctor` validation) — a genuinely new UI mechanism with zero prior overlap in this collection |
| `review.md` | Two-axis (Standards/Spec) PR review via parallel sub-agents — possibly third-party, see the authenticity caveat above |
| `claude-api.md` (truncated here) | Reference skill for building Claude-API apps |
| `update-config.md` (truncated here) | Settings.json configuration skill |

## Memory, learnings, and retrospectives

See [`agent-memory-learning.md`](../../agent-memory-learning.md) for the
cross-source comparison this feeds into. Claude Code is the clearest
example of the two-track model: **human-written instruction files and a
machine-written store, side by side, with different rules**. The
instruction-file half is visible in the leaked prompts and in
`architecture-notes.md`; the auto-memory half is documented by the
vendor and corroborated by leaked internals (`memdir/` — "persisted
cross-session memory" — and a `services/` area that includes "memory
extraction").

- **Two mechanisms, both loaded every session.** `CLAUDE.md` files are
  written by the user; auto memory is written by Claude. The vendor's
  own framing of the split: CLAUDE.md holds "instructions and rules"
  scoped to project/user/org, auto memory holds "learnings and patterns"
  scoped per repository and shared across worktrees. Both are context,
  not enforcement — "To block an action regardless of what Claude
  decides, use a PreToolUse hook instead."
- **Four human-written scopes plus a rules directory.** Managed policy
  (`/Library/Application Support/ClaudeCode/CLAUDE.md`,
  `/etc/claude-code/CLAUDE.md`, or the `claudeMd` key in
  managed-settings.json — un-excludable), user (`~/.claude/CLAUDE.md`),
  project (`./CLAUDE.md` or `./.claude/CLAUDE.md`), local
  (`./CLAUDE.local.md`), all concatenated root-downward rather than
  overriding; plus `.claude/rules/*.md` with optional `paths:`
  frontmatter globs so a rule loads only when Claude touches a matching
  file. `@path` imports expand at launch (max depth 4, code spans
  skipped, external imports gated behind a one-time approval dialog),
  and `claudeMdExcludes` skips other teams' files in a monorepo.
  `architecture-notes.md` confirms the loader is independently gated
  from git-status injection (`getUserContext()` vs `getSystemContext()`,
  with `CLAUDE_CODE_DISABLE_CLAUDE_MDS`).
- **Auto memory is an index-plus-topic-files store with an enforced
  budget** — the same shape Codex and Gemini CLI arrived at
  independently. `~/.claude/projects/<project>/memory/` holds
  `MEMORY.md` plus arbitrary topic files; only the first **200 lines or
  25KB** of the index is loaded at session start, topic files are read
  on demand. The enforcement is the distinctive part: after a write,
  the harness measures the file, nudges the model to shorten it if it's
  near the limit ("keep one line per entry, move detail into topic
  files, and merge or drop stale entries"), and returns an outright
  error if it's over, "because everything past the limit is dropped on
  the next load." Frontmatter and block-level HTML comments are stripped
  before measuring and before loading.
- **Provenance stamping**: when Claude writes a memory file that already
  has YAML frontmatter, the harness records a `modified` ISO-8601
  timestamp, so staleness is visible both to the user and to Claude on
  the next read. It never adds frontmatter to a file that has none.
- **Governance is audit-after, not approve-before**: writes happen
  during the session (surfaced as "Saved 2 memories" / "Recalled 2
  memories"), and the controls are `/memory` (browse/edit/toggle),
  `autoMemoryEnabled` per scope, `autoMemoryDirectory` to relocate the
  store, and `CLAUDE_CODE_DISABLE_AUTO_MEMORY=1`. Contrast Gemini CLI's
  approval inbox for the same class of writes.
- **Sub-agents get their own store**: the parent conversation's auto
  memory is *not* inherited by sub-agents (except a `fork`, which
  inherits the whole conversation); a sub-agent's `memory` field opts it
  into a separate directory of its own — the only per-sub-agent memory
  scoping found in this collection.
- **Memory shows up in unrelated subsystems**, confirming it's a
  first-class part of the harness rather than a bolt-on: `EnterWorktree`
  is gated on "the user directly, or... project instructions (CLAUDE.md
  / memory)"; `ExitWorktree` "clears CWD-dependent caches (system prompt
  sections, **memory files**, plans directory)"; the leaked
  `yoloClassifier.ts` permission gate is built "from recent conversation
  context plus the user's own configured allow/deny rules and
  CLAUDE.md"; and the compaction pipeline has "a sixth, experimental
  path: session-memory compaction reuses pre-extracted 'session memory'
  content instead of an LLM call when available."
- **Bootstrapping and interop**: `/init` generates a starting CLAUDE.md
  and, per the vendor docs, reads `.cursor/rules/`, `.cursorrules`, and
  `.github/copilot-instructions.md` when doing so (and, under
  `CLAUDE_CODE_NEW_INIT=1`, also `AGENTS.md`, `.devin/rules/`,
  `.windsurf/rules/`, `.clinerules`) — a cross-vendor rules-file
  importer, and the only one in this collection. Claude Code does not
  read `AGENTS.md` natively; the documented workaround is a `@AGENTS.md`
  import or a symlink.
- **No retrospective stage.** Nothing in the captured prompts or the
  documented behavior triages a finished session's outcome the way
  Codex's Phase 1 does; auto memory accumulates observations during the
  session rather than distilling them from a completed transcript
  afterwards.

## Context-file loading: the mechanics (`CLAUDE.md`)

The [memory section above](#memory-learnings-and-retrospectives) covers *what* the tiers
are and who writes them. This section covers the loader itself, read
2026-08-30 from the leaked source at `6f6f12b` (commit dated 2026-05-07)
— `src/utils/claudemd.ts` (1479 lines), `src/context.ts`,
`src/utils/api.ts`, `src/utils/messages.ts`, `src/utils/attachments.ts`.
Treat specifics as of that snapshot; the leaked-source caveats at the top
of this README apply.

- **Discovery order is fixed and additive, not first-match.**
  `getMemoryFiles()` pushes, in order: Managed `CLAUDE.md` → managed
  `.claude/rules/*.md` → user `~/.claude/CLAUDE.md` → user
  `~/.claude/rules/*.md` → then, walking **root-downward to cwd**, per
  directory: `CLAUDE.md`, `.claude/CLAUDE.md`, `.claude/rules/*.md`
  (Project) and `CLAUDE.local.md` (Local) → optional `--add-dir`
  directories (behind `CLAUDE_CODE_ADDITIONAL_DIRECTORIES_CLAUDE_MD`,
  default off) → the auto-memory `MEMORY.md` entrypoint → team memory.
  Every one that exists is loaded; nothing shadows anything.
- **A worktree-specific de-duplication rule.** When cwd is a git worktree
  nested inside its own main repo (`claude -w` puts them under
  `.claude/worktrees/`), the upward walk crosses both the worktree root and
  the main repo root, and would load the same checked-in `CLAUDE.md` twice.
  `isNestedWorktree` detects `findGitRoot != findCanonicalGitRoot` and skips
  **Project-type** files from directories inside the canonical root but
  outside the worktree — while still loading `CLAUDE.local.md`, because it
  is gitignored and therefore only exists in the main repo. Cited to
  `anthropics/claude-code#29599`.
- **Imports are extracted from a Markdown token stream, not a regex over
  raw text.** `parseMemoryFileContent` lexes once with `marked`
  (`gfm: false` — required so `~/path` doesn't tokenize as strikethrough)
  and shares the tokens between comment-stripping and import extraction.
  `extractIncludePathsFromTokens` skips `code` and `codespan` tokens
  outright, and for `html` tokens strips the comment spans and scans only
  the residue (so `<!-- note --> @./file.md` still imports). The scan regex
  is `/(?:^|\s)@((?:[^\s\\]|\\ )+)/g` — escaped spaces (`\ `) are supported
  and unescaped, and a `#fragment` suffix is trimmed off the path.
- **Import guards**: `MAX_INCLUDE_DEPTH = 5`; a `processedPaths` set
  normalized for Windows drive-letter casing, seeded with **both** the
  symlink path and its realpath; a `TEXT_FILE_EXTENSIONS` allowlist (~30
  extensions) so a `@./logo.png` cannot pull binary bytes into context; and
  an "external" check — an import resolving outside the original cwd is
  dropped unless `hasClaudeMdExternalIncludesApproved` is set, which is a
  **one-time user approval dialog** (`ClaudeMdExternalIncludesDialog.tsx`).
  User-tier files are exempt and always allowed external imports.
  Parent-before-children ordering: the importing file is pushed first, then
  its imports.
- **Content is transformed before it is measured or shown.** Frontmatter is
  stripped; block-level HTML comments are stripped via the lexer (inline
  comments and comments inside code spans are preserved, and an *unclosed*
  `<!--` is deliberately left in place "so a typo doesn't silently swallow
  the rest of the file"); `MEMORY.md` entrypoints are truncated to line and
  byte caps. When any of that fires, `contentDiffersFromDisk` is set and the
  untouched bytes are kept in `rawContent` — so the `readFileState` cache
  entry is marked `isPartialView` and `Edit`/`Write` still demand a real
  `Read` first. This is the only loader in the collection that tracks the
  divergence between what the model was shown and what is on disk.
- **`.claude/rules/*.md` are conditional on `paths:` frontmatter.** Rules
  *without* `paths` load eagerly with everything else. Rules *with* `paths`
  load only when a tool touches a matching file:
  `processConditionedMdRules` resolves the target relative to the parent of
  `.claude` (for Project rules) or the original cwd (Managed/User), rejects
  anything that escapes the base (`..`, absolute, cross-drive), and matches
  with the `ignore` library. `paths: **` is normalized away to "no globs"
  (i.e. unconditional), and a trailing `/**` is stripped because `ignore`
  treats a bare path as matching the subtree too.
- **Exclusion is a glob setting with symlink-aware pattern expansion.**
  `claudeMdExcludes` (picomatch, `dot: true`) applies to User/Project/Local
  only — **Managed, AutoMem and TeamMem can never be excluded**.
  `resolveExcludePatterns` additionally realpath-resolves the static prefix
  of each absolute pattern and adds the resolved form, so a user-written
  `/tmp/project/CLAUDE.md` still matches when the process sees
  `/private/tmp/...` on macOS.
- **The eager envelope has no delimiters at all.** `getClaudeMds()` emits
  `MEMORY_INSTRUCTION_PROMPT` once —

  > Codebase and user instructions are shown below. Be sure to adhere to
  > these instructions. IMPORTANT: These instructions OVERRIDE any default
  > behavior and you MUST follow them exactly as written.

  — then, per file, `Contents of <absolute path> <description>:\n\n<trimmed
  content>`, joined by blank lines. The description is the tier
  (`" (project instructions, checked into the codebase)"`, `" (user's
  private project instructions, not checked in)"`, `" (user's private
  global instructions for all projects)"`, `" (user's auto-memory, persists
  across conversations)"`). **The only tier that gets a machine-readable
  tag is team memory** — `<team-memory-content source="shared">` — i.e. the
  tag tracks provenance/trust (content synced from outside this repo), not
  document structure. Nothing is escaped or fenced.
- **Delivery is a synthetic first user message, not the system prompt.**
  `getUserContext()` returns `{ claudeMd, currentDate }`; `prependUserContext`
  (`src/utils/api.ts:449`) turns that map into one `isMeta` user message:

  ```
  <system-reminder>
  As you answer the user's questions, you can use the following context:
  # claudeMd
  <the getClaudeMds output>

  # currentDate
  ...

        IMPORTANT: this context may or may not be relevant to your tasks. You should not respond to this context unless it is highly relevant to your task.
  </system-reminder>
  ```

  Note the collision: the **outer** wrapper hedges ("may or may not be
  relevant"), while the **inner** `MEMORY_INSTRUCTION_PROMPT` it wraps says
  the same bytes "OVERRIDE any default behavior and you MUST follow them
  exactly as written". Two opposite framings of one payload, nested, in a
  single message.
- **JIT nested loading rides the attachment system.** `nested_memory`
  attachments are produced when a tool touches a path below cwd
  (`getMemoryFilesForNestedDirectory`), converted by
  `memoryFilesToAttachments` (skipping anything in `loadedNestedMemoryPaths`
  or already in `readFileState`), and rendered as
  `wrapMessagesInSystemReminder([...])` with the body
  `Contents of <path>:\n\n<content>` — the tier description is **dropped**
  on this path, so a JIT-loaded file arrives less labelled than an eager one.
- **Kill switches**: `CLAUDE_CODE_DISABLE_CLAUDE_MDS` is hard-off always;
  `--bare` skips auto-discovery but still honours explicit `--add-dir`
  ("skip what I didn't ask for", not "ignore what I asked for"); the
  `settingSources` mechanism gates the User/Project/Local tiers
  independently; and an `InstructionsLoaded` hook fires per file with its
  type, globs, parent and load reason (`session_start` / `include` /
  conditional) — audit-only, fire-and-forget, and deliberately **not**
  fired for AutoMem/TeamMem, which are "a separate memory system, not
  'instructions'".
