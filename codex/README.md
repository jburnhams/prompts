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
