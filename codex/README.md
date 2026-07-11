# Codex CLI

- **Type**: Coding agent (OpenAI's terminal coding agent, Rust)
- **License**: Apache-2.0
- **Source**: https://github.com/openai/codex
- **Retrieved from**: `main` branch, `codex-rs/core/` (2026-07-10)

Codex CLI ships a separate prompt file per model, selected at runtime based
on which model is configured. There's no single "the" Codex system prompt —
these files are the current set for the GPT-5.x/Codex model family.

## Files

- `gpt_5_codex_prompt.md` — prompt for the original GPT-5-Codex model.
- `gpt_5_1_prompt.md` — prompt for GPT-5.1.
- `gpt_5_2_prompt.md` — prompt for GPT-5.2.
- `gpt-5.1-codex-max_prompt.md` — prompt for GPT-5.1-Codex-Max.
- `gpt-5.2-codex_prompt.md` — prompt for GPT-5.2-Codex.
- `prompt_with_apply_patch_instructions.md` — a variant that adds explicit
  instructions for the `apply_patch` file-editing tool format (used for
  models that need it spelled out rather than relying on native tool-calling
  conventions).

Not included: the repo's root `AGENTS.md` — that's contributor/build
instructions for working on the Codex codebase itself, not part of the
agent's system prompt.

## Tool surface

**Correction, same root cause as the Sub-agents section below**: this
subsection was originally built entirely from the per-model prompt
text, which — as with delegation — undersells what's actually there.
The bullets below are corrected/extended against `openai/codex`'s live
`codex-rs/core/src/tools/` tree (a full tool-registry module: `registry.rs`,
`router.rs`, `orchestrator.rs`, `approvals.rs`, `sandboxing.rs`,
`parallel.rs`, plus a `handlers/` directory of ~25 individual tool
implementations and a `code_mode/` subdirectory), not from the prompt
files stored in this folder.

- **Shell**: unnamed generic shell (`shell.rs`, `unified_exec.rs`), but
  with an explicit ripgrep preference: "prefer using `rg` or `rg
  --files`... because `rg` is much faster than alternatives like
  `grep`. (If the `rg` command is not found, then use alternatives.)" —
  the clearest, most explicit fast-search-tool endorsement in this
  collection.
- **Search**: no dedicated grep/glob *tool* beyond shell + `rg` was
  found even in the live registry — file discovery and code search
  genuinely do go through the shell here, corroborating the original
  prompt-text finding rather than correcting it. There is, however, a
  **`tool_search` meta-tool** (`tool_search.rs`) — BM25 full-text search
  over the *tool registry itself* (MCP tools and dynamically-loaded
  tools included), letting the model discover which tools exist by
  natural-language query rather than relying on a fixed list always
  being in context. Not a code-search tool; a tool-*discovery* tool.
- **Code execution — a real CodeAct-style mechanism, missed entirely by
  the prompt-text-only pass**: `tools/code_mode/` implements a
  `CodeModeService` (`execute()`/`wait()`/`terminate()`) that runs a
  model-generated script in a managed runtime, where the script can
  call other registered tools mid-execution via a nested
  `call_nested_tool()`-style mechanism (routed back through the main
  tool dispatcher via `delegate.rs` in the same directory) — the same
  "model writes a program that chains tool calls" pattern documented
  for Microsoft's CodeAct+Hyperlight elsewhere in this collection (see
  [`../codeact-hyperlight/README.md`](../codeact-hyperlight) and
  [`agent-tool-surfaces.md`](../agent-tool-surfaces.md) §3), just native
  to Codex rather than a separate framework layer. Self-recursion is
  explicitly blocked (`"{PUBLIC_TOOL_NAME} cannot invoke itself"`).
- **Editing**: `apply_patch` preferred for single-file edits, but
  explicitly *not* mandatory — "it is fine to explore other options...
  Do not use apply_patch for changes that are auto-generated... or when
  scripting is more efficient (such as search and replacing a string
  across a codebase)." A distinct `prompt_with_apply_patch_instructions.md`
  variant exists for models that need the format spelled out rather than
  relying on native tool-calling.
- **Planning**: a "Plan tool" (`plan.rs`), explicitly told to skip it
  for the "easiest 25%" of tasks and never use it for single-step plans
  — the only source in the collection with a quantified threshold for
  when *not* to plan. Also confirmed: separate context-budget tools
  (`new_context_window.rs`, `get_context_remaining.rs`) not mentioned
  anywhere in the prompt text.
- **Browser/web**: still not addressed in the prompt text, and no
  dedicated web-fetch/search tool handler was found in the live
  registry either — a rare case where the correction confirms the
  original absence rather than overturning it.
- **Multimodal — wrongly marked absent originally**: `view_image.rs`
  implements a real `view_image` tool — reads an image file, base64-encodes
  it into a data URL, and returns it as an `InputImage` content item,
  gated on the active model actually supporting image input ("`view_image`
  is not allowed because you do not support image inputs" otherwise).
- **User interaction**: `request_user_input.rs` and
  `request_permissions.rs` — dedicated tools for asking the user a
  clarifying question or requesting a specific permission grant, rather
  than folding either into free-text turns.
- **Extensibility — plugins, not previously documented at all**:
  `request_plugin_install.rs` and `list_available_plugins_to_install.rs`
  give the model tools to discover and request installation of plugins
  mid-conversation, plus `extension_tools.rs` and `dynamic.rs` for
  runtime-registered tool sets. No plugin system was visible from the
  prompt text alone.
- **Utility tools**: `current_time.rs`, `sleep.rs`,
  `wait_for_environment.rs` (block until a sandbox/environment is
  ready) — small but concrete capabilities absent from every prompt
  file.
- **Sandbox/isolation**: `sandboxing.rs` and `network_approval.rs`
  confirm sandboxing and network-access approval are real, dedicated
  subsystems in the tools module (consistent with — though not read in
  as much detail as — the `github-pr-bots/codex-review/` Action-level
  `sandbox: read-only` example and `openai/codex-action`'s documented
  credential-isolation strategy already noted here).

## Sub-agents

**Correction to an earlier version of this doc**: the files stored in
this folder are only the per-model *prompt text*, pulled from
`codex-rs/core/`. Codex CLI's actual sub-agent tooling lives in Rust
source elsewhere in the same repo that was never fetched into this
folder — reasoning from the prompt files alone wrongly suggested Codex
had no delegation mechanism. It has one, and it's structurally the most
distinctive in this collection: not a stateless one-shot tool call, but
a **persistent, addressable child thread** the parent can message,
interrupt, and wait on across multiple turns. The notes below are
sourced directly from reading `openai/codex`'s live `codex-rs/core/src/`
tree (Apache-2.0, current `main` branch) rather than from any file
stored in this folder — treat this section as pointing at the upstream
source, not as an extraction kept locally.

- **The tool is `spawn_agent`** (`codex-rs/core/src/tools/handlers/multi_agents_spec.rs`,
  with a parallel v2 rewrite in `multi_agents_v2/`): "Spawn a sub-agent
  for a well-scoped task. Returns the spawned agent id plus the
  user-facing nickname when available." Takes a task message, an
  `agent_type`/role, a `fork_context` flag (v1: bool; v2: `fork_turns`
  enum — `"none"|"all"|N`) to fork the parent's conversation history
  into the child, and optional model/reasoning/service-tier overrides.
- **Companion tools make it a stateful family, not a single call**:
  `send_input` (message an existing agent by id, with an `interrupt`
  flag to redirect it immediately), `wait_agent` (block on one or more
  agent ids reaching a final status, with a timeout), and `close_agent`
  (tear down an agent and its open descendants). This is a materially
  different protocol shape from every other source in this collection's
  sub-agent survey (see `agent-subagent-architectures.md` §2) — those
  are single blocking tool-call-and-report; Codex's is spawn-then-poll/
  message/wait as separate, repeatable tool calls against a still-live
  child.
- **Approvals are routed to the parent, not auto-resolved by the
  child**: `codex_delegate.rs` streams the sub-agent's events back
  continuously and forwards its exec/patch/permission/user-input
  approval requests up to the orchestrating session rather than letting
  the child resolve them alone — the parent stays in the approval loop
  even though it doesn't see every intermediate model turn.
- **Role-based prompt/config layers**, not a full captured sub-agent
  system prompt: `agent/role.rs` defines role presets applied at spawn
  time via `agent_type` — `"default"`, `"explorer"` ("fast and
  authoritative... answer well-scoped codebase questions... can be
  parallelized"), and `"worker"` ("execution and production work:
  feature implementation, bug fixes, refactoring") — loaded through the
  same config machinery as `config.toml` and able to override
  model/reasoning/service-tier. This is a real behavioral persona
  layer, closer to Claude Code's typed `subagent_type` registry than to
  a single generic delegate, but the underlying prompt text for each
  role wasn't read in full, so it doesn't join Copilot Chat/Crush/
  Goose in the "fully captured sub-agent system prompt" category.
- **Persistent parent/child graph, not a flat pool**: relationships are
  stored as parent→child spawn edges in a dedicated `agent-graph-store`
  crate ("storage-neutral parent/child topology for thread-spawned
  agents"), and each session's `AgentControl` coordinator (one per root
  conversation tree) enforces a capacity/depth limit on how many agents
  can be live at once, with reservation-and-rollback semantics during
  spawn. Deep nesting (a spawned agent spawning its own children)
  appears to be allowed and only capacity/depth-limited, rather than
  banned outright the way Goose's sub-agent prompt states "cannot spawn
  additional subagents."
- **A batch/parallel convenience built on the same primitive**:
  `agent_jobs.rs` implements a CSV-driven "map a sub-agent over rows of
  a CSV and collect JSON results" pattern (`spawn_agents_on_csv`), with
  an explicit numeric concurrency cap (default 16, max 64) and
  DB-persisted recovery — one of the more concrete concurrency-limit
  numbers found anywhere in this collection's sub-agent survey (compare
  Gemini CLI's/Amp's file-conflict-aware *rules*, which are qualitative
  rather than a hard concurrency number).
- **Not the same thing as "Codex Cloud"**: the `cloud-tasks`/
  `cloud-tasks-client` crates are OpenAI's existing async/background
  cloud-execution product (one discrete cloud coding run, optionally
  with multiple alternative "attempts" of the *same* task) — unrelated
  to `spawn_agent`. Worth flagging since the naming ("task," "agent")
  invites confusion between three genuinely different concepts in this
  codebase: turn-execution tasks (`tasks/`, e.g. `CompactTask`/
  `RegularTask`), cloud background tasks (`cloud-tasks/`), and
  spawned-agent jobs (`agent_jobs.rs`).
- **`agents_md.rs`/`agents_md_manager.rs` are unrelated** — pure
  `AGENTS.md` project-instruction-file loading (the cross-tool
  convention also seen elsewhere in this collection), nothing to do
  with AI agent orchestration despite the name.
- **`external-agent-migration` imports *other tools'* sub-agent
  configs**, it doesn't bridge to live external agent runtimes — its
  source constant is literally `"claude"`; it converts another tool's
  MCP-server config, hooks, and custom sub-agent/slash-command
  definitions into Codex's own TOML config format. `external-agent-sessions`
  is the companion piece for importing past *conversation transcripts*
  from other tools, not live agents.

## Compaction

Sourced from the live upstream repo, not files stored in this folder —
see [`agent-context-compaction.md`](../agent-context-compaction.md) for
the cross-source comparison this feeds into.

- **Two model-callable tools, one of which is misleadingly named**:
  `new_context_window` (from the general tool-surface audit above)
  returns the message "A new context window will start without
  summarizing conversation history" — but that's only true if an
  internal `TokenBudget` feature flag is enabled. Otherwise, calling
  it just sets a flag that routes into the **same real-summarization
  pipeline** as automatic compaction — the tool's own returned message
  describes behavior that isn't actually what happens by default, a
  real documentation/behavior mismatch in the source itself.
  `get_context_remaining` is purely informational (no side effects).
- **A genuinely separate automatic compaction system**, not model-invoked
  at all, with three interchangeable backends chosen at runtime: local
  model-driven summarization, server-side compaction via the model
  provider's own API, or (when `TokenBudget` is enabled) a bare
  no-summary reset that just reinstalls initial context. Which backend
  runs is a deployment/feature-flag choice, not something the model
  picks.
- **Proactive by design, not reactive-on-error**: triggers are checked
  pre-turn and mid-turn against a token-budget threshold — plus two
  non-token triggers worth noting as genuinely distinctive: compacting
  because the *model was swapped mid-thread* (its prompt-compatibility
  hash changed) or because of a *model downshift* to a smaller context
  window. An actual `ContextWindowExceeded` API error is **not**
  auto-compacted — it's propagated as a hard failure; the only place
  that error triggers recovery is inside the compaction task's own
  drain loop, if compaction's *own* request overflows.
- **The compaction prompt is minimal free text**, not a structured
  template: "You are performing a CONTEXT CHECKPOINT COMPACTION. Create
  a handoff summary for another LLM that will resume the task,"
  followed by four loosely bulleted asks (progress/decisions,
  important context, next steps, critical references). One prompt for
  all model families — no per-model variants the way this collection's
  Copilot Chat material has. User-overridable via `config.compact_prompt`.
  Notably more minimal than Claude Code's 9-section structured template
  or Copilot Chat's 8-numbered-section one (see
  `agent-context-compaction.md`).
- **Sandbox/approval/personality context is explicitly preserved across
  a compaction event** — a world-state snapshot and turn-context item
  are reinjected into the replacement history by design, not by
  accident.
- **Hooks can veto compaction**: `PreCompact`/`PostCompact` hooks exist
  and can return a `Stopped` outcome that aborts the turn — a public
  extension point, analogous to Claude Code's own PreCompact hook.
- **Sub-agents (`spawn_agent`, documented above) compact
  independently** — each spawned agent is a separate session/thread
  with its own compaction state; no cross-agent compaction coordination
  was found.
- **Concrete numeric thresholds**: default auto-compact trigger at
  **90% of the resolved context window** (configurable), with a
  scope setting for counting the full context vs. only a sliding-window
  suffix; up to **20,000 tokens** of trailing raw user messages
  preserved verbatim (not summarized) in the compacted history; four
  distinct trigger reasons (`UserRequested`, `ContextLimit`,
  `ModelDownshift`, `CompHashChanged`) tracked explicitly in analytics.
  No fixed target compression ratio was found — the summarization
  prompt doesn't ask for a specific output length.

## Turn output: session titles and reasoning display

See [`agent-turn-output.md`](../agent-turn-output.md) for the
cross-source comparison this feeds into.

- **Session/task title generation: a confirmed absence on the client**,
  not just unchecked. `task.title` (for the separate Codex Cloud
  product) is deserialized straight from the backend API response — no
  generation code exists in `codex-rs/cloud-tasks/`; if an LLM produces
  it, that happens server-side, invisible to this repo. The local
  session-resume list (`codex-rs/tui/src/resume_picker.rs`) falls back
  to a raw server-provided preview string, not a generated title. The
  `/title` slash command is unrelated to conversation naming entirely —
  it only configures which telemetry fields (model, token counts,
  session id) appear in the terminal's window-title bar.
- **Reasoning: the richest configuration surface surveyed**, and the
  only one to explicitly target OpenAI's Responses-API reasoning
  *summaries* by design rather than raw chain-of-thought — consistent
  with OpenAI's own API not exposing raw CoT at all. `reasoning_effort`
  (how much the model reasons) and `model_reasoning_summary` (an enum —
  `Auto`/`Concise`/`Detailed`/`None`, `None` explicitly documented as
  disabling summaries outright) are two independently configurable
  axes, both overridable per-role and via CLI flag.
- **Reasoning summaries are hidden from the live interactive pane by
  default, shown only in the exported transcript** — a `transcript_only`
  flag on the TUI's `ReasoningSummaryCell` component means
  `display_lines()` (the live pane) returns empty while
  `transcript_lines()` (full transcript export) still renders it. Two
  further independent toggles layer on top: `hide_agent_reasoning`
  (suppresses summary display entirely, for users "only interested in
  the final agent responses") and `show_raw_agent_reasoning` (a
  separate raw-content event, gated independently from the summary
  display) — Codex draws its own raw-vs-summary distinction on top of
  OpenAI's API-level summary-not-CoT design, not just passing the API's
  choice straight through.
- **Live keybinding to adjust reasoning effort mid-session**
  (`chatwidget/reasoning_shortcuts.rs`) — the user can raise or lower
  how much the model reasons without restarting the conversation.
- **Narration is a separate, prompted mechanism**: both captured
  per-model prompts state "Communicate with the user by streaming
  thinking & responses, and by making & updating plans" — ordinary
  visible prose governed by the system prompt, unrelated to the native
  `reasoning_effort`/summary machinery above (the word "thinking" here
  is used loosely, not referring to the API mechanism).

## Self-verification and testing

See [`agent-self-verification.md`](../agent-self-verification.md) for
the cross-source comparison this feeds into.

- **`ReviewTask` is a general "review any diff" utility, not a
  self-check gate — a distinction worth being precise about.**
  Confirmed by reading `codex-rs/core/src/tasks/review.rs` and
  `codex-rs/core/src/session/review.rs`: it spawns a fully separate,
  nested one-shot Codex conversation (own system prompt — a dedicated
  `codex-rs/prompts/templates/review/rubric.md`, own approval policy
  forced to "never," own optional model override) that can target
  **uncommitted changes, a base-branch diff, an arbitrary commit SHA,
  or free-text instructions** — four interchangeable modes, only one of
  which (`UncommittedChanges`) naturally lines up with "review my own
  recent work." The review prompt itself is unconditional: "You are
  acting as a reviewer for a proposed code change made by **another
  engineer**" — used even when reviewing the CLI's own uncommitted
  diff. Output is structured JSON (`findings[]` with priority/confidence/
  location, plus an overall correctness verdict), spliced back into the
  *parent* conversation's history once the review sub-thread completes.
- **Always explicitly invoked, never auto-chained**: the `codex review`
  CLI subcommand (which requires one of the four target flags — no
  implicit default), the TUI's `/review` popup, and the app-server's
  programmatic review-request path all converge on the same
  `ReviewTask` pipeline, but nothing in the normal turn-completion or
  `apply_patch` flow calls it automatically. A search for
  `review_on_submit`/`self_review`/`request_review`-style
  completion-gating patterns (the SWE-agent/Roo Code style) turned up
  nothing — Codex has no code-level "you must review before finishing"
  gate.
- **The actual self-verification instruction lives entirely in the
  system prompt, not in code**: a "Validating your work" section
  ("If the codebase has tests or the ability to build or run, consider
  using them to verify changes once your work is complete") whose
  proactivity is itself gated by the *approval mode* — told to
  proactively test in fully-autonomous (`never`-approval) mode, told to
  hold off until the user is ready to finalize in interactive modes.
  Purely instructional, not enforced by any completion gate.
- **A second, separate route into review-like behavior**: the
  Codex-specific prompt variants additionally tell the *main* agent to
  switch into a "code review mindset" whenever a user asks for a
  "review" in normal chat — bypassing the `ReviewTask` subsystem
  entirely and staying in the regular agent loop.

## Permissions and approval

See [`agent-permissions-approval.md`](../agent-permissions-approval.md)
for the cross-source comparison this feeds into. Sourced from a live
clone of `openai/codex` (`codex-rs/`) — the single richest permission
architecture found across every source checked for this doc: not one
mechanism but **five cooperating subsystems** (a static command-safety
classifier, a Starlark rule engine, an LLM-based auto-reviewer, a
real OS-level sandbox, and a network proxy), several of them coupled
to each other by explicit design.

- **Four modes** (`AskForApproval`, not a continuous scale):
  `UnlessTrusted` (only a hardcoded read-only safelist auto-runs),
  `OnRequest` (default — "the model decides when to ask"), `Granular`
  (five independent sub-toggles: sandbox-escalation prompts,
  execpolicy `prompt` rules, skill-script execution, the
  `request_permissions` tool, MCP elicitations — each can be
  independently auto-rejected without ever reaching the user), and
  `Never` (no prompts; failures return straight to the model). The
  true "YOLO" switch, `--dangerously-bypass-approvals-and-sandbox`,
  force-sets `AskForApproval::Never` **and** full sandbox bypass
  together — approval-bypass and sandbox-bypass are one coupled flag,
  not two independent knobs.
- **Two-layer risk classification — a real, code-confirmed fast/slow
  split**:
  - **Fast, static**: a hardcoded read-only-command allowlist (`cat`,
    `ls`, `grep`, `pwd`, `whoami`, ...) with per-command carve-outs
    (`base64` is safe unless `-o/--output` is passed; `find` is unsafe
    with exec/delete/write flags), plus an inverse dangerous-pattern
    heuristic that parses `git`'s global options to find the real
    subcommand. Compound `bash -lc "cmd1 && cmd2"` invocations are
    recursively split and each sub-command checked independently.
  - **Slow, LLM-based — "Guardian"**: only active when explicitly opted
    into (`approvals_reviewer = auto_review`) and only for `OnRequest`/
    `Granular` modes. A dedicated, separate, faster/cheaper model
    (`codex-auto-review`, low reasoning effort where supported — even
    overridable per-provider) reviews the exact planned action against
    a written risk-taxonomy document (`guardian/policy.md` — sections
    on data exfiltration, credential probing, persistent security
    weakening, destructive git actions) and returns a structured
    `{risk_level: Low/Medium/High/Critical, user_authorization,
    outcome: Allow/Deny, rationale}` verdict. Runs in a **locked-down,
    cached sub-session** — "pinned to a read-only sandbox with
    `approval_policy = never`... intentionally runs without inherited
    exec-policy rules" — with a hard 90-second timeout and an explicit
    **fail-closed** guarantee: timeout, parse error, or session error
    all resolve to rejection, never silent allow. A circuit breaker
    (3 consecutive denials, or 10 in a trailing 50-entry window) force-
    interrupts the turn back to the human rather than letting the
    agent grind against auto-denial forever. Guardian gates shell
    exec, MCP tool calls, *and* network access — not just shell
    commands.
- **Rule/policy mechanism — Starlark, not TOML/YAML/JSON**: `.rules`
  files are real Starlark (Python-like) programs with `prefix_rule()`
  declarations carrying `pattern`/`decision` (`allow`/`prompt`/
  `forbidden`)/`justification`/unit-test-style `match`/`not_match`
  assertions, loaded from built-in/user/project config layers and
  merged strictest-wins. `codex execpolicy check --rules path.rules
  git status` is a real CLI subcommand for testing rules offline
  before deploying them.
- **Five persistence tiers, not four** (correcting/extending an
  earlier partial finding): one-off `Approved`;
  `ApprovedExecpolicyAmendment` (written directly into
  `codex_home/rules/default.rules`, survives process restart, applies
  to future sessions); `ApprovedForSession` (in-memory cache, this
  session only); `NetworkPolicyAmendment` (the same permanent-write
  pattern, scoped per-host for network egress); plus `TimedOut` and
  `Abort` as distinct non-approval outcomes (`TimedOut` is
  Guardian-specific — the review simply didn't finish; `Abort` stops
  the whole turn, distinct from an ordinary denial). Which decisions
  are even offered to the user is itself dynamic — an amendment option
  only appears when a concrete rule/prefix was actually derivable from
  the request.
- **Escalation reaches inside a running sandboxed process, not just
  the top-level command string**: a patched shell forwards every
  individual `exec()` call to a server over a Unix socket mid-execution,
  which can independently `Run`, `Escalate` (out of the sandbox),
  re-sandbox, or `Deny` that one syscall — approval isn't only a
  pre-flight gate on the command as typed; a compound command already
  running inside the sandbox can have one of its internal `exec()`
  calls separately intercepted and judged.
- **Sandbox/isolation — real, platform-specific, and explicitly
  coupled to approval, not a substitute for it**: Landlock (Linux),
  Seatbelt Profile Language (macOS), and a native Windows sandbox back
  a `SandboxPolicy` enum (`DangerFullAccess`/`ReadOnly`/
  `ExternalSandbox`/`WorkspaceWrite`). Even under `AskForApproval::Never`,
  an unsandboxed dangerous command stays `Forbidden` unless the sandbox
  is *explicitly* disabled too — a deliberate defense-in-depth design,
  confirmed by a source comment explaining even a patch provably
  confined to writable paths still runs sandboxed "to prevent hard
  link exploitation."
- **A dedicated network-layer firewall, not just an LLM judgment
  call**: a separate `codex_network_proxy` crate intercepts outbound
  traffic and evaluates per-host policy before allowing egress
  (`NetworkPolicyDecider`), with immediate vs. deferred approval modes
  for network calls that occur inside an already-running sandboxed
  process — Guardian and the static policy both sit in front of this
  layer, and accepted decisions persist via the same
  `NetworkPolicyAmendment` mechanism as file-system rules.

## Git and version control

See [`agent-git-vcs.md`](../agent-git-vcs.md) for the cross-source
comparison this feeds into. Sourced from a fresh live clone of
`openai/codex` (`codex-rs/`). Codex is the outlier of the three
CLI-shaped sources checked in depth for this doc (alongside OpenCode
and Gemini CLI): it has **no user-facing checkpoint/undo system and no
worktree-creation mechanism at all** — the richest git-adjacent
findings here are a not-yet-executed markdown-directive protocol and a
maintainer-only PR-babysitting skill, not features shipped to ordinary
users.

- **Commit/branch defaults split by prompt family, with a real content
  gap between them**: non-`codex`-suffixed model prompts state "Do not
  `git commit` your changes or create new git branches unless
  explicitly requested"; the `*-codex` variants drop that line
  entirely and instead carry a "dirty git worktree" section (working-
  tree-cleanliness sense, not isolated worktrees) — "never revert
  changes you did not make," "do not amend a commit unless explicitly
  requested," "**NEVER** use destructive commands like `git reset
  --hard` or `git checkout --` unless specifically requested or
  approved." The codex-suffixed prompts never explicitly restate "no
  commit without asking."
- **No user-facing checkpoint/undo system for the user's actual repo.**
  A genuine git-based "baseline diff" mechanism does exist
  (`git-utils/src/baseline.rs`, replacing `.git` with a fresh
  one-commit baseline via `gix` and diffing against it) but its only
  confirmed caller is Codex's own memory-writing subsystem
  (`memories/write/src/workspace.rs`), diffing `MEMORY.md`/
  `rollout_summaries/` against their last "init" — git used purely as
  a resettable diff primitive for Codex's *own* files, explicitly
  documented as such: "a lightweight baseline API for internal
  directories that use git only as a resettable diff mechanism." The
  internal baseline commit itself carries a real `Co-authored-by:
  Codex <noreply@openai.com>` trailer, but on that internal bookkeeping
  repo, never the user's project.
- **No worktree-creation mechanism** — Codex is worktree-*aware*, never
  worktree-*creating*, a real structural contrast with OpenCode's and
  Gemini CLI's dedicated worktree services (see those sources' Git
  sections). `spawn_agent`'s tool schema has no `cwd`/directory
  parameter at all — sub-agents share the parent's working directory,
  relying on prompt-level conflict avoidance rather than filesystem
  isolation. Two places acknowledge worktrees exist without creating
  them: `get_git_repo_root`'s own doc comment admits it "does **not**
  detect *work-trees* created with `git worktree add`... pass
  `--allow-no-git-exec`" to work around it; and hook-config resolution
  explicitly handles "is (1) part of a git repo, (2) a git worktree,
  or (3) just using the cwd" as three distinct cases when the user is
  already inside a linked worktree. Codex Cloud's background tasks
  don't create client-side worktrees either — `resolve_git_ref` only
  picks which branch/ref to send to the backend; actual isolation
  happens server-side, outside this repo.
- **A structurally novel, not-yet-wired-up mechanism**: the model can
  emit inline "git action directives" in its own markdown response —
  `::git-stage{cwd="..."}`, `::git-commit{...}`, `::git-create-branch{...
  branch="..."}`, `::git-push{...}`, `::git-create-pr{... branch="..."
  url="..." isDraft="true"}` — parsed by `git_action_directives.rs` and
  stripped from what the user sees. **Only `CreateBranch` is actually
  acted on** (re-syncing the tracked branch name for the UI thread);
  `Stage`/`Commit`/`Push`/`CreatePr` are parsed but have no confirmed
  call site that executes them anywhere in this codebase — real git
  mutation happens via the model's own shell calls instead. Worth
  flagging as a known-unknown (plausibly wired up in a separate "Codex
  App" client not present in this repo) rather than a verified
  feature.
- **No built-in `gh pr create` call site in the product code at all**
  — PR creation, when it happens, is the model shelling out to `gh`
  itself. Self-review before/around a PR is handled entirely by the
  separate, always-explicit `ReviewTask` subsystem (already documented
  under Self-verification above) — never auto-chained after a commit
  or PR-creation step.
- **A maintainer-only dogfooding skill bundle** (`.codex/skills/`, for
  working on the Codex repo itself, not shipped to all users) is
  nonetheless the richest git-workflow content found in the whole
  codebase: `babysit-pr/SKILL.md` polls `gh pr checks`, classifies CI
  failures as branch-related (auto-fix) vs. flaky (bounded retry),
  restricts itself to published review comments from trusted authors,
  and enforces a strict mutation policy (never close/reopen PRs, never
  toggle draft status, never reply to other humans' threads without
  confirmation, always prefixes bot replies with `[codex]`).
  `codex-pr-body/SKILL.md` gives PR-description-writing guidance
  (explain why before what, preserve existing images verbatim, strip
  abandoned approaches, use GitHub permalinks) with explicit support
  for Sapling-SCM stacked PRs.
- **A rich, best-effort git-info surface for host/IDE integrations**:
  an `app-server` RPC (`git_diff_to_remote`) and per-thread tracked
  git metadata (sha/branch/origin URL), plus a TUI status-line probe
  that resolves the open PR for the current branch via `gh pr view`/
  `gh api` — explicitly designed to degrade to "absent optional
  metadata" rather than a visible error on failure.
