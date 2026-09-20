# `agents/context` — a system prompt assembled from labelled blocks

`docs/agents/context.md` at `c076e4c`. Marked experimental:

> **Experimental.** Everything exported from `agents/context` may change
> between releases while the API stabilizes.

The most transferable thing in the SDK, and the one idea in it that no
other source in this collection has.

## The thesis

> `agents/context` assembles an agent's system prompt from labelled
> blocks. A block is a piece of prompt text with a storage provider behind
> it. **What the provider can do decides how the block behaves and which
> tools the model gets for it.**
>
> Context is prompt assembly. It is not conversation storage. It composes
> with `agents/sessions` rather than living inside it, so an agent can
> have a prompt without a transcript, or a transcript without a prompt.

```ts
import { ContextBlocks } from "agents/context";

const context = new ContextBlocks([
  {
    label: "soul",
    provider: { get: async () => "You are a helpful assistant." }
  },
  {
    label: "memory",
    description: "Facts learned about the user",
    maxTokens: 1_100,
    provider: memoryProvider
  }
]);

const system = await context.freezeSystemPrompt();
const tools = await context.tools();
```

Those last two lines are the point. **One declaration produces both the
prompt and the tool set.**

## Capability is inferred from the provider's shape

> | Provider shape          | Block behavior                               |
> | ----------------------- | -------------------------------------------- |
> | `get()`                 | Read-only text in the prompt                 |
> | `get()` + `set()`       | Writable through the `set_context` tool      |
> | `get()` + `search(key)` | Summary in the prompt, `search_context` tool |
>
> `get()` returns the block's current content, or `null` when it has none.
> An optional `init(label)` receives the block label before first use, so
> one provider class can serve several labels.

**"The checks are structural, not nominal."** A block does not declare
itself writable; it *is* writable because its provider has a `set`. That
removes an entire class of drift — the configuration that says a block is
read-only while the provider quietly accepts writes, or the tool that is
advertised for a block nothing can write to.

And the tool set follows:

> `tools()` returns an AI SDK `ToolSet` wired from what the blocks can do:
>
> - `set_context` when any block is writable
> - `search_context` when any block is backed by a search provider
>
> **An agent with only read-only blocks gets no tools at all.**

This is the same principle `data-agents/postgres-mcp/` applies to a
database tool — the access mode changes the tool description *and* the
annotations *and* the driver together — generalised to the whole prompt.
`agent-permissions-approval.md` argues for it; this is the cleanest
implementation of it found so far.

## The rendering carries the capability

> Each block renders as a labelled section of the system prompt. The
> header carries the label, the description, a token-usage percentage when
> `maxTokens` is set, and a capability marker (`[readonly]`, `[writable]`,
> `[loadable]`, or `[searchable]`).
>
> **An empty read-only block is skipped. Writable, loadable, and
> searchable blocks always render so the model knows which tools can
> address them.**

Three decisions in that second paragraph, and all three are right:

- **An empty read-only block is wasted tokens** — nothing to say, nothing
  to do about it, so it disappears.
- **An empty writable block is not** — the model needs to know the slot
  exists in order to fill it. This is the distinction most
  prompt-assembly code misses, and it falls straight out of asking "can
  the model act on this?"
- **The token-usage percentage is in the header.** The model is told how
  full a budgeted block is, in the block itself, which makes "should I
  write more here" answerable without a separate accounting tool.

The `[readonly]` / `[writable]` / `[loadable]` / `[searchable]` markers
are the prompt-side twin of MCP's tool annotations, and they exist for
the same reason: the consumer needs to know what it may do before it
tries.

## Frozen prompts, and why

The sharpest engineering in the file:

> `freezeSystemPrompt()` renders once and returns the same string on every
> later call, **so the provider's prefix cache stays warm across turns**.
> `setBlock()` writes to the provider immediately but **deliberately does
> not change the frozen prompt**; call `refreshSystemPrompt()` to
> re-render from current block state.

and, with a `promptStore` passed in:

> `freezeSystemPrompt()` returns the stored prompt when one exists, and
> otherwise loads providers, renders, and persists. **So a cold wake
> reuses the exact prompt string the model already cached instead of
> re-rendering a subtly different one.**

```ts
const context = new ContextBlocks(
  configs,
  new AgentContextProvider(this, "_system_prompt"),
  (label) => new AgentContextProvider(this, label)
);

const system = await context.freezeSystemPrompt();
```

**A dynamically assembled prompt is a cache-miss generator**, and this is
the fix: assemble once, persist the *rendered bytes*, and serve those
until something explicitly asks for a re-render. The "subtly different"
in that sentence is the whole hazard — a timestamp, a re-ordered map, a
token count that moved by one, and the prefix no longer matches.

Set beside the collection's other two answers to the same problem:

| Source | Mechanism |
|---|---|
| **OpenClaw** | a declared boundary *inside the prompt text* (`<!-- OPENCLAW_CACHE_BOUNDARY -->`), with section placement argued as a caching decision |
| **Codex** | sixteen world-state sections that `render_diff(previous)` and **return nothing when unchanged**, so a stable section costs zero bytes after turn one |
| **Cloudflare** | render once, **persist the rendered string**, and serve the stored bytes across eviction |

Three different layers — text, protocol, storage — and Cloudflare's is
the only one that survives the process dying, which is the case it was
built for.

The trade is stated rather than hidden: `setBlock()` updates the store
and *not* the prompt, so a block written mid-session is not visible to
the model until a refresh. That is a real staleness window, chosen
deliberately, and an agent that writes memory and expects to read it back
in the same turn needs `refreshSystemPrompt()` and the cache miss that
comes with it.

## Durable and searchable blocks

> `AgentContextProvider` stores one block per row in
> `cf_agents_context_blocks` in the Durable Object's own SQLite database

> `AgentSearchProvider` backs a block with a Durable Object FTS5 table
>
> `get()` renders a **count of indexed entries** rather than the entries
> themselves. `search(query)` returns up to 10 ranked matches through the
> `search_context` tool. `set(key, content)` replaces one keyed entry.

A searchable block therefore occupies a constant few tokens in the prompt
(*"1,284 entries"*) and is reached through a tool. That is progressive
disclosure applied to *memory* rather than to instructions or tools — the
same move as `data-agents/data-formulator/`'s `load_skill`, one layer
over.

The storage note is worth keeping for the reasoning as much as the fact:

> The FTS5 table is the only store for these entries. **A mirror row table
> would double the billed writes of every indexed entry to serve a count
> and a lookup the index already answers.** Entries live in
> `cf_agents_search_fts`, namespaced by label, separate from the Sessions
> message index.

## How Think uses it

```ts
class MyAgent extends Think<Env> {
  configureContext(): ContextConfig[] {
    return [
      { label: "soul", provider: { get: async () => "You are helpful." } },
      { label: "memory", description: "Learned facts", maxTokens: 2_000 }
    ];
  }
}
```

> A block declared without a provider is auto-wired to durable per-agent
> SQLite. The frozen system prompt is always persisted, in
> `_system_prompt`, so there is nothing to opt into.

And the migration is enforced with a runtime warning, from
`packages/think/src/think.ts`:

```
getSystemPrompt() is only used as a fallback when no context blocks are
configured. getSkills() registers a skills context block, so move
always-on instructions into configureContext() instead.
```

The source comment calls it *"the legacy fallback system prompt"*.

## Why this matters beyond Cloudflare

Every design in `agent-design/` currently treats the system prompt as a
document and the tool schemas as a separate list, and keeps them
consistent by discipline. This is the alternative: **declare the
capability once, derive both.**

It lands on four existing docs:

- `agent-context-file-loading.md` — context tiers become blocks with
  providers, and the tier's permissions become the block's capability.
- `agent-memory-learning.md` — memory is a writable block, and
  `set_context` is the write path, generated rather than hand-written.
- `agent-design/system-prompts.md` — the monolith becomes an assembly
  order plus a freeze.
- `agent-context-compaction.md` — a `maxTokens` budget rendered *into*
  the block header is a compaction signal the model can act on before the
  harness has to.

The honest caveat: there is no evidence here that the model *uses* the
capability markers well, or that a percentage in a header changes
behaviour. The mechanism is clean; whether it pays is an eval question,
and the SDK does not report one.
