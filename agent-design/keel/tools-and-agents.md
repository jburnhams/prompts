# Keel: tools

Tool sources, groups, grants, visibility, agents and harness checks. Part of [Keel](./README.md). Section numbers are shared across Keel's files, so a reference like §7f means the same section everywhere; [the README](./README.md#files) lists which file holds each.

---

## 4. Tools

Schema: [`tools.schema.json`](./schemas/tools.schema.json).

### 4a. Sources

There are three namespaces in a tool address:

- `builtin/Read`: in-process harness tools (`Read`, `Edit`, `Write`,
  `Bash`, `Grep`, `List`, `InspectImage`).
- `mcp:<server>/<tool>`: anything served by a registered MCP server.
- `harness/<Tool>`: tools generated from contracts (§5). These can't be
  referenced in a group, so no one can grant `Complete` to a sub-agent.

An `McpServer` records the transport, the pinned protocol version
(capped at what the SDK speaks, `../adk.md` §0), the auth mode (§8),
whether its `instructions` text is ignored or included as untrusted
context, a description cap, the two-axis limits from `../cloudflare.md`
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
`retry` defaults to `never` unless the tool is idempotent: `../adk.md` §4's
finding that retries make non-idempotent tools dangerous, as a field.

`../tools.md`'s three questions map onto three fields:

| Question | Field | Enforced |
|---|---|---|
| Granted | `agents.<a>.grant[]` (+ `kind_grants` for the kind given at spawn) ⊆ `tools.groups` | at the executor, every call |
| Registered | derived at resolve: grant + generated tools, as one fixed array per agent (`ResolvedSpec.agents.<a>.registered`) | provider validation |
| Visible | `ToolGroup.visibility`, overridden by `agents.<a>.visibility` | nothing; it shapes what the model tries |

`hidden` groups need a way to become visible: `hatches.expand.reveals`
or a monitor's `reveal`. R8 warns when a hidden group has
neither. How "deferred" and "hidden" are realised depends on the
deployment's provider flags (`deferred_tools`, `reveal`) and on whether
the agent's model supports them (`supports_reveal` on the tier). The
spec states intent; the resolver picks the mechanism and records it in
`ResolvedSpec.agents.<a>.deferred_tools` and `.reveal`.

- **Anthropic (Claude API, Claude Platform on AWS, Bedrock InvokeModel,
  Vertex):** a hidden or deferred tool is declared in `tools` with
  `defer_loading: true`. The harness reveals it with **mid-conversation
  tool changes** (beta `mid-conversation-tool-changes-2026-07-01`): a
  `role: "system"` message appended after a user turn, carrying a
  `tool_addition` block that references the tool by name. A
  `tool_removal` block withdraws one the same way. Neither changes the
  cached prefix, so "the tools array and system prompt are fixed for a
  run" still holds. Supported on Opus 5, Opus 5.5, Opus 4.8, Fable 5 and
  5.1 and Sonnet 5.5, not on Sonnet 5, and not on Foundry. A tier whose
  model isn't covered sets `supports_reveal: false`. One caution, if a
  deployment ever adds Anthropic's own tool-search tool: search can find
  a deferred tool by itself, so a tool that must stay hidden would have
  to stay out of `tools` until it's revealed. Keel's own `Expand` isn't
  that tool, so this doesn't arise today.
- **OpenAI Responses:** client-executed `tool_search` and
  `additional_tools`.
- **Bedrock `Converse`, or a model without reveal:** `hidden` resolves to
  `deferred` where deferral exists, otherwise to `loaded`, or to the
  once-only array growth that `hatches.expand.array_growth` permits
  (`../models.md` §4a). Authority is unaffected in every case: the
  executor checks the grant on every call.

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
  carries the kind in a field it calls `role`; Keel's generated
  `Task` calls it `kind`;
- `kind_grants`: the tool half of "kinds: one vocabulary, three
  resolutions";
- `kind_scope`: the prompt half. Each kind's scope text is rendered into
  the sub-agent's opening message as a `<lens>` block, before the
  spawner's brief. The system prompt stays one per sub-agent, so it
  caches across every lens;
- `spawn_args`: extra required `Task` fields, such as the validator's
  `finding`;
- a `report_schema` the harness validates.

The rules from `../tools.md` §"One job declares the tools", and where each
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
  (`../models.md` §7). That is a template author's decision, visible in the
  file, never a runtime one.

### 4d. Harness checks

`tools.checks[]` plus `Deployment.defaults.checks`: `input_sanitizer`,
`git_write_blocklist`, `read_before_edit`, `read_name_blocklist`,
`completion_checklist`, `post_run_crosscheck`, `conventions_write_flag`,
`secret_scan`, `egress_allowlist`, `anchor_validation`. They aren't
part of any grant, so no agent, param or prompt can remove them, and
they apply to every agent. Goose's sub-agents running with no hooks
(`../../agent-subagent-architectures.md` §7d) is the failure this is
shaped against.
