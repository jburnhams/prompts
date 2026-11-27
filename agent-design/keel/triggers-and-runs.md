# Keel: triggers and runs

What starts work, and the life of a run. Part of [Keel](./README.md). Section numbers are shared across Keel's files, so a reference like §7f means the same section everywhere; [the README](./README.md#files) lists which file holds each.

---

## 9. Triggers

[`trigger.schema.json`](./schemas/trigger.schema.json). A
trigger is `{owner, template | pipeline, source, filter, params,
origin, run_as, dedupe, concurrency, rate_limit, creates}`. It starts a
template or a pipeline. `origin` records where the request came from:
the issue, the PR, the chat thread. Each provider has a default, and
outputs addressed to `{origin: true}` go there.

| Source | For | Notes |
|---|---|---|
| `schedule` | digests, sweeps, check-back-later | `cron` with a required IANA `timezone`, `jitter_s`, `catch_up: none \| latest`, `overlap: skip \| queue`, start and end |
| `event` | Jira transitions, PR opened/updated/commented/merged, build failed, artifact published, generic signed webhooks | normalised `Event`, signature-checked and sanitised at `POST /v1/events/{provider}` |
| `run_outcome` | chaining across owners | another template's terminal and status |
| `manual` | chat commands, UI buttons | binds params and policy to an entry point; `run_as: invoker` makes the invoking user the principal |

**Expressions are CEL**, evaluated by the harness, never by or for the
model. They can be checked for cost before they run, and they can't
loop. The variables:

| Where | Variables |
|---|---|
| trigger `filter`, `params`, `dedupe.key`, `concurrency.key`, `run_as.actor` | `event` |
| spec `concurrency.key`, sink `idempotency_key`, `ChannelRef.target` | `params`, `principal`, `run` |
| continuation `on.expr`, `params` | `params`, `result`, `principal`, `run`, and `spinoff` (with `index`, `title`, `paths`, `kinds`) on spinoff edges |
| sink `when.expr`, sink `args` | `params`, `result`, `run`; on a pipeline sink also `pipeline`, `stage` |
| pipeline stage `params`, edge `params`, edge `on.expr` | `pipeline`, `origin`, `principal`; on an edge also `result` |
| a fixed tool argument | `params`, `run` (including `run.workspace.path`) |

Free text from `event` can only reach params with `trust: external`,
which can only bind to inputs (§6). So a PR title can become a
nonce-wrapped `<pull_request>` block, and nothing else.

**Every evaluation is a `Firing`**, including filtered, deduped,
skipped, rate-limited and refused ones, so "why didn't it run" has an
answer. `:fire` with `test: true` returns the `RunRequest` a supplied
event would produce, without starting it.

**Concurrency happens twice, deliberately.** The trigger's key limits
firings (one review per PR, with `supersede_queued` so a second push
replaces a queued review rather than adding another). The template's
key limits work on a resource: `(repository, branch)` for implement
runs, held while the stage settles on its PR (`../orchestration.md` §4's
`handoff` rule, §7f). A
running run is never cancelled by either.

The wait conditions in `../medium.md` §4c (`jira`, `build`, `pr`,
`timer`) are a stage's `waiting_on` and `settle` (§7f), evaluated by the
dispatcher. They're not triggers, because they resume existing work
rather than create it.

### 9a. Events from MCP servers *(proposed 2026-11-23, weekly pass)*

**Amendment.** MCP gained a standard way for a server to say what can
be watched: the Events extension (`io.modelcontextprotocol/events`,
SEP-3415, merged 2026-11-19, defined for `2026-07-28` only). Until now
every `event` source above needed a provider adapter behind `POST
/v1/events/{provider}`. Keel already connects to the servers that wrap
Jira, GitHub and the warehouse, so a server that offers events can be a
trigger source with no adapter. This adds `source.kind: mcp_event`
(`schemas/trigger.schema.json`) and changes nothing for the existing
providers.

What the extension gives (`../../mcp-events.md` has the detail):
`events/list` returns event types with an `inputSchema` for
subscription arguments and a `payloadSchema`; an occurrence is
`{eventId, name, timestamp, data, cursor}`; delivery is poll, push or a
signed webhook with a TTL the client refreshes; cursors are opaque and
replay is optional per type; `truncated: true` says events were
skipped; a `terminated` signal ends a subscription when access is
revoked or the type changes. The client owns every subscription, and the
spec leaves "what the agent does with an event" to the client.

The rules:

- **Keel is the client, and the trigger is the subscription.** The
  registry of `mcp_event` triggers is the client-owned subscription
  list the spec asks for. Subscriptions are opened by the dispatcher
  with the credential `run_as` resolves to, never by a model and never
  from a run. Arguments are literals or config-trust params, validated
  against `inputSchema` at publish, so event or model text can never
  widen what is watched. `events/list` is pinned in the server
  snapshot (`tools-and-agents.md` §4a) like `tools/list`; a type that
  disappears or changes its schema follows the server's `drift_policy`.
- **The model never chooses the delivery mode.** `auto` prefers
  webhook, because Keel already has a signed inbound endpoint and
  webhook survives a dispatcher restart without a held connection, then
  poll (honouring `nextPollMs`), then push.
- **The cursor commits with the Firing.** Each occurrence is one
  `Firing` with `event_id` and `cursor`, written in one transaction, so a
  crash replays from the last committed cursor and the repeat is caught
  by `eventId` (recorded `deduped`, filter not evaluated). OpenCode's
  automations commit the cursor "together, only after any handoff is
  durable" for the same reason. The trigger's own `dedupe` still applies
  on top, across subscriptions.
- **A gap is a Firing, not silence.** `truncated: true`, or a cursor the
  server no longer accepts, records `result: gap`. With the default
  `on_gap: fire_gap` the template also starts once with `event.gap =
  true` and no payload (the `Event` schema's `gap` field; `provider`
  is `mcp:<server>`), and is expected to read authoritative state
  through tools instead of trusting it saw everything. The spec says the
  same: agents "should use tools to read authoritative state, and should
  not rely solely on event payloads".
- **A trigger that was disabled restarts from now.** Re-enabling does
  not replay what happened while it was off (OpenCode resets the cursor
  to null for the same reason); `catch_up` is for schedules only.
- **Payload is `trust: external`, and small.** `data` binds only to
  external-trust params (§6), as every `event` source does, and reaches
  the model as a nonce-wrapped block. An occurrence over
  `max_payload_bytes` is recorded `skipped_oversize` and the cursor
  moves past it, so one large event cannot stall the watch (OpenCode
  #65673). Templates should bind ids and fetch content with tools, which
  is the spec's "payload minimality" from the receiving side.
- **Authority is checked at firing, not only at subscribe.** Receipt of
  an event is not authority to act (the spec's "action time" rule). The
  run is admitted under the trigger's `run_as` exactly as any other
  firing, so a revoked delegation refuses the firing with
  `delegation_missing` even if the server has not yet terminated the
  subscription. OpenCode re-checks the authorising session and grant
  before every delivery.
- **`terminated` disables the trigger.** The Firing is recorded
  `subscription_ended` with the error code; `Forbidden` disables the
  trigger and notifies its owner, while `NotFound` and `Unsupported`
  mark it for re-validation against a fresh `events/list`. A webhook
  subscription that fails refresh is treated the same way.

Not in this amendment: using MCP events for a stage's `waiting_on`
(§7f's settle conditions could subscribe instead of polling, and the
spec's open question 4, task state as events, would make that
natural); and multi-type subscriptions (open question 3). Status: the
SEP is marked Final, the TypeScript SDK reference implementation is
still in review, and Keel's own MCP client would carry this. OpenCode
shipped push delivery against it on 2026-11-21; Claude does not
support it yet; ChatGPT is reported to support webhook delivery only
(secondhand, `../../mcp-events.md` §4).

---

## 10. Runs

[`run.schema.json`](./schemas/run.schema.json).

```
queued → provisioning → running ⇄ finalizing → ended
                          │
                          └→ suspended ──(principal reply)──► a resume run, or an execute continuation
```

- **`provisioning`** resolves the spec for this principal and
  deployment, checks tool snapshots, takes the concurrency slot,
  provisions the checkout, resolves context, and pre-fetches inputs. A
  failure here ends the run with a refusal code, before any model call.
- **`finalizing`** is between the model's terminal call and the end:
  report validation, completion checks (the first-`done` checklist sends
  the run back to `running`), integrity cross-checks, sinks and
  continuations.
- **`suspended`** holds a gate. The run itself has ended. The suspended
  record keeps envelope and transcript for a resume.
- **Stopping**: `:stop` is graceful by default. It injects the
  final-turn steer at the next turn boundary, so even a cancelled run
  ends through `Complete` with an honest report. `abort` exists, and
  ends with `terminal: stopped`. The harness then posts the failure note
  itself, as `../formats.md` §7 requires for infrastructure deaths.
- **`ResolvedSpec`** is the immutable snapshot a run executes: the flat
  spec with params bound, and per agent the tier, model id, provider,
  deferral strategy and the fixed tools array with each tool's visibility
  at turn 0. "The tools array and the system prompt are fixed for a run"
  is this object not changing.
- **`Usage`** is per agent and per model id, with cache tokens and a
  price snapshot id, so cost stays reproducible after a price change
  (`../models.md` §8's "record tier, model ID and the price at the time").
- **Events** (`GET /v1/runs/{id}/events`, SSE): state changes, turns,
  tool calls and results (sizes and status, not bodies), refusals,
  narration, harness notes, reveals, the steer, gates, artifacts, usage,
  outcome, deliveries, follow-ons, `cache_collapse`,
  `context_overflow`, `response_retry`, `budget_stop` and
  `outbound_rewrite`. Bodies are in
  the transcript, which has its own permission and is audited.
- **`response_retry`** and **`budget_stop`** *(added 2026-11-16, weekly
  pass)*: a model response dropped and asked again, with its kind
  (`output_cut`, `stream_incomplete`, `malformed_response`,
  `empty_response`), request id and attempt number
  (`../formats.md` §7 item 4); and a hard budget reached, naming the
  budget and the admission point where it was caught
  (`run-spec.md` §3, budgets).
- **`outbound_rewrite`** *(proposed 2026-11-23, weekly pass)*: text
  bound for people was changed by the `outbound_text` check, naming the
  delivery or tool call, the rules that fired and a count per rule,
  never the text (`tools-and-agents.md` §4d).
- **`cache_collapse`** *(added 2026-11-11,
  `../proposals-agentic-sdks-2026-11.md` §2)*: the harness checks the
  prompt cache on every response. Per `(provider, endpoint, model)` key
  and per conversation it keeps the **established prefix**, the largest
  `cache_read + cache_write` the provider has confirmed. A response
  whose `cache_read` falls short of that by more than
  `cache_collapse.min_fraction` (default 5%) **and** at least
  `cache_collapse.min_tokens` (default 2,000) is a collapse. It is
  classified against the provider's retention window from the
  deployment's provider configuration, timed from the same key's
  previous request: `unexpected` (the window should still hold, so the
  prefix moved), `unknown` (the provider publishes no window),
  `ttl_expired`, `compacted` or `unreported`. Only `unexpected` and
  `unknown` emit the event, with `reason`, the model key,
  `established_tokens`, `cache_read_tokens` and `missed_tokens`; the
  mark then re-baselines to what that request established, and stays
  quiet until a healthy read-back, so a prefix that moves every request
  reports once. A model fallback starts its own key and does not report.
  Observe-only: nothing in the run changes. The design and its source
  (Pydantic AI Harness `WarnOnCacheBusts`) are in
  `../../agent-prompt-cache-health.md` §2.
- **Lineage**: `root_run_id` and `depth` across continuations, and
  `resumes` for a resume. `GET /v1/runs?root_run_id=` is everything one
  request led to. A stage run also carries `pipeline_run_id` and
  `stage`.
- **Ending tools** set `outcome.finished_with` (the tool, the ending's
  name, and any links its result wrote), so a pipeline edge or sink can
  tell which ending was chosen.

---

## 10a. Draft runs on a sandbox

A draft can't run on production; that's what publishing is for. It can
run on a **sandbox deployment**, which is how a configuration is tried
out and how `../eval.md`'s suites run against a change before it ships.

A sandbox is a deployment with `kind: sandbox`
([`examples/sandbox.deployment.json`](./examples/sandbox.deployment.json)).
It has its own tier map and providers. Its `sandbox` block says what
effects do there:

| Effect | Default | Meaning |
|---|---|---|
| sinks | `record` | every delivery is stored with its rendered payload and state `recorded`; nothing is sent |
| ending and built-in effects | `record` | `RequestHelp`'s post, and any tool on a workspace-bound server, are recorded with what they would have done, and the run continues as if they succeeded |
| MCP writes | `deny` | a call to a tool not annotated `read_only` is refused with `sandbox_write_blocked`, unless set to `allow` |
| servers | — | substitutes, e.g. `jira` → `jira-sandbox`, so a sandbox that allows writes writes to test data |

Rules:

- **Who and how.** A sandbox run is started by `POST /v1/runs` with
  `deployment` set to the sandbox, by someone holding `runs:draft` on
  the template. It runs as the caller only: no delegation, no service
  identity, no trigger. Triggers always start published versions on
  production.
- **Everything else is the same.** The same resolution, the same rules,
  the same events and outcome, so a sandbox run is a faithful rehearsal.
  The run record names its deployment and resolved digest, so eval
  results compare like with like.
- **Drafts of anything.** A draft template, pipeline or saved tool group
  can run there, and a draft template can use draft groups and prompts.
  On production every reference must be published
  (`draft_requires_sandbox`).

