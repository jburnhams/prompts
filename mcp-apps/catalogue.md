# MCP Apps catalogue: hosts, SDKs and servers

*Compiled 2026-11-12. "Source" means read in code at the SHA in
[`../sources.md`](../sources.md), "MCP Apps (read 2026-11-12)". "Docs"
means the vendor's own documentation. "Listed" means it appears in the
official client matrix
(`modelcontextprotocol.io/extensions/client-matrix`, repo `99a8e46`) or
the MCP-UI host table and nothing more was checked. Secondary sources
are named where they are the only evidence.*

---

## 1. Hosts

### 1a. Support matrix

| Host | MCP Apps | Level and limits | Evidence |
|---|---|---|---|
| **Claude** (web, Desktop, iOS, Android) | Yes, since 2026-01-26 | The fullest implementation. Inline, side panel and full screen. App tools (limited orgs), entry points on the Artifacts page with pinning (limited orgs, Verified or custom connectors, remote only), embedded sites, downloads. `ui/message` needs the user's agreement. Requires Claude's `ui.domain` format for a stable origin. App tools, entry points and embedded sites need a **remote** server. | Docs (claude.com/docs/connectors/building/mcp-apps/*) |
| **Claude Code** | **No** | Calls the tool and gets text. | Matrix; mcpbundles guide |
| **ChatGPT** (web; Business, Enterprise, Edu) | Yes | Implements the standard; `window.openai` kept as a compatibility layer with ChatGPT-only extras: `widgetState`, `uploadFile`/`selectFiles`/`getFileDownloadUrl`, `requestModal`, `requestCheckout` (private beta). Remote servers only. Not on mobile per one guide. Admin-approved connectors freeze the tool list. | Docs (developers.openai.com/apps-sdk/mcp-apps-in-chatgpt); mcpbundles guide |
| **Codex** (CLI core and app-server) | Pass-through | The core does not render. The app-server **forwards the MCP Apps extension to MCP servers only when its own client (an IDE or desktop front end) declares it**, filters out extensions it does not know, hides tools whose `visibility` lacks `model`, and **records the UI descriptor (`mcp_app_ui {resource_uri, preferred_model_display_mode}`) on the tool-call item** in thread history. | Source, `openai/codex` `c0cc9fc` |
| **VS Code** (GitHub Copilot Chat) | Yes, experimental | Off by default (`chat.mcp.apps.enabled`). Inline only, no fullscreen or pip. `ui/message` fills the input box and never sends. Context updates appear as attachments. Clipboard write only; no camera, mic or geolocation. Shipped in Insiders 2026-01-26. | Docs (code.visualstudio.com extension guide); VS Code blog |
| **Microsoft 365 Copilot** | Yes, since April 2026 | Inline required; side-by-side optional. Widgets from MCP Apps and the OpenAI Apps SDK. Declarative agents built with Agents Toolkit ≥ 6.12; one secondary source says Copilot Studio agents do not render widgets. Entra SSO or OAuth 2.1. | Docs (learn.microsoft.com plugin-mcp-apps); Andrew Connell |
| **Cursor** | Yes, since 2.6 (March 2026) | Launch examples Amplitude, Figma, tldraw. A later entry added structured content. A user-reported regression in 3.11.19. | Changelog; forum |
| **Goose** (Desktop) | Yes, experimental | Draft SEP-1865 since v1.19.0 (January 2026); MCP-UI since v1.3.0 (August 2025). Minimal: discovery, sandboxed render, basic relay. Apps can also run as standalone windows that can call tools and read resources but "cannot communicate with goose". | Docs (goose-docs.ai) |
| **Postman**, **MCPJam**, **Archestra.AI**, **PostHog Code**, **Kiro Crew**, **Glean** | Yes | MCPJam also does Tasks and Skills; Glean does Tasks, Skills and Enterprise Auth. | Listed |
| **MCP Inspector** | Partial | App review mode. | Listed |
| **LibreChat**, **Smithery** playground, **mcp-use** inspector, **Alpic** playground | Yes | | Listed (MCP-UI table, ext-apps README) |
| **Nanobot**, **fast-agent** | MCP-UI only | Nanobot renders and acts; fast-agent renders without actions. | MCP-UI table |
| **Open WebUI** | Yes (backend found in source) | Reads `ui://` resources up to 5 MB, builds its own CSP (stricter than the spec's: adds `form-action 'none'`, validates every domain with a regex), and **binds each view's callbacks to its server and tool with an HMAC** of `[server_id, tool_name]` under the instance secret, verified separately from viewer auth. Not in either matrix. | Source, `open-webui/open-webui` main, 2026-11-12 |
| **Cline** | Capability only (found in SDK source) | The SDK declares the extension and exposes `isMcpToolVisibleToModel` / `isMcpToolVisibleToApp`. Rendering in the VS Code extension was not confirmed. | Source, `cline/cline` main, 2026-11-12 |
| **DeepSeek Harness** (`dsh web`) | Via a third-party plugin | `oriliz/dsh-mcp-apps-host` renders cards in the web UI. Supports `ui/initialize`, `tools/call` (own server only, with `session_id` injected), `resources/read` (`ui://` only), `ui/update-model-context` (as a collapsed context row), `ui/message`. **Bridge calls skip the agent pipeline and never reach the session log.** | Plugin README |
| **Gemini CLI**, **Devin Desktop** (ex-Windsurf), **OpenCode**, **Zed**, **Copilot CLI** | Not found | No evidence of rendering. Copilot CLI was demoed with a flame-graph app at AI Engineer Europe 2026, which suggests work in progress. | Docs; searches |
| **Spring AI** 2.0.0-M3, **C# SDK** | Server side | Metadata on tools and resources (Spring); "experimental" extension package (C#). | Spring blog 2026-03-18; C# SDK docs |

### 1b. What "support" means varies a lot

Four hosts publish enough detail to compare. The differences are the
ones a data app would hit first.

| | Claude | ChatGPT | VS Code | M365 Copilot |
|---|---|---|---|---|
| Display modes | inline, side panel, fullscreen | inline, fullscreen, pip, plus `requestModal` | inline only | inline, side-by-side |
| `ui/message` | user agrees (approval or prefilled box), ≤ 8,000 chars, rate-limited | `sendFollowUpMessage` alias | prefills the box, never sends | not documented |
| `ui/update-model-context` | yes | yes | shown as an attachment | not documented |
| App tools (model → view) | yes, limited orgs; 64 tools, 45 s, 100,000 chars of result text | not documented | no | no |
| View calls server tools | yes, **no approval shown** | yes | yes | yes |
| Stable origin | `{sha256(url)[:32]}.claudemcpcontent.com` | subdomain of `oaiusercontent.com` | not documented | derived from server domain; CORS must allow it |
| Open without a prompt | entry points on the Artifacts page, pinnable | no | no | no |
| Local servers | renders; app tools and entry points need remote | remote only | yes | remote |

### 1c. Two host shapes

Most hosts are **chat clients that render**. Codex shows a second
shape that matters for a headless harness: **a core that does not
render but sits between a renderer and the servers.** Its rules, from
source:

- declare `io.modelcontextprotocol/ui` downstream **only if the
  front end declared it upstream**, and pass through only extension ids
  it recognises (`client_mcp_extensions`);
- apply `visibility` itself, in the tool catalogue, so app-only tools
  never reach the model whatever the front end does
  (`tool_is_model_visible`, which cites the stable spec);
- **capture the presentation on the history item at call time**, so a
  front end that resumes a thread later can still mount the view
  ("Presentation captured from the invoked descriptor; absent in older
  history").

### 1d. Whether `structuredContent` reaches the model

The extension says it should not. Hosts disagree:

| Host | What the model sees | Evidence |
|---|---|---|
| Claude, app tools | `text` blocks; `structuredContent` "only when it receives no text at all from `content`" | Docs |
| Open WebUI | `content`, **plus `structuredContent` serialised as an extra text block whenever it differs from the text** | Source (`normalize_tool_result`) |
| DeepSeek Harness plugin | "Card HTML never enters the model context"; result handling not stated | README |
| Others | not documented | |

`agent-tool-result-transport.md` §3f found the same disagreement for
plain tools a year earlier (SEP-1624: Cursor prefers `content`, VS Code
prefers `structuredContent`). For a data tool the practical rule is to
**assume rows in `structuredContent` may reach the model** and size
them accordingly, or move them behind an app-only tool the view calls.

---

## 2. SDKs, frameworks and tooling

| Name | Role | Notes |
|---|---|---|
| **`@modelcontextprotocol/ext-apps`** 2.1.0 | Official SDK | `App` (view), `AppBridge` (host), `./server` (`registerAppTool`, `registerAppResource`, `getUiCapability`), React hooks, `*-with-deps` CDN bundles. Builds on MCP TS SDK 2.x. Ships `examples/basic-host`, a reference host. Also ships **agent skills** (`create-mcp-app`, `migrate-oai-app`, `convert-web-app`, …) as a Claude Code plugin. |
| **`@mcp-ui/client`** 7.1.1, **`@mcp-ui/server`** 6.1.0, Python and Ruby servers | Community SDK, now `MCP-UI-Org/mcp-ui` | `AppRenderer` is the recommended host renderer; `UIResourceRenderer` for legacy MCP-UI hosts (`rawHtml`, `externalUrl`, `remoteDom`). Last commit 2026-07-08. |
| **Vercel AI SDK** (`@ai-sdk/mcp`, `@ai-sdk/react`) | Host framework | `MCPAppRenderer`, `splitMCPAppTools` (returns `modelVisible` and `appVisible`; pass only the first to the model), `readMCPAppResource`, `mcpAppClientCapabilities`. The app's `tools/call` proxy is yours to write and should 403 anything not app-visible. |
| **TanStack AI**, **assistant-ui** | Host frameworks | assistant-ui's renderer acts only on `ui://`. |
| **CopilotKit** | Host framework | AG-UI, A2UI and MCP Apps examples side by side (`CopilotKit/generative-ui`). |
| **FastMCP** (Python) | Server framework | `AppConfig` links tools to `ui://` resources and sets visibility; **Prefab** (`@mcp.tool(app=True)`) builds the view from Python components; `fastmcp dev apps` simulates a host; `ctx.client_supports_extension(UI_EXTENSION_ID)`. |
| **mcp-use** (10.9k stars) | Full-stack TS framework | Apps for ChatGPT and Claude from one codebase; inspector; templates including `mcp-chart-builder` (ECharts). |
| **Skybridge** (Alpic) | Full-stack TS framework | React, type-safe, platform-agnostic; Alpic playground and hosting. |
| **sunpeak** | Testing framework and app framework | Security-testing guidance for views. |
| **MCPJam Inspector** | Test host | Chat, inspect, debug, evaluate apps. |
| **Spring AI** 2.0.0-M3 | Java server | `@McpTool`/`@McpResource` with metadata. The only Java route found; the official Java SDK has no dedicated support. |
| **mcpkit-core** (Rust), **mcp_server** (Elixir), C# SDK | Servers | Extension modules. |

## 3. Servers and apps

### 3a. Data, analytics and charts

| Server | What the view does | How data reaches it | Evidence |
|---|---|---|---|
| **Hex** (launch partner) | Shows the Hex agent's thinking steps, then a carousel of charts and tables with citations, styled from Hex; starts and continues Hex Threads | Server runs its own agent; the view shows its outputs | Hex blog; Claude listing |
| **Amplitude** (launch partner) | Analytics charts the user can adjust in place | Server-side query | Launch coverage |
| **Rill** (`create_chart`, merged 2026-11-07) | A Svelte + Vega widget compiles a Flint chart spec on the client; fullscreen controls for grain, top-N, comparison, chart type; follows host and project themes; "Open in Rill" replays the call | Model sends a **chart spec plus a semantic-layer binding** (metrics view, range, filter, grain), not rows. Server runs the query and returns rows, field metadata and theme. **An app-only `chart_data` tool** re-queries on control changes. **`ui/update-model-context` reports the current view** back. Text fallback is a Markdown table and a link. | PR #10016 |
| **Paddle** (2026-10-20) | Revenue, refunds, chargebacks, conversion charts with grain and preset ranges | Server-side metrics; text answer when the host can't render | Changelog |
| **ext-apps examples**: `cohort-heatmap`, `customer-segmentation`, `budget-allocator`, `scenario-modeler`, `system-monitor` | Heatmap, scatter clusters, sliders, what-if modelling, live polling | `structuredContent` plus an app-only polling tool (`system-monitor`). **`customer-segmentation` puts the whole dataset into `content` as JSON as well**, which on most hosts sends every row to the model. | Source |
| **MCP Dashboards** (`KyuRish/mcp-dashboards`) | ~32 chart tools, dashboards, KPI widgets, live polling; PNG, PPT, A4 and CSV export | Model formats the data into tool arguments; `render_from_url` and `poll_http` fetch server-side with private addresses blocked | README (warns of a malware look-alike package) |
| **ChartBrick**, **mcp-use chart builder** | Hosted chart connector; ECharts template | Model passes data | Sites |
| **AWS AgentCore sales demo** | Selector form → app-only `get-sales-data` → dashboard → PDF viewer with `ui/download-file` | `update-model-context` carries selections and results into the conversation | dev.to (AWS) |
| **Lloyd Richards, "Generative data viz"** | One render tool per chart type with an Effect `Schema` payload | Model writes the rows into the tool input. Found ~8.2k tokens of tool schemas and ~1 MB per widget bundle | Blog, 2026-04-07 |
| **Anthropic knowledge-work `data` plugin** | Self-contained HTML dashboards | **Not** MCP Apps: files, not views | Repo |

### 3b. Other categories worth knowing

- **Work tools at launch** (Claude, 2026-01-26): Asana, Box, Canva, Clay,
  Figma (FigJam diagrams), monday.com, Slack, with Salesforce later.
- **Drawing**: Excalidraw (`excalidraw/excalidraw-mcp`, 5.7k stars,
  "fast and streamable", the image on the MCP Apps overview page),
  tldraw.
- **Viewers**: PDF (ext-apps `pdf-server`, chunked binary reads through
  an app-only tool), maps (CesiumJS), video, sheet music, 3D.
- **Microsoft samples**: `microsoft/mcp-interactiveUI-samples`.
- **Odd but telling**: a "thinking block" card that renders a model's
  intermediate reasoning (`gpt-thinking-block-mcp`), and Pi, DeepSeek
  Harness and Codex listed as hosts by a scientific-figure library.

## 4. Adjacent protocols

| | MCP Apps | A2UI (Google) | AG-UI (CopilotKit) | OpenAI Apps SDK |
|---|---|---|---|---|
| What travels | HTML the server wrote | a declarative component tree (data) | events between agent backend and frontend | HTML plus `window.openai` |
| Who renders | the host, in a sandbox | the client's own components | the client app | ChatGPT |
| Trust model | isolation | data, not code | the app owns both ends | isolation |
| Relation | the standard | "actively working on bridging" to MCP Apps (vendor claim) | carries A2UI or MCP Apps | folded into MCP Apps; aliases kept |

Thoughtworks put MCP Apps in **Assess** (Radar vol. 35, April 2026),
noting that "teams should weigh whether the added complexity over plain
text responses is justified".
