# Taxonomy

**Status: proposal, 2026-10-23.** One meaning per word, for
[Keel](./README.md) and for the configurations built on it, Forge first.
Where one of Forge's documents (in `../`) uses a different word for the
same thing, the entry says so. That way the older documents
don't have to be rewritten, and a reader of either can find their way.

Each entry gives the meaning, then *Not*: what it gets confused with,
then *Where*: the schema field or document. Section 10 lists words we
deliberately don't use as concepts. Section 11 records the collisions
and how each was settled.

---

## 1. Defining an agent

**Agent.** One model context inside a run, with its own prompt, tools
and tier. Every run has an **orchestrator** agent, and may spawn
**sub-agents**. Informally, "the data agent" or "the plan agent" means
the template whose orchestrator does that job, which is consistent: a
template is mostly a description of its orchestrator.
*Not:* a run (one execution), a **role** (an RBAC concept, §6).
*Where:* `agents` in a run spec.

**Run spec** (`RunSpec`). Everything that defines one run, before
params are bound: the model, the prompt, the inputs, the tools, the
agents, the ending contract, the outputs and the authority.
*Older word:* `AgentSpec`, renamed when "agent" came to mean one
context inside a run.
*Where:* `schemas/run-spec.schema.json`.

**Template.** A run spec with a name, a version, and declared
**params**. It is the thing you save, review, publish and run.
*Not:* a prompt template. Prompts take no params (see **Param**).
*Where:* `template.schema.json`.

**Base template** (`runnable: false`). A template that exists only to be
extended. It can't be run, triggered, or used as a pipeline stage.
`forge.coding` is one: the shared part of `forge.plan` and
`forge.implement`.

**Extends.** Reuse. A template takes a published parent's spec and
params, and changes some of them. Objects merge, lists replace, `null`
deletes. It says nothing about how the two behave.
*Not:* a mode or variant relationship (§10).

**Version; draft, published, deprecated.** Templates, pipelines, saved
tool groups, prompts and report schemas are numbered. A draft can
change. A published version never changes. A deprecated version
refuses new runs, while existing ones finish.

**Pinned.** Resolved to a concrete version when the referring thing is
published. So a published template always names exact tool snapshots,
and a published pipeline names exact stage templates.

**Param.** A named, typed value supplied per run: by the caller, a
trigger, a pipeline, or a continuation. Its **trust** decides where it
may go.
*Not:* a tool **argument**. Never interpolated into prompt text.
*Where:* `Template.params`, `ParamSpec`.

**Trust** (of a param or input). Who authored the content:
- `harness` and `config` content is instruction.
- `principal`, `participant` and `external` content is data: it reaches
  the model only as a nonce-wrapped input.

**Config param.** A param with `trust: config`. It may set config
fields (repository, branch, tier, budgets, paths), and must declare a
limit: an enum, a pattern, a subset or a maximum.

**Bindable.** A field that accepts `{"$param": …}`. Fields that grant
anything are never bindable: prompt, tools, agents, completion, hatches,
authority, monitors.

**Ad-hoc run.** A run of an unsaved spec. The harness publishes it as
`adhoc.<digest>` and applies every rule before it runs.

---

## 2. What the model is given

**System prompt.** Fixed, versioned text plus **generated blocks**. It
is the same for every run of a template version.
*Where:* `PromptSpec`; prompts are versioned in the registry.

**Generated block.** Text the harness writes per run from facts:
`env`, `capabilities`, `git_status`, `repo_context`, `data_overview`.

**Capability block.** The generated block that states what the run can
do, one line per tool family present, computed from the registered
tools (`../system-prompts.md` §7).

**Omitted section.** A prompt section removed by heading under a stated
condition, such as a tool being absent. A section can be removed, never
varied.

**Input.** One tagged block of the **envelope**. It has a kind, a
source and a trust level.
*Where:* `inputs[]`.

**Envelope.** All of a run's inputs together, in order: the task the
run is about. Untrusted blocks carry the run's **nonce** on both tags.
*Where:* `../formats.md` §1.

**Starting query.** The input of kind `instruction`: the user's
question or the task details. Filled from a `principal` param.
*Not:* the system prompt.

**Carry.** An input filled only when this run was started from another
run's outcome: a plan, a prior attempt, an approved action, a resumed
answer, findings. A transcript is never carried.

**Nonce.** A per-run random value on both tags of an untrusted block,
so the content can't forge the end of its block or open a
higher-privilege one.

**Conventions.** Standing written instructions (org, team, repo,
learned), resolved by the context service for a ref.
*Where:* `context.conventions`, `../context-files.md`.

**Kind.** One open vocabulary: `bugs`, `security`, `conventions`,
`visual`, … A kind selects context sections, prompt scope and extra
tool grants for a sub-agent. Kinds are declared by whoever spawns the sub-agent,
never by the agent about itself.
*Older words:* **lens** (`../review.md`), and the `role` argument of
Forge's v1 `Task` tool. Keel's generated `Task` calls it
`kind`.

**Workspace.** What the run may touch on disk: `none`, or a
harness-provisioned **checkout** with `writable`, a **write scope**
(path globs), a scratch directory outside the tree, and **git writes**
`none` or `via_action` (whether an agent of the run can cause a push,
only through `action/open_pull_request`), and **retain** (how long the
checkout outlives the run).

---

## 3. Tools

**Tool.** Something the model can call: a name, a description, an input
schema.

**Tool address.** `source/name`: `builtin/Read`, `mcp:jira/get_issue`,
`harness/Complete`.

**Tool source.** Where a tool comes from:
- `builtin`: harness-implemented file, shell and image tools.
- `action`: harness actions with effects outside the run, such as
  opening a PR.
- `mcp:<server>`: an MCP server.
- `harness`: generated from a contract (see **Generated tool**). These
  can't be put in a group.

**MCP server.** A registered tool provider, with its transport, auth
mode, limits and **snapshot**.

**Snapshot.** A frozen copy of a server's tool list, with a digest of
each description and input schema. Templates and saved groups pin one.
**Drift** is the live list differing from the pin. A changed input
schema always refuses.

**Tool reference** (`ToolRef`). One tool as a group includes it, with
the group's settings: alias, description, visibility, annotations,
limits, argument overrides.

**Alias.** The name the model sees, when different from the server's.

**Argument.** One input field of a tool.
*Not:* a **param**, which belongs to a template.

**Argument override** (`ParamOverride`). A change to how one argument
looks to the model: description, default, required, or narrowing (an
enum subset, a lower maximum, a pattern). Overrides only narrow, never
widen, and an argument can't be renamed. Despite the word `params` in
the field, these are tool arguments, not template params.

**Fixed argument.** An argument whose value the harness supplies (a
literal, a config param, or an expression). It is usually **hidden**
from the model too: hiding requires fixing.

**Annotation.** A fact the harness relies on: read-only, destructive,
idempotent, concurrency-safe, open-world, retry policy. The template's
annotations are authoritative and can only make a tool look more
dangerous. Unannotated MCP tools get the worst case.

**Tool group.** A named set of tool references, and the unit of grant
and default visibility. It is **inline** in one spec, or **saved**
(`SavedToolGroup`): versioned, owned, reused across templates, and
carrying its own pinned servers.

**Declaration.** Every tool and server a template lists in
`tools.groups` and `tools.servers`, granted or not. Nothing outside it
can be granted, revealed, wrapped by a finisher, or called.
*Older word:* "the job's declaration" (`../tools.md`).

**Grant.** The groups an agent may call (`agents.<a>.grant`), each a
subset of the declaration. Checked by the executor on every call.

**Registered.** In the fixed tools array sent to the provider for an
agent. Grant plus generated tools. It doesn't change during a run.

**Visibility.** Whether the model has a tool's schema in context right
now:
- **loaded**: the full schema;
- **deferred**: a name and search hint, loaded on request;
- **hidden**: nothing, until revealed;
- **revealed**: loaded at a point in the run by `Expand` or a monitor.

Visibility never grants.

**Generated tool.** A tool the harness builds from a contract:
`Complete`, each finisher, `AskUser`, `HandOff`, `Expand`, `Task`,
`Narrate`.

**Harness check.** Enforcement at the tool boundary for every agent,
which no grant can remove: sanitiser, git-write blocklist,
read-before-edit, secret scan, egress allowlist and so on.
*Where:* `tools.checks`.
*Not:* a **completion check** (§5).

---

## 4. Agents and models

**Orchestrator.** The top-level agent of a run. The only one with
generated ending tools and a human channel.

**Sub-agent.** An agent the orchestrator (or another agent) **spawns**
through `Task`. It returns a report to its spawner. It never ends the
run and never talks to a human. Its grant comes from the declaration,
not from its spawner's grant.

**Task.** The generated tool an agent uses to spawn a sub-agent. "Task"
is otherwise informal, for the work a run is given; it isn't a record.

**Kind grant.** Extra groups a sub-agent gets when spawned with a given
kind (`visual` → `vision`).

**Tier.** `economy`, `standard` or `strong`. Templates name tiers, never
models.

**Effort.** A reasoning-effort hint, separate from tier.

**Max tier.** The highest tier a run, its children and its pipeline may
reach. Set by template, pipeline and deployment. The lowest wins.

**Clamp.** A sub-agent never runs above its parent's tier unless the
template says `clamp_to_parent: false`.

**Deployment.** Operator-owned facts no template overrides: the tier →
model map, provider capabilities, the global max tier, mandatory
checks.

**Provider.** The model API (Anthropic, Bedrock `Converse`, …).
Recorded with its capabilities, such as whether it supports deferred
tool loading.

---

## 5. How a run ends

**Ending.** Any way a run stops. The kind of ending is the
**terminal**:
- `complete`: through `Complete` or a finisher;
- `suspend`: through `AskUser`;
- `handoff`: through `HandOff`;
- `infra_failure` and `stopped`: harness-side.

**Complete.** The generic ending tool, generated from the completion
contract. It can be switched off (`complete: false`).

**Finisher.** An ending the model chooses that also does something: it
wraps a declared tool, which can be a **harness action**. The completion checks
run first, then the action. If the action fails, the error goes back to
the model and the run continues.

**Harness action.** A tool the harness implements rather than an MCP
server, addressed `action/<name>`. Like any tool it can be granted
mid-run, wrapped by a finisher, or called by a pipeline sink after the
run. Which position is a configuration's choice, not Keel's.
- `open_pull_request`: commit, push and open the PR under the
  harness's git identity, and link it to the stage;
- `request_help`: post to a channel; as a finisher it ends the run
  `blocked`.

**Status.** How a `complete` ending went: `done`, `planned`, `skipped`,
`failed`, `blocked`, `budget_exhausted`.

**Report.** The structured part of an ending, validated against the
template's report schema.

**Summary.** The short human-readable part of an ending. Sinks render
it. The model never posts it itself.

**Completion check.** A deterministic test between the ending call and
the run actually ending: the first-`done` checklist,
`require_tool_called`, `report_crosscheck`, `provenance_closure`.
*Where:* `completion.checks`.
*Not:* a **gate** (§6), a **harness check** (§3).
*Older word:* "completion gate" (`../tools.md`, and the first draft of
Keel).

**Budget.** A limit on turns, context, wall time, tokens by tier, cost
or sub-agents. Turns and context end in the **final-turn nudge**.

**Final-turn nudge.** An injected last turn that allows only the
endings that exist, so every run ends with a report.

**Hatch.** Either of the two tools a quick run uses to get more than it
started with (`../models.md` §4):
- **Expand** reveals more granted sources and tools, and the run
  continues.
- **HandOff** ends the run with a reason, so a pipeline can start a
  stronger stage.

**Exit.** Something a template can end with that a pipeline can wire:
a status, a finisher, a HandOff **reason**, or a gate answer.

**Monitor.** A signal the harness watches during a run (two failed
queries in a row, zero rows, too many turns), and what it does: hand
off, reveal, or add a harness note.
*Where:* `monitors[]`.
*Older word:* "harness trigger" (`../models.md` §5).
*Not:* a **trigger** (§8).

**Harness note.** Harness-written text in its own field of a tool
result, never mixed into the data.

---

## 6. People and authority

**Role.** An RBAC role: a set of permission groups, assigned to a
**team**. A user has what their teams' roles grant. Roles live in the
RBAC system, outside this spec. This is the only meaning of "role".
*Not:* an agent; a kind.

**Team.** A group of users in the RBAC system. Roles are assigned to
teams. A gate's principal set can name a team, which is read for
membership only.

**Permission.** A named action Keel checks with RBAC:
`runs:create`, `runs:adhoc`, `runs:as-service`, `templates:publish`, …
(`authority.md` §12a). A permission lets you start or change something.
It never widens what a run may do: that is the template's grant and the
principal's own access.

**Principal.** On whose behalf a run acts. Downstream systems check
this identity's permissions.

**Requested by.** Who caused the run: an API caller, a trigger's owner,
whoever approved a gate.

**Actor.** The agent's own service identity, as audit logs show it.

**On-behalf-of (OBO).** Calling a tool with a token exchanged from the
principal's credential, per call. Downstream enforces the principal's
own permissions.

**Service credential.** A server called as the actor, not the
principal. Safe for runs that belong to no user. In a run for a user,
it needs an **entitlement check**.

**Entitlement check.** The harness checking, before a write call on a
service credential, that the principal may do it.

**Confused deputy.** A user acting with the bot's rights instead of
their own. Rule R12 exists to stop it.

**Delegation.** A user's consent for a template or pipeline to act for
them when they aren't present. **Stored** delegations are created by
the user, expire, can be revoked, and are tied to what they were shown.
**Session** delegations are minted from a live chat or UI session for
one pipeline run.

**Gate.** Anything waiting on a human:
- a `clarify` question,
- an `approve_action` question,
- a `continuation_approval` on an edge.

One resource, one reply path.
*Not:* a **completion check**.

**Principal set.** Who may answer a gate, resolved when the reply
arrives.

**Clarify / approve.** The two kinds of `AskUser` question. A clarify
answer **resumes** the same run with its transcript. An approve "yes"
starts a fresh run that does only the approved action.

**Suspend / resume.** `AskUser` suspends: the run ends and its
transcript is kept. A principal's reply resumes it as a new run that
inherits the transcript. This is the only path a transcript crosses.

**Bound digest.** The hash of what an approval covers (a plan, a
report, an action). If the content changes, the approval lapses.

**Ask for help.** Two different things:
- `AskUser`, during the run: the run resumes with the answer.
- The `request_help` finisher, as the ending: a person takes the task.

**Narrate.** A tool for a few short progress entries per run, kept as a
durable narrative.

---

## 7. What a run leads to

**Outcome.** The record of how a run ended: terminal, status, summary,
report, finisher, handoff reason, integrity checks, refusal.
*Older word:* "result" (prose).

**Effect.** Something the model does to the world during a run, through
a granted tool. The model decides.

**Sink.** A delivery the template or pipeline declares, done by the
harness after the run, from the outcome. For example: post the summary,
set a commit status, call a Jira transition. The author decides.
**Delivery** is one attempt at a sink, with its own retry state.

**Origin.** Where a request came from (a chat thread, an issue, a PR),
so sinks can reply there (`{origin: true}`).

**Continuation.** An edge from a run's outcome back into the same
template: approve then execute, a spinoff.

**Pipeline.** A versioned graph of **stages** joined by **edges**, with
its own sinks. It is a path, with no loops, branches or joins.
*Older word:* "landing" (`../models.md`) for a stage reached by a handoff.

**Stage.** A template used unchanged inside a pipeline, with its params
bound from the pipeline.

**Edge.** Wires one exit of one stage to the next stage. It has carry,
params, a gate, and an optional **announce** (a line posted to the
origin when the edge is taken).

**Pipeline run.** The durable record of one piece of work: a stage
record per stage entered, child runs, the subject, the final outcome.
Every run belongs to one. A template run on its own is a one-stage
pipeline run.

**Stage record.** One stage within a pipeline run: its state, frozen
params, **attempts**, what it is **waiting on**, its **links**, and the
concurrency key it holds.

**Attempt.** One run at a stage. A new attempt comes from entering the
stage, a **retry**, a resume, an approved action, or a cleared
dependency.

**Retry.** A stage policy: which ending statuses start another attempt
(by default `budget_exhausted`, infrastructure failure and a lost
lease, but not `failed`), how many times, and with what raised budgets.

**Waiting.** A stage not running because of a gate, a child pipeline
run, a concurrency key held elsewhere, a timer, or its settle event.

**Settle.** A stage whose run ended `done` but whose work isn't
finished until something external happens, such as its PR merging.
The stage is `settling` until then, and holds its concurrency key.
*Older word:* the ledger state `handoff` (`../orchestration.md`).

**Link.** A fact written back to a stage once, by something
downstream: the committer's PR, a commit.

**Subject.** The issue or PR a pipeline run is about, with what the
tracker last said about it.

**Spinoff.** Out-of-scope work a run reports and doesn't do. A
continuation turns it into a **child pipeline run**. For `blocks_this`,
the parent stage waits on it.

**Lineage.** How runs relate: the root run, depth, the run a resume
continues, the pipeline run and stage.

---

## 8. Starting work

**Trigger.** What starts a template or a pipeline. Its **source** is
one of:
- `schedule`
- `event`
- `run_outcome`
- `manual`

*Not:* a **monitor**.

**Event.** A normalised external occurrence (a Jira assignment, a PR
update, a chat command), signature-checked and sanitised.

**Firing.** One evaluation of a trigger, recorded even when nothing
ran.

**Filter, dedupe, rate limit.** Trigger-side reasons a firing starts
nothing.

**Concurrency key.** The value that decides whether two pieces of work
contend, such as `repository#branch`. Set on triggers and templates,
and held by a stage while it runs and settles.
*Older word:* `owner` on a ledger task (`../orchestration.md` §2).

**Expression.** A CEL expression the harness evaluates. Never shown to
or written by the model.

---

## 9. Running

**Run.** One template version executed with bound params under one
principal.

**Resolved spec.** What a run actually executes: the flat spec with
params bound, and per agent the model id and the fixed tools array.
Immutable for the run.

**Run state.** `queued`, `provisioning`, `running`, `finalizing`,
`suspended`, `ended`.

**Transcript.** Everything the model saw and did in a run. It has its
own permission, and it is never carried to another run except by a
resume.

**Events stream.** Live progress of a run, without tool bodies.

**Usage.** Turns, tokens per agent and model, cost, with a price
snapshot.

**Refusal code.** The closed vocabulary for every harness refusal or
degradation. The same codes appear in tool results and API errors.

**Ref, artifact.** A handle to bytes kept out of context
(`artifact://`, `table://`, `run://`).

**Lease.** The harness's claim on a stage while a run works on it,
refreshed by the run's activity and reclaimable when it lapses. A run
never sees it.

---

## 10. Words we don't use as concepts

| Word | Why not | Use instead |
|---|---|---|
| **mode** | "Plan" and "implement" are two templates. What makes one investigate and the other write code is its tools, prompt, model and ending contract, and the pipeline runs them in order. No field, tag or prompt line says "you are in plan mode". | the template's name; "configured to plan" if you need a verb. The word survives only in two unrelated field names, `auth.mode` and `run_as.mode`, which mean "credential kind" and "whose authority" |
| **job** | `../tools.md` says "the agent job declares the tools". That is the template's declaration | **template**, **declaration** |
| **lens** | the same thing as a kind | **kind** |
| **landing** | a stage reached by a handoff | **stage** |
| **harness trigger** | collided with **trigger** | **monitor** |
| **completion gate** | collided with **gate** | **completion check** |
| **owner** (of a ledger task) | collided with the owner of a template or trigger | **concurrency key** |
| **ledger**, **task** (ledger sense) | the pipeline run became the durable record; a second store with its own state machine had to agree with it | **pipeline run**, **stage record** |
| **handoff** (ledger state) | collided with the `HandOff` tool | **settling** |
| **role** (for an agent) | role is an RBAC concept | **agent**, **orchestrator**, **sub-agent** |
| **AgentSpec** | "agent" now means one context inside a run | **run spec** |
| **result** (as a field) | prose only | **outcome** |

## 11. Collisions

Resolved on review: `handoff` (the ledger state is gone; it's
**settling**), `Task` (no ledger, so `Task` is only the spawn tool, and
"task" stays informal for the work a run is given), and `role` (RBAC
only; the spawn argument is `kind`). The rest are left as they are,
each with its reason:

| Word | Meanings | Decision |
|---|---|---|
| **source** | a trigger source, an input source, a tool source | leave it: each is always qualified by what it is the source of, and none is a concept on its own |
| **check** | a harness check (every call) and a completion check (on ending) | leave it, but always qualify. They are both deterministic tests, which is the point of the shared word |
| **plan** | a stage, a template, a report, a carried input, `plan_hash` | leave it. They are all the same artefact at different points: the plan a plan run produced |
