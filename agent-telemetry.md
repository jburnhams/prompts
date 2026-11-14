# Agent telemetry: two records per run, joined by ids

*Added 2026-11-14, from the telemetry deep dive
([`telemetry/`](./telemetry)). Sources and SHAs are in
[`sources.md`](./sources.md), "Agent telemetry (read 2026-11-14)".
Proposals for Keel, none adopted, are in
[`agent-design/proposals-telemetry-2026-11.md`](./agent-design/proposals-telemetry-2026-11.md).*

Every harness in this collection keeps some record of what it did. This
document is about the shape of that record once it has to leave the
process: be correlated with other systems, stored for months, shown to
someone who was not watching, analysed across thousands of runs, and
alerted on.

## 1. The concept

An agent run produces two different records, and the sources that do
this well keep them apart:

| | **Trace** | **Transcript** |
|---|---|---|
| What | timing, structure, cost, status of every operation | what the model saw and said, in order |
| Shape | spans, metrics, log events | an ordered log of typed entries |
| Content | none by default; references | all of it |
| Who may read it | broadly: SREs, template owners, dashboards | narrowly, audited |
| Standard | OpenTelemetry (GenAI conventions, Development) | none; ATIF is the only interchange candidate |
| Used for | latency, cost, errors, loops, alerts, correlation with other services | replay, quality judgement, clustering, evaluation datasets, training |

They are **joined by ids**: the trace's model-call span carries a
reference to the transcript entries it consumed and produced
(`gen_ai.input.messages_ref` in the conventions, `message.uuid` in
Claude Code, `item.id` in Codex). A third record, **scores**, arrives
later from judges, checks, people or real-world outcomes, and attaches
to either.

## 2. Why the split matters

1. **Content is the expensive and dangerous part.** Prompts and tool
   results are large and sensitive. The OTel conventions say don't
   capture them by default, and for production "store content
   externally and record references … enables separate access
   controls" (`telemetry/standards.md` §2d). Half the SDKs capture
   content by default anyway (`telemetry/catalogue.md` §5), which
   turns every trace backend into a store of customer data.
2. **The cheap analyses don't need content.** Cost, latency, error
   rates, loop detection and alerting run on the trace alone. Only
   quality judgement and clustering need the transcript
   (`telemetry/analysis-and-alerts.md` §1).
3. **The trace vocabulary is unstable; the transcript is yours.** The
   GenAI conventions have twenty breaking changes pending
   (`telemetry/standards.md` §2e). A transcript in your own schema,
   exported to ATIF or OTel at the edge, does not move when they do.
4. **Runs outlive traces.** A run that waits days on a person, resumes,
   or spawns continuations does not fit one trace window. The
   transcript and the run record carry the lineage; traces link to each
   other (`agent-design/proposals-telemetry-2026-11.md` §3).

## 3. Design rules drawn from the sources

1. **Propagate W3C context through calls you already make**: HTTP
   headers, MCP `params._meta` (SEP-414), `TRACEPARENT` in subprocess
   environments. No new API.
2. **Model calls, tool calls, MCP calls and agent runs are spans with
   OTel GenAI names; everything specific to your platform is your own
   namespace.** Pin the conventions' commit.
3. **Content off on export; references into the transcript instead.**
   Redaction and delivery in one exporter that drops the batch on
   failure.
4. **Metrics never carry run, session or user ids**; user-named things
   (custom MCP servers) are labelled generically.
5. **Attribute cost to its cause** (the tool result, the reveal, the
   sub-agent), not only to the model.
6. **Record the human**: time waiting on approval is a span; who
   decided is an attribute.
7. **Scores are their own signal**, keyed to span, run or session, and
   may arrive days later.
8. **Show a run transcript-first**, with spans folded in; the waterfall
   is for latency work.
9. **Detect loops in the run; alert across runs by template version.**

## 4. Where each source sits

| Source | Trace | Transcript | Join | Scores |
|---|---|---|---|---|
| Claude Code | product events + beta spans; content opt-in, `body_ref` to files | JSONL | `message.uuid`, `tool_use_id` | none |
| Codex | product events, metrics, spans; content opt-in | JSONL rollouts | `conversation.id`, `turn.id`, `item.id` | none |
| Gemini CLI | events with some GenAI attrs, spans; prompts on by default | session JSON | session id | none |
| Pi | typed spans, sizes never content | JSONL tree | entry ids | none |
| OpenAI Agents SDK | own spans; content on by default | in the SDK's session store | `group_id` | via platform |
| ADK | GenAI spans + `gcp.vertex.agent.*`; content off | session events | session, invocation, event ids | eval module |
| Langfuse / Phoenix | ingest spans with or without content | the spans' content | trace and session ids | yes, separate table |
| **Keel today** | `RunEvent` stream, no bodies | transcript, `runs:transcript` | run id, `seq` | §3e only |
