# Sub-agents: when a scaffold spawns another agent

A second drill-down alongside [`agent-tool-surfaces.md`](./agent-tool-surfaces.md),
this time on a single capability that turned out to have far more
internal variety than "delegate a task to a helper agent" suggests: what
protocol the orchestrator and sub-agent speak, what (if any) system
prompt the sub-agent runs under, how its result gets back into the
orchestrator's context, and what happens if two sub-agents run at once.

Grounded directly in each source's own "## Sub-agents" README section
(all re-read from the files in this repo at time of writing). 16 sources
have one — a mix of the "coding agent" core collection and several
`leaked/` sources whose tool JSON turned out to carry unusually detailed
sub-agent specifications once actually read closely, plus two sources
(Codex CLI, OpenHands) added, and one (OpenCode) substantially deepened,
after prompt-text-only passes badly undersold what was actually there —
see the methodology note at the end of §2.

## Sources covered

Claude Code (leaked), the general Anthropic assistant prompts (leaked),
OpenCode, Cline, Roo Code, Codex CLI, OpenHands, Gemini CLI, GitHub
Copilot Chat, Crush, Goose, Composio SWE-Kit, Amp (leaked), Emergent
(leaked), Google Antigravity (leaked), and v0 (leaked). Sources with
**no** sub-agent mechanism found — Aider, SWE-agent, mini-swe-agent,
Live-SWE-agent, Augment SWE-bench Agent, Bolt.new, Pi,
CodeAct+Hyperlight, and (notably, given how rich their tool surfaces
are — see `agent-tool-surfaces.md` §§1–7) leaked Cursor and leaked
Windsurf — are covered only in the "Absences" section below, not
individually profiled. Unlike most other sources here, Codex CLI's and
OpenHands's sub-agent sections (and half of OpenCode's) are sourced from
reading live upstream repos directly rather than from a prompt/tool-JSON
file stored in this collection — see each README for why.

---

## 1. What triggers delegation

Every source that has sub-agents gives some framing for *why* to use one
instead of just doing the work directly — but the stated reason varies
from "save context" to "get a second opinion" to "isolate risk."

| Framing | Sources |
|---|---|
| **Context-window conservation**, stated explicitly as the reason | Gemini CLI ("Your own context window is your most precious resource... use sub-agents to 'compress' complex or repetitive work"), OpenCode ("reduce context usage"), Claude Code/Amp's `Task` ("run an operation that will produce a lot of output (tokens) that is not needed after the sub-agent's task completes"), v0's `SearchRepo` ("a separate agent with a new context window") |
| **Speed** — a sub-agent can search faster/more thoroughly than the orchestrator doing it serially | Claude Code, OpenCode, Crush, v0 — all frame their search delegate this way |
| **A genuinely different model/capability**, not just a fresh context | Amp's `oracle` (runs on OpenAI's o3, not whatever model is driving the main loop — the only source in this collection that specifies this) |
| **Risk isolation** — the sub-agent's mistakes are contained/verifiable before trusting them | Emergent (git-diff verification explicitly required after every sub-agent report), Google Antigravity's `browser_subagent` (orchestrator must independently re-check DOM/screenshot state rather than trust the report) |
| **A quantified threshold**, not just judgment | Gemini CLI ("more than 3 files or repeated steps") — comparable in spirit to Codex CLI's quantified plan-skip threshold (see `coding-agent-approaches.md` §6), applied here to delegation instead of planning |
| **Fixed pipeline stages**, not a judgment call at all — every task goes through the same roles in the same order | Composio SWE-Kit's 3-role handoff (`SOFTWARE_ENGINEER` → `CODE_ANALYZER`/`EDITING_AGENT`) |
| **Explicit "well-scoped task" framing plus a batch/map use case** | Codex CLI's `spawn_agent` description ("Spawn a sub-agent for a well-scoped task"), with a distinct bulk-delegation path (`agent_jobs.rs`'s CSV-driven "map a sub-agent over rows and collect results," capped at 16-64 concurrent) alongside single ad hoc spawns |
| **Overhead framed explicitly against the alternative, not just "it saves context"** | OpenHands's `task` tool description ("each delegation has overhead — use them when the task genuinely benefits from a separate agent... A single grep, find, or cat command would answer your question — just run it yourself") — near-identical phrasing to Claude Code's own Task tool, worth reading as convergent design or direct influence |
| **A whole extra tier: fan-out/fan-in over many sub-agents as its own use case**, not just single delegation | OpenHands's `workflow` tool (`wf.map_agents`/`wf.reduce_agent`/`wf.pipeline`) — triggered when the task is itself a batch/aggregation job (e.g. "review these 20 files and summarize"), a distinct use case from "delegate this one well-scoped thing" |

## 2. Calling convention & protocol shape

The biggest structural fork: is a "sub-agent" a **tool call** that
returns a result, or a **role in a shared conversation** that hands
control back and forth via convention?

| Shape | Sources |
|---|---|
| **Tool call → stateless, one-shot, single final report** — the orchestrator cannot send follow-up messages, only sees the sub-agent's last message | Claude Code (explicit: "Each agent invocation is stateless... you can't communicate with it until it finishes"), Amp's `Task` (near-identical wording), Crush, v0, Gemini CLI (implied by the "consolidated into a single summary" framing) |
| **Tool call with a typed registry** — caller picks from named agent *types*, each with a different tool scope | Claude Code (`general-purpose`/`statusline-setup`/`output-style-setup`, via a `subagent_type` parameter), Gemini CLI (`agent_name` parameter, `codebase_investigator` named explicitly), Amp (three tools with three different roles — `task`/`oracle`/`codebase_search_agent` — rather than one tool with a type parameter) |
| **Tool call with essentially one free-text parameter (`task`)**, fleet of separately-named single-purpose tools instead of a type enum | Emergent (`auto_frontend_testing_agent`, `deep_testing_backend_v2`, `integration_playbook_expert_v2`, `vision_expert_agent`, `support_agent`, `deployment_agent` — six separate tools, each essentially `(task: string) -> report`) |
| **Fixed multi-role team, control passed via literal keyword strings in a shared conversation** — not a tool call/return at all | Composio SWE-Kit (`"ANALYZE CODE"`, `"ANALYSIS COMPLETE"`, `"EDIT FILE"`, `"EDITING COMPLETED"`) — the one source in this collection where delegation isn't tool-mediated |
| **File-mediated handoff** — orchestrator and sub-agent communicate through a shared document, not tool-call parameters/results | Emergent's backend-testing flow specifically: `test_result.md` documents its own "Testing Protocol and communication protocol with testing sub-agent," and the orchestrator is told to read/update it before and after each test-agent invocation |
| **Confusable-but-different: session/context handoff to the *user*, not a spawned agent** | Cline's `new_task` — generates a structured summary and hands it to the user as a preview for starting a *fresh conversation*; no orchestrator-sub-agent relationship, no result passed back, the "new task" replaces the current one rather than running alongside it |
| **Async background process the orchestrator never directly invokes** — runs over history, produces artifacts the orchestrator later reads | Google Antigravity's Knowledge Subagent (distills past conversations into "Knowledge Items" the orchestrator reads later, rather than being called synchronously) |
| **Tool call → persistent, addressable child, not stateless one-shot** — spawn returns an id the orchestrator can message, interrupt, and block-wait on across *multiple, separate* follow-up tool calls, rather than one call that blocks until a final report | Codex CLI — `spawn_agent` returns an agent id; `send_input` (optionally with `interrupt: true`) messages it again later; `wait_agent` blocks on one or more ids with a timeout; `close_agent` tears it down. OpenCode's `task` tool independently converges on the same shape via a different mechanism: calling `task` again with an already-running `task_id` doesn't error, it gets queued onto the still-live job (`background.extend()`) and returns immediately — a genuine follow-up-to-a-running-sub-agent capability built on a generic `BackgroundJob` primitive rather than a purpose-built agent-session protocol. OpenHands's new-SDK `delegate` tool (`spawn` once, then repeated `delegate` calls by `agent_id`) and `task` tool (`resume: <task_id>`) are two more independent arrivals at the same shape. |
| **Hybrid: blocking by default, but can detach to background mid-flight and reattach via a synthetic follow-up message** | OpenCode — a `task` call races the sub-agent finishing against being *promoted* to background (interrupted-but-not-killed); if promoted, the tool call returns immediately and a forked watcher later injects the final result back into the parent session as a `synthetic: true` message rather than a tool result. Distinct from Codex's/OpenHands's explicit poll-or-wait model — here the transition from sync to async can happen unpredictably mid-call, gated behind an experimental flag (`OPENCODE_EXPERIMENTAL_BACKGROUND_SUBAGENTS`). |
| **True parallel execution via real OS threads, not sequential/cooperative turn-taking** — multiple sub-agents genuinely run concurrently, joined when done | OpenHands's `delegate` tool: `DelegateExecutor._delegate_tasks` spins up one Python thread per named sub-agent and `.join()`s them, capped at `max_children: int = 5`. Contrast with OpenHands's own *prior* (0.60.0) design, `AgentDelegateAction`, which was strictly one-delegate-at-a-time cooperative blocking within a single event loop — a real protocol upgrade across the two generations of the same product, not just an addition. |
| **A fan-out/fan-in orchestration DSL layered on top of a delegate primitive**, not just a single spawn call | OpenHands's `workflow` tool — `wf.map_agents(items, prompt, max_concurrency=...)`, `wf.reduce_agent(...)`, `wf.pipeline(items, *stages)` (staged, non-barriered — a fast item can reach a later stage while a slow item is still on an earlier one) exposed as a constrained Python sandbox API. The most structurally distinct protocol shape in this survey — every other row is "one call, one (or one resumable) sub-agent"; this is a small map-reduce/DAG engine over many. |

**Takeaway**: Cline's `new_task` is worth flagging as a trap for anyone
skimming tool names across sources — it's lexically adjacent to Claude
Code's `Task` and Roo Code's mode system, but semantically unrelated:
it's a context-compaction/session-restart convenience for the *user*,
not a delegation mechanism. Composio SWE-Kit's keyword-handoff pipeline
is a different kind of structural outlier — every stateless-tool-call
source treats "sub-agent" as one call with a return value; Composio
treats it as a fixed sequence of roles sharing one conversation; Codex,
OpenCode, and OpenHands each independently treat it as a *live,
continuing* child process the orchestrator keeps a handle to — three
unrelated codebases converging on the same "addressable, not
stateless" shape is a real signal, not a coincidence, and OpenHands's
`workflow` DSL pushes a step further still into genuine multi-sub-agent
orchestration rather than single-child addressing.

**A methodology note, since several rows here were added after the
fact**: my first pass on Codex CLI concluded it had no sub-agent
mechanism at all; my first pass on OpenCode found the Task tool
mentioned in prompt instructions but never its actual protocol; my
first pass on OpenHands didn't cover it as a source at all. All three
gaps trace to the same cause — the only material actually stored in
this collection for each of these three is prompt *text* (or, for
OpenCode, prompt text plus one file listing tool names without
descriptions), and delegation tooling for all three ships as separate
source that was never fetched in. The lesson generalizes: for every
source in this survey whose sub-agent findings come from a prompt-text
or tool-JSON *extraction* rather than full source (which, after these
three corrections, is now every source here **except** Codex,
OpenHands, and half of OpenCode), an absence in this doc means "not
mentioned in the captured prompt/tool text," not "confirmed not to
exist." Treat every row in §7 ("Absences") as provisional on that
basis, not as a verified negative.

## 3. Does the sub-agent get its own system prompt?

The question the user's request specifically asked about, and the one
with the most uneven documentation across sources — most tool JSON
extractions only capture the *orchestrator-facing tool description* that
triggers delegation, not what prompt (if any) the spawned agent itself
runs under.

| Sub-agent system prompt fully captured? | Sources |
|---|---|
| **Yes — complete, standalone prompt file(s)** | Copilot Chat (`executionSubagentPrompt.tsx`: "You are an AI coding research assistant that runs a series of terminal commands..."; `searchSubagentPrompt.tsx`: "...that uses search tools to gather information..."), Crush (`task.md.tpl`: "You are an agent for Crush..."; `agentic_fetch_prompt.md.tpl`: "You are a web content analysis agent for Crush..."), Goose (`subagent_system.md`: "You are a specialized subagent within the goose AI framework... You were spawned by the main goose agent"), OpenHands (four built-in `AgentDefinition` Markdown files — `bash-runner`, `code-explorer`, `web-researcher`, `general-purpose` — each with a distinct role-specific prompt body, e.g. `code-explorer`'s explicitly forbids any file-modifying command and whitelists specific read-only shell commands) |
| **Yes, but as an either/or *replacement* of the base prompt rather than an addition** | OpenCode — a sub-agent's `prompt` field, when its agent type defines one, entirely replaces the model-family base prompt (`session/llm/request.ts`) rather than appending to it; `explore` (read-only, its own dedicated persona) has one, `general` (full tool parity) doesn't and falls through to the same base prompt the orchestrator itself uses. Custom agents are also definable as Markdown+YAML-frontmatter files, the same convention OpenHands independently converges on. |
| **No — only the orchestrator-side tool/call description is captured, not the sub-agent's own prompt** | Claude Code, Amp (all three of `Task`/`oracle`/`codebase_search_agent`), Gemini CLI, v0, Emergent (six named agents, no prompt text for any of them), Google Antigravity's `browser_subagent` |
| **Partial — a role-based config/persona layer confirmed to exist, but the actual prompt text per role wasn't read** | Codex CLI — `agent/role.rs` defines named roles (`"default"`, `"explorer"`, `"worker"`) with distinct behavioral framing and the ability to override model/reasoning/service-tier per role, loaded through the same config machinery as `config.toml`; closer to Claude Code's typed `subagent_type` registry than to a single generic delegate, but not confirmed as a fully-captured standalone system prompt the way Copilot Chat/Crush/Goose/OpenHands are |
| **N/A — no tool-call boundary in the first place, so no separate "sub-agent prompt" concept applies** | Composio SWE-Kit (each of the three roles has its own persona prompt, but they're peers in one state machine, not an orchestrator-plus-spawned-sub-agent relationship) |

Worth noting the mechanism split even among the "Yes" sources: Goose,
Copilot Chat, and Crush swap in a wholly separate prompt with no
relationship to the orchestrator's own; OpenHands *appends* each
sub-agent's role-specific text as a `system_message_suffix` onto the
base message rather than replacing it; OpenCode does both depending on
agent type (`explore` replaces, `general` doesn't touch it at all). No
two sources implement this identically.

Of the sources with a captured sub-agent prompt, each makes a different
design choice about how much the sub-agent should know it *is* one:

- **Goose is explicit about identity and provenance**: "You were spawned
  by the main goose agent to handle a specific task efficiently" — the
  sub-agent is told directly who spawned it and why.
- **Copilot Chat and Crush give the sub-agent a role, not a
  spawned-by-relationship**: "an AI coding research assistant," "an
  agent for Crush," "a web content analysis agent for Crush" — no
  mention that a parent agent exists or that this is a delegated task.
- **OpenHands's four built-in roles are pure task specialization, no
  delegation framing at all**: `bash-runner`/`code-explorer`/
  `web-researcher`/`general-purpose` read like standalone job
  descriptions (what to do, what tools are off-limits) with zero
  mention of being spawned by anything — the delegation relationship
  lives entirely in the orchestrator-side `task`/`delegate` tool
  description, not in the sub-agent's own text.
- **OpenCode's `explore` sits with Copilot Chat/Crush** (a role, no
  spawned-by framing) **while `general` sits in a category none of the
  others do**: it has no distinct identity at all, delegated or
  otherwise — it's just the orchestrator's own persona, running with a
  different tool scope.

## 4. Turn/output bounding and the result-handling contract

How does the sub-agent know when to stop, and in what shape does its
answer arrive back at the orchestrator?

| Mechanism | Sources |
|---|---|
| **Hard turn cap with a forced-cutoff nudge message** injected on the last allowed turn | Copilot Chat — both sub-agents get "OK, your allotted iterations are finished..." on `isLastTurn`, pushing them to emit the required `<final_answer>` block rather than trailing off |
| **Turn cap as a template variable, no forced nudge described** | Goose (`{{max_turns}}` interpolated into the prompt; "Stop using tools once you have sufficient information" is a soft instruction, not an injected cutoff message) |
| **No stated turn limit in what's captured** | Claude Code, Amp, Gemini CLI, Crush, v0, Emergent, Google Antigravity |
| **No turn cap, but an explicit blocking-wait-with-timeout instead** — the orchestrator doesn't cap the sub-agent's own turns; it caps how long *it* will wait for a result | Codex CLI — `wait_agent` takes a `timeout_ms` and "returns empty status when timed out," leaving the child running rather than force-stopping it; a structurally different bounding mechanism from every turn-cap approach above, consistent with the sub-agent being a persistent addressable process rather than a single bounded call (see §2) |
| **A soft turn cap that nudges rather than force-stops** | OpenCode — an optional per-agent-type `steps` config; on the final allowed step, a synthetic trailing message (`MAX_STEPS_PROMPT`) is injected telling the model to wrap up, but nothing forcibly cuts off tool access the way Copilot Chat's forced `<final_answer>` cutoff does. No built-in agent type sets a default (`steps` defaults to unlimited). |
| **Status-typed observations with explicit failure-mode distinctions, not just free text** | OpenHands's new SDK — `TaskObservation`/`DelegateObservation` carry `status`/`is_error` fields; `TaskManager` distinguishes run-limit-hit, stuck, and paused terminal states from a clean finish, and preserves partial output even on failure rather than discarding it |
| **Strictly constrained output grammar** — the sub-agent's final message must match an exact format | Copilot Chat (`ExecutionSubagent`: command+summary pairs inside `<final_answer>`; `SearchSubagent`: bare `path:line-start-line-end` list, "ONLY" that tag) |
| **Structured-but-freeform** — a required section (e.g. Sources) but otherwise prose | Crush's `agentic_fetch` (mandatory `## Sources` section listing every URL used, answer text otherwise free-form) |
| **Free-text summary, no schema** | Claude Code ("a concise summary of the result" — no format specified), Amp's `Task`/`oracle` (same wording, inherited from the same lineage), Emergent (free-text "finish action" summary) |
| **Explicit distrust of the self-report — orchestrator must independently re-verify** | Emergent ("Please check the response from sub agent including git-diff carefully... Subagent sometimes is dull and lazy... or over enthusiastic"), Google Antigravity's `browser_subagent` ("you should read the DOM or capture a screenshot to see what it did" rather than trusting the report alone) |
| **Explicit trust instruction — take the report at face value** | Claude Code ("The agent's outputs should generally be trusted"), Composio SWE-Kit's integration playbook ("Always implement... EXACTLY as specified in the playbook returned") |
| **Structural mediation instead of a trust/distrust instruction** — the orchestrator isn't told to trust or verify a summary after the fact, because it's kept in the loop on risky actions *as they happen* | Codex CLI — `codex_delegate.rs` routes the sub-agent's exec/patch/permission/user-input approval requests up to the parent session rather than letting the child auto-resolve them; the parent doesn't see every intermediate model turn, but it does gate every risky action, which sidesteps the trust-the-summary question other sources have to answer explicitly |

**Takeaway**: this is the sharpest split in the whole comparison — some
sources (Claude Code, Composio's playbook role) instruct the
orchestrator to trust a sub-agent's self-report outright, while others
(Emergent, Google Antigravity) build in an explicit distrust-and-verify
step. Emergent's is the most pointed: it names both failure modes
("dull and lazy" under-delivery vs. "over enthusiastic" over-delivery)
and prescribes a concrete check (diff review) rather than leaving
verification to the orchestrator's judgment. Codex CLI's approval-routing
design is a genuinely different answer to the same underlying problem —
rather than choosing trust or verify-after-the-fact, it structurally
prevents the sub-agent from taking irreversible risky actions
unsupervised in the first place, which only works because its protocol
(§2) keeps the child addressable/interruptible instead of firing it off
stateless.

## 5. Concurrency and write-safety across sub-agents

Once an orchestrator can fire off more than one sub-agent, a new failure
mode appears that ordinary single-tool parallelism doesn't have: two
sub-agents editing the same file at once. Only a few sources address
this directly.

| Rule | Sources |
|---|---|
| **Explicit file-conflict-aware parallel/serial rule** | Gemini CLI ("NEVER run multiple subagents in a single turn if their abilities mutate the same files or resources... Only run multiple subagents in parallel when their tasks are independent") |
| **Per-sub-agent-type granularity, plus a worked good/bad example** | Amp — "Codebase Search agents: ...in parallel," "Task executors: ...in parallel **iff** their write targets are disjoint," with a concrete bad example (`Task(refactor)` and `Task(handler-fix)` both touching the same file "must serialize") — the most detailed concurrency policy captured in this collection |
| **Generic "launch multiple agents concurrently" encouragement, no conflict-safety caveat** | Claude Code ("Launch multiple agents concurrently whenever possible, to maximize performance") — notably *without* Gemini CLI's/Amp's same-file caveat |
| **A hard numeric concurrency cap, not a qualitative rule** | Codex CLI's `agent_jobs.rs` batch/CSV path caps concurrent spawned agents at 16 by default (max 64, configurable) — the only source in this collection with an actual number rather than a file-conflict heuristic; doesn't address same-file write conflicts directly, but bounds blast radius by construction |
| **A capacity/depth limit enforced by the coordinator infrastructure itself, independent of any prompt instruction** | Codex CLI's `AgentControl`/`AgentRegistry` enforce a max live-agent count with reservation-and-rollback semantics at spawn time — a systems-level guardrail rather than a rule the model is expected to follow voluntarily, distinct from every other row in this table (all of which are prompt instructions the model could in principle ignore); OpenHands's `DelegateExecutor` independently arrives at the same pattern with a hardcoded `max_children: int = 5`, and its `workflow` tool separately caps fan-out concurrency at `max_concurrency` (default 8, range 1–64) — three concrete numeric limits from two unrelated codebases, all enforced in code rather than by instruction |
| **Permission-system denial as the safety mechanism, not a concurrency rule at all** | OpenCode — no stated parallel/serial rule and no numeric cap; instead `deriveSubagentSessionPermission()` denies a sub-agent's own `task` tool by default (blocking runaway fan-out at the recursion layer — see §6) and ordinary per-file edit permission-ask rules apply to whatever a sub-agent does write, rather than a same-file lock across concurrently-running sub-agents |
| **Not addressed** | Cline (n/a — not a real sub-agent), Roo Code (n/a — no sub-agent at all), Copilot Chat, Crush, Goose, Composio SWE-Kit (structurally serial by design — one role active at a time), Emergent, Google Antigravity, v0 |

**Takeaway**: Claude Code's own "launch multiple agents concurrently"
instruction is a small but real gap relative to Gemini CLI's and Amp's
— maximize-performance guidance without a same-file-conflict caveat is
exactly the setup that produces the write-collision Amp's worked
example warns against.

## 6. Recursion and tool-scope limits

Can a sub-agent spawn its own sub-agents? Can it use every tool the
orchestrator can, or a deliberately narrower set?

| Rule | Sources |
|---|---|
| **Explicit no-recursion rule, stated in the sub-agent's own prompt** | Goose — "Security: Cannot spawn additional subagents," listed as one of five core characteristics. The only source in this collection that states this directly. |
| **Sub-agent tool scope narrower than the orchestrator's by design** | Claude Code (`statusline-setup`: `Read, Edit` only; `output-style-setup`: `Read, Write, Edit, Glob, LS, Grep`), Crush's search sub-agent (`glob, grep, ls, view` — no edit/bash), Amp's `oracle` (read-only: `list_directory, Read, Grep, glob, web_search, read_web_page` — no edit/bash, consistent with an advisory-only role), Composio SWE-Kit's `CODE_ANALYZER_PROMPT` ("you cannot modify files, execute shell commands, or directly access the file system") |
| **Sub-agent tool scope as broad as (or broader in composition than) a plain search delegate — can call other sub-agents itself** | Amp's `Task` — scoped to include `codebase_search_agent` among its own tools, meaning one sub-agent type can itself delegate to another, without an explicit recursion ban anywhere in the captured text |
| **Full tool parity with the orchestrator** | Claude Code's `general-purpose` type (`Tools: *`) |
| **Recursion allowed and structurally bounded (capacity/depth limit) rather than banned by rule** | Codex CLI — nested spawning (a spawned agent spawning its own children) appears permitted; `agent-graph-store`'s parent→child edges support arbitrary depth, and `AgentControl`'s capacity limit (§5) is what actually bounds it, not a prompt-level prohibition. A third position distinct from both "explicitly banned" (Goose) and "allowed with no stated limit at all" (Amp) — allowed, but enforced by infrastructure rather than by instruction or by silence. |
| **Recursion denied by default, per-agent-type grantable** — the most granular position in this table | OpenCode's `deriveSubagentSessionPermission()`: every sub-agent's own `task` tool (and `todowrite`) is denied unless its specific agent type's permission ruleset explicitly grants it — the `plan` agent, for instance, is allowed to spawn only the `general` subagent type and nothing else. Neither a blanket ban (Goose) nor silent allowance (Amp) nor infrastructure-capacity-bounded (Codex) — a per-type allowlist decided at agent-definition time. |
| **Recursion structurally *possible* but not exercised by any built-in — only reachable via a deliberately custom-authored agent definition** | OpenHands's new SDK — none of the four built-in `AgentDefinition` files (`bash-runner`/`code-explorer`/`web-researcher`/`general-purpose`) include the `task` or `delegate` tool in their own tool list, so out of the box, sub-agents can't recurse; a user or plugin author would have to deliberately build a custom agent definition that grants itself one of those tools. No code-level prohibition exists, unlike Goose's explicit ban — it's an emergent consequence of what ships by default, a fifth distinct position. |
| **Not addressed** | Gemini CLI, v0, Emergent (each named agent has an implicit fixed toolkit per its specialty, but no stated recursion rule), Google Antigravity |

**Takeaway**: this table now has five genuinely distinct positions, not
two — Goose's outright ban, Amp's apparent silent allowance, Codex's
infrastructure-capacity-bounded allowance, OpenCode's per-agent-type
allowlist decided at definition time, and OpenHands's "possible in
principle, absent from every built-in by omission." No two sources
converge on the same answer to "can a sub-agent itself delegate," and
unlike concurrency (§5, where three unrelated codebases converged on
similar numeric caps), recursion policy looks like the least-converged
design question in this entire survey.

## 7. Absences worth noting

- **Codex CLI, OpenHands, and OpenCode are not on this list, on
  correction — all three turned out to have real, and in Codex's and
  OpenHands's cases unusually sophisticated, sub-agent architectures**
  (see §2, §4, §5, §6). Called out here specifically because the
  omission (Codex, OpenCode) or under-coverage (OpenHands wasn't
  profiled at all originally) happened first: passes over only the
  prompt-text files stored in this collection's `codex/`/`opencode/`
  folders concluded there was little or no delegation mechanism, and
  OpenHands's actual agent implementation had moved to a separate repo
  (`OpenHands/software-agent-sdk`) never checked. See the methodology
  note at the end of §2 for what this implies about every other row
  below.
- **Leaked Cursor and leaked Windsurf — despite having two of the
  richest tool surfaces in this entire collection (see
  `agent-tool-surfaces.md` §§1–7, especially Windsurf's 30-tool
  browser/deployment/memory suite) — have no sub-agent/delegate tool in
  either extraction.** Tool-surface breadth and sub-agent capability are
  not the same axis: Windsurf invested in browser automation, deployment
  integration, and persistent memory instead of task delegation, while
  Claude Code, Gemini CLI, and (per the corrections above) Codex CLI,
  OpenCode, and OpenHands — all comparatively narrow, unglamorous tool
  surfaces by `agent-tool-surfaces.md`'s accounting — turn out to be
  exactly the sources that invested most heavily in delegation
  architecture. Worth taking as a real caution: Cursor's and Windsurf's
  sub-agent sections in this collection are *also* built from
  prompt/tool-JSON extractions of closed-source, leaked material with no
  live upstream repo to double-check against — unlike Codex/OpenCode/
  OpenHands, there's no way to go verify whether that absence is real or
  another instance of the same blind spot.
- **Benchmark-lineage agents (SWE-agent, mini-swe-agent, Live-SWE-agent,
  Augment SWE-bench Agent) have no sub-agent concept at all** —
  consistent with their single-tool-loop, one-shot-benchmark-run design;
  Live-SWE-agent's self-authored-tools capability (see
  `agent-tool-surfaces.md` §3) is the closest analog, and it's a script
  the same agent runs itself, not a second agent.
- **Roo Code's mode system is easy to mistake for sub-agent delegation
  and isn't one** — modes change what tools/persona the single active
  agent has, not how many agents are running (see its README's "Sub-agents"
  section for the full argument). Worth flagging because Roo Code is a
  Cline fork, and Cline's `new_task` is *also* not real delegation (§2
  above) — neither half of this fork lineage has genuine sub-agent
  spawning in what's captured here, despite both having a tool literally
  named `new_task`/mode-adjacent language that reads like it might.

---

## Design takeaways

- **"Sub-agent" spans at least three different architectures in this
  collection, not one pattern with minor variations**: a stateless
  tool-call-and-report delegate (Claude Code, Gemini CLI, OpenCode,
  Crush, v0, Amp), a fixed multi-role team sharing one conversation via
  keyword handoffs (Composio SWE-Kit), and an asynchronous background
  distillation process the orchestrator only consumes output from
  (Google Antigravity's Knowledge Subagent). Treating all "delegation"
  mentions across sources as the same mechanism would blur a real
  architectural difference.
- **Amp's three-sub-agent menu (Task/Oracle/Codebase-Search-Agent) is
  the most sophisticated delegation design surveyed here**, specifically
  because it's the only one that varies the *model* per sub-agent
  (Oracle on o3) rather than just the tool scope and prompt — every other
  source's sub-agent runs on the same underlying model as the
  orchestrator (or doesn't specify), making model choice itself a lever
  only Amp pulls.
- **Trust-the-report vs. verify-the-report is a real, unresolved split**,
  not a convergence: Claude Code and Composio's playbook role tell the
  orchestrator to trust sub-agent output outright; Emergent and Google
  Antigravity build explicit re-verification into the workflow. Given
  that sub-agent reports are, by construction, unverified self-summaries
  the orchestrator can't audit step-by-step (true across nearly every
  source per §2's statelessness), Emergent's "check the git-diff, don't
  just trust the summary" instinct reads as the more defensible design,
  though it does cost the orchestrator some of the context-savings that
  motivated delegation in the first place (§1).
- **Recursion policy is almost entirely unaddressed, and the two
  sources that do address it disagree** (§6) — Goose bans it outright in
  the sub-agent's own prompt, Amp's `Task` tool is scoped to include
  another sub-agent tool with no caveat. This is the least-converged
  design question in the whole survey.
- **Tool-surface richness and sub-agent investment are independent
  axes** (§7) — the two richest tool surfaces in this collection
  (Cursor, Windsurf) have no delegation mechanism at all, while several
  comparatively narrower-tool-surface sources (Claude Code, Gemini CLI,
  Amp) invested specifically in sub-agent architecture. Where a given
  product spends its complexity budget looks like a real product
  decision, not something that falls out of overall sophistication.
- **The naming collision worth remembering**: `new_task` (Cline),
  Roo Code's mode system, and Claude Code's `Task` tool all *sound* like
  the same capability and are not — only the last one is genuine
  spawn-and-report delegation. When comparing scaffolds by tool name
  alone, always check the actual protocol (§2) before assuming
  equivalence.
- **Codex CLI's `spawn_agent` family, OpenCode's `task` tool, and
  OpenHands's `delegate`/`task`/`workflow` trio are, in some order, the
  three most architecturally advanced sub-agent designs in this
  collection** — and all three were found by going back and checking
  live source after a prompt-text-only pass undersold each one. Codex
  combines a persistent addressable child with mid-flight steering and
  infrastructure-enforced safety limits; OpenCode independently arrives
  at addressable statefulness via a generic background-job primitive
  plus a promote-to-background escape hatch; OpenHands goes furthest of
  all, layering true multi-threaded parallel delegation *and* a
  constrained map-reduce/pipeline orchestration DSL (`workflow`) on top
  of an addressable `task`/`delegate` primitive that itself matches
  Codex's sophistication. Every other source in this survey picks one
  point on the stateless-call spectrum and a prompt-level policy for
  safety; these three each pick a different, more systems-engineered
  point on the spectrum (stateful, long-lived, interruptible,
  infrastructure-bounded) and back their safety properties with code
  guarantees rather than asking the model to follow a rule.
- **Convergent design across three unrelated codebases is itself a
  finding**: Codex, OpenCode, and OpenHands arrived independently at
  "spawn returns an addressable id, later calls reference it, the
  orchestrator can send follow-ups" — and OpenHands's own history shows
  this convergence happening *within* one product over time too (its
  0.60.0-era `AgentDelegateAction` was strictly one-at-a-time
  cooperative-blocking; the current SDK redesign lands on the same
  addressable/parallel shape the other two independently reached).
  When three unconnected engineering teams converge on the same
  protocol shape, that's stronger evidence it's the "right" design for
  this problem than any single source's choice would be on its own.
- **The Codex/OpenCode/OpenHands corrections are, together, the most
  important methodological finding in this document**: an absence in a
  prompt-text-only or tool-JSON-only extraction is evidence of nothing
  beyond "not mentioned in that text." All three looked capability-poor
  or capability-free on this exact axis right up until someone checked
  the actual source, at which point each turned out to be among the
  richest examples in the survey. Every "no sub-agent mechanism" claim
  elsewhere in this document rests on the same kind of extraction and
  should be read with the same discount — absence of evidence, not
  evidence of absence.
