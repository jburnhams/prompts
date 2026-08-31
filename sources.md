# Where the source came from

This collection stores *prompt text*. Several docs — most heavily
[`agent-tool-implementations.md`](./agent-tool-implementations.md) — are
grounded in the **implementation code** behind those prompts, which is not
stored here (too large, and mostly other people's licensed code).

This file records exactly where that code was read from, so a later pass can
re-fetch the same material in a couple of minutes instead of re-discovering
it. Paths drift — every repo below has been restructured at least once since
this collection started — so the "what changed" notes matter as much as the
paths.

## Fetch recipe

Every repo below is large; none needs to be cloned whole. Blobless + sparse
gets each one to a few MB:

```sh
git clone --depth 1 --filter=blob:none --sparse <url> <dir>
git -C <dir> sparse-checkout set <path> [<path> ...]
# a path that is a *file*, not a directory, needs --skip-checks:
git -C <dir> sparse-checkout set --skip-checks src/Tool.ts src/tools
```

If a path 404s, don't guess — list the tree from the packfile you already
have, which needs no extra network:

```sh
git -C <dir> ls-tree -r --name-only HEAD | grep -i tools/
```

`sparse-checkout disable` does **not** reliably repopulate a blobless clone
(observed on two repos here: it leaves you with root files only). Re-run
`sparse-checkout set` with corrected paths instead.

## Repos read, with the paths that matter

Commit SHAs are what was actually read on **2026-07-31**; they're recorded
so a future pass can diff rather than re-read.

| Source | Repo | Paths that matter | SHA read |
|---|---|---|---|
| **Claude Code** (leaked full source — see caveats below) | `github.com/tanbiralam/claude-code` | `src/Tool.ts` (the tool contract), `src/tools/<ToolName>Tool/` — each tool is a directory with `prompt.ts` (description text), `<Name>Tool.ts` (schema + `call` + result mapping), `UI.tsx`, and tool-specific helpers; `src/tools/BashTool/{bashSecurity,readOnlyValidation,pathValidation,sedValidation}.ts` | `main` @ read 2026-07-31 |
| **Codex CLI** | `github.com/openai/codex` | `codex-rs/core/src/tools/handlers/` — `*_spec.rs` files hold the wire schemas (`shell_spec.rs`, `apply_patch_spec.rs`, `tool_search_spec.rs`, `plan_spec.rs`), `apply_patch.lark` is the patch grammar; `codex-rs/core/src/tools/{registry,router,parallel}.rs` | `775fb21` |
| **Gemini CLI** | `github.com/google-gemini/gemini-cli` | `packages/core/src/tools/` — implementations; `packages/core/src/tools/definitions/` — **declarations are separate from implementations**: `base-declarations.ts` (name/param-name constants), `model-family-sets/{gemini-3,default-legacy}.ts` (per-model-family schemas + descriptions), `resolver.ts` | `d55e366` |
| **OpenCode** | `github.com/sst/opencode` | `packages/opencode/src/tool/` — `<tool>.ts` next to `<tool>.txt` (description text as a separate file), `registry.ts`, `tool.ts` | `19231fc` |
| **Crush** | `github.com/charmbracelet/crush` | `internal/agent/tools/` (**moved** from `internal/llm/tools/`) — `<tool>.go` next to `<tool>.md` or `<tool>.md.tpl` (description as a Go template with limits injected) | `d15f793` |
| **Zed** | `github.com/zed-industries/zed` | `crates/agent/src/tools/*_tool.rs` (**moved** from `crates/assistant_tools/`); the `AgentTool` trait is in `crates/agent/src/thread.rs` (~line 5067) | `98f39bf` |
| **Goose** | `github.com/block/goose` | `crates/goose/src/agents/platform_extensions/developer/` (**moved** from `crates/goose-mcp/src/developer/`) — `mod.rs` has the whole tool list | `eea5609` |
| **Cline** | `github.com/cline/cline` | `sdk/packages/core/src/extensions/tools/` — `schemas.ts` (Zod, incl. the tolerant union parsers), `definitions.ts`, `model-tool-routing.ts`, `presets.ts`, `executors/`. The VS Code extension is now `apps/vscode/` | `be8c16b` |
| **Google ADK, Java** (the intended build substrate — see [`agent-design/adk.md`](./agent-design/adk.md)) | `github.com/google/adk-java` | `core/src/main/java/com/google/adk/tools/mcp/` — `AbstractMcpTool.java` (`wrapCallResult`, the result conversion, and `declaration()`), `McpTool.java` (the retry policy), `McpToolset.java` (`toolFilter`, no name prefix); `agents/Callbacks.java` (`BeforeToolCallback`/`AfterToolCallback`); `tools/BaseToolset.java` (`getTools(ReadonlyContext)`, `processLlmRequest`) | `8049f7e` |
| **Google ADK, Python** (read first; **differs from Java** — kept for the comparison) | `github.com/google/adk-python` | `src/google/adk/tools/mcp_tool/` — `mcp_tool.py` (returns `response.model_dump()` of the whole `CallToolResult`, unlike Java's lossy `wrapCallResult`), `mcp_toolset.py` (`tool_filter`, optional `tool_name_prefix`). Docs live at `adk.dev` now, not `google.github.io/adk-docs` (301) | `c12a025` |
| **OMP** (Oh My Pi — read 2026-08-11; prompt text stored in [`omp/`](./omp)) | `github.com/can1357/oh-my-pi` | `docs/toolconv/*.md` — **eleven per-model-family tool-call dialect references** (anthropic, harmony, qwen3, gemma, glm-4.5, deepseek, kimi-k2, minimax, gemini, xml, plus the `pi-native` transport), the only documentation of the wire layer in this collection; `docs/tools/*.md` — 30 per-tool *implementation* references naming their own source files; `packages/hashline/src/` — `prompt.md`, `grammar.lark`, and the parser/apply/snapshot/recovery split; `packages/coding-agent/src/prompts/` — ~140 prompt templates, `system/system-prompt.md` being the main one; `packages/coding-agent/src/edit/` — `resolveEditMode()` and the four edit modes; `packages/agent/src/compaction/prompts/` — 16 compaction prompts; `packages/snapcompact/`, `packages/metaharness/`, `packages/typescript-edit-benchmark/` | `eb5e167` |
| **Kilo Code** (read 2026-08-11 — *targeted*, not a full pass) | `github.com/Kilo-Org/kilocode` | `packages/core/src/tool/read-filesystem.ts` — the whole read path in one file: `MAX_LINE_LENGTH`/`MAX_READ_LINES`/`MAX_READ_BYTES`, the streaming `TextDecoder("utf-8", { fatal: true })` loop, the `discard` flag that bounds a mega-line in memory, and the whole-line byte-budget composition written up in `agent-tool-implementations.md` §6c. Only the read tool was read; it is a Roo/Cline-lineage fork, so the rest is expected to be largely duplicative of sources already here | `64e5dd0` |
| **Hermes Agent** (Nous Research; read 2026-08-11) | `github.com/NousResearch/hermes-agent` | `evals/readtool/` — an A/B eval harness for read-tool engineering choices: `README.md` (nine hostile fixtures, metrics, rules of engagement), `fixtures.py`, `tasks.py`, `runner.py`, `results/SUMMARY.md` (the only per-feature ship/no-ship log with numbers found anywhere in this collection); `tools/` — ~60 tool modules incl. `browser_*`, `computer_use*`, `delegate_tool.py`, `code_execution_tool.py`; `agent/learn_prompt.py` (`/learn`, skill authoring by the live agent), `agent/system_prompt.py`, `agent/prompt_builder.py`; `skills/` + `optional-skills/`; `trajectory_compressor.py`, `toolsets.py`. MIT, Python-first | `ed5e17f` |
| **DeepSeek Harness** (`dsh`; read 2026-08-14 — prompt text and skills stored in [`deepseek-harness/`](./deepseek-harness)) | `github.com/deepseek-ai/deepseek-harness` | Nothing here holds a system prompt as a file — it is *assembled* from per-plugin sections, so read the **recorded snapshots** instead: `examples/acp-agent/tests/snapshots/*/system-prompt.expected.md` (17 variants; `text-turn` is the plain assembly, `code-mode-turn` the typed-TS one, `advanced-toolchain` the maximal 45 KB one) and `apps/web/tests/snapshots/`. `packages/core/system-prompt/` — the assembler (`section`/`context`/`tools`/`variable`/`assemble`, order bands, `toolOrder` with its one `'<unlisted-tools>'` rest entry, strict `{{var}}` interpolation). `packages/core/tools/` — the tool registry and Code Mode. `.agents/skills/` — 11 skills, incl. `dsh-code-review`, `dsh-prose-standard`, `dsh-trim-cot-leakage`. `.agents/notes/` — the Agent Note tree (`{lifecycle}/{class}/yyyy-mm-dd-topic.md`) and `notes/README.md`, its format spec. `docs/cookbook/maintaining-dsh-code-review.md` + `.agents/notes/proposed/process/2026-07-13-human-review-skill-maintenance.md` — the review-skill self-maintenance loop and its measured acceptance run. `docs/cookbook/adding-a-tool.md`, `docs/cookbook/adding-a-package.md` §4 (the Model Experience contract), `docs/AGENTS.md` (doc tiers + slop checklist), `docs/subsystems/` (44 pages, each with a generated `cordis-surface` region). `packages/guard/repeat-tool-reminder/` — the advisory loop-breaker. `scripts/verify-*.ts` — 30+ prose/doc gates, incl. `verify-package-readme-model-experience.ts`, `verify-agent-note-format.ts`, `verify-doc-budgets.ts`. MIT | `47f9438` |
| **OpenHands** | `github.com/OpenHands/software-agent-sdk` | `openhands-tools/openhands/tools/<tool>/definition.py` (schema + description) and `impl.py` (runtime). **The agent moved out of `All-Hands-AI/OpenHands`**, which is now the web/desktop app | `main` @ 2026-07-31 |
| **MCP Java SDK** (read 2026-08-21 — *targeted*, the version-ceiling question in `agent-design/adk.md` §0) | `github.com/modelcontextprotocol/java-sdk` | `mcp-core/src/main/java/io/modelcontextprotocol/spec/ProtocolVersions.java` — the whole finding in one file: four constants (`2024-11-05`, `2025-03-26`, `2025-06-18`, `2025-11-25`) and **no `MCP_2026_07_28`**, identical in `v1.1.2` and in `v2.0.1` (the latest release, 2026-08-19). Note the path moved between the 1.x and 2.x lines (`mcp/` vs `mcp-core/`), so `git ls-tree -r --name-only <tag> \| grep ProtocolVersion` before `git show`. Java is **Tier 2** (`modelcontextprotocol.io/community/sdk-tiers`): new protocol features "within 6 months", vs Tier 1's "before new spec version release" | `v1.1.2`, `v2.0.1` |
| **Google ADK, Java — the MCP pin** (read 2026-08-21; the same repo as the row above, re-read for one line) | `github.com/google/adk-java` | `pom.xml` — `<mcp.version>1.1.2</mcp.version>` and the `io.modelcontextprotocol.sdk:mcp` dependency block. A major version behind the SDK's own latest, which is the second half of the ceiling | `c1bda9c` (2026-08-19) |
| **OpenCode — MCP result projection** (read 2026-08-21 — *targeted*, a second pass on a repo already above) | `github.com/sst/opencode` | `packages/opencode/src/mcp/` — `catalog.ts` (`convertTool`: returns the whole `CallToolResult`, and synthesises a text block from `structuredContent` **only when `content` is empty**), `index.ts` (the client/catalog service, ~1,000 lines; `McpTool` is "an MCP tool in its native shape; consumers adapt it"). `packages/opencode/src/tool/code-mode.ts` — the Code Mode tool: `describeCatalog`/`toolTree` build a `server.tool` tree for a sandboxed program, and **`projectMcpResult`** is the named projection function (structuredContent-first, an `attachments` channel for image/audio/blob, a `[N files attached]` stub, `resource_link` kept as text). The two projections are deliberately opposite; see `agent-tool-result-transport.md` §3a | `ba72a6f` |
| **Roo Code** (read 2026-08-21 — *targeted*; prompt text stored in [`roocode/`](./roocode)) | `github.com/RooCodeInc/Roo-Code` | `src/core/tools/UseMcpToolTool.ts` — `processToolContent`, the whole MCP→model projection in 30 lines: text raw, embedded resource `JSON.stringify`d with `blob` destructured away, image routed to an `images[]` array, everything else `return ""`. `src/core/tools/accessMcpResourceTool.ts` (100 lines) is the `resources/read` side | `b867ec9` |
| **Cline — MCP result projection** (read 2026-08-21 — *targeted*, a second pass on a repo already above) | `github.com/cline/cline` | `sdk/packages/core/src/extensions/mcp/` — `types.ts` (`export type McpToolCallResult = unknown`), `tools.ts` (`createMcpTools` wraps each server tool with no MCP-aware flattening), `manager.ts`, `client.ts`. `sdk/packages/core/src/session/persisted-tool-result-content.ts` — the three-branch rule (string → as-is, array → as-is, **object → `JSON.stringify`**) that decides what an MCP result looks like in `ToolResultContent["content"]` (`sdk/packages/shared/src/llms/messages.ts`). Note the file is named for persistence; it is reached through `runtime/config/agent-message-codec.ts` | `fb60f9e` |
| **Codex — `AGENTS.md` loading** (read 2026-08-30 — *targeted*, the context-file-loading pass) | `github.com/openai/codex` | `codex-rs/core/src/agents_md.rs` — the whole discovery contract is a doc-comment at the top; `candidate_filenames` (`AGENTS.override.md` before `AGENTS.md`), `agents_md_paths` (root-marker search + `.buffered(256)` probes), the `project_doc_max_bytes` decrement loop and mid-file `data.truncate`, `AGENTS_MD_SEPARATOR` and `legacy_text`/`environment_labeled_text`. `codex-rs/core/src/agents_md_manager.rs` — the cache keyed on turn-environment selections + trust level (**not** mtime). `codex-rs/core/src/context/user_instructions.rs` — the `("# AGENTS.md instructions", "</INSTRUCTIONS>")` marker pair and `ContentItemKind("agents_md.instructions")`. `codex-rs/context-fragments/src/fragment.rs` — `matches_marked_text`, the case-insensitive prefix/suffix classifier those markers feed. `codex-rs/codex-home/src/instructions/mod.rs` — the `~/.codex` user tier. `codex-rs/config/src/config_toml.rs:73` (`DEFAULT_PROJECT_DOC_MAX_BYTES = 32 * 1024`), `config/src/project_root_markers.rs:5` (`[".git"]`) | `63d2138` |
| **Gemini CLI — `GEMINI.md` loading** (read 2026-08-30 — *targeted*) | `github.com/google-gemini/gemini-cli` | `packages/core/src/utils/memoryDiscovery.ts` (648 lines) — `deduplicatePathsByFileIdentity` (the `dev:ino` dedup), `findProjectRoot` (`.git` via `fs.access`, so a *file* `.git` counts), `findUpwardGeminiFiles`, `concatenateInstructions` (`--- Context from: … ---`), `loadJitSubdirectoryMemory`. `packages/core/src/utils/memoryImportProcessor.ts` (424) — `findImports` (hand-written scanner), `findCodeRegions`, tree vs flat formats, `validateImportPath` (realpath + fail-closed). `packages/core/src/tools/memoryTool.ts` — `DEFAULT_CONTEXT_FILENAME`/`PROJECT_MEMORY_INDEX_FILENAME`, `setGeminiMdFilename` taking a list. `packages/core/src/prompts/snippets.ts` — `renderUserMemory` (the `<loaded_context>` tier tags) and `mandateConflictResolution`. `packages/core/src/config/memory.ts` — `HierarchicalMemory`. `docs/cli/trusted-folders.md` — the seven features an untrusted folder disables, and `GEMINI_CLI_TRUST_WORKSPACE` | `0bd1d43` |
| **Claude Code — `CLAUDE.md` loading** (read 2026-08-30 — *targeted*; the leaked-source caveats below apply) | `github.com/tanbiralam/claude-code` | `src/utils/claudemd.ts` (1479 lines) — `getMemoryFiles` (the tier order and the nested-worktree skip for `anthropics/claude-code#29599`), `processMemoryFile` (`MAX_INCLUDE_DEPTH = 5`, external-include gating), `parseMemoryFileContent` / `stripHtmlComments` / `contentDiffersFromDisk` + `rawContent`, `extractIncludePathsFromTokens` (marked lexer, `gfm:false`), `TEXT_FILE_EXTENSIONS`, `isClaudeMdExcluded` / `resolveExcludePatterns`, `processConditionedMdRules` (the `paths:` frontmatter globs), `getClaudeMds` (`MEMORY_INSTRUCTION_PROMPT` and the per-tier description strings). `src/context.ts` — `getUserContext`, `CLAUDE_CODE_DISABLE_CLAUDE_MDS`, `--bare`. `src/utils/api.ts:449` — `prependUserContext`, the `<system-reminder>` first-user-message envelope. `src/utils/messages.ts:3097` — `wrapInSystemReminder`, and the `nested_memory` / `relevant_memories` attachment rendering. `src/utils/attachments.ts` — `memoryFilesToAttachments` | `6f6f12b` (2026-05-07) |
| **Goose — `.goosehints` loading** (read 2026-08-30 — *targeted*) | `github.com/block/goose` | `crates/goose/src/hints/load_hints.rs` (1039 lines) — `get_context_filenames`, `SubdirectoryHintTracker::record_tool_arguments` (the `shell_words::split` argv scan), `load_hint_files` (`### Global Hints` / `### Project Hints`), `build_gitignore`. `crates/goose/src/hints/import_files.rs` (1416) — `FILE_REFERENCE_REGEX`, `MAX_DEPTH = 3` / `MAX_REFERENCE_OPERATIONS = 64` / `MAX_EXPANDED_OUTPUT_BYTES = 1 MiB` / `MAX_GIT_POINTER_BYTES`, `ExpansionBudget`, `ImportBoundary`, and the degrade-to-literal-`@path` failure path | `8ae4e4b` |
| **Zed — rules-file loading** (read 2026-08-30 — *targeted*) | `github.com/zed-industries/zed` | `crates/prompt_store/src/prompts.rs:22` — `RULES_FILE_NAMES`, the nine-name cross-vendor list, plus `ProjectContext`/`WorktreeContext`/`RulesFileContext`. `crates/agent/src/agent.rs` — `RULES_FILE_REL_PATHS` and `load_worktree_rules_file` (first match via `.next()`, read through `project.open_buffer` → `Rope`, i.e. from the editor buffer not disk). `crates/agent/src/templates/system_prompt.hbs` (~line 247) — the `## User's Custom Instructions` block, the personal-vs-project precedence sentences, and the **six-backtick** fence with a triple-stache body | `399258f` |
| **Cline — rules loading** (read 2026-08-30 — *targeted*, a third pass on a repo already above) | `github.com/cline/cline` | `apps/vscode/src/core/context/instructions/user-instructions/` — `rule-helpers.ts` (467 lines; `getRuleFilesTotalContentWithMetadata`, `synchronizeRuleToggles`, `RULE_SOURCE_PREFIX`, the remote-rules tier), `rule-conditionals.ts` (153; `evaluatePathsConditional` and its fail-open/fail-closed policy comment, `extractPathLikeStrings`), `frontmatter.ts` (59; `stripUtf8Bom` for `cline/cline#12151`, fail-open YAML), `external-rules.ts` (the Cursor/Windsurf/AGENTS toggle sync) | `48d6385` |
| **Roo Code — custom-instruction loading** (read 2026-08-30 — the copy stored in [`roocode/`](./roocode) is the artifact) | `github.com/RooCodeInc/Roo-Code` | `src/core/prompts/sections/custom-instructions.ts` (548 lines) — `loadRuleFiles`, `loadAllAgentRulesFiles`, `loadAgentRulesFileFromDirectory`, `readTextFilesFromDirectory` (recursive symlink resolution, `MAX_DEPTH = 5`, sort-by-symlink-name/display-by-target), `shouldIncludeRuleFile` (the 20-pattern junk denylist), `addCustomInstructions` (the `==== USER'S CUSTOM INSTRUCTIONS` assembly order) | stored copy |
| **Crush — context-path loading** (read 2026-08-30 — *targeted*, a second pass on a repo already above) | `github.com/charmbracelet/crush` | `internal/config/config.go:28` — `defaultContextPaths`, the sixteen-entry list with three casings each of `crush.md`/`agents.md`. `internal/config/load.go:601` — the `append` + `slices.Sort` + `slices.Compact` that makes the casing enumeration work and makes precedence alphabetical. `internal/agent/prompt/prompt.go` — `loadContextFiles` (lowercased-path dedup), `processContextPath` (`WalkDir` on a directory entry, no extension filter), and the `text/template` import at line 12. Template: `internal/agent/templates/coder.md.tpl` (stored here as [`crush/coder.md.tpl`](./crush/coder.md.tpl)) — `<project_context>`/`<file path>`/`<user_preferences>` | `1ea2714` |
| **OpenHands — repo context and skills** (read 2026-08-30 — *targeted*, a second pass on a repo already above) | `github.com/OpenHands/software-agent-sdk` | `openhands-sdk/openhands/sdk/context/agent_context.py` — `load_project_skills` / `load_user_skills` / `load_public_skills` / `load_memory` / `disabled_skills` and their precedence contracts, written as Pydantic field descriptions. `openhands-sdk/openhands/sdk/context/prompts/sections/dynamic.py` — `RepoContextSection` and `MemoryContextSection`, the `<UNTRUSTED_CONTENT>` banners and the "coding style, project conventions, and documentation guidance only" scope limit. `openhands-sdk/openhands/sdk/context/prompts/section.py` — `CacheTier` (STATIC/DYNAMIC, mapped 1:1 onto the two `SystemPromptEvent` content blocks). `openhands-sdk/openhands/sdk/context/prompts/templates/skill_knowledge_info.j2` — the `<EXTRA_INFO>` keyword-match envelope | `9d143aa` |
| **Aider — the null case** (read 2026-08-30 — *targeted*) | `github.com/Aider-AI/aider` | `aider/website/docs/usage/conventions.md` — the whole design position in one page: no auto-discovery, `/read CONVENTIONS.md`, and the caching rationale. `aider/prompts/base_prompts.py:50` — `read_only_files_prefix` (stored here as [`aider/base_prompts.py`](./aider/base_prompts.py)) | stored copy + `main` @ 2026-08-30 |
| **Programmatic context channels — MCP instructions, skills, hooks, plugins** (read 2026-08-30 — *targeted*, the §12a pass; spans three repos already above) | `github.com/tanbiralam/claude-code`, `github.com/openai/codex`, `github.com/charmbracelet/crush` | Claude Code: `src/utils/mcpInstructionsDelta.ts` (130 lines — `getMcpInstructionsDelta` diffs connected servers against prior `mcp_instructions_delta` attachments in the message history, keyed on server **name** because `InitializeResult.instructions` is immutable per connection; `ClientSideInstruction`; the `DANGEROUS_uncachedSystemPromptSection` comment naming the cache-bust the delta exists to avoid) and `src/utils/messages.ts:4216` (the `# MCP Server Instructions` / disconnect-notice rendering). Codex: `codex-rs/core/src/context/` — `hook_additional_context.rs` and `plugin_instructions.rs` (role `developer`, **empty marker pair**, i.e. undelimited and unrecognizable), `apps_instructions.rs`, `available_plugins_instructions.rs`, `recommended_plugins_instructions.rs`; `codex-rs/ext/skills/src/fragments.rs` (`AvailableSkillsInstructions` role `developer` vs `SkillInstructions` role `user`); `codex-rs/ext/skills/src/dynamic_skill_selector/` — **eleven** competing selectors (fielded BM25, character n-gram, routing card, LRU and three hybrids, multi-query lexical, weighted lexical, RRF over lexical+character) behind a trait documented as running "in shadow mode on every turn" and "without changing the model-visible catalog". Crush: `internal/agent/templates/coder.md.tpl` `<skills_usage>` — skills loaded via the ordinary `View` tool against a `crush://skills/...` location, no skill tool | `6f6f12b`, `63d2138`, `1ea2714` |
| **Memory stores and memory tools** (read 2026-08-30 — *targeted*, the memory pass; spans five repos) | `github.com/openai/codex`, `github.com/google-gemini/gemini-cli`, `github.com/block/goose`, `github.com/tanbiralam/claude-code`, `github.com/cline/cline` | **Codex**: `codex-rs/ext/memories/src/tools/{mod,search,read,list,ad_hoc_note}.rs` — the four `memories.*` tool specs; `memory_function_tool::<I,O>` (the one builder that sets `output_schema` and wraps everything in `ToolSpec::Namespace`), the `AddAdHocNoteArgs` filename regex, and the twelve-variant `backend_error_to_function_call` match where only `Io` is fatal. `codex-rs/ext/memories/src/lib.rs` — every cap in one place (`DEFAULT_LIST_MAX_RESULTS = MAX_LIST_RESULTS = 2000`, search `200`, `DEFAULT_READ_MAX_TOKENS = 20_000`, `MEMORY_TOOL_DEVELOPER_INSTRUCTIONS_SUMMARY_TOKEN_LIMIT = 2500`). `codex-rs/ext/memories/templates/memories/read_path.md` (130 lines) — the read-path prompt: quick-pass budget, verify-or-declare rules, the `<oai-mem-citation>` format, and "only add one update note". `codex-rs/memories/README.md` — the pipeline contract, incl. **git-workspace dirtiness, not a DB watermark, deciding whether Phase 2 runs**. `codex-rs/memories/write/templates/memories/{stage_one_system,consolidation}.md` (569 + 880 lines) | `2832735` |
| ↳ same pass | `github.com/google-gemini/gemini-cli` | `packages/core/src/agents/skill-extraction-agent.ts` (490) — the `confucius` extraction agent in full: safety block, the canonical `.inbox/<kind>/extraction.patch` contract, the paired `MEMORY.md`-pointer hunk, the five-question STOP gate, high/medium/low confidence tiers, signal priority, and its seven-tool config (no shell, "intentionally unavailable in this background flow"). `packages/core/src/services/sessionSummaryUtils.ts` — `buildMemoryScratchpad` and the model-free session digest (`MAX_SCRATCHPAD_TOOLS = 6`, `MAX_SCRATCHPAD_PATHS = 4`, `MAX_WORKFLOW_SUMMARY_LENGTH = 160`, `VALIDATION_COMMAND_REGEX`). `packages/core/src/services/sessionScratchpadUtils.ts` — the shell-command sanitiser that reduces a command to its bare name. `packages/core/src/services/memoryService.ts` — eligibility gates and lock/throttle constants. `docs/cli/auto-memory.md` | `0bd1d43` |
| ↳ same pass | `github.com/block/goose` | `crates/goose-mcp/src/memory/mod.rs` (851) — the whole extension in one file: the four tool schemas, `MemoryServer::new()` building the injected instructions from **global memories only**, `get_memory_file`'s pre-I/O category validation (incl. Windows reserved device names), the append-only `# tags` + blank-line record format, and `retrieve`'s tag-keyed `HashMap::insert` (two entries with the same tag set silently collapse — `agent-tool-implementations.md` §12f) | `8ae4e4b` |
| ↳ same pass (leaked-source caveats below apply) | `github.com/tanbiralam/claude-code` | `src/memdir/memoryTypes.ts` (271) — the four-type taxonomy with per-type `<scope>` routing, the record-success-as-well-as-failure rule, the `**Why:**`/`**How to apply:**` body shape, the what-NOT-to-save list, and the read-side "Before recommending from memory" section — several carrying **eval results in code comments** (0/2 → 3/3; header wording and section position beating body text). `src/memdir/memdir.ts` — `MAX_ENTRYPOINT_LINES = 200` / `MAX_ENTRYPOINT_BYTES = 25_000`, the index-vs-memory rule, and the "Memory and other forms of persistence" section separating memory from plans and tasks. `src/memdir/findRelevantMemories.ts` — the Sonnet side-query retriever (≤5, JSON-schema output, filename allowlist, `alreadySurfaced`, recently-used-tools negative filter). `src/memdir/memoryAge.ts` — staleness rendered in words with its rationale. `src/services/teamMemorySync/` — `types.ts` (the org+repo API contract), `index.ts` (ETag/checksum sync, `MAX_FILE_SIZE_BYTES = 250_000`, `MAX_PUT_BODY_BYTES = 200_000`), `secretScanner.ts` (curated gitleaks subset), `teamMemSecretGuard.ts` (called from `FileWriteTool`/`FileEditTool` `validateInput`). `src/tools/AgentTool/agentMemory.ts` + `agentMemorySnapshot.ts` — per-sub-agent memory at three scopes, and snapshots as shippable starting memory | `6f6f12b` |
| ↳ same pass | `github.com/cline/cline` | `sdk/packages/core/src/extensions/tools/definitions.ts` — the nine-tool surface, confirming **no `new_rule` and no memory tool**; `apps/vscode/webview-ui/src/components/cline-rules/NewRuleRow.tsx` — what the capability became | `48d6385` |
| **DeepSeek Harness — the review-skill learning loop, re-read** (read 2026-08-30 — *targeted*, two weeks after the first pass at `47f9438`) | `github.com/deepseek-ai/deepseek-harness` | `.agents/notes/proposed/process/2026-07-13-human-review-skill-maintenance.md` (85 lines) — the full protocol: merge-commit-ancestry eligibility, why PR conversation comments are excluded, the `merge-base(B,T)→B` / `T→M` snapshot pair, batch-level fail-closed, CAS writes with unstaging rollback, the promote helper's blob-ID staleness check, and **"a singleton may qualify; recurrence is not required"**. `.agents/skills/dsh-code-review/SKILL.md` + `git log` on it — the one rule added since the first pass (item 7, locale-owned UI copy) arrived in `3c10f5d2d fix(client): route UI copy through locale`, i.e. **the implementation PR that established the convention**, not from the mining loop; `61703d224` and `a4be4b5e5` are the same shape. `packages/feedback/README.md` — the `/feedback` + per-message-rating group, and its contract that feedback is "a signal about the output, never input to it" | `cd5ef81` |

### Vision and multimodal pass (read 2026-08-30)

Twelve targeted reads behind [`agent-vision-multimodal.md`](./agent-vision-multimodal.md).
Sparse-checkout recipe as above; the paths below are the ones that matter.

| Source | Repo | Paths that matter | SHA read |
|---|---|---|---|
| **Codex CLI** | `github.com/openai/codex` | `codex-rs/core/src/tools/handlers/view_image{,_spec}.rs`; `codex-rs/core/src/image_preparation.rs` (resize limits, placeholders, `ImageResizeNotice`); `codex-rs/core/src/compact_remote_v2_images.rs` + `compact_remote_v2_image_budget_tests.rs` (atomic image truncation); `codex-rs/core/src/context_manager/history.rs` (`estimate_image_bytes`, `RESIZED_IMAGE_BYTES_ESTIMATE`); `codex-rs/core/src/context/node_repl_review_evidence.rs` (screenshots as reviewer evidence); `codex-rs/protocol/src/models.rs` ~1610–1830 (`<image name=… path=…>` sentinels, audio) | `88f7765` |
| **Cline** | `github.com/cline/cline` | **now a monorepo** — `sdk/packages/llms/src/providers/middleware/split-tool-images.ts` (the image-in-tool-result rewrite and the bug it fixes), `sdk/packages/shared/src/llms/media.ts` (budgets, placeholders, `GeneratedMedia`), `sdk/packages/shared/src/llms/ai-sdk-format.ts`, `apps/vscode/src/services/browser/BrowserSession.ts` | `48d6385` |
| **Gemini CLI** | `github.com/google-gemini/gemini-cli` | `packages/core/src/agents/browser/` in full — `browserAgentDefinition.ts` (the sub-agent prompt), `analyzeScreenshot.ts` (delegated computer-use model), `snapshotSuperseder.ts`, `automationOverlay.ts`, `inputBlocker.ts`, `modelAvailability.ts`, `browser-tools-manifest.json` | `0bd1d43` |
| **OpenHands** | `github.com/All-Hands-AI/agent-sdk` (**moved** — `All-Hands-AI/OpenHands` is now the app/frontend, and the agent is here) | `openhands-sdk/openhands/sdk/tool/builtins/vision_inspect.py`; `openhands-sdk/openhands/sdk/llm/utils/{image_resize,image_inline}.py`; `openhands-tools/openhands/tools/browser_use/definition.py`; `tests/sdk/context/prompts/snapshots/*browser-{on,off}*` | `9d143aa` |
| **Goose** | `github.com/block/goose` | `crates/goose/src/agents/platform_extensions/developer/image.rs` (the `read_image` tool with its `crop` rectangle) and `mod.rs` (tool registration) | `HEAD` @ read |
| **Crush** | `github.com/charmbracelet/crush` | `internal/agent/tools/view.go` (image branch, MIME sniffing), `internal/agent/tools/tools.go` (`SupportsImagesContextKey`), `internal/agent/agent.go` ~875 | `1ea2714` |
| **Zed** | `github.com/zed-industries/zed` | `crates/agent/src/tools/read_file_tool.rs` (image branch), `crates/agent/src/tools/context_server_registry.rs` (MCP image results), `crates/agent/src/thread.rs` ~1325 (ACP `PromptCapabilities.image`) and ~3640 (placeholder substitution) | `399258f` |
| **Roo Code** | `github.com/RooCodeInc/Roo-Code` | `src/api/transform/image-cleaning.ts`, `src/core/tools/GenerateImageTool.ts`, `src/core/mentions/resolveImageMentions.ts` | `b867ec9` |
| **OpenCode** | `github.com/sst/opencode` | `packages/opencode/src/mcp/browser.ts` (the negative result — it only opens a URL for OAuth), `packages/opencode/src/image/image.ts`, `packages/core/src/image/photon.ts` | `10765ff` |
| **SWE-agent** | `github.com/SWE-agent/SWE-agent` | `tools/image_tools/{config.yaml,bin/view_image}`, `tools/web_browser/config.yaml`, `sweagent/agent/history_processors.py` (`ImageParsingHistoryProcessor`), `config/default_mm_{with,no}_images.yaml` | `3ea751c` |
| **Claude Code** (leaked source — see caveat below) | `github.com/tanbiralam/claude-code` | `src/utils/imageResizer.ts` (880 lines: compression strategies, `createImageMetadataText`'s coordinate scale factor), `src/constants/apiLimits.ts`, `src/tools/FileReadTool/{imageProcessor,limits}.ts` | `6f6f12b` |
| **Playwright MCP** | `github.com/microsoft/playwright-mcp` | `README.md` (generated from the tool definitions by `update-readme.js`, so it is the authoritative tool list): `browser_snapshot` vs `browser_take_screenshot` wording, `--caps=vision`, `--snapshot-boxes` | `d0c29a5` |

Prompt-side material for the same doc came from already-stored captures:
`leaked/jules/DETAILS2.md` (the full tool JSON, incl.
`frontend_verification_complete`), `leaked/claude-code/claude-desktop-code.md`
(Claude-in-Chrome / Claude Preview / Playwright MCP tool lists and the
browser-safety block), `leaked/google-antigravity/`, `leaked/devin/Prompt.txt`,
`leaked/windsurf/tools-wave-11.txt`, `leaked/manus/tools.json`,
`leaked/same-dev/Prompt.txt`, `cline/system.ts`, `omp/tools/read.md` +
`omp/system-prompt.md`.

Already-stored captures used alongside the code (no fetch needed):
`leaked/claude-code/Tools.json` (16 tools, full JSON Schemas),
`leaked/claude-code/deferred-tools.md`, `leaked/manus/tools.json` (29 tools),
`leaked/windsurf/tools-wave-11.txt`, `leaked/grok-build/`,
`leaked/cursor/`, `leaked/github-copilot-cli/`.

## OpenClaw 2.0 (read 2026-08-31)

`github.com/openclaw/openclaw` at `5f714ef` (`main`, 2026-08-31). MIT.
Version `2026.8.1`, released as "OpenClaw 2.0"; state schema 15, agent
schema 19. 35,739 tracked files — a **full shallow clone** (`git clone
--depth 1`, ~647 MB checked out) was simpler than a sparse one here,
because the material is spread across `src/`, `extensions/`, `packages/`,
`docs/` and `.agents/`. Sparse alternative if disk matters:

```sh
git clone --depth 1 --filter=blob:none --sparse https://github.com/openclaw/openclaw.git openclaw
git -C openclaw sparse-checkout set src/agents src/skills/workshop \
  extensions/workboard extensions/memory-core packages/agent-core/src/harness \
  docs/concepts docs/tools docs/plugins docs/gateway .agents/skills/autoreview
```

Paths that matter, by topic:

| Topic | Path |
|---|---|
| System prompt renderer | `src/agents/system-prompt.ts` (1,605 lines), `system-prompt-contribution.ts`, `system-prompt-config.ts`, `prompt-surface.ts` |
| Prompt fragments | `src/agents/delegation-guidance.ts`, `promised-work-prompt.ts`, `bootstrap-prompt.ts`, `transcript-credential-safety.ts`, `skill-workshop-prompt.ts`, `watched-sessions-prompt.ts`, `progress-card-system-prompt.ts`, `gpt5-prompt-overlay.ts` |
| Prompt escaping | `src/agents/sanitize-for-prompt.ts` (`wrapPromptDataBlock`, `wrapUntrustedPromptDataBlock`) |
| Cache boundary | `packages/ai/src/utils/system-prompt-cache-boundary.ts` |
| Sub-agents | `src/agents/subagents/spawn/subagent-system-prompt.ts`, `subagents/registry/subagent-active-context.ts`, `subagents/announce/subagent-announce-output.ts`, `src/agents/tools/sessions-spawn-tool.ts`, `src/agents/tool-description-presets.ts` |
| Swarm | `src/agents/subagents/swarm/` (`swarm-scheduler.ts`, `swarm-collector.ts`, `swarm-output-schema.ts`), `src/agents/code-mode-swarm*.ts`, `docs/tools/swarm.md` |
| Workboard | `extensions/workboard/src/` — `dispatcher.ts` (worker prompt), `store-card-helpers.ts` (`buildWorkerContext`, diagnostics), `tools.ts`, `tools-orchestration.ts`, `sqlite-store.ts`; `docs/plugins/workboard.md`, `docs/cli/workboard.md` |
| File tools | `src/agents/sessions/tools/` — `read.ts`, `edit.ts`, `write.ts`, `grep.ts`, `find.ts`, `bash.ts`; ceilings in `packages/agent-core/src/harness/utils/truncate.ts` |
| exec | `src/agents/bash-tools.descriptions.ts` (`describeExecTool`), `bash-tools.exec-run.ts`, `exec-auto-reviewer.prompt.ts` |
| Compaction | `src/agents/agent-hooks/compaction-safeguard-quality.ts`, `compaction-instructions.ts`, `compaction-safeguard.ts`; `docs/concepts/compaction.md` |
| Memory / dreaming | `extensions/memory-core/src/` — `memory-tool-contract.ts`, `dreaming-consolidation.ts`, `dreaming-narrative.ts`; `src/plugins/memory-state.ts` |
| Self-learning | `src/skills/workshop/` — `experience-review-prompt.ts`, `learn-prompt.ts`, `history-scan-prompt.ts`, `skill-authoring-standards.ts` |
| Code review | `.agents/skills/autoreview/SKILL.md` + `scripts/autoreview` (6,168 lines of Python; `render_review_prompt`, `review_scope_policy`, `SCHEMA` at line 377) |
| Worktrees | `docs/concepts/managed-worktrees.md`; Workboard's use in `extensions/workboard/src/dispatcher.ts` |
| Roles / scopes | `docs/gateway/operator-scopes.md`, `docs/tools/permission-modes.md`, `docs/tools/exec-approvals.md` |
| Repo process corpus | `AGENTS.md` (361 lines), `.agents/skills/` (49 maintainer skills), `skills/` (52 bundled user skills), `taxonomy.yaml` (11,578 lines, not read) |

Committed prompt snapshots exist but were **not** used this pass:
`test/fixtures/agents/prompt-snapshots/codex-runtime-happy-path/` holds
Codex thread/turn params plus a reconstructed model-bound prompt layer
stack for Telegram-direct, Discord-group and heartbeat turns, regenerated
with `pnpm prompt:snapshots:gen` and drift-checked in CI. They cover the
*Codex* runtime only, not the OpenClaw-native prompt reproduced in
[`openclaw/system-prompt-main.md`](./openclaw/system-prompt-main.md), which
is reconstructed from the renderer. A future pass wanting byte-exact
evidence for the Codex path should start from those fixtures.

Not read: the ACP/ACPX bridge, `docs/specs/codex-supervision.md`, cloud
workers and placement, `src/plugin-sdk/`, the Control UI (`ui/`), the
native apps (`apps/`), and `taxonomy.yaml`.

## Caveat on the Claude Code source

`tanbiralam/claude-code` claims to be the full leaked TypeScript source
(exposed source map, 2026-03-31). [`leaked/claude-code/architecture-notes.md`](./leaked/claude-code/architecture-notes.md)
carries the full provenance discussion and the known-stub warning. Two
things learned this pass that are worth adding to that assessment:

- The tool directories read like genuine product code, not a reconstruction:
  they carry GrowthBook feature-flag lookups, `USER_TYPE === 'ant'`
  branches, dead-code-elimination `feature()` guards, and code comments
  citing internal PR numbers and reverted experiments (e.g. `FileReadTool/limits.ts`
  documenting experiment #21841 and why it was rolled back). That is very
  hard to fabricate and is consistent with the prompt-text corroboration
  already recorded in the architecture notes.
- The **security-sensitive areas are the ones that are stubbed**, so absence
  of logic there is not evidence of absence in the product. File-size
  measurements taken from this tree (used in
  `agent-tool-implementations.md` §2) should be read as lower bounds.

## Web references

- Anthropic, *Writing effective tools for agents* —
  https://www.anthropic.com/engineering/writing-tools-for-agents
  (tool consolidation, namespacing, `response_format` concise/detailed,
  the 72-vs-206-token Slack example, "no one-size-fits-all" on XML/JSON/
  Markdown, the 25,000-token Claude Code response cap).
- Anthropic, *Code execution with MCP* —
  https://www.anthropic.com/engineering/code-execution-with-mcp
  (150,000 → 2,000 tokens of tool definitions, 98.7%; intermediate results
  flowing through context twice).
- MCP specification, *Tools* —
  https://modelcontextprotocol.io/specification/2025-06-18/server/tools
  (`content` vs `structuredContent`, `outputSchema`, `isError`,
  `annotations`: `readOnlyHint`/`destructiveHint`/`idempotentHint`/
  `openWorldHint`, resource links, pagination).
- MCP specification, **`2026-07-28`** (the current revision; read
  2026-08-21) — https://modelcontextprotocol.io/specification/2026-07-28/server/tools
  and .../changelog. Supersedes the entry above for anything structural.
  The **"Stateful Tools"** section is the load-bearing new material for
  `agent-tool-result-transport.md` §7: protocol-level sessions and the
  `initialize` handshake are **removed**, and server-minted opaque handles
  passed as ordinary tool arguments are the sanctioned replacement, with
  four stated design rules (authorize on every call, keep handles opaque,
  put the retention policy in the creation tool's description, make expiry
  a recoverable tool-execution error). Also: `resultType` on every result,
  Multi Round-Trip Requests replacing server-initiated requests, tasks
  moved to an extension, Sampling/Roots/Logging **deprecated**,
  `ttlMs`/`cacheScope`, `icons`, `x-mcp-header`, and deterministic
  `tools/list` ordering justified by prompt-cache hit rates. The
  `structuredContent` backwards-compatibility SHOULD ("also return the
  serialized JSON in a TextContent block") survives unchanged — it is the
  duplication trap in §4.
- MCP, *tasks extension* (`io.modelcontextprotocol/tasks`) —
  https://modelcontextprotocol.io/extensions/tasks/overview (durable poll
  handles: `resultType: "task"`, `taskId`, TTL, `pollIntervalMs`,
  `tasks/get`/`tasks/update`/`tasks/cancel`; call-now/fetch-later).
- MCP, *SEP-1865: MCP Apps* —
  https://modelcontextprotocol.io/seps/1865-mcp-apps-interactive-user-interfaces-for-mcp
  (`ui://` HTML resources, `text/html;profile=mcp-app`, linked to a tool
  through `_meta`, rendered in a locked-down iframe with a CSP that blocks
  external requests; stable 2026-01-26; supported by Claude web/desktop,
  VS Code Insiders, Goose, Postman). The most mature "return this to the
  user" mechanism in the ecosystem — `agent-tool-result-transport.md` §8.
- **SEP-1624**, *Clarify `structuredContent` vs `content` usage guidance* —
  https://github.com/modelcontextprotocol/modelcontextprotocol/issues/1624
  (read 2026-08-21, **open**, not merged). The client-behaviour survey is
  the useful part: Cursor prefers `content`, VS Code prefers
  `structuredContent`, most clients ignore it entirely, some forward both.
  Worked example: 284 tokens structured vs 189 as prose. Companion:
  issue #1710 / discussion #1715, a proposed configurable response format
  (`text` / `structured` / `both`).
- **DesktopCommanderMCP issue #521** —
  https://github.com/wonderwhy-er/DesktopCommanderMCP/issues/521
  (read 2026-08-21). The best field measurement of base64-in-context found
  this pass: a 146 KB PNG returned with base64 in `structuredContent`
  alongside a native image block cost **106,356 tokens** through Claude
  Code vs **39,199** for the built-in read — 2.7× for identical visual
  output. Caveat: a bug report, single-case, numbers self-reported by the
  server's author, and the disagreement about whose fault it is (client
  stringifying vs server over-populating) is itself the finding.
- Anthropic, *Introducing advanced tool use on the Claude Developer
  Platform* — https://www.anthropic.com/engineering/advanced-tool-use
  (read 2026-08-21). Tool Search Tool with `defer_loading` (~72K → ~8.7K
  tokens of definitions); **programmatic tool calling**, where results
  process in a sandbox and "Claude only sees the final output" — 43,588 →
  27,297 tokens average, −37%, on complex research tasks; tool use
  examples, 72% → 90% on complex parameter handling. Vendor-reported,
  internal testing, no external replication.
- Cloudflare, *Code Mode: the better way to use MCP* —
  https://blog.cloudflare.com/code-mode/ (MCP schemas compiled to a
  documented TypeScript API, model writes a program, V8 isolate sandbox
  with no direct internet and MCP reached over bindings; the stated
  rationale — "the output of each tool call must feed into the LLM's
  neural network, just to be copied over to the inputs of the next call").
  The third independent arrival at the pattern, alongside Anthropic's and
  DeepSeek's; OpenCode's `code-mode.ts` is the fourth and is readable.
- Claude Code docs, *Connect Claude Code to tools via MCP* —
  https://code.claude.com/docs/en/mcp (read 2026-08-21). The only
  published per-tool cap negotiation found in any client:
  `_meta["anthropic/maxResultSizeChars"]` in a `tools/list` entry, ceiling
  500,000 chars, independent of `MAX_MCP_OUTPUT_TOKENS` (default 25,000,
  warning fixed at 10,000, image content exempt from the former but not
  the latter) — and the sentence that makes it an artifact system:
  oversized results are "persisted to disk and replaced with a file
  reference in the conversation." Also documents the root-level-combinator
  flattening for input schemas the Claude API won't accept.
- Google ADK docs, *Artifacts* — https://adk.dev/artifacts/ (read
  2026-08-21; note `google.github.io/adk-docs` 301s here). Named,
  **versioned** binary objects as `google.genai.types.Part`/`Blob`;
  session scope by default and a `user:` filename prefix for
  cross-session scope; `InMemoryArtifactService` and `GcsArtifactService`;
  and the property that matters for context budgets — artifact data does
  not automatically enter the LLM context, and `LoadArtifactsTool`
  appends a loaded artifact **to that request only**, not to history.
  The substrate for the artifact proposal in `agent-design/future.md`.
- Gemini API docs, *Function calling* —
  https://ai.google.dev/gemini-api/docs/function-calling (read
  2026-08-21). For Gemini 3 and later, a `functionResponse` may carry
  multimodal `parts` with `inlineData` — which is what dates the
  forward-looking half of `agent-design/adk.md` §2b.
- Command Code, *The Read Tool* —
  https://commandcode.ai/docs/harness-engineering/read-tool
  (Ahmad Awais, published on X 9 Aug 2026, long-form on the docs site;
  read 2026-08-11, page carries a changelog entry dated 10 Aug 2026).
  A capability-by-capability teardown of one tool across ten harnesses:
  the three-ceilings model (2,000 lines / 128 KB / 2,000 chars per line),
  a closed catalogue of recovery messages, the clamp→ledger→dedup
  deadlock, consume-on-hit dedup, seven-candidate Unicode filename
  retry, deferred chunk-boundary truncation, the JPEG quality ladder and
  downscale coordinate disclosure, notebook cells over 10K chars as `jq`
  pointers, `Number()`-not-`parseInt` coercion, and a device-path
  blocklist. Used throughout `agent-tool-implementations.md` §5d, §6b–§6d,
  §7b and §8b. **Read with three caveats, all disclosed by the page
  itself**: it is marketing for the product it benchmarks; the benchmark
  "was produced by AI with little human review, and should be read that
  way — we expect errors in it"; and the Claude Code column was **probed
  live rather than read** (four crafted files: a 3,000-line file, a
  3,900-character line, an empty file, a missing `AGENT.md` beside a real
  `AGENTS.md`), with "a dash means we looked and did not find it." Two of
  its Claude Code cells (unchanged-read dedup, did-you-mean) contradict
  this collection's own reading of the leaked source — see
  `agent-tool-implementations.md` §8b for why both readings are probably
  right. The other nine columns cite commits, read 29 July 2026: `pi`
  `027a584`, `opencode` `8cbea4f`, `codex` `d06c7ac`, `grok-build`
  `5da6962`, `cline` `c39c6d4`, `kilocode` `f844790`, `cloud` `8f32eff`,
  `openclaw` `18535626`, and `hermes-agent` `8359e760` (re-read 10 Aug
  2026) — useful for a future pass that wants to diff rather than
  re-derive, though the repos behind `hermes`, `kilocode`, `openclaw` and
  `cloud` are not identified by URL on the page.

## Live-session sources

Two things in this collection came from a Claude Code session's *own*
runtime rather than from a repo or a leak, and are labelled as such where
used: the live tool schemas visible to the running session (the
`agent-git-vcs.md` worktree finding, and this pass's confirmation of the
current `Read`/`Grep`/`Task` schemas and the `ToolSearch` deferred-tool
mechanism), and the MCP server `instructions` block that a connected server
injects into the system prompt.

## Candidates not yet read as code

Amp, Windsurf, Cursor, Devin, Jules, Antigravity (closed — prompt/tool-JSON
captures only, already in `leaked/`); Continue.dev, Plandex, Aider's
`coders/` (open, not yet needed); `github/github-mcp-server` (open — worth a
pass for its toolset/consolidation history, which is currently sourced only
from its in-band `instructions` block and tool list).

- Glukhov, Conti, Bogomolov & Golubev (JetBrains Research), *Diff-XYZ: A
  Benchmark for Evaluating Diff Understanding* —
  https://arxiv.org/abs/2510.12487 (read 2026-08-11 via the arXiv HTML
  rendering; dataset at
  `huggingface.co/datasets/JetBrains-Research/diff-xyz`). The one
  **independent** edit-format benchmark used in this collection, and the
  only source anywhere here that separates *generating* an edit from
  *reading* one: three tasks (apply, anti-apply, diff generation) over
  1,000 real edits from CommitPackFT, four formats (udiff, udiff-h,
  udiff-l, search-replace), with stripped EM plus parse/apply rates and
  F1 over added and deleted lines for generation. Numbers and the
  direction-split finding in `agent-tool-implementations.md` §4a. Caveats:
  the instances are commit-derived triples rather than realistic agent
  tasks, diff generation is scored by applying the generated diff so a
  valid-but-different diff can score 0, and the paper predates the
  harnesses compared elsewhere in this collection — it validates the
  *shape* of their claims, not their specific numbers. **The staleness
  caveat is the load-bearing one**: submitted 14 Oct 2025, roster
  GPT-4o/4o-mini, GPT-4.1/4.1-mini, Claude 4 Sonnet, Gemini 2.5 Flash and
  Qwen2.5-Coder 0.5B–32B — all superseded, on the one axis labs actively
  post-train for. The dataset is published, so re-running it beats citing
  it.
- Chi et al., *EDIT-Bench: Evaluating LLM Abilities to Perform Real-World
  Instructed Code Edits* — https://arxiv.org/abs/2511.04486 (Nov 2025;
  **abstract read 2026-08-11, full paper not yet read**). 540 problems
  built from instructions and code contexts collected in the wild from
  ~500 developers via a VS Code extension, with cursor position and
  highlighted code part of the problem; 40 models, only one above 60%
  pass@1. The finding used in `agent-tool-implementations.md` §4a2 is the
  harness-relevant one: contextual information alone swings success by up
  to 11 points. Same staleness caveat as above.
- *Edit, But Verify: An Empirical Audit of Instructed Code-Editing
  Benchmarks* — https://arxiv.org/abs/2604.05100 (April 2026; read
  2026-08-11). The most useful of the three and a corrective to both: of
  150+ code benchmarks only CanItEdit and EDIT-Bench evaluate instructed
  editing with human-authored instructions and test-based evaluation, and
  both are >90% Python with zero TypeScript/Java/C#/Go/Rust, invert the
  real domain mix, contain no documentation/testing/maintenance edits, and
  carry thin oracles (median 13 and 4 tests; 59% of EDIT-Bench's
  low-coverage suites cannot detect changes outside the edit region). Also
  11 of the 15 EDIT-Bench problems unsolved by all 40 models are benchmark
  artifacts, and 29% of its problems share a codebase with another. Its
  six desiderata are a usable specification for an internal eval. Read
  this before citing either benchmark.
- Command Code, *Tool Call Repairs* —
  https://commandcode.ai/docs/harness-engineering/tool-call-repairs
  (Ahmad Awais, 3 May 2026; read 2026-08-11). The published repair
  catalogue behind `agent-tool-implementations.md` §3h: the four
  container/nullability malformations that account for ~90% of "this open
  model can't do tool calls," their required application order, the
  validate-then-repair inversion and the silent-corruption bug that forced
  it, `pathString()` over `z.string()`, and relational defaults surfaced
  as notes rather than errors. Same caveats as the read-tool page below —
  vendor-authored, and the "DeepSeek V4 Pro beats Opus 4.7 6/10 on our
  internal evals" headline is an unreplicated internal claim. The failure
  taxonomy and the ordering constraint are mechanical and checkable; the
  eval result is not.
- Command Code, *Memory* and *Taste* —
  https://commandcode.ai/docs/memory · https://commandcode.ai/docs/taste
  (read 2026-08-11). Three additive `AGENTS.md` tiers with source-path
  headers and on-demand subdirectory loading; and taste profiles as
  push/pull/compose-able artifacts. Used in `agent-memory-learning.md` §9.
  The `taste-1` learning mechanism itself is undisclosed marketing copy
  and is recorded as a claim.
- Can Bölük, *The Minutiae of Tool-calling* —
  https://blog.can.ac/2026/08/03/the-minutiae-of-tool-calling/
  (3 Aug 2026; read 2026-08-11). The design rationale behind OMP's wire
  layer, by its author: how a tools array is actually rendered into the
  prompt (Harmony's `namespace functions` block), why a primitive
  parameter body needs no escaping while an array or object forces JSON
  into the same slot, and a five-interface experiment on one toy task
  where the *no-tools* emoji protocol beats every structured design on
  cost and beats the nested ones on reliability. Used in
  `agent-tool-implementations.md` §3g. Caveats: the scoreboard itself is
  images this pass could not extract, so only the numbers restated in the
  prose are quoted here (`exec` 7/10 and batch 9/10 on the two named
  models, E at 10/10, "2x less tokens"); it is one toy task on two models,
  and the author states the limits himself — post-training does favour the
  native channel, and he uses it. Links a reproduction setup and a
  dialect catalogue, both of which correspond to material in the OMP repo
  above. Two sibling posts not yet read: *Snapcompact: SoTA Compaction —
  Instant, Local, Free. Pick 3* (relevant to
  `agent-context-compaction.md`) and the Stencil piece below.
- Stencil, *Snapcompact: SoTA compaction — instant, local, free. Pick 3* —
  https://blog.can.ac/2026/06/10/snapcompact/
  (Can Bölük, 10 Jun 2026; read 2026-08-11). Context rendered into dense
  pixel-font bitmaps and carried as images. Used in
  `agent-context-compaction.md` §9 for three things: the SQuAD F1
  measurement of what prose compaction actually destroys (Gemini
  `UNREADABLE` 240/240, Opus 209/240 — "the summaries preserve what you
  were doing, not what you knew"), the 35–40 px²/character legibility
  cliff and the decode tax that offsets the input saving, and the
  vision-patch-alignment result (lock-on probability 0.39 → 1.00 on
  Qwen2.5-VL-7B). Caveats: SQuAD extractive QA is a retrieval proxy, not
  an agent-task proxy; the renderer was tuned against the four models
  benchmarked and the author states results are a property of each
  model's vision stack; vendor-run, though the eval harness, renderer,
  per-question records and white-box probes are open in the OMP repo
  above and reproduce for ~$35 plus a local GPU for the probes.
- Stencil, *We improved 15 LLMs at coding in one afternoon. Only the
  harness changed.* — https://stencil.so/blog/the-harness-problem
  (Can Bölük, 12 Feb 2026; read 2026-08-11). The hashline edit-format
  benchmark: 16 models × 3 edit formats × 180 tasks × 3 runs, fresh
  session each, fixtures generated by injecting invertible mutations into
  files from the React codebase, four tools (read, edit, write), ~$300 of
  inference. Headline numbers in `agent-tool-implementations.md` §4a.
  Caveats: **vendor-run and vendor-reported**, with no independent
  replication — though unusually, the harness, benchmark and per-run
  reports are open source in the OMP repo above, which is more than any
  other benchmark cited in this collection offers. Read the two regressions
  (DeepSeek V3.2, GPT-5.2 Codex) as the load-bearing part: they are why OMP
  keeps four edit modes rather than one. The post also carries vendor
  politics (Anthropic blocking OpenCode; the author's Gemini account
  disabled while benchmarking) and one unverified aside worth flagging
  rather than repeating — that Claude Code "leaks raw JSONL from sub-agent
  outputs." Note the date gap: the post describes a *per-line* 2–3
  character hash (`1:a3 |…`), while the August source implements a
  *per-file* four-hex snapshot tag (`[greet.py#A1B2]`) with plain line
  numbers — the "hashline v2" of its own results table. Where the two
  disagree, the code is what this collection documents.

**Hermes and Kilo Code have since been read** and are in the table above
(Hermes in full, Kilo's read tool only). One harness surfaced by the
Command Code write-up remained uncovered until 2026-08-31: **OpenClaw**,
now read in full (see the section above). **Command Code** itself is closed
today, though the post says "we're also going open source soon," which would
make the §6b–§8b material checkable against code rather than prose.

Benchmarks worth reading next: **CanItEdit** (the other half of the
audited pair, and the better-constructed one — near-complete whole-file
coverage with fail-before/pass-after validation), **Aider's** own
benchmark harness (the original format-swing result, and the only
long-running public leaderboard on this question), and **EDIT-Bench** in
full rather than by abstract. All three carry the same caveat the audit
establishes: they answer a narrower question than "which edit format
should this harness ship," and none is a substitute for an internal eval
on the languages and repositories a deployment actually touches.
