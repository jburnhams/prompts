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

- **Shell**: unnamed generic shell, but with an explicit ripgrep
  preference: "prefer using `rg` or `rg --files`... because `rg` is much
  faster than alternatives like `grep`. (If the `rg` command is not
  found, then use alternatives.)" — the clearest, most explicit
  fast-search-tool endorsement in this collection.
- **Search**: no dedicated search tool named beyond shell + `rg` — file
  discovery and code search both go through the shell.
- **Code execution**: none beyond the shell (scripts run via shell
  invocation, same as any other command).
- **Editing**: `apply_patch` preferred for single-file edits, but
  explicitly *not* mandatory — "it is fine to explore other options...
  Do not use apply_patch for changes that are auto-generated... or when
  scripting is more efficient (such as search and replacing a string
  across a codebase)." A distinct `prompt_with_apply_patch_instructions.md`
  variant exists for models that need the format spelled out rather than
  relying on native tool-calling.
- **Planning**: a "Plan tool," explicitly told to skip it for the
  "easiest 25%" of tasks and never use it for single-step plans — the
  only source in the collection with a quantified threshold for when
  *not* to plan.
- **Browser/web**: not addressed in this prompt.
- **Multimodal**: not addressed.
- **Sandbox/isolation**: not specified here — see
  [`../github-pr-bots/codex-review/`](../github-pr-bots/codex-review) for
  a `sandbox: read-only` example from the Action wiring, and
  `openai/codex-action`'s documented credential-isolation strategy.

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
