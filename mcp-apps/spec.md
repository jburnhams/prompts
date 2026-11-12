# MCP Apps: how the extension works

*Read 2026-11-12 from `modelcontextprotocol/ext-apps` at `ea3e9d0`
(SDK 2.1.0): `specification/2026-01-26/apps.mdx` (the stable revision)
and `specification/draft/apps.mdx` (2,713 lines, last changed
2026-11-04), plus `docs/{overview,patterns,migrate-to-2,csp-cors,authorization}.md`.
Negotiation under the stateless protocol is from
`modelcontextprotocol/modelcontextprotocol` `docs/extensions/overview.mdx`
at `99a8e46`.*

MCP Apps is SEP-1865, extension id `io.modelcontextprotocol/ui`. It
lets an MCP server ship an HTML view with a tool. A host that supports
the extension renders the view in a sandboxed iframe next to the tool
call and pushes the call's arguments and result into it. The view can
then call the server's tools itself, send a message into the chat,
update what the model will see next turn, and (in the draft) expose
tools of its own for the model to call. A host that does not support
it shows the tool's ordinary text result, so the server works either
way.

It was proposed on 2025-11-21 by authors from MCP-UI, Anthropic and
OpenAI, merged MCP-UI's community work with the OpenAI Apps SDK's
`window.openai` model, shipped as the first official extension on
2026-01-26, and became part of the core extensions framework in the
`2026-07-28` protocol revision.

---

## 1. The four parts

| Part | What it is | Where it lives |
|---|---|---|
| **UI resource** | An HTML5 document at a `ui://` URI with mimeType `text/html;profile=mcp-app` | `resources/read` on the server; may be left out of `resources/list` |
| **Tool linkage** | `_meta.ui.resourceUri` on a tool, plus `_meta.ui.visibility` | `tools/list` |
| **View ↔ host channel** | JSON-RPC 2.0 over `postMessage`, "its own dialect of MCP": some core methods (`tools/call`, `resources/read`), some `ui/*` methods | inside the browser |
| **Negotiation** | The host declares `{"mimeTypes": ["text/html;profile=mcp-app"]}` under the extension id; the server may then register UI-linked tools | capabilities |

The view is conceptually an **MCP client of the host**, and the host is
an MCP server to the view that proxies to the real server. The SDK keeps
these as two separate connections so that "iframe capabilities [don't
leak] into the server connection" (`docs/overview.md`).

## 2. Resources and the tool link

```jsonc
// tools/list
{ "name": "get_weather",
  "_meta": { "ui": { "resourceUri": "ui://weather-server/dashboard",
                     "visibility": ["model", "app"] } } }

// resources/read
{ "contents": [{ "uri": "ui://weather-server/dashboard",
                 "mimeType": "text/html;profile=mcp-app",
                 "text": "<!DOCTYPE html>…",
                 "_meta": { "ui": {
                   "csp": { "connectDomains": ["https://api.example.com"],
                            "resourceDomains": ["https://cdn.jsdelivr.net"],
                            "frameDomains": [], "baseUriDomains": [] },
                   "permissions": { "clipboardWrite": {} },
                   "domain": "a904794854a047f6.claudemcpcontent.com",
                   "prefersBorder": true } } }] }
```

- **The template is declared up front, separate from the data.** The
  spec's reasons: the host can prefetch and cache it, review it at
  connection time, hash it, and allow-list it. OpenAI's guidance adds
  that the URI is a cache key, so a breaking change to the HTML should
  get a new URI.
- **`_meta.ui` resource metadata may sit on the listing, the read, or
  both**; the read wins. Hosts must check both.
- **`visibility`** defaults to `["model", "app"]`. `["app"]` makes an
  **app-only tool**: callable by the view, hidden from the model. Host
  rules are MUSTs: never put a tool without `"model"` in the agent's
  tool list; reject a view's `tools/call` for a tool without `"app"`;
  never let a view call an app-only tool on a different server.
- **`domain`** asks for a stable sandbox origin (for OAuth callbacks,
  CORS, API-key allow-lists). Its format is host-defined: Claude wants
  the first 32 hex characters of SHA-256 of the server URL plus
  `.claudemcpcontent.com`; ChatGPT derives a subdomain of
  `oaiusercontent.com` from the server URL. Without it the origin is
  usually per conversation.
- The flat `_meta["ui/resourceUri"]` key is deprecated but still read by
  Claude Desktop, Codex and Open WebUI; ChatGPT also reads its own alias
  `_meta["openai/outputTemplate"]`.

## 3. Rendering and the sandbox

The spec stopped mandating an architecture on 2026-11-04 (PR #717,
"relax double sandboxed iframe architecture requirements"). It now
states requirements only:

- a web host MUST wrap the view in an iframe on **a different origin**
  from the host, with `allow-scripts allow-same-origin`;
- the document MUST be **served by a server the host controls**, so CSP
  arrives as real HTTP headers; a third-party MCP server may not serve
  the iframe's document;
- CSP enforces the declared domains, `frame-src 'none'` and
  `base-uri 'self'` unless declared, `object-src 'none'`, and this
  default when nothing is declared:
  `default-src 'none'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; media-src 'self' data:; object-src 'none'; connect-src 'none';`
- the host MAY tighten and MUST NOT loosen; it SHOULD log CSP
  configurations and SHOULD warn the user when a view wants external
  access;
- the host sends nothing to the view before `ui/notifications/initialized`.

Two non-normative patterns are described. The original **double
iframe** (an outer host-controlled sandbox proxy that writes the HTML
into an inner iframe, with reserved `ui/notifications/sandbox-*`
messages) and a **single iframe**, either a universal shim that turns
`postMessage`d bytes into a `blob:` URL (likened to Gemini's
SafeContentFrame) or a host-served cross-origin endpoint that streams
the HTML with the right headers. Downloads are blocked in the sandbox
(`allow-downloads` is not set), which is why `ui/download-file` exists.

One consequence is easy to miss: **because the sandbox has
`allow-same-origin` and a host often uses one origin per connector,
every view from the same server in a conversation shares an origin.**
Claude documents using `BroadcastChannel` across those views
(§7 below) and warns that a fixed `domain` widens the shared origin to
every conversation.

## 4. Lifecycle and data passing

1. **Discovery.** `tools/list` carries the `_meta.ui` links. The host
   may fetch and cache the `ui://` resource now.
2. **Call and mount, in parallel.** The host calls the tool and mounts
   the iframe. The view sends `ui/initialize` (with `appCapabilities`)
   and gets back `hostCapabilities`, `hostInfo` and `hostContext`, then
   sends `ui/notifications/initialized`.
3. **Input.** Zero or more `ui/notifications/tool-input-partial` while
   the model is still streaming the arguments (best-effort repaired
   JSON; the view MUST NOT act on it), then exactly one
   `ui/notifications/tool-input`.
4. **Result.** `ui/notifications/tool-result` carries the whole
   `CallToolResult`, or `ui/notifications/tool-cancelled` with a reason
   (user action, sampling error, "classifier intervention").
5. **Interactive phase.** The view calls tools and sends requests (§5).
6. **Teardown.** `ui/resource-teardown` is a request, and the host
   SHOULD wait for the answer "to prevent data loss". A view can ask to
   be closed with `ui/notifications/request-teardown`.

**The result has three projections, and the spec names their audiences**:

| Field | Audience, per the spec's best practices |
|---|---|
| `content` | "Text representation for model context and text-only hosts" |
| `structuredContent` | "Structured data optimized for UI rendering (not added to model context)" |
| `_meta` | "Additional metadata … not intended for model context" |

The core MCP tools spec does not say `structuredContent` stays out of
model context, and hosts differ (see `catalogue.md` §1d and
`../agent-interactive-views.md` §3). The split is a convention the
extension recommends, not a guarantee the server can rely on.

## 5. What the view can ask for

All requests are gated by `hostCapabilities`; a view must feature-detect.

| Method | Direction | What it does | Host capability |
|---|---|---|---|
| `tools/call`, `tools/list` | view → host → server | call the **same server's** tools, including app-only ones | `serverTools` |
| `resources/read` | view → host → server | read a resource (binary blobs, large files) | `serverResources` |
| `ui/message` | view → host | put a `role: "user"` message into the chat; "also trigger[s] follow-ups" | `message` (by content modality) |
| `ui/update-model-context` | view → host | set context the model sees on **future** turns; each call overwrites the last; the host may defer it to the next user message and should send only the latest | `updateModelContext` (by modality) |
| `ui/open-link` | view → host | open a URL in the user's browser | `openLinks` |
| `ui/download-file` *(draft)* | view → host | save a file, as an `EmbeddedResource` or a `ResourceLink` | `downloadFile` |
| `ui/request-display-mode` | view → host | ask for `inline`, `fullscreen` or `pip`; the host answers with the mode it actually set | `availableDisplayModes` in context |
| `sampling/createMessage` *(draft)* | view → host | ask the host's model for a completion, optionally with tools; host "has full discretion" and SHOULD rate-limit, cost-control and ask the user | `sampling` |
| `notifications/message` | view → host | logging | `logging` |
| `ui/notifications/size-changed` | view → host | the view's content size, for flexible containers | — |

`hostContext` gives the view the tool definition and call id
(`toolInfo`), `theme`, 36 standard CSS variables and font CSS,
`displayMode`, `containerDimensions` (fixed or max per axis), `locale`,
`timeZone`, `platform`, touch and hover, and safe-area insets. Changes
arrive as `ui/notifications/host-context-changed`.

## 6. App-provided tools (draft)

In the draft, the view can **register tools that the host and the model
call**: `app.registerTool(name, {inputSchema, …}, handler)`, served over
`tools/list` and `tools/call` from host to view, with
`notifications/tools/list_changed` when they change. The motivation is
"semantic introspection": the model cannot see the iframe's DOM, so the
view exposes operations (select these rows, set this filter, read the
current state) instead.

| | Server tools | App tools |
|---|---|---|
| Lifetime | the server process | while the view is loaded |
| Trust | trusted | "Sandboxed (untrusted)" |
| Discovery | server `tools/list` | the view's `tools/list` |

The security section asks hosts to attribute app tools visibly, to
require confirmation for anything not `readOnlyHint: true`, to stop app
tools shadowing server tool names, and recommends limits of 50 tools per
app, 30 s per call and 10 MB per result. App tools disappear on teardown
and MUST NOT persist across sessions. For long work the view SHOULD call
a server tool and return the server's **task** handle, so the host can
keep polling after the iframe is gone.

**WebMCP interop** (added 2026-10-27, PR #829): a view's tools and the
W3C-incubated `document.modelContext.registerTool()` are "two surfaces
for the same capability". The SDK mirrors `registerTool()` tools into
`document.modelContext` and bridges WebMCP tools back over `tools/list`,
and a host that can see both MUST consume exactly one.

## 7. Negotiation under `2026-07-28`

Before `2026-07-28` extensions were negotiated in `initialize`
(`capabilities.extensions`), outside the published schema. Under the
stateless revision there is no `initialize`:

- **the client sends its capabilities on every request**, in
  `_meta["io.modelcontextprotocol/clientCapabilities"].extensions`;
- **the server advertises its own** in the `server/discover` response,
  which carries `ttlMs` and `cacheScope`.

So whether a host "supports UI" is now **a property of each request,
not of the connection**. A server that checks the capability before
registering UI-linked tools (the spec's SHOULD, and the `getUiCapability`
helper) can return different `tools/list` results to the same client
depending on what that request declared. The spec's degradation rules
still apply: servers SHOULD give every UI-enabled tool a text fallback,
MUST return a meaningful `content` array even when UI is available, and
MAY register different tool variants per host capability.

## 8. The security model, in one table

| Threat (spec §"Threat Model") | Mitigation in the spec | What it does not cover |
|---|---|---|
| Malicious HTML | iframe sandbox, separate origin, host-served document | |
| Sandbox escape | browser isolation | a desktop host's webview is the host process's neighbour (Backslash's point that "a sandbox escape here is a full IDE compromise") |
| Unauthorised tool execution | visibility checks; same-server only; host may require approval or block | a view calling its own server's **write** tools: Claude does not show an approval for `callServerTool` |
| Exfiltration | CSP `connect-src` from declared domains only; MUST NOT loosen | data the host itself hands the view (`structuredContent`, `hostContext`) |
| Phishing, social engineering | "Hosts should clearly indicate sandboxed UI boundaries" | |
| *(not listed)* Injection into the model | — | `ui/message`, `ui/update-model-context` and app-tool results are text a third party wrote, entering the model's context |

The last row is the one the spec leaves to hosts. Claude's answer is to
make `ui/message` need the user's agreement (an approval or a prefilled
message box with a "Use caution before running this prompt" banner), cap
it at 8,000 characters, and refuse rapid or retried sends. VS Code
prefills the input box and never sends. Neither documents a check on
`ui/update-model-context`, which by design reaches the model silently
(VS Code shows it as an attachment).

## 9. What changed between the stable and draft revisions

| In draft only | Notes |
|---|---|
| App-provided tools and WebMCP interop | Claude ships app tools to "a limited set of organizations" |
| `sampling/createMessage` from the view | with SEP-1577 tool use |
| `ui/download-file`, `ui/notifications/request-teardown` | |
| Rendering requirements instead of a mandated double iframe | 2026-11-04 |
| Long-running app tools through core tasks | |
| `hostCapabilities` fields (`sandbox`, `updateModelContext` modalities, `downloadFile`) | PR #653, 2026-07-07 |

The SDK went to **2.0** on 2026-09-08, moving onto the split
`@modelcontextprotocol/{client,server,core}` 2.x packages and zod 4.2.
The wire protocol did not change: "The `ui/*` messages exchanged over
the iframe channel are byte-identical to 1.x."

## 10. What is still left open

From the spec's own "Extensibility" list: more than one view per
response, state persistence and restoration, per-resource sandbox
policies, view-to-view communication, screenshot or preview APIs, and
the `externalUrl` content type that MCP-UI had. Every one of these is a
host-specific workaround today: `localStorage` keyed by a server-minted
`viewUUID` for state, ChatGPT's `widgetState`, Claude's
`BroadcastChannel` supersession for views that represent one piece of
state, and embedded sites through `frameDomains`.
