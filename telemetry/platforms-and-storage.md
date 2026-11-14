# Platforms, storage and session viewers

Evidence tags as in [`standards.md`](./standards.md). Langfuse,
Phoenix and Mastra were read as code; the rest from documentation or
secondary write-ups, as tagged.

## 1. Four kinds of platform

| Kind | Examples | How data arrives | What it is good at |
|---|---|---|---|
| **LLM-native trace + eval platforms** | Langfuse, Arize Phoenix / AX, LangSmith, Braintrust, W&B Weave, MLflow Tracing, Opik, Laminar, Logfire, AgentOps | OTLP and/or their own SDK and HTTP API | trace and session views with content, prompt management, datasets, online and offline evals, annotation queues, cost |
| **General APM with an agent view** | Datadog Agent Observability (was LLM Observability), Honeycomb Agent Timeline, Grafana AI Observability (OpenLIT), Dynatrace, New Relic, AWS CloudWatch GenAI observability / AgentCore, Sentry | OTLP with GenAI or OpenInference attributes | one place with the rest of the system's traces, mature alerting, retention and access control |
| **Gateways / proxies** | Helicone, Portkey, LiteLLM proxy, Cloudflare AI Gateway, Envoy AI Gateway | the model traffic itself passes through | zero-code capture of every model call, cost, caching, rate limits; **blind to tool calls and agent structure** |
| **Harness-local** | Pi's HTML session export, ADK web UI with its SQLite exporter, Gemini CLI `outfile`, Claude Code and Codex JSONL transcripts, Inspect-style log viewers | files on disk | debugging one session; nothing across sessions |

**Datadog** natively maps OTel GenAI 1.37+ and OpenInference spans
into its agent view (December 2025) **[secondary, Datadog docs]**.
**Honeycomb** built Agent Timeline on GenAI conventions 1.40 and groups
spans by conversation id, "no Honeycomb-specific SDK" **[secondary,
Honeycomb blog]**. **Grafana** uses OpenLIT and ships dashboards for
GenAI, evaluations, vector DBs, **MCP servers** and agents **[docs]**.
**AgentCore** auto-instruments hosted agents with OTel to CloudWatch,
uses X-Ray headers alongside W3C, and correlates sessions with
`session.id` in baggage **[docs]**. **Helicone** was acquired by
Mintlify on 2026-03-03 and is in maintenance mode **[secondary]**,
which is a data point on the proxy model's ceiling. The **OpenAI Agents
SDK** lists 31 external processors, which is a fair census of who
competes here **[source]**.

## 2. Storage: what the platforms actually built

### Langfuse **[source, 48a31810e1]**

ClickHouse for traces, Postgres for configuration, object storage for
raw events and media.

- History: separate `traces`, `observations` and `scores` tables, then
  an `event_log`, now being replaced by a **single wide `events` table
  where every span is a row**, in two forms: `events_full` (input and
  output ZSTD-compressed) and `events_core`, fed by a materialized view
  that keeps only the **first 200 characters** of input and output for
  list views.
- Both are `ReplacingMergeTree(event_ts, is_deleted)`, partitioned by
  month, ordered by `(project_id, minute, hash(trace_id), span_id,
  start_time)`. Updates are new rows; the engine keeps the latest.
- Columns worth copying: `session_id`, `user_id`, `environment`,
  `release`, `version`, `tags`; prompt name and version; provided model
  name and resolved `model_id`; `provided_usage_details` and
  `usage_details` as **maps** (so new token kinds need no migration);
  `provided_cost_details` and calculated `cost_details` as maps, with
  materialized input/output/total cost; `tool_definitions`,
  `tool_calls`, `tool_call_names`; `input_length` and `output_length`
  materialized; experiment ids for eval runs.
- `scores` is a separate table keyed by trace, observation, **session**
  or dataset run, with numeric, categorical and long-string values and
  the trace id of the evaluator's own execution.
- `topics` and topic-assignment tables hold **clustered traces**:
  centroid, radius, representative summaries. Automatic topic discovery
  over sessions.

### Mastra v-next ClickHouse design **[source, 94fd1f0a5f, `observability/clickhouse-design/`]**

A written design for five append-only signals: **spans, metrics, logs,
scores and feedback**. Tracing is insert-only (`span_events` plus a
`trace_roots` table), only ended spans are persisted, retries are made
idempotent with a `dedupeKey`, scores and feedback may exist without a
trace, retention is by day, and filter semantics were deliberately
narrowed (top-level string metadata equality only) to keep queries
cheap. Discovery tables (distinct values for filters) are optional.

### Arize Phoenix **[source, a9ce4b0f4d]**

SQLite or Postgres via SQLAlchemy: `projects`, `project_sessions`,
`traces`, `spans`, annotations at **span, trace, document and session**
level, datasets with versions and splits, experiments with runs and
annotations, prompts with versions, `token_prices` and per-project
retention policies. A relational model is enough for single-team scale.

### Braintrust **[secondary, Braintrust blog]**

Built its own store, Brainstore: object storage as the source of truth,
stateless nodes, a write-ahead log, background indexing with Tantivy
full-text search, columnar analytics and vector indexes, with a run's
spans co-located so a whole execution loads together. They report
customer traces over 1 GB and single spans of 20 MB. Claims of speed
are vendor-reported.

### LangSmith **[source for the client, inference for the store]**

Runs are sent as a tree ordered by `dotted_order`. The store is not
open source.

### Harness-local stores

ADK's `sqlite_span_exporter.py` writes OTel spans to SQLite for its dev
UI **[source]**. Pi writes one JSONL file per session **[source]**.
Claude Code can write raw API bodies to a directory and reference them
**[docs]**.

### What the storage designs agree on **[inference]**

1. **One row per span, wide, with maps for open-ended keys** (usage,
   cost, metadata). Langfuse moved *to* this from normalised tables.
2. **Content is stored separately or truncated in the hot table.** The
   list view never needs more than a preview.
3. **Append-only with last-write-wins**, because spans arrive late, out
   of order and more than once (partial updates, retries).
4. **Scores and feedback are their own signal**, keyed by span, trace or
   session, and can arrive days later from a different process.
5. **ClickHouse** is the default at scale (Langfuse, Mastra, and most
   secondary sources for LangSmith and Helicone); SQLite/Postgres at
   team scale (Phoenix, ADK); object storage plus custom indexes at the
   top end (Braintrust).
6. **Cost is computed at ingest from a price table** and kept beside the
   provided cost, so a price change can be replayed. Keel's
   `price_snapshot` is the same idea.

## 3. Showing a session: the views that recur

Every platform read or documented offers some subset of these. They are
listed with what each answers.

| View | Answers | Who has it |
|---|---|---|
| **Span tree / waterfall** | what called what, how long, where the time went | all |
| **Session / thread** | what happened across turns of one conversation | Langfuse, Phoenix, LangSmith, Honeycomb (by conversation id), Weave |
| **Chat replay / transcript** | what the model saw and said, in order | Pi HTML export, Langfuse and LangSmith message rendering, ADK web, Docent |
| **Timeline / Gantt with lanes** | parallel sub-agents and tools, idle and waiting time | Honeycomb Agent Timeline, Claude Code's `blocked_on_user` spans make it possible |
| **Agent graph** | which agents and tools are connected, how often | Langfuse agent graphs, OpenInference `graph.node.*`, LangGraph Studio |
| **Cost and token breakdown** | spend per model, per tool result, per sub-agent | all LLM-native platforms; Claude Code attributes tokens to MCP tool and skill |
| **Diff / comparison** | two runs of the same task side by side | Braintrust, LangSmith experiments, Phoenix experiments |
| **Clusters / topics** | what kinds of sessions there are, which fail | Langfuse topics, Docent, LangSmith insights **[docs]** |
| **Dashboards** | rates and trends | APM vendors, Grafana, Codex and Gemini CLI's GCP dashboards |

**[inference]** For a coding or analysis agent the tree is the wrong
primary view. A run is a conversation with tool calls, so the primary
view is the **transcript with spans folded into it**: each model turn
with its tokens, cost and latency; each tool call with arguments,
status, duration and a collapsed result; sub-agents as nested,
collapsible transcripts; waits on a person as visible gaps. The
waterfall is a secondary tab for latency work.
