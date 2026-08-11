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
| **OpenHands** | `github.com/OpenHands/software-agent-sdk` | `openhands-tools/openhands/tools/<tool>/definition.py` (schema + description) and `impl.py` (runtime). **The agent moved out of `All-Hands-AI/OpenHands`**, which is now the web/desktop app | `main` @ 2026-07-31 |

Already-stored captures used alongside the code (no fetch needed):
`leaked/claude-code/Tools.json` (16 tools, full JSON Schemas),
`leaked/claude-code/deferred-tools.md`, `leaked/manus/tools.json` (29 tools),
`leaked/windsurf/tools-wave-11.txt`, `leaked/grok-build/`,
`leaked/cursor/`, `leaked/github-copilot-cli/`.

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

Four harnesses surfaced by the Command Code write-up that this collection
has no coverage of at all: **Kilo Code** (`kilocode`, a Roo/Cline-lineage
fork — the nearest neighbour to sources already here), **Hermes**
(`hermes-agent`), **OpenClaw**, and **Command Code** itself (closed today;
the post says "we're also going open source soon"). Kilo Code and Hermes
are scored as having read-tool features this collection hasn't seen
elsewhere — Kilo's UTF-safe per-line clamp, Hermes's cross-agent
partial-view ledger, scored did-you-mean, and PDF coverage warning — which
makes them the highest-value additions of the four, and the ones whose
absence most weakens the §6/§7/§8 comparisons.
