# Sub-agents: when a scaffold spawns another agent

A second drill-down alongside [`agent-tool-surfaces.md`](./agent-tool-surfaces.md),
this time on a single capability that turned out to have far more
internal variety than "delegate a task to a helper agent" suggests: what
protocol the orchestrator and sub-agent speak, what (if any) system
prompt the sub-agent runs under, how its result gets back into the
orchestrator's context, and what happens if two sub-agents run at once.

Grounded directly in each source's own "## Sub-agents" README section
(all re-read from the files in this repo at time of writing). 14 sources
have one — a mix of the "coding agent" core collection and several
`leaked/` sources whose tool JSON turned out to carry unusually detailed
sub-agent specifications once actually read closely.

## Sources covered

Claude Code (leaked), the general Anthropic assistant prompts (leaked),
OpenCode, Cline, Roo Code, Gemini CLI, GitHub Copilot Chat, Crush, Goose,
Composio SWE-Kit, Amp (leaked), Emergent (leaked), Google Antigravity
(leaked), and v0 (leaked). Sources with **no** sub-agent mechanism
captured in what's stored here — Codex CLI, Aider, SWE-agent,
mini-swe-agent, Live-SWE-agent, Augment SWE-bench Agent, Bolt.new, Pi,
CodeAct+Hyperlight, OpenHands, and (notably, given how rich their tool
surfaces are — see `agent-tool-surfaces.md` §§1–7) leaked Cursor and
leaked Windsurf — are covered only in the "Absences" section below, not
individually profiled.

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

## 2. Calling convention & protocol shape

The biggest structural fork: is a "sub-agent" a **tool call** that
returns a result, or a **role in a shared conversation** that hands
control back and forth via convention?

| Shape | Sources |
|---|---|
| **Tool call → stateless, one-shot, single final report** — the orchestrator cannot send follow-up messages, only sees the sub-agent's last message | Claude Code (explicit: "Each agent invocation is stateless... you can't communicate with it until it finishes"), Amp's `Task` (near-identical wording), OpenCode, Crush, v0, Gemini CLI (implied by the "consolidated into a single summary" framing) |
| **Tool call with a typed registry** — caller picks from named agent *types*, each with a different tool scope | Claude Code (`general-purpose`/`statusline-setup`/`output-style-setup`, via a `subagent_type` parameter), Gemini CLI (`agent_name` parameter, `codebase_investigator` named explicitly), Amp (three tools with three different roles — `task`/`oracle`/`codebase_search_agent` — rather than one tool with a type parameter) |
| **Tool call with essentially one free-text parameter (`task`)**, fleet of separately-named single-purpose tools instead of a type enum | Emergent (`auto_frontend_testing_agent`, `deep_testing_backend_v2`, `integration_playbook_expert_v2`, `vision_expert_agent`, `support_agent`, `deployment_agent` — six separate tools, each essentially `(task: string) -> report`) |
| **Fixed multi-role team, control passed via literal keyword strings in a shared conversation** — not a tool call/return at all | Composio SWE-Kit (`"ANALYZE CODE"`, `"ANALYSIS COMPLETE"`, `"EDIT FILE"`, `"EDITING COMPLETED"`) — the one source in this collection where delegation isn't tool-mediated |
| **File-mediated handoff** — orchestrator and sub-agent communicate through a shared document, not tool-call parameters/results | Emergent's backend-testing flow specifically: `test_result.md` documents its own "Testing Protocol and communication protocol with testing sub-agent," and the orchestrator is told to read/update it before and after each test-agent invocation |
| **Confusable-but-different: session/context handoff to the *user*, not a spawned agent** | Cline's `new_task` — generates a structured summary and hands it to the user as a preview for starting a *fresh conversation*; no orchestrator-sub-agent relationship, no result passed back, the "new task" replaces the current one rather than running alongside it |
| **Async background process the orchestrator never directly invokes** — runs over history, produces artifacts the orchestrator later reads | Google Antigravity's Knowledge Subagent (distills past conversations into "Knowledge Items" the orchestrator reads later, rather than being called synchronously) |

**Takeaway**: Cline's `new_task` is worth flagging as a trap for anyone
skimming tool names across sources — it's lexically adjacent to Claude
Code's `Task` and Roo Code's mode system, but semantically unrelated:
it's a context-compaction/session-restart convenience for the *user*,
not a delegation mechanism. Composio SWE-Kit's keyword-handoff pipeline
is the real structural outlier — every other source treats "sub-agent"
as a callable tool with a return value; Composio treats it as a fixed
sequence of roles sharing one conversation.

## 3. Does the sub-agent get its own system prompt?

The question the user's request specifically asked about, and the one
with the most uneven documentation across sources — most tool JSON
extractions only capture the *orchestrator-facing tool description* that
triggers delegation, not what prompt (if any) the spawned agent itself
runs under.

| Sub-agent system prompt fully captured? | Sources |
|---|---|
| **Yes — complete, standalone prompt file(s)** | Copilot Chat (`executionSubagentPrompt.tsx`: "You are an AI coding research assistant that runs a series of terminal commands..."; `searchSubagentPrompt.tsx`: "...that uses search tools to gather information..."), Crush (`task.md.tpl`: "You are an agent for Crush..."; `agentic_fetch_prompt.md.tpl`: "You are a web content analysis agent for Crush..."), Goose (`subagent_system.md`: "You are a specialized subagent within the goose AI framework... You were spawned by the main goose agent") |
| **No — only the orchestrator-side tool/call description is captured, not the sub-agent's own prompt** | Claude Code, Amp (all three of `Task`/`oracle`/`codebase_search_agent`), Gemini CLI, OpenCode, v0, Emergent (six named agents, no prompt text for any of them), Google Antigravity's `browser_subagent` |
| **N/A — no tool-call boundary in the first place, so no separate "sub-agent prompt" concept applies** | Composio SWE-Kit (each of the three roles has its own persona prompt, but they're peers in one state machine, not an orchestrator-plus-spawned-sub-agent relationship) |

Of the three sources with a captured sub-agent prompt, each makes a
different design choice about how much the sub-agent should know it
*is* one:

- **Goose is explicit about identity and provenance**: "You were spawned
  by the main goose agent to handle a specific task efficiently" — the
  sub-agent is told directly who spawned it and why.
- **Copilot Chat and Crush give the sub-agent a role, not a
  spawned-by-relationship**: "an AI coding research assistant," "an
  agent for Crush," "a web content analysis agent for Crush" — no
  mention that a parent agent exists or that this is a delegated task.

## 4. Turn/output bounding and the result-handling contract

How does the sub-agent know when to stop, and in what shape does its
answer arrive back at the orchestrator?

| Mechanism | Sources |
|---|---|
| **Hard turn cap with a forced-cutoff nudge message** injected on the last allowed turn | Copilot Chat — both sub-agents get "OK, your allotted iterations are finished..." on `isLastTurn`, pushing them to emit the required `<final_answer>` block rather than trailing off |
| **Turn cap as a template variable, no forced nudge described** | Goose (`{{max_turns}}` interpolated into the prompt; "Stop using tools once you have sufficient information" is a soft instruction, not an injected cutoff message) |
| **No stated turn limit in what's captured** | Claude Code, Amp, Gemini CLI, OpenCode, Crush, v0, Emergent, Google Antigravity |
| **Strictly constrained output grammar** — the sub-agent's final message must match an exact format | Copilot Chat (`ExecutionSubagent`: command+summary pairs inside `<final_answer>`; `SearchSubagent`: bare `path:line-start-line-end` list, "ONLY" that tag) |
| **Structured-but-freeform** — a required section (e.g. Sources) but otherwise prose | Crush's `agentic_fetch` (mandatory `## Sources` section listing every URL used, answer text otherwise free-form) |
| **Free-text summary, no schema** | Claude Code ("a concise summary of the result" — no format specified), Amp's `Task`/`oracle` (same wording, inherited from the same lineage), Emergent (free-text "finish action" summary) |
| **Explicit distrust of the self-report — orchestrator must independently re-verify** | Emergent ("Please check the response from sub agent including git-diff carefully... Subagent sometimes is dull and lazy... or over enthusiastic"), Google Antigravity's `browser_subagent` ("you should read the DOM or capture a screenshot to see what it did" rather than trusting the report alone) |
| **Explicit trust instruction — take the report at face value** | Claude Code ("The agent's outputs should generally be trusted"), Composio SWE-Kit's integration playbook ("Always implement... EXACTLY as specified in the playbook returned") |

**Takeaway**: this is the sharpest split in the whole comparison — some
sources (Claude Code, Composio's playbook role) instruct the
orchestrator to trust a sub-agent's self-report outright, while others
(Emergent, Google Antigravity) build in an explicit distrust-and-verify
step. Emergent's is the most pointed: it names both failure modes
("dull and lazy" under-delivery vs. "over enthusiastic" over-delivery)
and prescribes a concrete check (diff review) rather than leaving
verification to the orchestrator's judgment.

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
| **Not addressed** | OpenCode, Cline (n/a — not a real sub-agent), Roo Code (n/a — no sub-agent at all), Copilot Chat, Crush, Goose, Composio SWE-Kit (structurally serial by design — one role active at a time), Emergent, Google Antigravity, v0 |

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
| **Not addressed** | OpenCode, Gemini CLI, v0, Emergent (each named agent has an implicit fixed toolkit per its specialty, but no stated recursion rule), Google Antigravity |

**Takeaway**: Amp's `Task` tool having `codebase_search_agent` in its
own tool list, with no recursion caveat anywhere in the extracted text,
sits in real tension with Goose's explicit "cannot spawn additional
subagents" rule — two sources in this collection land on opposite sides
of the same design question (can a sub-agent itself delegate?) without
either being clearly "correct."

## 7. Absences worth noting

- **Codex CLI has no sub-agent mechanism captured anywhere in this
  collection's Codex files** (`codex/`, or the `github-pr-bots/`
  Codex-based review bot) — its "Plan tool" (see `coding-agent-approaches.md`
  §6) manages the orchestrator's own todo list, not a delegated agent.
- **Leaked Cursor and leaked Windsurf — despite having two of the
  richest tool surfaces in this entire collection (see
  `agent-tool-surfaces.md` §§1–7, especially Windsurf's 30-tool
  browser/deployment/memory suite) — have no sub-agent/delegate tool in
  either extraction.** Tool-surface breadth and sub-agent capability are
  not the same axis: Windsurf invested in browser automation, deployment
  integration, and persistent memory instead of task delegation, while
  Claude Code and Gemini CLI (comparatively narrower tool surfaces) both
  invested specifically in delegation.
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
