# Telemetry standards for agents: what exists and what each one covers

Evidence tags: **[source]** read in the repository at the pinned commit;
**[docs]** the project's own documentation; **[secondary]** someone
else's write-up; **[inference]** our reading, not stated anywhere.
Commits are in [`../sources.md`](../sources.md), "Agent telemetry (read
2026-11-14)".

## 1. The layering

Four layers decide whether two systems can share agent telemetry. They
are independent, and most confusion in this area comes from treating
them as one.

| Layer | The question | The standard answers |
|---|---|---|
| **Correlation** | How does a span in process B know it belongs to the request in process A? | W3C Trace Context (`traceparent`, `tracestate`) and W3C Baggage. Carried in HTTP headers, in MCP `params._meta`, in ACP, and in a `TRACEPARENT` environment variable for subprocesses. |
| **Transport** | How do the bytes get to a backend? | OTLP (gRPC or HTTP, protobuf or JSON). Everyone below supports it except where noted. |
| **Shape** | What is a span, a metric, a log event, and how do they nest? | OpenTelemetry's data model. Spans carry attributes, span events and links; logs carry a body and attributes; metrics are counters and histograms. |
| **Meaning** | Which attribute names say "this span is a model call, these are its tokens, this is the tool"? | **This is where there is no single answer.** OTel GenAI semantic conventions, OpenInference, OpenLLMetry's legacy names, and a dozen vendor dialects. |

**The first three layers are settled.** Every harness, SDK and platform
read here that exports at all can speak OTLP with W3C context. The
fourth layer is converging on OTel GenAI but is not there yet (§6).

X-Ray, correlation ids and APM tracing live in the first three layers.
X-Ray accepts W3C trace ids and OTLP through the AWS Distro for
OpenTelemetry, and Bedrock AgentCore's observability is OTel exported to
CloudWatch with a `session.id` in baggage **[docs, AWS]**. What makes
agent telemetry a distinct domain is entirely the fourth layer plus two
things APM never needed: **content** (prompts, completions, tool
arguments and results, which are large and sensitive) and **quality**
(scores, evaluations, feedback attached after the fact).

## 2. OpenTelemetry GenAI semantic conventions

**Where it lives now.** On 2026-06-12 (semconv v1.42.0) the GenAI, MCP
and OpenAI conventions were deprecated in the main
`open-telemetry/semantic-conventions` repo and moved to
`open-telemetry/semantic-conventions-genai` **[secondary, consistent
with the repos]**. The new repo has no tagged release; its schema URL is
literally "TODO" in the README **[source, e6658f1]**. Everything in it is
**Development** stability. Our main-repo clone still carries the old
`docs/gen-ai/` pages **[source, 45b690d]**.

### 2a. Spans

GenAI spans "represent logical operations as observed by the caller",
including retries **[source]**. The operations defined at e6658f1:

| Operation (`gen_ai.operation.name`) | Span | Kind | Notes |
|---|---|---|---|
| `chat`, `generate_content`, `text_completion` | inference client span, name `{operation} {model}` | CLIENT | the model call. `fetch_response` (re-reading a stored response) and `realtime_inference` are new. |
| `embeddings` | embeddings client span | CLIENT | |
| `retrieval` | `gen_ai.retrieval` | INTERNAL | the older `gen_ai.retrieval.client` is deprecated; a call to a search service follows DB conventions. |
| `execute_tool` | `execute_tool {gen_ai.tool.name}` | INTERNAL | specialised forms: `transfer` (handoff to another agent), `load_skill`, `read_skill_resource`, `command`. **Agent Skills got their own attributes** (`gen_ai.skill.*`). |
| `create_agent` | `create_agent {name}` | CLIENT | remote agent services. |
| `invoke_agent` | `gen_ai.invoke_agent.client` (remote) or `.internal` (in-process) | CLIENT / INTERNAL | the agent run. |
| `invoke_workflow` | same internal span, different operation name | INTERNAL | "when the application defines the control flow", e.g. LangGraph `StateGraph`, MS AF `Workflow`, CrewAI `Crew`. The separate workflow span was **merged** into `invoke_agent.internal` on this branch. |
| `invoke_{entrypoint}` | same | INTERNAL | e.g. `invoke_runner` for ADK `Runner.run`. |
| `plan` | `plan` span | INTERNAL | planning/task decomposition. |
| memory ops | memory span | | store create/delete, record create/update/search/delete. |
| MCP methods | `{mcp.method.name} {target}` | CLIENT / SERVER | see §3. A `tools/call` span *is* the `execute_tool` span; there is not a second one. |
| A2A | client/server spans | | protocol, task, conversation, Agent Card attributes. |

Sampling-relevant attributes (`gen_ai.agent.name`, operation, provider,
model) "SHOULD be provided at span creation time" **[source]**, so a
head sampler can keep all of one agent's traces.

The worked tree from the MCP doc **[source]**:

```
invoke_agent weather-forecast-agent (INTERNAL)
  ├─ chat {model} (CLIENT)
  ├─ tools/call get-weather (CLIENT)          ← MCP client = execute_tool
  │    └─ tools/call get-weather (SERVER)     ← in the MCP server process
  └─ chat {model} (CLIENT)
```

### 2b. The attributes that matter for agents

- **Identity**: `gen_ai.agent.name` (MUST be low cardinality; "NOT
  RECOMMENDED to use … framework defaults, or type names such as
  StateGraph"), `gen_ai.agent.id` (provider-assigned and stable only),
  `gen_ai.agent.version`.
- **Session**: `gen_ai.conversation.id`, the only attribute the
  conventions allow to be propagated in-process to child spans. It
  "should only be populated from an available conversation identifier",
  never a generated UUID, trace id or hash **[source, changelog]**.
- **Usage**: `gen_ai.usage.input_tokens` / `output_tokens` (totals over
  modalities, billed counts where billed and consumed differ),
  `cache_read.input_tokens`, `cache_write.input_tokens` (renamed from
  `cache_creation`), `reasoning.output_tokens`, per-modality variants.
  **Cache breakdowns were removed from the `invoke_agent` span** because
  they aggregate across models and mislead; consumers aggregate from the
  inference spans **[source, changelog]**. That is the same reasoning as
  Keel's per-model `Usage.by_model`.
- **Request**: model, temperature, `gen_ai.request.reasoning.level`,
  `gen_ai.request.stream`, `gen_ai.request.previous_response.id`.
- **Response**: model, id, `finish_reasons` (positional),
  `gen_ai.conversation.compacted` and a `CompactionPart` message type
  **[source, changelog]**. Compaction is now a first-class telemetry fact.
- **Prompt management**: `gen_ai.prompt.name`, `gen_ai.prompt.version`,
  `gen_ai.prompt.variable.*` (content-gated).
- **Content** (all opt-in, §2d): `gen_ai.system_instructions`,
  `gen_ai.input.messages`, `gen_ai.output.messages`,
  `gen_ai.tool.call.arguments`, `gen_ai.tool.call.result`,
  `gen_ai.tool.definitions`, retrieval documents, memory records. Each
  has a JSON schema and must be recorded as structured `AnyValue`, not
  a JSON string (the string fallback was removed).

### 2c. Metrics and events

Metrics at e6658f1 **[source, model/*.yaml]**: inference duration,
time-to-first-chunk and time-per-output-chunk; per-direction token
histograms; five `gen_ai.client.inference.usage.*` counters (input,
output, cache_read, cache_write, reasoning) that record only known,
positive values; `gen_ai.invoke_agent.duration` (buckets up to 24
hours); **`gen_ai.invoke_agent.inference_calls` and
`gen_ai.invoke_agent.tool_calls`** (how many model and tool calls one
agent invocation made); `gen_ai.execute_tool.duration`;
`gen_ai.retrieval.duration`; four MCP metrics (client and server
operation duration, client and server session duration).

Events: `gen_ai.client.inference.operation.details` (the content
carrier when content goes to logs, DEBUG severity, now Recommended),
per-operation exception events, realtime session start/end, and
**`gen_ai.evaluation.result`** with `gen_ai.evaluation.name`,
`score.value`, `score.label`, `explanation`, parented to the evaluated
span or keyed by `gen_ai.response.id` **[source]**. That is the whole
of the standard's support for quality; there is nothing for sessions,
human feedback or datasets.

### 2d. Content: off by default, three patterns

The conventions' content section **[source, gen-ai-spans.md]** is the
most important text in this area for us:

1. **Default: don't record** instructions, inputs or outputs.
2. **Record on the spans** — for pre-production or where the
   telemetry store is already compliant.
3. **Store externally and record references** — "recommended in
   production environments where telemetry volume is a concern or
   sensitive data needs to be handled securely. Using external storage
   enables separate access controls." The reference attributes are
   `gen_ai.system_instructions_ref`, `gen_ai.input.messages_ref`,
   `gen_ai.output.messages_ref`, `gen_ai.tool.definitions_ref`; the URI
   scheme, layout and retention are deliberately unspecified, and
   content-derived ids for deduplication (the same system prompt on
   every call) are allowed.

The single switch is `OTEL_INSTRUMENTATION_GENAI_CAPTURE_CONTENT` with
`NO_CONTENT` (default), `SPAN_ONLY`, `EVENT_ONLY`, `SPAN_AND_EVENT`.
Upload hooks have their own variables (`…_CONTENT_HOOK`,
`…_UPLOAD_BASE_PATH` with `s3://`, `gs://`, local paths, `…_UPLOAD_FORMAT`
`json`/`jsonl`). The hook runs "regardless of the span sampling
decision", so content can be kept for every call while spans are
sampled. **Keel's events-without-bodies plus a separately permissioned
transcript is pattern 3 already** **[inference]**.

### 2e. How much it is still moving

The pending changelog on the new repo has **90 fragments**, about
twenty of them marked breaking **[source, changelog.d/]**. In the last
cycle alone: the `gen_ai.client.token.usage` histogram and
`gen_ai.token.type` were replaced; `cache_creation` was renamed
`cache_write`; the workflow span was merged into the agent span;
retrieval moved; `gen_ai.provider.name` value `mistral_ai` became
`mistral`. Downstream evidence of the churn:

- Pydantic AI ships **six instrumentation "format versions"** (2-6,
  default 5) to track it, pinned to semconv 1.37.0 **[source]**.
- Gemini CLI still emits the deprecated `gen_ai.client.token.usage` and
  `gen_ai.client.operation.duration` **[docs]**.
- OpenCode's new runtime writes `gen_ai.usage.cache_creation.input_tokens`,
  the pre-rename name **[source, step.ts]**.
- Datadog ingests "1.37+", Honeycomb built on 1.40 **[secondary]**.
- ADK has an env var `OTEL_SEMCONV_STABILITY_OPT_IN=gen_ai_latest_experimental`
  to switch between old and new shapes **[secondary, Datadog docs]**;
  ADK Python has `_stable_semconv.py` and `_experimental_semconv.py`
  side by side **[source]**.

**Practical consequence: pin a commit of the conventions, record it as
the schema URL, and translate at the collector rather than in the
agent** **[inference]**.

## 3. MCP: trace context in `_meta` (SEP-414)

SEP-414 is **Final** and is in the `2026-07-28` specification
**[source, 0175d20]**: the keys `traceparent`, `tracestate` and
`baggage` in `params._meta` are reserved for OpenTelemetry propagation,
as the one exception to `_meta`'s DNS-prefix rule, with W3C value
formats. The OTel MCP conventions add the rest **[source]**:

- The client injects with the configured propagators on every request
  **and notification**; the server extracts and uses it as the **parent**
  of its server span, and **links** (does not parent) any ambient
  transport context.
- MCP and transport contexts are independent: one MCP request can span
  several HTTP requests (retries), and one Streamable HTTP response can
  carry several MCP messages, so HTTP `traceparent` alone is not enough.
- Span attributes: `mcp.method.name`, `gen_ai.tool.name`,
  `jsonrpc.request.id`, `mcp.resource.uri`, `gen_ai.prompt.name`,
  `mcp.protocol.version`, `mcp.session.id` (where the transport has one),
  `network.transport` (`pipe` for stdio), plus opt-in tool arguments and
  result. MCP server telemetry does **not** count client-caused errors
  as server failures.
- SEP-2028 (pending) forwards `_meta` values to HTTP headers.

Implementations named by the SEP: C# and Python MCP SDKs, OpenInference
(Python, TS), Envoy AI Gateway, Logfire, ToolHive. Read here as code:
**Codex** injects `traceparent` into `_meta` on every request and also
sets HTTP headers (`rmcp-client/src/trace_context.rs`) **[source]**;
**OpenLLMetry**'s MCP instrumentation does the same **[source]**.
**Claude Code** propagates `traceparent` on outbound *HTTP* MCP requests
**[docs]**; we found no statement that it writes `_meta`, so stdio MCP
servers would not join the trace **[inference]**.

ACP has the equivalent change (agent-client-protocol#297) **[source,
SEP text]**. A2A has its own span conventions in the GenAI repo.

## 4. OpenInference (Arize)

The second-largest convention set, older than OTel GenAI and still
independently maintained **[source, f35f8be]**.

- A required `openinference.span.kind` with eleven values: `LLM`,
  `EMBEDDING`, `CHAIN`, `RETRIEVER`, `RERANKER`, `TOOL`, `AGENT`,
  `GUARDRAIL`, `EVALUATOR`, `PROMPT`, `DECISION`. Kind is a single
  enum, where OTel uses operation names.
- Flattened attributes: `llm.input_messages.0.message.content`,
  `input.value` / `output.value` on every span, `llm.token_count.*`
  with cache and reasoning details.
- **Things OTel GenAI lacks**: `llm.cost.*` (prompt, completion, total,
  cache read/write, reasoning), `session.id`, `user.id`, `tag.tags`,
  `metadata`, `graph.node.id` / `parent_id` for agent graphs, and
  annotations and evaluations at span, trace and **session** scope.
- Content controls are fine-grained env vars (`OPENINFERENCE_HIDE_INPUTS`,
  `…_HIDE_OUTPUT_MESSAGES`, `…_HIDE_INPUT_IMAGES`, embeddings) and a
  `BlobUploader` that uploads large base64 media and records the URI.
- **38 Python and 11 JS instrumentation packages**, including a Claude
  Agent SDK one, and **converters**: `openinference-genai` (JS) turns
  OTel GenAI spans into OpenInference ("best effort … a subset",
  attributes "as of October 2025"); Python packages convert OpenLLMetry
  and OpenLIT output.

## 5. OpenLLMetry (Traceloop)

32 instrumentation packages plus `traceloop-sdk` **[source, e3d651a]**.
It moved its model attributes to upstream `gen_ai.*` in v0.5.0 but keeps
its own `traceloop.span.kind`, `traceloop.workflow.name`,
`traceloop.entity.*` (input/output), `traceloop.association.properties`,
prompt-registry attributes and `traceloop.correlation.id`. **Content is
captured by default**: `TRACELOOP_TRACE_CONTENT` defaults to `"true"`.
Its MCP instrumentation writes `traceparent` into `_meta`.

OpenLIT (the SDK behind Grafana's AI Observability) is a third
OTel-native auto-instrumentation family **[docs, secondary]**, not read
as code.

## 6. The dialects in practice

The clearest measure of how many dialects exist is what an ingester has
to accept. Langfuse's OTLP ingestion processor **[source, 48a31810e1]**
has, for input and output content alone, special cases for **fifteen
attribute families**: Langfuse's own, Vercel AI SDK `ai.*`, Google
Vertex/ADK `gcp.vertex.agent.*`, Logfire, LiveKit `lk.*` and `lk.pii.*`,
MLflow, Traceloop, OpenInference (`input.value`), Pydantic AI
(`pydantic_ai.all_messages`, `final_result`), Pipecat, current OTel
GenAI, legacy OTel GenAI (`gen_ai.prompt.N.content`), Claude Managed
Agents (`anthropic.tool_result.content`), Genkit and Flue. Its
observation-type mapper has separate rules for OpenInference,
OTel GenAI operation names, Genkit, LiveKit, Flue and Claude Managed
Agents, plus a fix for one old version of its own Python SDK.

That is the practical answer to "how many ways": one transport, one
data model, and about fifteen meanings, of which **two are general
standards (OTel GenAI, OpenInference)** and the rest are frameworks
that predate or ignore them.

## 7. Trajectory and transcript formats

Traces are not the only record of a run. The other record is the
**transcript**: the ordered messages, tool calls and results, as the
model saw them. There is no OTel shape for it (content on spans is a
per-call snapshot, not a conversation).

- **ATIF** (Agent Trajectory Interchange Format, Harbor RFC 0001, v1.8)
  **[source, 3cb627394b]**: a root object with `session_id`, `agent`
  (name, version, model, tool definitions), `final_metrics` (tokens,
  cached tokens, cost, steps), and `steps[]` each with `source`
  (`user`/`agent`/system), message (multimodal parts since 1.6, audio
  1.8), `reasoning_content`, `tool_calls[]`, an `observation` with
  `results[]` keyed by `source_call_id`, per-step metrics (tokens, cost,
  logprobs) and optional RL fields. Subagents embed by
  `trajectory_id` (1.7, a breaking change from `session_id`). The RFC
  compares it to mini-SWE-agent, OpenHands and Gemini CLI trajectories.
  Harbor converts Terminus-2, OpenHands, mini-SWE-agent, Gemini CLI,
  Claude Code and Codex logs to it; Phoenix imports it as traces; NVIDIA
  NeMo Agent Toolkit ships its models **[secondary]**.
- **Harness-native session logs**: Pi's session JSONL is a tree
  (`id`/`parentId`) with typed entries (`message`, `model_change`,
  `thinking_level_change`, `usage`, `compaction` with `tokensBefore`,
  `branch_summary`) **[source]**; Claude Code and Codex keep JSONL
  transcripts that their telemetry joins by `message.uuid` and
  `conversation.id` **[docs]**.
- **Run trees**: LangSmith stores a tree of runs ordered by a
  `dotted_order` string of start time and id **[source]**; the OpenAI
  Agents SDK has traces of typed spans (§ harnesses file).

**[inference]** The field is converging on *two* records per run, a
trace (timing, cost, structure, no content by default) and a transcript
(content, the replayable truth), joined by ids. Keel already has both.
