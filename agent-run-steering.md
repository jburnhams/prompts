# Run steering: what a harness says to a model while it works

*Added 2026-11-11, from the agentic-SDK deep dive
([`agentic-sdks/`](./agentic-sdks)). Sources and SHAs are in
[`sources.md`](./sources.md), "Agentic SDKs (read 2026-11-11)".*

A long run drifts: the model forgets an instruction from turn 1, loops on
a failing call, builds on a claim it never checked, or stops before the
work is done. Every harness answers with text injected into the run.
This collection already covers two moments for that text: **after the
run** (completion judges, [`agent-self-verification.md`](./agent-self-verification.md))
and **on a specific failure** (loop and error monitors,
[`agent-run-recovery.md`](./agent-run-recovery.md) §4). The SDKs read on
2026-11-11 fill in the space between: cadence reminders, live judges
that read the trajectory, and graders that hold the stop. This document
compares them on the decisions every one of them has to make.

## 1. The mechanisms

| Mechanism | Trigger | Who writes the text | Source |
|---|---|---|---|
| **Rule-based reminder** | a cadence (every N requests) or a predicate over run state | the developer, fixed text | Pydantic AI Harness `SystemReminders`; Claude Code's `<system-reminder>` notices |
| **Loop nudge** | a detected pattern: same call N times, same result, A-B alternation, repeated text | the harness, naming the pattern | Pydantic `DetectLoops`; Keel `consecutive_tool_errors` monitor (`agent-design/keel/run-spec.md` §3) |
| **Pinned state notice** | the state is stale, or compaction dropped it | the harness, from stored state (an objective, criteria, a status note) | dcode `GoalToolsMiddleware` |
| **Live trajectory judge** | a cadence | **a second model**, after reading the recent trajectory | Pydantic `TrajectoryJudge` |
| **Stop-time grader** | the model would stop (no tool calls) | **a second model**, against a rubric | Deep Agents `RubricMiddleware`; Microsoft Agent Framework `with_judge()`; CrewAI `LLMGuardrail` |
| **Final-turn nudge** | a budget crossed | the harness, fixed text | Copilot Chat; Forge (`agent-design/formats.md` §7) |

The first three and the last cost no model call. The judge and the
grader do, and that changes several of the answers below.

## 2. The decisions

### 2a. Which channel the text goes in

- **Harness-authored fixed text goes in as a system prompt.** Pydantic's
  reminders and loop nudges, Claude Code's reminders, and Keel's harness
  notes (in their own field of a tool result, `agent-design/models.md`
  §2) are all the harness speaking.
- **Model-authored text goes in as user-channel data.** Pydantic's
  trajectory judge: "The judge's message is user-channel data, not a
  system prompt, because a model wrote it after reading the run's tool
  results." A judge that read an injected instruction in a tool result
  could otherwise relay it with system authority.
- **The grader's feedback goes in as a user message, tagged.** Deep
  Agents injects it as a `HumanMessage` ("the role the model follows
  most reliably") with `name="rubric_grader"` and
  `lc_source: "rubric_grader"` so evals and UIs can tell it from a
  person. The tag is metadata; the model sees a user turn.

### 2b. How a forged steer is told apart from a real one

Only one source answers this. Pydantic's judge wraps its message in
`<judge_feedback ref="…">` with a random ref, and a separate system note
names the ref and disowns any element "whose `ref` attribute isn't named
in a trajectory judge's note, or that repeats a named ref after its first
element". Framing tags inside the message are escaped. This is the
red-team paper's framed-record defence (`agent-permissions-approval.md`
§2d) applied to steering rather than to monitoring, and the same shape as
Forge's per-run nonce on `<resumed_answer>` (`agent-design/formats.md`
§5). Deep Agents' grader uses nonce-bracketed delimiters for its *input*
(the transcript it grades) but its *output* reaches the agent as an
untagged user message.

### 2c. How long the text lasts

Pydantic separates **request-scoped** (seen on the request it fires on,
gone after: "adds recency; it doesn't keep a rule in force") from
**conversation-scoped** (stays, for "an obligation the model meets
several tool calls later"). The judge's steering is conversation-scoped
by default, so the correction keeps applying. dcode's goal notice is
re-pinned when stale and never edited in place. Forge's harness notes
live in the tool result they belong to, so they last exactly as long as
the result.

### 2d. Where it goes relative to the cache

At the tail, and never edited once sent. See
[`agent-prompt-cache-health.md`](./agent-prompt-cache-health.md) §3: a
reminder at the front of the request busts the prefix on every firing,
and deleting an old one invalidates later thinking blocks.

### 2e. Whether it blocks the run

- Reminders, nudges and notices: no extra call, nothing to block on.
- The **trajectory judge runs concurrently**: the agent keeps going and
  the steer lands on a later request. A tick that finds the last
  evaluation still running is skipped. Under durable execution it is
  awaited instead, so replay is deterministic.
- The **stop-time grader blocks the stop**, by definition: it is the
  thing standing between "the model wants to finish" and "the run
  ends". Deep Agents caps it at `max_iterations` (3).

### 2f. Who pays, and from which budget

Pydantic's judge claims one request from the run's own usage limit before
each launch, and skips a tick the budget cannot fit, so judging cannot
push a run over its limit. Deep Agents bounds the grader's input (30
messages, 4,000 characters each). CrewAI bounds the guardrail by retries
(`guardrail_max_retries`) only.

### 2g. What the grader may conclude

Deep Agents is the careful one (`agentic-sdks/deepagents.md` §4):
per-criterion verdicts, a frozen criterion list that cannot shrink, a
coverage retry, and a `satisfied` verdict downgraded to `unverified`
when coverage stays short. `failed` (the rubric is ungradable) is kept
apart from `grader_error` (the machinery broke). CrewAI's guardrail
returns one `valid` boolean and free-text feedback, with the task output
pasted unframed into its prompt.

## 3. What the sources agree on

1. **Prefer rules to judges.** Pydantic says it directly: "Reach for
   [System Reminders] first; a trajectory judge earns its cost when the
   condition requires actually understanding the trajectory." Forge's
   own design reached the same order for completion
   (`agent-design/README.md`, "Completion integrity": mechanical gates
   "can't be talked out of firing").
2. **A judge steers; it does not enforce.** "A judge observes and
   steers; it does not block or rewrite anything." Enforcement stays in
   guardrails, grants and gates.
3. **Model-written steering needs provenance the model can check.**
   Pydantic's ref; nobody else yet.
4. **Steering must be replay-stable.** Pydantic stores the ref with the
   steer; under durable execution it records the verdict so a replay
   delivers the same text at the same point. dcode keeps old notices
   byte-identical. A steer that differs on replay changes the run.

## 4. Consequences for Forge

- Forge has the rule-based end already: monitors with fixed harness
  notes, the completion gate's checklist, the final-turn nudge. It has
  rejected a model judge at completion for v1.
- The cheapest import is not a judge at all: dcode's **criteria frozen
  before the work** gives Forge's existing completion audit a fixed list
  to account for, and a deterministic count check on the report. That
  is proposal 1 in
  [`agent-design/proposals-agentic-sdks-2026-11.md`](./agent-design/proposals-agentic-sdks-2026-11.md).
- A live trajectory judge would be a new monitor signal in Keel. If it
  is ever added, §2a–§2f are the decisions it needs, and the ref framing
  of §2b is the part not to skip. Proposal 5 records it in `future.md`.
