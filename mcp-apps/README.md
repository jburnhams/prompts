# MCP Apps (SEP-1865): interactive views over MCP

- **Type**: an MCP extension, its SDKs, and the hosts and servers that
  use it, read for what they mean for an MCP-based data-analysis agent.
  No system prompts are stored here; the material is protocol, host
  behaviour and server design.
- **Prompted by**: Jonathan, 2026-11-12: "start a deep dive into mcp
  apps … for our data analysis agents this could be really useful. see
  what other agents and harnesses and tools support it (i believe vscode
  does?) and what other people are doing with it."
- **Read**: 2026-11-12. The spec and SDK from
  `modelcontextprotocol/ext-apps` at `ea3e9d0` (SDK 2.1.0), MCP-UI at
  `2b10490`, the client matrix and extensions overview from
  `modelcontextprotocol/modelcontextprotocol` at `99a8e46`, Codex at
  `c0cc9fc`, Open WebUI and Cline from `main` on the day, and vendor
  documentation for Claude, ChatGPT, VS Code, Microsoft 365 Copilot,
  Cursor and Goose. Details in [`../sources.md`](../sources.md), "MCP
  Apps (read 2026-11-12)".
- **Licenses**: ext-apps is mid-transition from MIT to Apache-2.0 (new
  contributions Apache-2.0, docs CC-BY-4.0); MCP-UI Apache-2.0.

## What it is, in one paragraph

An MCP server declares an HTML view as a `ui://` resource and links it
to a tool with `_meta.ui.resourceUri`. A host that declares the
`io.modelcontextprotocol/ui` extension renders the view in a sandboxed,
cross-origin iframe beside the tool call, and pushes the call's
arguments and result into it over `postMessage` JSON-RPC. The view can
then call the same server's tools (including **app-only** tools the
model never sees), read resources, send a message into the chat, set
context the model will see next turn, open links, download files and
ask for fullscreen. In the draft it can also register **tools of its
own** for the model to call. A host without the extension shows the
tool's text result. Full mechanics are in [`spec.md`](./spec.md).

## The files

| File | What |
|---|---|
| [`spec.md`](./spec.md) | How it works: resources and the tool link, the sandbox and CSP rules (relaxed 2026-11-04), lifecycle and the three result projections, every view request, app-provided tools and WebMCP, negotiation under the stateless `2026-07-28` revision, the security model and its gap, stable vs draft |
| [`catalogue.md`](./catalogue.md) | Hosts with their level of support, a four-host comparison, Codex's pass-through shape, which hosts let `structuredContent` reach the model; SDKs, frameworks and test tools; servers and apps (data first); adjacent protocols (A2UI, AG-UI, Apps SDK) |
| [`data-analysis.md`](./data-analysis.md) | Three shapes of data app and which keeps rows out of the model; Rill and Hex read closely; what breaks; eight design rules |

The new concept, a result that keeps calling tools and writing context
after delivery, is in a feature document,
[`../agent-interactive-views.md`](../agent-interactive-views.md).
Proposals for Forge, **none adopted**, are in
[`../agent-design/proposals-mcp-apps-2026-11.md`](../agent-design/proposals-mcp-apps-2026-11.md).

## Answers to the questions asked

**Does VS Code support it?** Yes, as an experimental feature of GitHub
Copilot Chat, off by default behind `chat.mcp.apps.enabled`, since
2026-01-26 in Insiders. It is the most limited of the major hosts:
inline only, `ui/message` fills the input box without sending, context
updates show as attachments, no camera, microphone or geolocation.

**Who else supports it?** Claude (web, Desktop, mobile: the fullest
implementation), ChatGPT (the standard plus `window.openai` extras),
Microsoft 365 Copilot (declarative agents, since April 2026), Cursor
(since 2.6), Goose (experimental), Postman, MCPJam, Archestra,
PostHog Code, Kiro Crew, Glean, LibreChat, and in source Open WebUI.
**Claude Code does not**, and no terminal agent renders views. Codex
passes the capability through to servers only when its front end can
render. See [`catalogue.md`](./catalogue.md) §1.

**What are people building?** Mostly work tools (Asana, Figma, Slack,
Canva), drawing (Excalidraw, tldraw), viewers (PDF, maps) and, the
largest single category, **charts and dashboards**: Hex, Amplitude,
Rill, Paddle, and a long tail of chart servers. See
[`catalogue.md`](./catalogue.md) §3 and
[`data-analysis.md`](./data-analysis.md).

## Eight findings

1. **The model/view split is real but not guaranteed.** The extension
   says `structuredContent` is "not added to model context"; core MCP
   does not, Claude documents keeping it out only when there is text
   (for app tools), and Open WebUI appends it. A data server should assume rows it returns may be
   read by the model.
2. **App-only tools are the important primitive for data.** A tool with
   `visibility: ["app"]` is absent from the model's tool list and
   callable by the view, so a chart can re-query, page and drill down
   without model turns or tool-schema tokens. It is also invisible to
   the user in Claude (no approval), which is why Rill's reviewer asked
   for metering.
3. **The best data apps send a spec and a binding, not rows.** Rill's
   model writes a chart spec and a semantic-layer binding; the server
   queries; the view re-queries through an app-only tool and reports
   its state back with `ui/update-model-context`. This is the same
   shape as Forge's `*.vl.json` citing a `table://` ref.
4. **"Support" ranges from inline-only to entry points.** Claude can
   open an app from the Artifacts page with no prompt and pin it to
   the sidebar; VS Code renders inline only. A view has to degrade
   across that range.
5. **Negotiation is per request under `2026-07-28`.** The client sends
   its extensions in each request's `_meta`, so a harness can declare
   UI for one run and not another, and a server's `tools/list` can
   differ between them.
6. **A headless harness has a defined role: pass-through.** Codex
   declares the extension only when its front end did, filters
   visibility itself, and records the view descriptor on the tool-call
   item so a later front end can render it.
7. **The view is a new author of model context.** `ui/message` and
   `ui/update-model-context` are text a third party wrote. Careful hosts
   make `ui/message` need the user's agreement; nobody documents a
   check on `update-model-context`.
8. **The spec keeps moving under a stable wire.** SDK 2.0 (September)
   changed every dependency and not one wire byte; the draft has added
   app tools, sampling, downloads and WebMCP since the stable revision,
   and stopped mandating the double iframe on 2026-11-04.

## Corrections to this collection

- [`../agent-tool-result-transport.md`](../agent-tool-result-transport.md)
  §8 (written 2026-08-21) said the view's CSP "blocks external network
  requests, so the view must be self-contained" and listed support as
  "Claude (web and desktop), VS Code Insiders, Goose and Postman". The
  default CSP does block them, but a resource can declare
  `connectDomains`, `resourceDomains`, `frameDomains` and
  `baseUriDomains`; and the host list is now much longer. A note there
  points here.
- [`../agent-design/generative.md`](../agent-design/generative.md) §5a
  says the `content` / `structuredContent` split is blocked on ADK-Java's
  MCP SDK pin. That blocker is gone now that Keel has its own MCP client
  on `2026-07-28` (decision row "MCP revision", 2026-11-11). This is
  proposal 1 in the proposals file; `generative.md` is not edited here.
