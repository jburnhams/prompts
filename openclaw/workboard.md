# OpenClaw Workboard — the team-based coding system, verbatim

From `extensions/workboard/` and
[`docs/plugins/workboard.md`](https://github.com/openclaw/openclaw/blob/v2026.8.1/docs/plugins/workboard.md)
at commit `5f714ef` (`main`, 2026-08-31). **License: MIT.**

Workboard is a bundled, **disabled-by-default** plugin: a Kanban board whose
cards are units of agent work, with a claim protocol, a dependency DAG, a
dispatcher that starts sub-agent workers, and a completion contract the
worker must satisfy or be marked in violation. It is the only thing in this
collection that gives a *multi-agent coding team* a shared durable
work-queue rather than a call graph.

Its own docs are careful about what it is not:

> Workboard is intentionally small: it tracks local operating work for one
> OpenClaw Gateway. It is not a replacement for GitHub Issues, Linear,
> Jira, or other team project management systems.

---

## The worker prompt

The whole prompt a dispatched worker receives, from
`buildWorkerPrompt` in
[`extensions/workboard/src/dispatcher.ts`](https://github.com/openclaw/openclaw/blob/v2026.8.1/extensions/workboard/src/dispatcher.ts):

```text
Work on this OpenClaw Workboard card: ${card.title}

## Worker protocol
Card id: ${card.id}
Claim ownerId: ${ownerId}
Claim token: ${token}

Heartbeat with workboard_heartbeat using the card id and token while working.
When done, call workboard_complete with the card id, token, summary, and proof.
If you recorded proof separately, pass its returned proofId to workboard_complete.
If blocked, call workboard_block with the card id, token, and reason.

${workerContext}
```

Six lines of protocol. Everything else the worker knows comes from the
rendered card, below.

## The worker context format

`buildWorkerContext` in
[`extensions/workboard/src/store-card-helpers.ts`](https://github.com/openclaw/openclaw/blob/v2026.8.1/extensions/workboard/src/store-card-helpers.ts).
Every section is omitted when empty, and each is capped by entry count and
per-entry characters:

```text
# Workboard card ${id}
Title: ${title}
Status: ${status}
Priority: ${priority}
Board: ${boardId}
Agent: ${agentId or (default)}

## Notes
${notes, capped 4000 chars}

## Recent attempts            (last 8)
- ${status} ${model} error=${capped 240}

## Recent comments            (last 12)
- ${body, capped 400}

## Proof                      (last 8)
- ${status}: ${label|command|url|note, capped 400}

## Artifacts                  (last 8)
- ${label|url|path, capped 400}

## Attachments                (last 8)
- ${fileName} · ${byteSize} bytes · ${mimeType} · ${note}

## Worker protocol
${state}: ${detail, capped 500}

## Worker logs                (last 8)
- ${level}: ${message, capped 500}

## Links                      (last 8)
- ${type}: ${title|url|targetCardId}

## Parent results             (last 6 done parents)
- ${id} ${title}: ${summary, capped 500}

## Recent done work by ${agentId}   (5 most recently updated done cards, same board, same assignee)
- ${id} ${title}: ${summary, capped 300}

## Automation
Tenant: ${tenant}
Board: ${boardId}
Skills: ${skills}
Workspace: ${kind} ${path}
Summary: ${summary, capped 400}

## Active diagnostics
- ${severity}: ${title}
```

Two of those sections are the interesting ones. **Parent results** is how a
decomposed DAG passes findings down an edge without a conversation — the
parent's own result summary is rendered into the child's brief. **Recent
done work by `<agentId>`** is a small per-assignee episodic memory scoped to
one board: the last five things this agent finished here, so a worker
re-dispatched onto the same board sees its own recent history without a
memory system.

A card's result summary is resolved by falling back through three places —
`metadata.automation.summary`, then the last non-empty comment, then the
last proof note.

---

## Card lifecycle

```text
status:    triage | backlog | todo | scheduled | ready | running | review | blocked | done
priority:  low | normal | high | urgent
```

Recorded event kinds on a card:

```text
created, edited, moved, linked, specified, decomposed, claimed, heartbeat,
execution_updated, attempt_started, attempt_updated, comment_added,
link_added, proof_added, artifact_added, attachment_added, diagnostic,
notification, dispatch, orchestration, protocol_violation, archived,
unarchived, stale
```

Linked-session lifecycle drives status automatically, with a manual
override that wins:

| Linked session state | Card status |
| --- | --- |
| active | `running` |
| completed | `review` |
| failed, killed, timed out, aborted | `blocked` |

> **Manual review states win.** Moving a card to `review`, `blocked`, or
> `done` stops auto-sync for that card until you move it back to `todo` or
> `running`.

---

## Agent tool descriptions, verbatim

From `extensions/workboard/src/tools.ts` and `tools-orchestration.ts`.

```text
workboard_list
  List Workboard cards with compact claim and diagnostic state. Use before choosing or routing board work.

workboard_create
  Create a Workboard card, optionally with parent dependencies, tenant, skills, workspace, and idempotency key.

workboard_link
  Link a parent card to a child card so the child becomes ready only after parents are done.

workboard_read
  Read one Workboard card and return bounded worker context with notes, attempts, comments, proof, links, and diagnostics.

workboard_claim
  Claim a Workboard card for this agent and move backlog/todo cards into running. Returns a claim token for heartbeats and release.

workboard_heartbeat
  Refresh this agent's Workboard claim heartbeat. Use during long-running card work so diagnostics do not mark it stale.

workboard_release
  Release this agent's Workboard claim after finishing, pausing, or handing off card work.

workboard_comment
  Append a compact comment to a Workboard card.

workboard_proof
  Attach proof or artifact metadata to a Workboard card after running tests, checks, or producing screenshots/logs. Returns proofId; pass it to workboard_complete when that call reports the terminal status for this proof.

workboard_complete
  Complete a claimed Workboard card with a structured summary, proof, artifacts, and created-card manifest.

workboard_block
  Block a claimed Workboard card with a durable reason and release the claim.

workboard_unblock
  Move a blocked Workboard card back to todo after adding enough context.

workboard_attachment_add
  Store a small Workboard attachment in plugin SQLite KV and link it to the card.

workboard_attachment_read
  Read one Workboard attachment from plugin SQLite KV.

workboard_attachment_delete
  Delete one Workboard attachment from plugin SQLite KV and the card index.

workboard_specify
  Turn a rough triage/backlog Workboard card into a specified todo card after reasoning through the requirements.

workboard_decompose
  Fan out a Workboard card into linked child cards and optionally complete the parent orchestration card.

workboard_boards
  List Workboard board namespaces with active, archived, and status counts.

workboard_board_create
  Create or update a Workboard board namespace with persisted SQLite metadata.

workboard_board_archive
  Archive or restore persisted Workboard board metadata.

workboard_board_delete
  Delete an empty non-default Workboard board metadata record.

workboard_stats
  Summarize Workboard counts by status and assignee for one board or all boards.

workboard_runs
  List persisted Workboard run attempts for one card.

workboard_worker_log
  Append a persisted worker log entry to a Workboard card.

workboard_protocol_violation
  Block a card and record a worker protocol violation when work stops without complete/block.

workboard_notify_subscribe
  Persist a Workboard notification subscription in the plugin SQLite store.

workboard_notify_list
  List persisted Workboard notification subscriptions.

workboard_notify_events
  Read replay-safe Workboard notification events without advancing cursors.
```

Selected parameter descriptions:

```text
workboard_create.parents        Parent card ids.
workboard_create.token          Claim token for claimed parent cards.
workboard_create.tenant         Soft tenant namespace.
workboard_create.boardId        Soft board namespace.
workboard_create.createdByCardId  Parent card that created this card.
workboard_create.idempotencyKey Idempotent create key.
workboard_create.skills         Suggested skills.
workboard_create.workspace.kind scratch, dir, or worktree.
workboard_create.workspace.path Absolute dir/worktree path.
workboard_create.workspace.branch Suggested branch.
workboard_create.maxRuntimeSeconds Run timeout seconds.
workboard_create.maxRetries     Retry budget.
workboard_claim.ttlSeconds      Claim TTL in seconds.
workboard_heartbeat.note        Optional compact progress note.
workboard_proof.status          passed, failed, skipped, or unknown.
workboard_proof.command         Command or exact step run.
workboard_complete.proofId      Proof id returned by workboard_proof when resolving that pending proof.
workboard_complete.createdCardIds  Cards created during this run.
workboard_board_create.orchestration.autoDecompose  Mark ready triage cards for decomposition.
workboard_board_create.orchestration.autoDecomposePerDispatch  Maximum orchestration candidates per dispatch.
workboard_board_create.orchestration.orchestratorProfile  Orchestrator profile id.
workboard_notify_subscribe.eventKinds  completed, failed, stale.
```

---

## Claim tokens

`workboard_claim` returns a token. From then on:

- Claimed cards **reject agent-tool mutations from other agents** unless the
  caller holds the token.
- Every card returned by any agent tool or Gateway RPC redacts
  `metadata.claim.token` to `[redacted]`. The token is returned exactly
  once, top-level, from `workboard_claim` itself.
- Recovery — `workboard_promote`, `workboard_reassign`,
  `workboard_reclaim` — deliberately does **not** require the token, so a
  stuck card is always recoverable by an operator or another agent.

## Dispatch

One dispatch pass, in order:

1. Promotes dependency-ready cards.
2. Records dispatch metadata on ready cards.
3. Blocks expired claims or timed-out runs.
4. Marks board-configured triage cards as orchestration candidates.
5. Claims a small batch of ready cards and starts worker runs through the
   Gateway subagent runtime.

Selection: at most **3 workers per pass** by default (`--max-starts`
overrides per request), ordered by priority → position → creation time, and

> A pass starts only one card per owner/agent and skips owners that already
> have running or review work on the board.

Session keys are deterministic per board/card, so re-dispatch routes back
to the same lane instead of forking a new one:

```text
agent:<agentId>:subagent:workboard-<boardId>-<cardId>     (assigned)
subagent:workboard-<boardId>-<cardId>                     (unassigned)
```

If a worker cannot be started after the card is claimed, Workboard blocks
the card, clears the claim, records the run-start failure, and appends a
worker log line.

## Proof is not verification

The docs say this outright, which is rarer than it should be:

> Proof statuses are worker-reported outcomes, not independent
> verification. A `passed` entry means the worker reports that its command
> or check succeeded; consumers that need an independent quality gate
> should inspect the attached command, URL, or artifact and run their own
> verifier.

Proof identity is preserved rather than re-created: `workboard_proof`
returns a `proofId`; passing it to `workboard_complete` resolves that
pending record **in place** without losing its timestamp. Completion proof
without a `proofId` is append-only, "so a later retry cannot rewrite older
history merely because its command or note is identical."

## Diagnostics

Computed from card metadata, not from the session:

| Kind | Condition |
| --- | --- |
| `stranded_ready` | Assigned `todo`/`backlog`/`ready` card not updated in over 1 hour. |
| `running_without_heartbeat` | `running` card with no claim heartbeat or execution update in over 20 minutes. |
| `blocked_too_long` | `blocked` card not updated in over 24 hours. |
| `repeated_failures` | Card's tracked failure count reaches 2 or more. |
| `missing_proof` | `done` card with no proof, artifacts, or attachments. |
| `orphaned_session` | `running` card with a `sessionKey` but no `execution` metadata. |
| `archived_but_active` | Archived card remains in any non-`done` lifecycle status. |

## Workspace authority

Dispatch does not spawn OS processes; normal sub-agent sessions own
execution. Workspace paths follow the *caller's* filesystem authority, and
the recorded authority is intersected with the current caller's authority
again at dispatch, "so a persisted card cannot widen a later caller's
access."

For a workspace-bound (non-admin) caller, a `worktree` request is narrowed
to a directory workspace and the target worker must use

> a writable, non-shared Docker sandbox for that exact workspace, without
> elevated execution, persisted host/node exec overrides, or unclassified
> plugin and MCP tools. Workboard enumerates its registered tools instead
> of trusting a `workboard_*` prefix, and dispatch refuses a hot Docker
> container whose live mount/config hash is stale.

For a full-host caller, Workboard materialises a managed worktree named
`wb-<card-id>`, runs the worker there, and writes the resolved path and
branch back onto the card. On run end it removes the checkout **only when
it is provably lossless** — clean `git status --porcelain` and no unpushed
commits.

## CLI and slash command

```bash
openclaw workboard list [--board <id>] [--status <status>] [--include-archived] [--json]
openclaw workboard create "Fix stale card lifecycle" --priority high --labels bug,workboard
openclaw workboard show <card-id> [--json]
openclaw workboard move <card-id> --status <status> [--json]
openclaw workboard dispatch [--board <id>] [--json]
```

Only `dispatch` needs the Gateway. If the Gateway is unreachable, the CLI
falls back to **data-only dispatch** against local SQLite: it can promote
dependencies, clean stale claims and block timed-out runs, but cannot start
workers. Auth, permission and validation failures from a *reachable*
Gateway are not treated as unavailable.

## Storage

A plugin-owned relational SQLite database under the OpenClaw state
directory — boards, cards, labels, lifecycle events, run attempts,
comments, dependency links, proof, artifact references, attachment metadata
and blobs, diagnostics, notifications, worker logs, protocol state and
subscriptions all as tables, not plugin key-value entries. The repo's
`AGENTS.md` makes that mandatory: *"Storage default: SQLite only. Do not add
JSON/JSONL/TXT/sidecar files for OpenClaw-owned runtime state."*

## RPC scopes

```text
operator.read   cards.list, cards.export, cards.diagnostics, attachment list/get,
                notification event reads, boards.list, cards.stats, cards.runs
operator.write  everything else, including cards.dispatch and cards.bulk
operator.admin  no method requires it; it only widens accepted host paths
```
