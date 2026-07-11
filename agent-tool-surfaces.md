# Tool surfaces: what scaffolds actually hand the model

A companion to [`coding-agent-approaches.md`](./coding-agent-approaches.md),
one layer down. That doc's §4 ("Tool-use policy & calling convention")
compares *how* tools get invoked and briefly flags a few specific tool
names in passing; this doc is the full inventory — for every source, what
tools actually exist, grounded directly in each source's own "Tool
surface" README section (all re-read from the files in this repo at time
of writing, not from memory or inference).

The trigger for writing this was noticing that **CodeAct** (see
[`codeact-hyperlight/`](./codeact-hyperlight)) isn't really one technique —
it's a data point in a much bigger design space every scaffold has to
answer: which shell, which search tool, whether code execution is a tool
at all, whether the model can see the browser, whether images come back
to it, whether the sandbox is a real OS or a micro-VM, and how (if at all)
the tool set can grow beyond what shipped on day one.

## Sources covered

The 21 sources in this collection with a dedicated "## Tool surface"
section: OpenHands, OpenCode, Codex CLI, Cline, Roo Code, Aider,
SWE-agent, Augment SWE-bench Agent, mini-swe-agent, Live-SWE-agent,
Composio SWE-Kit, CodeAct+Hyperlight, Pi, Goose, Crush, Bolt.new, Gemini
CLI, GitHub Copilot Chat, plus the three leaked closed-source extractions
(Claude Code, Cursor, Windsurf). The broader `leaked/` set (Manus, Devin,
Replit, v0, Same.dev, Trae, Emergent, Traycer, Amp, etc.) and
`github-pr-bots/` aren't individually profiled here — see each folder's
own README for what tool JSON is available if you want to extend this.

---

## 1. Shell

The one tool almost everyone has, but "a shell" hides real variation in
persistence, async support, and how tightly it's constrained.

| Approach | Sources |
|---|---|
| Generic, unconstrained shell tool, no special persistence/async handling mentioned | OpenHands, OpenCode (`Bash`, must explain non-trivial commands), Cline (`execute_command`), Roo Code (new terminal instance **per call**), Codex CLI, Gemini CLI's base tool (before its background flag — see below) |
| Explicit **non-persistent subshell** semantics — cwd/env resets every call, worked around by prefixing `VAR=val cd /path && ...` | mini-swe-agent, Live-SWE-agent |
| Explicit **persistent** shell (state, cwd, env vars survive across calls), via a real spawned process | Augment SWE-bench Agent (`pexpect`-driven `/bin/bash` with a sentinel prompt), SWE-agent (env vars set to disable pagers for headless use, implying long-lived session) |
| A runtime **template variable**, not a fixed assumption (`{{shell}}`) | Goose |
| Fixed, small, explicit command **allowlist** (39 named commands) — no shell escape beyond what's listed | Bolt.new (WebContainer) |
| Mandatory metadata attached to every shell call (a `description` param is *required*, not optional) | Crush (`bash` tool — "CRITICAL: The `description` parameter is REQUIRED for all bash tool calls") |
| A separate **plain-text convention** for weak/local models instead of structured tool calling — `$`-prefixed shell lines parsed out of the response text | Goose's `tiny_model_system.md` (distinct from Goose's own main `system.md`, which assumes native tool calling) |
| No shell tool exposed at all — every action goes through named, non-shell tools instead | Composio SWE-Kit (`FILETOOL_*`/`CODE_ANALYSIS_TOOL_*`/`GITHUB_*` only) |
| Shell is not directly model-visible — reached only via a code-execution sandbox's `call_tool` built-in | CodeAct+Hyperlight (whatever shell-equivalent tools the host registers) |
| **Async/background execution as a first-class capability** | See §6 below — cuts across several of the rows above |

**Takeaway**: persistence is a real fork, not a detail — mini-swe-agent's
and Live-SWE-agent's non-persistent model forces `cd`-prefixing
gymnastics that Augment's `pexpect` shell and most IDE-integrated tools
don't need. Bolt.new's allowlist is the only source that treats the shell
itself as something to be *restricted* rather than just wrapped — a
consequence of running inside a browser sandbox with no real OS beneath
it.

## 2. Search & code navigation

The clearest capability ladder in the whole comparison: plain filename/
text matching → dedicated fast-grep preference → semantic/AST-aware
search → LSP-backed symbol search → a delegated search sub-agent.

| Tier | Sources |
|---|---|
| No search tool at all — human manually adds files to context | Aider (the sharpest outlier: no `find`/`grep` tool of any kind; the user, not the model, decides what's in scope) |
| No search tool, falls back to ad hoc shell (`find`/`grep`) if the model chooses | Augment SWE-bench Agent, Composio SWE-Kit's editing role |
| Plain find/grep/git, explicitly **not** preferring `rg` | OpenHands ("use efficient tools like find, grep, and git commands with appropriate filters" — no `rg` mention despite an earlier draft of this claim being corrected, see `coding-agent-approaches.md` §4) |
| Named fast-search-tool preference (`rg`/`ripgrep` over `grep`), with a fallback note | Codex CLI ("prefer using `rg` or `rg --files`... because `rg` is much faster than alternatives like `grep`. (If the `rg` command is not found, then use alternatives.)"), Pi (conditionally — the guideline "Use bash for file operations like ls, rg, find" is only injected if no dedicated grep/find/ls tool is registered) |
| Dedicated `grep`/`glob` tools as named, separate primitives | Claude Code (`Glob`+`Grep`), OpenCode (`grep`+`glob`, named in its worked example), Gemini CLI (`GREP_TOOL_NAME`+`GLOB_TOOL_NAME` with fine-grained params: match cap, include/exclude, context lines), Crush's search sub-agent (`glob, grep, ls, view`), Windsurf (`grep_search`), Cursor (`grep_search`+`file_search`+`list_dir`) |
| Regex search + "view source definitions" (a lightweight symbol-listing capability, short of real LSP integration) | Roo Code |
| Semantic/embedding-based codebase search as the *primary* recommended tool, ahead of grep | Cursor (`codebase_search`, "your MAIN exploration tool" per the 2025-09-03 prompt), Windsurf (`codebase_search`, capped — "if you try to search over more than 500 files, the quality... will be substantially worse"), Copilot Chat (`Codebase`, "if you don't know exactly the string or filename pattern you're looking for") |
| LSP-backed **symbol** search (not just text/embedding match — actual language-server symbol resolution) | Copilot Chat (`SearchWorkspaceSymbols`) — a step beyond every semantic-search tool above, since it can leverage the editor's real language server |
| Class/method-granular structured lookups via a dedicated analysis toolkit, closer to symbol search than grep | Composio SWE-Kit's analyzer role (`CODE_ANALYSIS_TOOL_GET_CLASS_INFO`/`GET_METHOD_BODY`/`GET_METHOD_SIGNATURE`, `FILETOOL_SEARCH_WORD`) |
| A **dedicated sub-agent** specifically for open-ended/complex search, distinct from the general-purpose task-delegate | Gemini CLI (`codebase_investigator`, gated behind `enableCodebaseInvestigator`, reserved for "complex refactoring, codebase exploration or system-wide analysis"), Copilot Chat (`SearchSubagent`) |
| A recovery/"pull the full body" tool that complements semantic search once it's found something | Windsurf (`view_code_item` — pulls the full body of a function/class the semantic search only summarized) |

**Takeaway**: this is the axis with the most genuine capability spread in
the collection, from Aider's "no search tool, the human curates context"
to Windsurf/Copilot Chat's semantic-search-plus-symbol-resolution-plus-
delegate-subagent stack. Notably, the two sources with *zero* search
tooling (Aider, mini-swe-agent/mini's floor) are both benchmark-lineage
or deliberately-minimal designs, not accidents — the absence is a stated
design choice in both READMEs, not a gap.

## 3. Code execution as a distinct capability from "the shell"

Most sources fold "run code" into "run a shell command." A few make code
execution its own tool, or its own sandbox, distinct from the general
shell.

| Approach | Sources |
|---|---|
| Code execution is just shell commands (`python3 script.py`, etc.) — no dedicated code-exec tool | Nearly everyone with a shell tool (OpenHands, OpenCode, Cline, Roo Code, Augment SWE-bench Agent, mini-swe-agent, SWE-agent) |
| **CodeAct**: a single tool runs a whole model-generated program per call, chaining multiple *other* tools together mid-script instead of one tool call per model turn | CodeAct+Hyperlight (`execute_code`, an in-sandbox `call_tool(name, **kwargs)` built-in) — the source this pattern is named after in this collection; OpenHands's `CodeActAgent` naming references the same underlying research but the prompt captured here doesn't show the mechanism itself. **Correction**: Codex CLI independently implements the same pattern natively — `tools/code_mode/` (`CodeModeService`, a `call_nested_tool()`-style mechanism, self-recursion explicitly blocked) — invisible to this collection until its prompt-text-only extraction was checked against the live source; see `codex/README.md`'s "Tool surface" section. Not one source built entirely around CodeAct plus one naming reference, but at least two independent working implementations. |
| Notebook cell execution as its own tool, distinct from both shell and file-edit tools | Copilot Chat (`RunNotebookCell`, paired with `EditNotebook`/`GetNotebookSummary` — explicitly forbidden to use `EditFile` or shell out to `jupyter` for notebook work) |
| Stdlib-only Python (no `pip`), no C/C++ compiler at all — code execution is real but deliberately capability-limited by the runtime itself | Bolt.new (WebContainer) |
| The agent can **write and then execute its own new tools** mid-task (Python scripts invoked via bash), rather than being limited to pre-registered tools | Live-SWE-agent — unique in this collection; the "tool" that gets created is just a script the existing bash tool then runs, not a new entry in the model's function-calling schema |

**Takeaway**: CodeAct and notebook-cell-execution are really the same
underlying idea from two different angles — both exist because
one-tool-call-per-turn is a bad fit for "run several small computational
steps and look at the combined result." Live-SWE-agent's self-authored
tools are a third, cheaper way to get some of the same benefit without
building a program-execution sandbox at all.

## 4. Browser & web access

Three genuinely different capability tiers, not just "has a browser tool
or doesn't": plain fetch, fetch-plus-search, and full interactive
browser automation.

| Tier | Sources |
|---|---|
| No web/browser tool at all | OpenHands (`EXTERNAL_SERVICES` prefers API access over browsing), Roo Code (confirmed zero browser-tool mentions — a real divergence from its parent, Cline), Aider, SWE-agent, mini-swe-agent, Live-SWE-agent, Augment SWE-bench Agent (explicitly no internet access), Pi, Gemini CLI's captured snippet (no web-fetch constant imported here) |
| Scoped to fetching the product's **own documentation only**, not general browsing | OpenCode (`WebFetch` restricted to `opencode.ai`) |
| Plain URL fetch, no search | Claude Code (`WebFetch`, separate from `WebSearch`), Copilot Chat (`FetchWebPage`) |
| Fetch + general web search, as two distinct tools | Claude Code (`WebFetch`+`WebSearch`), Cursor (`web_search` only — no fetch-a-known-URL tool distinct from it in this extraction), Windsurf (`search_web`+`read_url_content`) |
| **Two-tier fetch** — a cheap plain fetch vs. an expensive AI-summarizing/question-answering fetch sub-agent, with the cost tradeoff stated explicitly | Crush (`fetch` vs. `agentic_fetch`, "slower and costlier") — conceptually the same tiering Copilot Chat applies to terminal output (§1), applied to web content instead |
| Full **vision-based interactive browser automation**: launch, click/type/scroll by pixel coordinate from a screenshot, close | Cline (`browser_action`, Puppeteer-driven, exclusive mode while active, conditional on a `supportsBrowserUse` capability flag) |
| Full browser automation, **split into granular single-purpose tools** rather than one multi-mode tool | Windsurf (`browser_preview`, `list_browser_pages`, `open_browser_url`, `read_browser_page`, `get_dom_tree`, `capture_browser_screenshot`, `capture_browser_console_logs` — seven separate tools covering the same ground as Cline's one) |
| Diagram generation exposed as its own tool (not literally "the web," but the only other visual/rendering-output tool in the collection worth grouping here) | Cursor (`create_diagram`) — the only dedicated diagram tool found in this collection |

**Takeaway**: browser automation is rare and, where present, expensive to
build — only Cline and Windsurf have it, and Windsurf's is meaningfully
richer (DOM tree extraction, console-log capture, a dedicated preview
tool for the app the agent itself is building). Everyone else stops at
fetch-and-maybe-search, and a substantial fraction of sources — mostly
the benchmark/headless-lineage ones — have no web access whatsoever,
consistent with running in network-isolated sandboxes.

## 5. Multimodal / images

The thinnest capability in the whole survey — almost nobody addresses it
directly as a named tool concern.

| Approach | Sources |
|---|---|
| Not addressed at all in what's captured | The large majority — OpenHands, OpenCode, Roo Code, Aider, SWE-agent, Augment SWE-bench Agent, mini/Live-SWE-agent, Composio SWE-Kit, Goose, Bolt.new, Gemini CLI, Claude Code's extracted tool list, Cursor's extracted tool list, Pi |
| Screenshots as the closest analog — captured for visual inspection as a side effect of browser automation, not a standalone "look at this image" tool | Cline (`browser_action`'s implicit screenshot feedback loop), Windsurf (`capture_browser_screenshot`) |
| Notebook **output mimetypes** as the only other multimodal-adjacent surface (a cell's output can be an image, surfaced through `GetNotebookSummary`) | Copilot Chat |
| A dedicated **create_diagram** tool for generating (not consuming) visual output | Cursor |
| A dedicated **view an image file** tool, model-gated on actual vision support | **Correction**: Codex CLI — `view_image` (base64-encodes a file into a data URL, returned as an `InputImage` content item; errors explicitly if "you do not support image inputs") — wrongly marked absent in an earlier prompt-text-only pass; found only by checking the live tool registry. See `codex/README.md`. |

**Takeaway**: despite most underlying models being vision-capable, almost
none of these scaffolds give the model a dedicated "attach/view an image"
tool independent of a browser-screenshot side effect — multimodal input
handling here is overwhelmingly implicit (whatever the chat UI passes
through) rather than a named, described tool capability.

## 6. Async / background execution

A capability that shows up in strikingly different shapes for the same
underlying need: don't block the whole turn on a long-running command.

| Pattern | Sources |
|---|---|
| A single boolean/flag on the shell tool's schema | Gemini CLI (`SHELL_PARAM_IS_BACKGROUND`) |
| A richer flag set (blocking vs. not, safe-to-auto-run, a wait-before-backgrounding delay) plus a **separate polling tool** | Windsurf (`run_command`'s `Blocking`/`SafeToAutoRun`/`WaitMsBeforeAsync` params + `command_status`) — the most fleshed-out version in the collection |
| **Two distinct named tools** — one to check output, one to terminate | Claude Code (`BashOutput`/`KillBash`) |
| Interactive/background status distinguished per Roo Code's terminal-instance model | Roo Code (new terminal instance per `execute_command` call, supports interactive and background commands with status) |
| Not addressed / not needed by design (single-shot, non-interactive benchmark loop) | SWE-agent, mini-swe-agent, Live-SWE-agent, Augment SWE-bench Agent, Aider |

**Takeaway**: three different shapes for the same idea — one flag
(Gemini CLI), a flag-plus-poller (Windsurf), or two fully separate tools
(Claude Code) — with no convergence on which is "right," though Windsurf's
is the only one that also lets the model tune *how long* to wait before
treating a command as background (`WaitMsBeforeAsync`).

## 7. Persistent memory & deployment as tools

Two capabilities that only one source in this collection exposes as
callable tools rather than passive conventions — both from the same
product.

| Capability | Sources |
|---|---|
| Cross-session memory as a **callable tool** (create/update/delete entries in a memory database, tagged and workspace-scoped, with an explicit dedup-check instruction) | Windsurf (`create_memory`) — no other source in this collection exposes persistent memory as a tool; everyone else relies on a passive file convention instead (`CLAUDE.md`/`AGENTS.md`/`GEMINI.md`/`CRUSH.md` — see `coding-agent-approaches.md` §8) |
| Searching the agent's **own past session history** | Windsurf (`trajectory_search`) |
| Shipping the app it built, not just building it — deploy + status-check + read-config as named tools | Windsurf (`deploy_web_app`, `check_deploy_status`, `read_deployment_config`) — unique in this collection |

**Takeaway**: memory-as-a-tool and deployment-as-a-tool are both Windsurf
exclusives in this collection — everywhere else, "remember this for next
time" means "write it to a file the next session might read," and
"deploy" is out of scope entirely.

## 8. Editing tool families

Covered in depth in `coding-agent-approaches.md` §5 (wire format); this
is the narrower question of *how many* editing tools a source exposes and
whether any are redundant/competing.

| Pattern | Sources |
|---|---|
| Exactly one edit tool | Most sources — Claude Code's `Edit` alongside `MultiEdit` is the closest thing to an exception in the "one primary format" camp |
| A batch/multi-location variant alongside the single-edit tool | Claude Code (`Edit`+`MultiEdit`), Copilot Chat (`ReplaceString`+`MultiReplaceString`) |
| **Two competing edit tools side by side** (not primary+batch, but two full alternative mechanisms) | Cursor (`edit_file` **and** `search_replace`), Copilot Chat (`ReplaceString`/`MultiReplaceString` **and** `ApplyPatch` — the only two sources in the collection with both a patch-style and a string-replace family available at once) |
| A dedicated **recovery tool** for when an edit fails to apply cleanly | Cursor (`reapply`) — not named explicitly anywhere else in this collection |
| Explicit denial that a specific patch tool exists, to stop the model hallucinating it | Cursor ("There is no apply_patch CLI available"), Crush ("Never attempt 'apply_patch' or 'apply_diff' - they don't exist. Use 'edit' or 'multiedit' instead") |
| No dedicated edit tool at all | Aider (text-parsed SEARCH/REPLACE, no tool-calling loop), mini-swe-agent, Live-SWE-agent (bash heredocs/`sed` only) |
| Edit-undo as its own explicit tool action | Augment SWE-bench Agent, SWE-agent (`undo_edit`, part of the `str_replace`-family editor both fork from Anthropic's reference tool) |

## 9. Sandbox / isolation

| Model | Sources |
|---|---|
| Real OS process, no sandbox indicated in the prompt itself | Cline, Roo Code, Cursor, Copilot Chat, Claude Code's extraction, Aider, Pi — all run in the user's actual editor/workspace or terminal |
| Docker container (implied by environment gotchas noted in the prompt, e.g. symlinked paths) | Augment SWE-bench Agent |
| Environment-conditional sandbox description (macOS Seatbelt vs. generic container vs. none), rendered as different prompt text depending on which is active | Gemini CLI — the sandbox enforcement itself is external, but the *description* shown to the model branches on it |
| Browser-based sandbox (WebContainer) — no real OS underneath, fixed command allowlist, no compiler | Bolt.new |
| **Micro-VM**, millisecond startup, no filesystem/network by default, everything explicitly allow-listed, and — uniquely — the capability *description itself* is assembled live from the sandbox's actual current config rather than fixed/branching text | CodeAct+Hyperlight — the most dynamically-rendered sandbox description in the collection (contrast Gemini CLI's ~2-way branch above) |
| Not specified / depends entirely on deployment | OpenHands, OpenCode, Codex CLI (cross-ref `github-pr-bots/codex-review`), SWE-agent, mini-swe-agent, Live-SWE-agent, Composio SWE-Kit, Goose, Crush, Windsurf |

## 10. Extensibility (MCP, skills, plugins, dynamic tool sets)

| Mechanism | Sources |
|---|---|
| MCP (Model Context Protocol) client tools, conditionally injected only when the user has configured a server | OpenCode (`use_mcp_tool`+`access_mcp_resource` equivalents), Cline (`use_mcp_tool`, `access_mcp_resource`, plus `load_mcp_documentation`) |
| A skills system with a dedicated activation tool | Gemini CLI (`ACTIVATE_SKILL_TOOL_NAME`), Roo Code (`SkillsManager`), Pi (skills appended to the prompt only if the `read` tool is available, via `formatSkillsForPrompt`) |
| Fully dynamic, plugin-loaded tool sets — **no built-in tools named in the base prompt at all** | Goose ("Extensions provide additional tools and context... You can dynamically enable or disable extensions"), with a distinctive too-many-tools warning (`extension_tool_limits`) not seen elsewhere |
| Tool list built by iterating over whatever's actually registered, each contributing its own one-line description — the prompt *cannot* describe a tool that isn't wired up | Pi (`toolSnippets[name]` per registered tool), Gemini CLI (tool name constants imported from `tools/tool-names.js`, "literally cannot drift out of sync with the tool implementations' actual names") |
| Sandbox tool registry rendered fresh per run from the live configuration | CodeAct+Hyperlight (`_format_tool_summaries` over whatever `FunctionTool`s are registered) |
| Sub-agent delegation as the extensibility axis, not a plugin system | Claude Code/OpenCode/Crush's `Task`/delegate agent, Gemini CLI's `AGENT_TOOL_NAME`+`codebase_investigator`, Copilot Chat's `ExecutionSubagent`/`SearchSubagent`, Composio SWE-Kit's fixed 3-role handoff team |
| A full custom-system-prompt escape hatch that replaces the default tool-list/guideline assembly entirely, rather than layering on top of it | Pi (`.pi/SYSTEM.md` / `~/.pi/agent/SYSTEM.md`) |

---

## Design takeaways

- **"Give the model a shell" is not one design — it's at least five**:
  unconstrained, non-persistent-subshell, persistent-process, allowlisted,
  or template-variable. The persistence axis in particular (mini-swe-agent
  vs. Augment SWE-bench Agent) produces genuinely different prompt-level
  workarounds (`VAR=val cd /path && ...` prefixing) for what is otherwise
  the same underlying capability.
- **Search tooling is the widest capability spread in the collection.**
  From Aider's *zero* search tooling (curated by the human) through plain
  grep, `rg`-preferring grep, semantic/embedding search, to LSP-backed
  symbol resolution plus a dedicated search sub-agent (Copilot Chat,
  Windsurf). This tracks roughly with how IDE-integrated a tool is —
  standalone CLI agents (Aider, SWE-agent-lineage) sit at the bottom,
  IDE extensions with real language-server access sit at the top.
- **CodeAct, notebook-cell execution, and Live-SWE-agent's self-authored
  tools are three answers to the same underlying complaint**: one
  tool-call-per-turn is a bad fit when the "step" naturally involves
  chaining several small operations and inspecting a combined result.
  They differ in cost/complexity — a full program-execution sandbox
  (CodeAct+Hyperlight) vs. a narrowly-scoped cell-execution tool
  (Copilot Chat) vs. just letting the model write a throwaway script and
  run it with the shell tool it already has (Live-SWE-agent) — but all
  three exist to route around the same constraint.
- **Browser automation and persistent-memory-as-a-tool are rare enough to
  be single-source features**, not converged-on capabilities: Cline and
  Windsurf are the only two with interactive browser control, and
  Windsurf alone has memory and deployment as callable tools. This is a
  different pattern from the strong convergence seen elsewhere in this
  collection (e.g. the terseness/no-comments rules in
  `coding-agent-approaches.md` §7) — tool *surface* breadth hasn't
  converged the way tool-independent behavioral rules have.
- **Multimodal input is the least-addressed capability of everything
  surveyed here**, despite most of the underlying models being
  vision-capable — almost no source names a dedicated "view this image"
  tool; what multimodal handling exists is a side effect of browser
  screenshots or notebook output mimetypes, not a first-class capability.
- **Dynamic tool-surface rendering (Gemini CLI's imported tool-name
  constants, Pi's `toolSnippets`, CodeAct+Hyperlight's live sandbox-config
  rendering, Goose's plugin-only model) is a maturity signal, not a
  gimmick** — each is a structural guard against the prompt describing a
  tool that doesn't actually exist in that deployment, which is exactly
  the failure mode Cursor's and Crush's explicit "this patch tool doesn't
  exist" denials (see `coding-agent-approaches.md` §5) exist to patch
  after the fact with static text instead.
