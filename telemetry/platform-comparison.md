# Platform comparison: Langfuse, X-Ray/CloudWatch, Datadog, Grafana, Splunk and others

*Added 2026-11-14 after Jonathan asked for "detailed comparisons of
existing apps like langfuse, xray, datadog, grafana, splunk". Several are
in use elsewhere in his organisation; none by his team.*

**Evidence.** Langfuse and Phoenix were read as code (SHAs in
[`../sources.md`](../sources.md)). Everything else is from the vendor's
own documentation **[docs]** or from third-party write-ups
**[secondary]**, fetched 2026-11-14. Nothing was run against any of
them. Prices change often and are not compared here; only the pricing
*model* is. Vendor product names in this space are being renamed
quarterly (Datadog "LLM Observability" → "Agent Observability"; Splunk
"AI Agent Monitoring" → "Agent Observability"), so check the current
page before relying on a feature name.

## 1. The short version

| | Kind | Takes agent traces as | Agent view | Evals / scores | Content | Self-host | Fit for Keel |
|---|---|---|---|---|---|---|---|
| **Langfuse** | LLM-native | OTLP (`/api/public/otel`), own SDK; parses ~15 dialects | sessions, trace tree, agent graph, transcript-style message rendering | yes: online LLM-judge, annotation queues, datasets, experiments, score table | stored in full (ClickHouse + object storage); masking is an Enterprise feature **[secondary]** | **yes, MIT core**, all core features free **[source, LICENSE; docs]** | best agent view; second system to run |
| **Arize Phoenix** | LLM-native | OTLP with OpenInference; converters for OTel GenAI | sessions, traces, spans | annotations at span/trace/document/session, datasets, experiments | stored in full | **yes, Elastic License 2.0** (free to self-host, not to resell) **[source]** | lighter alternative to Langfuse |
| **AWS X-Ray / CloudWatch** | APM + GenAI views | OTLP (ADOT or native OTLP endpoint), X-Ray or W3C headers; spans land in CloudWatch Logs via Transaction Search | GenAI Observability: Model Invocations, AgentCore agents (sessions, traces, spans), **Coding Agent Insights** for Claude Code, Codex, Copilot | "quality and accuracy" monitoring described; details thin **[docs]** | model invocation logs can include input/output; CloudWatch data-protection policies can mask **[docs]** | no (AWS service) | free correlation with AWS services; weakest agent UX |
| **Datadog** | APM + agent view | OTLP with OTel GenAI ≥1.37, OpenInference, OpenLLMetry ≥0.47 or Langfuse spans; needs `dd_llmobs_enabled=true` **[docs]** | Agent Observability: traces, sessions (from `gen_ai.conversation.id`), execution graph | external evaluations API (`source:otel`), prompt tracking, experiments **[docs]** | stored when on spans; mirrored into APM if APM is on, so use a Restricted Dataset **[docs]** | no | strong if the org already pays for it |
| **Grafana** (Cloud; LGTM stack) | APM + AI dashboards | OTLP with OTel GenAI (OpenLIT SDK or any GenAI instrumentation) into Tempo, Loki, Prometheus **[docs]** | AI Observability dashboards: GenAI, agents, evaluations, MCP servers, vector DBs, GPUs | evaluation dashboards in Cloud **[docs]** | wherever Tempo/Loki store it | Tempo/Loki/Prometheus yes; the AI Observability app is Cloud **[secondary]** | good for metrics and alerts; agent view is dashboards, not sessions |
| **Splunk** (Observability Cloud) | APM + agent view | OTLP with OTel GenAI (`opentelemetry-util-genai`), zero-code for supported frameworks, translators for LangSmith/OpenLIT/Traceloop **[docs, secondary]** | AI overview, agents, AI trace data with an "AI details" tab, service map **[docs]** | LLM-as-judge evaluators, in the library or on the platform **[docs, secondary]** | conversation data can be stored in Observability Cloud; feature availability depends on where **[secondary, release notes]** | Splunk Enterprise on-prem for logs; Agent Observability "on-premises" announced at .conf26 **[secondary]** | if Splunk is the org's log store |
| **Honeycomb** | APM + agent view | OTLP with OTel GenAI 1.40, no vendor SDK **[secondary]** | Agent Timeline, grouped by conversation id | not described | stored as span attributes | no | good trace query UX; least LLM-specific |
| **LangSmith** | LLM-native | own SDK (run trees); OTLP over HTTP **[source for SDK; secondary for ingest]** | runs, threads, LangGraph Studio | strong: datasets, evaluators, experiments, annotation | stored in full | Enterprise plan only **[secondary]** | best if Keel were LangChain; it isn't |

## 2. Per platform

### Langfuse

- **What it is.** Open-source LLM engineering platform: tracing, sessions,
  prompt management, evals, datasets. Owned by ClickHouse, Inc. since
  January 2026 (the LICENSE names ClickHouse) **[source, secondary]**.
- **Ingest.** OTLP traces at `/api/public/otel` (not logs or metrics
  **[secondary]**), plus native SDKs and an HTTP batch API. The ingester
  understands OTel GenAI current and legacy, OpenInference, Vercel `ai.*`,
  ADK `gcp.vertex.agent.*`, Logfire, Pydantic AI, MLflow, Traceloop,
  LiveKit, Genkit, Claude Managed Agents and more
  (`standards.md` §6) **[source]**. Keel's OTel GenAI export would map
  without extra work.
- **Data model.** Traces, observations (span, generation, agent, tool,
  retriever, evaluator, guardrail…), sessions, users, scores, datasets,
  prompts. Storage is ClickHouse (moving to one wide `events` table with
  a 200-character "core" copy for lists), Postgres for config, S3 for
  raw events and media (`platforms-and-storage.md` §2) **[source]**.
- **Agent view.** Session view, trace tree with message rendering, agent
  graphs, cost and latency per observation, topic clustering over
  sessions (`topics` tables) **[source]**.
- **Evals.** LLM-as-judge on live traces, annotation queues for people,
  datasets and experiments, scores keyed to trace, observation, session
  or dataset run, linked to the judge's own trace **[source]**.
- **Access and content.** Projects and org roles in the free version;
  project-level RBAC, audit logs, retention policies, SCIM and
  server-side masking are Enterprise **[secondary]**. Content is stored
  in full unless the client redacts it.
- **Self-host cost.** You run Postgres, ClickHouse, Redis, S3 and two
  services. Free under MIT; Enterprise licence custom-priced.
- **Alerts.** Limited compared with APM tools; most teams alert from
  their APM or from Langfuse's metrics API **[inference]**.

### AWS X-Ray and CloudWatch GenAI Observability

- **What it is.** X-Ray is AWS's distributed tracing; spans now land in
  CloudWatch Logs and are searched with **Transaction Search**, which
  must be enabled. On top sits **CloudWatch Generative AI
  Observability** **[docs]**.
- **Ingest.** ADOT (AWS Distro for OpenTelemetry) or CloudWatch's native
  OTLP endpoints. Both `X-Amzn-Trace-Id` and W3C `traceparent` are
  accepted **[docs]**. Agents outside AgentCore send OTLP with the right
  environment variables and a log-group resource policy for X-Ray
  **[docs]**.
- **Agent views.** Three pre-built areas: **Model Invocations** (Bedrock
  usage, tokens, an invocation log table with input and output),
  **AgentCore agents** (overview, sessions, traces with trajectory and
  timeline, spans), and **Coding Agent Insights**, dashboards for
  Claude Code, Codex and GitHub Copilot built from their native OTel
  metrics, sliced by organisation, department, team, cost centre and
  user sent as resource attributes **[docs]**. Claude Platform traces
  can also be sent to CloudWatch **[docs]**.
- **Evals.** "Assess AI application quality and accuracy" is described;
  no evaluator model or score API was found in the pages read **[docs]**.
- **Content.** Prompt traces and invocation logs can include content;
  CloudWatch Logs data-protection policies can mask sensitive data
  **[docs]**.
- **Alerts.** CloudWatch Alarms on any metric; PromQL over OTLP
  metrics **[docs]**. Mature.
- **For Keel.** If the services Keel calls are on AWS, this gives the
  end-to-end trace for free once Keel exports OTLP with W3C context. The
  agent session view exists only for AgentCore-shaped agents; a Keel
  run would show as generic spans with GenAI attributes **[inference]**.

### Datadog Agent Observability

- **Ingest.** OTLP traces over HTTP/protobuf with `dd-api-key`; GenAI
  conversion is switched on by a `dd_llmobs_enabled=true` resource
  attribute or header. Accepts OTel GenAI ≥1.37 (older partly),
  OpenInference, OpenLLMetry ≥0.47, Langfuse native spans **[docs]**.
- **Mapping.** `chat`/`generate_content` → LLM span, `execute_tool` →
  tool, `invoke_agent`/`create_agent` → agent, everything else →
  workflow. Unmapped `gen_ai.*` attributes become tags truncated at 256
  characters; **other attributes are dropped** (so `keel.*` attributes
  would need `_dd.ml_obs.metadata` to survive) **[docs]**.
- **Agent view.** Traces, sessions from `gen_ai.conversation.id`, an
  execution graph from span links within one trace (links across traces
  are stored but not drawn), cost estimated from tokens or supplied
  **[docs]**.
- **Evals.** External evaluations API, prompt tracking, offline
  experiments **[docs]**.
- **Content.** Stored if on spans; written to APM traces too when APM is
  enabled, which needs a Restricted Dataset to keep access the same
  **[docs]**. MCP is not mentioned on the OTel page.
- **Latency.** 3-5 minutes before traces appear **[docs]**.
- **For Keel.** Works with the proposed export. Two things to watch:
  `keel.*` attributes are dropped unless put in metadata, and Keel's
  cross-run span links (proposal 3) would not be drawn **[inference]**.

### Grafana

- **Ingest.** Any OTel GenAI instrumentation; Grafana promotes OpenLIT.
  Data goes through Alloy or an OTel Collector into Tempo (traces), Loki
  (logs) and Prometheus/Mimir (metrics) **[docs]**.
- **Agent view.** AI Observability in Grafana Cloud: dashboards for
  GenAI, agents, evaluations, MCP servers (tool latency histograms,
  success rates, invocation counts), vector DBs and GPUs; traces in
  Tempo's explorer **[docs]**.
- **Self-host.** Tempo, Loki and Prometheus are open source and widely
  self-hosted; the AI Observability app and its evaluation UI are Grafana
  Cloud, so a self-hosted stack builds its own dashboards
  **[secondary]**.
- **Alerts.** Grafana Alerting on any metric or log query. Mature.
- **For Keel.** The natural home for proposal 8's metrics and
  proposal 12's alerts. It is not a session or transcript viewer.

### Splunk

- **What it is.** Splunk Observability Cloud's **AI Agent Monitoring**
  (GA early 2026) shows performance, quality, tokens, estimated cost and
  risk for agents: an AI overview, per-agent pages, AI trace data and a
  service map **[docs]**. Its own docs page now says it is "scheduled for
  deprecation" in favour of **Splunk Agent Observability**, announced
  at .conf26 as powered by Galileo and available on-premises and in
  Observability Cloud from September 2026 **[docs, secondary]**.
- **Ingest.** OTel GenAI conventions via `opentelemetry-util-genai`,
  zero-code for supported frameworks, and translators for data already
  instrumented with LangSmith, OpenLIT or Traceloop; the Splunk
  Distribution of the OTel Collector **[docs, secondary]**.
- **Evals.** LLM-as-judge evaluators, run in the instrumentation library
  or on the platform (the platform option needs conversation data
  stored in Observability Cloud) **[secondary]**.
- **Content.** Conversation data can be stored in Observability Cloud;
  which features work depends on where it is stored **[secondary,
  May 2026 release notes]**.
- **Alerts.** Splunk detectors and Splunk platform searches. Mature.
- **For Keel.** Usable through OTLP, but the product is mid-transition;
  wait for Agent Observability's docs before committing **[inference]**.

### Honeycomb, Phoenix, LangSmith

Covered in the table above and in `platforms-and-storage.md`. Phoenix's
licence is Elastic 2.0, not OSI open source **[source]**. LangSmith
self-hosting is Enterprise only **[secondary]**.

## 3. What the comparison means for Keel

**[inference] throughout; these feed proposal 10 and open question 2 in
`../agent-design/proposals-telemetry-2026-11.md`.**

1. **Every one of them accepts OTLP with OTel GenAI attributes.** The
   export proposed (proposals 1, 2, 4) is the same whichever backend is
   chosen, and the Collector can send to two at once. Choosing a backend
   is not a design decision for Keel; it is a deployment decision.
2. **APM tools are good at correlation, metrics and alerts; LLM-native
   tools are good at sessions, transcripts and evals.** None of the APM
   tools has a transcript view as good as Langfuse's or a score model
   as complete. None of the LLM-native tools alerts as well as the APM
   tools.
3. **A sensible split for an organisation that already runs one of the
   APM tools:** Keel exports OTLP to the org's Collector; traces and
   metrics go to the APM the org already pays for (end-to-end
   correlation, alerting, on-call); the same traces, content-free, go to
   a self-hosted Langfuse for the agent team's session and eval work;
   transcripts stay in Keel behind `runs:transcript`, linked by ref.
4. **Things to check with the owning teams before choosing:** whether
   the org's Datadog or Splunk contract includes the agent product
   (not checked here); whether
   prompt and output content may enter that system at all (Datadog
   mirrors it into APM); retention; and whether span links across
   traces are drawn (Datadog: no).
5. **What none of them gives Keel:** gates, pipeline stages, refusal
   codes, endings, deliveries and cost attribution to tool results.
   Those stay in the Keel UI and run store whatever is chosen
   (proposal 11).
