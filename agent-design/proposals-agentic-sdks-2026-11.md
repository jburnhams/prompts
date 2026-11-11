# Proposals from the agentic-SDK deep dive (2026-11-11)

**Status: proposals only. Nothing in `agent-design/` has been changed.**
Each item names the sections it would amend, so it can be accepted,
changed or rejected on its own. The research is in
[`../agentic-sdks/`](../agentic-sdks) (one file per SDK) and in two new
feature documents,
[`../agent-run-steering.md`](../agent-run-steering.md) and
[`../agent-prompt-cache-health.md`](../agent-prompt-cache-health.md),
plus sections added the same day to
[`../agent-deferred-tool-loading.md`](../agent-deferred-tool-loading.md) §6,
[`../agent-tool-result-transport.md`](../agent-tool-result-transport.md) §12,
[`../agent-run-recovery.md`](../agent-run-recovery.md) §6 and
[`../agent-self-verification.md`](../agent-self-verification.md) §14.

Prompted by `agentic_sdks_mcp_deep_dive.docx` at the repo root.

## Summary

| # | Proposal | Amends | Recommendation |
|---|---|---|---|
| 1 | Plan fixes the acceptance criteria as a list; `implement` reports on each, and the gate checks the count | `formats.md` §3a, §3c, §6; `system-prompts.md` plan and implement workflows; `generative.md` §2c | Adopt now |
| 2 | Record prompt-cache collapses as a run event and an eval metric | `eval.md` "Metrics"; `keel/triggers-and-runs.md` §10 (events) | Adopt now |
| 3 | Recover from a context-overflow refusal by stubbing the trailing tool batch, once | `formats.md` §7; `tools.md` implementation contract | Adopt now |
| 4 | An elicitation answered by a responder is a reissued call under MCP `2026-07-28` | `keel/tools-and-agents.md` §4e | Adopt now (Keel is on `2026-07-28`) |
| 5 | Two model judges, recorded with the shape to use if either is ever added | `future.md` | Record only |
| 6 | Per-model harness profiles: no change, record the evidence | `README.md` "Per-model prompt variation"; `keel/decisions.md` | Record only |

---

## 0. The document's design rules against Keel and Forge

The deep dive closes with a layered architecture for a large MCP estate
and eight rules. Keel already meets most of them, which is worth saying
before proposing anything, because it means the document is not asking
for a redesign.

| The document's rule | Keel / Forge today | Gap |
|---|---|---|
| Authorised catalogue → discovery/deferral → compact results → separate artifacts | Saved tool groups pin server snapshots; grants ⊆ groups; visibility `loaded`/`deferred`/`hidden`; results as refs (`keel/README.md` §0a, `keel/tools-and-agents.md` §4b, `artifacts.md`) | none |
| 1. Keep a small permanent core | `Expand` and the quick core of 3–5 tools (`models.md` §4) | none |
| 2. Separate discovery from authorisation; filter before visibility | Grants checked "at the executor, every call"; visibility "shapes what the model tries" and nothing else (`keel/tools-and-agents.md` §4b) | none |
| 3. Optimise at the source (server-side pagination) | Argument overrides cap `page_size` per tool (`keel/README.md` §0a); Forge does not own the servers | none Forge can close |
| 4. Artifacts are first-class: origin, identity, time, schema, hash, expiry | Refs with `produced_by`, scheme, immutability and lifetime (`artifacts.md` §2, §5.5; `local.md` §2a) | none |
| 5. Idempotent side effects, stable operation ids, an external record of completed work | Retries are fresh attempts; dead attempts' writes are "may have happened"; task handles followed, never reissued (`keel/pipelines.md` §7f, `keel/tools-and-agents.md` §4e) | one case under `2026-07-28` (proposal 4) |
| 6. Bounded subagents: read-only investigators, a separate path for mutations | Review roles have no `Bash`; delegates have no human channel; grants per agent (`review.md` §2, `tools.md` `Task`) | none |
| 7. Log decision quality, not just output; redact payloads in traces | `eval.md` metrics, run events | prompt-cache health is not measured (proposal 2) |
| 8. Sandbox executable code, and keep untrusted configuration out | A `checkout` workspace per run (`keel/run-spec.md` §3); tool sources come from Keel configuration, and nothing in the checkout can add an MCP server, hook or skill (`context-files.md` §12) | none |

The document's two most quoted mechanisms, provider tool search and
skill-scoped tools, are covered in
[`../agent-deferred-tool-loading.md`](../agent-deferred-tool-loading.md)
§6. Keel's `hidden` groups revealed by `Expand` or a monitor already do
the first; the second needs skills, which Forge does not have. Neither
becomes a proposal.

---

## 1. Plan fixes the acceptance criteria as a list; `implement` reports on each

**What dcode and Deep Agents do** (`../agentic-sdks/deepagents.md` §4–§5,
`../agent-self-verification.md` §14). Before any work, a criteria agent
drafts "usually 2-5" short, observable bullets; a person accepts, rejects
or amends them; the accepted list is frozen. When the agent stops, a
grader returns one verdict per criterion, and a verdict that accounts for
fewer criteria than the frozen list cannot end the run as `satisfied`.
The drafting prompt bans invented requirements, implementation detail,
and bullets that only restate the goal.

**What Forge does.** The plan report has `acceptance_criteria` as one
free-text string (`formats.md` §3c). The implement report has
`verification` (checks run) but nothing per criterion (§3a). The
completion audit (`README.md`, "Claiming `done`") asks the model to
derive requirements and forbids narrowing them, but the requirements it
derives are never written down, so nothing can check that it kept them
all.

**Proposal.** Take the frozen list and the deterministic check. Do not
take the grader model, which Forge has deferred.

1. **Plan output** (`formats.md` §3c): `acceptance_criteria` becomes an
   array of strings, each one observable result. The plan workflow
   (`system-prompts.md`, `forge.plan.v1.md`) gets dcode's drafting rules,
   adapted:
   - usually 2–5 criteria; each short, concrete, outcome-focused, and
     needed to decide whether the ticket is done;
   - keep the ticket's own constraints, names, paths and commands
     verbatim;
   - no requirement the ticket does not state or clearly require (no
     cleanup, refactoring, documentation or generic testing unless asked);
   - describe results, not implementation;
   - never a criterion that only restates the ticket or says the work is
     complete.
2. **Handoff** (§6): under the gated pattern, the person approving the
   plan approves the criteria with it. An amended plan is a new plan run
   that keeps every criterion the amendment did not touch (dcode's
   amendment rule: "Preserve every unaffected acceptance criterion").
3. **Implement report** (§3a) gains:

   ```json
   "criteria": [
     { "criterion": "string — verbatim from the plan",
       "status": "met | not_met | not_verified",
       "evidence": "string — the command, file or ref that shows it; required when met" }
   ]
   ```

4. **The gate** (`generative.md` §2c's computed findings block): when
   the envelope carried a `<plan>` with criteria, `Complete(done)` FAILs
   unless `criteria` has exactly one entry per plan criterion, with the
   text unchanged, and every entry `met`. This is stronger than dcode's
   count check because Forge has the list itself, so it compares strings,
   not counts. A run that cannot meet a criterion reports `failed` or
   `blocked` and says which, rather than dropping it.
5. **Without a plan** (implement dispatched straight from a ticket),
   there is nothing frozen. The report still lists the criteria the
   audit derived, and the gate checks only that the list is non-empty.
   This is dcode's own first-pass limit: "the guarantee is … that the
   criterion set cannot shrink mid-run, not that the first decomposition
   was complete."

**Why now.** It makes the completion audit's hardest rule ("do not
redefine success around a smaller or easier task") something the harness
checks rather than something the model remembers, at no model-call cost.
It also gives review's compliance specialist (`review.md` §11i) a list to
check against instead of prose. **Cost:** one field in two schemas, five
lines of prompt, one gate check.

## 2. Record prompt-cache collapses as a run event and an eval metric

**What Pydantic AI Harness does** (`../agent-prompt-cache-health.md` §2).
Per `(provider, endpoint, model)` and per conversation, it tracks the
prefix the provider has confirmed (`cache_read + cache_write`) and flags
a request that reads back more than 5% and at least 2,000 tokens less,
classified against the provider's retention window as `unexpected`,
`unknown`, `ttl_expired`, `compacted` or `unreported`. It only observes.

**What Forge does.** Keel keeps the prefix still by construction (fixed
tools array and system prompt; reveals as mid-conversation messages),
but nothing checks that it stays still, and `eval.md` has no cache
metric. A bug that moves the prefix (a reordered tool group, a volatile
field in the envelope, a reveal on a provider without mid-conversation
changes) would show up only as a bill.

**Proposal.**

1. The harness computes the check on every response and emits a
   `cache_collapse` run event with `reason`, `established_tokens`,
   `cache_read_tokens`, `missed_tokens` and the model key, for
   `unexpected` and `unknown` only. Thresholds are config values with
   the 5% / 2,000-token defaults (`README.md`, "Tool limits: configurable
   or fixed").
2. `eval.md` "Metrics" gains **cache read ratio** (cache-read tokens over
   input tokens, per run) and **collapse count by reason**, recorded as
   diagnostics: an `unexpected` collapse in a sandbox run is a bug
   report.
3. Retention windows come from the deployment's provider configuration;
   a provider with none classifies as `unknown`, which still reports.

**Why now.** Observe-only, no prompt change, and the one place this
design's "the prefix never moves" claim would be checked.

## 3. Recover from a context-overflow refusal by stubbing the trailing tool batch, once

**What Deep Agents does** (`../agentic-sdks/deepagents.md` §6,
`../agent-tool-result-transport.md` §12). When the provider refuses a
request as too long, the trailing batch of tool results (the ones the
model has not seen yet) is shrunk: a file read is cut with a pointer back
to the file, anything else is offloaded and stubbed. Then the request is
retried.

**What Forge does.** Runs are bounded by a turn budget and a
context high-water mark checked between turns, with a five-figure
headroom (`formats.md` §7). Large results are refs, so overflow is rare.
But one parallel batch of results, each under the ref threshold, can
still take a single request over the window, and the design does not say
what happens then. The likely behaviour is an infrastructure failure: no
`Complete`, a harness-posted failure note.

**Proposal.** Add to `formats.md` §7:

- If the provider refuses a request for length, the harness re-renders
  every result in the trailing batch above a small floor as an
  `<artifact>` stub (§8g), minting refs for them, and sends the request
  once more. The model sees ordinary stubs it can `Read`.
- If that request is refused too, the run gets the final-turn nudge
  with `budget_exhausted`, the same as crossing the high-water mark.
- The re-render is a `context_overflow` run event, so `eval.md` can
  count it.

**Why now.** It turns an unspecified failure into an existing mechanism
(refs) and an existing status, and it touches only results the model has
not yet seen, so nothing it already reasoned about changes.

## 4. An elicitation answered by a responder is a reissued call under MCP `2026-07-28`

**What the source shows** (`../agentic-sdks/langchain-langgraph.md` §2,
`../agent-run-recovery.md` §6). Under the stateless protocol, a server
that needs input returns `InputRequiredResult`, and answering means
**sending the `tools/call` again** with the answers. LangChain's adapter
says so in its module docstring. Anything the server did before asking
happens again unless the server made it idempotent.

**What Keel does.** §4e cancels elicitation unless a deployment
responder answers it. Keel speaks `2026-07-28` as its primary revision
(`keel/decisions.md` §14a, "MCP revision"; this proposal first assumed
the older `2025-11-25` ceiling in `adk.md` §0, which no longer applies).
So a responder's answer is already a second call, and §4e does not say
so. On a legacy server negotiated at `2025-11-25` or earlier, elicitation
is still a request inside the open call and §4e stands unchanged.

**Proposal.** Add to §4e:

- A responder-answered elicitation on a stateless server is recorded as
  a **reissued call** in the run's events, linked to the first.
- A responder may answer only for tools whose group settings or MCP
  annotations mark them `idempotentHint: true` or `readOnlyHint: true`.
  For any other tool the elicitation is cancelled, as without a
  responder, and the harness note says the call may have done part of
  its work.
- Annotations are server-supplied and not a trust boundary, so a group
  setting overrides them (the deep dive's §6.2, and Keel's existing rule
  that a group can override annotations, `keel/tools-and-agents.md` §4b).

**Why now.** The responder exists and the protocol already reissues the
call, so without the rule a responder can repeat a non-idempotent side
effect today.

## 5. Two model judges, recorded for `future.md`

Forge decided against an LLM judge at completion for v1 (`README.md`,
"Completion integrity"). The SDKs supply two concrete shapes, and if
either is ever added, the details below are the ones that matter. See
[`../agent-run-steering.md`](../agent-run-steering.md) §2.

- **A stop-time grader** (Deep Agents `RubricMiddleware`): per-criterion
  verdicts as a discriminated union; a frozen criterion list with an
  under-coverage retry and an `unverified` downgrade; `failed` (rubric
  ungradable) kept apart from `grader_error`; bounded, nonce-framed
  transcript input; at most 3 iterations; the final answer never
  rewritten. With proposal 1 in place, Forge's frozen list is the rubric.
- **A live trajectory judge** (Pydantic `TrajectoryJudge`): a Keel
  monitor signal `judge` with a model, a review focus, a cadence and a
  token window that keeps the original request. It runs concurrently,
  skips a tick while busy, claims its call from the run's budget, and
  delivers `AllGood` or a steer. The steer is **user-channel data in an
  element named by a random ref** that a harness note vouches for, never
  a system message, because a model wrote it after reading tool results.

**Trigger for revisiting.** The grader: when `eval.md` shows false `done`
claims surviving proposal 1's gate. The judge: when long runs show drift
the existing monitors cannot name (scope creep, unsupported claims).

## 6. Per-model harness profiles: no change, record the evidence

**What Deep Agents does** (`../agentic-sdks/deepagents.md` §2). Deep
Agents 0.7 removed its authored base prompt. Behaviour per model now
comes from profiles keyed by exact model id: a prompt suffix, tool
description overrides, excluded tools, extra middleware, with a rule
that required scaffolding cannot be excluded. The frontier profiles are
short (Anthropic's published guidance verbatim for Claude; a bias-to-
action suffix and a todo tool for Codex). The Nemotron profile is 1,857
lines, nearly all middleware: a text-to-tool-call parser and about ten
named guards and nudges.

**What Forge decided.** One canonical prompt per mode; per-model
variation only as subtraction by heading, if ever (`README.md`,
"Per-model prompt variation").

**Proposal.** No change. Add the evidence to the decision row: the one
harness that went furthest toward per-model tuning shows that frontier
models need little (and only generic guidance), and that what weaker
models need is **middleware, not prompt text**. That supports Forge's
position for prompts and points to where variation would go if Forge
ever serves an open model: a per-model-family set of harness checks
(tool-call repair, final-answer guard) in Keel, never a forked prompt.
Deep Agents' "scaffolding cannot be excluded" is the same guard Forge's
subtraction rule needs: an ending tool or a safety section can never be
the thing a profile removes.
