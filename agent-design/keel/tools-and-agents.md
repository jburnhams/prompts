# Keel: tools

Tool sources, groups, grants, visibility, agents and harness checks. Part of [Keel](./README.md). Section numbers are shared across Keel's files, so a reference like §7f means the same section everywhere; [the README](./README.md#files) lists which file holds each.

---

## 4. Tools

Schema: [`tools.schema.json`](./schemas/tools.schema.json).

### 4a. Sources

There are three namespaces in a tool address:

- `builtin/<Tool>`: Keel's built-in tools, implemented by the harness
  itself. Not every tool is MCP.
- `mcp:<server>/<tool>`: anything served by a registered MCP server.
- `harness/<Tool>`: tools generated from contracts (§5). These can't be
  referenced in a group, so no one can grant `Complete` to a sub-agent.

**The built-in catalogue**, with the uses each allows (§5a). A template
can narrow a tool's uses; it can't widen them.

| Tool | Uses | What |
|---|---|---|
| `Read`, `Grep`, `List` | call | read the working tree and other refs |
| `Edit`, `Write` | call | change the working tree; never registered on a read-only workspace |
| `Bash` | call | run commands, with the git-write blocklist applied |
| `InspectImage` | call | look at an image through the sighted sub-model |
| `RequestHelp` | finish | post to a channel and end the run `blocked` |

**Keel knows nothing about pull requests**, or any other domain object.
Opening one is an MCP tool like any other, such as
`mcp:scm/open_pull_request`, granted for use during the run, as an
ending, or both. Two generic mechanisms are what make that work:

- **A server can be bound to the workspace** (`workspace: bind`). A
  per-run server process starts with the run's checkout mounted, so its
  tools can commit, push and open a review from the working tree. For a
  pipeline sink it starts against the stage's retained checkout. The
  model still can't run git writes through `Bash`.
  *(Added 2026-10-26.)* **The bound server does not trust the
  checkout's git metadata.** Blocking git writes in `Bash` is not
  enough: `Bash` can write `.git/config` or `.git/hooks/` with `echo`,
  and git configuration is code (`core.hooksPath`, `core.fsmonitor`,
  `core.sshCommand`, `include`, upload-pack overrides), so the server's
  next `git push`, holding the deployment's credentials, would run the
  agent's choice of program outside the sandbox. Two rules close it.
  The agent's sandbox mounts the checkout's git directory (including
  submodule and linked-worktree git folders) **read-only**, so `Bash`
  can still read history and diffs but cannot change what git will
  execute; the bound server owns the only writable copy. And the server
  runs every git command with hooks and fsmonitor disabled, `include`
  ignored, and a fixed allowlist of transport protocols, passing
  credentials through a helper rather than the environment. Claude Code
  reached the same conclusion from the other side, write-denying the
  folders git reads and refusing to suggest a command in a submodule
  whose git folder the sandbox could write
  (`../../agent-git-vcs.md` §8).
- **A tool's result can write stage links** (`ToolRef.links`, e.g.
  `pull_request: result.url`). A stage's settle wait then watches that
  link, whoever opened the PR.

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
- say how the agent may use it (`use`: `call`, `finish`, or both, §5a),
  and what ending it gives;
- map fields of its result to stage links (`links`);
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
| Granted | `agents.<a>.grant[]` ⊆ `tools.groups` | at the executor, every call |
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
- a `scope`: what this sub-agent is for, rendered into its opening
  message as a `<scope>` block before the spawner's brief. Several
  sub-agents can share one prompt version this way, each with its own
  scope and grant. Forge's four review specialists share
  `forge.reviewer@1`, and `visual_reviewer` alone is granted `vision`;
- `spawn_args`: extra required `Task` fields, such as the validator's
  `finding`;
- `conventions`: its own `<conventions>` block, rendered after its
  scope and narrowed by `tags`. Forge's `security_reviewer` gets
  `security`, `visual_reviewer` gets `ux`, and `conventions_reviewer`
  gets the whole corpus. Without it, a sub-agent sees only the brief;
- a `report_schema` the harness validates.

What Forge called a "kind" is a **tag** in Keel. Forge's kind (also
spelled role, and lens) picked a specialist's prompt scope, its extra
tools and its conventions sections at spawn time. A Keel tag does only
the last of those: it picks which conventions sections go into an
agent's opening message. Prompt scope is the sub-agent's `scope`, and
tools are its grant, so a tag can never widen what an agent may do. The
template sets every tag; a spawner can't pass one and an agent can't
ask for one.

The rules from `../tools.md` §"One job declares the tools", and where each
is enforced:

- **Siblings, not a chain.** Every agent's grant is checked against
  `tools.groups`, not against its spawner's grant (R1). A data
  sub-agent can hold a server the orchestrator never sees.
- **Only the template grants.** A conventions file can tag sections with
  tags; it can't add a grant to anything.
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
- **A sub-agent's report reaches its spawner as data** *(added
  2026-10-26)*. The `Task` result is wrapped in a nonce-tagged
  `<subagent_report>` block carrying the lowest trust of anything that
  sub-agent read: `untrusted` if it read a ticket, a PR, a web page, a
  tool result from an external server or a file outside the template's
  config, which is nearly always. The spawner may use the facts it
  reports; text in it that tells the spawner what to do, or claims
  approval or scope, is a finding to report and never an instruction
  (`../formats.md` §1b's consuming rule, now applied to delegates). A
  `report_schema` makes this easier to keep, since a structured report
  has fewer places for instructions to hide, but does not replace it.
  **Supersedes** `../tools.md`'s usage note that "a sub-agent's report
  should generally be trusted for `general-purpose` research tasks".
  The reason: a delegate that read injected text relays it with the
  orchestrator's own trust unless the boundary says otherwise, and the
  auto-mode red-team found handoffs between contexts to be a working
  channel (multi-agent attacks succeeded 18/18 against auto mode and
  0/20 against the hardened Auto Mode ++; `../../agent-permissions-approval.md` §2d). Claude Code's
  coordinator rule, that an approved action is run by a worker that
  never read the untrusted input (`../../agent-subagent-architectures.md`
  §7c), is the same boundary drawn from the other side.

### 4d. Harness checks

`tools.checks[]` plus `Deployment.defaults.checks`: `input_sanitizer`,
`git_write_blocklist`, `read_before_edit`, `read_name_blocklist`,
`completion_checklist`, `post_run_crosscheck`, `conventions_write_flag`,
`secret_scan`, `egress_allowlist`, `anchor_validation`. They aren't
part of any grant, so no agent, param or prompt can remove them, and
they apply to every agent. Goose's sub-agents running with no hooks
(`../../agent-subagent-architectures.md` §7d) is the failure this is
shaped against.

### 4e. Server requests and deferred results in a hands-off run *(added 2026-11-09)*

**Amendment.** Keel calls MCP servers, and an MCP server can do two
things during a call that §4a–§4d did not cover: ask for input
(elicitation), and hand back a task handle instead of a result (the
`io.modelcontextprotocol/tasks` extension). A Keel run usually has no
person watching it, so both need rules.

**Elicitation is answered by the harness, never by waiting.**

- An elicitation request is answered `cancel` at once, unless the
  deployment configures an **elicitation responder** for that server: a
  fixed rule in deployment configuration that answers it from
  configuration or the run's own `param` inputs. A responder can never
  come from a template param, a repository file, the model or a
  sub-agent.
- The model is never shown the request as something to answer, because
  an answer would be the model speaking for a person. The tool result
  carries a harness note instead: the server asked for input this run
  cannot supply, the request was cancelled, the call may have done
  nothing; if the step needs that input, use `AskUser` where the
  template grants `human.ask_user`, or end `blocked` and name what is
  needed.
- This holds for every agent, sub-agents included ("No delegate has a
  human channel", `../tools.md`), and the cancellation is a
  `server_request` event in the run's record.
- There is no setting that makes a run wait for a person on an
  elicitation. `AskUser` is the only way to suspend for a person, and it
  binds the question to what is approved (`../formats.md` §5).

**A task handle is followed, never reissued.**

- When a call returns a task handle, the harness records it (server,
  tool, arguments digest, task id, TTL) in the run's events and polls it.
  The model gets the result as the call's result, or as an event if the
  model has moved on (as with background `Bash`).
- If the harness loses track (polling fails past the TTL, the server
  says it does not know the task, the run is ending), the result is
  `outcome: unknown` with a fixed note, adapted from Claude Code
  2.1.319: the task may still be running or may have ended; do not
  report it as done or failed; do not call the tool again, because a
  second call may repeat the work. `unknown` is never mapped to an
  error code that a retry or a monitor would treat as a failure.
- A run that ends with an `unknown` task lists it in its report, and the
  pipeline treats it as an external write that may have happened
  (§7f's existing rule for a dead attempt's writes).
- **`interrupted_attempt` gains `pending_tasks`**: task handles that
  were still unresolved when the attempt died or ended. A retry's fixed
  paragraph tells it to follow each handle (a `harness/FollowTask` call
  the harness provides only when the block is present) before doing that
  step again. A handle past its TTL is listed as `expired`, with the
  same "may have run" wording as a call in flight.

**Why.** Claude Code 2.1.319 cancels elicitation when no one will answer
("an MCP server's request for input is cancelled unless an Elicitation
hook answers it") and treats a task it can no longer follow as an
unknown outcome that must not be repeated
(`../../agent-permissions-approval.md` §2g,
`../../agent-run-recovery.md` §5). Keel had neither rule. Without the
first, a hands-off run either hangs on a request nobody sees or lets the
model invent the answer. Without the second, a retry runs the long job
again. The responder is deployment-only for the same reason
`denyInsteadOfPrompting` ignores project settings: a repository should
not decide who answers for its own run.

**What it supersedes.** Nothing. `../adk.md` defers the tasks extension
for the Java stack; this section is what Keel does where a server offers
it.
