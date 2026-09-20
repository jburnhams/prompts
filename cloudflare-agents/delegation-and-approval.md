# Delegation and approval

`docs/agents/sub-agents.md`, `docs/agents/agent-tools.md`,
`docs/agents/human-in-the-loop.md`, `docs/agents/readonly-connections.md`
at `c076e4c`.

## Dynamic agents (facets): a sub-agent with its own database

> Dynamic agents are child Durable Objects **colocated under and
> supervised by** a parent agent, built on the runtime's facet primitive.
> Each child runs in its **own isolate** with its **own SQLite database**,
> but lives inside the parent's Durable Object: the parent spawns it, can
> abort or delete it, and **is the only way to reach it**.

```typescript
export class Supervisor extends Agent {
  @callable()
  async runJob(runId: string, input: string) {
    const worker = await this.dynamicAgents.get(JobRunner, runId);
    return worker.execute(input);
  }

  @callable()
  cancelJob(runId: string) {
    // Stops the child immediately; its storage survives for inspection.
    this.dynamicAgents.abort(JobRunner, runId, new Error("cancelled"));
  }

  @callable()
  async cleanupJob(runId: string) {
    // Wipes the child's storage and registry entry.
    await this.dynamicAgents.delete(JobRunner, runId);
  }
}
```

`agent-subagent-architectures.md` catalogues sub-agents that are
**stateless one-shot calls** — Claude Code's `Task`, and the design's own
`Task→general-purpose`. This is the far end of that axis: a child with
durable storage, an independent isolate, a lifecycle the parent owns, and
a drill-in URL.

Three details worth keeping:

**Abort and delete are separate verbs, and the comments say why.**
`abort` stops the child *and leaves its storage for inspection*; `delete`
wipes it. A failed sub-agent run whose working state is still readable is
a debugging affordance almost nothing else here offers — the collection's
other sub-agents evaporate, taking the reason with them.

**The parent is the only route.** Not a convention — a property of the
facet primitive. A capability boundary that cannot be bypassed by knowing
the child's name.

**The vendor tells you when not to use it**, which is the rarest kind of
documentation:

> Do **not** use dynamic agents to model an open-ended set of independent
> peers — many chats, documents, or sessions per user. Those want one
> top-level Durable Object each plus a per-user index.

and records its own naming history rather than quietly rewriting it:

> **Naming**: dynamic agents were previously called **sub-agents**. The
> `subAgent()` / `hasSubAgent()` / … methods still work and now delegate
> to the same `this.dynamicAgents` capability; they are deprecated in
> place.

## Agent tools: delegation the parent model decides on

> Agent tools let one chat agent dispatch another chat-capable sub-agent
> as part of its work … The child is a real sub-agent with its own Durable
> Object storage, messages, tools, resumable stream, and drill-in URL. The
> parent keeps a small **run registry** so clients can render the child
> timeline, **replay it after refresh**, and clean it up later.

```ts
export class Researcher extends Think<Env> {
  getSystemPrompt() {
    return "Research the user's topic and end with a concise summary.";
  }
}

export class Assistant extends Think<Env> {
  getTools() {
    return {
      research: agentTool(Researcher, {
        description: "Research one topic in depth.",
        displayName: "Researcher",
        inputSchema: z.object({ query: z.string().min(3) })
      })
    };
  }
}
```

**A sub-agent presented to the model as an ordinary tool**, with a
description, a display name and a Zod input schema. The model does not
know it is delegating; the *user* does, because the run registry streams
`agent-tool-event` frames and the child has a URL you can open.

That last part is the contribution. Sub-agent delegation elsewhere in
this collection is invisible to the user by design — Claude Code's `Task`
returns a summary the orchestrator paraphrases. Here the child's timeline
is a first-class rendered object that **survives a page refresh**. The
trade is that everything about the child has to be durable, which is
exactly the substrate this SDK already has.

The layering is stated plainly:

> Agent tools are built on dynamic agents, but add a parent-side run
> registry, streaming `agent-tool-event` frames, replay, cancellation, and
> cleanup.

with the escape hatch named:

> Use raw `subAgent(...).chat()` only for lower-level streaming RPC where
> your code owns forwarding, cancellation, and replay policy.

And one honest limitation:

> `AIChatAgent` children run headlessly through `saveMessages()`, so they
> should use server-side tools. **Browser-provided client tools are not
> available during an agent-tool turn** unless you model that interaction
> as server-side state or a separate parent-mediated workflow.

A delegated child cannot reach the user's browser. **Anything requiring
the human has to be hoisted to the parent**, which is a real constraint
on how deep a delegation chain can go before it stops being able to ask
a question.

## Six human-in-the-loop patterns, and a decision tree

`docs/agents/human-in-the-loop.md` is the most complete treatment of
approval in this collection, and its main contribution is admitting that
**there is no single right answer**:

> | Use Case               | Pattern               | Best For                                           |
> | ---------------------- | --------------------- | -------------------------------------------------- |
> | Long-running workflows | Workflow Approval     | Multi-step processes, durable approval gates       |
> | AIChatAgent tools      | `needsApproval`       | Chat-based tool calls with `@cloudflare/ai-chat`   |
> | OpenAI Agents SDK      | `needsApproval`       | Using OpenAI's agent SDK with conditional approval |
> | Client-side tools      | `onToolCall`          | Tools that need browser APIs or user interaction   |
> | Stateless servers      | Stateless Elicitation | Current MCP tools requesting structured input      |
> | Legacy servers         | Legacy Elicitation    | Existing sessionful MCP deployments                |

> ### Decision Guide
>
> ```
> Is this part of a multi-step workflow?
> ├── Yes → Use Workflow Approval (waitForApproval)
> └── No → Are you building an MCP server?
>          ├── Yes → Use MCP Elicitation (elicitInput)
>          └── No → Is this an AI chat interaction?
>                   ├── Yes → Does the tool need browser APIs?
>                   │        ├── Yes → Use onToolCall (client-side execution)
>                   │        └── No → Use needsApproval (server-side with approval)
>                   └── No → Use State + WebSocket for simple confirmations
> ```

The tree's first split is the load-bearing one: **is the approval inside
a durable workflow or inside a request?** A gate in a workflow can wait
days; a gate in a request cannot outlive the connection. Everything else
follows from where the pause has to survive.

The framing at the top is also worth quoting, because it separates four
motivations most designs conflate:

> - **Compliance**: Regulatory requirements may mandate human approval for certain actions
> - **Safety**: High-stakes operations (payments, deletions, external communications) need oversight
> - **Quality**: Human review catches errors AI might miss
> - **Trust**: Users feel more confident when they can approve critical actions

Compliance and safety demand a *blocking* gate; quality and trust are
satisfied by a *visible* one. Conflating them produces a design that
blocks on everything, which is how approval fatigue starts.

## Approval inside a generated program: it works, on one of two paths

**A correction to an earlier reading of this SDK.** `docs/agents/codemode.md`
lists under *Current limitations*: *"Tool approval (`needsApproval`) is not
supported yet … excluded from codemode instead of pausing execution for
approval."* Taken alone that says approval and Code Mode do not compose.
It is true of one path and false of the other, and the two use different
field names:

| Path | Field | Behaviour |
|---|---|---|
| **AI-SDK tools** (`createCodeTool`, `createBrowserCodeTool`) | `needsApproval` | tool is **filtered out** of the codemode surface — `resolve.ts` "filter out tools with needsApproval and return a clean copy" |
| **Connector + Runtime** (`CodemodeConnector`, `createCodemodeRuntime`) | `requiresApproval` | the run **pauses and resumes via replay** — [`../code-mode/cloudflare.md`](../code-mode/cloudflare.md) |

So the accurate statement is: **approval composes with Code Mode if you
write a connector and drive it through the runtime, and is silently
dropped if you hand in AI-SDK tools.** Silently is the operative word —
the filter returns "a clean copy" and nothing tells the model a
capability was removed, which is the more troubling half of the finding.
`agent-permissions-approval.md`'s recurring complaint is exactly this:
a capability that is present, absent, or degraded depending on a wiring
decision the model cannot see.

The mechanism itself is the strongest answer to program-shaped approval
found anywhere in this collection, and is documented with the Code Mode
material rather than here.

## Readonly connections: permissioning the transport

> When a connection is marked as readonly:
>
> - It **receives** state updates from the server
> - It **can call** RPC methods that don't modify state
> - It **cannot** call `this.setState()` — neither via client-side
>   `setState()` nor via a `@callable()` method that calls
>   `this.setState()` internally

```typescript
export class DocAgent extends Agent<Env, DocState> {
  shouldConnectionBeReadonly(connection: Connection, ctx: ConnectionContext) {
    const url = new URL(ctx.request.url);
    return url.searchParams.get("mode") === "view";
  }
}
```

The interesting clause is the third: the restriction is enforced at
`setState`, **not** at the RPC boundary. So a `@callable()` method that
happens to mutate is blocked from a readonly connection without anyone
having to remember to annotate it. Deny at the sink rather than at the
entry point, and the enumeration problem disappears.

The client is told, rather than left to discover it:

```typescript
const agent = useAgent({
  agent: "DocAgent",
  name: "doc-123",
  query: { mode: "view" },
  onStateUpdateError: (error) => {
    toast.error("You're in view-only mode");
  }
});
```

This is per-*connection* permissioning on a shared object — several
viewers and one editor on the same agent — which is a case
`agent-permissions-approval.md` does not currently cover, because every
harness there has exactly one user.
