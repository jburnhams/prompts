# Interactive views: tool results the user can act on

*Added 2026-11-12, from the MCP Apps deep dive
([`mcp-apps/`](./mcp-apps)). Sources and SHAs are in
[`sources.md`](./sources.md), "MCP Apps (read 2026-11-12)".*

[`agent-generative-output.md`](./agent-generative-output.md) asks how an
artefact gets from an agent to a person.
[`agent-tool-result-transport.md`](./agent-tool-result-transport.md)
asks how a tool's result is projected into the model's context. Both
treat the result as finished once it is delivered.

An **interactive view** is a result that keeps going after delivery. It
is rendered for the user, the user acts on it, and it then **calls
tools and writes into the model's context on its own**. That makes it a
second caller of tools (beside the model) and a second author of
context (beside the user and the harness). MCP Apps standardised this
in January 2026, and by November it renders in Claude, ChatGPT, VS Code,
Microsoft 365 Copilot, Cursor and Goose. This document compares how
hosts answer the questions a view raises, because a harness that wants
its results to be views, or that wants to consume servers that offer
them, has to answer the same ones.

## 1. The mechanisms

| Mechanism | Who writes the UI | Who renders it | Can it call tools? | Can it write to the model's context? | Source |
|---|---|---|---|---|---|
| **Server-supplied view** | the MCP server (HTML) | the host, in a sandboxed iframe | the same server's tools, through the host | yes: `ui/message`, `ui/update-model-context`, app-tool results | MCP Apps (SEP-1865); OpenAI Apps SDK |
| **Declarative component tree** | the agent (data) | the client's own components | through the client app | through the client app | A2UI; AG-UI carries it |
| **Model-written page** | the model (HTML, a file) | the harness's page host | through capabilities the harness grants the page (connected data, a store, "ask Claude") | through "ask Claude", as a separate call | Claude's `Artifact` pages; LibreChat artifacts |
| **Text only** | nobody | — | — | — | every text host; MCP Apps' fallback |

The first is the only one where **a third party writes code that runs
next to the user's conversation**, which is why it is the one with a
security model to compare.

## 2. The decisions

### 2a. Who renders, and what a non-rendering host does

Every MCP Apps host renders in a sandboxed, cross-origin iframe whose
document the host serves, so CSP arrives as headers
(`mcp-apps/spec.md` §3). The variation is in what a host that **does not
render** does:

- **Declare nothing.** Claude Code, Gemini CLI and most terminals. The
  server sees no UI capability and should register text-only variants.
- **Pass through.** Codex's core declares `io.modelcontextprotocol/ui`
  to servers only when its own front end declared it, and records the
  view descriptor on the history item so a front end that resumes the
  thread can mount it later (`mcp-apps/catalogue.md` §1c).
- **Render elsewhere.** Goose can open an app in a standalone window
  that can call tools but "cannot communicate with goose"; the DeepSeek
  Harness plugin renders cards in `dsh web` rather than the terminal.

Under MCP `2026-07-28` the declaration is per request, not per
connection (`mcp-apps/spec.md` §7). A harness that serves both headless
and interactive runs can therefore declare it for one run and not the
next, and a server may answer `tools/list` differently for each.

### 2b. Which tools a view may call

| Rule | MCP Apps | Who enforces it |
|---|---|---|
| A view calls only **its own server's** tools | MUST | host |
| A tool marked `visibility: ["app"]` is **never in the model's tool list** | MUST | host (Codex and the AI SDK do it in the catalogue, before the model sees anything) |
| A view may not call a tool without `"app"` in its visibility | MUST | host |
| A view's call needs the user's approval | not required; Claude shows none for `callServerTool` | host policy |
| A view's callbacks are bound to the server and tool that opened it | not specified | Open WebUI: an HMAC of `[server_id, tool_name]` under the instance secret, checked separately from viewer auth |

The gap is the fourth row. **App-only tools are designed to be
invisible**: to the model, which is the point, and in Claude to the
user. So a view can run a write tool, or a costly query in a loop,
with nobody approving each call. Rill's reviewer caught exactly that
for its re-query tool (`mcp-apps/data-analysis.md` §2). The answer that
holds is to treat an app-only tool as a **separate grant** with its own
annotations, limits and metering, not as a private detail of the tool
that opened the view.

### 2c. What reaches the model, and as whose words

A view can put text into the model's context in three ways, and each
host decides how much of it to trust.

| Channel | What the spec says | Claude | VS Code | DeepSeek Harness plugin |
|---|---|---|---|---|
| `structuredContent` of the opening call | "not added to model context" | read only if `content` has no text (app tools) | prefers it (SEP-1624 survey) | — |
| `ui/update-model-context` | context for future turns; last write wins; host may defer it | accepted | shown as an attachment | a collapsed, plugin-sourced context row |
| `ui/message` | a `role: "user"` message that triggers a reply | needs the user's agreement; ≤ 8,000 chars; rate-limited; a "Use caution" banner | prefilled in the input box, never sent | accepted |
| App-tool result | `content` for the model | text blocks, ≤ 100,000 chars | — | — |

Two observations.

- **The spec calls `ui/message` a user message, and the careful hosts
  refuse to treat it as one** until the user agrees. That is the same
  rule [`agent-content-provenance.md`](./agent-content-provenance.md)
  derives for every channel: a message's role is not its author. Text a
  third-party view composed is the server's words, whatever role it
  carries.
- **`ui/update-model-context` reaches the model silently by design**,
  and none of the hosts read documents a check on it. It is an indirect
  prompt-injection channel with the server as author, exactly like a
  tool result, and should be framed as one.

### 2d. How long a view lives

| Question | MCP Apps answer | Workarounds in the field |
|---|---|---|
| When does a view die? | at the host's teardown; the host should wait for the view to acknowledge | Claude web sends no teardown to widgets; Claude iOS only on navigation |
| Does its state survive a remount? | no ("starts from your HTML") | `localStorage` keyed by a server-minted `viewUUID`; ChatGPT `widgetState` |
| Which copy is live when there are several? | not specified; each call mounts a new iframe | Claude's server-minted `{createdAt, seq}` and a `BroadcastChannel` election |
| Do app tools outlive the view? | MUST NOT persist; calling a closed app's tool MUST error | Claude: "the action might have happened" on a 45 s timeout |
| Long work started from a view? | return the **server's** task handle so the host can keep polling | — |

The pattern underneath is the one
[`agent-run-recovery.md`](./agent-run-recovery.md) §5 found for work
still running elsewhere: **the transcript, not the client, is the
source of truth**, so anything that must survive (ordering, identity,
long-running work) is minted by the server and written into the result.

### 2e. What is recorded

The spec asks hosts to "log View-initiated RPC calls for security
review" and to log CSP configurations and app-tool registrations. The
one harness that documents its log says the opposite happened: the
DeepSeek Harness plugin's bridge calls "skip the agent pipeline and
never reach the session JSONL", visible only in a 64-entry debug buffer.
A view's calls are tool calls with effects, and a run record that omits
them is incomplete in the way
[`agent-run-recovery.md`](./agent-run-recovery.md) §6's tool-effect
ledger exists to prevent.

## 3. What the sources agree on

- **Text first, view second.** Every source keeps a meaningful `content`
  result and treats the view as progressive enhancement.
- **The template is declared, the data is pushed.** Templates are cached
  by URI and reviewable before any call; data arrives per call. No host
  lets a tool result carry arbitrary HTML inline.
- **Visibility is filtered before the model sees the catalogue**, not at
  call time.
- **Nothing a view sends is the user speaking** until the user says so.

## 4. Where they disagree

- **Whether `structuredContent` is private.** Claude documents keeping
  it out of app-tool results when there is text; Open WebUI appends it.
- **Whether a view's own tool calls need approval.** No host found asks.
- **How much a non-rendering host should know.** Codex records the view
  descriptor for later; terminals drop it.

## 5. A run behind a view

Hex's connector renders **another agent's** progress and outputs inside
Claude's conversation: thinking steps, then charts and tables with
citations, while Claude's model reads a summary. The view is the only
place the user sees the inner agent's evidence, and the outer model
treats the whole thing as one tool call.

That is the shape a headless agent platform takes when a chat host is
its user interface: the run is the server, the chat host is the
renderer, and the result has three readers (the outer model, the user
through the view, and the record). The rules above say what each one
should get: the outer model a summary in `content`; the view the rows,
charts and provenance; the record everything, including the view's
later calls.

## 6. Consequences for Forge

Written as proposals, not adopted, in
[`agent-design/proposals-mcp-apps-2026-11.md`](./agent-design/proposals-mcp-apps-2026-11.md).
