# Sub-agents: when a scaffold spawns another agent

A second drill-down alongside [`agent-tool-surfaces.md`](./agent-tool-surfaces.md),
this time on a single capability that turned out to have far more
internal variety than "delegate a task to a helper agent" suggests: what
protocol the orchestrator and sub-agent speak, what (if any) system
prompt the sub-agent runs under, how its result gets back into the
orchestrator's context, and what happens if two sub-agents run at once.

Grounded directly in each source's own "## Sub-agents" (or equivalent)
README section (all re-read from the files in this repo at time of
writing). 21 sources have one — a mix of the "coding agent" core
collection and several `leaked/` sources whose tool JSON turned out to
carry unusually detailed sub-agent specifications once actually read
closely, plus five sources (Codex CLI, OpenHands, Roo Code, SWE-agent,
Microsoft Agent Framework) added and two (OpenCode, Gemini CLI)
substantially deepened, after prompt-text-only passes badly undersold
what was actually there — see the methodology note at the end of §2.

## Sources covered

Claude Code (leaked), the general Anthropic assistant prompts (leaked),
OpenCode, Cline, Roo Code, Codex CLI, OpenHands, SWE-agent, Gemini CLI,
GitHub Copilot Chat, Crush, Goose, Composio SWE-Kit, Microsoft Agent
Framework (via `codeact-hyperlight/`), Amp (leaked), Emergent (leaked),
Google Antigravity (leaked), v0 (leaked), GitHub Copilot CLI (leaked —
eight fully-captured sub-agent prompts, an SQL-mediated fan-out
concurrency model, and a novel ambient "sidekick" agent pattern; a
distinct product from GitHub Copilot Chat above, see
`leaked/github-copilot-cli/README.md`), Grok Build (leaked — a typed
four-agent registry addressable via a shared task-ID space, and a
`codex:codex-rescue` agent type that echoes leaked Cursor's own
`codex-rescue` `subagent_type` almost exactly — see the note under §2
below), and Zed (genuinely open
source — a prompted-only "when to delegate" section, gated on a tool
literally named `spawn_agent` like Codex CLI's, but with no schema or
calling-convention detail captured for Zed's version — see
`zed/README.md`'s Sub-agents section). Sources with **no**
sub-agent mechanism found — Aider, mini-swe-agent, Live-SWE-agent,
Augment SWE-bench Agent, Bolt.new, Pi, and (notably, given how rich
their tool surfaces are — see `agent-tool-surfaces.md` §§1–7) leaked
Windsurf — are covered only in the "Absences" section below, not
individually profiled. **Leaked Cursor is a partial correction, not a
clean absence**: five of its six captured prompt files still show no
delegation mechanism, but a sixth, differently-provenanced capture
(`Agent Prompt (asgeirtj capture).md`, mirrored from a different
aggregator than the other five — see `leaked/cursor/README.md`) has a
real `Task` tool with seven named `subagent_type`s, described only at
the one-line level with no schema/protocol detail — thin enough that
it isn't given its own profiled section below, but real enough that
Cursor can no longer be grouped with Windsurf as a confirmed clean
absence; see the Absences section for the full writeup. Unlike most
other sources here, Codex
CLI's, OpenHands's, Roo Code's, SWE-agent's, and Microsoft Agent
Framework's sub-agent sections (and half of OpenCode's and Gemini
CLI's) are sourced from reading live upstream repos directly rather
than from a prompt/tool-JSON file stored in this collection — see each
README for why.

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
| **Coordination across specialties on complex, multi-step projects** — a whole mode exists for nothing else | Roo Code's Orchestrator mode ("Use this mode for complex, multi-step projects that require coordination across different specialties... break down large tasks into subtasks, manage workflows, or coordinate work that spans multiple domains") — the trigger isn't a tool description at all, it's an entire persona whose only job is deciding when and how to delegate |
| **Not "delegate part of the task" at all — "run the whole task N times and pick the best attempt"** | SWE-agent's `RetryAgentConfig`/reviewer architecture — triggered by wanting higher solution quality through ensembling, not context conservation or specialization; see §2 for why this is a structurally different category from every other row in this table |
| **Five different triggers for five different relationship topologies**, bundled as named patterns rather than one generic "delegate" instinct | Microsoft Agent Framework — "run these in order, each building on the last" (Sequential), "get N independent takes on the same input" (Concurrent), "route to the specialist who owns this" (Handoff — the framework's own docs position it as AutoGen `Swarm`'s successor, e.g. customer-support triage), "let named participants discuss until someone decides it's done" (GroupChat), "plan, delegate, monitor progress, replan on stall, for open-ended work" (Magentic — the framework's own samples position this for deep-research-style tasks). See §7 for the full pattern breakdown. |
| **Role-inversion framing** — the orchestrator is told its own job changes once sub-agents exist, plus an explicit anti-overuse guardrail for one specific agent type | GitHub Copilot CLI (leaked) — "When relevant sub-agents are available, your role changes from a coder making changes to a manager of software engineers. Your job is to utilize these sub-agents to deliver the best results as efficiently as possible" — close in spirit to OpenHands's own delegation framing (row above); its `explore` agent is separately gated with "Do not speculatively launch explore agents in the background 'just in case' — they consume resources and rarely finish before you've already found the answer yourself." |
| **Both context conservation and speed, stated together, for the same delegate** | Grok Build (leaked) — `spawn_subagent`: "valuable for parallelizing independent queries and for protecting the main context window from excessive results" — the same two-part framing this table already documents separately for Claude Code/OpenCode/Crush/v0 (speed) and Gemini CLI/OpenCode/Claude Code/Amp (context conservation), here combined into one sentence for one tool rather than split across separate delegate types |

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
| **Model-driven, dynamic agent *definition* — the orchestrator can create new sub-agent types on the fly, not just invoke pre-registered ones** — not matched by any other source in this survey | Google Antigravity's CLI harness (leaked, `CLI Prompt.md`): `define_subagent` lets the model author a brand-new sub-agent definition "available for the duration of this conversation," then `invoke_subagent` calls it by name; a separate `send_message` tool addresses an already-running instance by conversation ID, with an explicit carve-out that it must never substitute for user-facing text. No parameter schema or named example is captured for either tool, and the notification model is stated as reactive rather than poll-based ("you do NOT need to poll or check your inbox in a loop... you will be notified when there is a message to process"). This is the only source in this collection where the *set of available sub-agent types itself* is something the model can expand, rather than choosing among a fixed registry (contrast Claude Code's/Gemini CLI's typed-registry row above) — closest in spirit to §7's N-party orchestration flexibility, but expressed as a two-party primitive (define, then invoke) rather than a named topology. |
| **Tool call → persistent, addressable child, not stateless one-shot** — spawn returns an id the orchestrator can message, interrupt, and block-wait on across *multiple, separate* follow-up tool calls, rather than one call that blocks until a final report | Codex CLI — `spawn_agent` returns an agent id; `send_input` (optionally with `interrupt: true`) messages it again later; `wait_agent` blocks on one or more ids with a timeout; `close_agent` tears it down. OpenCode's `task` tool independently converges on the same shape via a different mechanism: calling `task` again with an already-running `task_id` doesn't error, it gets queued onto the still-live job (`background.extend()`) and returns immediately — a genuine follow-up-to-a-running-sub-agent capability built on a generic `BackgroundJob` primitive rather than a purpose-built agent-session protocol. OpenHands's new-SDK `delegate` tool (`spawn` once, then repeated `delegate` calls by `agent_id`) and `task` tool (`resume: <task_id>`) are two more independent arrivals at the same shape. |
| **Hybrid: blocking by default, but can detach to background mid-flight and reattach via a synthetic follow-up message** | OpenCode — a `task` call races the sub-agent finishing against being *promoted* to background (interrupted-but-not-killed); if promoted, the tool call returns immediately and a forked watcher later injects the final result back into the parent session as a `synthetic: true` message rather than a tool result. Distinct from Codex's/OpenHands's explicit poll-or-wait model — here the transition from sync to async can happen unpredictably mid-call, gated behind an experimental flag (`OPENCODE_EXPERIMENTAL_BACKGROUND_SUBAGENTS`). |
| **True parallel execution via real OS threads, not sequential/cooperative turn-taking** — multiple sub-agents genuinely run concurrently, joined when done | OpenHands's `delegate` tool: `DelegateExecutor._delegate_tasks` spins up one Python thread per named sub-agent and `.join()`s them, capped at `max_children: int = 5`. Contrast with OpenHands's own *prior* (0.60.0) design, `AgentDelegateAction`, which was strictly one-delegate-at-a-time cooperative blocking within a single event loop — a real protocol upgrade across the two generations of the same product, not just an addition. |
| **A fan-out/fan-in orchestration DSL layered on top of a delegate primitive**, not just a single spawn call | OpenHands's `workflow` tool — `wf.map_agents(items, prompt, max_concurrency=...)`, `wf.reduce_agent(...)`, `wf.pipeline(items, *stages)` (staged, non-barriered — a fast item can reach a later stage while a slow item is still on an earlier one) exposed as a constrained Python sandbox API. The most structurally distinct protocol shape in this survey among *two-party* delegation designs — every other row here is "one call, one (or one resumable) sub-agent"; this is a small map-reduce/DAG engine over many. (Microsoft Agent Framework's five orchestration patterns, §7, go further still into genuinely N-party topologies — not covered in this table.) |
| **Stateful and addressable, but strictly sequential (one LIFO stack, not concurrent) — result delivered via deferred injection into the parent's own history, not a synchronous return** | Roo Code's `new_task` + Orchestrator mode: pushes a new `Task` onto a `clineStack`, suspending (not destroying) the parent; only the top of the stack is ever active, so this is *effectively* blocking despite being implemented as a session-stack switch rather than an in-process function call. When the child calls `attempt_completion`, its summary is injected back into the parent's actual conversation history as the deferred tool result for the original delegation call — the parent literally cannot take its next turn until that happens. A fourth independent arrival at "addressable, not one-shot," but (with Codex/OpenCode/OpenHands) one of only two of the five (with Grok Build, row below) that's single-threaded by construction rather than supporting real concurrency. |
| **A fifth independent arrival, via a shared task-ID space spanning both background commands and sub-agents, plus an explicit resume-a-completed-conversation capability** | Grok Build (leaked) — `spawn_subagent` returns a handle polled via `get_command_or_subagent_output` and terminated via `kill_command_or_subagent`, the same shape Codex's `spawn_agent`/`wait_agent`/`close_agent` trio has; its own distinguishing feature is `resume_from`: "Resume from a previously completed subagent's conversation. Pass the subagent_id returned by a prior call" — closer to re-opening a finished session than to Codex's mid-flight `send_input`/`interrupt` (which steers a *still-running* child) or OpenCode's queue-onto-a-still-live-job model. `wait_commands_or_subagents`' `wait_any`/`wait_all` modes additionally let the orchestrator block on several spawned agents (or background commands) at once through the same primitive — see `agent-tool-surfaces.md` §6. |
| **Not delegation at all — a fundamentally different category: N full independent attempts at the whole task, judged afterward by a separate model call** | SWE-agent's `RetryAgentConfig` (`sweagent/agent/reviewer.py`): a `ScoreRetryLoop` runs a `Reviewer` LLM call (distinct system/instance prompts, not sharing cost accounting with the main agent) that scores each complete attempt and decides whether to run another; a `ChooserRetryLoop` runs several attempts to exhaustion, then a separate `Chooser` call (optionally preceded by a `Preselector` call) picks the best. This doesn't fit the "orchestrator delegates a sub-task, gets a partial result back" framing every other row in this table shares — it's ensemble generate-then-judge over *whole* task attempts, closer in spirit to Augment SWE-bench Agent's `ensembler_prompt.py`/majority-vote mechanism (already documented in this collection) than to any delegation design here. Worth naming as its own category rather than shoehorning into "stateless one-shot" or "addressable." |

**Takeaway**: Cline's `new_task` is worth flagging as a trap for anyone
skimming tool names across sources — it's lexically adjacent to Claude
Code's `Task` *and to Roo Code's tool of the exact same name*, and
means something different in all three: pure user-facing context
handoff in Cline, real hierarchical delegation in Roo Code, synchronous
in-process delegation in Claude Code. Composio SWE-Kit's keyword-handoff
pipeline is a different kind of structural outlier — every
stateless-tool-call source treats "sub-agent" as one call with a return
value; Composio treats it as a fixed sequence of roles sharing one
conversation; Codex, OpenCode, OpenHands, and Roo Code each
independently treat it as a *live, continuing* child process the
orchestrator keeps a handle to — four unrelated codebases converging on
the same "addressable, not stateless" shape is a real signal, not a
coincidence, even though Roo Code's version is uniquely single-threaded
among the four. OpenHands's `workflow` DSL and Microsoft Agent
Framework's five orchestration patterns (§7) both push further still
into genuine multi-party orchestration rather than single-child
addressing — and SWE-agent's reviewer/retry architecture shows that not
everything that *looks* sub-agent-adjacent is delegation at all.

**A notification-driven, non-blocking variant, distinct from every
addressable-child design above**: GitHub Copilot CLI (leaked) — its
`task` tool description frames delegation as scope *ownership*, not a
one-shot call: "Once you delegate a scope to an agent, that agent owns
it until it completes or fails; do not investigate the same scope
yourself." A separate "Background Agents" protocol governs the
notification path: "After launching a background agent for work you
need before your next step, tell the user you're waiting, then end your
response with no tool calls. A completion notification will arrive
automatically... call `read_agent` once with `wait: true`." Closer to
Codex CLI's/OpenCode's addressable-child shape than to Claude Code's
blocking one-shot `Task`, but the orchestrator explicitly ends its own
turn (no tool calls) while waiting rather than polling or blocking
in-call — a fifth data point for "addressable, not stateless," with its
own distinct idle-and-wait mechanic.

**A methodology note, since most rows in this document were added or
substantially corrected after an initial pass undersold them**: my
first pass on Codex CLI concluded it had no sub-agent mechanism at all;
on OpenCode, the Task tool was mentioned in prompt instructions but its
actual protocol was never found; OpenHands wasn't covered as a source
at all; Roo Code was concluded to have no delegation mechanism; Gemini
CLI's `codebase_investigator` was documented only from the
orchestrator's side; SWE-agent's bundles were never opened, only
speculated about from their names; Microsoft Agent Framework's entire
multi-agent orchestration layer was invisible from the one narrow
CodeAct-related package this collection had fetched. Seven corrections,
all tracing to the same cause: the only material actually stored in
this collection for each of these sources is prompt *text*, a partial
tool-JSON extraction, or (for Microsoft Agent Framework) one specific
feature's source tree — and the real delegation/orchestration
machinery for every one of them ships as separate source that was
never fetched in. The lesson generalizes: for every source in this
survey whose sub-agent findings come from a prompt-text or tool-JSON
*extraction* rather than full source (which, after these seven
corrections, is now a minority of the sources profiled here — see
"Sources covered" above), an absence in this doc means "not mentioned
in the captured prompt/tool text," not "confirmed not to exist." Treat
every row in §8 ("Absences") as provisional on that basis, not as a
verified negative.

## 3. Does the sub-agent get its own system prompt?

The question the user's request specifically asked about, and the one
with the most uneven documentation across sources — most tool JSON
extractions only capture the *orchestrator-facing tool description* that
triggers delegation, not what prompt (if any) the spawned agent itself
runs under.

| Sub-agent system prompt fully captured? | Sources |
|---|---|
| **Yes — complete, standalone prompt file(s)** | Copilot Chat (`executionSubagentPrompt.tsx`: "You are an AI coding research assistant that runs a series of terminal commands..."; `searchSubagentPrompt.tsx`: "...that uses search tools to gather information..."), Crush (`task.md.tpl`: "You are an agent for Crush..."; `agentic_fetch_prompt.md.tpl`: "You are a web content analysis agent for Crush..."), Goose (`subagent_system.md`: "You are a specialized subagent within the goose AI framework... You were spawned by the main goose agent"), OpenHands (four built-in `AgentDefinition` Markdown files — `bash-runner`, `code-explorer`, `web-researcher`, `general-purpose` — each with a distinct role-specific prompt body, e.g. `code-explorer`'s explicitly forbids any file-modifying command and whitelists specific read-only shell commands), GitHub Copilot CLI (leaked — eight complete sub-agent YAML files with embedded prompts: `code-review`, `explore`, `rem-agent`, `research`, `rubber-duck`, `sidekick/github-context`, `sidekick/subconscious-agent`, `task`; each carries an explicit per-role model pin, e.g. `code-review`/`research` on `claude-sonnet-4.5`/`claude-sonnet-4.6`, `explore`/`task` on the cheaper `claude-haiku-4.5`, and `rubber-duck`'s model deliberately left unset — "selected dynamically at runtime based on user's current model preference," a fourth model-assignment strategy alongside Amp's fixed-per-role pinning, Claude Code's uniform-Haiku-for-titling, and "unspecified" found elsewhere: explicitly inherit the parent's live model choice rather than pin one) |
| **Yes, but as an either/or *replacement* of the base prompt rather than an addition** | OpenCode — a sub-agent's `prompt` field, when its agent type defines one, entirely replaces the model-family base prompt (`session/llm/request.ts`) rather than appending to it; `explore` (read-only, its own dedicated persona) has one, `general` (full tool parity) doesn't and falls through to the same base prompt the orchestrator itself uses. Custom agents are also definable as Markdown+YAML-frontmatter files, the same convention OpenHands independently converges on. |
| **Yes — a genuinely separate model call with its own captured prompts, though not a "delegated sub-task" in the usual sense** | SWE-agent's `Reviewer`/`Chooser`/`Preselector` (`sweagent/agent/reviewer.py`) each have their own `system_template`/`instance_template`, fully distinct from the main agent's — the clearest "yes" in this table by one measure (real, separate, captured prompts) even though the *relationship* (judge a completed attempt, not perform a sub-task) doesn't match what every other "Yes" row is doing |
| **No — only the orchestrator-side tool/call description is captured, not the sub-agent's own prompt** | Claude Code, v0, Emergent (six named agents, no prompt text for any of them), Google Antigravity's `browser_subagent`, Grok Build (leaked — all four `spawn_subagent` types described only from the caller's side) |
| **Yes, but only a single generic delegate prompt, not per-sub-agent-type prompts** | Amp — the two YAML captures (`claude-4-sonnet.yaml`/`gpt-5.yaml`) only had the orchestrator-side `Task`/`oracle`/`codebase_search_agent` tool descriptions (as the "No" row above used to say of all three), but a later, richer binary-string capture (`leaked/amp/amp-code.md`) supplies `H_R`, the actual generic subagent prompt run when `Task` spawns a worker: "You are [specialAgentName or 'Amp'], a powerful AI coding agent" plus a compact ruleset (absolute paths only, read each file once, treat AGENTS.md as ground truth, prefer `finder` for discovery) — one shared prompt for the delegate role, not a distinct prompt per sub-agent type the way Claude Code's typed registry implies it might have. |
| **No, and confirmed rather than just uncaptured — the delegated task reuses whichever mode's normal prompt applies, no distinct delegate-mode prompt exists** | Roo Code — `new_task`'s `mode` parameter selects an ordinary Roo Code mode (Code/Ask/Debug/Architect/etc.) for the child task, which then runs that mode's regular system prompt; there is no special "you are a delegated sub-agent" framing anywhere in the confirmed source |
| **Partial — a role-based config/persona layer confirmed to exist, but the actual prompt text per role wasn't read** | Codex CLI — `agent/role.rs` defines named roles (`"default"`, `"explorer"`, `"worker"`) with distinct behavioral framing and the ability to override model/reasoning/service-tier per role, loaded through the same config machinery as `config.toml`; closer to Claude Code's typed `subagent_type` registry than to a single generic delegate, but not confirmed as a fully-captured standalone system prompt the way Copilot Chat/Crush/Goose/OpenHands are |
| **Confirmed to exist and be fully distinct per participant, but not "sub-agent" prompts in the delegation sense** | Microsoft Agent Framework — every orchestration participant is a full `Agent` object with its own `instructions` field, untouched/untemplated by the orchestration layer; the one orchestration-specific prompt set found is the **Magentic manager's** own multi-stage prompts (facts/plan/progress-ledger/final-answer) — a single coordinator prompt, not a per-participant one. See §7. |
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
- **SWE-agent's Reviewer/Chooser have no "sub-agent" framing at all** —
  they're framed purely as an evaluator role ("score this attempt,"
  "pick the best of these attempts"), with no acknowledgment that
  they're part of a multi-call pipeline let alone that another model
  produced what they're judging.
- **Microsoft Agent Framework's participants have no delegation framing
  either, for a structural reason**: nothing in the orchestration layer
  templates or wraps a participant's `instructions` — a participant is
  configured as a normal, standalone agent and literally doesn't know
  it's operating inside a Sequential chain, a Handoff swarm, or a
  Magentic team unless its own author wrote it to expect that context.

## 4. Turn/output bounding and the result-handling contract

How does the sub-agent know when to stop, and in what shape does its
answer arrive back at the orchestrator?

| Mechanism | Sources |
|---|---|
| **Hard turn cap with a forced-cutoff nudge message** injected on the last allowed turn | Copilot Chat — both sub-agents get "OK, your allotted iterations are finished..." on `isLastTurn`, pushing them to emit the required `<final_answer>` block rather than trailing off |
| **Turn cap as a template variable, no forced nudge described** | Goose (`{{max_turns}}` interpolated into the prompt; "Stop using tools once you have sufficient information" is a soft instruction, not an injected cutoff message) |
| **No stated turn limit in what's captured** | Claude Code, Amp, Gemini CLI, Crush, v0, Emergent, Google Antigravity |
| **No turn cap, but an explicit blocking-wait-with-timeout instead** — the orchestrator doesn't cap the sub-agent's own turns; it caps how long *it* will wait for a result | Codex CLI — `wait_agent` takes a `timeout_ms` and "returns empty status when timed out," leaving the child running rather than force-stopping it; a structurally different bounding mechanism from every turn-cap approach above, consistent with the sub-agent being a persistent addressable process rather than a single bounded call (see §2). Grok Build (leaked) independently converges on the same shape — `get_command_or_subagent_output`'s `block`/`timeout_ms` params, plus `wait_commands_or_subagents`' `wait_any`/`wait_all` for capping a wait across *several* spawned agents at once, something Codex's single-target `wait_agent` doesn't offer. |
| **A soft turn cap that nudges rather than force-stops** | OpenCode — an optional per-agent-type `steps` config; on the final allowed step, a synthetic trailing message (`MAX_STEPS_PROMPT`) is injected telling the model to wrap up, but nothing forcibly cuts off tool access the way Copilot Chat's forced `<final_answer>` cutoff does. No built-in agent type sets a default (`steps` defaults to unlimited). |
| **Status-typed observations with explicit failure-mode distinctions, not just free text** | OpenHands's new SDK — `TaskObservation`/`DelegateObservation` carry `status`/`is_error` fields; `TaskManager` distinguishes run-limit-hit, stuck, and paused terminal states from a clean finish, and preserves partial output even on failure rather than discarding it |
| **No stated turn limit found**, and the "output" isn't a report at all but a blocking session-stack transition | Roo Code — no `new_task`/Orchestrator turn or token cap found in the confirmed source |
| **Self-monitoring with automatic replan on detected stall**, a mechanism found nowhere else in this table | Microsoft Agent Framework's Magentic manager: tracks a stall counter across progress-ledger rounds, and on exceeding `max_stall_count` triggers `replan()` (a fresh facts/plan pass) plus a reset signal broadcast to all participants, bounded overall by `max_rounds`/`max_resets`. Every other bounding mechanism in this table is a static cap or timeout; this is the only one that detects *lack of progress* specifically and reacts by changing the plan rather than just stopping. |
| **A hard, enumerated tool-allowlist bound on the orchestrator itself**, not the sub-agent — the strongest "you must delegate" enforcement in this table | GitHub Copilot CLI's leaked "Research Orchestrator" mode: confined to exactly four tools (`task`, `create`, `view`, `report_intent`), with an explicit forbidden list naming `bash`, `grep`, `glob`, `web_fetch`, `web_search`, every `github-mcp-server-*` tool, `read_agent`, and `ask_user` — "You are ONLY allowed to use these tools... If you catch yourself about to use a forbidden tool, STOP and dispatch a research subagent instead." Every other row in this section bounds the *sub-agent's* turns or output; this bounds the *orchestrator's own* tool access instead, turning it into a pure dispatcher by prompt-level constraint rather than by discipline alone (no code-level enforcement is confirmed, since only prompt text was captured). |
| **Strictly constrained output grammar** — the sub-agent's final message must match an exact format | Copilot Chat (`ExecutionSubagent`: command+summary pairs inside `<final_answer>`; `SearchSubagent`: bare `path:line-start-line-end` list, "ONLY" that tag) |
| **Structured-but-freeform** — a required section (e.g. Sources) but otherwise prose | Crush's `agentic_fetch` (mandatory `## Sources` section listing every URL used, answer text otherwise free-form) |
| **Free-text summary, no schema** | Claude Code ("a concise summary of the result" — no format specified), Amp's `Task`/`oracle` (same wording, inherited from the same lineage), Emergent (free-text "finish action" summary) |
| **Explicit distrust of the self-report — orchestrator must independently re-verify** | Emergent ("Please check the response from sub agent including git-diff carefully... Subagent sometimes is dull and lazy... or over enthusiastic"), Google Antigravity's `browser_subagent` ("you should read the DOM or capture a screenshot to see what it did" rather than trusting the report alone) |
| **Explicit trust instruction — take the report at face value** | Claude Code ("The agent's outputs should generally be trusted"), Composio SWE-Kit's integration playbook ("Always implement... EXACTLY as specified in the playbook returned") |
| **Structural mediation instead of a trust/distrust instruction** — the orchestrator isn't told to trust or verify a summary after the fact, because it's kept in the loop on risky actions *as they happen* | Codex CLI — `codex_delegate.rs` routes the sub-agent's exec/patch/permission/user-input approval requests up to the parent session rather than letting the child auto-resolve them; the parent doesn't see every intermediate model turn, but it does gate every risky action, which sidesteps the trust-the-summary question other sources have to answer explicitly |
| **A structural variant of mediation**: the "orchestrator" (parent task) is blocked until the child finishes, so there's no window where an untrusted summary could be acted on prematurely — but nothing gates the child's *actions* the way Codex's approval-routing does | Roo Code — the parent literally cannot resume until `attempt_completion` fires and injects the result; this prevents "acting on a stale/wrong summary while the child is still working" but doesn't provide Codex's per-action approval gate, and no explicit trust/verify instruction was found either |
| **Quantified trust, decided by a dedicated scoring model rather than a prompt instruction to the orchestrator** | SWE-agent's `ScoreRetryLoop` — a `Reviewer` LLM assigns a numeric acceptance score to a completed attempt (optionally sampled multiple times for self-consistency, averaged and variance-penalized), and that score — not an instruction to the orchestrator about how much to trust free text — decides whether the attempt is accepted or another is run. The only source in this survey where "how much to trust the result" is itself computed by a model call rather than stated as a policy. |

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
| **Concurrency is architecturally impossible, not merely unaddressed** — a genuinely different case from "no rule stated" | Roo Code — the single LIFO `clineStack` means only one task (root or delegated) is ever active at a time by construction; there's nothing to write a same-file-conflict rule *about*, since simultaneous sub-agents can't exist in this design at all |
| **True parallel fan-out is the default mode for one whole orchestration pattern**, with an explicit aggregation step to reconcile results rather than a same-file-conflict rule | Microsoft Agent Framework's Concurrent pattern — every participant gets the same input and runs simultaneously with an *isolated* conversation (not shared, so no mid-run interference possible by construction), and a default or custom aggregator combines their independent outputs afterward. Sidesteps the write-conflict problem the same way Roo Code sidesteps it, but by the opposite extreme — always-parallel-but-isolated instead of always-sequential. |
| **SQL rows, not a DSL or object graph, as the coordination substrate for parallel dispatch** | GitHub Copilot CLI's leaked "Fleet Mode": dispatches sub-agents off a shared `todos`/`todo_deps` SQL schema rather than a workflow DSL (contrast OpenHands's `wf.map_agents`) or a Builder-configured topology (contrast Microsoft Agent Framework) — "Query ready todos: `SELECT * FROM todos WHERE status = 'pending' AND id NOT IN (SELECT todo_id FROM todo_deps td JOIN todos t ON td.depends_on = t.id WHERE t.status != 'done')`," with each dispatched sub-agent responsible for updating its own row's status on completion and an explicit anti-single-agent rule ("Never dispatch just a single background subagent"). No same-file-conflict caveat is stated (unlike Gemini CLI's/Amp's), but the dependency graph itself is what prevents genuinely conflicting work from running concurrently in the first place. |
| **A structurally novel concurrency pattern: ambient, self-triggered, budget-capped background agents that inject into a shared inbox rather than being invoked by the orchestrator at all** | GitHub Copilot CLI's leaked "sidekick" agents (`sidekick/github-context`, `sidekick/subconscious-agent`) — both declare `triggers: [user.message]`, `cancelOnNewTurn: true`, `maxSendsPerTurn: 1`, a `featureFlag`, and `launchConditions` (e.g. `hasMemories`); each fires on every user turn, decides independently whether it has anything worth surfacing ("If the board is empty, stop immediately — do not call `send_inbox`"), and pushes at most one ≤500-character entry for the main agent to read. Closest existing analog is Google Antigravity's Knowledge Subagent (§2's "async background process" row), but with explicit machine-readable gating (trigger/cancel/budget/feature-flag/launch-condition fields) not captured for Antigravity's version — worth naming as its own concurrency category: the orchestrator never decides to spawn these at all. |
| **Not addressed** | Cline (n/a — not a real sub-agent), Copilot Chat, Crush, Goose, Composio SWE-Kit (structurally serial by design — one role active at a time), Emergent, Google Antigravity, v0, SWE-agent (multiple full attempts confirmed, but not confirmed whether run in parallel or sequentially), Grok Build (leaked — only the tool-agnostic general parallelism guidance under `<tool_calling>` applies; no sub-agent-specific same-file-conflict caveat found) |

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
| **Sub-agent tool scope narrower than the orchestrator's by design** | Claude Code (`statusline-setup`: `Read, Edit` only; `output-style-setup`: `Read, Write, Edit, Glob, LS, Grep`), Crush's search sub-agent (`glob, grep, ls, view` — no edit/bash), Amp's `oracle` (read-only: `list_directory, Read, Grep, glob, web_search, read_web_page` — no edit/bash, consistent with an advisory-only role), Composio SWE-Kit's `CODE_ANALYZER_PROMPT` ("you cannot modify files, execute shell commands, or directly access the file system"), Grok Build (leaked — `explore` scoped to `run_terminal_command`/`read_file`/`list_dir`/`grep` only; `plan` broader still but excludes `search_replace` specifically, "all tools except search_replace") |
| **Sub-agent tool scope as broad as (or broader in composition than) a plain search delegate — can call other sub-agents itself** | Amp's `Task` — scoped to include `codebase_search_agent` among its own tools, meaning one sub-agent type can itself delegate to another, without an explicit recursion ban anywhere in the captured text |
| **Full tool parity with the orchestrator** | Claude Code's `general-purpose` type (`Tools: *`) |
| **Recursion allowed and structurally bounded (capacity/depth limit) rather than banned by rule** | Codex CLI — nested spawning (a spawned agent spawning its own children) appears permitted; `agent-graph-store`'s parent→child edges support arbitrary depth, and `AgentControl`'s capacity limit (§5) is what actually bounds it, not a prompt-level prohibition. A third position distinct from both "explicitly banned" (Goose) and "allowed with no stated limit at all" (Amp) — allowed, but enforced by infrastructure rather than by instruction or by silence. |
| **Recursion denied by default, per-agent-type grantable** — the most granular position in this table | OpenCode's `deriveSubagentSessionPermission()`: every sub-agent's own `task` tool (and `todowrite`) is denied unless its specific agent type's permission ruleset explicitly grants it — the `plan` agent, for instance, is allowed to spawn only the `general` subagent type and nothing else. Neither a blanket ban (Goose) nor silent allowance (Amp) nor infrastructure-capacity-bounded (Codex) — a per-type allowlist decided at agent-definition time. |
| **Recursion structurally *possible* but not exercised by any built-in — only reachable via a deliberately custom-authored agent definition** | OpenHands's new SDK — none of the four built-in `AgentDefinition` files (`bash-runner`/`code-explorer`/`web-researcher`/`general-purpose`) include the `task` or `delegate` tool in their own tool list, so out of the box, sub-agents can't recurse; a user or plugin author would have to deliberately build a custom agent definition that grants itself one of those tools. No code-level prohibition exists, unlike Goose's explicit ban — it's an emergent consequence of what ships by default, a fifth distinct position. |
| **Explicit code-level prohibition, enforced against even a wildcard tool grant** — stronger than a prompt-level ban | Gemini CLI — the local executor strips any tool of `kind === Kind.Agent` from a spawned sub-agent's own tool registry before it runs ("We do not allow agents to call other agents"), so recursion is blocked structurally even if a sub-agent definition tried to grant itself `*` tool access. A sixth position, and — unlike Goose's prompt-stated ban, which a sufficiently determined/confused model could in principle still attempt — one the model has no code path to violate. |
| **Confirmed supported and tested, with no depth limit found** | Roo Code — nested delegation (parent → child → grandchild) works and unwinds correctly, evidenced by dedicated test coverage for exactly a 3-level chain; no `maxSubtaskDepth`-style constant was found anywhere in the confirmed source. The only source in this table where recursion is both actively exercised *and* unlimited. |
| **Recursion is generalized into full compositional nesting, not a binary "can a sub-agent delegate" question at all** | Microsoft Agent Framework — `Workflow.as_agent()` lets an *entire orchestration* (Sequential chain, Handoff swarm, Magentic team) satisfy the same `SupportsAgentRun` protocol a single agent does, so it can become one participant nested inside another orchestration; a demonstrated sample (`magentic_workflow_as_agent.py`) confirms this is real, not theoretical. This reframes the whole §6 question — it's not "can one agent spawn one more agent," it's "can any composed structure be nested inside any other," a strictly more general capability than every other row in this table addresses. |
| **Not addressed** | v0, Emergent (each named agent has an implicit fixed toolkit per its specialty, but no stated recursion rule), Google Antigravity, SWE-agent (n/a in the usual sense — a `RetryAgentConfig` doesn't "recurse," it just runs more full attempts), Grok Build (leaked — `capability_mode: "all"` on `spawn_subagent` is ambiguous as to whether it includes `spawn_subagent` itself; no explicit ban and no explicit allowance found either way) |

**Takeaway**: this table now has seven genuinely distinct positions —
Goose's outright prompt-level ban, Gemini CLI's stronger code-level
ban, Amp's apparent silent allowance, Codex's infrastructure-
capacity-bounded allowance, OpenCode's per-agent-type allowlist decided
at definition time, OpenHands's "possible in principle, absent from
every built-in by omission," Roo Code's "confirmed working, no limit
found," and Microsoft Agent Framework's generalization of the whole
question into compositional nesting. No two sources converge on the
same answer to "can a sub-agent itself delegate," and unlike
concurrency (§5, where several unrelated codebases converged on similar
numeric caps or the same all-or-nothing extremes), recursion policy
looks like the least-converged design question in this entire survey.

## 7. Multi-party orchestration patterns (Microsoft Agent Framework)

Everything in §§1–6 assumes a two-party relationship: one orchestrator,
one sub-agent it delegates to (or, at most, OpenHands's `workflow` DSL
fanning out to many copies of the *same* kind of relationship).
Microsoft's Agent Framework — the same upstream project
[`codeact-hyperlight/`](../codeact-hyperlight) sources from, but a
completely separate installable package
(`agent-framework-orchestrations`) with no code cross-references to the
CodeAct material — implements something structurally different: five
named, `Builder`-configured topologies for composing **N** participants
with no fixed hierarchy assumed. Confirmed by reading the actual
`_sequential.py`/`_concurrent.py`/`_handoff.py`/`_group_chat.py`/
`_magentic.py` implementations, not just names.

| Pattern | Relationship shape | Conversation sharing | How a final result is determined |
|---|---|---|---|
| **Sequential** | Chain — each participant runs after the last | Shared, cumulative by default (a flag switches to "only the immediately-prior response") | Last participant's output, unless `output_from` names someone else |
| **Concurrent** | Fan-out/fan-in — all participants get the same input at once | **Isolated** — no participant sees another's conversation | Default aggregator pulls each participant's final message; a custom callback can combine differently |
| **Handoff** | Decentralized, model-driven routing — any participant can transfer control to any other it's been wired to | Shared single thread, broadcast to all after every turn (handoff plumbing stripped before broadcast) | Whatever the currently-in-control participant produces, live per-turn — no synthesized final event |
| **GroupChat** | Centrally managed — one orchestrator decides who speaks next | Shared, centrally owned history | Full conversation history returned as the output |
| **Magentic** | Manager-directed, plan-and-monitor loop | Shared, with a structured "task ledger" (facts + plan) the manager maintains separately from the raw conversation | Manager explicitly synthesizes a final answer from the complete history once its progress ledger reports the task done |

Mechanically, **Handoff routes via synthetic tools**: allowed handoffs
are injected into each agent's own toolset as `handoff_to_{target_id}`
functions, and a middleware intercepts calls to them to redirect the
turn — routing is implemented as an ordinary tool call the model makes,
not a special protocol primitive. **Magentic is the most elaborate**:
its manager runs a three-stage prompt sequence to build an initial
facts/plan "task ledger," then loops — produce a structured progress
ledger (task satisfied? loop detected? next speaker + instruction?),
route that participant, append and broadcast the response, repeat —
with stall detection triggering a full replan-and-reset (see §4) and an
optional human plan-sign-off gate before execution begins at all.

**Composability, not competition, with everything else in this
document**: every participant just needs to satisfy a `SupportsAgentRun`
protocol (`id`/`name`/`description`/`run()`), and `Workflow.as_agent()`
lets a whole *orchestration* satisfy that same protocol — so a CodeAct-
using agent can be one Sequential-chain participant, and an entire
Magentic team can itself be nested as one participant inside a larger
Handoff swarm (confirmed real via a demonstrated sample, not just
theoretically possible — see §6). The framework's own migration guides
position these as direct successors to prior-art multi-agent
frameworks: Handoff ↔ AutoGen's `Swarm`, Magentic ↔ AutoGen's
`MagenticOneGroupChat`, GroupChat/Sequential ↔ AutoGen's
`RoundRobinGroupChat`/`SelectorGroupChat` — this is a deliberate,
documented design lineage, not five patterns invented independently of
prior multi-agent-framework research.

None of the other 18 sources in this document implement anything
resembling GroupChat's centrally-arbitrated shared conversation or
Magentic's ledger-driven replanning — the closest analog anywhere else
is Composio SWE-Kit's fixed 3-role keyword-handoff pipeline (§2), which
is a single hardcoded sequence with no dynamic turn-selection, LLM-based
routing, or stall-recovery mechanism at all.

### 7a. Claude Code's "Team" system — a second N-party design, now confirmed rather than inferred

`leaked/claude-code/architecture-notes.md`'s Multi-agent "Team"
coordination section was originally built entirely from source-code
inference (file names, comments, constant names — never a captured
prompt). A later, much richer prompt-text capture
(`deferred-tools.md`, see that folder's README) has since confirmed
the core of it directly: real `TeamCreate`/`TeamDelete`/`SendMessage`
tool schemas exist, `TeamCreate`'s own description states "Teams have
a 1:1 correspondence with task lists (Team = TaskList)," and
`SendMessage`'s structured message types
(`shutdown_request`/`shutdown_response`/`plan_approval_request`/
`plan_approval_response`) match what had only been inferred before.
This is a genuinely different shape from anything in the §7 table
above — a **supervisor-worker structure layered as a tool-allowlist
policy over the same primitive as ordinary two-party delegation**
(`COORDINATOR_MODE_ALLOWED_TOOLS` vs. `ASYNC_AGENT_ALLOWED_TOOLS`
picking which policy applies), broadcast/direct/cross-session
messaging via `bridge:`/`uds:` prefixes, and a idle-state UX rule not
seen in any Microsoft Agent Framework pattern ("Teammates go idle
after every turn... going idle immediately after sending you a message
does NOT mean they are done").

The same richer capture also surfaces a **structurally distinct
second mechanism**, `Workflow` — a deterministic, JS-scripted
orchestration tool (`agent()`/`parallel()`/`pipeline()`/`phase()`
primitives, a concurrency cap of `min(16, cpu cores - 2)`, a
1000-agent lifetime cap) explicitly gated behind user opt-in ("the
user must request that scale, not have it inferred") because of its
cost. Its standout feature is **resumability**: `resumeFromRunId`
replays cached `agent()` results for an unchanged script prefix ("Same
script + same args → 100% cache hit"), which is specifically why
`Date.now()`/`Math.random()` are banned inside workflow scripts —
either would break the cache-hit guarantee. This is closer in spirit
to a deterministic fan-out/fan-in primitive (like §7's Concurrent
pattern) than to Team's persistent supervisor/worker structure, but
implemented as scripted orchestration rather than a `Builder`-configured
topology — a third distinct shape (Team, Workflow, and Microsoft Agent
Framework's five patterns) for solving overlapping but not identical
problems, none of which were designed with the others in mind.

## 8. Absences worth noting

- **Codex CLI, OpenHands, OpenCode, Roo Code, SWE-agent, Gemini CLI,
  and Microsoft Agent Framework are not really absences at all, on
  correction — most turned out to have real, and in several cases
  unusually sophisticated, sub-agent or multi-agent architectures**
  (see §§2–7). Called out here specifically because the gap or
  under-coverage happened first, seven separate times, for the same
  underlying reason: passes over only prompt-text or one narrow
  tool-JSON/source-tree extraction concluded there was little or no
  delegation mechanism, when the real machinery shipped as separate
  source that was never fetched in. See the methodology note at the
  end of §2 for what this implies about every other row below.
- **Leaked Windsurf — despite having one of the richest tool surfaces
  in this entire collection (see `agent-tool-surfaces.md` §§1–7, its
  30-tool browser/deployment/memory suite) — has no sub-agent/delegate
  tool in its extraction.** Tool-surface breadth and sub-agent capability
  are not the same axis: Windsurf invested in browser automation,
  deployment integration, and persistent memory instead of task
  delegation, while Claude Code, Gemini CLI, and (per the corrections
  above) Codex CLI, OpenCode, OpenHands, and Roo Code — all comparatively
  narrow, unglamorous tool surfaces by `agent-tool-surfaces.md`'s
  accounting — turn out to be exactly the sources that invested most
  heavily in delegation architecture. Worth taking as a real caution:
  Windsurf's sub-agent section in this collection is *also* built from
  a prompt/tool-JSON extraction of closed-source, leaked material with
  no live upstream repo to double-check against — unlike every
  open-source correction made in this document, there's no way to go
  verify whether that absence is real or another instance of the same
  blind spot.
- **Leaked Cursor no longer belongs in this bucket, on correction.**
  Five of Cursor's six captured prompt files (everything sourced from
  x1xhlol's aggregator) still show zero delegation mechanism — the
  original finding above held for all of them. But a sixth,
  independently-sourced capture (`Agent Prompt (asgeirtj capture).md`,
  from a different aggregator entirely — see `leaked/cursor/README.md`)
  has a real `Task` tool with seven named `subagent_type`s
  (`generalPurpose`, `explore`, `shell`, `browser-use`, `cursor-guide`,
  `best-of-n-runner`, `codex-rescue`), one of which (`best-of-n-runner`,
  "Run a task in an isolated git worktree") also supplies this
  collection's first confirmed Cursor worktree-isolation finding (see
  `agent-git-vcs.md` §4). No schema or protocol detail is captured
  beyond the one-line role descriptions, so this doesn't get promoted to
  a fully profiled §2-style entry — but "Cursor has no delegation
  mechanism at all" is no longer an accurate blanket statement about
  Cursor's full captured corpus, only about five-sixths of it. The same
  caution above still applies in the other direction, too: this is a
  single leaked capture with no live source to verify it against, so
  treat the *existence* of the mechanism as more confirmed than its
  *absence* ever was — a leak naming a tool is harder to fabricate by
  omission than a leak failing to mention one.
- **A cross-source echo worth flagging rather than resolving**: leaked
  Cursor's `codex-rescue` `subagent_type` (row above) and Grok Build's
  `codex:codex-rescue` `spawn_subagent` type (leaked, xAI) name the
  identical rescue/second-opinion role -- "Use when stuck, wants a
  second implementation pass, or deeper root-cause investigation" in
  Grok's case -- across two unrelated vendors. Both leaks were also
  mirrored from the same independent aggregator,
  `asgeirtj/system_prompts_leaks`, rather than the x1xhlol repo most of
  this collection's other `leaked/` sources come from. Three
  explanations are all consistent with what's captured and none can be
  ruled out from the prompt text alone: a genuine shared third-party
  integration (an actual `codex-rescue` service both products call
  out to), independently-but-identically-named internal concepts for
  the same "run a second, unstuck attempt" idea, or an artifact of how
  this particular aggregator captures/labels its leaks. Flagged as an
  open question, not a resolved finding.
- **The remaining benchmark-lineage agents (mini-swe-agent,
  Live-SWE-agent, Augment SWE-bench Agent) have no sub-agent concept at
  all** — consistent with their single-tool-loop, one-shot-benchmark-run
  design; Live-SWE-agent's self-authored-tools capability (see
  `agent-tool-surfaces.md` §3) is the closest analog, and it's a script
  the same agent runs itself, not a second agent. SWE-agent, the fourth
  member of this lineage, has been moved out of this bullet on
  correction — see §2 and §4 for its reviewer/retry-loop architecture.

---

## Design takeaways

- **"Sub-agent" spans at least six different architectures in this
  collection, not one pattern with minor variations**: a stateless
  tool-call-and-report delegate (Claude Code, Crush, v0, Amp), an
  addressable/resumable child process (Codex, OpenCode, OpenHands, Roo
  Code — see below), a fixed multi-role team sharing one conversation
  via keyword handoffs (Composio SWE-Kit), an asynchronous background
  distillation process the orchestrator only consumes output from
  (Google Antigravity's Knowledge Subagent), a generate-then-judge
  ensemble over whole independent attempts rather than partial
  delegation (SWE-agent), and five named N-party orchestration
  topologies with no fixed two-party hierarchy at all (Microsoft Agent
  Framework, §7). Treating all "delegation" mentions across sources as
  the same mechanism would blur real, load-bearing architectural
  differences.
- **Amp's three-sub-agent menu (Task/Oracle/Codebase-Search-Agent) is
  still the most sophisticated *single-orchestrator* delegation design
  surveyed here**, specifically because it's the only one that varies
  the *model* per sub-agent (Oracle on o3) rather than just the tool
  scope and prompt — every other two-party source's sub-agent runs on
  the same underlying model as the orchestrator (or doesn't specify).
  Microsoft Agent Framework's orchestration layer is more sophisticated
  in aggregate (five topologies vs. one menu of three), but doesn't
  vary model choice per participant in what was confirmed by reading.
- **A previously-invisible axis, distinct from delegation entirely: the
  orchestrator's own top-level identity can itself be mode-selected.**
  `leaked/amp/amp-code.md` (a binary-string capture richer than the two
  YAML files this collection's Amp entry was built from) shows the Amp
  CLI assembling its system prompt from an identity string plus shared
  sections, chosen from at least eleven named modes at launch (default,
  autonomous-agent, pair-programming, lead-orchestrator, three tiers of
  "powerful AI coding agent," two extreme-terseness speed modes, a
  generic subagent prompt, and a non-coding platform-control-plane
  persona) — several modes explicitly declared to share verbatim
  subsections with others. This is orthogonal to the Task/Oracle/
  Codebase-Search-Agent menu above: that's *within-conversation*
  delegation to a different persona; mode selection is *which persona
  the top-level conversation itself runs as*, chosen once per session/
  invocation rather than per tool call. Claude Code's "session-mode-
  dependent prompt axis" (interactive vs. autonomous/background,
  documented in `leaked/claude-code/README.md`'s Sub-agents section) is
  the nearest analog elsewhere in this collection, but Amp's is far more
  granular — eleven identities vs. one extra block — and, unusually,
  confirmed by direct textual cross-reference between capture files
  rather than inferred from a single session's behavior.
- **Trust-the-report vs. verify-the-report vs. quantify-the-trust is a
  real, unresolved three-way split**, not a convergence: Claude Code
  and Composio's playbook role tell the orchestrator to trust sub-agent
  output outright; Emergent and Google Antigravity build explicit
  re-verification into the workflow; SWE-agent sidesteps the question
  entirely by having a separate model compute a numeric score instead
  of asking the orchestrator to decide how much to trust free text (§4).
  Given that sub-agent reports are, by construction, unverified
  self-summaries the orchestrator usually can't audit step-by-step,
  Emergent's "check the git-diff, don't just trust the summary" and
  SWE-agent's "let a dedicated judge model score it" both read as more
  defensible than blanket trust — though both cost something blanket
  trust doesn't (verification effort, or a second model call).
- **Recursion policy is the least-converged design question in the
  whole survey, now spanning seven distinct positions** (§6) — from
  Goose's prompt-level ban and Gemini CLI's stronger code-level ban, to
  Amp's apparent silent allowance, Codex's infrastructure-bounded
  allowance, OpenCode's per-type allowlist, OpenHands's absent-by-
  omission-from-built-ins, Roo Code's confirmed-working-no-limit, up to
  Microsoft Agent Framework generalizing the question away entirely via
  compositional nesting. No two sources land in the same place.
- **Tool-surface richness and sub-agent investment are independent
  axes** (§8) — Windsurf, one of the richest tool surfaces in this
  collection, has no delegation mechanism at all, while several
  comparatively narrower-tool-surface sources (Claude Code, Gemini CLI,
  Amp, Codex, OpenCode, OpenHands, Roo Code) invested specifically in
  sub-agent architecture. Where a given product spends its complexity
  budget looks like a real product decision, not something that falls
  out of overall sophistication. **Cursor no longer belongs on the
  "richest surface, no delegation" side of this claim on correction**:
  its five x1xhlol-sourced captures still fit that pattern, but the
  independently-sourced `Agent Prompt (asgeirtj capture).md` has a real
  (if thinly-described) `Task`/sub-agent mechanism — see the Absences
  section above.
- **The naming collision worth remembering, now with a sharper edge**:
  `new_task` means three different things across `cline/`, `roocode/`,
  and (as `Task`) `leaked/claude-code/` — pure user-facing context
  handoff, real hierarchical delegation, and synchronous in-process
  delegation, respectively, from a tool name that *sounds* like the same
  capability in all three. When comparing scaffolds by tool name alone,
  always check the actual protocol (§2) before assuming equivalence —
  identical names across a literal fork lineage (Cline → Roo Code) were
  not enough to guarantee identical behavior here.
- **Codex CLI's `spawn_agent` family, OpenCode's `task` tool, OpenHands's
  `delegate`/`task`/`workflow` trio, Roo Code's `new_task`/
  Orchestrator pairing, and Grok Build's `spawn_subagent`/
  `get_command_or_subagent_output`/`resume_from` trio are five
  independent arrivals at "addressable, not stateless" delegation** —
  found by going back and checking live source (or, for Grok Build, a
  closely-read leak) after a prompt-text-only pass undersold each one.
  Codex combines a persistent addressable child with mid-flight
  steering and infrastructure-enforced safety limits; OpenCode
  independently arrives at addressable statefulness via a generic
  background-job primitive plus a promote-to-background escape hatch;
  OpenHands layers true multi-threaded parallel delegation *and* a
  constrained map-reduce/pipeline orchestration DSL (`workflow`) on top
  of an addressable `task`/`delegate` primitive; Roo Code reaches the
  same addressable-with-deferred-result shape via the plainest
  mechanism of the five — a single LIFO session stack — trading
  concurrency away entirely in exchange for simplicity; Grok Build adds
  a fifth variant, closest to Codex's shape but with `resume_from`
  reopening a *completed* sub-agent's conversation rather than steering
  one still in flight. Five unconnected engineering teams converging on
  "spawn returns something you can address later," even while
  disagreeing completely on whether that something runs concurrently,
  is stronger evidence about the right shape for this problem than any
  one source's choice would be alone.
- **GitHub Copilot CLI's "sidekick" agents (§5) add a seventh
  architecture to the opening bullet's count, not a variant of one
  already listed**: every other pattern in this document — even Google
  Antigravity's asynchronous Knowledge Subagent, the closest prior
  analog — is triggered by *something the orchestrator or user did*.
  Sidekicks fire on every user turn regardless, gated purely by their
  own `launchConditions`/`featureFlag`, decide independently whether
  they have anything worth surfacing, and inject at most one
  budget-capped entry into a shared inbox the orchestrator reads
  passively — the orchestrator never decides to spawn one, never learns
  it ran unless it produced output, and has no addressing handle to it
  at all. Combined with the same source's SQL-mediated Fleet Mode
  (coordination via shared database rows rather than a workflow DSL or
  Builder-configured topology), this is a second genuinely novel
  concurrency mechanism from a single source in one research pass — a
  reminder that this document's typology, even after seven prior
  corrections, is still being extended by newly-checked sources rather
  than settling into a fixed set of categories.
- **Microsoft Agent Framework's five orchestration patterns are a
  different kind of finding from everything else in this document**:
  every other source here answers "how does one agent delegate to
  another," including the addressable designs above. Sequential,
  Concurrent, Handoff, GroupChat, and Magentic instead answer "how do N
  agents with no fixed hierarchy relate to each other" — a genuinely
  different problem, not a more sophisticated answer to the same one.
  Magentic's ledger-driven plan/monitor/replan loop in particular has no
  analog anywhere else in this survey, including in every "planning
  tool" documented in `coding-agent-approaches.md` §6 (all of which
  manage one agent's own todo list, not a team's shared progress).
- **The seven corrections in this document (Codex, OpenCode, OpenHands,
  Roo Code, SWE-agent, Gemini CLI, Microsoft Agent Framework) are,
  together, the most important methodological finding here**: an
  absence in a prompt-text-only or narrow tool-JSON/source-tree
  extraction is evidence of nothing beyond "not mentioned in that
  text." Every one of the seven looked capability-poor or
  capability-free on this exact axis right up until someone checked the
  actual source, at which point most turned out to be among the richest
  examples in the survey. Every "no sub-agent mechanism" claim
  elsewhere in this document — every source not yet checked against
  live upstream code — rests on the same kind of extraction and should
  be read with the same discount: absence of evidence, not evidence of
  absence.
