# Agent telemetry: how harnesses, SDKs and platforms record, store, show and analyse agent runs

- **Type**: a survey of standards, harness and SDK implementations,
  observability platforms and storage designs, read for what they mean
  for Keel, Forge and Lens. No system prompts are stored here.
- **Prompted by**: Jonathan, 2026-11-14: "a new deep dive into
  telemetry (OTLP?) to see how different harnesses and SDKs and agentic
  platforms handle this: best ways to show the data of an agent session,
  pipelines, MCP calls, LLM calls etc. How to capture and store it, then
  analyse it. Alerts. … Is it possible to standardise it into existing
  calls? Has some commonalities with X-Ray / correlation ids / tracing
  but is also quite a distinct domain … find out how many different ways
  there are, what most common are, best approaches, then we can discuss
  how Keel / Forge / Lens should do it."
- **Read**: 2026-11-14. As source: the OTel GenAI conventions
  (`semantic-conventions-genai` at `e6658f1`), the MCP spec and SEP-414
  (`0175d20`), OpenInference (`f35f8be`), OpenLLMetry (`e3d651a`),
  Codex, Gemini CLI, OpenCode, Pi, Goose, the Claude Agent SDK, the
  OpenAI Agents SDK, Pydantic AI, LangSmith's SDK, Microsoft Agent
  Framework, ADK (Python and Java), Vercel AI SDK, Mastra, CrewAI,
  Langfuse, Phoenix and Harbor's ATIF RFC. As documentation: Claude Code's
  monitoring page. As secondary sources: Datadog, Honeycomb, Grafana,
  Braintrust, Helicone, AgentCore and Docent. Every SHA is in
  [`../sources.md`](../sources.md), "Agent telemetry (read 2026-11-14)",
  and every claim carries a tag: **[source]**, **[docs]**,
  **[secondary]** or **[inference]**.

## The files

| File | What |
|---|---|
| [`standards.md`](./standards.md) | The four layers (correlation, transport, shape, meaning). OTel GenAI semantic conventions in detail: spans, agent and workflow operations, attributes, metrics, the evaluation event, the three content patterns, and how fast it is changing. MCP trace context in `_meta` (SEP-414). OpenInference, OpenLLMetry, the other dialects, and the transcript formats (ATIF, harness session logs, run trees). |
| [`harnesses-and-sdks.md`](./harnesses-and-sdks.md) | Claude Code, Codex, Gemini CLI, OpenCode, Pi, Goose and the Claude Agent SDK; ten agent SDKs in a table; seven patterns across them. |
| [`platforms-and-storage.md`](./platforms-and-storage.md) | Four kinds of platform; how Langfuse, Mastra, Phoenix and Braintrust store traces, and what they agree on; the session views that recur and what each answers. |
| [`analysis-and-alerts.md`](./analysis-and-alerts.md) | What gets analysed and from which signal; evaluations from traces; loop detection in and after the run; the alerts that matter, by who acts on them. |
| [`platform-comparison.md`](./platform-comparison.md) | Side by side: Langfuse, Phoenix, AWS X-Ray/CloudWatch, Datadog, Grafana, Splunk, Honeycomb, LangSmith on ingest, agent view, evals, content, self-hosting and fit for Keel; what the comparison means for Keel. |
| [`catalogue.md`](./catalogue.md) | Counts: how many ways there are on each axis, which are most common, and the best approaches seen. |

The cross-source concept is in
[`../agent-telemetry.md`](../agent-telemetry.md). Proposals for Keel,
Forge and Lens, **none adopted**, are in
[`../agent-design/proposals-telemetry-2026-11.md`](../agent-design/proposals-telemetry-2026-11.md).

## Answers to the questions asked

**Is it OTLP?** Yes, for transport. Every system read here that exports
telemetry can speak OTLP, usually beside one other route (a vendor API,
local files, or a proxy). OTLP and W3C trace context are settled; what
is not settled is the vocabulary on top (`standards.md` §1).

**How many different ways are there?** On the axis that matters, the
meaning of the attributes, about **fifteen** dialects are in use;
Langfuse's ingester special-cases fifteen families for content alone.
**Two are general standards**: OpenTelemetry's GenAI semantic
conventions and Arize's OpenInference. The rest are frameworks that
predate them or products that name events after themselves. On other
axes: five transports, six signal shapes, four content policies, four
storage designs, about nine kinds of session view (`catalogue.md`).

**What is most common?** OTLP; W3C `traceparent`; a span tree shaped
`invoke_agent → chat {model} → execute_tool {tool}`; a session or
conversation id as an attribute; token usage on the model span; content
off by default or kept outside the trace; a backend that adds scores
afterwards. The harnesses add product events (decisions, approvals,
loops, goals) as OTel log events and metrics.

**What are the best approaches?** In short (`catalogue.md` §9):
OTel's "store content externally and record a reference" pattern, which
Keel already follows; trace context in MCP `_meta`; attributing token
cost to the tool result that caused it (Claude Code); a span for time
spent waiting on a person (Claude Code); TTFT split into engine, service
and client (Codex); lineage ids for parent turn and root turn (Codex);
a wide events table with a truncated list view (Langfuse); five
append-only signals including scores and feedback (Mastra); recording
sizes and kinds instead of content (Pi); and a redaction step that fails
closed in the same exporter that delivers (OpenAI Agents SDK).

**Can it be standardised into existing calls?** For correlation, yes,
with no new API anywhere: `traceparent` goes in the HTTP headers Keel
already sends, in the `params._meta` of every MCP request (now in the
MCP spec), and in the environment of every sandbox command. The OTel
GenAI conventions then describe the existing calls (model call, tool
call, MCP call, agent run) as spans. What is not standardised, and has
to stay Keel's own: runs that suspend for days and resume, pipeline
stages, gates, refusal codes, endings, deliveries, cost (OTel has no
cost attribute), most of evaluation, and the transcript format (ATIF is
the only candidate).

**How does it relate to X-Ray and correlation ids?** It is the same
first three layers: W3C trace context, OTLP, spans. X-Ray accepts both
through the AWS Distro for OpenTelemetry, and Bedrock AgentCore exports
OTel GenAI spans to CloudWatch with the session id in baggage. A Keel
run can appear inside an X-Ray trace with no special work. What makes
agent telemetry a distinct domain is the fourth layer plus two things
APM never had: **content** (large and sensitive, so it needs its own
store and permission) and **quality** (scores that arrive later, from
elsewhere, and are keyed to a session as often as to a span).

**How should a session be shown?** Transcript-first, with spans folded
in: each turn with tokens, cost and latency, each tool call with status
and a collapsed result, sub-agents nested, waits on a person visible.
The waterfall is a secondary view (`platforms-and-storage.md` §3).

**Store and analyse?** At scale everyone converges on one wide row per
span in ClickHouse with maps for usage and cost, content separate or
truncated, scores in their own table. Cost, latency, errors and loops
need no content; quality and clustering need the transcript
(`analysis-and-alerts.md` §1).

**Alerts?** Always in the backend, on metrics and scores; in-run
detection (loops, budgets) belongs in the harness. The useful
granularity is the template version (`analysis-and-alerts.md` §4).

## What was read, and what was not

- **Read as code**: everything listed as source above. Pins are exact.
- **Docs only**: Claude Code (closed source); the first 100,000 of the
  page's 176,000 characters were read, so events described later on the
  page may be missing.
- **Secondary only**: Datadog, Honeycomb, Grafana/OpenLIT, Braintrust's
  Brainstore, Helicone's status, AgentCore, Docent, ATIF adoption beyond
  Harbor, and the date the GenAI conventions moved repositories. Vendor
  performance claims are not repeated as fact.
- **Not read**: LlamaIndex's instrumentation module, W&B Weave, MLflow
  Tracing, Opik, Laminar, AgentOps, Logfire's backend, LangSmith's
  backend, Dynatrace, New Relic, Sentry's agent monitoring. They are
  named where a source names them.
