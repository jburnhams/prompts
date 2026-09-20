# Interop: how an agent is reached, and how it reaches other agents

`docs/agents/{channels,email,webhooks}.md`, `examples/{a2a,x402}/` at
`c076e4c`. Channels is marked experimental and its "interface _will_
change".

Everything in this collection assumes the agent is invoked one way: a
human types into a CLI, or a webhook fires a CI job. This SDK treats
**how the agent is addressed** as a design surface in its own right, and
two of its answers are categories the collection has no coverage of at
all.

## A2A: an agent as a discoverable service

`examples/a2a/` exposes an agent as an
[A2A protocol](https://a2a-protocol.org/) server:

> - **Agent Card discovery** at `/.well-known/agent-card.json`
> - **JSON-RPC transport** (`message/send`, `message/stream`) via the `@a2a-js/sdk` server
> - **SSE streaming** for real-time task status updates
> - **DO-backed TaskStore** using Durable Object SQLite for persistent task state

```sh
curl http://localhost:5173/.well-known/agent-card.json
```

**This collection has zero other coverage of agent-to-agent protocols**,
and the shape is worth knowing because it is the mirror image of MCP.
MCP is how an agent reaches a *tool*; A2A is how an agent reaches another
*agent* — and the difference is that the far side is not a function that
returns, it is a peer that accepts a **task** and streams **status**
until it is done.

Three consequences fall out of that, visible in the example:

- **Discovery is a well-known URL, not a registry.** `/.well-known/agent-card.json`
  is the same shape as `robots.txt` or an OIDC discovery document: point
  at an origin, learn what it can do. Compare MCP, where the client is
  configured with a server and then calls `tools/list`.
- **The unit is a task with a lifecycle**, not a call with a return
  value. Hence `message/stream` and SSE status updates, and hence the
  **TaskStore** — tasks outlive requests, so they need durable storage.
  Cloudflare backs it with Durable Object SQLite, which is the one thing
  they have that most A2A implementations have to build.
- **The two protocols compose rather than compete.** The same agent in
  this SDK can be an MCP server, an MCP client, and an A2A server
  simultaneously. Nothing forces a choice.

Against `../agent-subagent-architectures.md`, this is a fourth
delegation shape, after in-process sub-agents, stateless `Task` calls,
and [dynamic agents](./delegation-and-approval.md): **delegation across
an organisational boundary**, where the far agent is not yours, has its
own model and its own tools, and you learn what it can do by fetching a
document.

The example's stated design point is worth keeping too — *"The server
uses the SDK's `DefaultRequestHandler` + `AgentExecutor` to avoid
hand-rolling A2A protocol logic"*, which is the same reason nobody
hand-rolls MCP framing any more.

## x402: an agent with a wallet

`examples/x402/`:

> HTTP payment gating using the [x402 protocol](https://x402.org) with
> Hono middleware. A `/protected-route` requires a **$0.10 payment on Base
> Sepolia** — an Agent with a test wallet **pays automatically**.
>
> - **`@x402/hono` middleware** — `paymentMiddleware()` gates any Hono route behind a price
> - **`@x402/fetch`** — `wrapFetchWithPayment(fetch)` wraps `fetch` so the agent signs and pays automatically

Also new to this collection, and the mechanism is smaller than it sounds:
x402 revives HTTP `402 Payment Required`. The server responds 402 with
payment terms; the client signs a payment and retries. `wrapFetchWithPayment`
makes that transparent — **the agent's `fetch` just works, and money
moves.**

Two observations, one of which is a warning.

**It closes a loop the collection has been missing.** `agent-data-analysis.md`
§12 and `agent-local-compute.md` §8 both record that **no harness reasons
about what anything costs**. This is the first source here where an agent
can *incur* a cost directly rather than through an API key someone else
pays for — and therefore the first where cost is a runtime value rather
than a billing surprise.

**And it is the sharpest version of the permission question in the
collection.** `wrapFetchWithPayment(fetch)` means every `fetch` the agent
makes is potentially a purchase, with no approval step in the path. The
collection's whole permissions story — `agent-permissions-approval.md`'s
tiers, Cloudflare's own `requiresApproval` — is about gating
consequential actions, and this wraps the least-gated primitive an agent
has. The example is a testnet demo and does not pretend otherwise; the
design point stands regardless. **If an agent can pay, `fetch` is a
destructive tool**, and nothing in the wrapper's shape says so.

## Channels: one interface, many messaging platforms

> `agents/channels` gives an agent one interface for sending and
> receiving messages across different platforms. Use a Channel directly,
> expose it as an AI tool, or register it with a durable `ChannelHost`
> that owns **routing and delivery recovery**.

Three usage modes from one abstraction — direct, as a tool, or hosted —
and the third is the interesting one. A `ChannelHost` owning *delivery
recovery* is the counterpart to the recovery-aware delivery in
[`durability.md`](./durability.md): if an agent is reachable on Slack,
SMS and email, "did this message actually arrive" is a per-platform
question that something has to own.

Exposing a channel **as an AI tool** is the notable option: the model can
send a message as a tool call, which makes "notify the team when this
finishes" an ordinary action rather than a harness feature. Set against
`../agent-design/`'s `AddComment`, which is one tool bound to two
destinations (Jira, PR), this is the generalisation — and it raises the
same question `AddComment` answers deliberately: *which destinations may
the model write to without asking?*

## Email and webhooks: inbound addressing

**Email** is bidirectional — send via a `send_email` binding, receive via
a routing rule that delivers inbound mail into the Worker, plus:

> Optional: an `EMAIL_SECRET` secret if you want **secure reply routing**

Reply routing is the non-obvious hard part: a reply has to find its way
back to the *specific agent instance* that sent the original, and the
only carrier is the address or subject line. Signing that with a secret
is what stops a stranger addressing an arbitrary agent by guessing a
reply address. It is the same problem
`../agent-permissions-approval.md` treats as untrusted-input handling,
arriving through a channel where the *routing key itself* is
attacker-supplied.

**Webhooks** make the routing explicit:

> Receive webhook events from external services and route them to
> dedicated agent instances. **Each webhook source (repository, customer,
> device) can have its own agent with isolated state**, persistent
> storage, and real-time client connections.

```typescript
import { Agent, getAgentByName, routeAgentRequest } from "agents";
…
async function verifyGitHubWebhook(…)
```

`getAgentByName` is the whole idea: because agents are **named durable
objects**, "the agent for `acme/payments`" is an address, not a lookup.
A per-repository agent with its own accumulated state is one line, where
every other harness in this collection would need a database and a
session key.

Signature verification is in the quick-start rather than an appendix,
which is the right placement for the one step that decides whether the
endpoint is an open door.

## What transfers

The protocols are specific; three questions are not, and none is asked
anywhere in `agent-design/`:

1. **Is this agent discoverable, and by whom?** A `/.well-known/` card
   makes an agent a service. That is a different security posture from a
   CLI, and it arrives the moment anyone wants agent-to-agent work.
2. **How is an agent addressed, and who may address it?** Per-source
   instances make isolation free and make the routing key a security
   boundary — for webhooks a signature, for email a signed reply address.
3. **Can the agent spend money?** If yes, the least-gated primitive it
   has just became consequential, and the permission model has to reach
   `fetch`.
