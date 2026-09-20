# Durability: surviving a runtime that kills you twice a day

`docs/agents/durable-execution.md`, `docs/agents/sessions.md`,
`docs/think/messengers.md` at `c076e4c`.

Every other harness in this collection assumes its process survives the
task. This one assumes it will not, states the numbers, and builds the
recovery machinery in the open. That makes it the best available source
on a question the rest of the collection has mostly hand-waved:
**what happens to an agentic loop when it is killed mid-turn?**

## The hazard, numbered

> Durable Objects get evicted for three reasons:
>
> 1. **Inactivity timeout** — ~70–140 seconds with no incoming requests or open WebSockets
> 2. **Code updates / runtime restarts** — non-deterministic, 1–2x per day
> 3. **Alarm handler timeout** — 15 minutes
>
> When eviction happens mid-work, **the upstream HTTP connection (to an
> LLM provider, an API, a database) is severed permanently.** In-memory
> state — streaming buffers, partial responses, loop counters — is lost.
> Multi-turn agent loops lose their position entirely.

Reason 2 is the one worth sitting with. A **non-deterministic restart
once or twice a day**, from a platform deploy nobody on your team
triggered, is not an edge case for an agent that runs for hours. It is a
scheduled certainty with an unknown arrival time.

## Two mechanisms, and the difference between them

> `keepAlive()` reduces the chance of eviction. `runFiber()` makes
> eviction survivable.

That sentence is the design in miniature: one control lowers probability,
the other removes consequence, and they are not substitutes.

### `keepAlive()` — lower the probability

> Prevents idle eviction by creating a 30-second alarm heartbeat that
> resets the inactivity timer.

```typescript
class Agent {
  keepAlive(): Promise<() => void>;
  keepAliveWhile<T>(fn: () => Promise<T>): Promise<T>;
}
```

> `keepAliveWhile()` is the recommended approach — it runs an async
> function and automatically cleans up the heartbeat when it completes or
> throws

> For manual control, `keepAlive()` returns a disposer. **Always call it
> when done — otherwise the heartbeat continues indefinitely.**

A scoped form recommended over a manual one, with the leak named. The
manual version's failure mode is an agent that never goes idle and bills
forever, which is exactly the kind of thing that only shows up on an
invoice.

### `runFiber()` — remove the consequence

```typescript
class MyAgent extends Agent {
  async doWork() {
    await this.runFiber("my-task", async (ctx) => {
      const step1 = await expensiveOperation();
      ctx.stash({ step1 });

      const step2 = await anotherExpensiveOperation(step1);
      this.setState({ ...this.state, result: step2 });
    });
  }

  async onFiberRecovered(ctx: FiberRecoveryContext) {
    if (ctx.name !== "my-task") return;
    const snapshot = ctx.snapshot as { step1: unknown } | null;
    if (snapshot) {
      // Resume from the checkpoint — step1 is done, run step2
      const step2 = await anotherExpensiveOperation(snapshot.step1);
      this.setState({ ...this.state, result: step2 });
    }
  }
}
```

> `runFiber()` registers a task in SQLite, keeps the agent alive during
> execution, lets you checkpoint intermediate state with `stash()`, and
> calls `onFiberRecovered()` on the next activation if the agent was
> evicted mid-task.

Three properties worth naming:

- **Checkpointing is explicit and manual.** `ctx.stash()` is a call the
  author makes, at a granularity they choose. There is no automatic
  replay, no deterministic re-execution, no effect log. Compare
  Code Mode's durable replay, which *is* deterministic and pays for it
  with the `Promise.all` divergence caveat
  ([`../code-mode/cloudflare.md`](../code-mode/cloudflare.md)).
- **Recovery is a separate code path, and the author writes it.**
  `onFiberRecovered` is not "continue where you left off" — it is a
  handler that receives a snapshot and has to decide what remains. That
  is more work and more honest: the framework cannot know whether
  `expensiveOperation` was idempotent.
- **The `if (ctx.name !== "my-task") return;` line is in the vendor's own
  example**, which tells you fibers are expected to be plural and the
  handler is expected to be a dispatch.

And the boundary with the platform's other primitive is stated:

> For work that should run independently of the agent with per-step
> retries and multi-step orchestration, use Workflows instead. **Fibers
> are for work that is part of the agent's own execution.**

## Recovery-aware delivery: the part with no equivalent anywhere

From `docs/think/messengers.md`:

> Recovery snapshots store only serializable event and Chat SDK thread
> data. **If a restart happens before streaming starts, Think can replay
> the answer. If a restart happens after streaming starts, Think posts the
> configured interruption message instead of risking a duplicate partial
> answer.**

This is the best treatment in the collection of a failure mode everything
else ignores. An agent killed mid-stream has already sent bytes to a
human. On revival it has exactly two options and they are not symmetric:

| State at death | Action | Why |
|---|---|---|
| accepted, not yet streaming | **replay** — produce the answer | nothing was shown; a fresh answer is correct |
| streaming already started | **interrupt** — post a notice | a replay would append a second partial answer to a visible first one |

The asymmetry is the insight. *Whether it is safe to retry depends on
whether the side effect was already observed*, and for a chat agent the
side effect is text on someone's screen. An at-least-once delivery model
is fine for an idempotent write and produces a garbled conversation here.

The companion rule is small and right:

> Delivery errors use a generic user-facing message by default **so
> internal exception details are not posted into external chats.**
> Override `delivery.errorResponseText` when you want a custom safe
> message.

An agent that posts into Slack or SMS has an error path that is *also* a
publishing path. Defaulting it closed is the correct choice and one that
`agent-design/`'s error contracts do not currently make, because nothing
in that design posts an exception anywhere a stranger reads it.

## Compaction as a read-time overlay

From `docs/agents/sessions.md`. `agents/sessions` stores

> tree-structured messages, streamed and byte-budgeted reads, compaction
> overlays, optional full-text search, and lossless payload storage.

and the mechanism is:

> **Compaction overlays replace a range at read time without deleting the
> original rows**

```ts
import { createCompactFunction } from "agents/sessions";

session
  .onCompaction(
    createCompactFunction({
      summarize: async (prompt) => summarize(prompt),
      keepRecentTokens: 20_000
    })
  )
  .compactAfter(80_000);
```

> `createCompactFunction` takes exactly two options. `summarize` calls the
> model with a prompt and returns its text. `keepRecentTokens` is the
> token budget for the recent tail kept verbatim, defaulting to 20,000.
> **The first three messages are kept verbatim as the head, at least the
> last two are kept as the tail, and the boundaries are aligned so a tool
> call is never separated from its result.**

Four things `agent-context-compaction.md` should absorb:

**Non-destructive is a different category.** Every mechanism in that doc
summarises and discards. Here the original rows stay in
`cf_agents_session_compactions`-shadowed storage and the overlay applies
on read, so compaction is **reversible, auditable, and branch-local**
(`session.compact(leafId)` compacts one branch of a message *tree*).
The Stencil result that prose compaction "preserves what you were doing,
not what you knew" hurts much less when what you knew is still on disk.

**The trigger never reads the transcript.**

> Sessions stamps each message with a token estimate when the row is
> written. `compactAfter()` gates on that O(1) aggregate and **never reads
> the transcript to decide whether to compact.**

Deciding *whether* to compact should not cost what compacting costs.
Writing the estimate at insert time makes the gate a single sum.

**It fails open, deliberately.**

> Auto-compaction failures are non-fatal: they log, emit `session:error`,
> and **leave the transcript alone.**

The exact opposite of OpenClaw, whose compaction **fails closed** after
auditing five required headings in the post-budget text. Both are
defensible and the difference follows from what is being protected:
OpenClaw is guarding pending asks and exact identifiers against
truncation, so a bad summary is worse than no compaction; here the
original rows survive either way, so the worst case of a failed
compaction is a large prompt rather than a lossy one. **Non-destructive
storage is what buys the right to fail open.**

**Tool call and tool result are never split.** Stated as a boundary
alignment rule. This is the single most common way a hand-rolled
compactor produces a transcript the provider rejects, and it is one line
of the spec here.

The read path is built for the same shape:

> A newest-first read follows parent pointers from the leaf, one row per
> message the loop actually takes, **so its cost has no transcript term.**
> Compaction overlays are honored: the walk stays row-by-row until it
> reaches the end of a compacted span, and only then plans the overlays
> over the remaining prefix and streams it leaf-first in eight-row
> windows.

"No transcript term" is the property that makes a months-long agent
affordable: reading the context for turn 10,000 costs the same as turn
10, because you walk the path, not the history.

## What transfers

The mechanisms are Durable Object specific. The **questions** are not,
and three of them should be in any hands-off agent design:

1. If the run dies between a tool call and its result, what happens on
   revival — and is that different depending on whether anyone saw the
   partial output?
2. What is the cheapest possible test for "should I compact", and does it
   cost less than compacting?
3. Is compaction destructive? If not, the failure policy can be much more
   relaxed than if it is.
