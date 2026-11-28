# Agent swarms: many agents on one task

- **Type**: a cross-source survey of how systems put many agents on one task:
  agent SDKs, harnesses, research systems and papers, read for what they mean for
  Keel, Forge and Lens. No system prompts are stored here.
- **Prompted by**: Jonathan, 2026-11-28: "research into agent swarms -
  frameworks/techniques used, how to communicate, organise, focus, iterate,
  orchestrate. inspired by but not limited by use cases like breaking a maths
  problem", and "make use of and update taxonomies".
- **Read**: 2026-11-28. Every claim carries a tag. **[source]**: read in the code
  (SHAs in [`sources.md`](./sources.md), "Agent swarms (read 2026-11-28)").
  **[paper]**: read in a paper's full text. **[abstract]**: read in its abstract
  only. **[docs]**: an official page or engineering post. **[secondary]**: a third
  party's account. **[inference]**: ours.
- **Proposals** for Keel, Forge and Lens, **none adopted, for discussion**, are in
  [`agent-design/proposals-swarms-2026-11.md`](./agent-design/proposals-swarms-2026-11.md).

**Words.** This doc uses the `prompts` glossary's heading words (agent, harness,
run, sub-agent, orchestrator, second model, pipeline, handoff, run budget,
completion gate, retry, resume, authority, transcript, eval). The coordination
area has no stage yet, so six words used here have no entry: **swarm**,
**topology**, **fan-out**, **board**, **vote** and **debate**. Each is defined
where it is first used and has a `term-request` issue in `jburnhams/taxonomies`
(listed in `changelog.md`'s entry for today), with a `clarify` request on
**handoff**, whose entry covers a run passing work on but not one agent passing
control to another inside a run (§4b).

**What this adds.** The repo already covers the two-party case in depth:
[`agent-subagent-architectures.md`](./agent-subagent-architectures.md) (how one
agent delegates to another in 21 harnesses, Microsoft Agent Framework's five
topologies in §7, Claude Code's teams in §7a, orchestration moving into code in
§7b, "fewer sub-agents, or a thousand" in §7e),
[`agent-design/review.md`](./agent-design/review.md) §6a (the three reasons to
fan out) and [`agent-design/orchestration.md`](./agent-design/orchestration.md)
(task splitting across runs). This doc does not repeat them. It adds what happens
when the number of agents goes from two to dozens or hundreds, the evidence on
whether that helps, and the techniques under each of the five verbs in the ask.

---

## 1. What a swarm is, and the five decisions

A **swarm** here is a set of agents working on one task at the same time, whose
results are combined into one outcome. It is broader than a sub-agent call (one
spawner, one report) and narrower than a pipeline (runs in sequence, joined by
edges). The word is used loosely in the field: OpenAI's Swarm was a two-agent
handoff library, Kimi's Agent Swarm is an orchestrator with up to 300 frozen
sub-agents, and Agensh's swarm has no orchestrator at all.

A survey of RL for multi-agent systems (Zhang, arXiv 2605.02801, 2026-05-04)
**[paper]** gives the frame this doc uses. Any orchestration makes five decisions,
and a system's design is which of them a model makes and which are code:

| # | Decision | Examples of a model making it | Examples of code making it |
|---|---|---|---|
| O1 | **When to spawn** | Kimi's orchestrator, Claude Code's `Task` | Forge review's fixed specialist list; ADK `ParallelAgent` |
| O2 | **Whom to delegate to** | Magentic's progress ledger names the next speaker; OpenAI handoffs | CrewAI sequential process; Cursor workers taking the next task |
| O3 | **How to communicate** | Claude Code teammates choosing to `SendMessage` | ArcticSwarm's board as the only channel; Codex `disable_direct_message` |
| O4 | **How to aggregate** | Anthropic's lead agent synthesising; MoA's aggregator layer | Majority vote; ArcticSwarm's verdict counting; Forge's same-location dedup |
| O5 | **When to stop** | Magentic's "task satisfied?" field; a judge agent per cycle (Cursor) | `max_iterations` (ADK `LoopAgent`); ArcticSwarm's deadline; run budgets |

The survey found no published method that trains the stop decision (O5) as of May
2026. It is also the decision most often wrong in practice: "unaware of
termination conditions" and "premature termination" together are 18.6% of the
failures in MAST (§8d).

**Topology** here means the shape of who talks to whom. Five recur:

| Topology | Shape | Examples |
|---|---|---|
| **Independent** | N agents, same task, no messages, a fixed rule combines | self-consistency and vote; best-of-N; AutoSwarm's parallel members; Forge's sampled reviewers |
| **Centralized** | one orchestrator spawns, briefs and integrates | Anthropic's research system; Kimi Agent Swarm; SwarmBench; Claude Code `Task` |
| **Hierarchical** | orchestrators under an orchestrator | Cursor's planners and sub-planners; Cognition's manager Devin; MS Agent Framework's nested workflows |
| **Decentralized** | peers message each other or pass control | OpenAI and LangGraph handoffs; Claude Code teammates; Agensh |
| **Board** | agents read and write one shared record; nobody routes | blackboard systems; ArcticSwarm's bulletin board; Codex message boards; LeanMarathon's blueprint file |

---

## 2. The systems read

| System | Kind | Topology | Channel | Aggregation | Evidence |
|---|---|---|---|---|---|
| OpenAI Swarm → Agents SDK handoffs | SDK | decentralized | full conversation, filterable | the agent holding control answers | [source] `6afdd47`, [docs] |
| LangGraph swarm / supervisor | SDK | decentralized / centralized | graph state with `active_agent` | last active agent / supervisor | [source] `8956b13`, [docs] |
| Google ADK Sequential/Parallel/Loop agents | SDK | code-defined | isolated branch per parallel child | code | [source] `03725e8` |
| CrewAI crews | SDK | sequential or hierarchical (manager LLM) | delegate and ask-question tools | manager | [source] `77237ae` |
| Microsoft Agent Framework (5 patterns) | SDK | all five | shared thread, isolated, ledger | per pattern | [source], `agent-subagent-architectures.md` §7 |
| Claude Code `Task`, teams, Workflow | harness | centralized; decentralized; code | report; mailbox and task list; script | lead; script | [docs], leaked prompts, §7a-§7c there |
| Codex multi-agent v2 | harness | centralized, nested | direct messages or a board | parent | [source], §7b there |
| Kimi K2.5 / K2.6 Agent Swarm | trained model + product | centralized, up to 300 | brief in, task-relevant output back | orchestrator | [paper] 2602.02276, [docs] |
| Anthropic research system | product | centralized | brief in, file refs back | lead + citation agent | [docs] 2025-06-13 |
| Anthropic C compiler | experiment | flat peers, 16 | git and lock files | git merge | [docs] 2026-02-05 |
| Cursor long-running coding | experiment | hierarchical, hundreds | task records with optimistic concurrency; git | judge per cycle | [docs] 2026-01-14 |
| Cognition / Devin | product | single writer, manager-child | internal MCP | manager | [docs] 2025-06-12, 2026-04-22 |
| Google Antigravity `/swarm` and Dynamic Workflows | harness | coordinator, workers, verifiers, monitor; or a script | shared append-only board; or the script | coordinator; or code | [docs] 2026-11-10 |
| AI co-scientist | research system | supervisor + 6 roles | worker queue | tournament with Elo | [docs] 2025-02-19 |
| AlphaEvolve | research system | population | program database | evaluator scores, evolution | [docs] 2025-05-14 |
| LeanMarathon, LEAP, ToMap | maths papers | roles over a proof DAG | a Lean blueprint file | Lean compiler | [abstract] |
| ArcticSwarm | paper | orchestrator + board | one bulletin board | gated verdicts, no vote | [paper] 2609.01870 |
| AutoSwarm | paper | planned team with supervisors | shared execution state, artifact refs | supervisors | [paper] 2610.33048 |
| SwarmBench | benchmark | centralized | local contexts, some shared state | orchestrator | [paper] 2608.30661 |
| Blackboard for data discovery | paper | board, agents volunteer | blackboard | central agent | [abstract] 2510.01285 |
| Agensh | paper | no orchestrator, 128-1,024 workers | git, message bus, typed context board | merge | [abstract], §7e there |
| A2A 1.0 | protocol | agent to agent across vendors | Task, Message, Artifact | n/a | [docs] |

---

## 3. Does it help? The evidence, and when

The strongest finding of this pass is that **a swarm is not a better default**.
It helps on a narrow, recognisable class of task and hurts outside it, and most
reported gains shrink when compared at equal spend.

**Controlled comparisons.**

- **Towards a Science of Scaling Agent Systems** (Google and MIT, arXiv 2512.08296,
  v3 2026-04-08) **[paper]**, 260 configurations over six benchmarks and three
  model families, a single agent against four topologies with tools, prompts and
  compute held equal:
  - Centralized coordination gained **+80.8%** on decomposable financial
    reasoning; decentralized gained +9.2% on web navigation.
  - **Every topology lost on sequential planning**, by 39% to 70% (PlanCraft).
    SWE-bench Verified lost 2.1% to 14.9%. The mean change across all tasks was
    -0.3%, with a confidence interval from -58.7% to +77.2%.
  - **A capability ceiling**: where the single agent already scores above about
    45%, adding agents gave negative returns.
  - **Tool-heavy tasks pay a coordination cost** (β = -0.096, p = 0.002).
  - **Errors compound by topology**: independent agents amplified errors 17.2×,
    centralized 4.4×, because the orchestrator acts as a check before results
    spread.
  - A 20-term regression picks the best topology for 87% of held-out
    configurations, so the choice is predictable from task features.
- **When Sub-Agents Work in Parallel** (Li et al., arXiv 2610.10263, 2026-10-07)
  **[paper]** turned native concurrency on and off in Codex (GPT-5.4), Claude
  Code (Opus 5) and Kimi Code (K3): 354 tasks, 2,124 runs, about $20.8K.
  - Claude Code on SWE-bench Verified: **83.0% sequential, 59.0% concurrent**.
    On LoopsBench it went the other way, 7.1% to 21.4%.
  - Across all: -11.9 to +2.3 points, at 1.41× to 3.31× the tokens. Claude Code's
    and Kimi's declines were significant; Codex's gain was not.
  - Sub-agents shared one workspace, which is where most failures came from. A
    taxonomy of 28 failure patterns (804 instances, κ = 0.77).
  - Concurrency helped in three cases: **complementary work, alternative
    attempts and independent validation**.
- **Beyond Symmetric Agents** (arXiv 2609.35875, under review) **[abstract]**: 23
  models, 5,500+ runs, every debate paired with a vote at the same generation
  budget. Debate beat one agent by 3-7 points but tied or lost to
  self-consistency, at 1.6× the wall clock and 3.4× the tokens. "Nearly all of
  debate's benefit comes from the first exchange." Personas lowered accuracy, and
  mixed-model teams lost to a vote over their own members.
- **MAST** (Cemri et al., arXiv 2503.13657, NeurIPS 2025) **[paper]**: 1,642
  traces from seven open-source multi-agent systems failed 41% to 86.7% of the
  time; gains over best-of-N "often remain minimal".

**Where it clearly helps.**

- **Breadth search with independent parts.** Anthropic's research system
  (Opus lead, Sonnet sub-agents) beat a single Opus by 90.2% on its internal
  research eval **[docs]**; token use alone explained 80% of BrowseComp variance,
  so much of the gain is more spend in more fresh contexts. Kimi's swarm raised
  WideSearch F1 from 72.8% to 79.0% and cut latency up to 4.5× **[paper]**.
  ArcticSwarm reached 82.6% on BrowseComp-Plus against 48.4% for one agent and
  62.5% for a vote over 20 single runs **[paper]**.
- **Very large builds with a near-perfect oracle.** The C compiler (16 agents,
  two weeks, under $20,000, builds Linux 6.9) and Cursor's browser (about a week,
  over a million lines) both depended on a test suite or reference implementation
  that could judge any piece alone **[docs]**.
- **Search over candidates with an automatic scorer**: AlphaEvolve's population
  of programs, the co-scientist's tournament, Lean-checked proof attempts (§9).

**Where it hurts.** One line of judgment through the task (sequential
planning, a support conversation), many tools, a strong single agent, and above
all **several agents writing the same files**. Cognition's 2026 follow-up states
the working rule: "multiple agents contribute intelligence to a task while writes
stay single-threaded" **[docs]**; unstructured swarms are "mostly a
distraction".

**[inference]** The evidence lines up with `review.md` §6a's three reasons to
fan out (context coverage, role specialisation, sampling variance) plus a
fourth, **alternative attempts**, and with one precondition the field keeps
relearning: a way to judge a part's result without judging the whole.

---

## 4. Communicate

### 4a. What travels: full history, a brief, or a reference

| What the receiver gets | Who does it | Cost | Risk |
|---|---|---|---|
| **The whole conversation** | OpenAI Agents SDK handoffs by default; LangGraph swarm; MS Handoff and GroupChat | every agent re-reads everything | context bloat; an injection read by one reaches all |
| **A summary of the history** | Agents SDK `nest_handoff_history` (beta, off by default) wraps earlier turns in a `<CONVERSATION HISTORY>` block **[source]** | one summary | the summariser decides what matters |
| **A brief** | Anthropic research ("an objective, an output format, guidance on the tools and sources to use, and clear task boundaries"); Claude Code `Task`; Kimi; Forge | the spawner writes it | the brief is the sub-agent's whole world |
| **A reference** | Anthropic research (large outputs to the filesystem, "lightweight references" back); AutoSwarm artifact refs; A2A `Artifact`; Keel artifacts | almost nothing | the reader must fetch, and may not |

Cognition's 2025 rule, "share full agent traces, not just individual messages",
argues for the top row; the 2026 evidence argues against it for anything but a
single writer. The Agents SDK's own docs draw the line that matters for a hosted
system: `input_filter` is where shared content is chosen and redacted, and
"Nested handoff history is not a redaction mechanism" **[source]**.

### 4b. Handoff: passing control inside a run

OpenAI's Swarm (now "replaced by the OpenAI Agents SDK") and its successor expose
each possible handoff as a tool, `transfer_to_<agent_name>`, with `on_handoff`,
an `input_filter` and an `is_enabled` callable that can hide a handoff by state
**[source]**. LangGraph's swarm does the same with a tool returning
`Command(goto=agent, graph=Command.PARENT, update={"active_agent": ...})`, and
needs a checkpointer so the next turn resumes with the last active agent
**[source]**. LangChain archived `langgraph-supervisor` on 2026-09-20 and now
recommends "the supervisor pattern directly via tools rather than this library"
**[docs]**.

This is a different act from the glossary's **handoff** (a run passing its work
to a person or another run instead of finishing): control moves between agents
and the run goes on. The `clarify` request asks which word to use.

### 4c. Shared channels

- **A shared conversation** (GroupChat, Magentic, MoA layers): every agent sees
  every turn. Simple, and the failure MAST calls "ignored other agent's input"
  (1.9%) and "task derailment" (7.4%) live here.
- **Peer messages** (Claude Code teams, Codex `send_message`): a mailbox per
  agent. Claude Code keeps them at `~/.claude/teams/{team}/inboxes/{agent}.json`
  with a shared task list (pending, in progress, completed, with dependencies and
  file-locked claims) **[docs]**.
- **A board**: one append-only record every agent may read and post to, and no
  agent routes. The pattern is old (the blackboard systems of 1980s AI) and has
  come back in several forms this year:
  - ArcticSwarm's bulletin board is the **only** channel. Each task is either
    *isolation* (may post, may not read) or *collaboration* (reads the board), so
    agents do not converge on the first plausible answer. Keeping the wrong first
    candidate fell from 32.2% to 22.3% of runs with the gate **[paper]**.
  - Codex can replace direct messages with a board (`disable_direct_message`),
    so all coordination goes through one observable channel **[source]**.
  - Google's data-discovery blackboard: the central agent posts a request and
    agents that each own a slice of a data lake, or web search, **volunteer** if
    they can answer, so the centre need not know who knows what (13-57% relative
    gain in end-to-end success) **[abstract]**.
  - Agensh's typed shared context board **[abstract]**, Antigravity's
    "shared, append-only message board" ("Workers don't message each other
    privately"; posts go to `@name`, `@group` or `@all`, and a waiting worker is
    "asleep on the board, using no tokens until a post mentions it") **[docs]**,
    and LeanMarathon's blueprint file as the "shared system of record"
    **[abstract]**.
- **Git as the channel** (the C compiler, Cursor, Agensh): the repository is the
  shared state, push and pull are the sync points, and merge conflicts are the
  collision signal. It works when an oracle can judge each commit.

### 4d. Between vendors: A2A

A2A 1.0.0 **[docs]**, accepted into the Linux Foundation's Agentic AI Foundation
on 2026-08-27, defines an Agent Card, a `Task` with states (submitted, working,
input required, auth required, completed, failed, canceled, rejected), `Message`,
`Part` and `Artifact`, streaming, at-least-once push webhooks and signed cards.
Its own framing is that MCP is "the vertical integration layer" and A2A "the
horizontal protocol". **[inference]** Keel's run already has every field A2A's
task needs; no source read uses A2A *inside* a swarm, only at its edge.

---

## 5. Organise

- **Flat peers fail first, then work with an oracle.** Cursor's first version
  had equal agents claiming tasks in a shared file with locks: agents held locks
  too long, 20 agents ran at the speed of two or three, and with no owner they
  became "risk-averse" **[docs]**. The C compiler stayed flat (16 agents, lock
  files in `current_tasks/`, no orchestrator) and worked, because each agent took
  "the next most obvious" failing test **[docs]**. When all 16 hit the same kernel
  bug they overwrote each other's fixes; the fix was not a manager but an oracle
  that split the work (GCC compiles most files, Claude's compiler a random subset).
- **Planner, worker, judge.** Cursor's second design: planners explore and
  create tasks, and can spawn sub-planners; workers "grind on their assigned task
  until it's done, then push"; a judge decides at each cycle's end whether to go
  on. An integrator role "created more bottlenecks than it solved" and was
  removed **[docs]**.
- **A coordinator that does not do the work.** Antigravity's `/swarm`
  (preview, 2026-11-10) turns the current conversation into a coordinator that
  "splits the task", "doesn't do the technical work itself" and "judges what
  comes back". Workers start with a clean context and a brief posted to the board
  ("what it owns, what it must not touch, and what 'done' looks like"); a
  `@verifier` is added "for every two to four workers" and reports problems to the
  worker that wrote the code; a `@monitor` "stays asleep while the swarm is making
  progress" and posts only if everyone goes quiet before the work is done. Workers
  share the workspace by default, and the coordinator can give each its own git
  worktree; a removed worker must "land its changes first" **[docs]**.
- **Roles are a means, not a goal.** The co-scientist's six roles (generation,
  reflection, ranking, evolution, proximity, meta-review) each run a distinct
  step of a search loop **[docs]**. Kimi's swarm has "no predefined roles"; the
  orchestrator creates "domain-specialized agents" per task **[docs]** (its help
  page now says the swarm is driven by Kimi K3). K2.6's Claw Groups (research
  preview) extends the same coordinator to agents "from any device, running any
  model" with people in a shared space; when an agent fails or stalls the
  coordinator "automatically reassigns the task or regenerates subtasks" **[docs]**. Persona prompts lowered debate
  accuracy (§3). AutoSwarm has a planner propose the team, each task unit with a
  responsible agent, a supervising agent, acceptance conditions and dependency
  edges; removing supervisory review cost 12.8 points on PlanCraft **[paper]**.
- **Model per role.** Anthropic: Opus lead, Sonnet sub-agents. Cursor: "the most
  suitable model for each role" (GPT-5.2 for long runs; "Opus 4.5 tends to stop
  earlier"). Cognition's "Smart Friend": a weaker primary consults a stronger
  model, which worked across frontier models and failed when the primary was
  their own small model **[docs]**. SwarmBench found the orchestrator's model
  matters most (GPT-5.4 50.5, Sonnet 4.6 43.5, Kimi K2.5 32.8) and that removing
  the sub-agent model cards from its context hurt most **[paper]**.
- **Recursion** stays rare and bounded: Cursor's sub-planners, Codex's nested
  delegation, Cognition's manager over child Devins. Claude Code teams allow no
  nested teams **[docs]**; Keel allows none in v1.
- **Who owns the end.** In every system that worked at scale, one agent or one
  piece of code owns the result: the lead, the judge, the merge, the Lean
  compiler. MAST's ChatDev fix that gave +9.4% was a clearer role spec and the CEO
  agent having the final say **[paper]**.

---

## 6. Focus

- **Fresh contexts are the point.** The repeated justification for a sub-agent
  is a clean context: Cognition's reviewer "works best with a clean context"
  (2 bugs found per PR on average, 58% severe) **[docs]**; Kimi's sub-agents keep
  their own working memory and return only task-relevant output **[paper]**;
  Cursor needs "periodic fresh starts to combat drift and tunnel vision" **[docs]**.
- **The brief decides the quality.** Anthropic's early agents spawned "50
  subagents for simple queries" and duplicated searches until the lead was given
  scaling rules and each brief got boundaries **[docs]**.
- **Decomposition is the hard step.** ToMap (arXiv 2607.11307) **[abstract]**
  found the decomposer, not the prover, to be "the critical bottleneck" in proof
  autoformalization, and spent its test-time compute evolving candidate
  decompositions (+19.0% on ProofFlowBench).
- **Decompose against an oracle.** The units that worked at scale were ones an
  external check could pass alone: a failing test (C compiler), a file compiled
  against GCC, a lemma Lean accepts, a program an evaluator scores. Where no such
  check exists, the evidence points to fewer agents.
- **Isolation before collaboration.** ArcticSwarm's gathering gate keeps some
  agents from reading the board, which defers early consensus **[paper]**. MoA
  does the opposite on purpose: each layer reads all of the last **[abstract]**.
  **[inference]** For search tasks the order matters: independent drafts first,
  shared evidence after.
- **Context for the orchestrator itself.** Anthropic's lead saves its plan to
  memory because context past 200K tokens is truncated **[docs]**. SwarmBench's
  SwarmExp puts skills, tricks and model cards learned from past runs into the
  orchestrator's context **[paper]**.

---

## 7. Iterate

- **Vote** (the field's "self-consistency", "majority voting", "sampling and
  voting"): N independent answers, the most common wins. "More Agents Is All You
  Need" (arXiv 2402.05120) **[abstract]** showed accuracy scaling with N, more on
  harder tasks. It is the baseline every other method must beat at equal budget,
  and usually does not (§3).
- **Debate**: agents see each other's answers and revise over rounds. At matched
  budget it ties or loses to a vote; most of its gain is in the first exchange.
  It wins in specific settings (a data-cleaning study reported F1 roughly doubled
  over a vote) **[secondary]**.
- **When the minority is right.** Minority Sentinel (arXiv 2606.29270)
  **[abstract]**: model errors are correlated, so a vote assumes what is false; in
  about one in four split cases the minority was right. A small classifier over
  the debate's features overturns the majority with 81.2% precision, where an LLM
  judge doing the same lost accuracy overall.
- **Layered refinement** (Mixture-of-Agents, arXiv 2406.04692) **[abstract]**:
  each layer's agents read all of the previous layer's outputs; open models
  together scored 65.1% on AlpacaEval 2.0 against 57.5% for GPT-4o.
- **Tournaments.** The co-scientist ranks hypotheses by pairwise debate and an
  Elo rating, and says plainly that "the Elo is an auto-evaluation and is not
  based on an independent ground truth" **[docs]**.
- **Evolution.** AlphaEvolve keeps a database of programs; a prompt sampler
  builds prompts from good ones, Flash proposes breadth, Pro depth, and automated
  evaluators score; it improved the best known result on about 20% of 50+ open
  problems, and only applies where a result "can be described as an algorithm,
  and automatically verified" **[docs]**.
- **Verify, don't vote.** The systems with the best results replace aggregation
  by agreement with aggregation by check: Lean (LeanMarathon, LEAP, Aristotle),
  tests and CI (C compiler, Cursor), ArcticSwarm's integration gate (a builder's
  and an independent reviewer's `Verified` verdict before the answer is released;
  removing it cost 5.9 points), AutoSwarm's supervisors. MAST's verification
  failures (no or incomplete verification 8.2%, incorrect verification 9.1%,
  premature termination 6.2%) are 23.5% of all failures **[paper]**.

---

## 8. Orchestrate

### 8a. Model or code

The October convergence in `agent-subagent-architectures.md` §7b (the model does
the leaf work, code decides who runs and what happens to results) has
strengthened. ArcticSwarm's phrase for it is "model proposes, harness disposes":
the orchestrator has no execution tools, and the harness owns spawning (a lifetime
cap of 16), tool tables, verdict counting and deadlines **[paper]**. SwarmBench
also bars the orchestrator from tools **[paper]**. ADK's `SequentialAgent`,
`ParallelAgent` (each child in an isolated branch, run under an asyncio task group)
and `LoopAgent` (`max_iterations`, or a child's `escalate` action ends the loop)
are the same split as SDK types **[source]**. Antigravity's Dynamic Workflows
(2026-11-13) has the agent write a short Python script, shown for approval, with
`phase()`, `agent(prompt, schema, role, model, workspace)`, `parallel()` and
`pipeline()`; each agent returns schema-checked output through a `finish` tool,
workflow agents "don't see the script or each other", and `workspace` is
`inherit`, `branch` (its own worktree) or `share` **[docs]**. That is Claude Code's
Workflow tool (§7b there) with the write isolation made a parameter. The other direction is trained:
Kimi's orchestrator learns all five decisions by RL (§8c).

### 8b. Scheduling and concurrency

- **Locks fail at scale; optimistic writes work.** Cursor replaced locks with
  writes that fail if the state changed since it was read **[docs]**.
- **Concurrency caps** are everywhere and small: Codex's default 16, OpenHands
  5-8 (`agent-subagent-architectures.md` §5), ArcticSwarm 16 per lifetime, Claude
  Code teams "start with 3-5" and "5-6 tasks per teammate" **[docs]**.
- **Count the critical path, not the steps.** Kimi measures a swarm by
  `CriticalSteps = Σ_t (S_main^(t) + max_i S_sub,i^(t))`: the orchestrator's
  steps plus the longest sub-agent in each parallel stage **[paper]**. That is the
  latency a person waits; total steps are the bill.
- **Stragglers.** ArcticSwarm's answer check waits up to 300 seconds, after which
  its conditions become advisory **[paper]**. **[inference]** Any join needs a
  deadline and a rule for what a missing part means.

### 8c. Budgets, and the two ways spawning goes wrong

- Agents use about 4× the tokens of chat and multi-agent systems about 15×
  (Anthropic) **[docs]**; the C compiler spent 2 billion input tokens; Cursor
  "trillions".
- Kimi's training names the two failures any spawn policy has to avoid:
  **serial collapse** (the orchestrator does everything itself despite having
  capacity) and **spurious parallelism** (spawning many sub-agents without real
  decomposition, a reward hack). Its reward has a term for spawning and a term for
  sub-agents finishing, both annealed to zero so that only the task result counts
  in the end **[paper]**. SwarmBench: "a higher parallelism rate does not
  necessarily lead to higher parallelism gain" **[paper]**.

### 8d. Failure handling

- **MAST's 14 modes** **[paper]**, in three groups: specification (disobey task
  spec 11.8%, disobey role spec 1.5%, step repetition 15.7%, loss of history 2.8%,
  unaware of termination 12.4%); inter-agent misalignment (conversation reset
  2.2%, fail to ask for clarification 6.8%, task derailment 7.4%, withholding
  information 0.85%, ignoring another agent 1.9%, reasoning-action mismatch
  13.2%); verification (premature termination 6.2%, no or incomplete
  verification 8.2%, incorrect verification 9.1%). The authors' conclusion is
  that most need "structural redesign" rather than better prompts.
- **Small transactions.** LeanMarathon "turns one brittle multi-hour run into
  many local, recoverable, parallel transactions": each lemma is proved and
  CI-gated on its own, so a failure loses one lemma **[abstract]**. Anthropic added
  resume from checkpoint, retries and rainbow deployments for its long research
  runs **[docs]**. Claude Code's Workflow caches completed `agent()` calls so a
  resumed run skips them (`agent-subagent-architectures.md` §7b).
- **Shutdown and orphans**: Codex's coordinated tree shutdown and provisional
  children (§7b there); Claude Code teams list slow shutdown and lagging task
  status as known limits **[docs]**.

---

## 9. Case study: a hard maths problem across many agents

**What has happened.** In 2026 AI systems resolved a run of Erdős problems
(Quanta, 2026-08-03) **[docs]**. Harmonic's Aristotle produced a Lean proof for
#728 on 2026-01-06 from an argument found with GPT-5.2 Pro. A DeepMind team
screened 700 problems marked open with Gemini; a later DeepMind agent resolved 9
of 353 at a few hundred dollars each. An amateur's method was to "feed that
solution into a fresh instance of the chatbot" to check it, and repeat. The
caveats are as instructive: #333 was retracted when a 1977 paper turned out to
have solved it, several "solutions" were rediscoveries, and one DeepMind report
found 6.5% of candidate solutions "meaningfully correct" (cited by LeanMarathon).

**Independent teams, checked, then shared.** DeepMind's quantum-algorithm work
(2026-11-23, arXiv 2611.09822) **[docs]** gave "separate, independent agent teams"
of Gemini 4 agents each problem; ideas "were then verified with Lean, before
entering a shared notebook", and "every four hours, agents from each team met at a
virtual conference to trade, debate and compare ideas". Results include an 11.8×
cheaper fusion-simulation circuit and a 290× faster arcsin routine, with the Lean
library open-sourced. The order is §6's: isolation, then a check, then sharing.

**How the multi-agent provers are built** **[abstract]**:

- **LeanMarathon** (2026-06-03): four "contract-scoped agents construct, audit,
  prove, and repair" a blueprint, a Lean file that is at once proof skeleton,
  natural-language proof graph and shared record. Stage one makes the statement
  faithful "through adversarial review"; stage two discharges the proof DAG
  "from its dynamic leaves upward in parallel CI-gated rounds". It formalised
  seven theorems from four Erdős problems with no `sorry` (258 lemmas).
- **LEAP**: decomposes into smaller units against the Lean compiler; all 12
  Putnam 2025 problems; one-shot rate on its own Lean-IMO-Bench from under 10% to
  70%.
- **ToMap**: decomposer, formalizer, prover, with test-time compute on the
  decomposer.

**The pattern, as a sketch for any hard problem** **[inference]**:

1. **Make the problem checkable first.** Fix the statement (adversarial review of
   the formal statement against the informal one, by agents that did not write it).
   Every later step trusts this.
2. **Decompose into a DAG of claims**, each with its own check (a Lean lemma, a
   test, a computation). The plan is a file every agent reads, not a conversation.
3. **Fan out over the leaves.** Many independent attempts per open leaf (vote is
   useless here; the checker decides), in fresh contexts, with the dependencies'
   statements but not their proofs.
4. **Feed failures back into decomposition**, not just retries: a leaf that
   resists N attempts is split, restated or flagged as possibly false
   (counterexample search is a separate kind of agent).
5. **Integrate by check, not agreement**, and keep a person on what no checker
   covers: the statement's faithfulness, novelty against the literature, and
   whether the result matters.

The same shape carries to the other uses in this repo:

| Use | The checkable unit | The fan-out | The single writer |
|---|---|---|---|
| Large migration or build (coding) | a test, a file against a reference, a module's CI | one worker per unit, git as channel | the merge, gated by CI |
| PR review | one finding | specialists, then one validator per finding | the orchestrator posting |
| Research question | a cited claim | searchers by sub-question, isolation then board | the lead writing the report |
| Data analysis (Lens) | a query result that reproduces | one agent per data source or hypothesis, volunteering on a board | the writer of the answer |

---

## 10. What recurs

1. **Fan out only where parts can be judged alone.** Breadth search, alternative
   attempts, independent validation, units under an oracle.
2. **One writer.** Many agents read, explore, propose or check; one agent or the
   merge writes.
3. **Code owns the control flow**: spawn caps, joins, deadlines, verdict counts,
   budgets. The model proposes.
4. **Verify, don't vote.** Agreement is weak evidence when errors correlate.
5. **Isolate before sharing**, so the swarm does not converge on its first idea.
6. **References, not transcripts**, move between agents.
7. **Small transactions**: each part checked and kept on its own, so failure is
   local and resume is cheap.
8. **Compare at matched spend**: against one agent with the same budget and
   against a vote over N single runs, per task, more than once.

**Anti-patterns seen**: a flat team with locks; parallel writers on one
workspace; an integrator agent in the path of every change; debate as a quality
method; personas as diversity; spawning to look busy; an orchestrator that
forwards findings instead of understanding them (Claude Code's coordinator prompt:
"Never write 'based on your findings'", `agent-subagent-architectures.md` §7c).

---

## 11. Where Keel, Forge and Lens stand

Already in the design: briefs and typed reports (`report_schema`); reports as
untrusted data (`keel/tools-and-agents.md` §4c); siblings not chains, no recursion,
`clamp_to_parent` and per-agent model tiers; one budget ledger for a run and its
children checked at every admission point, including spawn, and a lifetime
spawn cap, `budgets.subagents_total` (`keel/run-spec.md` §3); review's fan-out and validation as harness code (`review.md` §11h); frozen
acceptance criteria and a completion gate; a concurrency cap in `Task`'s
description (`tools.md`).

Gaps this pass shows:

- **Parallel writers are allowed.** `forge.implement`'s `general-purpose`
  sub-agent holds `core.write` and `core.shell`, and the only guard is a prompt
  line ("Never launch two sub-agents in the same turn if their write targets could
  overlap"). The strongest negative result read (83.0% to 59.0%) is exactly this
  case.
- **No join semantics** beyond "the orchestrator reads the reports": no deadline,
  no rule for a missing part, no critical-path measure.
- **No shared channel** between sub-agents, by design; nothing for the cases where
  one would help (research, Lens discovery).
- **No campaign shape** for work too large for one run with an oracle to split it
  (`orchestration.md` §6 has task splitting across runs, without an oracle).
- **No matched-spend rule** in `eval.md` for adopting a multi-agent shape.

The proposals are in
[`agent-design/proposals-swarms-2026-11.md`](./agent-design/proposals-swarms-2026-11.md).

---

## Sources

As code (SHAs in `sources.md`): OpenAI Agents SDK (`src/agents/handoffs/`),
`langgraph-swarm-py`, Google ADK (`src/google/adk/agents/`), CrewAI (`crew.py`,
`tools/agent_tools/`).

Papers, full text (HTML; parts of some read through a summarising fetch):
2512.08296 (scaling agent systems), 2503.13657 (MAST), 2602.02276 (Kimi K2.5),
2605.02801 (orchestration-trace survey), 2608.30661 (SwarmBench), 2609.01870
(ArcticSwarm), 2610.10263 (dynamic concurrency in coding), 2610.25966
(information-flow probes), 2610.33048 (AutoSwarm).

Papers, abstract only: 2510.01285 (blackboard data discovery), 2606.29270
(Minority Sentinel), 2609.35875 (cognitive diversity and debate), 2402.05120 (More
Agents), 2406.04692 (Mixture-of-Agents), 2606.05400 (LeanMarathon), 2606.03303
(LEAP), 2607.11307 (ToMap), 2609.26781 (Agensh, read earlier).

Official pages and posts: Anthropic, "How we built our multi-agent research
system" (2025-06-13) and "Building a C compiler with a team of parallel Claudes"
(2026-02-05); Cursor, "Scaling long-running autonomous coding" (2026-01-14);
Cognition, "Don't Build Multi-Agents" (2025-06-12) and "Multi-Agents: What's
Actually Working" (2026-04-22); Claude Code agent teams docs; Kimi K2.5 blog and
K2.6 help page; A2A specification 1.0.0 and the AAIF announcement (2026-08-27);
OpenAI Swarm README and Agents SDK handoffs docs; LangGraph swarm and supervisor
READMEs; Google Research, AI co-scientist (2025-02-19); DeepMind, AlphaEvolve
(2025-05-14); Quanta, "Why the Legendary Erdős Problems Are Falling to AI"
(2026-08-03).

Google Antigravity: "Gemini 4 Carbon in Google Antigravity" (2026-11-10), the
`swarm` and `dynamic-workflows` docs and the changelog (v2.31.0 2026-11-09, v2.32.0
2026-11-13, read partly through a summary); Kimi K2.6 blog (2026-04-20); DeepMind,
"Finding faster quantum algorithms with agents and formal verification"
(2026-11-23).

Secondary: the data-cleaning debate result (from a search summary of arXiv
2606.02866).

Not read: Agensh's code; Aletheia (DeepMind's Deep Think maths agent, not found on
the DeepMind blog); the quantum-algorithms paper itself (2611.09822); the Kimi K2.5
step-limit appendix.
