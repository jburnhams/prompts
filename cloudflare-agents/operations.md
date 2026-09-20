# Operations: running for weeks, and knowing what happened

`docs/agents/observability.md`, `scheduling.md`, `queue.md`, `tasks.md`,
`retries.md`, `state.md`, `mcp-client.md`, `mcp-transports.md` at
`c076e4c`.

The operational surface. `agent-self-verification.md` asks how an agent
knows it is done; nothing in this collection asks **how an operator knows
what an agent did**, or what happens when it needs to run on Tuesday.
This SDK answers both, and the observability channel list is the single
most useful artifact in the folder for anyone instrumenting an agent.

## Thirteen channels, and what they instrument

> Agents emit structured events for every significant operation — RPC
> calls, state changes, schedule execution, workflow transitions, MCP
> connections, and more. These events are published to diagnostics
> channels and are **silent by default (zero overhead when nobody is
> listening)**.

```ts
{
  type: "rpc",                        // what happened
  agent: "MyAgent",                   // which agent class emitted it
  name: "user-123",                   // which agent instance (Durable Object name)
  payload: { method: "getWeather" },  // details
  timestamp: 1758005142787            // when (ms since epoch)
}
```

| Channel | Event types |
|---|---|
| `agents:state` | `state:update` |
| `agents:rpc` | `rpc`, `rpc:error` |
| `agents:message` | `message:request`, `message:response`, `message:clear`, `message:cancel`, `message:error`, `tool:result`, **`tool:approval`** |
| `agents:chat` | `chat:request:failed`, `chat:recovery:*`, **`chat:stream:stalled`**, **`chat:context:compacted`** |
| `agents:transcript` | **`chat:transcript:repaired`** |
| `agents:fiber` | `fiber:run:*`, `fiber:recovery:*` |
| `agents:agent_tool` | `agent_tool:recovery:*` |
| `agents:schedule` | `schedule:create`, `schedule:execute`, `schedule:cancel`, `schedule:retry`, `schedule:error`, **`schedule:duplicate_warning`**, `queue:create`, `queue:retry`, `queue:error` |
| `agents:lifecycle` | `connect`, `disconnect`, `destroy` |
| `agents:workflow` | `workflow:start`, `workflow:event`, `workflow:approved`, `workflow:rejected`, `workflow:terminated`, `workflow:paused`, `workflow:resumed`, `workflow:restarted` |
| `agents:mcp` | `mcp:client:preconnect`, `mcp:client:connect`, `mcp:client:authorize`, `mcp:client:discover`, `mcp:client:close` |
| `agents:email` | `email:receive`, `email:reply` |

**Read the bolded ones as a list of failure modes somebody hit in
production.** They are not generic telemetry; each one names a specific
thing that goes wrong with agents and that nothing else in this
collection instruments:

- **`chat:context:compacted`** — compaction is an *event*, not a silent
  internal. `agent-context-compaction.md` records several harnesses where
  compaction happens invisibly and the user discovers it by noticing the
  agent forgot something. Emitting it makes "why did it lose that" answerable.
- **`chat:transcript:repaired`** — the transcript was *malformed* and got
  fixed. Orphaned tool calls, a result without a call, an interrupted
  stream. That this needs its own channel says it is routine.
- **`chat:stream:stalled`** — the provider stopped sending without
  closing. A hang that is not an error and has no exception.
- **`schedule:duplicate_warning`** — the same task scheduled twice.
  Cheap to emit, and the symptom otherwise is "why did this run four times".
- **`tool:approval`** — approvals are auditable as events, not just as UI.
- **`*:recovery:*` on three channels** (chat, fiber, agent_tool) — recovery
  is expected often enough to be a first-class observable.

The `{agent, name}` pair is the other quiet good idea: every event
identifies the class *and* the instance, so a fleet of agents is
queryable per-tenant without inventing a correlation id.

`subscribe()` is typed per channel, and events are **silent by default**
— no cost unless something is listening, which is what makes it
reasonable to emit this many.

## Scheduling: four modes, persisted

> Schedule tasks to run in the future — whether that's seconds from now,
> at a specific date/time, or on a recurring cron schedule. **Scheduled
> tasks survive agent restarts and are persisted to SQLite.**

| Mode | Syntax | Use Case |
|---|---|---|
| **Delayed** | `this.schedule(60, ...)` | Run in 60 seconds |
| **Scheduled** | `this.schedule(new Date(...), ...)` | Run at specific time |
| **Cron** | `this.schedule("0 8 * * *", ...)` | Run on recurring schedule |
| **Interval** | `this.scheduleEvery(30, ...)` | Run every 30 seconds |

> Under the hood, scheduling uses Durable Object alarms to wake the agent
> at the right time. Tasks are stored in a SQLite table and executed in
> order.

Almost nothing else in this collection can do this. Every coding and
review agent here is invoked — by a human, a webhook, or a CI run — and
has no way to arrange its own future. An agent that can schedule its own
wake-up is a different category of thing, and the design consequence is
that **the agent's identity has to outlive the process**, which is what
the Durable Object provides and a CLI does not.

## Three kinds of background work, distinguished

The SDK ships `queue`, `tasks` and `workflows`, and the distinctions are
drawn carefully rather than left to taste:

**Queue** — *"Durable background work … persists a callback name and a
payload, runs from the Durable Object's alarm loop one item at a time in
push order, retries when the callback throws, and survives the object
leaving memory."* Serial, FIFO, retrying.

**Tasks** — *"durable, replayable background work … A run of a definition
survives process loss, deployments, and hibernation: completed steps
return journaled results, sleeps consult persisted deadlines, and
execution continues from the first unfinished step."* Journaled steps,
so a multi-step run resumes mid-way. Note *"The capability never touches
the Durable Object's physical alarm"* — it composes rather than competing
for the one alarm slot.

**Workflows** — independent of the agent, per-step retries, multi-step
orchestration, and the home of durable approval gates
(`waitForApproval`).

Plus **fibers** ([`durability.md`](./durability.md)) for work that is
part of the agent's own execution.

Four mechanisms for "do something later" is a lot, and the
differentiators are real: *is it part of this turn* (fiber), *is it
serial work this agent owns* (queue), *does it need step-level
journaling* (tasks), *should it outlive the agent entirely* (workflow).
Most harnesses have zero of these and use a `Bash` background process.

## Retries, with the failure modes named

> - **Exponential backoff** — each retry waits longer than the last
> - **Jitter** — randomized delays prevent thundering herd problems
> - **Configurable** — tune attempts, delays, and caps per call site
> - **Built-in** — schedule, queue, and workflow operations retry automatically

`this.retry()` for arbitrary async work, and automatic retry on the three
background mechanisms. Jitter for thundering herd is the detail that says
someone ran this at scale: a hundred agents whose scheduled task failed
at the same instant will otherwise retry at the same instant.

## State: synchronised, not just persisted

> Agent state is:
> - **Persistent** — Automatically saved to SQLite, survives restarts and hibernation
> - **Synchronized** — Changes broadcast to all connected WebSocket clients instantly
> - **Bidirectional** — Both server and clients can update state
> - **Type-safe** — Full TypeScript support with generics

Bidirectional plus multi-client is the part with no analogue in this
collection, and it is what makes
[`delegation-and-approval.md`](./delegation-and-approval.md)'s readonly
connections necessary in the first place. Every other harness here has
exactly one user and no concurrent observers, so "who may mutate agent
state" has never had to be a question.

## MCP in both directions

The SDK is an MCP **client** and an MCP **server**, and the server story
has a live migration worth recording:

> - Current SDK v2 servers use `createMcpHandler`, a **per-request
>   stateless Worker handler** with no Durable Object or WebSocket bridge.
> - Retained SDK v1 servers use the **deprecated, feature-frozen**
>   `McpAgent`, which provides sessionful transports through a Durable
>   Object and internal WebSocket bridge.
>
> The current stateless handler also accepts stateless 2025-era Streamable
> HTTP requests by default. It does not expose standalone legacy SSE.

**The direction of travel is sessionful → stateless**, and from the
vendor best positioned to make sessions cheap — they already have a
durable object per session. They deprecated it anyway. That is a data
point worth having when weighing a stateful MCP server design:
`data-agents/jupyter-mcp/`'s `use_notebook` modal pointer is exactly the
sessionful shape, and it needs the explicit-`notebook_name` escape hatch
precisely because sessions and concurrency interact badly.

On the client side, `MCPClientManager` is a lifecycle capability, and the
`agents:mcp` channel instruments `preconnect`, `connect`, `authorize`,
`discover` and `close` separately — so "the tools are missing" resolves
to which of those five failed, which is more than most MCP clients can
say.

`securing-mcp-servers.md` is the other half, covering OAuth 2.1 via
`workers-oauth-provider`, and it names the proxy case plainly:

> most MCP servers aren't just servers, they can actually be OAuth
> clients too. Your MCP server might sit between Claude Desktop and a
> third-party API like GitHub or Google. To Claude, you're a server. To
> GitHub, you're a client. … There are a few security footguns to
> securely building a proxy server.

with `redirect_uri` validation called out first, and a handling rule for
credentials that belongs in any design:

> Treat `authInfo.token` and `authInfo.extra.props` as sensitive and do
> not log or return them.

## What transfers

The mechanisms are platform-specific; three of the *questions* are not,
and none of them is currently asked anywhere in `agent-design/`:

1. **What does this agent emit that an operator can subscribe to?** The
   channel table is a ready-made checklist, and the non-obvious entries
   (compaction, transcript repair, stream stall, duplicate schedule) are
   the ones worth copying.
2. **Can the agent arrange its own future?** If yes, its identity has to
   outlive the process.
3. **Which kind of "later" is this?** Part of the turn, serial owned
   work, journaled multi-step, or independent — four different answers
   with four different failure modes.
