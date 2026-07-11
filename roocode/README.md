# Roo Code

- **Type**: Coding agent (VS Code extension; fork of Cline)
- **License**: Apache-2.0
- **Source**: https://github.com/RooCodeInc/Roo-Code — **archived/read-only as
  of 2026-05-15** (project shut down)
- **Retrieved from**: `main` branch, `src/core/prompts/` (2026-07-10)

Roo Code (formerly "Roo Cline") diverged from Cline early on and developed
its own prompt structure: a `system.ts` entry point that assembles a system
prompt from many small, single-purpose section files, plus a mode system
(Code/Ask/Debug/Architect/etc.) that swaps in different role definitions.

## Files

- `system.ts` — assembles the full system prompt from the section files
  below, based on the active mode and enabled tools.
- `responses.ts` — templates for tool-result/error messages fed back to the
  model.
- `sections/capabilities.ts` — describes what the agent can do (tools,
  environment_details, MCP).
- `sections/custom-instructions.ts` — folds in user/workspace custom
  instructions, language preferences, and mode-specific rules.
- `sections/markdown-formatting.ts` — output formatting rules (clickable
  file/symbol links).
- `sections/modes.ts` — lists available modes and how to switch between them.
- `sections/objective.ts` — the "how to approach a task" framing.
- `sections/rules.ts` — operational rules and constraints.
- `sections/skills.ts` — skill-system instructions.
- `sections/system-info.ts` — injects OS/shell/cwd environment info.
- `sections/tool-use.ts` / `sections/tool-use-guidelines.ts` — tool-calling
  protocol and guidance on choosing/sequencing tools.

## Tool surface

**Correction**: this section originally covered only the prompt-assembly
section files (`system.ts` + `sections/*.ts`), which describe tool
*behavior* in prose but not the full tool *roster* — the actual tool
implementations live in `src/core/tools/`, never fetched originally.
Reading them directly (from the archived-but-still-browsable
`RooCodeInc/Roo-Code` repo, Apache-2.0) corrects three of four claims
below.

- **Shell**: `execute_command`, runs in the user's actual VS Code
  terminal — explicitly notes commands run in "a new terminal instance"
  each time and that interactive/long-running/background commands are
  supported with status updates, unlike Cline's more generic framing.
- **Search — corrected, real semantic search exists**: regex search
  ("view source code definitions," same lightweight symbol-listing as
  Cline's `list_code_definition_names`) *plus* a confirmed
  `CodebaseSearchTool.ts` (`codebase_search`) that's genuine
  embedding-based vector search — OpenAI embeddings, a Qdrant vector
  store, cosine-similarity-ranked results with file path/line range —
  not a grep wrapper despite the original doubt about whether it was
  "obviously surfaced." Backing service: `src/services/code-index/`.
- **Editing — corrected, six live tools not one pluggable strategy**:
  `write_to_file` (full overwrite) and `apply_diff` (pluggable
  `DiffStrategy`, SEARCH/REPLACE-block unified diff) are the two core,
  always-available editors; four more are opt-in "customTools" gated
  per-mode or by experiment flag — `edit`/`search_replace` (literal
  string match, exact-uniqueness or `replace_all`), `edit_file`
  (three-tier fallback matcher: exact → whitespace-tolerant regex →
  token-based regex), and `apply_patch` (an OpenAI/Codex-style V4A
  envelope patch format — `*** Add File:`/`*** Update File:` markers).
  `SearchAndReplaceTool.ts` is a deprecated re-export of `edit`, kept
  only for back-compat. Six live tools plus one dead shim, not "a
  pluggable `DiffStrategy`" — the evolution visibly tracks toward
  Claude-Code/Codex-style conventions layered on top of the original
  Cline-inherited `apply_diff`.
- **Code execution**: none beyond the shell.
- **Multimodal — corrected**: `GenerateImageTool.ts` (`generate_image`)
  calls OpenRouter's image-generation models for real text-to-image and
  image-to-image generation, writing the result to a workspace file.
  `UseMcpToolTool.ts`/`accessMcpResourceTool.ts` also extract image
  content (not just text) from MCP tool responses/resources.
- **Browser/web — corrected with important history, not a flat
  absence**: Roo Code *did* ship a Puppeteer-based `browser_action`-style
  tool ("Browser Use 2.0," added Nov 2025) and then **removed it
  entirely** in v3.48.0 (Feb 2026, per `CHANGELOG.md`) — three months
  before the repo was archived. `puppeteer-core`/
  `puppeteer-chromium-resolver` remain as orphaned `package.json`
  dependencies with no importing code left. "No browser tool" is
  accurate for the final snapshot, but stating it as an inherent
  architectural gap (as the original version of this doc did) is
  misleading — it's a removed feature, not a never-had one.
- **Sandbox/isolation**: none described — runs directly in the user's VS
  Code environment.
- **Extensibility**: MCP support (`use_mcp_tool`/`access_mcp_resource`,
  confirmed to handle image content too), plus its own **mode
  system** — different modes expose different *tool groups*, so the
  available tool surface itself, not just the persona, changes per mode
  (see `coding-agent-approaches.md` §13). Also `SkillTool.ts`
  (`skill`, mode-scoped skill lookup/execution) and
  `RunSlashCommandTool.ts` (`run_slash_command`, can auto-switch mode
  based on the resolved command's frontmatter) — both confirmed by
  direct reading, not just inferred from `SkillsManager`/
  `DiffStrategy` imports as before.

## Sub-agents

**Correction — this was wrong.** The original version of this section
concluded Roo Code has no sub-agent/delegation mechanism, based only on
the prompt-assembly files. It does: **`NewTaskTool.ts`
(`new_task`) plus a built-in "Orchestrator" mode together implement
real, tested, recursive task delegation** — publicly marketed as
"Boomerang Tasks." This is a different `new_task` from Cline's (which
really is just a user-facing context-handoff, no delegation at all —
see `../cline/README.md`); Roo Code's fork diverged on this specific
tool's actual behavior even though the name stayed the same.

- **Orchestrator is a built-in mode** (slug `orchestrator`, "🪃
  Orchestrator") with **no direct tool-execution groups of its own** —
  its entire job is decomposing work and delegating: "Use this mode for
  complex, multi-step projects that require coordination across
  different specialties... break down large tasks into subtasks, manage
  workflows, or coordinate work that spans multiple domains." Its
  custom instructions explicitly script the loop: decompose into
  subtasks via `new_task`, give each a clearly defined scope, require
  each subtask to finish via `attempt_completion`, track progress after
  each one, synthesize a final overview.
- **`new_task` protocol — stateful and addressable, but sequential, not
  concurrent**: calling it pushes a new `Task` onto a LIFO stack
  (`clineStack`) with `rootTask`/`parentTask` references; the parent is
  suspended (marked `status: "delegated"`, not destroyed) while the
  child becomes the sole focused task. Only the top of the stack is
  ever active — this is **effectively blocking** delegation (the parent
  cannot proceed until the child finishes) but implemented as a
  session/UI stack-switch, not an in-process function call the way
  Claude Code's `Task` tool is.
- **Result handoff is deferred, not synchronous**: `NewTaskTool.ts`
  deliberately does *not* return a result for the `new_task` call
  itself (a source comment explains why: an immediate result would be
  orphaned since history is already persisted by that point). When the
  child later calls `attempt_completion`, its summary gets injected
  back into the **parent's actual conversation history** as the
  deferred tool result for the original delegation call, and the parent
  reactivates. Functionally similar in spirit to Codex's/OpenCode's/
  OpenHands's addressable designs (a real, trackable parent/child
  relationship survives across turns — even across VS Code reloads, via
  `awaitingChildId` persisted in history), but single-threaded rather
  than parallel.
- **Recursion — confirmed supported and tested**: nested delegation
  (parent delegates to child, child delegates to grandchild) works and
  unwinds correctly, evidenced by test coverage for exactly this
  scenario. No stated depth limit was found.
- **No concurrency** — the single LIFO stack means Roo Code's model is
  strictly sequential/depth-first, a real architectural difference from
  Codex's/OpenHands's genuinely parallel addressable designs (see
  `agent-subagent-architectures.md` §2).
- **Mode-switching remains a separate, non-overlapping mechanism**:
  `SwitchModeTool.ts` (`switch_mode`) changes the active mode
  *within the same task* — no delegation, no new stack entry — confirming
  Roo Code has two genuinely distinct concepts (in-place persona/tool-set
  change vs. hierarchical task delegation) that happen to share the word
  "mode."

## Turn output: session titles

See [`agent-turn-output.md`](../agent-turn-output.md) for the
cross-source comparison this feeds into.

**Confirmed absence, mirroring Cline almost exactly** (same lineage) —
verified directly against the schema rather than inferred from a
keyword-search miss (this archived repo's code isn't indexed by
GitHub's cross-repo search at all, so files had to be fetched directly).
`historyItemSchema` (`packages/types/src/history.ts`) has `id`,
`rootTaskId`, `parentTaskId`, `task`, `tokensIn`/`tokensOut`,
`totalCost`, `workspace`, `mode`, `status`, and more — **no `title`
field anywhere**. The webview's task-history list renders straight from
this schema, so what looks like a "task list" is really just the raw
task text, not an AI-generated title. Same design answer as Cline: skip
the extra LLM call entirely.
