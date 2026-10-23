# Agent platform: data models and APIs

**Status: proposal, 2026-10-23, revised the same day against four use
cases (§0).** This turns the Forge design into resources a service could
store and an API could serve. It doesn't change what Forge does. It says
where each decision already made in this folder lives as data, who may
change it, and when.

| File | What it is |
|---|---|
| this file | the model, the rules, and the reasons |
| [`platform/schemas/`](./platform/schemas) | JSON Schema (2020-12) for every resource |
| [`platform/openapi.yaml`](./platform/openapi.yaml) | the API, OpenAPI 3.1, referencing those schemas |
| [`platform/examples/`](./platform/examples) | Forge's three entrypoints and the quick-analysis path written as templates, plus triggers, servers, a delegation and a deployment |
| [`taxonomy.md`](./taxonomy.md) | the agreed meaning of every term used here, and which words to avoid |
| [`platform/check.py`](./platform/check.py) | validates every example against the schemas, then runs the publish rules in §11. `python3 -I agent-design/platform/check.py` |

---

## 0. Four use cases, end to end

Each one is a set of files in `platform/examples/` that `check.py`
passes. The first pass of this spec handled the third and fourth. The
first two exposed three gaps, now closed: saved tool groups with
per-tool settings, finishers, and pipelines.

### 0a. A saved tool group for Java agents, used against a repo

*"I define a tool group for Java coding agents from several MCP servers,
control each tool's visibility, override its params and other settings
to change how the agent sees it, and save it. Then I run an agent with
that group against a repo, with a saved Java prompt and a query with
the task details."*

- **The group** is [`java-coding.tool-group.json`](./platform/examples/java-coding.tool-group.json),
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
- **The agent** is [`coding.java`](./platform/examples/coding.java.template.json).
  It uses the group by reference (`{ref: {name: java.coding, version: 3},
  id: java}`), the saved prompt `java.developer@4`, and params for the
  repository, branch, issue and **`task`**. `task` is the starting
  query: an `instruction` input with `trust: principal`.
- **The run** is one request:
  [`run-request.java.json`](./platform/examples/run-request.java.json).
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

- `OpenPullRequest`: a harness action. It commits, pushes and opens the
  PR under harness-owned git identity, which needs `git_writes:
  on_finish`.
- `FinishWithJiraUpdate`: wraps `mcp:jira/update_issue`. The issue key
  is fixed and the transitions are narrowed.
- `RequestHelp`: a harness action. It posts to the team channel and ends
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

- **The pipeline** is [`jira.plan-implement`](./platform/examples/jira-plan-implement.pipeline.json)
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
- **The trigger** is [`jira-assigned.trigger.json`](./platform/examples/jira-assigned.trigger.json):
  `issue.assigned` to `forge-bot`. It runs as the person who assigned
  it (`event_actor`), only if they hold a delegation for this pipeline,
  and replies go to the issue (`origin`).

### 0d. A chat message to a cheap data agent that hands over to a stronger one

*"A user sends a chat message, which triggers a data agent. It starts on
a cheap model with only a few tools, finds the job is harder, and hands
over to a more powerful agent with more tools."*

- **The trigger** is [`chat-data.trigger.json`](./platform/examples/chat-data.trigger.json):
  a `manual` `chat_command`, with `run_as: invoker` and `origin` set to
  the chat thread.
- **The pipeline** is [`analysis`](./platform/examples/analysis.pipeline.json).
  Its entry is `analysis.quick`: economy tier, four tools, the hatches
  from `models.md`. Its `HandOff` reasons are wired to
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
| MCP servers | `McpServer` registry resource; a spec lists the ones it uses, pinned to a tool snapshot | `adk.md`, `tools.md` |
| Tools, tool groups | `ToolRef`, `ToolGroup` (the unit of grant), and `SavedToolGroup`: versioned, reusable across templates, with per-tool argument overrides | `tools.md` |
| Visibility and deferral | `Visibility` per group, per tool, and overridable per agent; the provider flag sits in deployment | `tools.md` "Granted, registered, visible" |
| Completion tools | `completion` (with `finishers`), `human.ask_user`, `hatches.handoff`. The harness **generates** these tools (§5) | `formats.md` §3, §5; `models.md` §4b |
| **Pipelines** | `Pipeline`: template stages wired exit to entry, with their own sinks | new here, §7e |
| System prompt | `PromptSpec`: versioned fixed text, subtraction by heading, generated blocks | `system-prompts.md` §6–§7 |
| Starting query | an `inputs[]` entry of kind `instruction`, filled from a param | `formats.md` §1 |
| Model | a **tier** plus a ceiling. The deployment maps tiers to model ids | `models.md` §2.5 |
| Sub-agents | `agents`: one orchestrator plus named sub-agents, each with its own grant, tier and prompt | `tools.md`, `system-prompts.md` §3–§5 |
| User on-behalf-of | `authority`, server `auth.mode: obo`, `Delegation` | new here, §8 |
| **Inputs other than the query** | `inputs[]`: ticket, diff, comments, plan, prior attempt, approved action. Each is typed and has a trust level | `formats.md` §1, `context-files.md` §4 |
| **Standing context** | `context.conventions` (tiers, kinds, paths, at which SHA) | `context-files.md` §1b |
| **Workspace** | `workspace`: none, or a harness-provisioned checkout with `writable`, `write_scope`, scratch dir, `git_writes: deny` | README decision log, `orchestration.md` §4 |
| **Budgets** | `budgets`: turns, context high-water mark, wall time, tokens by tier, sub-agent count | `formats.md` §7, `models.md` §10 |
| **Harness checks** | `tools.checks`: enforcement that no grant can remove | `tools.md` "Harness-side checks are not part of the subset" |
| **Human channel** | `human.ask_user` (who may answer, where it goes) and `human.narrate` | `formats.md` §5a, `medium.md` §2f, §5c |
| **Hatches and monitors** | `hatches.expand`, `hatches.handoff`, `monitors[]` (what `models.md` §5 calls harness triggers) | `models.md` §4–§5 |
| **Outputs** | `outputs.sinks[]` and `outputs.continuations[]` (§7) | new here; unifies several |
| **Concurrency** | `concurrency.key` and a policy | `orchestration.md` §4 |
| **Durable work** | the pipeline run: per-stage attempts, retries, waits, settling, spinoffs | `orchestration.md`, which it replaces, §7f |
| **Versioning and pinning** | template versions, tool snapshot digests, pinned continuation targets | new here, §6 |
| **Deployment facts** | `Deployment`: tier→model map, provider capabilities, global ceiling, mandatory checks | `models.md` §10 open point, now closed |

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

---

## 3. The RunSpec

Schema: [`run-spec.schema.json`](./platform/schemas/run-spec.schema.json).
It was called `AgentSpec` until "agent" came to mean one model context
inside a run ([`taxonomy.md`](./taxonomy.md)).
The fields, with the reason each is shaped the way it is:

- **`model`**: `tier`, optional `effort`, and `max_tier`. The ceiling
  applies to this run and to every continuation from it, so a handoff
  chain can't climb above it (`models.md` §5, "escalation is clamped by
  config"). `max_tier` is never bindable.
- **`system_prompt`**: `base` is a versioned prompt ref (or inline text).
  `omit_sections` is subtraction by heading, the only variation the
  README's per-model-prompt decision allows. `generated` lists the
  harness blocks (`env`, `capabilities`, `git_status`, `repo_context`,
  `data_overview`), in order. No field accepts a param (§6).
- **`inputs[]`**: the task envelope as an ordered list of tagged blocks.
  Each one has a `kind`, a `source` and a `trust`. There are four kinds
  of source:
  - `param`: the starting query, a manual instruction.
  - `fetch`: pre-fetched through a declared tool before turn 0, like
    the ticket in `formats.md` §1a.
  - `carry`: filled only by a continuation or a resume: plan, prior
    attempt, approved action, resumed answer, findings.
  - `builder`: a harness component, such as the review diff builder or
    the comment-thread model.

  Anything not authored by `harness` or `config` is sanitised and
  nonce-wrapped.
- **`context`**: the context-service resolution (`tiers`, `team`,
  `paths`, `kinds`, `at: base_sha` for review) and, for analysis, the
  data overview. A failed resolution means the run doesn't start, as
  `context-files.md` §1b already says.
- **`workspace`**: `none`, or `checkout`. `writable: false` registers no
  write tools for any agent, whatever the grants say (rule R9 rejects
  the contradiction at publish). `git_writes` has one value, `deny`.
- **`tools`**: the job's declaration (§4).
- **`agents`**: `orchestrator` plus named sub-agents (§4c).
- **`human`**, **`completion`**, **`hatches`**: these generate tools (§5).
- **`monitors[]`**: `models.md` §5's "harness triggers" table as data,
  renamed so that "trigger" only ever means what starts a run. Each is a
  signal (consecutive errors on a tool, zero rows, turns without an
  answer, an unlisted source named, a request matching keywords) and an
  action (hand off, reveal a group, add a harness note, skip to a
  landing before turn 0).
- **`budgets`**: crossing `turns` or `context_high_water_tokens` triggers
  the final-turn nudge. `tokens_by_tier` counts the run and its children
  together, so spend can't hide in a cheap child (`models.md` §10).
- **`outputs`**: sinks and continuations (§7).
- **`authority`**: who the run may act for (§8).
- **`concurrency`**: from `orchestration.md` §4; held through a stage's
  settle wait (§7f).

### 3e. Deployment

[`deployment.schema.json`](./platform/schemas/deployment.schema.json).
The tier map, provider capabilities (`deferred_tools: native | client |
none`, cache minimum, advisor), the global `max_tier`, default budgets,
and checks added to every template that no template can remove. This is
where `models.md` §10's open point ("the tier→model mapping … needs a
home") lands. It isn't in the template, because the same template should
run on Bedrock and on the Anthropic API without a new version.

---

## 4. Tools

Schema: [`tools.schema.json`](./platform/schemas/tools.schema.json).

### 4a. Sources

There are three namespaces in a tool address:

- `builtin/Read`: in-process harness tools (`Read`, `Edit`, `Write`,
  `Bash`, `Grep`, `List`, `InspectImage`).
- `mcp:<server>/<tool>`: anything served by a registered MCP server.
- `harness/<Tool>`: tools generated from contracts (§5). These can't be
  referenced in a group, so no one can grant `Complete` to a sub-agent.

An `McpServer` records the transport, the pinned protocol version
(capped at what the SDK speaks, `adk.md` §0), the auth mode (§8),
whether its `instructions` text is ignored or included as untrusted
context, a description cap, the two-axis limits from `cloudflare.md`
§2d, an egress allowlist for stdio processes, and a **tool snapshot**.

**Snapshots exist because a server's tool list can change under you.**
`:discover` stores the `tools/list` result with digests of each
description and input schema. A template version pins a digest at
publish. At run start the harness compares the live list with the pin.
A changed input schema or annotation always refuses (`tools_drift`).
`drift_policy` decides whether removals or description-only changes are
tolerated. Without this, a published, reviewed template could quietly
gain a tool, or keep a tool whose arguments changed meaning, the day a
server redeploys.

### 4b. Groups, grants and visibility

A `ToolGroup` is a named set of `ToolRef`s (with `include` for
composition). A `ToolRef` can:

- rename a tool for the model (`alias`: `mcp:jira/get_issue` becomes
  `FetchJira`);
- replace its description;
- set its visibility, overriding the group's;
- set limits and override annotations;
- override its **arguments** (`params`).

`mcp:x/*` is allowed in drafts and is expanded against the snapshot,
then frozen, at publish.

**A group can be inline in a spec, or saved.** A `SavedToolGroup` is a
registry resource with a name, a version, an owner and the server
snapshots it pins. A spec uses it as `{ref: {name, version}, id}`, and
publishing inlines it, so the resolved spec has one shape whichever way
it was written. The saved group brings its servers into the template's
declaration. A fixed argument written as `{"$param": "repository"}`
must be a param of every template that uses the group, and R4 checks it
there like any other config binding. `:preview` returns each tool as
the model will see it.

**Argument overrides change what the model sees and can only narrow
what it can do.** Per argument, a `ParamOverride` can:

- replace `description` or `default`;
- make it `required`;
- narrow it: `enum` to a subset, a lower `maximum` or a higher
  `minimum`, a `max_length`, a `pattern`;
- **fix** it: a literal, a config param, or an expression over the run.
  A fixed value is supplied by the harness, and `hidden: true` removes
  the argument from the model's schema entirely. `hidden` requires
  `fixed`, so a call never depends on a server default the author
  didn't choose.

The executor validates the model's arguments against the overridden
schema, merges the fixed values, then validates the result against the
server's own schema. R13 is checked against the pinned snapshot at
publish: an enum must be a subset of the server's, a maximum can only go
down. Narrowing is what makes overrides safe to hand to template
authors. Renaming an argument is not supported. It would need a
two-way mapping in every error the server returns, and nothing in the
use cases needs it.

**Annotations are authoritative from the job, hints from the server**,
and an override may only make a tool look more dangerous. An
unannotated MCP tool is treated as destructive, non-idempotent and not
concurrency-safe, which is MCP's own default for `destructiveHint`.
`retry` defaults to `never` unless the tool is idempotent: `adk.md` §4's
finding that retries make non-idempotent tools dangerous, as a field.

`tools.md`'s three questions map onto three fields:

| Question | Field | Enforced |
|---|---|---|
| Granted | `agents.<a>.grant[]` (+ `kind_grants` for the kind given at spawn) ⊆ `tools.groups` | at the executor, every call |
| Registered | derived at resolve: grant + generated tools, as one fixed array per agent (`ResolvedSpec.agents.<a>.registered`) | provider validation |
| Visible | `ToolGroup.visibility`, overridden by `agents.<a>.visibility` | nothing; it shapes what the model tries |

`hidden` groups need a way to become visible: `hatches.expand.reveals`
or a monitor's `reveal`. R8 warns when a hidden group has
neither. How "deferred" and "hidden" are realised depends on the
provider flag in deployment: `defer_loading` on Anthropic,
`tool_search`/`additional_tools` on OpenAI, and on Bedrock `Converse`
either everything loads upfront or the once-only array growth that
`hatches.expand.array_growth` permits (`models.md` §4a). The spec
states intent. The resolver picks the mechanism and records it in
`ResolvedSpec.agents.<a>.deferred_tools`.

### 4c. Agents

An **agent** is one model context inside a run. Every run has an
`orchestrator`, and may have named sub-agents. ("Role" is not used for
this: it means an RBAC role, §12a.)

Every agent has a `grant`, optional `visibility` overrides, a `model`,
and `spawns` (which sub-agents it may launch). A non-empty `spawns`
generates `Task`, with `subagent_type` limited to those sub-agents and
each one's `description` as the enum text. Sub-agents add:

- a `prompt`;
- `spawn_kinds`: the kinds a spawner may pass. Forge's v1 `Task` schema
  carries the kind in a field it calls `role`; the platform's generated
  `Task` calls it `kind`;
- `kind_grants`: the tool half of "kinds: one vocabulary, three
  resolutions";
- `spawn_args`: extra required `Task` fields, such as the validator's
  `finding`;
- a `report_schema` the harness validates.

The rules from `tools.md` §"One job declares the tools", and where each
is enforced:

- **Siblings, not a chain.** Every agent's grant is checked against
  `tools.groups`, not against its spawner's grant (R1). A data
  sub-agent can hold a server the orchestrator never sees.
- **Only the job grants.** Kind→tools lives in `kind_grants`, which is
  template config. A conventions file can tag sections with kinds. It
  can't add a `kind_grants` entry.
- **No delegate has a human channel.** `human`, `completion` and
  `hatches` generate tools for the orchestrator only, and `harness/`
  tools can't be put in a group.
- **No recursion in v1.** Sub-agent `spawns` has `maxItems: 0`. That's
  a constant to relax, not a structure to add.
- **Children never run above their parent unless the template says
  so.** `clamp_to_parent` defaults to true. The review validator sets it
  false on purpose: it runs `strong` under a `standard` orchestrator
  (`models.md` §7). That is a template author's decision, visible in the
  file, never a runtime one.

### 4d. Harness checks

`tools.checks[]` plus `Deployment.defaults.checks`: `input_sanitizer`,
`git_write_blocklist`, `read_before_edit`, `read_name_blocklist`,
`completion_checklist`, `post_run_crosscheck`, `conventions_write_flag`,
`secret_scan`, `egress_allowlist`, `anchor_validation`. They aren't
part of any grant, so no agent, param or prompt can remove them, and
they apply to every agent. Goose's sub-agents running with no hooks
(`../agent-subagent-architectures.md` §7d) is the failure this is
shaped against.

---

## 5. Completion tools: separate tools, or a flag on a tool?

**Neither. The spec declares a contract, and the harness generates the
tool.** Authors don't write `Complete`, and they can't mark an arbitrary
tool as run-ending.

| Contract in the spec | Generated tool | Ends the run? | What the harness does on the call |
|---|---|---|---|
| `completion` | `harness/Complete` (or `tool_name`), unless `complete: false` | yes: `complete` | validates `report` against `report_schema`, runs the completion `checks`, files spinoffs, evaluates sinks and continuations |
| `completion.finishers[]` | one tool per finisher, under its `name` | yes: `complete`, with `outcome.finisher` set | completion checks, then the wrapped tool or harness action; on failure, back to the model (§5a) |
| `human.ask_user` | `harness/AskUser` | yes: `suspend` | opens a gate, posts to `channels`, records who may answer |
| `hatches.handoff` | `harness/HandOff`, its `reason` enum = the declared reason ids | yes: `handoff` | starts the continuation wired to that reason |
| `hatches.expand` | `harness/Expand` | no | reveals granted groups and sources |
| `agents.*.spawns` | `harness/Task` | no | spawns a sub-agent under its own grant |
| `human.narrate` | `harness/Narrate` | no | appends to the run narrative |

Why not a `terminal: true` flag that authors could set on any tool:

1. **Ending a run is harness behaviour, not tool behaviour.** It means
   exclusivity in the turn (`terminal_not_exclusive`), the final-turn
   nudge naming exactly the allowed terminals, the first-`done`
   checklist, the post-run cross-check, and the outcome on the run
   record. A flag would put the trigger for all of that on a tool whose
   implementation is somewhere else, possibly an MCP server.
2. **A remote server must not be able to end your run, or decide its
   status.** With a flag, a server's tool would be one annotation away
   from doing that.
3. **The report is validated by the harness, against a schema the
   template owns.** If the terminal were a server tool, the server would
   validate it.
4. **The calling convention is stated once.** `models.md` §4c
   principle 7: `Complete`, `AskUser` and `HandOff` share one rule
   ("calling it is the last thing you do"), which is only stated once if
   one component owns all three.

Authors do control everything that differs between agents: the tool
name, the allowed `statuses`, the `report_schema`, the `summary` cap,
which completion `checks` run, whether spinoffs are allowed, and which handoff
reasons exist and what situation each describes. That is the whole of
what Forge's three entrypoints vary.

**`form: "text"`** covers the quick analysis run (`models.md` §3): the
run ends on an assistant message with no tool calls, with status
`done`, and that message becomes `outcome.summary`. R5 limits it to
specs with no report schema, completion checks, spinoffs or finishers, because
there's nothing to validate.

### 5a. Finishers: choosing the ending from a set of tools

Use case 0b asks for the opposite of a generic `Complete`: pick some
real tools (update Jira, open a PR, ask for help) and make *those* the
ways a run can end. That is a **finisher**: an entry in
`completion.finishers` naming a declared tool or a harness action, the
status it ends with, and whether it takes a report.

This keeps the reasons above intact, because the termination is still
the harness's, not the tool's. The tool doesn't know it's a finisher,
and the same MCP tool can be a finisher in one template and an ordinary
mid-run tool in another. What the author marks is the *ending*, in the
contract, which is the right place for it.

- **The model sees a separate generated tool.** It takes `summary`,
  `report` when `report: true`, and `args`: the wrapped tool's
  arguments with the finisher's and the `ToolRef`'s overrides applied.
  The arguments are nested under `args` so that no server argument can
  collide with `summary`. That costs a nested object in the call, which
  `agent-tool-implementations.md` §3g measures as slightly less reliable
  to emit, and it's the price of not reserving names in every server's
  schema.
- **Completion checks run before the action, not after.** The
  first-`done` checklist, `report_crosscheck` and the rest fire on the
  finisher call.
  A PR is opened, or Jira is moved, only after they pass. For an
  irreversible action that order is the whole point.
- **A failed action doesn't end the run.** The error goes back to the
  model with a `finisher_failed` refusal code, and the run continues:
  it can fix the problem, or pick another ending.
- **A finisher's tool is declared, not granted.** `FinishWithJiraUpdate`
  wraps `mcp:jira/update_issue`, which `coding.java` declares in a group
  it grants to nobody. The model can move the ticket as its ending, and
  can't do it halfway through. Granting it as well would allow both,
  under two different names (R11).
- **Two harness actions exist today.**
  - `open_pull_request` commits, pushes and opens the PR with the
    harness's git identity, signing and templates. It needs
    `workspace.git_writes: on_finish` (R14). This is the platform form
    of Forge's "the committer downstream does it": the model never runs
    a git write itself, and the push happens only after the checks, from
    the harness. Forge's own templates keep `deny` and the external
    committer.
  - `request_help` posts the report to a channel and ends with status
    `blocked`. Nothing resumes.
- **`complete: false`** removes the generic `Complete`. The run can
  then end only through a finisher, `AskUser`, `HandOff`, or the
  final-turn nudge, which lists exactly the endings that exist.

**Ask for help during the run, or as the ending.** These are
different, and both are useful. `AskUser` mid-run suspends and resumes
the same task with its context, which is right for a question. A
`request_help` finisher ends the run and hands the task to a person,
which is right when no single answer would unblock it. Their
descriptions say so, because the model choosing between them is the
point.

---

## 6. Templates and params

Schema: [`template.schema.json`](./platform/schemas/template.schema.json).

A template is `{name, version, params, spec}`, optionally `extends` one
published parent. Versions are numbered. Drafts are mutable. Publishing
does all of this:

- flattens `extends` (objects deep-merge, arrays replace, `null`
  deletes);
- expands tool wildcards against pinned snapshots;
- resolves `version: "pinned"` continuation targets to concrete
  versions;
- generates harness tools per agent;
- runs the rules in §11;
- computes three digests: the spec, the fixed prompt text per agent,
  and each server snapshot.

After that the version never changes.

**Params are typed, and their `trust` decides where they may bind.**
Placeholders are structural (`{"$param": "issue_key"}`), allowed only in
fields the schema marks bindable. There's no string interpolation
anywhere.

| `trust` | Typical source | May bind to | Must be |
|---|---|---|---|
| `external` | event text, a PR title | an input (`inputs[].source.param`) only | — |
| `principal` | the user's question, a manual instruction | an input only | — |
| `config` | an issue key, a repo, a branch, a tier, a budget, a kinds list | config slots: workspace, context paths/kinds, model tier, budgets | constrained: `enum`, `pattern`, `subset_of`, `maximum` or `max_tier` |

Not bindable at all: `system_prompt`, `tools`, `agents`, `completion`,
`hatches`, `authority`, `monitors`, `model.max_tier`. That is
R4. It's the reason "params narrow, never widen" holds: every
config-bound param has a declared ceiling, and the fields that grant
anything take no params.

**Two consequences worth wanting:**

- **One cacheable prefix per template version.** Params never reach
  the system prompt, and the tools array per agent is fixed at publish
  (up to the deployment's tier map). So every run of a version shares
  the same tools-plus-system prefix, and the cache is shared across
  runs, not just within one. `Template.resolved.prompt_digest` names it.
- **`:render`** shows exactly what a model would be given for a set of
  params (tools array, visibility, rendered prompt, envelope with
  placeholder nonces) without running anything. It's what you diff when
  someone asks why a run behaved the way it did.

**Ad-hoc runs** (use case 0a's "just run it"): `POST /v1/runs` with
`adhoc: {params, spec}` instead of `template`. The harness publishes the
body as `adhoc.<digest>`, a content-addressed version (the same body is
the same version and shares its prompt cache), runs every rule, then
runs it. The body can reference saved tool groups and saved prompts like
any template. It needs a `runs:adhoc` permission, because it skips the
review a named template gets. It never skips a rule.

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
call" (`tools.md`). That is a sink. Plan mode's step-5 posting *is* the
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
| approve → execute (`formats.md` §5) | template continuation | `suspend`, `answer: approve` | `self` | `approved_action`, `resumed_answer` | `auto` (the gate was the question) |
| `blocks_this` spinoff (`orchestration.md` §6) | template continuation | `complete`, `blocked`, `spinoff: blocks_this` | a child pipeline run; this stage waits on it | `prior_attempt` | `auto` |
| `follows_this` spinoff | template continuation | `complete`, `spinoff: follows_this` | a child pipeline run | `prior_attempt` | `approval` |
| plan → implement (`formats.md` §6) | pipeline [`jira.plan-implement`](./platform/examples/jira-plan-implement.pipeline.json) | `complete`, `planned` | `implement` | `plan` | `approval`, `bind: plan_hash` (gated), or `auto` (auto-chained) |
| HandOff `too_complex` (`models.md` §4b) | pipeline [`analysis`](./platform/examples/analysis.pipeline.json) | `handoff`, reason | `investigate` | `prior_attempt` | `auto` |
| HandOff `report_requested` | pipeline `analysis` | `handoff`, reason | `report` | `prior_attempt`, `artifacts` | `auto` |
| review → fix (`medium.md` §1b) | pipeline [`pr.review-fix`](./platform/examples/pr-review-fix.pipeline.json) | `complete`, `done`, an expression on findings | `fix` | `findings` | `approval` by the PR author |

The rules that keep this safe, for both kinds:

- **The model chooses among declared exits. It never names a target.**
  `HandOff.reason` is an enum of the template's declared reasons, and a
  pipeline must wire every one (P2). Run on its own, a template has no
  wired exits, so `HandOff` is not generated. `spun_off` is a proposal
  the edge turns into a child pipeline run. No result field can name a template
  (`continuation_undeclared`). This is `orchestration.md` §8's
  invariant, "a run may file, propose or report; it may not act on
  what it oversees", stated as a schema.
- **Carry is what crosses, and never a transcript.** The target must
  declare a matching `carry` input (R7, P3), so context crosses only
  through typed envelope blocks, as `formats.md` §6 already requires.
  The one exception is **resume**, which is neither: a `clarify` answer
  resumes the same template with the suspended run's transcript
  (`Run.lineage.resumes`). It's built in because it's the one case where
  the transcript has to survive.
- **Bounded.** `max_chain_depth` limits a template's own continuations;
  a pipeline's `max_hops` limits its longest path, and its graph must be
  acyclic (P6). Every stage lands at or below the pipeline's `max_tier`
  (P5), and below the deployment ceiling at run time (`tier_ceiling`).
  `models.md`'s "at most two hand-offs" is `max_hops: 2` on `analysis`.
- **Gated edges open a `Gate`.** Approval gates bind to `report_hash`
  or `plan_hash`, and the approval lapses if the content changes
  (`formats.md` §5a rule 4).
- **Never someone else's authority.** A continuation's `run_as` is
  `same` or `service`. A pipeline runs every stage as the pipeline
  run's principal, and P7 requires a principal type every stage allows.

**Chaining across owners.** A `run_outcome` trigger (§9) lets one team
start its template or pipeline when another team's finishes, without
editing either. When you own both ends, prefer a pipeline: the edge is
then in a version that was reviewed.

### 7d. Gates

[`gate.schema.json`](./platform/schemas/gate.schema.json). One resource
for everything waiting on a human: `clarify`, `approve_action`,
`edge_approval` and `spinoff_approval`. It holds the question (with `{id, label,
implication}` options and, for approvals, the named action), the
`bound_digest`, the principal set, the channels with the external ref
each reply is matched on, the replies (each with harness-asserted
`from`, `author`, `option_id`, `match`), and a resolution.
`GET /v1/gates?answerable_by=me&state=open` answers "what is waiting on
me" across every template. `POST /v1/gates/{id}/replies` is the single
reply path for the UI and for every channel adapter, which is
`medium.md` §5c's multi-channel delivery without a new tool.

### 7e. Pipelines

[`pipeline.schema.json`](./platform/schemas/pipeline.schema.json). A
pipeline is versioned like a template: `{name, version, params, entry,
stages, edges, sinks, tools, max_hops, max_tier}`.

- **Stages are templates, used unchanged.** A stage names a template
  (`version: "pinned"` resolves at publish) and binds its params from
  `pipeline.params`, `origin` and `principal`. An edge into a stage can
  add params from the previous `result`. For example, implement's
  `write_scope` comes from the plan's report. P4 checks every route into
  every stage binds its template's required params.
- **Edges wire exits.** `on` names exactly one exit of the `from` stage:
  a status, a finisher id, a HandOff reason, or a gate answer, plus an
  optional expression. P2 checks every exit named is one that template
  really has, and every HandOff reason is wired.
- **Pipeline sinks run once, when the pipeline ends**, with `stage` and
  `result` set to the last stage's. The Jira update in use case 0c and
  the chat answer in 0d are pipeline sinks, so whichever stage ends the
  pipeline, the person hears back once, in one place. A pipeline that
  calls tools in its sinks declares them in its own `tools`. That
  declaration is never granted to a stage (P8).
- **`announce`** posts a line to the origin channel when an edge is
  taken. This is `models.md` §4c's "what the user sees" row ("Taking a
  closer look"), now on the edge that causes it.
- **A `PipelineRun`** is the durable record of the work (§7f): the
  principal, delegation, origin and subject, a record per stage entered,
  child runs, the final outcome and the deliveries. Each attempt at a
  stage is an ordinary `Run` with `pipeline_run_id`, `stage` and
  `attempt` set, and its own events stream.

**Not a workflow engine.** There are no loops, no parallel branches and
no joins. Each stage ends in one exit, and at most one edge fires, so
the run is always a path through the graph. Fan-out lives inside a run,
where Forge already has it (`Task`, the review team). Nothing in the
use cases needs more, and a join would have to answer what "both stages
done" means when one was gated and the other wasn't.

### 7f. Pipeline runs are the durable record

There is no ledger. Everything `orchestration.md` designed a ledger
for is a property of a pipeline run. **Every run belongs to one**: a
template run on its own is a one-stage pipeline run named after the
template. The cost on the quick chat path is one row written before the
first turn, and the dispatcher starts the stage at once rather than on a
polling cycle.

A pipeline run holds one **stage record** per stage it entered. Each
record has:

- `state`: `ready`, `running`, `waiting`, `settling`, `blocked`, `done`
  or `abandoned`;
- its frozen params;
- its **attempts**, each one run, with its cause (`entered`, `retry`,
  `resume`, `approved_action`, `dependency_cleared`), terminal, status
  and summary;
- `waiting_on`, when it's waiting;
- `links` written back from downstream;
- the last outcome, and the concurrency key it holds.

Where each ledger job now lives:

| `orchestration.md` (ledger) | Pipeline run |
|---|---|
| `attempts`, `max_attempts`, retry with a raised budget on `budget_exhausted` | the stage's `retry`: `max_attempts`, which ending statuses retry (by default `budget_exhausted`, `infra_failure` and a lost lease, but not `failed`), `raise_budgets` multipliers capped by the params' maxima. The previous attempt's report rides in as `prior_attempt`, so the persistence rule still spans attempts |
| `handoff` until the PR merges or closes | the stage's `settle`. A `done` run moves the stage to `settling`. The committer links the PR (`POST …/stages/{stage}:link`); merged → `done`, closed unmerged → `abandoned`. The concurrency key is held throughout (`held_while_settling`). `link_within_s` flags the case where the committer never ran |
| `parked` with a wake predicate | `waiting_on`: a gate, a child pipeline run, a settle event, a concurrency key held elsewhere, or a timer |
| `depends_on` from a `blocks_this` spinoff | the spinoff is a **child pipeline run** of the same template. The parent stage waits on it, and when it's done the parent gets a new attempt with `spinoff_report` carried in. If the child is abandoned, the parent stage is blocked with `dependency_abandoned` |
| `follows_this` spinoff, gated | a child pipeline run that starts only after a `spinoff_approval` gate. The parent doesn't wait |
| caps: 2 per run, depth 0, 8 per ticket | `completion.spinoffs.max_per_run`, the pipeline's `limits.spinoff_depth` and `limits.runs_per_subject` |
| one task per owner, `handoff` occupied | the template's concurrency key, taken per stage and held while settling. Read-only stages declare none, so they never queue behind implementation |
| health as queries, not a supervisor | `GET /v1/pipeline-runs?health=`: `stranded`, `waiting_stale`, `unlinked`, `repeated_failure`, `orphan_dependency`. These are still stored-field checks: nothing reads task text and decides |
| lease taken by the harness, never by the run | unchanged. The run never sees its pipeline run, its stage record or a lease |
| tracker reconciliation (§10a: adopt, stop, say) | unchanged rules, applied to the pipeline run's `subject`. A ticket closed under a running stage lets the run finish, delivers its report, then abandons with `ticket_closed`. A reopened ticket starts a new pipeline run with `supersedes`, and the old one is never resurrected |
| tracker updates on four transitions | stage-timed pipeline sinks: `at: {stage, event: run_ended \| settled \| blocked \| abandoned}` |

Two things are **not** carried over. A pipeline run can't be filed by
hand as an empty obligation: work starts by running something. And the
"one task, many unrelated runs sharing a ticket key" picture is gone.
Retries are attempts at a stage, follow-on work is a child run, and both
are visible on one record.

The invariant stays exactly as it was, under its new subject: **a run
may file, propose or report; it may not act on what it oversees.** A
run proposes spinoffs in its report, and the pipeline starts them. A
run never sees, retries, settles or abandons its own pipeline run.

---

## 8. Principals and on-behalf-of

Every run records three identities:

| Field | Meaning | Example |
|---|---|---|
| `principal` | on whose behalf it acts; whose authority downstream systems check | the engineer who moved the ticket |
| `requested_by` | who caused it | the API caller, the trigger owner, the person who approved a gate |
| `actor` | the agent's own identity, as it appears in downstream audit logs | `forge-bot` |

**Effective authority = template grant ∩ principal entitlement ∩
delegation scopes.** The template says what the job may ever do. The
principal's own permissions bound it to what that person could do. A
delegation, if one is used, narrows it further.

How the intersection is enforced depends on the server's auth mode:

- **`obo`**: the credential broker exchanges the principal's credential
  for an audience-scoped token, per call (RFC 8693 token exchange).
  Downstream enforces the principal's entitlement. The token never
  enters context. This is the default for anything user-facing; it's
  what makes `Expand` able to reveal only "what the user is already
  granted" (`models.md` §4a) without the harness keeping a copy of
  everyone's permissions.
- **`service`**: calls run as the service principal. Downstream sees
  `forge-bot` and enforces nothing about the user. That's correct for
  review runs, which belong to no user, and it's a **confused deputy**
  in any template a user may run: they would act with the bot's rights,
  not their own. R12 rejects a template that a user may run
  (`authority.run_as` includes `user`) and that grants a non-read-only
  tool on a service-credentialed server, unless the server declares
  `entitlement_check: harness_policy`. With that set, the harness checks
  the principal against the resource before each write call.
- **`none`**: public or local tools.

**Delegation is how a user acts while absent.** A schedule at 07:47 on a
Monday, a Jira event, or a continuation that starts after the user has
gone home has no live session to exchange. A `Delegation` is the user's
stored consent:

- it is for one template or one pipeline, from `min_version`;
- it carries OBO scopes per server, within what the template declares;
- it can constrain params ("only repository X");
- it carries `consented_spec_digest`, a digest of the servers, scopes
  and write tools the user was shown;
- it has an expiry, capped by the template's `max_ttl_days`.

A later template version whose consent-relevant digest differs needs
re-consent (`:publish` lists the delegations affected). A delegation is
created only by the user it names, in an interactive session, because
the IdP may need them to approve the scopes. Revoking it is immediate.

Triggers choose `run_as`:

- `service`: the review trigger.
- `delegation`: the weekly digest. It names a delegation its owner
  granted.
- `event_actor`: the Jira trigger. The person who assigned the ticket
  is the principal, but only if they hold a delegation for this
  pipeline; otherwise `fallback: refuse`. This is deliberately not "run as
  whoever commented". Mapping a provider account to an IdP subject is
  necessary, and it isn't sufficient: consent is still needed.
- `invoker`: the chat trigger, and `manual` sources only. The user is
  present, so no stored consent is needed. But a pipeline's later stages
  may outlive the chat request, so the harness mints a **session
  delegation**: scoped to this one pipeline run, the user's current
  session scopes, the template's or pipeline's declared scopes, and
  expiring when the pipeline run ends or at a cap. It's created from the
  live session, so there is nothing for the user to approve, and it
  can't be reused by any other request.

**Gates use the same identities.** Who may answer is a
`PrincipalSetRule` list (`principal`, `requested_by`,
`issue_assignee`, `issue_reporter`, `pr_author`, `trigger_owner`, a
named principal, an RBAC team). It's resolved when the reply arrives,
not when the question was asked, exactly as `formats.md` §5a specifies.
An empty resolved set is said in the posted question.

---

## 9. Triggers

[`trigger.schema.json`](./platform/schemas/trigger.schema.json). A
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
runs, held while the stage settles on its PR (`orchestration.md` §4's
`handoff` rule, §7f). A
running run is never cancelled by either.

The wait conditions in `medium.md` §4c (`jira`, `build`, `pr`,
`timer`) are a stage's `waiting_on` and `settle` (§7f), evaluated by the
dispatcher. They're not triggers, because they resume existing work
rather than create it.

---

## 10. Runs

[`run.schema.json`](./platform/schemas/run.schema.json).

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
  itself, as `formats.md` §7 requires for infrastructure deaths.
- **`ResolvedSpec`** is the immutable snapshot a run executes: the flat
  spec with params bound, and per agent the tier, model id, provider,
  deferral strategy and the fixed tools array with each tool's visibility
  at turn 0. "The tools array and the system prompt are fixed for a run"
  is this object not changing.
- **`Usage`** is per agent and per model id, with cache tokens and a
  price snapshot id, so cost stays reproducible after a price change
  (`models.md` §8's "record tier, model ID and the price at the time").
- **Events** (`GET /v1/runs/{id}/events`, SSE): state changes, turns,
  tool calls and results (sizes and status, not bodies), refusals,
  narration, harness notes, reveals, the nudge, gates, artifacts, usage,
  outcome, deliveries, follow-ons. Bodies are in the transcript, which
  has its own permission and is audited.
- **Lineage**: `root_run_id` and `depth` across continuations, and
  `resumes` for a resume. `GET /v1/runs?root_run_id=` is everything one
  request led to. A stage run also carries `pipeline_run_id` and
  `stage`.
- **Finishers** set `outcome.finisher` (`{id, external_ref}`, e.g. the
  PR it opened), so a pipeline edge or sink can tell which ending was
  chosen.

---

## 11. Publish rules

The checks a JSON Schema can't express. `:validate` and `:publish` run
them; `check.py` implements each one against the examples. The one part
it can't do is R13's comparison with a server's own input schema: the
example snapshots carry digests rather than schemas. That half runs at
publish against the real snapshot.

| Rule | Checks |
|---|---|
| R1 | every agent's grant, including `kind_grants`, names a declared group |
| R2 | every `mcp:<server>` tool names a server in `tools.servers` |
| R3 | the spawn graph names real agents; `kind_grants` keys are in `spawn_kinds` |
| R4 | params: declared; `external`/`principal` bind only to inputs; config-bound params are constrained; grant-bearing fields take no params |
| R5 | `completion.form: text` has no report schema, completion checks, spinoffs or finishers, and status `done` only |
| R6 | monitor handoffs name declared reasons; a template with HandOff reasons that no pipeline wires is a warning, since alone it has no HandOff |
| R7 | continuations (to `self` only, by schema): required params bound, carry inputs accept what is carried, spinoff edges have spinoffs enabled; `at` appears only on pipeline sinks; `approve` questions have an execute edge |
| R8 | `Expand` reveals only what the orchestrator is granted; `array_growth.bundle` is revealable; hidden groups have a reveal path (warning) |
| R9 | a read-only or absent workspace grants no `Edit`/`Write` |
| R10 | literal tiers are within `max_tier`; a clamped child above its parent is a warning |
| R11 | tool names, after aliasing, are unique per agent, including finisher names and generated tools |
| R12 | no write tool (granted, wrapped by a finisher, or called by a pipeline sink) on a service-credentialed server in anything users can run, unless the server has `entitlement_check: harness_policy` |
| R13 | argument overrides only narrow: a hidden argument is fixed, an enum is a subset of the server's, a maximum only goes down; a fixed `$param` is a config param of the template; other overrides on a fixed argument are a warning |
| R14 | finishers: `complete: false` needs at least one; each ends with a declared status; `report` needs a report schema; a wrapped tool is declared; `open_pull_request` needs a writable checkout with `git_writes: on_finish`, and `on_finish` needs an `open_pull_request` finisher |
| P1 | a pipeline's entry and edges name real stages; every `pipeline.params.x` it reads is declared |
| P2 | every exit an edge waits on (status, finisher, HandOff reason) exists in that stage's template; every HandOff reason of every stage is wired |
| P3 | each edge's carry is accepted by the next stage's template |
| P4 | every route into every stage (the entry, and each incoming edge) binds that template's required params, and only params it declares |
| P5 | no stage runs above the pipeline's `max_tier` |
| P6 | every stage is reachable, the graph is acyclic, and the longest path is within `max_hops` |
| P7 | there is a principal type every stage allows |
| P8 | pipeline sinks call only tools the pipeline declares, on servers it declares |

At resolve time, before a run starts: tool snapshot drift, delegation
scope and consent digest, deployment tier ceiling, param values against
their constraints, and the provider's deferral capability against the
visibility plan.

---

## 12. API

[`openapi.yaml`](./platform/openapi.yaml). Problem+json errors with the
closed `RefusalCode` vocabulary (the same codes tool results use,
`generative.md` §2b). `Idempotency-Key` on every create. Cursor
pagination. `:verb` for actions.

| Resource | Operations |
|---|---|
| MCP servers | CRUD, `:discover` (new snapshot + diff), `snapshots/{digest}` |
| Tool groups | versions: draft create/replace, get, `:publish` (pins snapshots, checks R13), `:preview` (each tool as the model sees it) |
| Prompts, report schemas | versioned create, get |
| Templates | list, versions, draft create/replace, `:validate`, `:publish`, `:deprecate`, `:render` |
| Pipelines | list, versions, draft create, get, `:publish` (P1–P8) |
| Pipeline runs | list (by state, subject, and `health=` for `orchestration.md` §7's queries), get, stage `:link` (the committer's PR), stage `:retry`, `:abandon`, `:stop` |
| Runs | create for a template, a pipeline or an `adhoc` body (or `dry_run`), get, list (by template, state, principal, root, pipeline run), `events` (SSE), `transcript`, `artifacts`, `:stop`, delivery `:retry` |
| Gates | list (`answerable_by=me`), get, `replies`, `:cancel` |
| Triggers | CRUD, `:fire` (test by default), `:pause`, `:resume`, `firings` |
| Events | `POST /v1/events/{provider}`: signed inbound webhooks; gate replies arriving as comments go through here too |
| Delegations | create (with a consent URL), list own, get, revoke |
| Deployment | get, put (operators) |

Two deliberate absences. There's **no endpoint that edits a published
template**, and **no endpoint that changes a running run's spec**. The
only things that act on a running run are `:stop` (which goes through
the nudge) and a delegation revoke (which fails its next OBO call).

### 12a. Permissions and RBAC

Authorisation is the RBAC system's, and it's outside this spec. There,
a **role** is a set of permission groups, assigned to a **team**, and a
user has what their teams' roles grant. That's the only meaning of
"role" anywhere in this spec ([`taxonomy.md`](./taxonomy.md)). The
platform names the permissions it checks, and RBAC decides who has them:

| Permission | Lets the holder |
|---|---|
| `templates:write`, `templates:publish` | draft, and publish or deprecate, templates (likewise `pipelines:*`, `tool-groups:*`) |
| `servers:write` | register MCP servers and run `:discover` |
| `runs:create` (per template or pipeline) | start runs of it as themselves |
| `runs:adhoc` | run an unsaved spec |
| `runs:as-service` (per template) | start runs, or create triggers, with `run_as: service` |
| `runs:read`, `runs:transcript` | see runs; read full transcripts, separately audited |
| `triggers:write` | create triggers they own |
| `pipeline-runs:operate` | stage `:retry`, `:abandon`, `:stop` on runs they didn't start |
| `stages:link` | write a stage's links back (held by the committer's service identity) |
| `deployment:write` | change the tier map and ceilings |

Two things RBAC does **not** decide, deliberately:

- **What a run may do.** That's the template's grant intersected with
  the principal's own access downstream (OBO, §8). Holding
  `runs:create` on `coding.java` lets you start it, and nothing more.
- **Who may answer a gate.** That's the gate's principal set (assignee,
  reporter, a named principal, or a `team`), resolved when the reply
  arrives. A team in a principal set is an RBAC team, read for
  membership only.


---

## 13. Forge on this platform

The examples are the mapping, and `check.py` passes on them:

| Forge | Platform |
|---|---|
| coding `implement` | [`forge.implement`](./platform/examples/forge.implement.template.json) |
| what Forge calls the coding modes | three templates: the base [`forge.coding`](./platform/examples/forge.coding.template.json) (`runnable: false`) and its siblings [`forge.plan`](./platform/examples/forge.plan.template.json) (read-only, `jira.comment` granted, `require_tool_called: AddComment`, strong tier) and `forge.implement` |
| plan → implement handoff | pipeline [`jira.plan-implement`](./platform/examples/jira-plan-implement.pipeline.json), edge gated on `plan_hash` |
| review, multi-stage | [`forge.review`](./platform/examples/forge.review.template.json): `reviewer` with `spawn_kinds` and `kind_grants.visual = [vision]`, `validator` at `strong` with `clamp_to_parent: false`, attention tier as a `commit_status` sink |
| review → fix | pipeline [`pr.review-fix`](./platform/examples/pr-review-fix.pipeline.json), approval by the PR author |
| analysis quick run and landings | pipeline [`analysis`](./platform/examples/analysis.pipeline.json): [`analysis.quick`](./platform/examples/analysis.quick.template.json) → [`analysis.investigate`](./platform/examples/analysis.investigate.template.json) / [`analysis.report`](./platform/examples/analysis.report.template.json) |
| "the job declares the tools; each sub-agent gets a subset" | `tools.groups` + `agents.*.grant`, R1 |
| `AddComment` absent in `implement` | declared in `tools.groups`, not granted to the orchestrator |
| AskUser `approve` → fresh execute run | continuation `execute_approved`, `carry: [approved_action, resumed_answer]`, no transcript |
| run ledger | the pipeline run (§7f): stage attempts and retry policy, `waiting_on`, `settle` for the PR, child runs for spinoffs |
| tier map (`models.md` §10 open point) | [`deployment.json`](./platform/examples/deployment.json) |

---

## 14. Decisions

Recorded in the README decision log (2026-10-23 rows). In short:

- Mode is not a concept. Plan and implement are sibling templates on a
  shared base, differing by tools, prompt, model and contract, and
  linked by a pipeline (§1).
- One word, one meaning (`taxonomy.md`): completion **checks** (not
  gates), in-run **monitors** (not harness triggers), **agents** for
  the contexts inside a run, and **role** only for RBAC.
- No ledger. The pipeline run is the durable record of work (§7f).
- Terminal tools are generated from contracts, never flagged (§5).
- Outputs split into effects (tools), result, sinks, continuations and
  pipeline edges, by who decides (§7). Every inter-run edge is declared.
- *Revised against the use cases:* finishers let a template choose its
  endings from real tools while the harness keeps termination (§5a);
  saved tool groups carry per-tool visibility and narrowing argument
  overrides (§4b); continuations go back into the same template only,
  and edges between templates belong to pipelines (§7c, §7e); `invoker`
  mints a session delegation for one pipeline run (§8).
- Params never reach prompt text; trust decides where they bind;
  grant-bearing fields take no params (§6).
- MCP tool lists are pinned by snapshot digest per template version
  (§4a).
- Three identities per run; OBO by token exchange; delegation for
  absent users; the R12 confused-deputy rule (§8).
- CEL for every harness expression (§9).

## 15. Open

- **Where report schemas live.** They're registry refs here. Forge's
  report shapes are in `formats.md` §3 as prose plus JSON. They need
  extracting into versioned schemas before `:publish` can validate
  against them.
- **Delegation for continuations.** Mostly settled by `invoker`'s
  session delegation (§8), which covers a pipeline started from chat or
  the UI. Still open: a template run directly from the API by a user,
  whose `follows_this` spinoff is approved days later. Today that edge
  refuses with `delegation_missing` unless the user holds a stored
  delegation.
- **More harness finishers.** `open_pull_request` and `request_help`
  are what the use cases need. Candidates are a draft PR (a config flag
  today), publishing an artifact, and merging. Merging is deliberately
  not on the list: it's an approval, and an agent can't approve its own
  work.
- **Draft runs.** Drafts run only with `dry_run`. A "run a draft
  against a sandbox deployment" mode is probably needed for eval
  (`eval.md`), and isn't specified.
- **A saved group's new version** doesn't reach templates until they
  are re-published against it. That's the right default for review, and
  it makes "roll a fix to the Java group out to fifty templates" a
  bulk re-publish. A `:republish-dependents` operation is probably
  wanted and isn't specified.
- **Hidden-tool reveal on Anthropic** is still unverified
  (`tools.md` rule 3), so `visibility: hidden` may resolve to `deferred`
  on that provider. The resolver records what it chose.
