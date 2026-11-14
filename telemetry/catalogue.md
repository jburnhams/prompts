# Catalogue: how many ways, and which are most common

Counts are over the **27 systems examined** in this pass: 7 harnesses
(Claude Code, Codex, Gemini CLI, OpenCode, Pi, Goose, Claude Agent
SDK), 10 SDKs and frameworks (OpenAI Agents, Pydantic AI,
LangChain/LangGraph/Deep Agents via LangSmith, Microsoft Agent
Framework, Google ADK, Vercel AI SDK, Mastra, CrewAI, LlamaIndex,
Strands), and 10 platforms (Langfuse, Phoenix, LangSmith, Braintrust,
Datadog, Honeycomb, Grafana/OpenLIT, Helicone, Logfire, AgentCore).
"Read" means source code; the rest are from documentation or secondary
write-ups (tags in the other files). Where a system does several
things, it is counted in each. Counts are approximate where marked ~.

## 1. Correlation: how a span finds its parent across a boundary

| Way | Systems | Common? |
|---|---|---|
| W3C `traceparent` in HTTP headers | essentially all that trace | **universal** |
| W3C context in MCP `params._meta` (SEP-414) | Codex, OpenLLMetry, OpenInference, MCP C#/Python SDKs, Logfire, Envoy AI Gateway, ToolHive | growing; standard since `2026-07-28` |
| `TRACEPARENT` env var into a child process | Claude Code (Bash children), Claude Agent SDK (spawned CLI) | rare but the only way into subprocesses |
| Conversation / session id as an attribute | OTel `gen_ai.conversation.id`, OpenInference `session.id`, OpenAI `group_id`, Codex `conversation.id`, Claude Code `session.id`, Honeycomb grouping, AgentCore baggage | **universal** for sessions; not a trace parent |
| Product-specific lineage ids | Codex parent/root turn, Claude Code agent/parent agent, Mastra resume lineage, Keel `root_run_id` | ~5 |
| X-Ray `X-Amzn-Trace-Id` | AgentCore beside W3C | AWS only |

## 2. Transport: how data leaves the process

| Way | Count | Examples |
|---|---|---|
| OTLP to any backend | ~20 of 27 | everything OTel-based |
| Vendor HTTP ingestion API | ~6 | OpenAI Agents default exporter, LangSmith, Langfuse SDK, Goose's Langfuse layer, CrewAI to its own endpoint, Codex to Statsig |
| In-process bus with pluggable exporters | 4 | OpenAI Agents processors, Mastra (13 exporters), Vercel diagnostics channel, Pi typed schema |
| Proxy capture of model traffic | ~5 products | Helicone, Portkey, LiteLLM, Cloudflare and Envoy gateways |
| Local files | 5 | Gemini CLI `outfile`, ADK SQLite, Pi JSONL, Claude Code and Codex transcripts |

**Most common: OTLP**, usually alongside one other route.

## 3. Meaning: which attribute dialect

| Dialect | Who emits it | Status |
|---|---|---|
| **OTel GenAI `gen_ai.*`** (some version) | ADK, MAF, Pydantic AI, OpenCode, Gemini CLI spans, Strands, OpenLLMetry model attrs, Codex token attrs, LangSmith OTel export | **the convergence point**; Development stability, heavy churn |
| **OpenInference** | 49 Arize packages; Phoenix, Arize AX, Datadog accept it | mature, independent, has cost/session/annotations |
| Traceloop `traceloop.*` + legacy `gen_ai.prompt.N` | OpenLLMetry | legacy |
| Vercel `ai.*` | AI SDK (older) | legacy, being replaced by the channel |
| `gcp.vertex.agent.*` | ADK (both languages) | beside `gen_ai.*` |
| Product-named events | `claude_code.*`, `codex.*`, `gemini_cli.*`, `pi.ai.*` | per product |
| Own non-OTel trace models | OpenAI Agents span types, LangSmith run trees | translated at the edge |
| Others ingested by Langfuse | Logfire, LiveKit, MLflow, Pipecat, Genkit, Flue, Claude Managed Agents | ~7 more |

Total distinct dialects an ingester sees: **about fifteen** (Langfuse
handles fifteen families for content alone). **Two are general
standards.**

## 4. Signal shapes used for the agent itself

| Shape | Who |
|---|---|
| Spans (tree) | all tracing systems |
| Log events (flat, product-named) | Claude Code, Codex, Gemini CLI — the harnesses' primary signal |
| Metrics | Claude Code, Codex, Gemini CLI, Pi, semconv, APM vendors |
| Transcript / trajectory file | Pi, Claude Code, Codex, Gemini CLI; ATIF as interchange |
| Scores / feedback / annotations | OTel evaluation event, OpenInference annotations, Langfuse, Phoenix, Mastra, Braintrust, LangSmith |
| Live event stream to a UI | Keel SSE, OpenCode server, ADK web, most SDK streaming APIs **[inference]** |

**Most common combination: spans + metrics + a separate transcript.**

## 5. Content capture default

| Default | Systems |
|---|---|
| **Off / redacted** (opt in per kind) | OTel GenAI (standard), Claude Code, Codex, MAF, ADK (Python and Java), Gemini CLI traces, Keel events |
| **Never recorded** | Pi telemetry (counts and kinds only) |
| **On** (opt out) | OpenAI Agents, Pydantic AI, OpenLLMetry, Gemini CLI prompts in logs, LangSmith, CrewAI-to-OTel |
| **External reference** | OTel `*_ref`, Claude Code `body_ref`, OpenInference blob uploader, Langfuse media, Keel transcript |

Split roughly 6 off, 6 on. **Off with external references is where the
standard and the security-sensitive harnesses landed.**

## 6. Storage

| Store | Who | Scale |
|---|---|---|
| ClickHouse, one wide row per span, maps for usage/cost | Langfuse, Mastra v-next; LangSmith and Helicone **[secondary]** | the default at scale |
| Postgres / SQLite, normalised | Phoenix, ADK dev exporter | team scale |
| Object storage + custom index | Braintrust Brainstore | very large traces |
| General APM stores | Datadog, Honeycomb, Grafana Tempo, CloudWatch | when agents are one service among many |
| JSONL files | Pi, Claude Code, Codex | one machine |

## 7. Session views

Span tree (all), session/thread (most LLM-native), transcript replay
(~6), timeline with lanes (Honeycomb; others implicitly), agent graph
(~3), comparison (experiment platforms), clusters (Langfuse, Docent,
LangSmith). See [`platforms-and-storage.md`](./platforms-and-storage.md)
§3.

## 8. Alerting

Backend-side in every case: metric thresholds and anomaly detection
(APM vendors, Grafana), score monitors (LLM-native platforms). In-run
detection that acts (loops, budgets, crash repeats) lives in the
harness: Gemini CLI, Codex goals, Keel monitors.

## 9. The short answer

- **Most common overall:** OTLP transport, W3C context, spans shaped
  like `invoke_agent → chat → execute_tool`, a session id attribute,
  token usage on the model span, content off or external, a backend
  that adds scores.
- **Least settled:** attribute names (the conventions are Development
  and churning), cost (OTel has no cost attribute; OpenInference does),
  evaluations beyond one event, the transcript format (ATIF is the only
  candidate), and anything about runs that suspend, resume or fan out.
- **Best approaches seen:** OTel's external-content pattern; Claude
  Code's attribution of tokens to the tool result that caused them and
  its human-wait span; Codex's TTFT decomposition and its lineage ids;
  Langfuse's wide events table with truncated core view; Mastra's
  five-signal append-only design and resume lineage; Pi's typed schema
  that records sizes not content; the OpenAI Agents rule that redaction
  and export share one fail-closed exporter.
