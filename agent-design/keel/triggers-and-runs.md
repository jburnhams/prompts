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
  final-turn nudge at the next turn boundary, so even a cancelled run
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
  narration, harness notes, reveals, the nudge, gates, artifacts, usage,
  outcome, deliveries, follow-ons. Bodies are in the transcript, which
  has its own permission and is audited.
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

