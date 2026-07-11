# Claude Code: internal architecture notes (from a full-source leak)

This is a different, much larger source than the `Prompt.txt`/`Tools.json`
extraction documented in this folder's main [`README.md`](./README.md).
Those are prompt-only extractions (the kind pulled via a debug flag or a
prompt-injection trick). What's summarized here comes from
[`tanbiralam/claude-code`](https://github.com/tanbiralam/claude-code), a
public repo claiming to hold the **full, unobfuscated TypeScript source**
of Claude Code — allegedly leaked on 2026-03-31 via an exposed source
map file in the npm registry, discovered by Chaofan Shou and posted
publicly. Its own README puts it at ~1,900 files and ~512,000 lines,
built on Bun + React/Ink.

**This document is a synthesized architecture summary, not a copy of
the source.** No source files from that repo are stored in this
repository. Everything below is written in my own words from browsing
the repo (via `github.com` tree/blob views, since it couldn't be cloned
in this environment) and should be read as secondary analysis, not a
spec — treat it the same way the rest of this folder treats the
prompt-only extraction: a data point, not ground truth.

## Caveats before anything else

- **Authenticity is unverified.** A repo claiming to be a specific
  commercial product's full leaked source is easier to fabricate
  convincingly than a short prompt-text extraction, and there's no
  independent way to confirm this one is genuine from the outside.
- **A meaningful fraction of the repo is stub code, concentrated in the
  most security-sensitive areas.** Confirmed stubs (files whose entire
  body is a placeholder, e.g. a comment reading roughly "Stub: not
  included in leaked source" or "ANT-ONLY," with disabled/no-op logic)
  include the peer-agent-listing tool, the bash-command security
  classifier, and the SSH session manager. File *names* and directory
  *structure* may be complete while the *logic* inside some files isn't
  — so treat the module map below as showing intended architecture, not
  proof that every described behavior is actually implemented in what's
  public.
- **This summary itself is one level removed from the source**: it was
  produced by browsing GitHub's rendered file views through an
  AI-summarization step (no local clone, no full-text grep across the
  repo), so it should be read as "plausible structural description,"
  not "verified line-by-line audit." Confirmed-by-direct-reading vs.
  inferred-from-file-naming is noted inline where it matters.
- **A materially stronger authenticity signal arrived later**: a
  separate, much richer prompt-text capture (`claude-code-2.1.172-
  opus-4.6.md`, from a different leak aggregator — see the folder's
  README for full provenance) turned out to be a near-verbatim match
  to this live session's own actual system prompt: same section
  headers, same "Committing changes with git" numbered steps, same
  Git Safety Protocol bullets, the identical `Agent({description:
  "Branch ship-readiness audit", ...})` worked example. That's
  stronger corroboration than anything available when this document
  was first written, and it's cited inline below wherever it upgrades
  a previously source-inferred claim to a directly-confirmed one.

## Module map

`src/` is organized as roughly three dozen top-level areas: `tools/`
(~58 individual tool implementations, each its own directory),
`commands/` (~85 slash-command implementations), `services/` (business
logic — MCP, LSP, OAuth, analytics, memory extraction, plugin
management), `bridge/` (~35 files, IDE integration), `coordinator/`
(multi-agent "Team" supervisor logic), `state/` (in-memory session
state), `memdir/` (persisted cross-session memory), `skills/`,
`plugins/`, `permissions`-related code under `utils/permissions/` (24
files), plus `vim/`, `voice/`, `ssh/` as smaller feature-specific areas,
and top-level orchestration files (`QueryEngine.ts`, `query.ts`,
`Tool.ts`, `tools.ts`, `Task.ts`, `context.ts`).

## The agentic loop

Two files split the responsibility that other sources in this
collection's `agent-tool-surfaces.md`/`agent-subagent-architectures.md`
docs usually describe as one undifferentiated "the agent loop":

- **`QueryEngine.ts`** owns the *conversation*: one instance per
  conversation, persisting message history, file-state cache, usage
  tracking, and permission-denial history across multiple
  `submitMessage()` calls. It normalizes streamed API events
  (`message_start`/content-block deltas/`message_stop`) into SDK-facing
  message types, writes to a persistent transcript (fire-and-forget for
  still-mutating assistant messages, awaited for user/system messages to
  keep them consistent), and handles compaction-boundary bookkeeping —
  when a "snip" compaction occurs, it replays the message store to
  strip stale markers rather than leaving them to leak memory across a
  long session.
- **`query.ts`** owns the *turn*: assembles the system + user/system
  context each call, drives compaction strategy selection (autocompact,
  reactive compact on a "prompt too long" error, "snip," or full context
  collapse), executes tools — including letting a tool start running
  while the model is *still streaming* the rest of its response — and
  has narrow recovery paths for specific failure modes (image/media
  errors, max-output-token truncation retried).

This two-layer split (conversation-level state vs. turn-level
execution) doesn't have a clean one-to-one analog elsewhere in this
collection's sources — most of what's captured for other agents is
prompt text plus a flat tool list, not the surrounding session-engine
architecture, since none of the other sources have a full-source leak
to draw this distinction from.

## Context compaction — a layered pipeline, not one mechanism

The richest compaction architecture found anywhere in this collection
(see [`agent-context-compaction.md`](../../agent-context-compaction.md)
for the cross-source comparison this feeds into). Rather than a single
"summarize when full" strategy, `query.ts` runs **several distinct
mechanisms as a sequential pipeline on every turn**, cheapest first,
plus a genuinely separate reactive fallback for actual API errors.
Two of the pipeline's defining implementation files
(`snipCompact.ts`, `snipProjection.ts`) and the reactive-compact
implementation (`reactiveCompact.ts`) are absent from this leak
(referenced by call sites but 404 on fetch, with `SnipTool.ts` an
explicit stub reading "not included in the leaked source") — so the
proactive pipeline's outer structure is confirmed by reading real code,
but the exact snip-selection logic and reactive-compact internals are
inferred from caller comments only.

- **The pipeline, in order**: **snip** (a model-nudged, boundary-based
  tool for trimming a specific region of context, not the whole
  conversation — a periodic "context-efficiency nudge" prompts the
  model to use it proactively) → **microcompact** (no LLM call at all —
  heuristically strips/replaces old tool outputs with placeholders,
  either via Anthropic's cache-editing API or direct replacement when
  the prompt cache has likely already expired) → **context collapse**
  (runs deliberately before autocompact, so that if it alone gets under
  threshold, autocompact becomes a no-op) → **autocompact** (the real
  LLM-summarization pass, gated by a token threshold). A comment in the
  source states explicitly that snip and microcompact "are not mutually
  exclusive" — this is a fallback *chain* of increasingly expensive
  interventions, not a menu of alternative strategies.
- **A genuinely separate reactive path**: triggered only by the literal
  API error string `"Prompt is too long"`, independent of the proactive
  pipeline — tries a cheap "collapse drain" first, then falls back to
  full reactive compaction. This is the one place Claude Code's
  compaction is reactive rather than proactive.
- **A sixth, experimental path**: session-memory compaction reuses
  pre-extracted "session memory" content instead of an LLM call when
  available, falling back to the normal pipeline otherwise.
- **The compaction prompt itself is structured, not free text**: a
  9-section template (Primary Request and Intent, Key Technical
  Concepts, Files and Code Sections, Errors and fixes, Problem Solving,
  All user messages, Pending Tasks, Current Work, Optional Next Step),
  wrapped in a scratchpad `<analysis>` tag that gets stripped after
  generation ("a drafting scratchpad that improves summary quality but
  has no informational value once the summary is written"). Three
  variants exist — full-history, recent-only, and "up to a pivot
  point" — confirming a directional partial-summarization mode
  distinct from whole-history compaction. Tool use during the
  compaction call itself is explicitly forbidden ("Tool calls will be
  REJECTED and will waste your only turn").
- **Recovery pointer to the full transcript**: the post-compaction
  summary message includes a literal instruction — "If you need
  specific details from before compaction... read the full transcript
  at: `${transcriptPath}`" — the same transcript-lookup-hint pattern
  independently found in this collection's Copilot Chat material (see
  `copilot-chat/README.md`), except here confirmed to also carry a
  distinct "you were already working autonomously before compaction"
  framing when the compaction happens mid-unattended-run.
- **Compaction and prompt caching**: compaction is treated as a
  deliberate, accepted cache-reset point (`clearSystemPromptSections()`
  runs on both `/compact` and `/clear`) rather than something the
  system tries to hide from the cache — but microcompact's cache-editing
  path is itself a cache-*preservation* optimization (deletes stale
  tool-result cache entries without invalidating the surrounding cached
  prefix), and full compaction can optionally fork off the main
  conversation's already-cached prefix instead of a cold cache-miss
  summarization call.
- **Concrete numeric thresholds** (approximate, from an automated
  research pass, not hand-verified against source): autocompact
  triggers at the effective context window minus a **13,000-token
  buffer** (overridable via an env var); a **20,000-token** warning
  threshold before the hard limit; up to **20,000 tokens** reserved for
  the compaction summary itself; a **50,000-token** post-compact budget
  for re-attached files/skills (5,000 per file, 5,000 per skill, capped
  at 25,000 total across skills); and a circuit breaker that gives up
  after **3 consecutive autocompact failures** rather than retrying
  forever.
- **User-visible commands are structurally different, not just two
  names for the same thing**: `/compact` is summarize-and-continue
  (accepts custom free-text instructions, tries session-memory →
  reactive → legacy compaction in order); `/clear` is a hard reset that
  wipes rather than summarizes, sharing only the cache-cleanup step
  with `/compact`.

## Turn output: session titles and reasoning display

See [`agent-turn-output.md`](../../agent-turn-output.md) for the
cross-source comparison this feeds into.

**Three separate title generators exist, not one** — all calling Haiku
explicitly (a distinct cheap/fast model, never the main Sonnet/Opus
agent loop), all with narrow, non-overlapping triggers rather than
running for every session:

- `src/utils/sessionTitle.ts`'s `generateSessionTitle()` — a
  3-7-word sentence-case title, JSON-schema-constrained output
  (`{"title": "..."}`), with good/bad worked examples embedded in the
  prompt. Triggered from `src/hooks/useRemoteSession.ts` exactly once,
  after the first user message, but **only for remote/background
  sessions started without an initial prompt** — a comment explains why:
  "gives the session a meaningful title on claude.ai instead of
  'Background task'." Ordinary interactive terminal sessions with an
  initial prompt don't appear to get this treatment at all.
- `teleport.tsx`'s `generateTitleAndBranch` — a 6-word title *plus* a
  git branch name in one call, for the remote/CCR teleport flow.
- `rename/generateSessionName.ts`'s `generateSessionName` — a
  kebab-case 2-4-word name, used only by the explicit `/rename` command.

All three share an `extractConversationText` helper that tail-slices to
the last 1,000 characters of the conversation rather than reading the
full history — titling is deliberately cheap even before considering
the small-model choice.

**Reasoning display is raw-but-collapsible by default, not
summarized** — a real design choice distinct from every other source
surveyed defaulting to hidden-unless-opted-in (Codex's interactive
pane, Gemini CLI, OpenCode):

- `AssistantThinkingMessage.tsx` shows a collapsed one-line "∴
  Thinking" hint by default; expanding (via a verbose/transcript mode)
  reveals the model's *actual, unmodified* thinking text rendered as
  markdown — nothing passes through a summarization step the way
  visible chat responses might.
- A dedicated on/off setting (`ThinkingToggle.tsx`, bound to `alt+t`)
  controls whether extended thinking is requested from the API at all,
  with an explicit latency/quality tradeoff warning if toggled
  mid-conversation.
- A magic keyword, literally the word **"ultrathink"**, typed anywhere
  in a user message, is detected (`src/utils/thinking.ts`,
  `src/utils/ultraplan/keyword.ts`) and boosts the thinking budget for
  that turn — with its own rainbow-highlighted UI treatment as you type
  it. (This collection's own conversational surface uses the same
  keyword convention — see the system-reminder in the turn that
  triggered this very research pass.)
- `redacted_thinking` blocks (Anthropic's API-level safety redaction of
  certain thinking content) render only as an opaque "✻ Thinking…"
  placeholder — genuinely hidden by the model provider, not a Claude
  Code display choice.
- **Transcript noise control**: only the *most recent* thinking block
  stays expanded as a long session scrolls on; older ones automatically
  collapse away, independent of the verbose/transcript-mode toggle —
  a scaffold-level UI decision layered on top of the raw-display default.

**Narration is a separate mechanism entirely**: ordinary visible
assistant prose (what most sources' "communication style"/terseness
rules govern — see `coding-agent-approaches.md`) is governed by the
system prompt's conciseness rules, not by anything to do with the
native thinking-block machinery above.

## Tool definition and dispatch

`Tool.ts` defines a generic `Tool<Input, Output>` contract: identity,
a Zod input schema, a `call()` method taking a `ToolUseContext` and a
`canUseTool` permission-check callback, a `checkPermissions()` method
tied into the permission system below, and capability flags
(`isConcurrencySafe()`, `isReadOnly()`, `isDestructive()`,
`isSearchOrReadCommand()`) that presumably drive some of the
parallel-tool-call and confirmation behavior documented from the
prompt-text side in `coding-agent-approaches.md` §4.

`tools.ts` is the registry. Its own in-repo framing (per the research
pass) describes `getAllBaseTools()` as "the source of truth for ALL
tools." Filtering happens in layers on top of that base list:
per-mode restriction (a stripped-down "simple mode" exposes only
Bash/FileRead/FileEdit; worktree mode adds `EnterWorktreeTool`/
`ExitWorktreeTool`; coordinator mode swaps in a different allowed-tool
set entirely — see below), permission-deny rules that can remove a tool
from the model's visible list entirely rather than just blocking a call
to it, and a final merge step that combines built-ins with MCP-derived
tools while preserving a stable order — reordering the tool list between
turns would invalidate Anthropic's prompt cache, so ordering is treated
as a correctness concern, not cosmetic.

**A deferred/on-demand tool-loading layer, confirmed directly rather
than inferred from source** — this section previously had nothing to
say about tool *deferral* specifically; the richer capture's
`deferred-tools.md` supplies it, and it matches this live session's
own deferred-tool list almost tool-for-tool. A consistently small core
set (`Agent`, `Bash`, `Edit`, `Read`, `Skill`, `Write`, plus
`AskUserQuestion` and `Workflow` in the three versioned captures) is
always present; a larger catalog — confirmed at 23 tools in the
captured snapshot: `Cron{Create,Delete,List}`, `Enter/ExitPlanMode`,
`Enter/ExitWorktree`, `Monitor`, `NotebookEdit`, `PushNotification`,
`RemoteTrigger`, `ScheduleWakeup`, `SendMessage`,
`Task{Create,Get,List,Output,Stop,Update}`, `Team{Create,Delete}`,
`WebFetch`, `WebSearch` — is named-only until a lookup call fetches its
full schema. This is presumably the same context-budget-preservation
motivation as the prompt-caching-aware section design described below,
applied to the tool list instead of the prompt text.

**Several tool families named in `deferred-tools.md` were entirely
unknown to this document before**, worth cataloguing as their own
finding rather than folding silently into the tool-dispatch mechanics
above:

- **`Cron{Create,Delete,List}`** — a persistent/session scheduling
  system distinct from anything else described in this document.
  `CronCreate` schedules a prompt for future enqueueing (5-field cron,
  local timezone, `recurring` default true vs. one-shot) with a
  `durable` flag choosing between `.claude/scheduled_tasks.json`
  (survives restarts) and in-memory-only (dies with the session), plus
  explicit anti-thundering-herd guidance ("Avoid the :00 and :30 minute
  marks... requests from across the planet land on the API at the same
  instant"). Jobs only fire while the REPL is idle, and recurring jobs
  auto-expire after 7 days.
- **`RemoteTrigger`** — calls claude.ai's own remote-trigger API
  (`/v1/code/triggers`, OAuth handled in-process) to list/get/create/
  update/run what the product surfaces as "Routines" — a cloud/
  server-side scheduling surface distinct from the local `Cron*`
  family, driven by the `schedule.md` bundled skill (see the folder's
  README).
- **`ScheduleWakeup`** — the self-pacing wakeup scheduler behind
  `/loop` dynamic mode (see Self-verification below for the skill that
  drives it), with an explicit, quantified prompt-cache heuristic
  baked into the tool description: "The Anthropic prompt cache has a
  5-minute TTL. Sleeping past 300 seconds means the next wake-up reads
  your full conversation context uncached... Don't pick 300s. It's the
  worst-of-both." A concrete numeric data point for the same
  cache-preservation instinct this document documents elsewhere for
  compaction and prompt-section memoization.
- **`Monitor`** — a background event-stream watcher, distinct from
  Bash's own `run_in_background`: picks a notification cardinality
  (one / one-per-occurrence / indefinite), documents pipe-buffering
  gotchas (`grep --line-buffered`, `head` never flushing), states a
  "coverage — silence is not success" doctrine (a monitor that only
  greps for a success marker stays silent on crash/hang too), and
  auto-shuts-down noisy monitors.
- **`PushNotification`** — sends a desktop/phone notification,
  explicitly framed around attention cost: "err toward not sending
  one... Notify when there's a real chance they've walked away."
- **`Task{Create,Get,List,Output,Stop,Update}`** — a structured,
  ID-based task system with `blocks`/`blockedBy` dependency edges and
  an `owner` field (an agent name), distinct from both `TodoWrite`
  (this document's earlier tool list) and the source-inferred "Team"
  task-list architecture below — `TaskList`'s own documentation states
  the relationship directly: **"Team = TaskList (1:1)."** `TaskOutput`
  is marked deprecated in favor of `<task-notification>` events plus
  direct file reads.
- **`Workflow`** — the largest single new finding: a deterministic,
  JS-scripted multi-agent orchestration tool, gated behind explicit
  user opt-in (an "ultracode" keyword or explicit request — "Workflows
  can spawn dozens of agents and consume a large amount of tokens; the
  user must request that scale, not have it inferred"). `agent()`/
  `parallel()`/`pipeline()`/`phase()`/`log()`/`workflow()` primitives;
  `pipeline()` is documented as the default over `parallel()` because
  pipeline has no cross-item barrier. Concurrency capped at
  `min(16, cpu cores - 2)` per workflow, 1000-agent lifetime cap,
  4096-item batch cap. **Resumable**: `resumeFromRunId` replays cached
  `agent()` results for an unchanged script prefix ("Same script + same
  args → 100% cache hit"), which is specifically why `Date.now()`/
  `Math.random()` are banned inside workflow scripts — either would
  break the cache-hit guarantee. A `budget` object enforces a hard
  token ceiling tied to a user's stated budget, not an advisory one.
  Extensive prose on "quality patterns" (adversarial verify, judge
  panel, loop-until-dry, completeness critic) reads as the concrete,
  currently-shipped, user-facing productization of the orchestration
  architecture the Multi-agent "Team" section below previously had to
  infer from source-file names alone.
- **`AskUserQuestion`** and **`EnterPlanMode`** — both real, richly
  specified tools this document didn't previously name at all (the
  README's tool list only had `ExitPlanMode`). `EnterPlanMode` is the
  missing other half of the plan-mode story already documented below —
  a 7-condition "when to use" rubric with worked good/bad examples,
  the mirror image of `ExitPlanMode`'s own documented trigger
  conditions. `AskUserQuestion` has a `preview` field (ASCII mockups
  or code snippets rendered side-by-side with the options) not
  documented anywhere else in this collection.

## System prompt assembly

`src/constants/prompts.ts` assembles the prompt from named sections
(identity/tone, task-doing conventions, tool-use policy, environment
block, dynamic language/output-style/MCP-instruction sections) — the
same overall shape documented from the plain-text `Prompt.txt`
extraction in this folder's main README, which is a point of
convergence between the two independently-sourced leaks rather than
something this document is asserting on its own.

Two things the full-source view adds that a prompt-text extraction
can't show:

- **Explicit prompt-caching-aware section design.** A separate file,
  `systemPromptSections.ts`, wraps most sections in a memoization layer
  (`systemPromptSection()`) computed once and cached until `/clear` or
  `/compact`, but marks a few sections with a deliberately named
  `DANGEROUS_uncachedSystemPromptSection()` wrapper for content that
  must be recomputed every turn — a naming choice that reads as a
  direct warning to future maintainers that adding an uncached section
  has a real prompt-cache-cost consequence, not just a style note.
- **CLAUDE.md loading and git-status injection are two separate,
  independently-gated functions** in `context.ts` (`getUserContext()`
  for CLAUDE.md, respecting a `CLAUDE_CODE_DISABLE_CLAUDE_MDS` env var
  and a "bare mode"; `getSystemContext()` for git branch/status/recent
  commits, skipped in remote-execution contexts) — confirming these are
  independently toggleable pieces of environment injection rather than
  one monolithic block, and that git-status text is truncated past
  2000 characters specifically to control token cost.

## Permission system

The most fleshed-out subsystem in the research pass, and worth reading
alongside this collection's cross-source tool-surface work since none
of the prompt-only extractions elsewhere in this repo show this level
of mechanism (they only show the *instruction text* asking the model to
seek permission, not the enforcement architecture behind it).

- **Six modes**: `default`, `plan`, `acceptEdits`, `bypassPermissions`,
  `dontAsk`, and an internal-only `auto` mode gated behind a feature
  flag and excluded from the externally-available mode set by an
  `isExternalPermissionMode()` type guard.
- **Rule model**: a `PermissionRule` is `{source, behavior, value}` —
  `source` ∈ user/project/local/flag/policy settings, CLI arg, command,
  or session; `behavior` ∈ allow/deny/ask; `value` carries the tool name
  plus optional pattern content (e.g. a bash-prefix pattern). Rules from
  all sources are aggregated into three maps (always-allow,
  always-deny, always-ask) that the decision function consults in
  order — allow wins outright, deny blocks outright, otherwise
  content-specific pattern matching applies, and remaining "ask"
  decisions get transformed per-mode (`dontAsk` auto-denies with a
  rationale instead of prompting; `acceptEdits` short-circuits the
  expensive classifier path for file-op tools).
- **An LLM-based "auto" classifier** (`yoloClassifier.ts`) for the
  internal-only `auto` mode: a fast first-pass decides allow/no-allow
  cheaply, and only escalates to a slower "thinking" pass if the fast
  pass leans toward blocking — built from recent conversation context
  plus the user's own configured allow/deny rules and CLAUDE.md. A
  companion `bashClassifier.ts` for more granular bash-specific
  classification exists as a file but is one of the confirmed stubs
  ("classifier permissions feature is ANT-ONLY") — its real logic isn't
  in the public repo.
- **Storage**: settings-file-based, loaded at policy (managed/
  enterprise) > project > user > local scope, format
  `{"permissions": {"allow": [...], "deny": [...], "ask": [...]}}` as
  string-pattern arrays per behavior, with a managed-settings flag that
  can restrict evaluation to policy rules only (an enterprise lockdown
  mechanism).
- **The model's own prompt text is silent on all of this** — a targeted
  search of `Prompt.txt` (the plain extracted system prompt, distinct
  from this architecture doc) found zero language about permission
  modes, risk classification, or approval mechanics anywhere. The
  entire machinery above lives in the harness, invisible to the model;
  unlike OpenHands (below, in a cross-source companion doc) or Cline,
  Claude Code's model isn't told the rules, it's just gated by them.
- **Cross-source corroboration, not just a leak claim**: Anthropic's
  own public hooks documentation (`code.claude.com/docs/en/hooks`)
  independently confirms the exact same six-value `permission_mode`
  enum (`default`/`plan`/`acceptEdits`/`auto`/`dontAsk`/
  `bypassPermissions`, with `default` labeled "Manual" in the UI) as a
  field passed into hook payloads — strong evidence the leaked
  architecture reflects the real shipped product, not just this
  extraction's interpretation.
- **`PreToolUse`, missing from this repo's own leaked source, is real
  and fully documented publicly** — worth flagging since it's easy to
  assume every hook event this doc cites came from the leak; this one
  didn't. Per the public docs: fires "before a tool call executes,"
  can inspect `tool_name`/`tool_input`/the current `permission_mode`,
  and returns a `permissionDecision` of `deny`/`allow`/`ask`/`defer`
  (defer falls through to the normal permission system) plus a
  `permissionDecisionReason` shown to the model — and, distinctively,
  an `updatedInput` field that lets the hook **rewrite** the tool's
  arguments before execution, not just block or allow it. Exit code 0
  with JSON output processes `permissionDecision`; exit code 2 is a
  hard block. Matchers operate on tool name (including regex like
  `"mcp__.*"`) with an `if` field using the same pattern syntax as
  settings rules (`"Bash(git *)"`). Two further hook events named in
  the public docs but not in the leak — `PermissionRequest` ("when a
  permission dialog appears") and `PermissionDenied` ("when a tool
  call is denied by the auto mode classifier") — directly confirm the
  `auto` mode's LLM classifier above is real and has its own
  hook-observable denial event, not just an internal implementation
  detail.
- **`ExitPlanMode`, the tool that ends `plan` mode**: per its own tool
  description, "Use this tool when you are in plan mode and have
  finished presenting your plan and are ready to code. This will
  prompt the user to exit plan mode" — with explicit good/bad examples
  distinguishing "planning implementation steps" (should trigger it)
  from pure research tasks (should not) — the model has a dedicated
  tool to request the mode transition, unlike Cline's Plan/Act split
  (see `cline/README.md`'s Permissions section), where the model can
  only ask in prose and has no equivalent forcing tool.
- **`EnterPlanMode`, its counterpart**, confirmed only via the richer
  later capture (not the original leak): a 7-condition "when to use"
  rubric with worked good/bad examples — the missing other half of the
  plan-mode story this section could previously only describe from the
  exit side.
- **Provenance discipline worth keeping straight when citing this
  section**: the six-mode enum, rule model, `yoloClassifier.ts`/
  `bashClassifier.ts`, and settings-file storage are all leak-confirmed
  (this repo's own extraction); the `PreToolUse` mechanics,
  `permissionDecision`/exit-code protocol, and the `PermissionRequest`/
  `PermissionDenied` event names are confirmed only via Anthropic's
  public docs, fetched separately — don't conflate the two
  provenances when citing this section elsewhere.

## Git and version control

See [`agent-git-vcs.md`](../../agent-git-vcs.md) for the cross-source
comparison this feeds into. Sourced from `Prompt.txt`/`Tools.json`
(the leak) plus, for worktree isolation specifically, this live
session's own current tool schemas (fetched directly, not read from
any file — flagged explicitly below since it's a different provenance
than everything else in this document).

- **Commit message conventions, fully specified**: the Bash tool's own
  description carries a dedicated "# Committing changes with git"
  section — gather `git status`/`git diff`/`git log` in parallel first
  (the log read specifically "so that you can follow this repository's
  commit message style"), draft a concise 1-2 sentence message
  focused on "why" not "what," pass it via HEREDOC, and append a
  trailer. **The trailer text has visibly evolved between the leaked
  snapshot and this live session** — the leak (captured with Sonnet 4,
  dated 2025-08-19) ends commits with "🤖 Generated with [Claude
  Code](https://claude.ai/code)\n\nCo-Authored-By: Claude
  &lt;noreply@anthropic.com&gt;"; this live session's own Bash-tool
  description instead ends with a model-version-specific author name
  and an added session-URL trailer, with the emoji/"Generated with"
  line dropped — a real, dated convention change, not a discrepancy
  between two captures of the same thing.
- **Pre-commit hook handling is the one place amending is explicitly
  sanctioned**: "If the commit fails due to pre-commit hook changes,
  retry the commit ONCE... If it fails again, it usually means a
  pre-commit hook is preventing the commit. If the commit succeeds but
  you notice that files were modified by the pre-commit hook, you MUST
  amend your commit to include them." Elsewhere amending is treated as
  a destructive action requiring explicit authorization (consistent
  with the general "hard to reverse" framing this doc's §6 covers for
  other sources).
- **When to commit at all is a hardcoded prompt-level prohibition,
  not tied to the configurable permission-mode system**: "NEVER commit
  changes unless the user explicitly asks you to. It is VERY IMPORTANT
  to only commit when explicitly asked, otherwise the user will feel
  that you are being too proactive." No environment variable or
  settings-file key was found anywhere in this doc's Permission-system
  research (six modes, settings-file scopes, LLM classifier) that
  toggles this specifically — file edits and bash commands get the
  full permission-mode machinery, but committing is gated by one
  separate, non-configurable rule layered independently on top of
  whatever mode is active.
- **PR workflow, fully specified with a literal template**: the same
  parallel-gather-then-analyze pattern as commits, extended to look at
  the *entire* branch's commit history since divergence ("NOT just the
  latest commit, but ALL commits that will be included"), then:
  ```
  gh pr create --title "the pr title" --body "$(cat <<'EOF'
  ## Summary
  <1-3 bullet points>

  ## Test plan
  [Checklist of TODOs for testing the pull request...]

  🤖 Generated with [Claude Code](https://claude.ai/code)
  EOF
  )"
  ```
  No distinct self-review-before-opening step is described — the model
  is told to *analyze* the diff/history to draft the summary, but
  there's no instruction to critique its own diff for bugs first, the
  way this collection's self-verification doc found the (ant-gated)
  verification subagent does for general task completion; PR creation
  isn't wired to that mechanism in what's captured.
- **Branch naming**: no explicit convention or template found (unlike,
  say, a `feature/xyz` pattern) — the current repo's main branch name
  is injected as live environment context at conversation start rather
  than assumed, and branch creation is just "create new branch if
  needed," one of three parallel steps in the PR flow.
- **Worktree isolation — the richest finding on this axis in the whole
  survey, confirmed via this live session's own current tool
  schemas** (not the leak, which only names `EnterWorktreeTool`/
  `ExitWorktreeTool` as conditionally-added, confirmed-non-stub tools
  without reading their bodies): a dedicated, **user/project-invoked**
  session-mode-switching mechanism, not a background implementation
  detail.
  - **Explicitly gated to avoid being confused with ordinary branch
    work**: "Use this tool ONLY when explicitly instructed to work in
    a worktree — either by the user directly, or by project
    instructions (CLAUDE.md / memory)... Never use this tool unless
    'worktree' is explicitly mentioned."
  - **Mechanism**: creates a real `git worktree` inside
    `.claude/worktrees/` on a new branch, with a `worktree.baseRef`
    setting (`fresh`, default, branches from `origin/<default-branch>`;
    `head` branches from local HEAD) governing what it forks from.
    Outside a git repo, it "delegates to WorktreeCreate/WorktreeRemove
    hooks for VCS-agnostic isolation" — a genuinely pluggable non-git
    fallback.
  - **Composes with sub-agent isolation**: works from agents whose
    working directory was pinned at launch, and "the switch only
    affects this agent, not the parent session."
  - **`path` parameter for entering an *existing* worktree, confirmed
    only via the richer later capture**: `EnterWorktree` isn't only a
    creation tool — passing `path` switches into an already-existing
    worktree rather than creating a new one, with its own concurrency
    rule ("Must not already be in a worktree session when creating a
    new worktree (`name`); switching into another existing worktree
    via `path` is allowed").
  - **A tmux-session lifecycle tied to the keep/remove decision, also
    confirmed only via the richer capture**: `ExitWorktree`'s two
    dispositions affect any tmux session running inside the worktree
    differently — `"keep"` leaves it running so the user can reattach,
    `"remove"` kills it.
  - **Fail-closed removal**: exiting with `"remove"` "will REFUSE to
    remove it unless [`discard_changes`] is set to `true`" if the
    worktree has uncommitted files or commits not on the original
    branch — no silent data loss, and "on session exit, if still in
    the worktree, the user will be prompted to keep or remove it,"
    never removed silently.

## Multi-agent "Team" coordination

This is the part most directly relevant to
[`agent-subagent-architectures.md`](../../agent-subagent-architectures.md)
in this collection, and it turns out to be more structured than
anything captured from prompt-only extractions elsewhere: a
**supervisor-worker architecture layered on top of the same sub-agent
primitive** used for ordinary Task-tool delegation, not a separate
peer-to-peer engine.

- **`Task.ts`** (top-level) defines a shared abstraction — a `TaskType`
  union covering six execution modes (local bash, local agent, remote
  agent, in-process teammate, local workflow, MCP monitoring, plus a
  "dream" mode) and a common status lifecycle. Concrete task kinds
  (`LocalAgentTask`, `RemoteAgentTask`, `InProcessTeammateTask`, etc.)
  implement this shared contract — meaning plain async sub-agent
  delegation and full "Team" coordination are **two policies riding the
  same underlying task machinery**, distinguished mainly by which tools
  each context is allowed to use (`ASYNC_AGENT_ALLOWED_TOOLS` vs.
  `COORDINATOR_MODE_ALLOWED_TOOLS` vs.
  `IN_PROCESS_TEAMMATE_ALLOWED_TOOLS`, all defined as constants in
  `tools.ts`).
- **`coordinator/coordinatorMode.ts`** generates a distinct system
  prompt for the supervisor role, explicitly instructing it to behave
  like a manager rather than a conversational peer (e.g. told not to
  thank or acknowledge worker output the way it would a human).
- **`TeamCreateTool`** materializes a team: generates a team name, a
  deterministic lead-agent ID, writes team metadata to disk, resets
  task numbering to start fresh per swarm, and registers the team for
  cleanup at session end — a fix, per an in-code comment, for a prior
  bug where teams were "left on disk forever unless explicitly
  TeamDelete'd." The lead agent is explicitly excluded from its own
  teammate registry.
- **Workers are spawned through the same `AgentTool`/`runAgent.ts`
  machinery as ordinary sub-agent delegation** — self-contained
  prompts, no visibility into prior conversation, a unique task ID per
  worker. Coordinator mode is a policy/tool-restriction layer on top of
  this, not a different transport.
- **`SendMessageTool`** both continues a running worker by task ID and
  routes messages between named teammates — direct, broadcast (`"*"`),
  or cross-session via `bridge:`/`uds:` prefixes — plus structured
  message types beyond plain text (shutdown request/response, plan
  approval/rejection). Delivery is asynchronous: messages land in
  per-agent mailboxes; a stopped in-process agent gets auto-resumed to
  receive a queued message. Results surface back to the coordinator as
  structured `<task-notification>`-style blocks carrying status/summary/
  token-usage — a close analog to the `<task-notification>` structure
  this very session receives from its own background sub-agents,
  suggesting (without proving) real architectural continuity between
  what's leaked here and the live product.
- **Gating**: the whole feature requires an experimental env var or CLI
  flag for external users, plus a remote GrowthBook killswitch — see
  "Feature flags" below.
- One real gap in the research pass: `ListPeersTool.ts`, which would
  show exactly how peer discovery/listing works, is a confirmed stub —
  so the peer-visibility mechanism is inferred (from `TeamCreateTool`'s
  teammate registry) rather than directly confirmed.

**This whole section was built entirely from source-code inference —
file names, comments, and constant names, never a captured prompt.
The richer, later capture (`deferred-tools.md`) confirms the core of
it directly, promoting several claims above from "inferred" to
"confirmed via captured tool schema":**

- **`TeamCreate`/`TeamDelete` are real, captured tools**, not just
  source-inferred classes. `TeamCreate`'s own description states the
  Task-system relationship even more directly than the source-code
  inference above managed to: **"Teams have a 1:1 correspondence with
  task lists (Team = TaskList)"** — confirming `TaskList`'s "Teammate
  Workflow" documentation and this section's `Task.ts`-based inference
  are describing the same system from two different captured angles.
  Creates `~/.claude/teams/{team-name}/config.json` and
  `~/.claude/tasks/{team-name}/`. `TeamDelete` "will fail if the team
  still has active members" — a real precondition, not previously
  documented.
- **`SendMessage`'s structured message types are confirmed by name**:
  `shutdown_request`/`shutdown_response`/`plan_approval_request`/
  `plan_approval_response` as literal JSON message-type values,
  directly validating this section's previous "shutdown request/
  response, plan approval/rejection" claim, which had been sourced
  only from code inference before.
- **A previously-undocumented idle-state UX rule**: "Teammates go idle
  after every turn... A teammate going idle immediately after sending
  you a message does NOT mean they are done" — with its own
  peer-visibility mechanism ("a brief summary is included in their
  idle notification"), a more specific and different claim than the
  `ListPeersTool.ts`-stub-driven uncertainty above; whether this
  resolves that gap or describes a separate summary channel isn't
  fully clear from the captured text alone, but it's a real, new,
  directly-quoted data point either way.

## Plugins and skills

Two related but distinct extensibility layers:

- **Plugins** are the broader installable unit — can register skills,
  hooks, *and* MCP servers, with marketplace/versioning/trust machinery
  (`name@marketplace` identity, dependency validation between plugins,
  non-in-place updates that fetch-then-swap rather than mutate in
  place, policy-based install blocking for admin-managed environments).
  Built-in plugins ship with the CLI and are distinguished from
  marketplace ones by a `@builtin` ID suffix.
- **Skills** are one specific artifact type plugins (or bare
  `.claude/skills` directories, or MCP servers) can supply into a
  shared registry: a directory containing `SKILL.md` with YAML
  frontmatter (name, description, `when-to-use`, gitignore-style
  activation `paths`, allowed-tools, model/effort overrides,
  shell-execution and variable-substitution support) plus a markdown
  body that becomes the actual prompt text delivered to the model.
  Discovery walks up the directory tree from an edited file to find
  nested `.claude/skills` dirs, in addition to a static startup scan of
  managed/user/project skill directories.
- **The skill-ranking/relevance logic is a confirmed stub**
  (`skillSearch/signals.ts` — a `DiscoverySignal` interface with no
  body) — so *how* skills actually get surfaced/prioritized to the
  model isn't visible in what's public, only that a structured
  "signal" concept for it exists.

## Feature flags: two independent systems

- **Compile-time, via Bun's bundler**: a `feature('FLAG_NAME')` macro
  that Bun's bundler replaces with a literal `true`/`false` at build
  time, letting false-gated branches be statically stripped from the
  shipped bundle (real dead-code elimination, not just a runtime
  no-op). Outside the bundler, the macro just returns `false`.
- **Runtime, via GrowthBook**: a remote-eval feature-flagging client
  (flag keys observed with a `tengu_` prefix) with a resolution order
  of env-var override → local config override (internal-only) →
  in-memory cache → disk-persisted cache (so flags survive restarts
  without a fresh network round-trip). This is the layer used as an
  emergency killswitch independent of redeploys — e.g. the
  multi-agent-teams feature and voice mode both have a GrowthBook flag
  that can disable them for external users without shipping new code.

The two systems answer different questions: the compile-time one
decides what code exists in the shipped bundle at all; the runtime one
decides what's turned on for a given session among code that did ship.

## MCP integration

Broader transport support than any single MCP-related mention captured
from the prompt-only sources in this collection: stdio, SSE, streamable
HTTP, WebSocket (plus an IDE-specific WebSocket variant), in-process
servers (Chrome and Computer-Use MCP servers run without subprocess
overhead), and a proxied path for remote servers reached through
Anthropic's own infrastructure. Auth covers standard OAuth (RFC 9728
discovery → RFC 8414 metadata → PKCE) plus a separate "Cross-App
Access" path letting one enterprise IdP login be reused across multiple
MCP servers. Connected servers' tools get surfaced into the local tool
registry with `mcp__servername__toolname`-prefixed names — the same
naming convention visible directly in this very session's own deferred
MCP tool list, which is the closest thing to independent corroboration
this research pass found.

## State, sessions, and memory — two genuinely different systems

- **`state/`** is in-memory, per-process application state (including
  the live `teamContext` used by Team coordination above) — session UI
  state, not persisted memory.
- **`memdir/`** is a separate, file-based, cross-session memory store —
  markdown files with an index (`MEMORY.md`) pointing to per-topic
  files, each with YAML frontmatter constraining memory to four
  categories (user preferences, collaboration-pattern feedback,
  project-specific context, reference material) and **explicitly
  excluding anything derivable from the current project state** (code
  patterns, architecture, git history) — a deliberate scope boundary
  keeping it from overlapping with CLAUDE.md, which already covers
  code-adjacent documentation (see "System prompt assembly" above).
  Retrieval is LLM-based, not keyword/recency matching: a side-query
  sends the user's current message plus every memory file's
  filename+description header to a model, with a conservative
  selection prompt ("if you are unsure... do not include it"), capped
  at 5 memories per turn, filtering out redundant tool-doc memories for
  tools already used recently while preserving warning/edge-case notes.

This is architecturally close to what `agent-tool-surfaces.md` §7 in
this collection flags as a rare capability — persistent cross-session
memory exposed as a genuine system rather than a passive file
convention (the closest other example in this collection being leaked
Windsurf's `create_memory`/`trajectory_search` tools) — except here
retrieval is a background LLM call gating what gets *read into* context
each turn, rather than a tool the model calls explicitly to search its
own memory.

## Other distinctive findings

- **Vim emulation** (`src/vim/`: `motions.ts`, `operators.ts`,
  `textObjects.ts`, `transitions.ts`) — file naming strongly suggests a
  real modal-editing implementation for the terminal input box
  (motion+operator+text-object composition, a mode-transition state
  machine), though file contents weren't read directly.
- **Voice mode** is real but carefully gated — requires Anthropic OAuth
  specifically (rejects plain API-key auth), talks to a dedicated
  streaming endpoint, and carries its own GrowthBook emergency
  killswitch, distinct from the SSH stub below in that this one reads
  as a genuinely shipped, staged-rollout feature rather than a
  placeholder.
- **SSH support is a confirmed stub** — whatever remote-execution-over-
  SSH capability the real product has, its implementation isn't in this
  public repo.
- **Worktree-scoped sub-sessions** (`EnterWorktreeTool`/
  `ExitWorktreeTool`) are conditionally added to the tool pool in
  worktree mode, and both tools have the same fully-fleshed-out
  four-file structure as other confirmed-real tools (unlike the
  stubbed ones) — a reasonably confident signal this one isn't a stub,
  though the tool bodies themselves weren't read directly.
- **A broader tool inventory than any single prompt extraction shows**:
  beyond the well-known Bash/Read/Edit/Grep/Task family, the full
  `src/tools/` listing includes tools not visible in any prompt-only
  leak in this collection — an interactive clarifying-question tool, a
  context-inspection/debug tool, a context-"snip" compaction tool, a
  synthetic-output tool used specifically by coordinator mode, a
  terminal-capture tool, and others whose purpose is inferred from
  naming only.

## Self-verification and testing

See [`agent-self-verification.md`](../../agent-self-verification.md) for
the cross-source comparison this feeds into. **Read the caveat below
before the findings** — it changes how to interpret nearly everything
in this section.

**The critical caveat: most of what's interesting here is an
internal-only experiment, not shipped behavior.** Almost every
mechanism below is gated behind `process.env.USER_TYPE === 'ant'` (an
Anthropic-employee-only flag) or a GrowthBook flag explicitly commented
"3P default: false — ant-only A/B" — meaning it's dead-code-eliminated
out of ordinary external builds. What's confirmed is Anthropic testing
verification mechanisms internally, not necessarily what ships to
regular Claude Code users. One mechanism (Stop hooks, below) is the
exception — genuinely general, not ant-gated, consistent with Claude
Code's publicly documented hook system.

- **A built-in adversarial "verification" subagent**
  (`src/tools/AgentTool/built-in/verificationAgent.ts`) — the single
  most distinctive finding. A structurally separate LLM instance, no
  file-write access, whose entire prompt is built around **not trusting
  the implementer's own self-report**: it must gather command-output
  evidence for every check rather than accept claims, run the build,
  run the full test suite ("failing tests are an automatic FAIL"), run
  linters/type-checkers, apply type-specific strategies
  (frontend/backend/CLI/infra/migration), and perform mandatory
  "adversarial probes" (concurrency, boundary values, idempotency)
  before issuing a **PASS/FAIL/PARTIAL verdict the implementer cannot
  self-assign**. Internal-only, per the caveat above.
- **`VerifyPlanExecutionTool` is a stub**, but the wiring around it is
  real: gated behind `CLAUDE_CODE_VERIFY_PLAN=true` plus the ant-only
  flag, model-invoked (not automatically triggered by `ExitPlanMode`),
  with a periodic nudge — every 10 human turns since a plan was
  approved, if verification hasn't started, a system-reminder is
  injected: "You have completed implementing the plan. Please call the
  'VerifyPlanExecution' tool directly (NOT the Task tool or an agent)."
  The nudge's own trigger logic is a naive text-match (checks todo text
  for the substring "verif"), not diff-aware — no automated mechanism
  compares the actual code diff against the plan; that's left entirely
  to whatever the verification subagent itself does when it runs.
- **A quantified, empirically-motivated problem statement, disclosed in
  the leak's own code comments**: two ant-gated system-prompt lines
  ("verify it actually works before reporting complete"; "never claim
  'all tests pass' when output shows failures... to manufacture a green
  result") are annotated with an internal measurement — "False-claims
  mitigation for Capybara v8 (29-30% FC rate vs v4's 16.7%)" — i.e. an
  internal model version was observed falsely claiming task completion
  roughly 3 times in 10, and this specific mitigation was built and put
  under A/B test in response. Rare, concrete evidence (rather than
  speculation) that false-completion-claiming is a real, measured
  failure mode significant enough to drive dedicated engineering.
- **The one genuinely shipped, general mechanism: `Stop` hooks can
  force continuation.** Not ant-gated. A 26-member `HookEvent` union
  includes `Stop`, `StopFailure`, `SubagentStop`, `PostToolUse`,
  `PostToolUseFailure`, `TaskCompleted`, `TeammateIdle` alongside the
  already-documented `PreCompact`/`PostCompact`. If a user-configured
  `Stop` hook returns `preventContinuation: true`, the agent loop does
  **not** end — it keeps running with the hook's stated reason surfaced
  as a message. This is the concrete mechanism behind "wire up `npm
  test` on Stop and block the agent from finishing if it fails" — a
  real, user-configurable verification gate, just one the user sets up
  rather than the agent choosing to use.
- **A softer, genuinely-shipped "autonomy" framing**: a non-ant-gated
  "Autonomous work" section (gated only by a real feature flag) tells
  the model it can "run tests, check types, run linters — all without
  asking" (a permission statement, not a mandate) and poses a rhetorical
  self-check: "what would I want to verify before calling this done?" —
  softer than the verification subagent's hard PASS/FAIL gate, but
  present in ordinary builds.
- **`SyntheticOutputTool` is real infrastructure, not a stub** — Ajv
  JSON-schema validation of arbitrary agent output, used as supporting
  plumbing for both agent hooks and "background verification" broadly;
  it's a building block the verification machinery uses, not itself a
  correctness-checker.
- **A much more opinionated, genuinely-shipped verification doctrine,
  confirmed via the richer capture's `verify.md`/`run.md` bundled
  skills** — not ant-gated, and considerably stronger than the "softer
  autonomy framing" bullet above: "verification is runtime
  observation... don't run tests, don't typecheck" — i.e. the shipped
  `/verify` skill explicitly *deprioritizes* the two checks the
  ant-gated verification subagent treats as mandatory, in favor of
  actually launching and exercising the application, with `run.md`
  supplying the app-launching patterns by project type. Worth reading
  as a second, real self-verification tier — external users get a
  runtime-observation-first doctrine via `/verify`; the exhaustive
  build/test/lint/adversarial-probe gate stays internal-only.
- **`loop.md` (the `/loop` skill) adds a distinct, genuinely-shipped
  autonomy-discipline layer**, driving `ScheduleWakeup` (see Tool
  definition and dispatch above): explicit "steward, not initiator"
  framing, a trust-erosion warning ("If you find yourself reaching for
  justifications about why a push is probably fine, that's a signal to
  wait"), and a rule to scale back after three consecutive
  nothing-to-do results. This extends, rather than contradicts, the
  "Autonomous work" section documented above — a second, richer,
  loop-specific autonomy doctrine layered on top of the general one.
- **`security-review.md` is a second, functionally distinct security
  mechanism, not a restatement of anything already in this
  document** — the built-in `/security-review` skill is manually
  invoked, git-diff-scoped, and multi-agent (a finder pass, then a
  parallel false-positive filter), with a detailed confidence-scoring
  rubric and hard exclusions (DoS, secrets-already-on-disk,
  rate-limiting-by-design). This is architecturally different from the
  automatic, hook-triggered `security-guidance` plugin already
  documented in this collection (`skills/anthropic/security-guidance/`
  — pattern+LLM two-pass, fires on edit/commit without being asked).
  Both mechanisms coexist in the shipped product; don't conflate them.

## Why this is worth having alongside the prompt-only extraction

Three independently-sourced captures now corroborate each other on the
parts that overlap (system prompt structure, the Agent/Task tool's
stateless one-shot sub-agent contract, the git-commit trailer
convention, the worktree tool's gating language) while the full-source
leak adds an entire layer this collection's other sources can't show
at all: not just *what a scaffold tells the model to do*, but the
actual engineering underneath — prompt caching mechanics, a two-tier
feature-flag system, a real permission rule-resolution algorithm, and
a supervisor-worker multi-agent system built as a policy layer over the
same primitive as ordinary sub-agent delegation. That last point in
particular sharpens a distinction `agent-subagent-architectures.md`
could only gesture at from prompt text alone: "sub-agent delegation"
and "multi-agent team coordination" aren't two different mechanisms
here, they're the same mechanism under two different tool-allowlist
policies — and the richer, later prompt-text capture (`deferred-tools.md`)
has since confirmed the `TeamCreate`/`TeamDelete`/`SendMessage` half of
that claim directly, closing the gap between "inferred from source"
and "confirmed via captured schema" that this document flagged as an
open question when it was first written.
