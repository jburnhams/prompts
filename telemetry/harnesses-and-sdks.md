# How harnesses and agent SDKs emit telemetry

Evidence tags as in [`standards.md`](./standards.md). Commits in
[`../sources.md`](../sources.md), "Agent telemetry (read 2026-11-14)".

## 1. Coding harnesses

### Claude Code **[docs: code.claude.com/docs/en/monitoring-usage]**

Not open source; read from the monitoring docs (first 100k of 176k
characters). The richest harness telemetry found, and almost none of it
uses `gen_ai.*` names.

- **Switches**: `CLAUDE_CODE_ENABLE_TELEMETRY=1`, then standard
  `OTEL_*_EXPORTER` and `OTEL_EXPORTER_OTLP_*`. Admins can lock the
  destination in managed settings; a repository's own settings cannot
  enable telemetry or pick where it goes.
- **Metrics** (`claude_code.*`): session count by start type, lines of
  code, PRs, commits, `cost.usage` (USD) and `token.usage` (by `type`
  input/output/cacheRead/cacheCreation), edit-tool decisions, active
  time. Cost and token metrics are **attributed** by model, query source,
  effort, `agent.name`, `skill.name`, `plugin.name`, `mcp_server.name`,
  `mcp_tool.name`: which subagent, skill or MCP tool's result the tokens
  were spent on.
- **Log events**: `user_prompt`, `assistant_response`, `api_request`
  (cost, duration, tokens including 5-minute and 1-hour cache writes,
  request ids), `api_error`, `api_refusal`, optional raw request and
  response bodies, `tool_decision` (accept/reject and **who** decided:
  config, hook, user permanently or temporarily, classifier verdict,
  permission mode), `tool_result` (success, duration, error type,
  input and result sizes), plus MCP connection, plugin, subagent
  completion and safety events.
- **Traces (beta)**: `claude_code.interaction` (root, one per user
  prompt) → `llm_request`, `hook`, `tool` → `tool.blocked_on_user`,
  `tool.execution`, with subagents nested under the Agent tool. **Time
  waiting on the human is its own span.**
- **Content**: redacted by default, with separate opt-ins for prompts,
  responses, tool details (commands, paths, MCP names), tool output and
  raw API bodies. Raw bodies can go to `file:<dir>` and the event then
  carries `body_ref`, the external-reference pattern. Content is
  truncated at 60 KB. User-configured MCP server names become `"custom"`
  unless tool details are on, so a metric label can't leak an internal
  hostname.
- **Propagation**: `TRACEPARENT` into Bash and PowerShell children;
  `traceparent` on Anthropic API requests (not to third-party providers
  unless forced) with the response's `traceresponse` recorded as a
  link; `traceparent` on outbound HTTP MCP requests; inbound
  `TRACEPARENT` honoured for SDK and `-p` sessions only.
- **Join keys**: `session.id`, `prompt.id` (all events of one prompt),
  `event.sequence`, `request_id`, `client_request_id`, `tool_use_id`,
  `message.uuid` (the transcript entry), `workflow.run_id`, `agent_id`,
  `parent_agent_id`.
- **Cardinality controls**: env vars to include or drop session id,
  account, version, entrypoint and repository on metrics.

### Codex **[source, 641e2e362c, `codex-rs/otel`]**

- One crate wires OTLP logs, traces and metrics; default exporter
  `none`. Metrics default to **delta temporality**; there is a built-in
  Statsig exporter for OpenAI's own use.
- `SessionTelemetry` stamps every event with conversation id, model,
  account, auth mode, originator, terminal and session source. User
  prompts are logged as `[REDACTED]` unless `log_user_prompts`.
- About 100 distinct `codex.*` metric and event names: API request and SSE timing
  split into **engine TTFT, service TTFT and client overhead**,
  `turn_cost`, `turn_ttft`, tool calls and durations, `tool_decision`,
  `sandbox_outcome`, hooks, multi-agent spawn failures, Guardian
  (approval reviewer) review duration and truncation, goal lifecycle
  (`goal.created/completed/blocked/budget_limited/usage_limited`),
  skill enablement and truncation, reasoning replay.
- Opt-in log-only events with content: `codex.agent_response` (final
  answers, 64 KB cap, `response_truncated`) and
  `codex.guardian_assessment` (risk level, rationale, outcome). Both
  are excluded from traces, local logs and feedback uploads.
  **Lineage** on these events: `parent.conversation.id`,
  `parent.turn.id`, `root.turn.id`, `initiating.agent.path`.
- Only token-usage attributes use `gen_ai.*`.
- Configurable `[otel.span_attributes]` and `[otel.tracestate]` members
  stamped on every span and propagated.
- MCP: `traceparent` injected into `params._meta` and HTTP headers
  (`rmcp-client/src/trace_context.rs`).

### Gemini CLI **[source, 4ed06ed0dd; docs/cli/telemetry.md]**

- OTLP or a local `outfile`; first-class Google Cloud export with
  prebuilt dashboards. `logPrompts` **defaults to true**; detailed trace
  attributes are off unless `telemetry.traces` is set.
- About 100 distinct `gemini_cli.*` names: API request/response/error with a
  latency breakdown, tool calls, edit strategy and edit correction,
  model routing, chat compression, invalid chunks and content retries,
  flash fallback, hook calls, file operations, memory and event-loop
  monitors, plus a `gen_ai.client.inference.operation.details` event in
  OTel shape.
- Spans carry `gen_ai.*` (operation `tool_call`, `llm_call`,
  `user_prompt`, `agent_call`, `schedule_tool_calls`; agent name
  `gemini-cli`; conversation id = CLI session). Metrics include the
  now-deprecated `gen_ai.client.token.usage`.
- **`loop_detected`** event with `loop_type`, count, and optionally the
  model that confirmed it, its analysis and confidence: an in-harness
  loop detector whose result is telemetry.

### OpenCode **[source, 83960f8a56]**

The Effect-based rewrite exports OTLP logs and traces when
`OTEL_EXPORTER_OTLP_ENDPOINT` is set (`packages/util/src/observability.ts`),
with `gen_ai.*` on the step span (`LLM.stream`) and tool spans,
including the pre-rename `gen_ai.usage.cache_creation.input_tokens`. The
old `experimental.openTelemetry` config (Vercel AI SDK telemetry) is now
listed as unsupported. It also ships `@opencode/http-recorder`, which
records real provider traffic into JSON cassettes for replay in tests.

### Pi **[source, 827383a152]**

Its own typed schema library (`@earendil-works/pi-telemetry`):
`pi.ai.request` and `pi.ai.poll` spans with start and end attribute
sets, `pi.ai.block` events per content block that **record kind, index,
character count and tool name, never content**, and duration and
first-chunk histograms. Errors keep at most 500 characters; aborted
stays `ok`. The session file is a JSONL tree with typed entries and an
HTML export (`core/export-html`) as the session viewer.

### Goose **[source, 2365bc5e89]**

Both a native Langfuse ingestion layer (`tracing/langfuse_layer.rs`,
batching straight to Langfuse's HTTP API) and an OTLP exporter
(`otel/otlp.rs`); docs cover Langfuse, MLflow and Laminar.

### Claude Agent SDK **[source, 32e96114c1]**

The SDK spawns the CLI, so its telemetry *is* Claude Code's. What the
SDK adds is propagation: if `opentelemetry` is installed and a span is
active, it injects `TRACEPARENT` and `TRACESTATE` into the child's
environment (explicit options win), so the CLI's `interaction` span
parents under the caller's span. OpenInference has a separate
instrumentation package for it.

## 2. Agent SDKs and frameworks

| SDK | Own model | OTel GenAI | Content default | Notes |
|---|---|---|---|---|
| **OpenAI Agents** (64fbde5d02) **[source]** | **Own**: traces (`workflow_name`, `trace_id` as `trace_<32>`, `group_id` for a conversation) of typed spans: agent, task, turn, function, generation, response, handoff, guardrail, custom, transcription, speech, MCP list-tools | no; exporters translate | **on** (`trace_include_sensitive_data=True`) | Default exporter sends to OpenAI's dashboard. Processors observe; 31 third-party processors listed. Docs warn that a redaction processor added beside the exporter does not stop the exporter, so **redact and deliver inside one exporter and drop the batch if redaction fails**. |
| **Pydantic AI** (fb64b4100c) **[source]** | OTel spans via Logfire or plain OTel | yes, versioned format 2-6, default 5, pinned to semconv 1.37.0 | **on** (`include_content=True`) | Prompt-cache health warnings (the source of Keel's `cache_collapse`). Logfire is an OTel backend with SQL over spans. |
| **LangChain / LangGraph / Deep Agents** (langsmith-sdk 290f06a628) **[source]** | **Own**: run trees (`run_type`, `dotted_order`) sent to LangSmith | LangSmith can export runs as OTel and ingest OTel | on | Deep Agents and LangGraph get tracing by setting the LangSmith key. |
| **Microsoft Agent Framework** (92838b6049) **[source]** | OTel | yes, native | **off** (`enable_sensitive_data`, env `ENABLE_SENSITIVE_DATA`) | The conventions' own examples name MAF `Agent` and `Workflow`. |
| **Google ADK** Python (12aab4aaaa), Java (1b11290840) **[source]** | OTel | yes, plus `gcp.vertex.agent.*` (session, invocation, event ids, request and response bodies) | **off** (`OTEL_INSTRUMENTATION_GENAI_CAPTURE_MESSAGE_CONTENT`; Java `ADK_CAPTURE_MESSAGE_CONTENT_IN_SPANS`) | Spans `invoke_agent`, `call_llm`, `execute_tool`. Python has a **SQLite span exporter for local development** and a web UI trace view; stable and experimental semconv modules side by side. |
| **Vercel AI SDK** (0e8e0543ae) **[source]** | Publishes typed events on a Node diagnostics channel `ai:telemetry` (`generateText`, `streamText`, `step`, `languageModelCall`, `executeTool`, …); integrations subscribe | the older `ai.*` span attributes are what Langfuse still parses | per integration | Decouples emitting from exporting completely. |
| **Mastra** (94fd1f0a5f) **[source]** | Own tracing bus with exporters for 13 backends (Arize, Arthur, Braintrust, Datadog, DeepEval, Laminar, Langfuse, LangSmith, PostHog, Sentry, OTel, an OTel bridge, its own store) | via exporter | configurable | A written ClickHouse design (§ platforms). Tests pin how a **suspended and resumed** agent stays in the original trace: resumes are siblings under the initial agent span, and lineage is saved with the snapshot. |
| **CrewAI** (d7dfa0ef5a) **[source, partial]** | Anonymous usage telemetry to `telemetry.crewai.com:4319` by default; content only with `share_crew` | via OpenInference / OpenLLMetry | off to vendor | Vendor-bound telemetry on by default is the outlier. |
| **LlamaIndex** **[docs, not read]** | Own instrumentation dispatcher (events and spans) | via OpenInference / OpenLLMetry | | |
| **Strands Agents** **[secondary, Datadog docs]** | OTel | yes, needs `OTEL_SEMCONV_STABILITY_OPT_IN=gen_ai_latest_experimental` for current shape | | |

## 3. Patterns across both groups

**[inference] from the above.**

1. **Three emission architectures.** (a) Direct OTel spans with GenAI
   attributes (ADK, MAF, Pydantic AI, OpenCode, Gemini CLI spans).
   (b) Own trace model with exporters/processors (OpenAI Agents,
   LangSmith, Mastra, Vercel's channel, Pi's typed schema), translated
   to OTel at the edge. (c) Product telemetry as OTel **log events and
   metrics** named for the product (Claude Code, Codex, Gemini CLI's
   events), with traces added later and marked beta.
2. **Harnesses measure the product; SDKs measure the calls.** The
   harness events are about decisions and outcomes (who approved a tool,
   did the sandbox block it, was the goal blocked, was a loop detected,
   which skill was loaded). The SDK spans are about calls and tokens.
   Neither set covers the other, and the conventions cover only the
   second.
3. **Content defaults split almost evenly.** Off: Claude Code, Codex,
   MAF, ADK, Pi (never). On: OpenAI Agents, Pydantic AI, OpenLLMetry,
   Gemini CLI prompts, LangSmith. The standard says off.
4. **The human is in the trace.** Claude Code's `tool.blocked_on_user`
   span and `tool_decision.source`, Codex's `tool_decision` and Guardian
   events: approval latency and who approved are first-class.
5. **Lineage beyond parent/child.** Codex carries parent conversation,
   parent turn and root turn; Claude Code carries agent and parent
   agent; Mastra keeps resumes in the original trace. Plain span
   parentage is not enough once runs suspend, resume and spawn.
6. **Join keys to the transcript.** Claude Code's `message.uuid` and
   Codex's `item.id` tie a telemetry event to a transcript entry, so the
   trace can stay content-free and still lead to the content.
7. **MCP propagation is real but uneven.** Codex and OpenLLMetry write
   `_meta`; Claude Code covers HTTP only per its docs.
