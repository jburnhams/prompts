# Grok Build

- **Type**: Coding agent (xAI's terminal/CLI coding agent)
- **Status**: closed source (leaked)
- **Vendor**: xAI
- **Mirror source**: https://github.com/asgeirtj/system_prompts_leaks
  (`xAI/grok-build.md`), retrieved 2026-07-12 — a different,
  independently-maintained leak aggregator than the
  [`x1xhlol/system-prompts-and-models-of-ai-tools`](https://github.com/x1xhlol/system-prompts-and-models-of-ai-tools)
  repo used for most of this collection's other `leaked/` sources (see
  `../README.md`). First xAI coding-agent coverage in this collection —
  previously only general Grok chatbot variants existed elsewhere, none
  fetched in.

## Files

- `grok-build.md` (1329 lines) — a structured, three-part capture:
  "1. Core System Prompt" (persona through a dynamically-appended
  memory section), "2. Tool Definitions & JSON Schemas" (26 tools, full
  JSON Schema per tool), "3. Runtime-Injected Context" (five
  system-reminder/wrapper templates: project instructions, skills
  manifest, MCP announcement, user-query wrapper, user-info block).
  Opens with "You are Grok 4.3 released by xAI in April 2026. You are
  an interactive CLI tool that helps users with software engineering
  tasks."

## A finding that runs through nearly every section below

Grok Build's tool descriptions and several of its behavioral rules are
**near-verbatim reproductions of Claude Code's own leaked tool
descriptions and prompt text** — not just convergent phrasing on a
common idea, but the same sentences, in the same order, with the same
worked examples, differing mainly in tool names. This is stronger and
more literal than any other cross-vendor text match found in this
collection (the previous strongest instance, documented in
`agent-git-vcs.md` §2, is a single one-line match between Claude Code's
leaked prompt and OpenCode's base persona: "NEVER commit changes unless
the user explicitly asks you to..."). Confirmed against files already
stored in this collection, not from outside memory:

- **Grok's `write` tool description is Claude Code's `Write` tool
  description with one string substituted.** Claude Code's `Tools.json`
  (already in `leaked/claude-code/`): "Writes a file to the local
  filesystem. Usage: - This tool will overwrite the existing file if
  there is one at the provided path. - If this is an existing file, you
  MUST use the Read tool first to read the file's contents. This tool
  will fail if you did not read the file first. - ALWAYS prefer editing
  existing files in the codebase. NEVER write new files unless
  explicitly required. - NEVER proactively create documentation files
  (*.md) or README files. Only create documentation files if explicitly
  requested by the User. - Only use emojis if the user explicitly
  requests it. Avoid writing emojis to files unless asked." Grok's
  `write`: identical text, verbatim, with "the Read tool" changed to
  "the read_file tool" and nothing else.
- **Grok's `search_replace` tool is Claude Code's `Edit` tool**, same
  substitution pattern: "You **MUST** use your `read_file` tool at
  least once in the conversation before editing... Only use emojis if
  the user explicitly requests it. Avoid adding emojis to files unless
  asked. The edit will FAIL if `old_string` is not unique in the
  file... Use `replace_all` for replacing and renaming strings across
  the file" — matches `Tools.json`'s `Edit` description clause for
  clause, only reordering one sentence about disambiguating
  `old_string`.
- **Grok's `read_file` tool matches Claude Code's `Read` tool almost
  exactly**, including catching up to the *same* later feature addition:
  Claude Code's older `Tools.json` capture lacks a PDF `pages`
  parameter, but the newer `claude-code-2.1.172-opus-4.6.md` capture
  (also in this collection) adds one — "Reads PDFs via the `pages`
  parameter (e.g. '1-5', max 20 pages/request; required for PDFs over
  10 pages)" — and Grok's `read_file` has the identical capability,
  worded almost the same way: "PDFs with 10 or fewer pages are read
  automatically. For larger PDFs, specify which pages to read using the
  `pages` parameter (e.g. pages="1-5"). Maximum 20 pages per call."
- **Grok's git-commit guidance inside `run_terminal_command` is Claude
  Code's Bash-tool git guidance, word for word.**
  `claude-code-2.1.172-opus-4.6.md` (already in this collection): "Prefer
  to create a new commit rather than amending an existing commit... 
  Before running destructive operations (e.g., git reset --hard, git
  push --force, git checkout --), consider whether there is a safer
  alternative that achieves the same goal. Only use destructive
  operations when they are truly the best approach... Never skip hooks
  (--no-verify) or bypass signing (--no-gpg-sign, -c
  commit.gpgsign=false) unless the user has explicitly asked for it. If
  a hook fails, investigate and fix the underlying issue." Grok's
  `run_terminal_command`: "Prefer creating a new commit rather than
  amending an existing commit... Before running destructive operations
  (e.g., git reset --hard, git push --force, git checkout --), consider
  whether there is a safer alternative that achieves the same goal.
  Only use destructive operations when they are truly the best
  approach... Never skip hooks (--no-verify) or bypass signing
  (--no-gpg-sign) unless the user has explicitly asked for it. If a
  hook fails, investigate and fix the underlying issue." Identical
  clause-for-clause, minus the `-c commit.gpgsign=false` aside.
- **The exact same tone rule, same worked example**:
  `claude-code-2.1.172-opus-4.6.md`: "Do not use a colon before tool
  calls. Your tool calls may not be shown directly in the output, so
  text like 'Let me read the file:' followed by a read tool call should
  just be 'Let me read the file.' with a period." Grok's
  `<tone_and_style>`: the identical sentence, identical example.
- **The same delegation-parallelism rule, same structure**:
  `claude-code-2.1.172-opus-4.6.md`: "If the user specifies that they
  want you to run agents 'in parallel', you MUST send a single message
  with multiple Agent tool use content blocks." Grok: "If the user
  specifies that they want you to run multiple agents in parallel, send
  a single message with multiple spawn_subagent tool calls."
- **The `grep` tool description carries the identical worked example**
  for escaping literal braces (`interface\{\}` "to find `interface{}`
  in Go code") found in Claude Code's `Tools.json` `Grep` entry.

Whether this is xAI directly adapting Claude Code's tool prompts, or
both drawing on a shared/leaked template that's begun circulating as
industry boilerplate, isn't determinable from this file alone — but the
degree of literal match (identical sentences, identical worked
examples, identical parenthetical asides) goes well beyond convergent
design and reads as direct textual reuse. Flagged once here in detail;
referenced rather than re-quoted in the topic sections below.

## Tool surface

See [`agent-tool-surfaces.md`](../../agent-tool-surfaces.md) for the
cross-source comparison this feeds into. 26 tools total — mid-sized by
this collection's standards, but with two genuinely novel capabilities
(video generation, a scheduler) not seen in any other source surveyed
for that doc.

- **Shell**: `run_terminal_command` — persistent-shell-adjacent bash
  tool (see the Claude Code parity note above for its git-commit
  guidance). Background execution via a `background` flag, timeout up
  to **36,000,000ms (10 hours)** — the longest ceiling found in this
  collection, well beyond Windsurf's or Claude Code's 10-minute caps.
  On timeout, "the wrapper kills the child process group (SIGTERM,
  escalated to SIGKILL after a ~1s grace period)"; `background: true`
  with `timeout: 0` disables the wrapper timeout entirely, handing
  lifetime ownership to the model via `kill_command_or_subagent`. A
  `description` parameter is present but nullable/optional (unlike
  Crush's *required* description field for its `bash` tool).
- **Search**: `grep` (ripgrep-backed, `-A`/`-B`/`-C`/`-i`/`multiline`/
  `head_limit`, same shape as Claude Code's `Grep`) and `list_dir`
  ("Respects .gitignore patterns... Large directories are summarized
  with file counts and extension breakdowns instead of listing all
  files" — the directory-summarization behavior for large dirs isn't
  called out this explicitly by most other sources surveyed for
  `agent-tool-surfaces.md` §2). No semantic/embedding search, no LSP
  symbol resolution — plain grep/glob tier only.
- **Code execution**: no dedicated code-exec tool; folded into
  `run_terminal_command` like most sources in this collection.
- **Browser/multimodal — the richest finding in this section**:
  `read_file` handles images, PDFs (page-rendered-as-image by default,
  `format: "text"` to extract raw text instead), `.pptx` (text from
  slides and notes), and `.ipynb`. Beyond that: `image_gen` and
  `image_edit` (xAI's own Imagine API, both with an `aspect_ratio` enum
  spanning ten ratios including `19.5:9`/`20:9` phone-screen ratios),
  and — **not seen anywhere else in this collection's tool-surface
  survey** — `video_gen`: "Generate a video from a text description
  using the xAI Video Generation API... Duration 1-15 seconds (default
  8s). Resolution '480p' or '720p'." No other source in
  `agent-tool-surfaces.md`'s §5 (Multimodal) has a video-generation
  tool; Cursor's `create_diagram` and Roo Code's `generate_image` are
  the closest prior examples of dedicated generative-output tools, both
  image-only. No browser-automation tool (no Cline/Windsurf-style
  click/type/screenshot loop) — `web_fetch`/`web_search` only, plain
  fetch-and-search tier, not full interactive browsing.
- **Web**: `web_search` (coding-tailored, `allowed_domains` filter) and
  `web_fetch` (markdown output, 100k-char truncation, "a self-cleaning
  15-minute cache," and — a detail not called out this specifically
  elsewhere — "Cross-host redirects are not followed automatically,"
  a deliberate SSRF-adjacent guard).
- **Planning**: `enter_plan_mode`/`exit_plan_mode`, structurally close
  to Claude Code's own plan-mode pair — read-only exploration
  (`list_dir`, `grep`, `read_file` only, no `search_replace`) followed
  by a plan read "from the plan file on disk, NOT passed as a
  parameter" for user approval. `todo_write` defaults `merge: true`
  ("send only the items you are changing, not the full list") — the
  **opposite default** from Claude Code's `TodoWrite`, which requires
  the full list every call; Grok's opening-call convention explicitly
  overrides the default with `merge: false` to define the full list
  once, then reverts to `merge: true` for status transitions.
- **Extensibility — MCP**: a two-step, mandatory-schema-fetch pattern —
  `search_tool` (keyword search over connected MCP servers' tools) must
  be called before every first `use_tool` invocation: "NEVER guess or
  infer parameter names from the tool's name or description -- the
  schema from `search_tool` is the only source of truth." Structurally
  identical in spirit to this very collection's own `ToolSearch`
  deferred-tool-schema mechanism, worth noting as a case where the
  scaffold being documented and the scaffold doing the documenting
  share a design pattern.
- **Extensibility — Skills**: slash commands (`/<skill-name>`) resolve
  to text files read via `read_file`. Skill search locations span
  `~/.grok/skills/`, `~/.grok/bundled/skills/`, **and also**
  `~/.claude/skills/` and `~/.agents/skills/` — Grok Build explicitly
  reads Claude Code's own skill directory and a generic
  vendor-neutral `.agents/skills/` location, a direct, named
  cross-tool-compatibility gesture not found described this explicitly
  in any other source's tool surface in this collection.
- **Extensibility — scheduler**: `scheduler_create`/`scheduler_list`/
  `scheduler_delete` — recurring or one-shot prompt execution
  ("5m"/"2h"/"1d"/"60s" interval strings, max 50 concurrent, auto-expire
  after 7 days unless `durable: true`). No other source in this
  collection's tool-surface doc has a user-facing recurring-task
  scheduler as a named tool; the closest analog anywhere in this
  collection is this very session's own external trigger/Routine
  system, not another coding-agent source.
- **Persistent memory**: file-based, not database-tool-based like
  Windsurf's `create_memory` — a `MEMORY.md` at both workspace-scoped
  (`~/.grok/memory/<workspace-slug>/MEMORY.md`) and global
  (`~/.grok/memory/MEMORY.md`) locations, read/written via `memory_get`/
  a search-only `memory_search` ("referenced in the `<memory>` section
  but not present in the standard function-calling tool list; they
  appear to be handled internally by the runtime" — a capture note
  worth flagging: two memory tools are named and described in prose but
  have no JSON Schema entry among the 26 captured tools). A `/flush`
  command triggers "a detailed LLM-generated summary... written to the
  searchable session log," distinct from the terser structured
  metadata (message counts, tool-usage breakdown, file paths) saved
  automatically at session end. Compare to Windsurf's `create_memory`
  (tagged, deduped, callable mid-task with no permission needed) —
  Grok's version is closer to Claude Code's/Aider's `CLAUDE.md`/
  `AGENTS.md` passive-file convention, just with a dedicated read/write
  tool pair layered on top rather than ordinary file edits.
- **Async/background — a richer poll/kill/wait trio than most sources**:
  `get_command_or_subagent_output` (by `task_id`, optional blocking
  wait with `timeout_ms`), `kill_command_or_subagent` (SIGTERM/SIGKILL
  for bash, "Cancel+Shutdown" for subagents), and
  `wait_commands_or_subagents` (`wait_any`/`wait_all` mode across
  *multiple* task IDs at once) — the same shape as Codex CLI's
  `wait_agent`, but generalized to cover both background commands and
  subagents through one shared task-ID space, and with an explicit
  any/all mode choice Codex's single-target `wait_agent` doesn't have.
  A separate `monitor` tool exists specifically for streaming
  long-running watch processes ("Each stdout line is an event... Exit
  ends the watch"), distinct from the poll-based background-command
  path — the same background-vs-watch split this collection's
  `agent-tool-surfaces.md` §6 documents for other sources, here with
  three tools instead of two.
- **Sandbox/isolation**: not described for the main session itself (no
  Landlock/Seatbelt-style platform branching, no described OS sandbox).
  What exists is scoped to delegation: `spawn_subagent`'s
  `capability_mode` (`read-only`/`read-write`/`execute`/`all`) and
  `isolation` (`none`/`worktree`) parameters — see Sub-agents and Git
  below.
- **A UI-level tool**: `ask_user_question` — structured multi-choice
  questions with an optional `preview` field rendered when an option is
  focused, and `multiSelect` support; and `update_goal`, a
  goal-progress-logging tool distinct from `todo_write`, whose
  `blocked_reason` field is explicitly gated: "Set only when truly
  stuck after 3+ consecutive failed attempts" — a bounded-retry
  threshold embedded directly in a tool's JSON Schema description
  rather than stated as prose elsewhere in the prompt (see
  Self-verification below).

## Sub-agents

See
[`agent-subagent-architectures.md`](../../agent-subagent-architectures.md)
for the cross-source comparison this feeds into. `spawn_subagent`
implements the **addressable, not stateless** protocol shape that doc's
§2 documents converging on independently across Codex CLI, OpenCode,
OpenHands, and Roo Code — Grok Build is a fifth, equally independent
arrival at the same shape, via yet another concrete mechanism.

- **Delegation trigger**: framed for two purposes at once —
  "parallelizing independent queries and for protecting the main
  context window from excessive results" — the same context-
  conservation-plus-speed framing this doc's §1 documents for Claude
  Code/OpenCode/Crush/v0's search delegates.
- **A typed registry of four agent kinds**, one of them cross-vendor
  branded: `general-purpose` (full tool access), `explore` (read-only:
  `run_terminal_command`, `read_file`, `list_dir`, `grep`), `plan`
  (read-only, "all tools except search_replace" — i.e. broader than
  `explore`, can still run shell commands and fetch the web while
  planning), and **`codex:codex-rescue`** — "Use when stuck, wants a
  second implementation pass, or deeper root-cause investigation." The
  `codex:` namespace prefix on an agent-type string, inside an xAI
  product, naming a rescue/second-opinion role, is worth flagging
  explicitly: no other captured detail in this file explains whether
  this routes to an actual OpenAI Codex integration, a locally-defined
  agent merely styled after Codex naming conventions, or something
  else — flagged as a genuinely unresolved, quotable oddity rather than
  asserted either way.
- **Addressable via a shared task-ID space, not stateless one-shot**:
  `spawn_subagent` returns a handle checked via
  `get_command_or_subagent_output`, terminated via
  `kill_command_or_subagent`, and — the clearest "addressable" signal —
  **`resume_from`**: "Resume from a previously completed subagent's
  conversation. Pass the subagent_id returned by a prior call." This is
  closer to Codex CLI's `send_input`-to-a-still-running-agent shape
  than to Claude Code's/Crush's/v0's fire-and-forget stateless report,
  though Grok's version resumes a *completed* subagent's conversation
  rather than steering one still in flight — a variant not quite
  matching Codex's mid-flight `send_input`/`interrupt` model or
  OpenCode's queue-onto-still-live-job model, closer in spirit to
  re-opening a finished session than either.
- **`capability_mode`** (`read-only`/`read-write`/`execute`/`all`) is a
  tool-scope control distinct from the four named agent types — the
  orchestrator can narrow (or, via `all`, presumably not narrow) a
  spawned agent's permissions independently of which named type it
  picked, a combination of "typed registry" and "per-call scope
  override" not seen together this explicitly elsewhere in this
  collection's sub-agent survey.
- **Turn/output bounding**: no stated turn cap or forced-cutoff nudge
  found (contrast Copilot Chat's `isLastTurn` message, OpenCode's
  `MAX_STEPS_PROMPT`). `get_command_or_subagent_output`'s `block` +
  `timeout_ms` parameters bound how long the *orchestrator* waits, the
  same "cap the wait, not the child's own turns" shape
  `agent-subagent-architectures.md` §4 documents for Codex's
  `wait_agent`.
- **Result-handling contract**: not specified beyond the generic tool
  description ("get output and status from a background task or
  subagent") — no free-text-vs-schema distinction, no explicit
  trust/distrust instruction comparable to Claude Code's "generally be
  trusted" or Emergent's "sometimes dull and lazy" warning. A capture
  gap, not a confirmed absence.
- **Concurrency/write-safety**: no same-file-conflict rule specific to
  sub-agents was found (contrast Gemini CLI's/Amp's explicit
  parallel-iff-disjoint-write-targets guidance) — only the general,
  tool-agnostic "make all independent tool calls in parallel" framing
  under `<tool_calling>` applies, with no sub-agent-specific carve-out.
- **Recursion**: not addressed either way — `capability_mode: "all"`
  is ambiguous as to whether it includes `spawn_subagent` itself; no
  explicit ban (contrast Goose) and no explicit allowance (contrast
  Amp) was found in the captured tool description.
- **Own system prompt**: not captured — only the orchestrator-facing
  tool description (`spawn_subagent`'s schema and surrounding prose)
  is present in this file, the same "No — orchestrator-side only"
  bucket this doc's §3 places Claude Code, Amp, v0, and Emergent in.

## Compaction

See
[`agent-context-compaction.md`](../../agent-context-compaction.md) for
the cross-source comparison this feeds into. No summarization prompt,
trigger threshold, or token budget is captured — but the file does
capture something none of that doc's other sources have: an explicit,
named **consumer-side contract** for what the agent must do immediately
after a compaction event, independent of whatever produces the summary
itself.

- **The existence claim is stated plainly, without qualification**:
  "The conversation has unlimited context through automatic
  summarization" (`<tool_calling>`).
- **A named system-reminder header the agent is told to watch for and
  react to**: "After a context compaction, if your prior todo list is
  no longer in conversation history, **reseed it** with a fresh
  todo_write call (merge: false) before continuing the task." The
  `<task_completion_discipline>` section restates this as a hard rule
  with the trigger condition spelled out precisely: "If a context
  compaction occurs mid-task (the harness signals this with a `##
  Pre-Compaction Todo List` system-reminder), your FIRST tool call
  after the reminder MUST be todo_write (merge: false) reconstructing
  the remaining phases from the pre-compaction snapshot. Do not advance
  any other step until the list is back." A targeted search of this
  collection's `leaked/claude-code/` files (which document Claude
  Code's own `TodoWrite`/compaction machinery in detail — see
  `agent-context-compaction.md`'s Claude Code entry) found no
  `Pre-Compaction Todo List` string or equivalent reseed instruction
  anywhere — unlike the tool-description matches above, this specific
  mechanism is **not** a confirmed match to anything already documented
  for Claude Code in this collection, and reads as a genuinely distinct
  design choice layered onto an otherwise closely-parallel tool
  surface, not another instance of the copying pattern.
- **No recovery philosophy captured**: no stated pointer back to a full
  transcript (contrast Claude Code/Copilot Chat), no "the summary is
  the only surviving record" framing (contrast Crush/Gemini CLI), and
  no externalize-before-compaction strategy comparable to Windsurf's
  `create_memory`/`trajectory_search` pair — though Grok's own
  `MEMORY.md`/`memory_search` system (see Tool surface above) could in
  principle serve a similar externalization role; nothing in the
  captured text explicitly frames memory-writing as a compaction
  mitigation the way Windsurf's `<memory_system>` block does.
- **No trigger model, prompt shape, or numeric token budget captured**
  at all — this file documents only the post-compaction *consumer
  contract* (the todo-reseed rule above), not the summarization prompt,
  trigger logic, or any threshold. A capture gap for everything else
  this doc's §1/§2/§6 typically compare.

## Turn output

See [`agent-turn-output.md`](../../agent-turn-output.md) for the
cross-source comparison this feeds into.

- **Title generation**: not found anywhere in the captured text — no
  session-naming tool, no title-generation instruction, despite Grok
  Build's TUI presumably showing named sessions in its own interface
  (the `~/.grok/docs/user-guide/` reference confirms a real surrounding
  product with configuration/theming/etc., none of which is captured
  here). A capture gap, the same category this doc places most other
  "not found" sources in, not a confirmed design choice.
- **Reasoning/thinking display: absent from what's captured, worth
  flagging precisely because of Grok's public reputation.** xAI's
  consumer-facing Grok models are publicly known for a distinctive
  reasoning-transparency posture (visible chain-of-thought,
  "Think"/reasoning-trace UI), but nothing in this system prompt
  references a `reasoning_effort`-style parameter, a thinking-display
  toggle, or any instruction about how much of the model's own
  reasoning to surface — no `<think>`-style tool (contrast Devin), no
  native-block visibility config (contrast Codex's layered
  raw/summary/effort controls). Given this file is system-prompt-only
  (no UI/session-management code), this reads as a capture gap rather
  than a confirmed absence — the reasoning-display behavior Grok is
  known for publicly plausibly lives entirely in the client/rendering
  layer, never touching the system prompt at all, the same explanation
  this doc gives for several other sources' title-generation absences.
- **Narration**: `<output_efficiency>` — "Keep your text output brief
  and direct. Lead with the answer or action, not the reasoning. Skip
  filler words, preamble, and unnecessary transitions." Ordinary
  terseness/anti-preamble guidance, the same register as most sources'
  "communication style" material.
- **A structural, harness-enforced tool-call-before-narration rule —
  the most distinctive turn-output finding in this file**:
  `<task_completion_discipline>`'s rule 1, "Tool-call first, narration
  second": "Any past-tense or present-continuous prose describing an
  action ('I launched...', 'I'm now reading...', 'The subagent is
  working on...') MUST be paired with the corresponding tool call in
  the same assistant response. If you end a turn with such a sentence
  but no tool call, the action did not happen." This isn't ordinary
  prompted narration guidance (this doc's §3) — it specifically targets
  the failure mode of a model *claiming* an action narratively without
  actually invoking the tool that performs it, a distinct concern from
  how much or how little the model should say.
- **A second, harness-enforced completion-discipline mechanism worth
  cross-referencing into `agent-self-verification.md`'s §2** (see that
  section below): rule 4's "End-of-turn todo gate" is stated as
  mechanically enforced, not just requested: "The harness enforces
  this: if you try to end a turn with unbacked pending/in_progress
  todos, you will receive a system-reminder and be forced into another
  turn." This is a turn-output-shaping mechanism (it determines whether
  a content-only, tool-call-free assistant message is even a valid way
  to end a turn) as much as it is a verification gate.

## Self-verification and testing

See
[`agent-self-verification.md`](../../agent-self-verification.md) for
the cross-source comparison this feeds into. Mostly prompted-only (§7),
with one structural finding that's a genuinely new entry for §2
(deterministic, non-LLM completion gates).

- **`<making_code_changes>`'s core instruction is the familiar
  "green-run" idiom already documented recurring across this
  collection**: "Before reporting a task complete, verify it actually
  works: run the test, execute the script, check the output... If you
  can't verify (no test exists, can't run the code), say so explicitly
  rather than claiming success." Same register as Claude Code's "never
  fake a green result" and Cursor's 2025-09-03 "ensure a green
  test/build run" requirement — another data point for that phrase
  circulating across vendors rather than being one company's internal
  wording.
- **A new §2 candidate: an end-of-turn gate on the absence of tool
  calls, not on one specific completion-tool call.** Every existing §2
  entry in the master doc gates a *specific tool* (SWE-agent's `submit`
  wrapper, Roo Code's `attempt_completion` precondition check). Grok
  Build's "End-of-turn todo gate" is structurally different: it gates
  the act of ending a turn with **no tool call at all** while any todo
  is `pending`/`in_progress` and unbacked by a live background process —
  "the turn may NOT end -- advance the next pending todo with the
  appropriate tool call in this same response... you will receive a
  system-reminder and be forced into another turn." Three explicit
  exceptions are carved out (a live background subagent/command still
  running, a destructive operation awaiting authorization, or a hard
  external blocker with todos marked `cancelled`), each requiring the
  model to state the exception explicitly rather than just going quiet.
  This is a harness-level, code-enforced completion gate in the same
  family as Roo Code's `preventCompletionWithOpenTodos` setting, but
  broader in scope — it blocks silently ending the turn at all, not
  just one named completion tool.
- **A tool-schema-embedded bounded-retry threshold**: `update_goal`'s
  `blocked_reason` field — "Set only when truly stuck after 3+
  consecutive failed attempts" — mirrors Cursor's/Copilot Chat's
  three-try-then-ask idiom, but states the threshold inside a tool's
  JSON Schema `description` field rather than as free prose elsewhere
  in the prompt, closer in mechanism (if not in stakes) to Windsurf's
  schema-embedded `toolSummary` narration requirement than to any other
  bounded-retry instance in the self-verification doc.
- **`spawn_subagent`'s `codex:codex-rescue` type** (see Sub-agents
  above) reads as a second-opinion/deeper-investigation escalation path
  — "Use when stuck, wants a second implementation pass, or deeper
  root-cause investigation" — but isn't a verification judge in this
  doc's §3 sense (no scoring, no pass/fail verdict, no adversarial
  stance toward the first attempt is described); closer to a fresh
  attempt than a check on a completed one.
- **No SWE-bench-lineage echo, no separate-LLM-call judge, no hook
  system, no per-action mandate (contrast Jules)** found anywhere in
  the captured text.

## Permissions and approval

See
[`agent-permissions-approval.md`](../../agent-permissions-approval.md)
for the cross-source comparison this feeds into. Firmly in that doc's
§7 "enforcement lives in the harness, not the prompt" category — the
model is told a permission system exists and how to behave around it,
but is given no named modes, no risk-classification flag, and no
rule/policy mechanism of its own to reason about.

- **`<system_information>`'s framing is entirely procedural, not
  classificatory**: "Tools are executed in a user-selected permission
  mode. When you attempt to call a tool that is not automatically
  allowed by the user's permission mode or permission settings, the
  user will be prompted so that they can approve or deny the
  execution." No mode names are enumerated (contrast Gemini CLI's
  `plan → default → autoEdit → yolo` or Claude Code's six named modes),
  no boolean self-tag exists on any of the 26 tool schemas (contrast
  Windsurf's `SafeToAutoRun`, Replit's `is_dangerous`, Cline's
  `requires_approval` — Grok's `run_terminal_command` schema has no
  risk-adjacent field at all, only `command`/`description`/`timeout`/
  `background`).
- **An explicit, specific denial-handling instruction, not called out
  quite this way in the master doc's existing survey**: "If the user
  denies a tool you call, do not re-attempt the exact same tool call.
  Instead, think about why the user has denied the tool call and adjust
  your approach." Most sources checked for that doc are silent on
  *post-denial* behavior specifically (as opposed to pre-approval risk
  classification) — worth flagging as a modest, quotable addition to
  that gap rather than a major structural finding.
- **Hooks are named and explained directly to the model** — a partial
  counter-example to `agent-permissions-approval.md`'s §7 finding that
  Claude Code's own leaked `Prompt.txt` says nothing about its hook
  system to the model at all: "Users may configure 'hooks', shell
  commands that execute in response to events like tool calls, in
  settings. Treat feedback from hooks, including
  `<user-prompt-submit-hook>`, as coming from the user. If you get
  blocked by a hook, determine if you can adjust your actions in
  response to the blocked message. If not, ask the user to check their
  hooks configuration." Grok Build's prompt tells the model considerably
  more about the surrounding hook mechanism than Claude Code's own
  system-prompt text does on this specific point, even though neither
  source's *approval/permission-mode* machinery itself is described to
  the model.
- **Sandbox/isolation**: not described for the main session (see Tool
  surface above) — the only isolation concept present is
  `spawn_subagent`'s `capability_mode`/`isolation` pair, which scopes a
  *delegated* agent's tool access and working directory rather than
  describing any sandbox the primary agent itself runs inside.
- **No rule/policy definition mechanism, no scope/persistence tiers, no
  escalation behavior** found anywhere in the captured text — consistent
  with the harness-hides-the-mechanism pattern, not with a source that
  simply has none of this machinery at all.

## Git and version control

See [`agent-git-vcs.md`](../../agent-git-vcs.md) for the cross-source
comparison this feeds into. The git guidance itself is the clearest
instance of the Claude Code parity finding documented at the top of
this README — see that section for the full side-by-side quote. What's
git-specific beyond that shared text:

- **No commit-message trailer/attribution convention captured** —
  unlike Claude Code's evolving `Co-Authored-By`/session-URL trailer
  (`agent-git-vcs.md` §1), Grok's `run_terminal_command` description
  never mentions a HEREDOC template, a required trailer line, or any
  attribution format. The procedural git-safety guidance is copied
  near-verbatim (see above); the commit-message-formatting convention
  that sits right next to it in Claude Code's own Bash tool is not
  present here at all — a real difference in what got carried over, not
  just an extraction gap, since the surrounding text is otherwise so
  closely matched.
- **"Don't commit unless asked" is not stated anywhere in this file** —
  a genuine gap relative to this doc's finding that the rule is close
  to a universal convention across the collection (Claude Code,
  OpenCode, Copilot Chat, Gemini CLI, Crush, OpenHands, and others all
  state some version of it explicitly). Nothing in Grok's captured text
  either authorizes or restricts when the agent may commit — the
  general git-safety guidance (prefer new commits over amends, avoid
  destructive operations, don't skip hooks) is procedural, not a
  when-to-commit gate.
- **Worktree isolation exists, but scoped to delegation, not the main
  session** — `spawn_subagent`'s `isolation: "worktree"` parameter
  ("isolated git worktree," mutually exclusive with an explicit `cwd`)
  is the only worktree-creation mechanism found. This is a fourth data
  point for `agent-git-vcs.md` §4's "independently-converged worktree
  isolation" finding (alongside Gemini CLI, OpenCode, and Claude Code),
  but a structurally narrower one than any of those three: Gemini
  CLI's/OpenCode's/Claude Code's worktree tools are all directly
  callable by the primary agent for its own use ("work on multiple
  tasks at once... give each session its own copy"), while Grok's
  version is reachable only as a side effect of spawning a sub-agent —
  there's no equivalent of Claude Code's user-facing
  `EnterWorktreeTool`/`ExitWorktreeTool` pair for the main conversation
  itself.
- **No branch-naming convention, no PR/push workflow, no `gh` CLI
  guidance, no checkpoint/undo system** found anywhere in the captured
  text — beyond the general "avoid destructive operations" guidance
  already covered above, git-specific behavior stops at the
  commit-safety guidance quoted at the top of this README.

## Absences worth stating explicitly

- **No `/review` or diff-judge-style command** was found (contrast
  Codex CLI's `codex review`, OpenCode's `/review`) — self-checking is
  entirely the prompted-only pattern described above.
- **No content-based command escalation** (contrast Gemini CLI's
  redirection-triggers-re-ask rule, OpenCode's `doom_loop` repeat-call
  circuit breaker) — nothing resembling either was found in the
  captured tool schemas or prose.
- **No sandbox description for the primary agent's own execution
  environment** — see Permissions above; whatever sandboxing exists is
  either undocumented in this capture or scoped entirely to delegated
  sub-agents.
