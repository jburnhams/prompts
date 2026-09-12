<!-- Written from openai/codex `main` @ ee6814b (2026-09-12), reading
     codex-rs/models-manager/{models.json,src/{lib,manager,cache,model_info}.rs}
     and codex-rs/core/src/context/world_state/. Analysis, not a captured
     prompt; the captured text lives in the sibling files this one names. -->

# The model catalog: Codex's prompt corpus is served data, not source

Until mid-2026 Codex CLI selected a per-model system prompt from a small set
of `.md` files compiled into `codex-rs/core` — the five files this folder
still stores. That is no longer how the prompt is assembled, and the change
is large enough that most of the rest of this folder's original findings had
to be re-derived rather than updated.

The prompt corpus now lives in a **model catalog**: a JSON document, one
entry per model, where each entry carries its own instructions and its own
per-subsystem prompt fragments as string fields. `codex-rs/models-manager/`
owns it.

## Where the catalog comes from

`OpenAiModelsManager` is documented as "backed by bundled models, cache, and
`/models`", in that order of fallback and the reverse order of authority:

- **`/models`** — the live catalog, fetched from the backend for the
  authenticated account.
- **`models_cache.json`** under `~/.codex`, with
  `DEFAULT_MODEL_CACHE_TTL = 300` seconds. `refresh_ttl` revalidates at
  half-life (`cache_ttl / 2`).
- **`models.json`**, 294 KB, `include_str!`-ed into the binary by
  `bundled_models_response()`. Nine models. This is the offline fallback and
  the only copy that can be read from source, which is what the sibling
  capture files here are extracted from.

So the deployed system prompt is a **cached remote resource with a
five-minute TTL**. Nothing else in this collection serves its agent
instructions over the wire on that cadence; the closest comparisons are
harnesses that fetch *configuration* remotely and assemble the prompt
locally from compiled-in text. Here the text itself is the payload.

Two consequences worth stating plainly, because they change what a prompt
capture from this repo means:

1. **The bundled catalog is a floor, not the truth.** A captured
   `instructions_template` is what a client would use if it could not reach
   the backend, pinned to the commit it was read at. The prompt an actual
   session ran on may differ and leaves no trace in the repository.
2. **Prompt changes ship without a client release.** `minimal_client_version`
   on each entry (`"0.153.0"` for `gpt-6-astra`) is the gate in the other
   direction: the catalog can withhold a model from clients too old to
   honour its settings, but a prompt edit inside an already-supported entry
   reaches every running client within the TTL.

## What an entry holds

`gpt-6-astra` — the GPT-6 entry, `priority: 1`, `visibility: "list"` — is the
fullest. Its non-prompt fields are the runtime contract:

| Field | Value | What it decides |
| --- | --- | --- |
| `tool_mode` | `code_mode_only` | The entire tool surface is one freeform `exec` tool. See the Tool surface section of `README.md`. |
| `shell_type` | `unified_exec` | Which shell handler is registered. |
| `multi_agent_version` | `v2` | Selects the mailbox-style delegation toolset over v1's spawn-and-wait. |
| `multi_agent_reasoning_effort` | `xhigh` | Reasoning effort for spawned children, independent of the parent's. |
| `context_window` / `max_context_window` | 272,000 / 872,000 | Default and ceiling. |
| `truncation_policy` | `{mode: tokens, limit: 10000}` | Per-tool-result cap. |
| `apply_patch_tool_type` | `freeform` | Grammar-constrained rather than JSON-argument patching. |
| `input_modalities` | `["text", "image"]` | No audio in, despite the code-mode runtime having an `audio()` helper. |
| `default_reasoning_level` | `low` | With six levels offered, up to `ultra` — "Maximum reasoning with automatic task delegation", the only level whose description names a *behaviour* rather than a depth. |
| `node_repl_auto_review_required` | `true` | Computer/browser use cannot run without the guardian reviewer, whatever the user's approval policy says. |
| `include_skills_usage_instructions` | `false` | …and the same for apps and plugins: this model's own `instructions_template` already covers them, so the generic blocks are suppressed to avoid duplication. |
| `comp_hash` | `"3000"` | Prompt-compatibility hash. A mid-thread model swap that changes it forces a compaction. |
| `experimental_supported_tools` | `["send_user_message_async", "clock"]` | The two tools persistent mode depends on, gated per model. |

## The prompt fields

`model_messages` is where the corpus lives. For `gpt-6-astra`:

| Key | Size | Captured in |
| --- | --- | --- |
| `instructions_template` | 21,261 chars | [`gpt-6-astra_instructions.md`](./gpt-6-astra_instructions.md) |
| `persistent_instructions` | 5,737 chars | [`gpt-6-astra_persistent-mode.md`](./gpt-6-astra_persistent-mode.md) |
| `confirmation_policies` | 2 × 11,229 chars | [`gpt-6-astra_confirmation-policy.md`](./gpt-6-astra_confirmation-policy.md) |
| `guardian_v2` | 9 fields, one prompt | [`guardian-v2-classifier.md`](./guardian-v2-classifier.md) |
| `token_budget` | 7 fields, three prompts | [`gpt-6-astra_token-budget.md`](./gpt-6-astra_token-budget.md) |
| `multi_agent` | `role.root`, `role.subagent` | [`gpt-6-astra_multi-agent-roles.md`](./gpt-6-astra_multi-agent-roles.md) |
| `collaboration_modes` | `default` set, `plan` null | [`gpt-6-astra_collaboration-mode-default.md`](./gpt-6-astra_collaboration-mode-default.md) |
| `approvals`, `auto_review` | one string each set | [`gpt-6-astra_auto-review-messages.md`](./gpt-6-astra_auto-review-messages.md) |
| `permissions`, `tools`, `instructions_variables` | null | falls back to the compiled-in templates |

The null entries are the interesting half of the design. Every subsystem
that can be prompted has a catalog slot; a model that says nothing gets the
in-repo template. `gpt-5.6-sol`, `gpt-5.6-terra` and `gpt-5.6-luna` share one
byte-identical 17,730-char `instructions_template` and differ only in
`multi_agent_version` and whether `auto_review` is overridden — three
"models" that are one prompt plus a routing difference. So the catalog is
doing two jobs at once: per-model prompt authorship, and per-model
*subsystem configuration expressed as prompt text*.

**A defect visible in the captured data**: `confirmation_policies` has two
keys, `browser_use` and `computer_use`, and for `gpt-6-astra` the two strings
are byte-identical at 11,229 characters each. Whatever the distinction was
meant to be, the shipped catalog does not draw it, and a model that loads
both pays ~22 KB for one policy. This folder stores one copy and says so.

## The world state: the prompt is a change stream

The catalog supplies the text; `codex-rs/core/src/context/world_state/`
decides when any of it is *emitted*. Sixteen named sections
(`ModelInstructionsState`, `AgentsMdState`, `PermissionsState`,
`CompactPermissionsState`, `CollaborationModeState`, `MultiAgentModeState`,
`MultiAgentUsageHintState`, `PersistentModeState`, `ToolsState`,
`PluginsInstructionsState`, `AppsInstructionsState`, `EnvironmentsState`,
`EnvironmentsInstructionsState`, `ContextWindowGuidanceState`,
`RealtimeState`, `ManagedDeveloperInstructionsState`) each implement
`render_diff(previous)` against a SHA-1'd JSON snapshot of their own prior
value, and **return `None` when nothing changed**.

The system prompt is therefore not a preamble that is re-sent each turn. It
is an append-only stream of state transitions, and a section that has been
stable for forty turns contributes nothing after the first. Two things fall
out of that:

- **Model instructions are themselves a diffable section.** A mid-thread
  model switch emits the new model's instructions as a delta, with the
  previous model's slug in hand — so the harness knows what the model was
  told before, not just what it is being told now.
- **A policy flip emits a correction, not just a replacement.**
  `ext/git-attribution`'s section is the clearest instance: turning
  attribution off renders *"Ignore any earlier instructions requiring Codex
  attribution and do not add it"*, and turning it on renders *"Ignore any
  earlier instructions disabling Codex attribution; this policy reflects the
  current workspace."* Because the earlier instruction is still sitting in
  the transcript, the new fragment has to revoke it by name. That is the
  cost of a diffed prompt made explicit, and it is a cost most harnesses
  avoid by paying the re-render instead.

Each section also carries a `with_legacy_matcher` — a predicate that
recognises its own older rendered text in an existing history — so a session
resumed under a newer client can identify and supersede fragments written by
the previous format. The prompt format is versioned *in the transcript*.
