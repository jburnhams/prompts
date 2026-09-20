# `@cloudflare/think` — the chat agent, and its tool surface

`docs/think/{index,tools,client-tools,actions,lifecycle-hooks,messengers}.md`
and `packages/think/README.md` at `c076e4c`. Marked experimental:
*"The API surface is stable but may evolve before graduating out of
experimental."*

The part of this SDK closest to what the rest of this collection
analyses: an opinionated chat-agent base class with a **built-in tool
surface almost identical to every coding agent here**, plus three
mechanisms around it that none of them have.

> Think is for agents whose work must outlive the request.

## The built-in tools

> Every Think agent gets `this.workspace` — a virtual filesystem backed by
> the Durable Object's SQLite storage. Workspace tools are automatically
> available to the model with no configuration.

| Tool | Description |
|---|---|
| `read` | Read text with line numbers; pass images and PDFs to multimodal models |
| `write` | Write content to a file (creates parent directories) |
| `edit` | Apply a find-and-replace edit to an existing file (**supports fuzzy matching**) |
| `list` | List files and directories in a path |
| `find` | Find files matching a glob pattern |
| `grep` | Search file contents by regex or fixed string |
| `delete` | Delete a file or directory |
| `bash` | Run a sandboxed Bash script against workspace files |

That is Claude Code's surface, and close to
[`../agent-design/tools.md`](../agent-design/tools.md)'s eleven, arrived
at independently on a completely different substrate. Three differences
worth noting against `../agent-tool-implementations.md`:

- **`read` is multimodal by contract** — "pass images and PDFs to
  multimodal models" is in the one-line description, so the model knows
  it can read a screenshot without a separate `InspectImage`.
- **`edit` "supports fuzzy matching" — and the docs undersell it in a way
  that matters.** Read from source (`packages/think/src/tools/workspace.ts`),
  it is not fuzzy matching in the edit-distance sense at all. See
  [`implementation.md`](./implementation.md) §1 for the mechanism; the
  short version is that exact-and-unique is tried first, the fallback is
  **whitespace normalisation only**, it has its own ambiguity guard, and
  it **flags itself in the result** (`fuzzyMatch: true`). That is the
  narrow, defensible subset rather than the silent-corruption risk this
  line previously claimed.
- **`bash` runs "against workspace files"**, i.e. against a virtual
  filesystem, not a machine. So there is a shell, and it cannot run the
  project's test suite — which is the same limit
  [`tools-and-workspace.md`](./tools-and-workspace.md) reaches from the
  `state.*` side. **This is a tool surface for an agent that edits, not
  one that verifies.**

## Seven tool sources, with a stated merge order

> On every turn, Think merges tools from multiple sources. **Later sources
> override earlier ones if names collide:**
>
> 1. **Workspace tools** — `read`, `write`, `edit`, `list`, `find`, `grep`, `delete`, `bash` (built-in)
> 2. **`getTools()`** — your custom server-side tools
> 3. **Extension tools** — tools from loaded extensions (prefixed by extension name)
> 4. **Context tools** — `set_context`, `search_context` (from `configureContext`)
> 5. **Skill tools** — `activate_skill`, `read_skill_resource`, `run_skill_script` (from `getSkills()`)
> 6. **MCP tools** — from connected MCP servers (when `includeMcpTools` is enabled)
> 7. **Client tools** — from the browser

**No other source in this collection documents a tool-precedence order**,
and every one of them has the problem: Claude Code merges built-ins, MCP
servers and skills; OpenClaw merges 159 plugins. A collision is resolved
*somehow* in all of them, and only this one says how.

Two things the ordering encodes. **Extension tools are namespaced**
("prefixed by extension name") while the other six are not — so the
collision risk is concentrated where the author has least control.
And **client tools win over everything**, which is defensible (the
browser is the most specific context) and is also the largest attack
surface in the list, since the client sends its schemas in the request
body.

The scoping rule is stated too, and it is the right one:

> Tools belong to the agent running the turn. For parent-child
> orchestration, use Agent Tools instead of passing one-off tools through
> `chat()`.

## Client tools: the absence of `execute` is the routing signal

> Client tools are tools **without an `execute` function on the server**
> — they only have a schema. When the LLM produces a tool call for one of
> these, Think sends the call to the client instead of executing it
> server-side.

> 1. The client sends tool schemas as part of the chat request body
> 2. Think merges client tools with server-side tools
> 3. The LLM calls a client tool — the tool call chunk is sent to the client over WebSocket
> 4. The client executes the tool and sends back a `CF_AGENT_TOOL_RESULT` message
> 5. Think persists the result, broadcasts `CF_AGENT_MESSAGE_UPDATED`, and optionally auto-continues

An elegant piece of API design: **a schema with no implementation is, by
definition, something someone else implements.** No `location: "client"`
flag to set or forget.

It is also the mechanism `../code-mode/cloudflare.md` and
[`delegation-and-approval.md`](./delegation-and-approval.md) keep running
into from the other side — a delegated child *cannot* use client tools,
because there is no socket to the browser from inside a headless
sub-agent turn. The capability is real and does not compose downward.

For `../agent-design/`, the transferable bit is the persistence: the
result is **persisted and broadcast** before the turn continues, so a
client tool's answer survives a refresh. Every browser-side tool in this
collection loses its result if the page reloads mid-call.

## Actions: tools with the dangerous parts pre-solved

> Where a plain AI SDK `tool()` is just a description, a schema, and an
> `execute` function, an `action()` adds the things that are tedious and
> dangerous to get right by hand for a tool that has real side effects:
>
> - **Idempotency** — a durable ledger replays a settled result by a
>   stable key instead of re-running the side effect on a recovery retry.
> - **Approvals** — gate a call behind a human, either inline (the turn
>   waits) or durably (the turn parks and resumes later, **even from a
>   dashboard with no live socket**).
> - **Authorization** — declare the permissions a call requires and grant
>   them per-turn.
> - **Reply attachments** — record advisory delivery metadata (a drafted
>   email, a card, a voice note) **without changing what the model sees**.

This is the most complete single answer to "what does a *consequential*
tool need beyond a schema" in the collection, and each of the four names
a failure the rest of this repo has documented separately:

- **Idempotency by stable key** is the fix for
  [`durability.md`](./durability.md)'s recovery problem. An agent that
  dies after sending an email and retries sends two emails, unless the
  send is keyed. Note this is a *ledger*, not the abort-and-replay of
  Code Mode — a different mechanism for the same hazard, at the tool
  level rather than the program level.
- **Inline vs durable approval** is the distinction
  `../agent-permissions-approval.md` needs and does not have. *"Even from
  a dashboard with no live socket"* is the part that matters: approval
  that outlives the connection is a different engineering problem from a
  modal dialog, and conflating them is why most approval designs quietly
  only support the second.
- **Per-turn permission grants** make authorization a property of the
  turn rather than of the deployment — the closest thing here to a
  capability that can be handed out and taken back.
- **Reply attachments "without changing what the model sees"** is the
  cleanest statement of the audience split
  [`context-blocks.md`](./context-blocks.md) and
  [`../data-agents/vanna/`](../data-agents/vanna) both circle: a tool
  result has more than one consumer, and metadata for the delivery layer
  should not enter the model's context.

> Actions compile into Think tools, so the model calls them exactly like
> any other tool.

Invisible to the model, which is right — none of the four is the model's
concern.

## Eleven lifecycle hooks

> Think owns the `streamText` call and provides hooks at each stage of the
> chat turn. **Hooks fire on every turn regardless of entry path** —
> WebSocket chat, sub-agent `chat()`, `saveMessages()`, durable
> `submitMessages()` execution, `continueLastTurn()`, and
> auto-continuation after tool results.

| Hook | When it fires | Return |
|---|---|---|
| `configureSession(session)` | Once during `onStart` | `Session` |
| `configureContext()` | Once during `onStart` | `ContextConfig[]` |
| `beforeTurn(ctx)` | Before `streamText` | `TurnConfig` or void |
| `beforeStep(ctx)` | Before each model step | `StepConfig` or void |
| **`beforeToolCall(ctx)`** | When model calls a tool | **`ToolCallDecision`** or void |
| `afterToolCall(ctx)` | After tool execution | void |
| `onStepFinish(ctx)` | After each step completes | void |
| `onChunk(ctx)` | Per streaming chunk | void |
| `onChatResponse(result)` | After turn completes and message is persisted | void |
| `onChatError(error, ctx?)` | On error during a turn | error to propagate |
| `classifyChatError(error, ctx?)` | On a turn error, when `contextOverflow.reactive` is enabled | `ChatErrorClassification` |

Three observations:

**"Regardless of entry path" is the load-bearing guarantee.** Six ways
into a turn and one set of hooks. A policy implemented in
`beforeToolCall` cannot be bypassed by arriving over RPC instead of
WebSocket — which is exactly how policy gets bypassed in harnesses that
grew entry points one at a time.

**`beforeToolCall` returning a `ToolCallDecision` is a policy hook in the
right place.** Deny, rewrite, or allow, evaluated per call, on every
path. `../agent-permissions-approval.md`'s whole subject matter has a
single insertion point here.

**`classifyChatError` + `contextOverflow.reactive` is compaction
triggered by failure.** `../agent-context-compaction.md` catalogues
proactive triggers — token thresholds, turn counts. This is the reactive
one: hit the provider's context limit, classify the error as overflow,
compact, retry. It pairs with the overlay-based compaction in
[`durability.md`](./durability.md), and it is the honest admission that a
threshold you chose will sometimes be wrong.

## What Think is for, in its own words

> The opinionated pieces are the ones that are tedious and dangerous to
> get right by hand:
>
> - **Durable turns** — an in-flight turn survives Durable Object eviction and resumes; it is not silently lost on deploy or hibernation.
> - **Recovery-aware delivery** — replies are snapshotted as `accepted`, `streaming`, or `completed` …
> - **Durable submissions** — webhooks and RPC callers submit a turn with an idempotency key and check status later.
> - **Sessions, not just a message list** — tree-structured history with branching, compaction, and full-text search.
> - **Human-in-the-loop and client tools** — a turn can pause for approval or a browser-side tool and resume later, **without holding a request open**.

and when *not* to use it:

> If you only need a chat-protocol adapter where you own the loop and the
> `Response`, use `AIChatAgent` instead.

**"Without holding a request open"** is the thesis of the whole package.
Every harness in this collection that pauses for a human does it by
keeping something alive — a process, a socket, a request. Think's claim
is that pausing should be a *storage* operation, and everything else
(durable submissions with idempotency keys, tree-structured sessions,
recovery snapshots) follows from taking that seriously.

That is the same conclusion `../agent-design/`'s `AskUser` reaches for a
hands-off agent — *suspend the run and exit, resume when a reply lands* —
arrived at from the opposite direction, and with the durable machinery
this design currently leaves to the harness.
