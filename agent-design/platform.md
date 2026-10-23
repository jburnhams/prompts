# Agent platform: data models and APIs

**Status: proposal, 2026-10-23.** This turns the Forge design into
resources a service could store and an API could serve. It doesn't
change what Forge does. It says where each decision already made in this
folder lives as data, who may change it, and when.

| File | What it is |
|---|---|
| this file | the model, the rules, and the reasons |
| [`platform/schemas/`](./platform/schemas) | JSON Schema (2020-12) for every resource |
| [`platform/openapi.yaml`](./platform/openapi.yaml) | the API, OpenAPI 3.1, referencing those schemas |
| [`platform/examples/`](./platform/examples) | Forge's three entrypoints and the quick-analysis path written as templates, plus triggers, servers, a delegation and a deployment |
| [`platform/check.py`](./platform/check.py) | validates every example against the schemas, then runs the publish rules in §11. `python3 -I agent-design/platform/check.py` |

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
| Tools, tool groups | `ToolRef`, `ToolGroup` (the unit of grant) | `tools.md` |
| Visibility and deferral | `Visibility` per group, overridable per role; the provider flag sits in deployment | `tools.md` "Granted, registered, visible" |
| Completion tools | `completion`, `human.ask_user`, `hatches.handoff`. The harness **generates** these tools (§5) | `formats.md` §3, §5; `models.md` §4b |
| System prompt | `PromptSpec`: versioned fixed text, subtraction by heading, generated blocks | `system-prompts.md` §6–§7 |
| Starting query | an `inputs[]` entry of kind `instruction`, filled from a param | `formats.md` §1 |
| Model | a **tier** plus a ceiling. The deployment maps tiers to model ids | `models.md` §2.5 |
| Sub-agents | `roles`: one orchestrator plus named sub-agent roles, each with its own grant, tier and prompt | `tools.md`, `system-prompts.md` §3–§5 |
| User on-behalf-of | `authority`, server `auth.mode: obo`, `Delegation` | new here, §8 |
| **Inputs other than the query** | `inputs[]`: ticket, diff, comments, plan, prior attempt, approved action. Each is typed and has a trust level | `formats.md` §1, `context-files.md` §4 |
| **Standing context** | `context.conventions` (tiers, kinds, paths, at which SHA) | `context-files.md` §1b |
| **Workspace** | `workspace`: none, or a harness-provisioned checkout with `writable`, `write_scope`, scratch dir, `git_writes: deny` | README decision log, `orchestration.md` §4 |
| **Budgets** | `budgets`: turns, context high-water mark, wall time, tokens by tier, sub-agent count | `formats.md` §7, `models.md` §10 |
| **Harness checks** | `tools.checks`: enforcement that no grant can remove | `tools.md` "Harness-side checks are not part of the subset" |
| **Human channel** | `human.ask_user` (who may answer, where it goes) and `human.narrate` | `formats.md` §5a, `medium.md` §2f, §5c |
| **Hatches and harness triggers** | `hatches.expand`, `hatches.handoff`, `harness_triggers[]` | `models.md` §4–§5 |
| **Outputs** | `outputs.sinks[]` and `outputs.continuations[]` (§7) | new here; unifies several |
| **Concurrency** | `concurrency.key` and a policy | `orchestration.md` §4 |
| **Ledger participation** | `ledger` | `orchestration.md` |
| **Versioning and pinning** | template versions, tool snapshot digests, pinned continuation targets | new here, §6 |
| **Deployment facts** | `Deployment`: tier→model map, provider capabilities, global ceiling, mandatory checks | `models.md` §10 open point, now closed |

**One thing on the list is not a concept: `mode`.** Forge's `plan` and
`implement` differ in tools, statuses, report schema and gates, and
those all have their own fields now. So a mode is a separate template,
and `forge.plan` `extends` `forge.implement`
([example](./platform/examples/forge.plan.template.json)). The envelope's
`<mode>` tag is still rendered, from the template. It's no longer a
switch inside one spec.

---

## 2. Layers

```
 Deployment ─────────── tier→model map, provider flags, ceilings, mandatory checks
     │
 Registry ───────────── McpServer (+ ToolSnapshot), ToolGroup, prompts, report schemas
     │  referenced, pinned by digest
     ▼
 Template@version ───── params + AgentSpec      (immutable once published)
     │  bind params, resolve for this principal and deployment
     ▼
 Run ────────────────── ResolvedSpec snapshot + state + outcome + usage
     │       ▲                    │
     │       │ creates            │ outcome feeds
     │   Trigger ◄── Event        ├──► Sinks           (deliveries)
     │   (schedule, event,        ├──► Continuations   (more runs, or tasks)
     │    run_outcome, manual)    └──► Gates           (a human decides first)
     ▼
 Task (ledger) ──────── an obligation across runs: attempts, deps, lease
 Delegation ─────────── a user's standing consent for a template to act for them
```

This is a deliberately short chain. An **AgentSpec** is everything
about a run. A **Template** is an AgentSpec with named holes and a
version. A **Run** is one template version with the holes filled, under
one principal. A **Trigger** decides when a run starts. **Outputs**
decide what the run leads to.

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

## 3. The AgentSpec

Schema: [`agent-spec.schema.json`](./platform/schemas/agent-spec.schema.json).
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
  write tools for any role, whatever the grants say (rule R9 rejects
  the contradiction at publish). `git_writes` has one value, `deny`.
- **`tools`**: the job's declaration (§4).
- **`roles`**: `orchestrator` plus named sub-agent roles (§4c).
- **`human`**, **`completion`**, **`hatches`**: these generate tools (§5).
- **`harness_triggers[]`**: `models.md` §5's table as data. Each is a
  signal (consecutive errors on a tool, zero rows, turns without an
  answer, an unlisted source named, a request matching keywords) and an
  action (hand off, reveal a group, add a harness note, skip to a
  landing before turn 0).
- **`budgets`**: crossing `turns` or `context_high_water_tokens` triggers
  the final-turn nudge. `tokens_by_tier` counts the run and its children
  together, so spend can't hide in a cheap child (`models.md` §10).
- **`outputs`**: sinks and continuations (§7).
- **`authority`**: who the run may act for (§8).
- **`concurrency`**, **`ledger`**: from `orchestration.md`.

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
composition). A `ToolRef` can rename a tool for the model (`alias`:
`mcp:jira/get_issue` becomes `FetchJira`), replace its description,
set limits, and override annotations. `mcp:x/*` is allowed in drafts
and is expanded against the snapshot, then frozen, at publish.

**Annotations are authoritative from the job, hints from the server**,
and an override may only make a tool look more dangerous. An
unannotated MCP tool is treated as destructive, non-idempotent and not
concurrency-safe, which is MCP's own default for `destructiveHint`.
`retry` defaults to `never` unless the tool is idempotent: `adk.md` §4's
finding that retries make non-idempotent tools dangerous, as a field.

`tools.md`'s three questions map onto three fields:

| Question | Field | Enforced |
|---|---|---|
| Granted | `roles.<r>.grant[]` (+ `kind_grants` for the kind given at spawn) ⊆ `tools.groups` | at the executor, every call |
| Registered | derived at resolve: grant + generated tools, as one fixed array per role (`ResolvedSpec.roles.<r>.registered`) | provider validation |
| Visible | `ToolGroup.visibility`, overridden by `roles.<r>.visibility` | nothing; it shapes what the model tries |

`hidden` groups need a way to become visible: `hatches.expand.reveals`
or a harness trigger's `reveal`. R8 warns when a hidden group has
neither. How "deferred" and "hidden" are realised depends on the
provider flag in deployment: `defer_loading` on Anthropic,
`tool_search`/`additional_tools` on OpenAI, and on Bedrock `Converse`
either everything loads upfront or the once-only array growth that
`hatches.expand.array_growth` permits (`models.md` §4a). The spec
states intent. The resolver picks the mechanism and records it in
`ResolvedSpec.roles.<r>.deferred_tools`.

### 4c. Roles

Every role has a `grant`, optional `visibility` overrides, a `model`,
and `spawns` (which roles it may launch). A non-empty `spawns` generates
`Task`, with `subagent_type` limited to those roles and each role's
`description` as the enum text. Sub-agent roles add a `prompt`,
`spawn_kinds` (the kinds a spawner may pass, Forge's `Task.role`),
`kind_grants` (the tool half of "kinds: one vocabulary, three
resolutions"), `spawn_args` (extra required `Task` fields, such as the
validator's `finding`) and a `report_schema` the harness validates.

The rules from `tools.md` §"One job declares the tools", and where each
is enforced:

- **Siblings, not a chain.** Every role's grant is checked against
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
part of any grant, so no role, param or prompt can remove them, and
they apply to every role. Goose's sub-agents running with no hooks
(`../agent-subagent-architectures.md` §7d) is the failure this is
shaped against.

---

## 5. Completion tools: separate tools, or a flag on a tool?

**Neither. The spec declares a contract, and the harness generates the
tool.** Authors don't write `Complete`, and they can't mark an arbitrary
tool as run-ending.

| Contract in the spec | Generated tool | Ends the run? | What the harness does on the call |
|---|---|---|---|
| `completion` | `harness/Complete` (or `tool_name`) | yes: `complete` | validates `report` against `report_schema`, runs `gates`, files spinoffs, evaluates sinks and continuations |
| `human.ask_user` | `harness/AskUser` | yes: `suspend` | opens a gate, posts to `channels`, records who may answer |
| `hatches.handoff` | `harness/HandOff`, its `reason` enum = the declared reason ids | yes: `handoff` | starts the continuation wired to that reason |
| `hatches.expand` | `harness/Expand` | no | reveals granted groups and sources |
| `roles.*.spawns` | `harness/Task` | no | spawns a sub-agent under its role's grant |
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
which `gates` run, whether spinoffs are allowed, and which handoff
reasons exist and what situation each describes. That is the whole of
what Forge's three entrypoints vary.

**`form: "text"`** covers the quick analysis run (`models.md` §3): the
run ends on an assistant message with no tool calls, with status
`done`. R5 limits it to specs with no report schema, no gates and no
spinoffs, because there's nothing to validate.

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
- generates harness tools per role;
- runs the rules in §11;
- computes three digests: the spec, the fixed prompt text per role,
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

Not bindable at all: `system_prompt`, `tools`, `roles`, `completion`,
`hatches`, `authority`, `harness_triggers`, `model.max_tier`. That is
R4. It's the reason "params narrow, never widen" holds: every
config-bound param has a declared ceiling, and the fields that grant
anything take no params.

**Two consequences worth wanting:**

- **One cacheable prefix per template version.** Params never reach
  the system prompt, and the tools array per role is fixed at publish
  (up to the deployment's tier map). So every run of a version shares
  the same tools-plus-system prefix, and the cache is shared across
  runs, not just within one. `Template.resolved.prompt_digest` names it.
- **`:render`** shows exactly what a model would be given for a set of
  params (tools array, visibility, rendered prompt, envelope with
  placeholder nonces) without running anything. It's what you diff when
  someone asks why a run behaved the way it did.

---

## 7. Outputs: tools, chaining, or something else?

**All three, but they're three different things, and the line between
them is who decides.**

| | Decided by | When | Mechanism | Forge examples |
|---|---|---|---|---|
| **Effects** | the model | during the run | a granted **tool** | `AddComment` in plan and review runs; a warehouse write |
| **Result** | the model, inside a contract | at the end | the terminal call → `Run.outcome` | `Complete.report`, `HandOff.reason`, artifacts in `evidence` |
| **Sinks** | the template | after the run, fixed by outcome | harness **delivery** | posting `summary` to the ticket; the attention tier as a commit status; publishing a report |
| **Continuations** | the template declares the edges; the outcome (and sometimes a human) picks one | after the run | a new **run** or **task** | plan → implement; HandOff landings; approve → execute; spinoffs; review → fix |

The rule for effects versus sinks: **if the model decides whether,
what, or where to post, it's a tool. If posting is a fixed consequence
of how the run ended, it's a sink.** Forge already draws this line. Its
`Complete.summary` is "not posted anywhere by Forge itself — whether
and how it reaches a PR, a Jira comment … is the invoking harness's
call" (`tools.md`). That is a sink. Plan mode's step-5 posting *is* the
model's choice of content, so it's an effect, and
`completion.gates: require_tool_called` checks it happened.

### 7a. Result

`Run.outcome`: `terminal` (`complete | suspend | handoff |
infra_failure | stopped`), `status`, `summary`, `report` (validated),
`handoff {reason, why}`, `nudged`, the post-run `integrity` checks, a
`refusal` code if the harness ended it, and `report_digest` for
approvals to bind to. Artifacts are listed on the run. Everything
downstream reads this one object, so sinks and continuations never
parse prose.

### 7b. Sinks

`{id, when, kind, channel, render, idempotency_key, retry}`. Kinds:
`comment`, `commit_status`, `webhook`, `chat`, `email`,
`artifact_publish`, `dataset_write`. `render` is a Mustache template
over the result, written by the template author, and the output is
Markdown converted per channel. That matches the decision that comment
bodies are always Markdown, with conversion harness-side. Every
delivery is a `Delivery` record with its own retry state, so a Jira
outage loses nothing and can be retried by id.

### 7c. Continuations

`{id, on, target, params, carry, gate, via, run_as}`. One structure
covers every inter-run edge this folder had specified separately:

| Edge | `on` | `target` | `carry` | `gate` |
|---|---|---|---|---|
| plan → implement (`formats.md` §6) | `complete`, `planned` | `forge.implement` | `plan` | `approval`, `bind: plan_hash` (gated pattern), or `auto` (auto-chained) |
| approve → execute (`formats.md` §5) | `suspend`, `answer: approve` | `self` | `approved_action`, `resumed_answer` | `auto` (the gate was the question) |
| `blocks_this` spinoff (`orchestration.md` §6) | `complete`, `blocked`, `spinoff: blocks_this` | `self`, `via: task` | `prior_attempt` | `auto` |
| `follows_this` spinoff | `complete`, `spinoff: follows_this` | `self`, `via: task` | `prior_attempt` | `approval` |
| HandOff `too_complex` (`models.md` §4b) | `handoff`, reason | `analysis.investigate` | `prior_attempt` | `auto` |
| HandOff `report_requested` | `handoff`, reason | `analysis.report` | `prior_attempt`, `artifacts` | `auto` |
| review → fix (`medium.md` §1b) | `complete`, `done`, an expression on findings | `forge.implement`, `via: task` | `findings` | `approval` by the PR author |

The rules that keep this safe:

- **The model chooses among declared edges. It never names a target.**
  `HandOff.reason` is an enum generated from the edges. `spun_off` is a
  proposal the edge turns into a task. No result field can name a
  template (`continuation_undeclared`). This is `orchestration.md` §8's
  invariant, "a role may file, propose or report; it may not act on
  what it oversees", stated as a schema.
- **Carry is what crosses, and never a transcript.** The target must
  declare a matching `carry` input (R7), so context crosses only
  through typed envelope blocks, as `formats.md` §6 already requires.
  The one exception is **resume**, which is not a continuation: a
  `clarify` answer resumes the same template with the suspended run's
  transcript (`Run.lineage.resumes`). It's built in because it's the
  one case where the transcript has to survive.
- **Bounded.** `max_chain_depth` counts hops from the root request
  (resume excluded). Every target lands at or below the root's
  `max_tier` (R7), and below the deployment ceiling at run time
  (`tier_ceiling`). `models.md`'s "at most two hand-offs" is
  `max_chain_depth: 2` on `analysis.quick`.
- **Gated edges open a `Gate`.** Approval gates bind to
  `report_hash` or `plan_hash`, and the approval lapses if the content
  changes (`formats.md` §5a rule 4).
- **`run_as` is `same` or `service`, never someone else.** A
  continuation can't move work to a different user's authority.

**Chaining across owners.** A `run_outcome` trigger (§9) lets one team
start its template when another team's template finishes, without
editing the other template. Inside one template, prefer a continuation:
the edge is then in the version that was reviewed.

### 7d. Gates

[`gate.schema.json`](./platform/schemas/gate.schema.json). One resource
for everything waiting on a human: `clarify`, `approve_action`,
`continuation_approval`. It holds the question (with `{id, label,
implication}` options and, for approvals, the named action), the
`bound_digest`, the principal set, the channels with the external ref
each reply is matched on, the replies (each with harness-asserted
`from`, `author`, `option_id`, `match`), and a resolution.
`GET /v1/gates?answerable_by=me&state=open` answers "what is waiting on
me" across every template. `POST /v1/gates/{id}/replies` is the single
reply path for the UI and for every channel adapter, which is
`medium.md` §5c's multi-channel delivery without a new tool.

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

- it is for one template from `min_version`;
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
- `event_actor`: the Jira trigger. The person who moved the ticket is
  the principal, but only if they hold a delegation for this template;
  otherwise `fallback: refuse`. This is deliberately not "run as
  whoever commented". Mapping a provider account to an IdP subject is
  necessary, and it isn't sufficient: consent is still needed.

**Gates use the same identities.** Who may answer is a
`PrincipalSetRule` list (`principal`, `requested_by`,
`issue_assignee`, `issue_reporter`, `pr_author`, `trigger_owner`, a
named principal, an IdP group). It's resolved when the reply arrives,
not when the question was asked, exactly as `formats.md` §5a specifies.
An empty resolved set is said in the posted question.

---

## 9. Triggers

[`trigger.schema.json`](./platform/schemas/trigger.schema.json). A
trigger is `{owner, template, source, filter, params, run_as, dedupe,
concurrency, rate_limit, creates}`.

| Source | For | Notes |
|---|---|---|
| `schedule` | digests, sweeps, check-back-later | `cron` with a required IANA `timezone`, `jitter_s`, `catch_up: none \| latest`, `overlap: skip \| queue`, start and end |
| `event` | Jira transitions, PR opened/updated/commented/merged, build failed, artifact published, generic signed webhooks | normalised `Event`, signature-checked and sanitised at `POST /v1/events/{provider}` |
| `run_outcome` | chaining across owners | another template's terminal and status |
| `manual` | chat commands, UI buttons | binds params and policy to an entry point; the invoking user is the principal |

**Expressions are CEL**, evaluated by the harness, never by or for the
model. They can be checked for cost before they run, and they can't
loop. The variables:

| Where | Variables |
|---|---|
| trigger `filter`, `params`, `dedupe.key`, `concurrency.key`, `run_as.actor` | `event` |
| spec `concurrency.key`, sink `idempotency_key`, `ChannelRef.target` | `params`, `principal`, `run` |
| continuation `on.expr`, `params` | `params`, `result`, `principal`, `run`, and `spinoff` (with `index`, `title`, `paths`, `kinds`) on spinoff edges |
| sink `when.expr` | `params`, `result`, `run` |

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
runs, with `handoff` counting as occupied (`orchestration.md` §4). A
running run is never cancelled by either.

The parked-task wake predicates in `medium.md` §4c (`jira`, `build`,
`pr`, `timer`) are `Task.wake`, evaluated by the dispatcher. They're
not triggers, because they wake an existing obligation rather than
create work.

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
  report validation, completion gates (the first-`done` checklist sends
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
  spec with params bound, and per role the tier, model id, provider,
  deferral strategy and the fixed tools array with each tool's visibility
  at turn 0. "The tools array and the system prompt are fixed for a run"
  is this object not changing.
- **`Usage`** is per role and per model id, with cache tokens and a
  price snapshot id, so cost stays reproducible after a price change
  (`models.md` §8's "record tier, model ID and the price at the time").
- **Events** (`GET /v1/runs/{id}/events`, SSE): state changes, turns,
  tool calls and results (sizes and status, not bodies), refusals,
  narration, harness notes, reveals, the nudge, gates, artifacts, usage,
  outcome, deliveries, follow-ons. Bodies are in the transcript, which
  has its own permission and is audited.
- **Lineage**: `root_run_id` and `depth` across continuations, and
  `resumes` for a resume. `GET /v1/runs?root_run_id=` is everything one
  request led to.

---

## 11. Publish rules

The checks a JSON Schema can't express. `:validate` and `:publish` run
them; `check.py` implements each one against the examples.

| Rule | Checks |
|---|---|
| R1 | every role's grant, including `kind_grants`, names a declared group |
| R2 | every `mcp:<server>` tool names a server in `tools.servers` |
| R3 | the spawn graph names real roles; `kind_grants` keys are in `spawn_kinds` |
| R4 | params: declared; `external`/`principal` bind only to inputs; config-bound params are constrained; grant-bearing fields take no params |
| R5 | `completion.form: text` has no report schema, gates or spinoffs, and status `done` only |
| R6 | HandOff reasons and handoff continuations match one to one; harness-trigger handoffs name declared reasons |
| R7 | continuations: the target exists, its required params are bound, its carry inputs accept what is carried, spinoff edges have spinoffs enabled and a ledger, and the landing tier is within `max_tier`; `approve` questions have an execute edge |
| R8 | `Expand` reveals only what the orchestrator is granted; `array_growth.bundle` is revealable; hidden groups have a reveal path (warning) |
| R9 | a read-only or absent workspace grants no `Edit`/`Write` |
| R10 | literal tiers are within `max_tier`; a clamped child above its parent is a warning |
| R11 | tool names, after aliasing, are unique per role |
| R12 | no write tool on a service-credentialed server in a template users can run, unless the server has `entitlement_check: harness_policy` |

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
| Tool groups, prompts, report schemas | versioned create, get |
| Templates | list, versions, draft create/replace, `:validate`, `:publish`, `:deprecate`, `:render` |
| Runs | create (or `dry_run`), get, list (by template, state, principal, root, task), `events` (SSE), `transcript`, `artifacts`, `:stop`, delivery `:retry` |
| Gates | list (`answerable_by=me`), get, `replies`, `:cancel` |
| Tasks | list (with `health=` for `orchestration.md` §7's queries), file, get, `:retry`, `:abandon` |
| Triggers | CRUD, `:fire` (test by default), `:pause`, `:resume`, `firings` |
| Events | `POST /v1/events/{provider}`: signed inbound webhooks; gate replies arriving as comments go through here too |
| Delegations | create (with a consent URL), list own, get, revoke |
| Deployment | get, put (operators) |

Two deliberate absences. There's **no endpoint that edits a published
template**, and **no endpoint that changes a running run's spec**. The
only things that act on a running run are `:stop` (which goes through
the nudge) and a delegation revoke (which fails its next OBO call).

---

## 13. Forge on this platform

The examples are the mapping, and `check.py` passes on them:

| Forge | Platform |
|---|---|
| coding `implement` | [`forge.implement`](./platform/examples/forge.implement.template.json) |
| coding `plan` | [`forge.plan`](./platform/examples/forge.plan.template.json), `extends` implement, read-only workspace, `jira.comment` granted, `require_tool_called: AddComment`, gated edge to implement bound to `plan_hash` |
| review, multi-stage | [`forge.review`](./platform/examples/forge.review.template.json): `reviewer` with `spawn_kinds` and `kind_grants.visual = [vision]`, `validator` at `strong` with `clamp_to_parent: false`, attention tier as a `commit_status` sink, review → fix as an approval-gated continuation |
| analysis quick run and landings | [`analysis.quick`](./platform/examples/analysis.quick.template.json) → [`analysis.investigate`](./platform/examples/analysis.investigate.template.json) / [`analysis.report`](./platform/examples/analysis.report.template.json) |
| "the job declares, roles get subsets" | `tools.groups` + `roles.*.grant`, R1 |
| `AddComment` absent in `implement` | declared in `tools.groups`, not granted to the orchestrator |
| AskUser `approve` → fresh execute run | continuation `execute_approved`, `carry: [approved_action, resumed_answer]`, no transcript |
| run ledger | `ledger`, `via: task`, [`task.schema.json`](./platform/schemas/task.schema.json) (`orchestration.md` §2 restated on templates) |
| tier map (`models.md` §10 open point) | [`deployment.json`](./platform/examples/deployment.json) |

---

## 14. Decisions

Recorded in the README decision log (2026-10-23 rows). In short:

- Mode is a template, not a field: `extends` plus narrowing replaces
  `mode`.
- Terminal tools are generated from contracts, never flagged (§5).
- Outputs split into effects (tools), result, sinks and continuations,
  by who decides (§7). Every inter-run edge is a declared continuation.
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
- **Delegation for continuations.** A continuation with `run_as: same`
  after the user's session has ended needs a delegation. The current
  rule is that the root run's delegation (if any) is inherited and
  checked against the target template. If there was none, the edge
  refuses with `delegation_missing`. Whether an interactive root run
  should mint a short-lived delegation automatically is not decided.
- **Draft runs.** Drafts run only with `dry_run`. A "run a draft
  against a sandbox deployment" mode is probably needed for eval
  (`eval.md`), and isn't specified.
- **Group registry versioning** is sketched (`{ref: {name, version}}`)
  but publish-time expansion of a shared group into a template's frozen
  spec isn't argued for here beyond "same as `extends`".
- **Hidden-tool reveal on Anthropic** is still unverified
  (`tools.md` rule 3), so `visibility: hidden` may resolve to `deferred`
  on that provider. The resolver records what it chose.
