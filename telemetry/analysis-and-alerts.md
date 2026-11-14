# Analysing agent telemetry, and alerting on it

Evidence tags as in [`standards.md`](./standards.md).

## 1. What gets analysed, grouped by the question

| Question | Signal | Sources that do it |
|---|---|---|
| **What does it cost, and on what?** | tokens and cost per model call, attributed up the tree | Claude Code attributes cost and tokens to agent, skill, plugin, MCP server and MCP tool **[docs]**; Langfuse cost maps **[source]**; OpenInference `llm.cost.*` **[source]**; Keel `Usage.by_model` with price snapshot |
| **Is the prompt cache holding?** | cache read vs established prefix | Pydantic AI `WarnOnCacheBusts`, Keel `cache_collapse` (already adopted); Codex `websocket.continuation` reasons **[source]** |
| **Where does the time go?** | TTFT, time per chunk, tool duration, time blocked on a person | semconv metrics; Codex splits engine TTFT, service TTFT and client overhead **[source]**; Claude Code `tool.blocked_on_user` **[docs]** |
| **What fails, and how?** | error type per model call and per tool; refusals; malformed output; retries | Claude Code `api_refusal` and `tool_result.error_type`; Gemini CLI `malformed_json_response`, `invalid_chunk`, `content_retry` **[source]**; Keel refusal codes |
| **Is it looping or stuck?** | repeated identical calls, repeated failures, turns without progress | Gemini CLI `loop_detected` (count, type, an LLM confirmation with confidence) **[source]**; Keel's deterministic-crash stop (same tool and argument digest twice); Codex `goal.blocked` / `budget_limited` **[source]** |
| **How much work does a run do?** | model calls and tool calls per invocation | semconv `gen_ai.invoke_agent.inference_calls` and `.tool_calls` **[source]** |
| **Who decided?** | approvals, denials, classifier verdicts, waits | Claude Code `tool_decision.source`, Codex `tool_decision` and Guardian assessments **[docs, source]** |
| **Was the answer good?** | scores from code, LLM judges, people; outcomes days later | OTel `gen_ai.evaluation.result`; OpenInference annotations at span, trace and session scope; Langfuse and Phoenix score tables; Keel finding-outcome telemetry (`medium.md` §3e) |
| **What kinds of sessions are there?** | clustering and summarising whole sessions | Langfuse `topics` with centroids **[source]**; Docent's search, clustering and "Docent Agent" reports over transcripts, with a SQL-like DQL **[secondary, Transluce docs]** |
| **Did a change make it better?** | the same suite before and after | experiments in Braintrust, LangSmith, Phoenix; Keel `eval.md` on sandbox deployments |

Two kinds of analysis need content and two do not. Cost, latency,
errors, loops and counts work on **content-free** telemetry. Quality
scores and session clustering need **the transcript** (or a judge that
read it). That split is the strongest argument for keeping the trace
content-free and the transcript separate: the cheap, broadly visible
analyses never need the sensitive store **[inference]**.

## 2. Evaluations from traces

Three patterns **[docs and source across Langfuse, Phoenix, Braintrust,
LangSmith; inference for the grouping]**:

1. **Online evaluators.** A sampled stream of finished traces is fed to
   a judge (code or LLM); the result is written back as a score on the
   span, trace or session. The judge's own run is a trace, linked from
   the score (Langfuse's `execution_trace_id` on scores).
2. **Trace to dataset.** A person or rule promotes an interesting trace
   to a dataset item with an expected output; offline experiments then
   re-run the agent on the dataset.
3. **Outcome joins.** The real verdict arrives later from outside: a PR
   merged or reverted, a review thread resolved, a user's thumbs-down.
   It is joined to the trace by id as a score. Keel's §3e recorder is
   this pattern, and the pattern most platforms support least well
   (they assume the judge is near the trace).

ATIF exists so that trajectories can feed **training** as well as
evaluation (`rl_experience` with rewards and logprobs) **[source]**.

## 3. Loop and anomaly detection, in the run and after it

**In-run** (the harness acts on it): Gemini CLI's loop detector, Keel's
monitors and deterministic-crash stop, budget limits (Codex goals,
Keel `max_attempts`). The telemetry is a record that the harness acted.

**After the run** (a person acts on it): the same signals aggregated,
e.g. the rate of `loop_detected` per model version, the rate of
`context_overflow` per template.

Simple, effective detectors seen or implied **[inference from the above]**:

- The same tool with the same argument digest N times in a row
  (Keel already keys on the digest).
- The same error type from the same tool N times in a row.
- Turns since the last state-changing call (no edit, no write, no
  ending tool) above a threshold.
- Output tokens per turn collapsing towards zero, or the same text
  repeated (Gemini CLI's content loop).
- Cache read collapsing (Keel `cache_collapse`).

## 4. Alerts

Nobody in the sources defines alerts in the agent; alerting is done by
the backend on metrics or on queries over spans **[inference]**. What
the vendors ship as defaults **[docs, secondary]**: error rate, latency
percentiles, token and cost spikes per model, per-tool failure rates
(Grafana's MCP dashboard), evaluation score drops, and budget
thresholds.

The ones that matter for an agent platform, by who acts:

| Alert | Signal | Acted on by |
|---|---|---|
| Provider degraded | model call error rate or TTFT p95 per (provider, model) | platform on-call; failover |
| MCP server degraded | `execute_tool` error rate and p95 per server and tool | the server's owner |
| Cost anomaly | cost per run p95 per template version vs its baseline; any single run above a ceiling | template owner |
| Cache regression | `cache_collapse` rate per template version | template owner (a prompt change moved the prefix) |
| Quality regression | score mean per template version vs baseline (eval suite or outcome telemetry) | template owner; rollback |
| Stuck work | stages blocked, gates waiting beyond SLA, `repeated_infra_failure` | operator / approver |
| Safety | refusals, sandbox blocks, permission denials above baseline | security owner |

**[inference]** The right granularity is **template version**: almost
every regression in this list is caused by publishing a new version of
a template, prompt or tool group, so alerts should compare a version
with the one before it, and the alert should link to the diff.
