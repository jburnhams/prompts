# Cloudflare Agents SDK

- **Type**: agent framework where each agent is a **stateful, addressable,
  hibernatable object** · **Vendor**: Cloudflare · **Licence**: MIT
- **Source**: https://github.com/cloudflare/agents — `main` @ `c076e4c`
  (2026-09-18)
- **Retrieved**: 2026-09-20
- **Scale**: 8 packages, 44 documentation pages under `docs/agents/`,
  ~60 examples

A different *kind* of source from the rest of this collection. Every
other harness here is a **process**: a CLI that starts, runs a loop, and
exits, or a server that handles a request. Cloudflare's agent is a
**Durable Object** — a named, single-threaded, persistent object with its
own embedded SQLite database, which the platform evicts and revives
underneath you.

That one substrate difference forces answers to questions the
process-shaped harnesses never have to ask, and those answers are why
this folder exists:

- What happens to an agentic loop when the runtime **kills it mid-turn**?
- How do you keep a **prompt prefix byte-identical** across an eviction so
  the provider's cache still hits?
- What does a sub-agent look like when it can have **its own isolate and
  its own database**?
- How does a turn **pause for a human** without holding a request open?

## Files

| File | What it is |
|---|---|
| [`context-blocks.md`](./context-blocks.md) | `agents/context` — the system prompt assembled from labelled blocks, where the **provider's shape decides both the rendering and which tools the model gets**. The most transferable thing in the SDK |
| [`tools-and-workspace.md`](./tools-and-workspace.md) | `@cloudflare/shell` — a 24-method filesystem and a 14-method **git client as typed sandbox APIs**, `STATE_SYSTEM_PROMPT` verbatim, transactional multi-file edits with `dryRun`, and the Workspace spill threshold. The coding-agent surface |
| [`durability.md`](./durability.md) | Fibers (`runFiber`/`stash`/`onFiberRecovered`), the eviction numbers, recovery-aware delivery, frozen prompts, and compaction as a **non-destructive read-time overlay** |
| [`delegation-and-approval.md`](./delegation-and-approval.md) | Dynamic agents (facets), agent tools, the six human-in-the-loop patterns with the vendor's own decision tree, and the two approval paths that disagree |
| [`operations.md`](./operations.md) | Thirteen observability channels (read the event names as a list of production failure modes), four kinds of "do something later", scheduling, retries, state sync, and MCP in both directions |
| [`think.md`](./think.md) | `@cloudflare/think` — the chat agent: a built-in `read/write/edit/list/find/grep/delete/bash` surface, a **seven-source tool merge order**, client tools identified by the absence of `execute`, **actions** (idempotency, approvals, authorization, reply attachments), and eleven lifecycle hooks that fire on every entry path |
| [`skills.md`](./skills.md) | The third skills implementation in this collection, and the first where **a skill script runs with a gated capability context** and declares its own `allowedTools`. Three generated tools, the catalog prompt, the tagged envelope |
| [`browser.md`](./browser.md) | Code Mode over **raw CDP** — the protocol, not a verb set — with `cdp.spec()` for live discovery, and a **base64 redactor** that is the most complete implementation yet of `../agent-vision-multimodal.md`'s strip-and-say-so rule |
| [`interop.md`](./interop.md) | How an agent is addressed and how it reaches peers: **A2A** (agent cards, tasks, SSE), **x402** (an agent that pays), channels, email reply routing, per-source webhook agents |

Code Mode lives in [`../code-mode/cloudflare.md`](../code-mode/cloudflare.md)
— the `codemode` tool, the iframe sandbox and the CSP, **plus the Runtime
layer**: durable tool-call log, approvals via abort-and-replay, rollback
through per-tool `revert`, and snippets as curated procedural memory. It
is indexed there because it is one instance of a pattern with four
implementations.

## Coverage

`docs/agents/` has **44 pages**, plus `docs/think/` (11), `docs/codemode/`
(6), `docs/shell/`, `docs/voice/`, 8 packages and ~60 examples. This
folder now covers the material relevant to what this collection
analyses — prompts, tool surfaces, context handling, delegation,
approval, durability and interop — at parity with the other large
sources here.

**Read** — `context`, `durable-execution`, `sessions`, `sub-agents`,
`agent-tools`, `human-in-the-loop`, `readonly-connections`,
`observability`, `scheduling`, `queue`, `tasks`, `retries`, `state`,
`mcp-client`, `mcp-servers`, `mcp-transports`, `securing-mcp-servers`,
`browse-the-web`, `channels`, `email`, `webhooks`; all six
`docs/codemode/` pages; `docs/shell/index.md`; `docs/think/{index,
tools, client-tools, actions, lifecycle-hooks, messengers}.md`;
`examples/{a2a,x402,codemode-browser,webmcp}`. In source:
`packages/agents/src/skills/` (all 9 files),
`packages/agents/src/browser/ai.ts`, `packages/shell/src/{prompt.ts,
git/provider.ts}`, `packages/codemode/src/*`,
`packages/think/src/think.ts` (partially).

**Deliberately not read**, as low signal for this collection: the two
AI-SDK migration guides, `getting-started`,
`adding-to-existing-project`, `configuration`, `agent-class`,
`callable-methods`, `get-current-agent`, `http-websockets`,
`client-sdk`, `chat-sdk`, `cross-domain-authentication`, `routing`,
`lifecycle`, `voice`, `push-notifications`, `streams` /
`resumable-streaming` / `server-driven-messages` (transport mechanics),
and the remaining `docs/think/` pages
(`getting-started`, `channels`, `programmatic-submissions`,
`sub-agents`, `workflows`) whose substance is covered from the pages
above.

Note that `agent-think/` also exists at the repo root, separate from
`packages/think/`, and was not read.

## The packages

| Package | What |
|---|---|
| `agents` | The `Agent` base class, state, routing, sessions, scheduling, context blocks, MCP client *and* server, dynamic agents |
| `@cloudflare/think` | Opinionated chat-agent base class — "for agents whose work must outlive the request" |
| `@cloudflare/codemode` | Sandboxed execution, tool providers, connectors, approvals |
| `@cloudflare/shell` | `Workspace` — a durable virtual filesystem on SQLite + R2, exposed to Code Mode as `state.*` and `git.*` tool providers |
| `@cloudflare/ai-chat`, `voice`, `hono-agents`, `worker-bundler` | Adapters and transports |

## What is genuinely new here

**1. The system prompt and the tool surface are generated from one
declaration.** `agents/context` renders a block as prompt text *and*
decides which tools exist, from the same object:

> | Provider shape          | Block behavior                               |
> | ----------------------- | -------------------------------------------- |
> | `get()`                 | Read-only text in the prompt                 |
> | `get()` + `set()`       | Writable through the `set_context` tool      |
> | `get()` + `search(key)` | Summary in the prompt, `search_context` tool |
>
> The checks are structural, not nominal.

No other source in this collection couples the two. See
[`context-blocks.md`](./context-blocks.md).

**2. `getSystemPrompt()` is deprecated in favour of assembly — and the
SDK warns you at runtime.** From `packages/think/src/think.ts`:

> `getSystemPrompt()` is only used as a fallback when no context blocks
> are configured. `getSkills()` registers a skills context block, so move
> always-on instructions into `configureContext()` instead.

The collection has watched this migration happen three times now —
OpenClaw assembling per surface from ~60 runtime parameters, Codex
turning the prompt into a diff stream of sixteen world-state sections,
and now Cloudflare turning it into labelled blocks with capability
markers. Three independent arrivals at *the monolithic system prompt is
not the unit of composition*.

**3. Eviction is a first-class, documented, numbered hazard.**

> Durable Objects get evicted for three reasons:
>
> 1. **Inactivity timeout** — ~70–140 seconds with no incoming requests or open WebSockets
> 2. **Code updates / runtime restarts** — non-deterministic, 1–2x per day
> 3. **Alarm handler timeout** — 15 minutes
>
> When eviction happens mid-work, the upstream HTTP connection (to an LLM
> provider, an API, a database) is severed permanently.

Every long-running-agent design in this collection assumes the process
survives. This one assumes it will not, **twice a day**, and builds from
there.

**4. Sub-agents get real isolation, not just a fresh context window.**
Dynamic agents are child Durable Objects with their own isolate and their
own SQLite, colocated under a parent that can abort or delete them and is
the only route to reach them. `agent-subagent-architectures.md` catalogues
sub-agents that are stateless one-shot calls; this is the other end of
that axis.

**5. Approval composes with a generated program.** A connector tool
marked `requiresApproval` aborts the run, records the action pending, and
on approval **re-runs the same code with every prior call served from a
durable log**. Corrected from an earlier reading of this SDK that took
`docs/agents/codemode.md`'s *Current limitations* at face value; that
text describes the AI-SDK path, where approval-gated tools are silently
filtered out instead. Both are true, of different paths.

**6. Compaction is a read-time overlay, not a rewrite.**

> Compaction overlays replace a range at read time without deleting the
> original rows

which makes it reversible and auditable, and is a different answer from
every mechanism in `agent-context-compaction.md`.

## What it is not

**Not a coding agent, and mostly not a prompt corpus.** This is an SDK.
The prompt-bearing surfaces are thin: Code Mode's `DEFAULT_DESCRIPTION`
(captured in [`../code-mode/cloudflare.md`](../code-mode/cloudflare.md)),
Think's `getSystemPrompt()` fallback, and whatever an application puts in
its context blocks. Read it for **mechanism**, not for prompt text.

**Heavily platform-coupled.** Durable Objects, facets, Workflows, R2,
Workers RPC and the Dynamic Worker Loader are Cloudflare primitives.
The *questions* transfer everywhere; several of the answers do not. Where
a mechanism depends on something only Cloudflare has, the file says so.

**Moving fast, and says so.** `agents/context` is marked
*"Experimental. Everything exported from `agents/context` may change
between releases"*; `@cloudflare/think` and `@cloudflare/shell` are
experimental; the WebMCP adapter carries a DO-NOT-USE-IN-PRODUCTION
banner. Commit-pinned above for that reason.
