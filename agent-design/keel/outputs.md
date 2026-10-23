# Keel: outputs

Results, sinks, continuations, gates and harness actions. Part of [Keel](./README.md). Section numbers are shared across Keel's files, so a reference like §7f means the same section everywhere; [the README](./README.md#files) lists which file holds each.

---

## 7. Outputs: tools, chaining, or something else?

**All three, but they're different things, and the line between them
is who decides.**

| | Decided by | When | Mechanism | Forge examples |
|---|---|---|---|---|
| **Effects** | the model | during the run | a granted **tool** | `AddComment` in plan and review runs; a warehouse write |
| **Result** | the model, inside a contract | at the end | the terminal call → `Run.outcome` | `Complete.report`, `HandOff.reason`, artifacts in `evidence` |
| **Sinks** | the template | after the run, fixed by outcome | harness **delivery** | posting `summary` to the ticket; the attention tier as a commit status; publishing a report |
| **Continuations** | the template declares edges back into itself; the outcome (and sometimes a human) picks one | after the run | another run in the same stage, or a child pipeline run | approve → execute; spinoffs |
| **Pipeline edges** | the pipeline declares them; the outcome picks one | after a stage | the next **stage** | plan → implement; HandOff landings; review → fix |

The rule for effects versus sinks: **if the model decides whether,
what, or where to post, it's a tool. If posting is a fixed consequence
of how the run ended, it's a sink.** Forge already draws this line. Its
`Complete.summary` is "not posted anywhere by Forge itself — whether
and how it reaches a PR, a Jira comment … is the invoking harness's
call" (`../tools.md`). That is a sink. Plan mode's step-5 posting *is* the
model's choice of content, so it's an effect, and
the completion check `require_tool_called` confirms it happened.

### 7a. Result

`Run.outcome`: `terminal` (`complete | suspend | handoff |
infra_failure | stopped`), `status`, `summary`, `report` (validated),
`handoff {reason, why}`, `finisher {id, external_ref}`, `nudged`, the post-run `integrity` checks, a
`refusal` code if the harness ended it, and `report_digest` for
approvals to bind to. Artifacts are listed on the run. Everything
downstream reads this one object, so sinks and continuations never
parse prose.

### 7b. Sinks

`{id, when, kind, channel, render, idempotency_key, retry}`. Kinds:
`comment`, `commit_status`, `webhook`, `chat`, `email`,
`artifact_publish`, `dataset_write`, and `tool`, which calls a declared
tool after the run (a Jira transition) with arguments from the result.
`render` is a Mustache template
over the result, written by the template author, and the output is
Markdown converted per channel. That matches the decision that comment
bodies are always Markdown, with conversion harness-side. Every
delivery is a `Delivery` record with its own retry state, so a Jira
outage loses nothing and can be retried by id. A channel target of
`{origin: true}` is wherever the request came from (the chat thread, the
issue, the PR), which the trigger records as `Run.origin`.

### 7c. Continuations and pipeline edges

There is one rule for every inter-run edge, and two places to write
one. **A continuation is an edge back into the same template**
(`target: self`). **An edge to a different template belongs to a
pipeline** (§7e). The first pass of this spec let a template's
continuations name any template. Use case 0c showed why that's wrong:
`forge.plan` then hard-wired `forge.implement`, and `forge.implement`
would have had to carry "update Jira when done" for every caller,
including callers that don't want it. Templates are now reusable on
their own, and wiring is a separate, versioned thing.

| Edge | Lives in | `on` | to | `carry` | `gate` |
|---|---|---|---|---|---|
| approve → execute (`../formats.md` §5) | template continuation | `suspend`, `answer: approve` | `self` | `approved_action`, `resumed_answer` | `auto` (the gate was the question) |
| `blocks_this` spinoff (`../orchestration.md` §6) | template continuation | `complete`, `blocked`, `spinoff: blocks_this` | a child pipeline run; this stage waits on it | `prior_attempt` | `auto` |
| `follows_this` spinoff | template continuation | `complete`, `spinoff: follows_this` | a child pipeline run | `prior_attempt` | `approval` |
| plan → implement (`../formats.md` §6) | pipeline [`jira.plan-implement`](../forge-on-keel/jira-plan-implement.pipeline.json) | `complete`, `planned` | `implement` | `plan` | `approval`, `bind: plan_hash` (gated), or `auto` (auto-chained) |
| HandOff `too_complex` (`../models.md` §4b) | pipeline [`analysis`](./examples/analysis.pipeline.json) | `handoff`, reason | `investigate` | `prior_attempt` | `auto` |
| HandOff `report_requested` | pipeline `analysis` | `handoff`, reason | `report` | `prior_attempt`, `artifacts` | `auto` |
| review → fix (`../medium.md` §1b) | pipeline [`pr.review-fix`](../forge-on-keel/pr-review-fix.pipeline.json) | `complete`, `done`, an expression on findings | `fix` | `findings` | `approval` by the PR author |

The rules that keep this safe, for both kinds:

- **The model chooses among declared exits. It never names a target.**
  `HandOff.reason` is an enum of the template's declared reasons, and a
  pipeline must wire every one (P2). Run on its own, a template has no
  wired exits, so `HandOff` is not generated. `spun_off` is a proposal
  the edge turns into a child pipeline run. No result field can name a template
  (`continuation_undeclared`). This is `../orchestration.md` §8's
  invariant, "a run may file, propose or report; it may not act on
  what it oversees", stated as a schema.
- **Carry is what crosses, and never a transcript.** The target must
  declare a matching `carry` input (R7, P3), so context crosses only
  through typed envelope blocks, as `../formats.md` §6 already requires.
  The one exception is **resume**, which is neither: a `clarify` answer
  resumes the same template with the suspended run's transcript
  (`Run.lineage.resumes`). It's built in because it's the one case where
  the transcript has to survive.
- **Bounded.** `max_chain_depth` limits a template's own continuations;
  a pipeline's `max_hops` limits its longest path, and its graph must be
  acyclic (P6). Every stage lands at or below the pipeline's `max_tier`
  (P5), and below the deployment ceiling at run time (`tier_ceiling`).
  `../models.md`'s "at most two hand-offs" is `max_hops: 2` on `analysis`.
- **Gated edges open a `Gate`**, which expires after 7 days by default
  and then blocks the waiting stage. Approval gates bind to `report_hash`
  or `plan_hash`, and the approval lapses if the content changes
  (`../formats.md` §5a rule 4).
- **Never someone else's authority.** A continuation's `run_as` is
  `same` or `service`. A pipeline runs every stage as the pipeline
  run's principal, and P7 requires a principal type every stage allows.

**Chaining across owners.** A `run_outcome` trigger (§9) lets one team
start its template or pipeline when another team's finishes, without
editing either. When you own both ends, prefer a pipeline: the edge is
then in a version that was reviewed.

### 7d. Gates

[`gate.schema.json`](./schemas/gate.schema.json). One resource
for everything waiting on a human: `clarify`, `approve_action`,
`edge_approval` and `spinoff_approval`. It holds the question (with `{id, label,
implication}` options and, for approvals, the named action), the
`bound_digest`, the principal set, the channels with the external ref
each reply is matched on, the replies (each with harness-asserted
`from`, `author`, `option_id`, `match`), and a resolution.
`GET /v1/gates?answerable_by=me&state=open` answers "what is waiting on
me" across every template. `POST /v1/gates/{id}/replies` is the single
reply path for the UI and for every channel adapter, which is
`../medium.md` §5c's multi-channel delivery without a new tool.

### 7g. Harness actions, and where a PR gets opened

Keel doesn't decide who opens a PR. A configuration does.
Keel provides **harness actions**: tools the harness implements
rather than an MCP server, addressed `action/<name>`. Like any tool,
an action can sit in any of three positions, and a configuration picks
one per template or pipeline:

| Position | How it's written | Who decides when | Example |
|---|---|---|---|
| **during the run** | the action in a granted group | the model, mid-run | a template that opens a draft PR early so CI runs while it keeps working |
| **as the ending** | a finisher wrapping the action | the model, by choosing that ending; the completion checks run first | `coding.java`'s `OpenPullRequest` |
| **after the run** | a pipeline sink `kind: tool` calling the action, `at` a stage's `run_ended` | the pipeline author, fixed by the outcome | `jira.plan-implement` opens the PR from implement's retained checkout |

A fourth arrangement needs no action at all. An **external committer**
picks up the retained working tree and links the PR back with
`POST …/stages/{stage}:link`. Forge's original design did this.

Whichever position opens the PR, `action/open_pull_request` writes
`links.pull_request` on the stage. So a stage's `settle` watches
`stage.links.pull_request` in every arrangement, and the rest of the
pipeline doesn't care which one the configuration chose. Sinks at the
same moment run in the order declared. `jira.plan-implement` opens the
PR, then moves the ticket to In Review only if a PR was linked.

The rules:

- **The model never runs git writes itself.** The `git_write_blocklist`
  check applies in every position. An action is the only way a push
  happens, and it uses the harness's git identity, signing and PR
  templates.
- **`workspace.git_writes` is about the run's agents only.**
  `via_action` is required when any agent can reach the action, granted
  or wrapped by a finisher, and is an error when none can (R15). `none`
  says no agent of this run can cause a push. It does not stop a
  pipeline from opening a PR from the tree afterwards. That push is the
  pipeline's, declared in its own `tools`, and checked by P9: the stage's
  checkout must be writable and retained.
- **Two actions exist today**:
  - `open_pull_request` (title, body, base, draft, labels);
  - `request_help` (message, channel): as a finisher it ends the run
    `blocked`.

  Argument overrides fix and hide whatever a configuration doesn't want
  the model choosing, such as the base branch or the labels.
