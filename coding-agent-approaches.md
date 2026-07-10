# Approaches to full coding-agent system prompts

The companion to [`code-review-approaches.md`](./code-review-approaches.md),
prompted by that doc's finding that every review tool checked runs on top
of a full general-purpose coding-agent system prompt rather than a lean
one — which makes the *content* of those full prompts worth comparing
directly. This covers the actual persona/tool/behavior prompt that
governs a coding agent end to end, not just its review-specific
add-ons.

Deeper focus on the five the request called out — **OpenHands, OpenCode,
Codex, Claude (Code), Cursor** — with the rest of the collection's
full-agent prompts included for contrast. All claims below are re-read
from the files in this repo at the time of writing, not from memory.

## Sources covered

| Source | Product | License / status |
|---|---|---|
| [`openhands/`](./openhands) | OpenHands | MIT |
| [`opencode/`](./opencode) | OpenCode | MIT |
| [`codex/`](./codex) | Codex CLI | Apache-2.0 |
| [`leaked/claude-code/`](./leaked/claude-code) | Claude Code | **Leaked**, not official |
| [`leaked/cursor/`](./leaked/cursor) | Cursor | **Leaked**, not official |
| [`cline/`](./cline) | Cline | Apache-2.0 |
| [`roocode/`](./roocode) | Roo Code | Apache-2.0 |
| [`aider/`](./aider) | Aider | Apache-2.0 |
| [`swe-agent/`](./swe-agent) | SWE-agent | MIT |
| [`goose/`](./goose) | Goose | Apache-2.0 |
| [`crush/`](./crush) | Crush | FSL-1.1-MIT |
| [`bolt/`](./bolt) | Bolt.new | MIT |
| [`gemini-cli/`](./gemini-cli) | Gemini CLI | Apache-2.0 |
| [`copilot-chat/`](./copilot-chat) | GitHub Copilot Chat | MIT |
| [`leaked/windsurf/`](./leaked/windsurf) | Windsurf (Cascade) | **Leaked**, not official |

Note on the two "leaked" leaders: `claude-code` and `cursor` don't
officially publish their prompts, so these are third-party extractions
(see each folder's README for provenance) — treat their exact wording as
lower-confidence than the officially-published sources, though the
overall *shape* they show (terseness mandates, TodoWrite, etc.) is
corroborated by public documentation and by how similar tools that copy
their conventions behave.

---

## 1. Identity & self-referential framing

How the prompt introduces the agent, and what happens when the user asks
"are you X" or "can you do Y".

| Approach | Sources |
|---|---|
| One-line identity + explicit instruction to answer questions about itself via a live docs fetch (`WebFetch`) rather than from the prompt's own (possibly stale) knowledge | Claude Code (`docs.anthropic.com`, with an enumerated sub-page list), OpenCode (`opencode.ai`) — nearly word-for-word identical structure between the two |
| One-line identity, no self-referential doc-fetch instruction | OpenHands ("You are OpenHands agent, a helpful AI assistant..."), Codex ("You are Codex, based on GPT-5..."), Goose ("You are a general-purpose AI agent called goose, created by AAIF") |
| Identity framed around the *product's relationship to the user*, not just a role label | Cursor ("You are pair programming with a USER..."), Windsurf ("You are Cascade, a powerful agentic AI coding assistant designed by the Codeium engineering team... exclusively available in Windsurf") |
| Identity + explicit "you are an agent, keep going until resolved" framing | Cursor, OpenCode's `beast.txt`/o-series variant, Codex (implicit via Plan-tool section) |
| No fixed identity string in the base prompt at all — persona comes from a `roleDefinition` injected per-mode | Roo Code (`system.ts`'s `generatePrompt` starts with `${roleDefinition}`, not a hardcoded "You are X") |

**Cross-cutting observation**: OpenCode's identity/help/feedback block
(lines 1-9 of `opencode/prompt/default.txt`) is close to line-for-line
identical to Claude Code's (`leaked/claude-code/Prompt.txt` lines 6-10) —
right down to the "first use the WebFetch tool" instruction and the
"are you able...", "can you do..." example phrasing. This is the
strongest textual-similarity evidence in the whole collection that one
was written with direct reference to the other.

## 2. Per-model / per-provider prompt variants

Covered in more depth in each source's own README; summarized here for
the "leaders":

| Source | Variant strategy |
|---|---|
| OpenCode | Full separate prompt file per provider family — `anthropic.txt`, `gpt.txt`, `beast.txt` (o-series/GPT-4), `codex.txt`, `gemini.txt`, `kimi.txt`, `trinity.txt`, `meta.txt`, plus `default.txt` fallback — selected in `system.ts`'s `provider()` function by matching on model ID substring |
| Cline | Two-way split: a Claude-4-specific prompt (`model_prompts/claude4.ts`, with an experimental variant) vs. a generic prompt for everything else, chosen in `system.ts` by an `isNextGenModel` flag |
| Copilot Chat | The most granular in the collection — a distinct file per model/family (Anthropic, OpenAI GPT-5/5.1/5.2 in several sub-variants, Gemini, xAI, Zai, MiniMax, plus an internal "family H" and a Copilot-CLI-specific prompt) |
| Codex CLI | Distinct prompt per model generation (`gpt_5_codex_prompt.md`, `gpt_5_1_prompt.md`, `gpt-5.1-codex-max_prompt.md`, etc.) rather than one prompt with conditionals |
| Gemini CLI | One prompt *assembled from options structs* (interactive vs. autonomous phrasing, sandbox type, hierarchical-memory presence, etc.) rather than separate files per model — variance is along runtime/environment axes, not model identity |
| OpenHands, Claude Code, Cursor, Goose, Crush, Bolt, Aider, SWE-agent | Single prompt, no per-model branching visible in what's published |

## 3. Environment & context injection

What gets told to the model about *where* it's running, and how that data
gets in — static text baked at build time vs. dynamically interpolated
per session.

| Approach | Sources |
|---|---|
| A dedicated `<env>` block: cwd, git-repo yes/no, platform, OS version, today's date, model ID/name | Claude Code, OpenCode (near-identical block shape — see §1) |
| Environment folded into narrative prose rather than a tagged block | OpenHands (no explicit env block in the base prompt — environment is established via tool results), Codex (relies on tool outputs + `AGENTS.md`, not a prompt-level env block) |
| A whole options-struct system that conditionally includes sandbox-specific paragraphs (macOS Seatbelt vs. container sandbox vs. none), git-repo status, hierarchical memory file paths | Gemini CLI (`snippets.ts` — by far the most parameterized env handling in the collection) |
| Live git status/branch/recent-commits snippet appended to the very end of the prompt (outside the `<env>` block) | Claude Code (`gitStatus:` section at the tail — separate templating pass from the rest) |
| Environment is a function call result, not template interpolation — a TypeScript `Effect` computes and returns the block at request time | OpenCode (`system.ts`'s `environment()` function, `<env>...</env>` built from live `ctx` object) |
| WebContainer-specific environment constraints (what binaries exist, no `pip`, no C compiler) as a large dedicated section | Bolt.new (the only source describing a *browser-sandboxed* runtime rather than a real OS) |

## 4. Tool-use policy & calling convention

| Convention | Sources |
|---|---|
| Custom XML-style tags (`<tool_name><param>value</param></tool_name>`), one tool per message historically | Cline (`## execute_command`, `## read_file`, etc. — explicit "You can use one tool per message" in the base non-Claude-4 prompt) |
| Native/structured function calling, explicit push toward **parallel** tool calls as the default | OpenCode, Claude Code, Gemini CLI (`GREP_PARAM_*` etc. imply native schemas), Codex, Cursor (`<maximize_parallel_tool_calls>` — the most emphatic parallelism section in the collection, repeating the instruction three separate ways) |
| Tool catalog explicitly *excluded* from the system prompt itself (tool schemas delivered via the API's native tools mechanism, not spelled out in text) | Roo Code (`system.ts`: `const toolsCatalog = ""` — a deliberate code-level choice, with a comment noting "Tools catalog is not included in the system prompt") |
| A stated preference ranking of *which* tool to use for a given job (e.g. semantic/codebase search over grep, a task-delegation tool over ad hoc search) | Cursor (`codebase_search` mandated as primary, `<grep_spec>`), Claude Code/OpenCode/Crush (Task/Agent tool preferred for open-ended search "to reduce context usage") |
| A specific fast-search-tool brand preference stated in the prompt | OpenHands and Codex both explicitly recommend `rg`/`ripgrep` over `grep` for speed |

## 5. Code-editing format

The most consequential and most divergent design choice in this whole
comparison — how a proposed code change actually gets represented and
applied.

| Format | Sources |
|---|---|
| Custom `SEARCH/REPLACE` block syntax (`<<<<<<< SEARCH` / `=======` / `>>>>>>> REPLACE`), fenced, with a worked multi-example teaching sequence in the prompt itself | Aider (`editblock_prompts.py` — the most example-heavy teaching of an edit format in the collection: two full worked examples before any rules are stated) |
| XML-tagged `SEARCH/REPLACE` variant, different fence syntax (`------- SEARCH` / `=======` / `+++++++ REPLACE`) inside a `<replace_in_file>` tool call | Cline |
| `old_string`/`new_string` pair via a dedicated edit tool, must be unambiguous (fails if `old_string` isn't unique) | Claude Code, Gemini CLI (`EDIT_PARAM_OLD_STRING`), OpenHands (implied by the same "read enough to make it unambiguous" framing) |
| `apply_patch`-style patch tool as the *preferred but not exclusive* path, with an explicit list of cases where it should be skipped (auto-generated files, bulk search-and-replace) | Codex CLI |
| Bespoke `<boltAction type="file">` XML-in-artifact syntax carrying the **full file contents**, not a diff — whole-file rewrite is the unit of change | Bolt.new |
| A dedicated `read_lints`/linter-integration step is part of the edit loop itself, not a separate "verification" stage | Cursor (`<linter_errors>` — checks linter state after every edit and caps retries at 3 before asking the user) |
| Editing format left to "use the appropriate tool" without specifying a wire format in the base prompt (delegated entirely to tool schemas) | OpenCode, Roo Code, Crush, Goose |
| A note that **no patch tool is available at all**, so a different tool must be used | Cursor ("There is no apply_patch CLI available in terminal. Use the appropriate tool for editing the code instead.") — notable because Codex explicitly prefers `apply_patch` and Cursor explicitly says it doesn't have one; same underlying concept, opposite availability |
| Explicit prohibition against a specific patch tool name that doesn't exist in that product, to stop the model hallucinating it | Crush ("Never attempt 'apply_patch' or 'apply_diff' - they don't exist. Use 'edit' or 'multiedit' instead.") — direct evidence that this is a real failure mode vendors have had to patch (pun intended) by naming the wrong tool explicitly |

**Takeaway**: there is no format convergence here at all — five genuinely
different wire formats (SEARCH/REPLACE in two dialects, old/new string,
patch-based, whole-file) across a dozen tools, several of which
explicitly warn the model off a *different* tool's format by name. This
is the single biggest source of "an agent trained/tuned against one
tool's conventions behaves worse in another" friction in this space.

## 6. Planning & task tracking

| Approach | Sources |
|---|---|
| A dedicated stateful `TodoWrite` tool, instructed to be used "VERY frequently," with worked multi-step examples in the prompt (near-verbatim shared text) | Claude Code, and — only in OpenCode's **Claude-model-specific** variants (`prompt/anthropic.txt`, `prompt/meta.txt`), not its `default.txt` fallback. OpenCode's non-Claude variants use a *different* convention instead (see next row) |
| A todo list maintained as a plain **Markdown checklist re-displayed to the user on every update**, rather than a structured tool call | OpenCode's `beast.txt` (o-series/GPT-4 variant — "todo lists must always be written in markdown format and must always be wrapped in triple backticks") and `copilot-gpt-5.txt` variant ("use the todo tool to track your progress... update the todo list, marking completed, skipped..."). Notably a genuinely *different* mechanism from the Claude-variant's `TodoWrite` tool within the same product, chosen per model family. |
| `WRITE_TODOS_TOOL_NAME` referenced as a named, native tool | Gemini CLI |
| `<todo_spec>` with the most detailed todo-authoring rules of any source: ≤14 words per item, verb-led, "high-level, meaningful, nontrivial (≥5 min)" | Cursor |
| A "plan mode" / planning tool with an explicit **skip-it-for-easy-tasks** heuristic (roughly bottom quartile of tasks) | Codex CLI ("Skip using the planning tool for straightforward tasks (roughly the easiest 25%)... Do not make single-step plans") |
| A distinct **mode** (not just a tool) that's read-only and requires an explicit user hand-off to switch into execution | Gemini CLI ("Plan Mode" with an explicit "State Transition Override" paragraph once a plan is approved), OpenCode (`prompt/plan.txt`, `plan-mode.txt`, `build-switch.txt` as separate files) |
| No explicit planning tool/mode in the base prompt | OpenHands, Aider, Bolt.new, SWE-agent |

## 7. Coding conventions & the "minimal comments" rule

This is the strongest point of **convergence** across the whole
collection — nearly every source states some version of "don't add
comments unless asked," often close to verbatim:

| Wording | Sources |
|---|---|
| "DO NOT ADD ***ANY*** COMMENTS unless asked" (identical capitalization/emphasis) | Claude Code, OpenCode |
| "Write clean, efficient code with minimal comments... do not repeat information that can be easily inferred from the code" | OpenHands |
| "Add succinct code comments... You should not add comments like 'Assigns the value to the variable'... Usage of these comments should be rare" | Codex CLI (the only one of the five leaders to *allow* comments, conditionally, rather than banning them outright) |
| "Do not add comments for trivial or obvious code... Never use inline comments... Avoid TODO comments. Implement instead" | Cursor |
| "NEVER ADD COMMENTS: Only add comments if the user asked you to do so. Focus on *why* not *what*" | Crush |
| No comments rule found | Roo Code's section files (`sections/*.ts`) — checked directly, no mention of "comment" anywhere in what's in this collection, despite Roo Code being a Cline fork and Cline itself not having this rule either (Cline predates it; the rule appears to be a Claude-Code-era addition that neither Cline nor its forks picked up) |

Also near-universal: **"check existing conventions before writing code"**
— look at neighboring files/imports/package manifests before assuming a
library is available, match existing style. Present in near-identical
phrasing in Claude Code, OpenCode, and referenced equivalently in Cursor's
`<code_style>` and OpenHands's `<CODE_QUALITY>` sections. Only Cursor
inverts the *terseness* convergence though — see §11.

## 8. Project memory files (CLAUDE.md / AGENTS.md / etc.)

| File(s) | Sources |
|---|---|
| `CLAUDE.md` | Claude Code (also referenced by name in several other tools' review skills throughout this collection as *the* de facto standard to check for) |
| `AGENTS.md` | Codex CLI (explicitly: "closest `AGENTS.md`... applies to each changed file" — also the emerging cross-vendor standard; Crush and OpenCode's `system.ts` also read `AGENTS.md` per their own docs) |
| `GEMINI.md` (+ hierarchical memory, multiple files merged) | Gemini CLI — the most elaborate memory system: `DEFAULT_CONTEXT_FILENAME`, `HierarchicalMemory` type, per-directory merging |
| `CRUSH.md`, plus reads `AGENTS.md`/`CLAUDE.md`/`GEMINI.md` too | Crush — the only source that explicitly reads *four* different competing memory-file conventions for compatibility |
| No project-memory-file convention mentioned in the base prompt | OpenHands, Bolt.new, SWE-agent (SWE-agent is single-shot/non-interactive by design, so persistent project memory is less relevant to its use case) |

**Takeaway**: `AGENTS.md` is emerging as the closest thing to a
cross-vendor standard (explicitly supported by Codex, and read
compatibly by Crush/OpenCode per their own docs even though their native
file is different), while `CLAUDE.md` remains Anthropic-specific but is
widely *referenced* by other tools' review skills as the convention to
check for regardless.

## 9. Safety, refusals & sandboxing

| Constraint | Sources |
|---|---|
| "Assist with defensive security tasks only. Refuse to create, modify, or improve code that may be used maliciously" (near-identical wording) | Claude Code, Crush |
| Explicit warnings against specific destructive git operations (`git reset --hard`, force operations, amending commits) unless the user explicitly asks | Codex CLI, OpenHands (`<VERSION_CONTROL>` — "Do NOT make potentially dangerous changes... unless explicitly asked"), OpenCode/Claude Code (both: "NEVER commit changes unless the user explicitly asks") |
| "STOP IMMEDIATELY" instruction if the agent notices unexpected changes it didn't make, rather than silently working around or reverting them | Codex CLI |
| A structured, template-driven risk-assessment step included via a separate file (not inlined) | OpenHands (`<SECURITY_RISK_ASSESSMENT>{% include 'security_risk_assessment.j2' %}</SECURITY_RISK_ASSESSMENT>` — the only source that externalizes this into its own template rather than writing it inline) |
| Sandbox-awareness text that changes *content*, not just parameters, depending on execution environment (macOS Seatbelt vs. container vs. none), including instructions on how to explain sandbox-caused failures to the user | Gemini CLI |
| Process-management safety rule against overly broad kill commands (`pkill -f python` could kill unrelated processes) | OpenHands — a notably specific, narrow safety rule not seen elsewhere in the collection |
| No explicit security-refusal clause in the base prompt (security posture left to the platform/company layer rather than the prompt) | OpenCode, Cursor, Bolt.new, Aider, Goose, SWE-agent |

## 10. Sub-agents & delegation

| Approach | Sources |
|---|---|
| A general-purpose "Task" agent, recommended specifically to reduce context usage on open-ended search | Claude Code, OpenCode ("prefer to use the Task tool in order to reduce context usage" — identical framing to Claude Code again), Crush (`agent_tool.md`) |
| Extensible, dynamically-loaded tool sources via a plugin/extension system rather than fixed named sub-agents | Goose ("Extensions provide additional tools and context... You can dynamically enable or disable extensions") |
| Sub-agent behavior described but not exposed as a distinct named tool in the base prompt shown | OpenHands, Cursor, Codex CLI, Aider, Bolt.new |

## 11. Communication style & verbosity

The other major point of near-**identical convergence** in the Claude
Code-descended family, and the clearest outlier from Cursor.

| Style | Sources |
|---|---|
| "You MUST answer concisely with fewer than 4 lines... unless user asks for detail," with a near-identical worked example set (`2+2` → `4`, prime-number check, `ls` for "list files") | Claude Code, OpenCode, Crush ("Under 4 lines of text") — same numeric threshold, same example shape, strong evidence of shared lineage/copying |
| "Only use emojis if the user explicitly requests it" (near-verbatim) | Claude Code, OpenCode |
| Deliberately **inverted** stance: concise *narration* but explicitly **high-verbosity code** ("even if you have been asked to communicate concisely with the user"), full descriptive variable names, avoids abbreviations | Cursor — the only source in the collection to explicitly decouple chat terseness from code verbosity as two separately-tuned axes |
| A structured, multi-part "status update" protocol during long turns — narrated present/future tense progress notes tied to todo-list state, separate from the final summary | Cursor (`<status_update_spec>`, `<summary_spec>`) — the most elaborate mid-task communication protocol in the collection; none of the other leaders specify anything this granular for *in-progress* narration |
| Extensive final-answer formatting spec (heading rules, bullet density, monospace usage, tone words) as its own dedicated section | Codex CLI (`### Final answer structure and style guidelines`) — comparably detailed to Cursor's but focused on the *final* message only, not in-progress narration |
| No dedicated verbosity-control section in the base prompt | OpenHands (verbosity is not addressed — consistent with it being designed for autonomous/headless operation rather than a chat UI), SWE-agent, Bolt.new |

## 12. Completion & verification requirements

| Requirement | Sources |
|---|---|
| Mandatory lint/typecheck run before declaring a task done, with an instruction to ask the user for the command if unknown and offer to persist it to the memory file for next time | Claude Code, OpenCode (identical structure, `CLAUDE.md` vs `AGENTS.md` as the persistence target) |
| A full explicit 5-step workflow (Exploration → Analysis → Testing → Implementation → Verification), including a rule to *ask the user* before investing time setting up a testing framework that doesn't exist | OpenHands (`<PROBLEM_SOLVING_WORKFLOW>`) — the most process-heavy, numbered methodology of any source here |
| A "5-7 possible causes, ranked by likelihood" debugging ritual for when repeated fix attempts fail | OpenHands (`<TROUBLESHOOTING>`) — unique to OpenHands in this collection |
| Verification framed as running the app/tests immediately after each modification, as a top-level "critical rule" rather than a late pipeline step | Crush ("TEST AFTER CHANGES: Run tests immediately after each modification") |
| Linter-error checking folded into the edit loop itself (see §5) rather than a separate final step | Cursor |
| No explicit test/lint gate described in the base prompt | Bolt.new (no persistent test runner in a WebContainer sandbox), Codex CLI (delegates this to the "review mindset" section instead, when explicitly asked to review), SWE-agent (verification is inherent to its benchmark-style single-task loop, not a prompted rule) |

## 13. Role/mode variants within one product

| Product | Modes |
|---|---|
| OpenCode | `default`/provider-specific build persona, `beast.txt` (o-series), `plan.txt`/`plan-mode.txt` (read-only), `build-switch.txt` (short reminder when leaving plan mode) |
| Gemini CLI | Interactive vs. autonomous phrasing of the same base identity line; a distinct Plan Mode with its own "State Transition Override" text |
| Roo Code | A whole mode system (`Mode`, `ModeConfig`, `defaultModeSlug`) — role definition, base instructions, and even which *tool groups* are available are all mode-dependent, assembled fresh per mode via `generatePrompt()` |
| Codex CLI | Not modes exactly, but a distinct "review mindset" sub-persona triggered specifically when the user asks for a "review" (`## Special user requests` in `gpt_5_codex_prompt.md`), layered into the same base prompt rather than a separate file |
| Cline | Model-tier variant (Claude-4 vs. everything else) rather than task-mode variant |
| Claude Code, Cursor, OpenHands, Aider, Bolt.new, Goose, Crush, SWE-agent | Single mode in what's published here (Aider's *other* coder files, not included in this collection's subset, do add mode-like variants — see `aider/README.md`) |

---

## Design takeaways

- **Two rules have converged almost word-for-word across independently
  built products**: "don't add comments unless asked" and "answer in
  under 4 lines unless asked for detail." Both are specific enough,
  phrased distinctively enough, and repeated with near-identical worked
  examples (OpenCode vs. Claude Code especially) that this reads as
  either shared lineage/copying or convergent evolution toward what
  turned out to work — not independent invention from first principles.
- **Code-editing format is the opposite story: total divergence.** Five
  different wire formats across a dozen tools, with at least two sources
  (Cursor, Crush) explicitly telling the model a *different* tool's patch
  format doesn't exist in this one — direct evidence that models trained/
  tuned on one convention will hallucinate it into a tool that uses
  another, and vendors have had to patch that with explicit denials.
- **`AGENTS.md` is winning the memory-file standardization race** even
  though it's not the format any single major lab's own flagship tool
  (Claude Code) uses — Codex is built around it, and both OpenCode and
  Crush read it for compatibility alongside their native file.
- **Cursor is the consistent outlier** on communication style — every
  other leader converges on "be terse," but Cursor explicitly splits
  terse chat from verbose, heavily-annotated code, and adds a mid-task
  narration protocol none of the others specify.
- Given `code-review-approaches.md`'s finding that review tools run on
  top of these full prompts unmodified: a review invoked through, say,
  Crush's `/code-review`-equivalent isn't just "a review prompt" — it's
  this entire persona (defensive-security-only stance, never-comment
  rule, 4-line terseness, AGENTS.md-reading) plus the review instructions
  on top. The base prompt's behavior always leaks through.
