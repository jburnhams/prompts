# Context compaction: how a scaffold survives running out of room

A further drill-down alongside
[`agent-tool-surfaces.md`](./agent-tool-surfaces.md) and
[`agent-subagent-architectures.md`](./agent-subagent-architectures.md):
what happens when a long-running conversation approaches its context
window. Every agent with a long-enough task eventually has to answer
the same question — throw away detail to keep going, or stop — and the
answers here turn out to vary as much as tool surfaces and sub-agent
protocols do: what triggers it (a token-budget check run every turn, an
actual API error, a manual command, or some mix), what shape the output
takes (free text vs. a rigid template, XML vs. Markdown), whether it's
one mechanism or a layered pipeline of increasingly expensive
interventions, whether the discarded detail is genuinely gone or just a
pointer away, and — the specific thing this doc was asked to cover in
depth — the actual numeric token budgets involved.

**Methodology note**: a first pass covered nine sources — five (Copilot
Chat, Goose, Crush, Pi, Gemini CLI) had their compaction prompt text
already sitting in this collection's stored files, just never written
up as its own section; four (Claude Code, Codex CLI, OpenCode,
OpenHands) required going back to live upstream source, the same
pattern established across `agent-tool-surfaces.md` and
`agent-subagent-architectures.md`, where prompt-text-only extractions
repeatedly undersold real architecture. A second pass added nine more
sources read from local files already in this collection (Cline, Aider,
Roo Code, and the leaked Cursor, Devin, Windsurf, Warp, Replit,
Factory/Droid) and turned up two of this doc's richest findings —
Cline's three-mechanism layered-but-unpipelined design and Windsurf's
"externalize before compaction" strategy — from sources that hadn't
been checked for this topic at all before. Every source's individual
README has a "## Compaction" section with full detail and file
citations; this doc synthesizes across them.

## Sources covered

**With confirmed compaction content**: Claude Code (leaked, via
`leaked/claude-code/architecture-notes.md`), Codex CLI, OpenCode,
OpenHands, GitHub Copilot Chat, Goose, Crush, Pi, Gemini CLI, Cline,
Windsurf (leaked, partial — the strategy is confirmed, the prompt/
trigger text isn't), Cursor (leaked, partial — a prompt-injection-
defense tag only, dropped after v1.2, no summarization template),
Google Antigravity (leaked — a dual-context "Knowledge Items" system,
no trigger/threshold captured; see §4 and §5 below), GitHub Copilot CLI
(leaked — a 5-section structured Continuation Summary template plus a
distinct SQL-queryable cross-session recovery mechanism; no numeric
trigger threshold captured; see §1, §2, §5), **OpenClaw** (read from
source 2026-08-31, MIT — the only source here that **audits its own
summary and fails closed** when it cannot pass; see §2 and the new §2a),
Grok Build (leaked,
partial — the existence claim ("unlimited context through automatic
summarization") and a named post-compaction consumer-side contract are
confirmed, but no summarization prompt, trigger threshold, or recovery
philosophy is captured; see the note after §5 below).

**Confirmed absent via targeted search** (every relevant file read in
full, keyword search came up empty — a stronger finding than "not
checked"): Roo Code, Devin (leaked).

**Not found in captured files, but flagged as a capture gap rather than
a confirmed absence** (the relevant orchestration/session-management
code plausibly exists but isn't part of what this collection fetched):
Aider, Warp (leaked), Replit (leaked), Factory/Droid (leaked).

**No compaction mechanism confirmed at all** — everything else in this
collection. For most of those, that means "not checked yet," not
"confirmed absent" — the exceptions are sources whose architecture
makes compaction structurally unnecessary (single-turn benchmark loops
like SWE-agent/mini-swe-agent/Live-SWE-agent/Augment SWE-bench Agent,
which run one bounded task and exit) or where the product genuinely
doesn't seem to have it (Jules's leaked prompt explicitly shows no
summarization tool in either captured version — see
`leaked/jules/README.md`).

---

## 1. What triggers compaction

The clearest three-way split: does the scaffold compact **proactively**
(a token-budget check run before it's actually a problem), **reactively**
(only after the API rejects an oversized request), or does it require a
**manual** command — and, more interestingly, which sources combine more
than one of these.

| Trigger model | Sources |
|---|---|
| **Proactive only — no reactive-on-error path found**, an actual context-length API error is treated as a hard failure rather than triggering recovery | Codex CLI (checked pre-turn and mid-turn against a 90%-of-window threshold; two *non-token* proactive triggers too — the model was swapped mid-thread, or downshifted to a smaller-context model), OpenCode (per-turn token check before every LLM call; no reactive path found) |
| **A layered proactive pipeline plus a genuinely separate reactive fallback** | Claude Code — four-to-six proactive mechanisms run in sequence every turn (see §3), *plus* a distinct reactive path triggered only by the literal API error string "Prompt is too long," independent of the proactive chain |
| **Explicit soft vs. hard trigger distinction, named as such** | OpenHands — "soft" triggers (event-count or token-count thresholds) can be deferred/retried next step; a "hard" trigger (an explicit unhandled condensation-request event) forces an emergency single-shot summarization with a shrink-and-retry loop if even that overflows |
| **Manual command, trigger mechanics otherwise not investigated for this pass** | Claude Code (`/compact`, `/clear` — investigated), OpenCode (`/compact`/`/summarize` — investigated); presumably present in most interactive CLI tools but not confirmed for Goose/Crush/Pi/Gemini CLI in this pass |
| **Background vs. foreground as an explicit, tracked distinction** | Copilot Chat — a small state machine lets summarization run concurrently with the agent continuing other work rather than always blocking the turn; the foreground/background choice is even carried into telemetry |
| **Not captured — prompt text only, no surrounding trigger logic fetched** | Goose, Crush, Pi, Gemini CLI — each folder's compaction prompt is confirmed, but what decides *when* to call it lives in code not part of this collection |
| **Model-proposes, user-approves — a genuinely different third trigger shape, neither proactive-silent nor manual-command** | Cline — a `condense` acknowledgment string confirms the model generates a summary that the **user must explicitly accept** before it takes effect ("The user has accepted the condensed conversation summary you generated"). Not silent (the user sees and approves it first) and not a bare manual command either (the model appears to propose it, not just execute a user-typed `/compact`). The prompt that actually asks the model to produce the summary isn't in any captured file, so what triggers the *proposal* itself remains unconfirmed. |

**A real design fork worth naming**: Codex's and OpenCode's
proactive-only, no-reactive-fallback design is a different philosophy
from Claude Code's belt-and-suspenders layered approach — Codex/OpenCode
bet on the proactive check catching everything before it becomes a
problem; Claude Code assumes the proactive checks can still be wrong and
builds a second, independent recovery path for when they are.

## 2. Prompt shape: free text vs. structured template, XML vs. Markdown

| Shape | Sources |
|---|---|
| **Minimal free text, loosely bulleted, no rigid section headers** | Codex CLI — "Create a handoff summary... Include: current progress and key decisions, important context/constraints, what remains to be done, critical data/references. Be concise, structured, and focused." One prompt for every model family, no per-model variants. |
| **Structured Markdown template, 5-6 named sections** | Crush (Current State / Files & Changes / Technical Context / Strategy & Approach / Exact Next Steps), OpenCode (Objective / Important Details / Work State with Completed-Active-Blocked sub-sections / Next Move / Relevant Files), Pi (Goal / Constraints & Preferences / Progress with Done-In Progress-Blocked / Key Decisions / Next Steps / Critical Context), GitHub Copilot CLI (leaked — Task Overview / Current State / Important Discoveries / Next Steps / Context to Preserve, wrapped in `<summary></summary>` tags, injected only when "the context window is exhausted" with no numeric threshold stated) |
| **Structured template, 8-9 named sections with sub-bullets** — the most elaborate Markdown-shaped templates surveyed | Claude Code (9 sections: Primary Request and Intent, Key Technical Concepts, Files and Code Sections, Errors and fixes, Problem Solving, All user messages, Pending Tasks, Current Work, Optional Next Step), Copilot Chat (8 numbered sections: Conversation Overview → Technical Foundation → Codebase Status → Problem Resolution → Progress Tracking → Active Work State → Recent Operations → Continuation Plan, each with its own sub-bullets) |
| **Structured XML tags, not Markdown** | Gemini CLI — `<state_snapshot>` with named child tags (`<overall_goal>`, `<active_constraints>`, `<key_knowledge>`, `<artifact_trail>`, `<file_system_state>`, `<recent_actions>`, `<task_state>` with `[DONE]`/`[IN PROGRESS]`/`[TODO]` markers) |
| **Structured prose with named sections, but semi-structured rather than a rigid template** — a Jinja2-templated prompt producing guided paragraphs, not a fill-in-the-blank skeleton | OpenHands — `USER_CONTEXT`/`TASK_TRACKING`/`COMPLETED`/`PENDING`/`CURRENT_STATE` plus code-specific sections, with worked examples rather than a strict format contract |
| **Five named sections, two of which are machine-audited afterwards** | OpenClaw's `safeguard` mode (the default for new configs) — `## Decisions`, `## Open TODOs`, `## Constraints/Rules`, `## Pending user asks`, `## Exact identifiers`. Shorter than Claude Code's nine or Copilot's eight, and the brevity is the point: the last two sections exist to be *checked*, not merely requested. See §2a. |
| **A private reasoning scratchpad before the structured output**, stripped after generation | Claude Code (`<analysis>`, explicitly stripped — "a drafting scratchpad... has no informational value once the summary is written"), Goose (`<analysis>`), Gemini CLI (`<scratchpad>`), Copilot Chat (`<analysis>`/`<summary>` pair) — four independent sources converging on "think privately first, then emit the structured output," none of them showing the reasoning to the model in the post-compaction context |

## 2a. The summary as an audited artifact, and the fail-closed path

Every source in §2 *asks* for a shape. OpenClaw is the only one that
**verifies it got one**, and the only one whose compaction can refuse to
happen.

The mechanism, from
[`src/agents/agent-hooks/compaction-safeguard-quality.ts`](https://github.com/openclaw/openclaw/blob/v2026.8.1/src/agents/agent-hooks/compaction-safeguard-quality.ts):

1. **The final summary budget is applied *before* validation**, so the
   text being audited is the text that would actually be stored. This
   ordering is the whole design — a summary that satisfies the contract
   and then loses a section to truncation has satisfied nothing.
2. **The five headings must appear, in order**, in the retained body.
3. **Two sections are audited against the source**: pending user asks,
   and exact identifiers extracted from the messages being summarised.
   A rebuild plan protects exactly those two and lets the model's own
   prose shrink around them, with the audited sections capped at a
   0.25 content share so they cannot themselves eat the budget.
4. **A bounded number of corrective attempts.** If none produces a
   summary that validates, compaction **stops before writing a
   transcript entry and keeps the original history.**

Point 4 is the finding. Everywhere else in this survey, a bad summary is
simply the context you now have — the failure is silent and unrecoverable,
because the detail it replaced is gone (§5). OpenClaw's answer is that a
compaction which cannot be verified is not performed, which trades a
context-limit failure the operator will notice for a silent-quality
failure they will not.

**The in-flight request is protected by name**, which no other template
here does. When a user request is still unresolved, the prompt adds:

```text
Make the exact request below the first item in ## Pending user asks.
Its run owner will resume it after compaction, so summary prose cannot mark it complete.
```

with the request itself in an escaped `<untrusted-text>` block. The
second sentence is doing real work: it tells the model that a fact it
might reasonably infer from the transcript — "this was handled" — is
wrong for a reason outside the transcript.

**Operator input to the summariser is untrusted data, not prompt.**
`/compact <focus>` text is capped at 800 code points and wrapped rather
than spliced, as is a custom identifier-policy string. This collection
has repeatedly found untrusted content interleaved into instruction
text; a compaction focus string is an easy one to miss, because it comes
from the operator and therefore *feels* trusted — but it reaches a model
call that rewrites the agent's entire memory of the session.

**Old summaries are demoted on re-embed.** When a summary is later
included as supporting context, `nestRequiredSummaryHeadings` rewrites
its five `##` headings to `###`, so a previous summary cannot be
mistaken for the live contract by the next summariser. A small
mechanism, and the only instance in this collection of a scaffold
worrying about its own output being re-ingested as instructions.

**Omitted non-text input is marked, with a budget on the markers.**
Built-in summarisation receives text, not pixels, so images become
`[image data omitted from summary input]` — but the marker policy is
itself bounded: at most two fixed markers on each of the first eight
affected messages, one aggregate statement thereafter, and a hard
ceiling of **847 UTF-8 bytes** of added markers per summariser request.
Compare §5's recovery discussion: the marker deliberately does not claim
the model processed the data, so a later reader can tell the difference
between "the summariser saw this and judged it unimportant" and "the
summariser never saw it."

## 3. One mechanism vs. a layered pipeline vs. a pluggable strategy

The biggest architectural fork in this survey: does the scaffold have
*one* way to compact, or does it treat compaction as a set of
interchangeable/stackable strategies?

| Architecture | Sources |
|---|---|
| **A single mechanism** | Codex CLI (three *backend implementations* — local, remote/server-side, no-summary reset — but these are a deployment/feature-flag choice, not a strategy chain the model or a fallback triggers), Crush, Pi, Goose (as captured — no pipeline/fallback structure visible in the prompt text alone) |
| **A two-tier fallback: cheap deterministic trim, then expensive LLM summarization** | OpenCode — `prune` (deterministic, truncates/removes old large tool outputs once savings clear a threshold, protecting specific tool-name-tagged content) is tried before invoking the `compaction` sub-agent at all |
| **A two-tier fallback in the other direction: LLM summarization first, structural truncation as the fallback when summarization itself can't be done** | Copilot Chat — "Full" mode (real LLM call) vs. "Simple" mode (no LLM call at all, just priority-packing raw history with large tool results truncated) — Simple mode exists specifically for when Full mode fails or would exceed budget, i.e. a fallback *for the summarizer*, not a fallback for the underlying task |
| **A 4-6 stage proactive pipeline, cheapest-first, explicitly not mutually exclusive** | Claude Code — snip (targeted, model-nudged trimming of a specific region) → microcompact (no LLM call — heuristic placeholder-replacement of old tool outputs) → context collapse → autocompact (real LLM summarization), plus a separate reactive path and an experimental session-memory-reuse path. A source comment states directly that "both may run — they are not mutually exclusive." |
| **A genuinely pluggable strategy pattern — the compression algorithm itself is a swappable component** | OpenHands — the only source in this survey with this shape. `CondenserBase` is an abstract interface; confirmed concrete implementations are `LLMSummarizingCondenser` (the real strategy), `NoOpCondenser` (explicit disable), and `PipelineCondenser` (chains multiple condensers). Any agent — top-level or sub-agent — selects its own condenser at config time, independent of every other agent in the same delegation tree. |
| **Multiple parallel, non-pipelined mechanisms — not a fallback chain, not a single strategy either** | Cline — three separate, independently-triggered mechanisms coexist with no confirmed ordering or fallback relationship between them: silent deterministic truncation (keep-first-and-last, drop-the-middle, no LLM call), a user-approved LLM "condense" summarization, and a narrower duplicate-file-read dedup. Structurally distinct from Claude Code's/Copilot's cheapest-first pipelines (§ above) because nothing in what's captured shows one mechanism escalating to the next — they read as independent answers to the same problem rather than stages of one design. |

**Takeaway**: Claude Code's and OpenCode's "cheap heuristic trim before
expensive LLM call" pipelines are independently convergent designs (see
Design takeaways below) — but OpenHands's pluggable `Condenser` is a
different kind of sophistication entirely: not a fixed sequence of
fallbacks, but compaction treated as a first-class, swappable software
component.

## 4. Incremental/anchored summarization vs. from-scratch every time

A capability easy to miss unless the actual summarization-call code is
read closely: does compacting for the *second* time in a long session
re-read and re-summarize the entire history again, or does it build on
top of the summary from the *first* compaction event?

| Approach | Sources |
|---|---|
| **Explicit incremental UPDATE mode — a genuinely separate prompt for "merge new information into the existing summary"** | Pi — `UPDATE_SUMMARIZATION_PROMPT` is a distinct prompt (from the fresh-summarize `SUMMARIZATION_PROMPT`) invoked when a prior summary exists: "PRESERVE all existing information... ADD new progress... UPDATE the Progress section: move items from 'In Progress' to 'Done'... you may remove [something] if it's no longer relevant." OpenCode — the `compaction` agent's own prompt instructs it, when a `<previous-summary>` block is present, to treat it as the anchor and update it in place (preserve still-true details, remove stale ones, merge in new facts) rather than re-deriving everything from the raw history again. Two unrelated codebases arriving at the same design independently. |
| **The same anchor-and-update idea, one level up — corpus-level rather than session-level** | Google Antigravity (leaked) — its Knowledge Items (KI) system is generated by a background "Knowledge Subagent" that "distills... into new KIs or updates existing KIs as appropriate" — not updating one conversation's rolling summary, but incrementally updating a persistent, cross-conversation, per-topic knowledge base. A third data point for this pattern, structurally distinct from Pi's/OpenCode's single-session anchoring. |
| **A prompted re-distill instruction, part of the required-section contract rather than a separate prompt** | OpenClaw — the same five-section instruction block ends with *"When prior compaction summaries are present, re-distill them with new messages and remove stale duplicate detail."* A third position: not a distinct UPDATE prompt (Pi), not an anchor block the model is told to edit in place (OpenCode), but a standing clause inside the one prompt, so the second and tenth compactions run the same call. Paired with the heading-demotion rule (§2a), which is what stops the prior summary's headings from competing with the live contract while it is being re-distilled. |
| **Not confirmed either way** | Every other source in this survey — none of the other captured prompts explicitly address whether a second compaction event in the same session re-reads full history or anchors on the prior summary; this is a real gap in what's been investigated, not a confirmed "from scratch" finding |

**Why this matters for token budgeting specifically**: incremental/
anchored summarization is cheaper (only the messages since the last
compaction need to be read by the summarization call, not the entire
session) and arguably less lossy (the model is editing its own prior
structured output rather than re-deriving the same facts from raw
transcript a second time, with a fresh chance to drop something). Given
only two of nine sources confirm this design, it's plausible more
sources do this and it just wasn't visible in what was captured — flagged
as a good candidate for a future deeper pass.

## 5. Recovery: is the discarded detail actually gone?

| Philosophy | Sources |
|---|---|
| **Explicit pointer back to the full, still-readable transcript** — compaction is lossy for the model's immediate context, not for the underlying record | Claude Code (the post-compaction summary message includes a literal instruction: "If you need specific details from before compaction... read the full transcript at: `${transcriptPath}`," with the transcript's current line count included), Copilot Chat (same pattern — a trailing hint to use the `ReadFile` tool on the tracked session transcript, frozen into the summary text at compaction time specifically so it doesn't change on later renders and bust the prompt cache) |
| **The full history is structurally never deleted, but no agent-facing re-query tool exists** — recovery exists at the data layer, not as a capability the model can reach for | OpenHands — condensation events are appended to an append-only conversation log; the "view" the LLM sees is computed by replaying non-destructive `Condensation.apply()` over the full log, which retains every original event and an exact record of what was forgotten at each step. Genuinely recoverable in principle (e.g. by a human debugging the session, or by product tooling), but not confirmed reachable by the agent itself mid-conversation. |
| **Explicitly treated as the sole surviving record — no recovery offered** | Crush ("This summary will be the ONLY context available when the conversation resumes. Assume all previous messages will be lost"), Gemini CLI ("This snapshot is CRITICAL, as it will become the agent's *only* memory of the past") |
| **No summary offered at all — the plainest form of loss found in this survey** | Cline's deterministic truncation path: "Some previous conversation history with the user has been removed to maintain optimal context window length... intermediate conversation history has been removed." No LLM summary stands in for the deleted middle, and no pointer back to a transcript is offered — more primitive than every other recovery philosophy in this table, which all substitute *something* (a summary, a pointer, an append-only log) for what's dropped. |
| **Sidestep recovery entirely — externalize important facts to a persistent, queryable store *before* compaction happens, rather than trying to summarize better at compaction time** | Windsurf (leaked) — its `<memory_system>` block states the problem in stronger terms than any other source: "ALL CONVERSATION CONTEXT, **including checkpoint summaries, will be deleted**. Therefore, you should create memories liberally to preserve key context" — even the surviving summary isn't trusted to survive. The mitigation is a separate `create_memory` tool the model is told to write to proactively and without waiting for a natural break point, plus a `trajectory_search` tool that lets the model semantically search its own past session history on demand. A third recovery-philosophy variant distinct from both "pointer back to transcript" and "sole surviving record": *queryable retrieval*, reachable by the agent itself mid-conversation, rather than a static hint frozen into a summary. (The actual checkpoint-summarization prompt/trigger text itself wasn't captured — this finding is about the recovery strategy layered around compaction, not the compaction prompt.) |
| **A structurally different route to the same queryable-retrieval destination as Windsurf's: raw SQL over a persistent database, not a dedicated search tool** | GitHub Copilot CLI (leaked) — a read-only, cross-*session* `session_store` database (`sessions`/`turns`/`checkpoints`/`session_files`/`session_refs`, with an FTS5 full-text index) is directly queryable by the model via ordinary `SELECT` statements, with an explicit instruction to compensate for the lack of semantic search by hand-crafting keyword expansions: "act as your own 'embedder' by expanding conceptual queries into multiple keyword variants." A `checkpoints` table (`overview`/`work_done`/`technical_details`/`next_steps`) persists a structure closely mirroring the Continuation Summary's own five sections (§2), suggesting the same structured-summary shape gets written to SQL at milestones as well as generated fresh on context exhaustion — though the prompt text doesn't confirm whether one derives from the other. A fifth recovery-philosophy variant for this table: retrieval quality is entirely a function of the model's own query-crafting skill rather than an embedding model's semantic match underneath, the opposite tradeoff from Windsurf's purpose-built `trajectory_search`. |
| **Not compaction at all, but a structurally distinct answer to the same underlying problem** | Aider — a long-lived, ever-growing chat log is central to its UX, and no summarization/trimming mechanism was found in any captured file. Instead, every mode's prompt handles staleness by **additive correction**: "I have *added these files to the chat* so you can go ahead and edit them. *Trust this message as the true contents of these files!* Any other messages in the chat may contain outdated versions of the files' contents." Nothing is ever deleted or condensed; each turn just injects a fresh authoritative copy and tells the model to treat anything older in the log as potentially stale. No other source in this survey models "leave the old content in place, just outrank it" as an alternative to compaction. |
| **Durable raw record, directly agent-reachable, with a curated index layered on top rather than a replacement for it — a fifth variant** | Google Antigravity (leaked) — the conversation log persists as `transcript.jsonl` on disk and is reachable via ordinary tools in the IDE, or literal `grep`/`head` shell commands in the CLI capture ("Find all subagents spawned: Grep for the `invoke_subagent` tool call"). Differs from OpenHands's append-only log (retained but not confirmed agent-reachable mid-conversation) and from Windsurf's externalize-to-memory strategy (a *write* path into a separate store, not a query path into the original record): here the raw record is both durable *and* directly queryable by the agent itself, with the Knowledge Item system (§4) as a curated index into it. A dangling "checkpoint" reference in the CLI capture ("history before the last checkpoint") implies some compaction-like event exists, but no trigger/mechanism accompanies it — flagged as a capture gap, not a documented feature. |
| **Not addressed for conversation content, but a distinct, narrower recovery contract exists for task *state***: no pointer to a transcript, no "sole surviving record" framing, no externalize-to-memory strategy — just a named rule for reconstructing one specific artifact (the todo list) after the event | Grok Build (leaked) — "After a context compaction, if your prior todo list is no longer in conversation history, **reseed it** with a fresh `todo_write` call (`merge: false`) before continuing the task," triggered by a named system-reminder header the agent is told to watch for: "the harness signals this with a `## Pre-Compaction Todo List` system-reminder, your FIRST tool call after the reminder MUST be `todo_write` (`merge: false`) reconstructing the remaining phases from the pre-compaction snapshot." This is a genuinely different kind of "recovery" from every other row in this table — none of it is about the model's own lost conversational detail; it's a harness-enforced contract for rebuilding one specific piece of task-tracking state that would otherwise silently vanish across the compaction boundary. No pointer back to a full transcript and no externalization strategy for anything *other* than the todo list was found. |
| **Recovery is not the answer — non-performance is.** The only source here where a compaction that cannot be verified simply does not happen | OpenClaw's `safeguard` mode (§2a): the audit runs against the post-budget text, and if no corrective attempt validates, *"compaction stops before writing a transcript entry, keeps the original history, and surfaces the existing recovery outcome."* Every other philosophy in this table is a way of living with a summary once it exists; this one declines to install a summary it cannot vouch for, which converts a silent quality failure into a loud context-limit one. It stacks with the ordinary recovery story rather than replacing it — the full conversation stays on disk, and compaction *"only changes what the model sees on the next turn."* |
| **Not addressed** | Codex CLI, OpenCode, Goose, Pi |

## 6. Token budgeting — the numbers

The specific ask this doc was written to cover in depth. Four sources
had concrete, code-confirmed numeric thresholds available; the rest
either don't expose fixed numbers in what's captured, or the relevant
config lives outside the fetched files.

| Source | Proactive trigger threshold | Reserved buffer | Summary/output cap | Other numeric limits |
|---|---|---|---|---|
| **Claude Code** | Effective context window minus buffer | **13,000 tokens** (env-overridable) | Up to **20,000 tokens** reserved for the compaction summary itself | 20,000-token pre-limit warning threshold; 50,000-token post-compact re-attachment budget (5,000/file, 5,000/skill, 25,000 total across skills); circuit breaker gives up after **3 consecutive autocompact failures** |
| **Codex CLI** | **90% of the resolved context window** (configurable; a scope setting chooses full-context vs. sliding-window-suffix accounting) | n/a (threshold-based, not buffer-based) | No fixed target — the prompt doesn't ask for a specific length | **20,000 tokens** of trailing raw user messages preserved verbatim (not summarized) in the compacted history |
| **OpenCode** | Total counted tokens (input+output+cache) ≥ window capacity minus reserved buffer | **20,000 tokens** (CLI-package layer) / 20,000-buffer + 8,000-keep (core-package layer — two parallel implementations, see §3) | **4,096 tokens** for the compaction summary's own output | `tail_turns` default **2** recent turns kept verbatim; 2,000–8,000-token guard on that recent slice; tool outputs truncated to **2,000 characters** when building the compaction prompt; `prune` fallback triggers at **20,000 tokens** minimum savings, protects at least **40,000 tokens** of tagged tool-call content |
| **OpenHands** | Event count (`max_size`) or token count (`max_tokens`, if configured) | n/a (event/token-count based, not a reserved-buffer model) | Condenses down toward roughly half of `max_tokens` when the token trigger fires | `max_size` default **80** events (SDK preset) / 240 (bare class default); `keep_first` default **4** events always preserved verbatim (SDK preset) / 2 (class default); `minimum_progress` **0.1** (≥10% of the view must be condensable or the condenser refuses to run); hard-reset emergency path retries up to **5** times, shrinking event-string length by **20%** per attempt |
| **Copilot Chat** | `triggerSummarize` flag set when budget exceeded (exact upstream threshold not confirmed in this pass) | n/a | Optional hard cap: `min(sizing.tokenBudget, maxSummaryTokens)` — the summarization attempt fails outright (`'Summary too large'`) rather than truncating if exceeded | None else confirmed as a fixed constant |
| **Goose, Crush, Pi, Gemini CLI** | Not captured | Not captured | Not captured | Not captured — these four folders have the compaction *prompt* confirmed but not the surrounding orchestration code that would show trigger/threshold numbers |

**What actually converges**: of the four sources with a real
"reserved buffer before the window fills" number (Claude Code, OpenCode
×2, and Codex's percentage-based equivalent), the buffer sizes cluster
in the same rough band — Claude Code's 13,000 tokens and OpenCode's
20,000 tokens are the same order of magnitude regardless of how
different the surrounding architectures are, and Codex's 90% threshold
against a typical large context window lands in a comparable absolute
range. That's a real, if loose, convergence — three unrelated codebases
independently decided a five-figure token buffer is roughly the right
safety margin, rather than landing on wildly different numbers.

## 7. Prompt-cache interaction

Only two sources address this explicitly, but both treat it as a real
design constraint, not an afterthought.

- **Claude Code**: compaction is a deliberate, accepted cache-reset
  point (cached system-prompt sections are explicitly cleared on both
  `/compact` and `/clear`) — but two of the pipeline's cheaper stages
  are themselves cache-*preservation* optimizations: microcompact edits
  the cache directly (deleting stale tool-result cache entries without
  invalidating the surrounding cached prefix) rather than busting it,
  and full compaction can optionally fork off the main conversation's
  already-cached prefix instead of paying for a cold cache-miss
  summarization call.
- **Copilot Chat**: cache breakpoints are explicitly stripped from the
  summarization request before it's sent — the summarization call is
  deliberately excluded from the normal caching path rather than an
  attempt being made to keep it cache-compatible.
- **OpenClaw** goes further than either, and in the other direction:
  rather than managing the cache *around* compaction, it makes cache
  boundaries a first-class feature of the system prompt itself, and then
  makes prompt-state changes deferred so they cannot bust it
  mid-session. Three mechanisms, all confirmed in source:
  - The system prompt carries a **literal boundary marker in its own
    text** — `SYSTEM_PROMPT_CACHE_BOUNDARY` is the string
    `"\n<!-- OPENCLAW_CACHE_BOUNDARY -->\n"`. Everything above it is
    memoised on a hash of its inputs (a 64-entry LRU) and is
    byte-identical across turns and across sessions sharing a
    workspace; everything below is rebuilt per turn. Section placement
    is argued as a caching decision in code comments — temporal
    context, channel guidance, the runtime line and watched sessions
    all sit below the boundary specifically so a day rollover or a
    channel change cannot invalidate the workspace prefix.
  - **`ensureSystemPromptCacheBoundary`** appends the marker to any
    prompt that lacks one — a hook that overrides the system prompt
    would otherwise route every dynamic addition into the cached
    prefix. The commit reference in the source names that as the bug
    it fixes.
  - **Prompt-state mutations default to deferred invalidation.** The
    repository's own `AGENTS.md` states it as a rule:
    *"Prompt-state mutations (skills/tools/memory) default to deferred
    cache invalidation — effect next session; immediate invalidation is
    an explicit opt-in."* So learning a skill or changing a tool policy
    does **not** rewrite the cached prefix underneath a running
    conversation. This collection has documented plenty of caching
    tactics; this is the only instance of a scaffold constraining what
    the *rest of the product* may change, in order to protect one.
  - One more detail worth carrying, because it is the kind of thing
    only a live deployment finds: the `## Runtime` line deliberately
    renders a cron job's stable base session key and **drops the
    volatile `:run:<id>` suffix**, because some providers' automatic
    literal-prefix caches include that line before the tool catalogue,
    and a per-run id there would defeat reuse across runs of the same
    job.
- **Not addressed**: every other source in this survey.

## 8. Sub-agent / multi-session isolation

Relevant only to sources with a real delegation mechanism (see
`agent-subagent-architectures.md`) — does compacting the parent's
history affect an in-flight child, and does each child manage its own
context independently?

- **OpenHands**: confirmed fully independent — each sub-agent spawned
  via `delegate`/`task` gets a brand-new event log and its own
  condenser instance (defaulting to a summarizing condenser "so deep
  runs auto-compact instead of erroring on context overflow" — a
  correctness requirement for long delegated runs, not just a cost
  optimization, per an in-code comment). No cross-agent or
  orchestration-level shared condensation exists.
- **OpenCode**: confirmed fully independent — a spawned child task gets
  a distinct session ID with no shared message state; compacting the
  parent session cannot touch an already-running child's context.
  Confirmed by reading the session-creation code, not just assumed.
- **Codex CLI**: sub-agents (`spawn_agent`) are separate session/thread
  instances; each compacts independently; no cross-agent compaction
  coordination found in what was read.
- **Claude Code**: not specifically investigated in this pass — the
  "Team" coordination system documented in `architecture-notes.md`
  wasn't cross-checked against the compaction pipeline.
- **Everyone else**: n/a (no confirmed sub-agent delegation mechanism
  to check against) or not investigated.

---

## 9. Someone measured the loss, and proposed a carrier instead of a summary

Every mechanism above is a *summarization* strategy, and this doc has had
to take on faith the thing they all trade away: fidelity. Stencil's
["Snapcompact"](https://blog.can.ac/2026/06/10/snapcompact/) (Can Bölük,
10 Jun 2026 — the same author as the OMP material in
`agent-tool-implementations.md`) supplies both a measurement of that loss
and a strategy that isn't on this doc's list.

**The measurement.** SQuAD v1.1 extractive QA over a corpus packed to each
technique's carrying capacity, 30 questions per chunk spread evenly, four
frontier models, with `UNREADABLE` as an allowed answer. Against a
verbatim-text ceiling of ~0.90 F1:

| Technique | Fable 5 | Opus 4.8 | GPT-5.5 | Gemini 3.5 Flash |
|---|---|---|---|---|
| text (ceiling) | 0.904 | 0.911 | 0.861 | 0.898 |
| handoff | 0.540 | 0.248 | 0.368 | 0.889 |
| compact (prose / server-side) | 0.406 | 0.000 | 0.896 | 0.000 |
| snapcompact (img-6×10-sent) | 0.882 | 0.601 | 0.822 | 0.805 |

The blunt version, and the single most useful sentence in this doc's whole
subject area: **"the summaries preserve what you were doing, not what you
knew."** On compacted context Gemini answered `UNREADABLE` **240 times out
of 240**, Opus 209 — a total loss of extractable fact, not a degradation.
That is a hard number to put against §5's "is the discarded detail actually
gone" question, and the answer for prose compaction is *yes, essentially
all of it*, on two of four models tested.

Two exceptions matter. **OpenAI's server-side compaction is the outlier
that works** (0.896, above its own text ceiling of 0.861), which the author
flags with appropriate suspicion — "they might just be skipping it, who
knows?" And **Gemini's handoff documents score 0.889 by disobeying their
own prompt**: they "write down the trivia," which is exactly what a handoff
is told not to do and exactly what preserves the facts.

**The failure mode of handoffs, stated better than anywhere else here.**
This doc's §5 treats handoff-style externalization as the strong option.
The author agrees it is "as good as it gets" and then names its
pathology: unlike a plan, handoffs are unsteered, so "agents waste precious
context writing an unnecessarily detailed diary, followed by a TODO list
that practically begs the next agent to declare the goal impossible and
ship an 'MVP' instead." The same objection applies to eliding tool results
— "LLMs complete stories; if half of your story is `[elided...]`, how
confident do you think it will be about using them?" — which is a
mechanism-level argument that elision degrades *tool-calling* specifically,
not just recall.

**The strategy.** Render the context into a dense pixel-font bitmap and
hand it back as an image. A 1568×1568 PNG holds ~40,000 characters in a
6×10 font — ~10,000 tokens of text — and bills as 3,279 image tokens under
Anthropic's pixel formula, so the carrier costs about a third of the text
it carries, with no summarization step and therefore no fact loss by
construction. Reported: context carried 170k → 46k tokens (÷3.7), and a
÷1.8–÷2.9 full-run bill at F1 parity across four frontier models.

Three findings inside it are transferable regardless of whether anyone
ships this:

- **There is a legibility cliff at 35–40 px² per character**, and it is
  sharp: 8×13 transcribes at 1.00, 6×10 at 0.79, 5×8 at 0.37, 4×6 at 0.02.
  Above the cliff, exact transcription degrades long before *identifier*
  recall does — the model stops reproducing every byte well before it
  stops reading the names.
- **The input saving is not free: there is a decode tax.** Models decode
  dense images by reasoning about them, costing ~5× the output tokens of
  the text condition. At Anthropic's output pricing that can eat the input
  saving in a single pass — mitigated only by the fact that the decode
  happens once while the carry is paid every turn. Any comparison that
  counts input tokens alone is wrong.
- **The format can't make the model read sooner, but it can make the
  reading unambiguous.** White-box probes on Qwen2.5-VL-7B locate the
  layer where a visual patch's top-1 vocabulary entry becomes the answer's
  BPE piece ("lock-on"). Aligning glyph cells to the model's 28×28 vision
  patch grid and repeating lines in alternating hues moved lock-on
  barely at all (L24 → L22) but took the decoded answer's probability from
  **0.39 to 1.00**. Depth is architectural; confidence is yours.

The supporting claim — that this is a memory format rather than a party
trick — rests on representation probes: matched text↔image pairs reach
cosine 0.66 at layer 19 against −0.06 for mismatched pairs,
cross-carrier nearest-neighbour retrieval is 12/12 from layer 2 onward, and
the two carriers' question-similarity geometries correlate at r = 0.94 by
layer 1. Stated as: "the PNG isn't a picture of your context — it converges
to being your context."

**Caveats, several supplied by the author.** SQuAD extractive QA is a
*retrieval* proxy and not an agent-task proxy — it measures whether a fact
survives the carrier, not whether an agent can still act; a compaction
strategy is judged on more than fact retention. Whether it works at all "is
an empirical property of each model's vision stack, and you have to test
it" — Opus scores 0.601 where Fable scores 0.882 on the same rendering. The
tuning was done against the four models benchmarked. And this is vendor-run
research, though unusually the eval harness, font renderer, per-question
records and probes are open source in the OMP repo (`sources.md`), with a
stated reproduction cost of ~$35. Prior art is acknowledged: DeepSeek-OCR's
trained encoder for optical context compression, and Karpathy's riff on
pixels as an input medium.

For this doc's typology, it is a genuinely new branch: not a trigger, not a
prompt shape, not a retention policy, but **a change of carrier that makes
the compression lossless-by-construction and moves the cost from fidelity
to decode**. Nothing else surveyed here does anything like it.

## Design takeaways

- **Two unrelated codebases (Claude Code, OpenCode) independently
  converged on the same pipeline shape**: try a cheap, deterministic,
  non-LLM trim first (microcompact / prune), escalate to real LLM
  summarization only if that isn't enough. Neither borrowed from the
  other — this looks like a genuinely sound design that two different
  engineering teams arrived at separately, the same kind of signal
  `agent-subagent-architectures.md` found for addressable sub-agent
  protocols across Codex/OpenCode/OpenHands/Roo Code.
- **Incremental/anchored summarization (Pi, OpenCode) is a real but
  rare capability**, and probably underexplored in this survey rather
  than genuinely rare in the wild — only two of nine sources confirm
  it, but the other seven's captured material simply doesn't say either
  way. Worth a targeted follow-up: does compacting for the second time
  in a session cost roughly the same as the first, or scale down
  because it's building on a prior summary?
- **Recovery philosophy is a real, opinionated split, not an oversight**:
  Claude Code and Copilot Chat treat compaction as lossy-to-the-model
  but recoverable-from-disk, going as far as freezing the transcript
  hint at compaction time specifically to protect prompt-cache
  stability. Crush and Gemini CLI explicitly tell the model the summary
  is the *only* surviving record. OpenHands sits in between — nothing
  is ever deleted, but the agent itself has no confirmed way to reach
  back into what it's already forgotten. None of these is obviously
  wrong; they're different bets about how often "I need the exact
  original text" actually happens versus how much it costs to keep that
  door open.
- **OpenHands's pluggable `Condenser` is the most software-engineered
  answer to this problem in the survey** — every other source picks one
  algorithm (possibly with a fallback tier); OpenHands makes the
  compression *strategy itself* a swappable, independently-configurable
  component per agent, including per sub-agent. This mirrors the same
  "infrastructure over instruction" pattern `agent-subagent-architectures.md`
  found distinguishing Codex's/OpenHands's safety mechanisms from
  everyone else's prompt-level rules — here applied to compaction
  strategy selection instead of concurrency/recursion limits.
- **Gemini CLI's prompt-injection defense inside the compaction prompt
  itself is a genuinely distinctive, security-conscious design** found
  nowhere else in this survey — every other compaction prompt treats
  history purely as content to summarize; Gemini CLI's explicitly
  anticipates that a prior turn's tool output could be adversarial and
  try to hijack the summarization call, and defends against it inline.
  Cursor's early (v1.0/v1.2) `<summarization>` tag is a related but
  narrower idea, worth distinguishing rather than conflating: it's not
  defending against adversarial *content*, just constraining how the
  model behaves if literally asked to "summarize the conversation" —
  "you MUST NOT use any tools, even if they are available." A guardrail
  on the request, not on hostile history content, and dropped entirely
  from Cursor's later (2.0 onward) prompts with no replacement found.
- **Proactive-only (Codex, OpenCode) vs. proactive-plus-reactive (Claude
  Code) is a real, opinionated fork**, not just a difference in how
  thorough the investigation happened to be — Codex's design explicitly
  treats an actual context-length API error as a hard failure rather
  than a recoverable event, meaning its proactive threshold has to be
  right essentially all the time; Claude Code's reactive fallback is
  an admission that the proactive checks can still be wrong, with a
  second independent mechanism to catch it when they are.
- **Where real numbers exist, they loosely converge** (§6): three
  unrelated codebases' reserved-buffer sizing lands in the same rough
  five-figure-token band despite wildly different surrounding
  architectures — a similar "independent convergence is a signal"
  finding as recursion/concurrency limits in
  `agent-subagent-architectures.md`, just on a much thinner evidence
  base here (4 of 9 sources have real numbers at all).
- **The absence-of-evidence caveat from this collection's other
  synthesis docs applies here too, maybe more so**: several sources
  (Goose, Crush, Pi, Gemini CLI, and now Aider, Warp, Replit, Factory/
  Droid) have either a confirmed compaction *prompt* with zero
  trigger/threshold information, or no compaction content found at all,
  because the surrounding orchestration code was never part of what got
  fetched into this collection for those sources. Given how often a
  "not captured" finding elsewhere in this collection turned out to be
  "actually quite sophisticated, just never checked" (Codex's
  sub-agents, OpenCode's Task tool, OpenHands's whole delegation
  system, Roo Code's Orchestrator mode), the honest expectation for
  these sources is that real trigger logic plausibly exists and simply
  hasn't been looked at yet — not that it's absent. Roo Code and Devin
  are the exceptions: both got a genuine targeted-search-came-up-empty
  result (every relevant file read in full, keyword search covering
  every plausible term), a materially stronger claim than "not
  captured."
- **A single source (Cline) turned out to have three separate,
  uncoordinated context-management mechanisms rather than one** —
  silent lossy truncation, user-approved LLM summarization (with an
  unusual post-compaction instruction telling the model *not* to resume
  work until asked), and a narrow duplicate-file-read dedup — none of
  which call each other in what's captured. This doesn't fit either the
  "single mechanism" or "layered pipeline" bucket cleanly; it reads as
  a scaffold that grew multiple independent answers to "context is
  getting full" over time rather than one designed system, a useful
  reminder that this doc's three-way single/pipeline/pluggable
  typology is itself a simplification some real sources fall outside
  of.
- **Windsurf's "externalize before compaction" is a genuinely different
  strategic move than anything else in this survey**: every other
  source treats the problem as "how do we summarize well when
  compaction happens"; Windsurf's framing — that even the summary
  itself will eventually be deleted — leads to a different bet
  entirely: continuously push important facts out to a durable,
  separately-queryable store *before* compaction, so the compaction
  event's quality matters less. Combined with a `trajectory_search`
  tool letting the model reach back into its own past sessions on
  demand, this is the most pessimistic-about-recoverability design in
  the survey, and arguably the most defensive as a result. GitHub
  Copilot CLI (leaked) reaches the same "queryable retrieval, not a
  static pointer" destination by a different road: raw SQL access to a
  persistent, cross-session database with an FTS5 index, rather than a
  purpose-built semantic-search tool — two unrelated products
  converging on the same recovery *philosophy* (externalize and make it
  queryable) while diverging completely on *mechanism* (a bespoke
  memory-entry tool vs. a generic database the model must query
  skillfully itself).
- **Aider is a useful reminder that compaction isn't the only answer to
  a long-lived conversation** — its chat-log-native architecture solves
  the same underlying staleness problem with "leave old content in
  place, just tell the model to distrust it" rather than removing or
  summarizing anything. Worth keeping in mind as a design space this
  doc's typology doesn't otherwise cover: not every long-running
  scaffold needs compaction if it can instead re-assert ground truth
  every turn.
- **Grok Build's todo-reseed contract (§5) is a reminder that "recovery"
  isn't only about conversational content** — every other source in
  this doc's §5 answers "is the discarded *text* actually gone"; Grok
  Build is the only one found addressing a narrower, orthogonal
  question: does a specific piece of *task-tracking state* survive the
  compaction boundary, and if not, whose job is it to rebuild it. The
  answer here is structural rather than prompted-only-in-spirit — a
  named system-reminder header (`## Pre-Compaction Todo List`) plus a
  hard "your first tool call after this MUST be `todo_write`" rule —
  closer to OpenHands's soft/hard trigger distinction (§1) in how
  concretely it's specified than to any other source's recovery
  philosophy, but scoped to one artifact rather than the whole
  conversation.
