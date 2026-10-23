# Keel

**Keel is a generic agent platform**: the data models, rules and API for
defining agents, running them, wiring them together, and starting them
from events. It knows nothing about coding, tickets or reviews. Those
come from configurations built on it.

**Forge**, the coding and review agent the rest of `agent-design/`
describes, is one such configuration. Its templates and pipelines are in
[`../forge-on-keel/`](../forge-on-keel), and where Forge decides
something (for example, who opens a PR), Keel only provides the means.

**Status: proposal, 2026-10-23.** Terms are defined in
[`taxonomy.md`](./taxonomy.md); every word below means what it says
there.

## Files

| File | Sections | What |
|---|---|---|
| this file | §0–§2 | the four use cases, the concept list, the layers |
| [`run-spec.md`](./run-spec.md) | §3, §6 | What defines a run, and how a template makes it reusable. |
| [`tools-and-agents.md`](./tools-and-agents.md) | §4 | Tool sources, groups, grants, visibility, agents and harness checks. |
| [`endings.md`](./endings.md) | §5 | Generated ending tools, and finishers. |
| [`outputs.md`](./outputs.md) | §7 (7a–7d, 7g) | Results, sinks, continuations, gates and harness actions. |
| [`pipelines.md`](./pipelines.md) | §7e, §7f | Template stages wired together, and the pipeline run as the durable record of work. |
| [`authority.md`](./authority.md) | §8, §12a | Principals, on-behalf-of, delegations, and permissions in the RBAC system. |
| [`triggers-and-runs.md`](./triggers-and-runs.md) | §9, §10 | What starts work, and the life of a run. |
| [`rules.md`](./rules.md) | §11 | The checks a JSON Schema can't express, run at validate and publish. |
| [`api.md`](./api.md) | §12 | The resources and operations, summarised. The wire contract is `openapi.yaml`. |
| [`decisions.md`](./decisions.md) | §14, §15 | What was decided, what it replaced, and what is still open. |
| [`taxonomy.md`](./taxonomy.md) | | one meaning per term |
| [`schemas/`](./schemas) | | JSON Schema (2020-12) for every resource |
| [`openapi.yaml`](./openapi.yaml) | | the API, OpenAPI 3.1 |
| [`examples/`](./examples) | | generic configurations: a saved Java tool group and agent, the analysis pipeline, chat and schedule triggers, servers, a delegation, a deployment |
| [`check.py`](./check.py) | | validates `examples/` and `../forge-on-keel/` against the schemas, then runs the publish rules. `python3 -I agent-design/keel/check.py` |

---

## 0. Four use cases, end to end

Each one is a set of files in `keel/examples/` that `check.py`
passes. The first pass of this spec handled the third and fourth. The
first two exposed three gaps, now closed: saved tool groups with
per-tool settings, finishers, and pipelines.

### 0a. A saved tool group for Java agents, used against a repo

*"I define a tool group for Java coding agents from several MCP servers,
control each tool's visibility, override its params and other settings
to change how the agent sees it, and save it. Then I run an agent with
that group against a repo, with a saved Java prompt and a query with
the task details."*

- **The group** is [`java-coding.tool-group.json`](./examples/java-coding.tool-group.json),
  a `SavedToolGroup`, version 3. It has built-in file and shell tools,
  `maven/run_goal`, two `jdtls` navigation tools, `sonar/search_issues`
  and `jira/get_issue`, and it pins each server's snapshot. Per tool,
  you can set:
  - a new name (`run_goal` → `Maven`);
  - a new description;
  - visibility: the language-server and Sonar tools are `deferred` with
    a search hint, while the rest are `loaded`;
  - annotations and limits;
  - **argument overrides**. For example, `goal` is narrowed to four
    values; `offline`, `settings_file` and `project_dir` are fixed and
    hidden; Sonar's `project_key` is fixed to the run's `repository`
    param; `page_size` is capped at 50 with a default of 20.

  `:preview` shows each tool exactly as the model will see it (§4b).
- **The agent** is [`coding.java`](./examples/coding.java.template.json).
  It uses the group by reference (`{ref: {name: java.coding, version: 3},
  id: java}`), the saved prompt `java.developer@4`, and params for the
  repository, branch, issue and **`task`**. `task` is the starting
  query: an `instruction` input with `trust: principal`.
- **The run** is one request:
  [`run-request.java.json`](./examples/run-request.java.json).
  If you'd rather not save a template first, `POST /v1/runs` also takes
  an `adhoc` body. The harness publishes it as `adhoc.<digest>` and runs
  every publish rule on it, so an ad-hoc run is as checked and as
  auditable as a saved one (§6).

### 0b. Choosing how the run ends: Complete, update Jira, open a PR, ask for help

*"When the task is finished it calls Complete. I could instead have
selected other tools as the final options: update Jira, create a PR,
ask for help. Ask-for-help could also be used during the run."*

`coding.java` sets `completion.complete: false` and declares three
**finishers** (§5a):

- `OpenPullRequest`: wraps the harness action `action/open_pull_request`.
  It commits, pushes and opens the PR under harness-owned git identity,
  which needs `git_writes: via_action`.
- `FinishWithJiraUpdate`: wraps `mcp:jira/update_issue`. The issue key
  is fixed and the transitions are narrowed.
- `RequestHelp`: wraps `action/request_help`. It posts to the team channel and ends
  the run with status `blocked`.

The model sees each one as a tool. Calling it runs the completion checks
first, then the action. If the action fails, the error comes back to
the model and the run continues.

**Ask-for-help is two things, and the spec keeps them apart.** *During*
the run, it's `AskUser`: the run suspends and resumes with the answer
and its context intact. *As an ending*, it's `RequestHelp`: the run is
over and a person takes the task. The tool descriptions tell the model
which is which. Both can be enabled in one template, as they are here.

### 0c. A plan → implement pipeline, triggered by Jira, updating Jira at the end

*"A template for an agent pipeline: a plan job that hands over to an
implement job. Triggered by a Jira ticket being assigned; when it
finishes it updates Jira."*

- **The pipeline** is [`jira.plan-implement`](../forge-on-keel/jira-plan-implement.pipeline.json)
  (§7e). It has two stages, `forge.plan` and `forge.implement`, each
  used unchanged. One edge, `plan_approved`, goes from plan's
  `planned` status to implement. It carries the plan, and it is gated
  on the assignee or reporter approving that exact plan (`bind:
  plan_hash`).
- **The Jira updates** are sinks on the pipeline, not on either
  template. Each is a `tool` sink calling `mcp:jira/update_issue`:
  transition `In Review` when implement's run ends `done`, and `Done`
  when its PR merges. The implement stage **settles** on the PR, which
  the committer links back (§7f). There's also a summary comment
  whichever stage the pipeline ended in. Run on its own,
  `forge.implement` doesn't touch Jira's status. That belongs to this
  pipeline.
- **The trigger** is [`jira-assigned.trigger.json`](../forge-on-keel/jira-assigned.trigger.json):
  `issue.assigned` to `forge-bot`. It runs as the person who assigned
  it (`event_actor`), only if they hold a delegation for this pipeline,
  and replies go to the issue (`origin`).

### 0d. A chat message to a cheap data agent that hands over to a stronger one

*"A user sends a chat message, which triggers a data agent. It starts on
a cheap model with only a few tools, finds the job is harder, and hands
over to a more powerful agent with more tools."*

- **The trigger** is [`chat-data.trigger.json`](./examples/chat-data.trigger.json):
  a `manual` `chat_command`, with `run_as: invoker` and `origin` set to
  the chat thread.
- **The pipeline** is [`analysis`](./examples/analysis.pipeline.json).
  Its entry is `analysis.quick`: economy tier, four tools, the hatches
  from `../models.md`. Its `HandOff` reasons are wired to
  `analysis.investigate` (standard tier, every source, the full tool
  set) and `analysis.report`. Each edge `announce`s to the thread
  ("Taking a closer look…"). The answer goes back to the thread through
  a sink targeting `{origin: true}`, whichever stage produced it.
- **Acting for the user throughout**: `invoker` mints a session
  delegation scoped to this pipeline run (§8). The investigate stage
  can then still query the warehouse as the user after the chat
  request itself has returned.

---

## 1. The concept list, checked

The starting list was: MCP servers, tools, tool groups, tool visibility
and deferral, completion tools, system prompts, starting query, model,
sub-agents, user on-behalf-of. All of them are here. A run needs eleven
more things, and each is something this folder already decided. The
spec just has to give it a field:

| Concept | Where it lives | Already decided in |
|---|---|---|
| MCP servers | `McpServer` registry resource; a spec lists the ones it uses, pinned to a tool snapshot | `../adk.md`, `../tools.md` |
| Tools, tool groups | `ToolRef`, `ToolGroup` (the unit of grant), and `SavedToolGroup`: versioned, reusable across templates, with per-tool argument overrides | `../tools.md` |
| Visibility and deferral | `Visibility` per group, per tool, and overridable per agent; the provider flag sits in deployment | `../tools.md` "Granted, registered, visible" |
| Completion tools | `completion` (with `finishers`), `human.ask_user`, `hatches.handoff`. The harness **generates** these tools (§5) | `../formats.md` §3, §5; `../models.md` §4b |
| **Pipelines** | `Pipeline`: template stages wired exit to entry, with their own sinks | new here, §7e |
| System prompt | `PromptSpec`: versioned fixed text, subtraction by heading, generated blocks | `../system-prompts.md` §6–§7 |
| Starting query | an `inputs[]` entry of kind `instruction`, filled from a param | `../formats.md` §1 |
| Model | a **tier** plus a ceiling. The deployment maps tiers to model ids | `../models.md` §2.5 |
| Sub-agents | `agents`: one orchestrator plus named sub-agents, each with its own grant, tier and prompt | `../tools.md`, `../system-prompts.md` §3–§5 |
| User on-behalf-of | `authority`, server `auth.mode: obo`, `Delegation` | new here, §8 |
| **Inputs other than the query** | `inputs[]`: ticket, diff, comments, plan, prior attempt, approved action. Each is typed and has a trust level | `../formats.md` §1, `../context-files.md` §4 |
| **Standing context** | `context.conventions` (tiers, kinds, paths, at which SHA) | `../context-files.md` §1b |
| **Workspace** | `workspace`: none, or a harness-provisioned checkout with `writable`, `write_scope`, scratch dir, `git_writes: none \| via_action`, `retain` | README decision log, `../orchestration.md` §4 |
| **Budgets** | `budgets`: turns, context high-water mark, wall time, tokens by tier, sub-agent count | `../formats.md` §7, `../models.md` §10 |
| **Harness checks** | `tools.checks`: enforcement that no grant can remove | `../tools.md` "Harness-side checks are not part of the subset" |
| **Human channel** | `human.ask_user` (who may answer, where it goes) and `human.narrate` | `../formats.md` §5a, `../medium.md` §2f, §5c |
| **Hatches and monitors** | `hatches.expand`, `hatches.handoff`, `monitors[]` (what `../models.md` §5 calls harness triggers) | `../models.md` §4–§5 |
| **Outputs** | `outputs.sinks[]` and `outputs.continuations[]` (§7) | new here; unifies several |
| **Concurrency** | `concurrency.key` and a policy | `../orchestration.md` §4 |
| **Durable work** | the pipeline run: per-stage attempts, retries, waits, settling, spinoffs | `../orchestration.md`, which it replaces, §7f |
| **Versioning and pinning** | template versions, tool snapshot digests, pinned continuation targets | new here, §6 |
| **Deployment facts** | `Deployment`: tier→model map, provider capabilities, global ceiling, mandatory checks | `../models.md` §10 open point, now closed |

**One thing on the list is not a concept: `mode`.** "Plan" and
"implement" are two different agent runs, from two templates,
`forge.plan` and `forge.implement`. They behave differently because they
are given different things:

- **tools**: plan's grant has no `Edit`/`Write` and does have
  `AddComment`, and its workspace is read-only;
- **prompt**: `forge.plan@1` versus `forge.implement@1`;
- **model**: strong versus standard;
- **completion contract**: plan can end `planned`; implement has the
  first-`done` checklist and spinoffs;
- **wiring**: the pipeline that runs one after the other.

Nothing in the spec says "you are in plan mode". The two are siblings:
both extend `forge.coding`, a base template marked `runnable: false`
that holds what they share (the ticket input, the checkout, the tool
declaration and checks, authority). Neither is a variant of the other,
and the base can't run on its own. "Mode" survives only as an informal
word for "what a run ends up doing, given its configuration"
([`taxonomy.md`](./taxonomy.md)).

---

## 2. Layers

```
 Deployment ─────────── tier→model map, provider flags, ceilings, mandatory checks
     │
 Registry ───────────── McpServer (+ ToolSnapshot), SavedToolGroup, prompts, report schemas
     │  referenced, pinned by digest
     ▼
 Template@version ───── params + RunSpec        (immutable once published)
     │        │
     │        └──► Pipeline@version ── stages (templates) + edges + pipeline sinks
     │  bind params, resolve for this principal and deployment
     ▼
 Run ────────────────── ResolvedSpec snapshot + state + outcome + usage
     │       ▲                    │                    (a PipelineRun groups stage runs)
     │       │ creates            │ outcome feeds
     │   Trigger ◄── Event        ├──► Sinks           (deliveries)
     │   (schedule, event,        ├──► Continuations   (back into the same template)
     │    run_outcome, manual)    ├──► Pipeline edges  (to the next stage)
     │                            └──► Gates           (a human decides first)
     ▼
 PipelineRun ────────── the durable record of the work: stages, attempts, waits, children
 Delegation ─────────── a user's standing consent for a template to act for them
```

This is a deliberately short chain. A **RunSpec** is everything about a
run. A **Template** is a RunSpec with named holes and a
version. A **Pipeline** wires templates together without changing them.
A **Run** is one template version with the holes filled, under one
principal. A **Trigger** decides when a run or pipeline starts.
**Outputs** decide what the run leads to.

Most of the safety story is in one table: **who may change what, and
when.**

| Thing | Changed by | When | Can it widen authority? |
|---|---|---|---|
| Deployment | operators | any time; applies to runs that start afterwards | it *is* the ceiling |
| McpServer, ToolSnapshot | registry owners | discovery makes a new snapshot; published templates keep theirs | only by a new template version that pins it |
| Template draft | template owners | freely | yes, it's authoring |
| Template version | nobody | never (publish freezes it) | — |
| Params | callers, triggers, continuations | per run | **no**. Params narrow only (§6) |
| Delegation | the user it names | consent and revoke | no, it caps what a template may do for that user |
| Anything the model reads | tickets, PRs, repos, MCP results | during the run | **no**. Data only |
| Anything the model calls | the model | during the run | **no**. Every call is checked at the executor |
