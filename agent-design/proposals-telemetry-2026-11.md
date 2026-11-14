# Proposals from the agent telemetry deep dive (2026-11-14)

**Status: proposals only, none adopted.** Jonathan asked to discuss how
Keel, Forge and Lens should do this before anything changes, so no
other file under `agent-design/` is edited. The research is in
[`../telemetry/`](../telemetry), the cross-source concept in
[`../agent-telemetry.md`](../agent-telemetry.md).

**Evidence level.** Every proposal names the source it rests on and
whether that source was read as code or as documentation. Where a
proposal rests on our inference only, it says so.

## Where Keel stands today

Keel already has more of this than most harnesses read here:

- **An event stream without bodies** (`triggers-and-runs.md` §10,
  `RunEvent`): state, turns, tool calls and results (size and status),
  refusals, narration, harness notes, reveals, the nudge, gates,
  artifacts, usage, outcome, deliveries, follow-ons, server requests,
  reissued calls, `cache_collapse`, `context_overflow`. SSE, resumable
  by sequence number.
- **A transcript with its own permission** (`runs:transcript`,
  separately audited). This is OTel's recommended production pattern,
  "store content externally and record references … enables separate
  access controls" (`../telemetry/standards.md` §2d), arrived at
  independently.
- **Usage per agent and per model**, with cache tokens and a price
  snapshot (`Usage.by_model`). OTel removed cache breakdowns from the
  agent span for the same reason Keel keeps them per model.
- **Lineage**: `root_run_id`, `depth`, `resumes`, `pipeline_run_id`,
  `stage`. Richer than any harness except Codex.
- **Health signals already decided**: `cache_collapse`,
  `context_overflow`, the deterministic-crash stop
  (`repeated_infra_failure`), and Forge's finding-outcome telemetry
  (`../medium.md` §3e).

What it lacks:

- **No export.** Nothing says how a run appears in a trace backend, an
  APM tool or X-Ray, or how a Keel run joins the traces of the systems
  it calls (MCP servers, the sandbox, the model provider) and of the
  system that called it.
- **No metrics** as such, and no cardinality rules.
- **No quality signal** beyond §3e: completion-check results, eval
  scores and human feedback have no common shape or store.
- **No defined transcript format.** "Everything the model saw and did"
  is a definition, not a schema.
- **No view.** The Keel UI exists (memory: it is not headless), but the
  docs don't say what a run looks like in it.
- **No alerts** and no in-run loop detector beyond the crash repeat.

## Proposals

### 1. One emitter, two projections: `RunEvent` stays the record, OpenTelemetry is an export

**What.** The harness keeps writing `RunEvent`s and the transcript as
today. A telemetry exporter, in the harness process, turns the same
calls into OTel spans, metrics and events. Keel concepts are never
modelled *only* in OTel.

**Why.** The OTel GenAI conventions are Development stability with 90
pending changelog fragments, 20 of them breaking
(`../telemetry/standards.md` §2e), and they have no words for gates,
refusal codes, endings, deliveries or pipeline stages. Every harness
that does this well keeps its own model and exports (OpenAI Agents
processors, Mastra exporters, Pi's typed schema, Vercel's channel;
`../telemetry/harnesses-and-sdks.md` §3). Keel's API consumers (the UI,
pipelines, health queries) must not break when the conventions do.

**Cost.** One exporter module and a mapping table (proposal 2).

### 2. The mapping to OTel GenAI, pinned

**What.** Export with these shapes, pinned to
`open-telemetry/semantic-conventions-genai@e6658f1` and recorded as the
schema URL and a `keel.semconv.commit` resource attribute:

| Keel | OTel span | Key attributes |
|---|---|---|
| pipeline run | `invoke_agent.internal`, operation `invoke_workflow` | `gen_ai.agent.name` = pipeline name, `keel.pipeline_run.id` |
| run (stage run, ad hoc run) | `invoke_agent.internal`, operation `invoke_agent` | `gen_ai.agent.name` = template name, `gen_ai.agent.version` = template version, `gen_ai.conversation.id` (proposal 3), `keel.run.id`, `keel.root_run.id`, `keel.stage`, `keel.deployment`, `keel.tier` |
| sub-agent | nested `invoke_agent.internal` | `gen_ai.agent.name` = sub-agent name |
| model call | inference client span `chat {model}` | provider, request and response model, usage incl. `cache_read` / `cache_write` / reasoning, `gen_ai.request.reasoning.level`, `finish_reasons`, `gen_ai.conversation.compacted` after compaction |
| built-in tool call | `execute_tool {name}` | `gen_ai.tool.name`, `gen_ai.tool.call.id`, `keel.tool.visibility`, `keel.refusal.code` on refusal |
| MCP tool call | MCP client span `tools/call {name}` (it *is* the `execute_tool` span) | `mcp.method.name`, `mcp.protocol.version`, `jsonrpc.request.id`, `keel.server` |
| `Expand` / reveal, `Load*` of a skill | `execute_tool` with the skill operations (`load_skill`, `read_skill_resource`) where they fit | `gen_ai.skill.*` |
| waiting on a person (gate, approval, elicitation) | `keel.wait` child span | `keel.wait.kind`, who answered |
| nudge, harness note, `cache_collapse`, `context_overflow`, `reissued_call` | span events on the run span, `keel.*` names | the event's data minus bodies |
| outcome | attributes on the run span | `keel.outcome.terminal`, `keel.outcome.finished_with`, span status `ERROR` only for infrastructure death |

The `keel.*` attribute names are a small registry in Keel's own docs,
versioned with Keel.

**Why.** The conventions' own examples name the patterns this maps to
(MAF `Agent` vs `Workflow`, LangGraph `StateGraph`) and merged the
workflow span into the agent span on this branch. The human-wait span
is Claude Code's `tool.blocked_on_user` (docs): time waiting on a person
is the largest and least visible latency in an approval-gated run.
Span status `ERROR` only for infrastructure keeps the error rate
meaningful; a run that ended with `RequestHelp` is not an error.

**Rests on:** `semantic-conventions-genai` (source), Claude Code
monitoring docs (docs).

### 3. Trace boundaries: one trace per run, linked; the session id is the root

**What.**

- **Each run is its own trace.** A stage run, a continuation, a resume
  and a sub-run each start a new trace whose root span carries **span
  links** to the run that caused it (the previous stage, the suspended
  run, the parent).
- `gen_ai.conversation.id` = the chat thread id when a chat started the
  work, otherwise `root_run_id`. Every run in the tree carries it, so
  backends that group by conversation (Honeycomb, Langfuse sessions,
  Datadog) show the whole request.
- The pipeline run gets a short trace of its own (its `invoke_workflow`
  span covers orchestration, not the stage runs' contents), linked from
  each stage.

**Why.** A gate can hold work for days. Backends assemble traces in
time windows, tail samplers buffer whole traces, and a trace that lasts
three days defeats both **[inference]**. Links keep the causal chain
without the duration. **The alternative** is Mastra's: resumes stay in
the original trace as siblings under the first agent span, with lineage
saved in the snapshot (`../telemetry/harnesses-and-sdks.md` §2,
source). It gives one picture per request but needs the original trace
id to outlive the suspension; worth it only if the chosen backend
tolerates long traces. **This is the main open question.**

### 4. Propagate context through every call Keel already makes

**What.**

- **Inbound**: accept `traceparent` / `tracestate` on `POST /v1/runs`
  and on inbound events (`/v1/events/{provider}` where the provider
  sends it), and parent the run under it.
- **MCP**: Keel's own MCP client writes `traceparent`, `tracestate`
  and filtered `baggage` into `params._meta` on every request and
  notification (SEP-414, Final in `2026-07-28`, which Keel targets), as
  well as HTTP headers on Streamable HTTP.
- **Sandbox**: commands run with `TRACEPARENT` / `TRACESTATE` in the
  environment of the tool span (Claude Code's pattern).
- **Model providers**: `traceparent` header where the provider records
  it.
- **Baggage**: only `keel.run.id`, `keel.root_run.id` and the tenant,
  and **none to servers outside the first-party trust tier**
  (`proposals-mcp-apps-2026-11.md`'s tiers). Never the principal.

**Why.** It costs nothing extra: these are calls Keel already makes, and
Keel owns its MCP client (`keel/decisions.md` §14a). Keel's own MCP
servers then appear as children of the tool call in the same trace, and
Forge's checkout and test runs join it through the environment. Codex
does the `_meta` and header injection (source,
`rmcp-client/src/trace_context.rs`); Claude Code covers HTTP MCP only
(docs), which leaves stdio servers out. Baggage travels to every
downstream system, so it must hold nothing a third party should not see.

**This answers "can it be standardised into existing calls"**: yes for
correlation. No new API is needed anywhere.

### 5. Content: off on export, references into the transcript

**What.**

- The exporter's default is `NO_CONTENT`. Spans carry
  `gen_ai.input.messages_ref`, `gen_ai.output.messages_ref`,
  `gen_ai.system_instructions_ref` and `gen_ai.tool.definitions_ref`
  as `run://{run_id}/transcript#{entry_id}` URIs, resolvable only with
  `runs:transcript`. System prompts and tool definitions use
  content-derived ids, so the same prompt is one object.
- A deployment may opt in to `SPAN_ONLY` content, and only a `sandbox`
  deployment by default. Zero-retention and HIPAA deployments cannot
  opt in (consistent with `keel/decisions.md`'s message-thread rule).
- **Redaction and export are one exporter that fails closed**: if
  serialising or redacting a batch fails, the batch is dropped and a
  fixed message is logged.
- Metric labels never carry user-supplied names: an MCP server or tool
  configured by a user is labelled `custom` unless the deployment opts
  in.

**Why.** OTel's three patterns, of which Keel already is the third
(`../telemetry/standards.md` §2d, source). The fail-closed rule is the
OpenAI Agents SDK's explicit warning: a redaction processor beside the
exporter does not stop the exporter (source, `docs/tracing.md`). The
`custom` label is Claude Code's (docs).

### 6. A defined transcript format, with join keys and an ATIF export

**What.** Define the transcript as append-only JSONL of typed entries
with stable ids and parent ids (user/model/tool messages, tool results,
reveals, compaction with tokens before and after, model changes, harness
notes, waits). Every `RunEvent` that corresponds to an entry carries its
`entry_id`; every exported span carries it as `keel.transcript.entry_id`.
Offer `GET /v1/runs/{id}/transcript?format=atif` producing ATIF v1.8,
with sub-agents embedded by `trajectory_id`.

**Why.** The trace stays content-free and still leads to the content in
one hop, which is how Claude Code (`message.uuid`) and Codex (`item.id`)
join their telemetry to their transcripts (docs, source). Pi's session
tree shows the entry types a harness needs (source). ATIF is the only
interchange format for trajectories, used by Harbor and imported by
Phoenix (source, Harbor RFC 0001); it gives `eval.md` and any future
training work a standard input.

### 7. Attribute cost to what caused it

**What.** Each model call's input tokens are attributed to the context
that was new since the previous call: which tool result, which reveal,
which sub-agent report. Usage events and the model-call span carry
`keel.cost.attributed_to` (tool name and server, or `reveal`, `nudge`,
`user`), and the run outcome carries a per-source total. Add
`keel.run.inference_calls` and `keel.run.tool_calls` (the semconv's
`invoke_agent.inference_calls` / `.tool_calls`).

**Why.** "Which MCP tool is costing us" is the question a tool-group
author can act on, and a total per model cannot answer it. Claude Code
attributes cost and token metrics to `mcp_server.name`, `mcp_tool.name`,
`skill.name` and `agent.name` (docs). It also gives `tools.md`'s result
caps a measurement.

### 8. A small metric set with cardinality rules

**What.** Export the semconv metrics (inference duration, time to first
chunk, the five usage counters, `execute_tool.duration`,
`invoke_agent.duration`, MCP client operation duration) plus:

| Metric | Labels |
|---|---|
| `keel.run.count` by terminal outcome | template, version, deployment, trigger kind |
| `keel.run.cost` (USD, histogram) | template, version, tier |
| `keel.refusal.count` | code, tool or server |
| `keel.cache_collapse.count`, `keel.context_overflow.count` | template, version, model |
| `keel.wait.duration` | wait kind, template |
| `keel.stage.blocked` (gauge) | pipeline, stage, reason |

Rules: **no run, principal, session or trace id on any metric**
(they are span attributes); model ids and user-named things only as
described in proposal 5; Codex's lesson that metrics default to delta
temporality with a switch for cumulative backends (source).

**Why.** Alerts (proposal 12) need metrics; metrics with run ids are a
cardinality incident. Claude Code exposes switches to drop session and
account ids from metrics for exactly this reason (docs).

### 9. Scores as a first-class signal

**What.** A `Score` record, written by anything that judges a run, keyed
by run, model call, tool call, pipeline run or root run:
`{name, value | label, explanation, source: check|eval|judge|human|outcome,
judge_run_id?}`. Sources Keel already has: completion-check results,
report validation, integrity cross-checks, `eval.md` suites, Forge's
§3e finding outcomes, Lens's answer gate. New: human feedback from a
channel (a reaction or reply on a delivered result). Exported as
`gen_ai.evaluation.result` events parented to the scored span; stored
in their own table.

**Why.** Every platform read keeps scores apart from spans because they
arrive later and from elsewhere (Langfuse `scores`, Phoenix annotations
at four levels, Mastra's score and feedback signals; source).
OpenInference adds session-scope scores, which match Keel's root run.
It gives §3e, `eval.md` and Lens's gate one place to land, and gives
proposal 12 something to alert on.

### 10. Storage: keep Keel's store authoritative; send telemetry to a backend, don't build one first

**What.**

- Keel's run store (events, transcripts, outcomes, scores) stays the
  system of record, as now.
- Telemetry goes out over OTLP to an OpenTelemetry Collector the
  deployment configures. The Collector routes it: to the
  organisation's APM (X-Ray, Datadog, Grafana) for infrastructure
  correlation, and to an LLM-native backend for the agent view.
- For the LLM-native backend, **start with a self-hosted Langfuse**
  (ClickHouse, OTLP ingestion of GenAI spans, sessions, scores,
  datasets, open source) rather than building one. Phoenix is the
  lighter alternative.
- If Keel later needs its own analytics store, copy the shape that
  Langfuse moved to and Mastra designed: one wide row per span in
  ClickHouse, maps for usage and cost, a truncated "core" table for
  lists and a full one for detail, append-only with
  replacing-merge, scores in their own table, content in object
  storage (the transcript store).

**Why.** Two different audiences: an SRE wants a Keel run inside the
same trace as the services it touched; a template author wants
sessions, scores and transcripts. One Collector feeds both. Building
the second is a product of its own (Braintrust built a database;
Langfuse rebuilt its tables twice; source and secondary). **Depends
on** whether Jonathan's organisation already runs an APM and an
LLM-native backend, which is an open question below.

### 11. The Keel UI run view is transcript-first

**What.** The run page in the Keel UI renders from `RunEvent`s and the
transcript, not from the trace backend:

- the transcript, with each model turn showing tokens, cost, latency
  and cache hit, and each tool call showing arguments, status, duration
  and a collapsed result;
- sub-agents as collapsible nested transcripts, parallel ones as
  lanes;
- waits on a person as visible gaps with who answered;
- refusals, nudges, reveals and harness notes inline where they
  happened;
- a header with outcome, cost by source (proposal 7), scores
  (proposal 9) and links to the trace in the backend and to the parent
  and child runs;
- per use case, a panel: **Forge** the diff, checks and review findings
  with their later outcomes; **Lens** the queries run, rows scanned and
  the refs each claim cites.

Live runs use the existing SSE stream. A waterfall tab is for latency
work.

**Why.** A run is a conversation with tool calls; the span tree is the
wrong primary view for it (`../telemetry/platforms-and-storage.md` §3,
inference). The Keel UI already exists and already has the stream.
The per-use-case panels are where Forge and Lens differ.

### 12. Loop detection as monitors, and fleet alerts per template version

**What.**

- **In run**, add three built-in monitors: the same tool with the same
  argument digest N times in a row (default 3); the same error type from
  the same tool N times in a row; N turns with no state-changing call.
  Each emits a `loop_suspected` event and takes the monitor's configured
  action (note, nudge, stop).
- **Across runs**, an `alerts` block on a template (or a resource beside
  it) using proposal 8's metrics and proposal 9's scores: cost per run
  p95, refusal rate, tool error rate per server, `cache_collapse` rate,
  score mean. Each alert **compares the current published version with
  the previous one** and links to the diff between them. Keel evaluates
  them, or exports them as rules for the deployment's alerting system.

**Why.** Gemini CLI's `loop_detected` (source) shows the in-run
detector; Keel's deterministic-crash stop already keys on the argument
digest, so the first monitor is cheap. Almost every regression in the
alert list follows publishing a new version of a template, prompt or
tool group (inference), so the version is the right comparison.

### 13. Lens on Keel's own telemetry

**What.** Ship two Lens templates that read the run store through the
query DSL: a **quick** one for questions like "which tool failed most
for Forge implement v4 last week, and what did it cost", and an
**investigate** one that reads transcripts (needs `runs:transcript`) to
cluster failed runs and say why, citing run ids, like Docent's reports.

**Why.** It dogfoods Lens on data Keel owns, and Docent shows that
LLM-over-transcripts finds problems aggregate metrics don't, such as
missing packages in an environment that lowered a solve rate
(secondary, Transluce). **Depends on** proposal 10's analytics store or
the DSL reaching the run store.

### 14. Forge and Lens specifics

**Forge**: emit §3e finding outcomes and PR follow-up fixes as scores
(proposal 9) so they appear beside the run that produced them; label
spans with repository and ticket (as span attributes, not metric
labels); add `keel.run.cost` per ticket to the PR report.
**Lens**: attribute warehouse query cost and rows scanned to the run
(an MCP server result field, recorded like tokens), and record the
answer gate's citation check as a score.

**Why.** Each use case already has one quality signal that is waiting
for somewhere to go.

## Open questions for the discussion

1. **Trace boundary** (proposal 3): one trace per run with links, or
   Mastra's one trace per request that survives suspension?
2. **Which backends exist already?** Is there an APM in use (X-Ray,
   Datadog, Grafana, Honeycomb), and is an LLM-native backend
   acceptable to self-host, or should the Keel UI and run store be the
   only agent view?
3. **Content opt-in**: should any production deployment be allowed
   `SPAN_ONLY`, or only sandboxes?
4. **Who owns `keel.*` names**: a registry in `keel/` docs, or a
   Weaver model so it can be validated like the OTel conventions?
5. **Scores resource**: a new API resource, or a `RunEvent` type plus a
   query?
6. **Order**: proposals 1, 2, 4 and 5 are the foundation; 6 and 9 are
   format work; 11-13 depend on them. Is that the right order?
