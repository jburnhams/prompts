# Proposals from the MCP Apps deep dive (2026-11-12)

**Status: proposals only, none adopted.** Jonathan asked to discuss
before anything changes, so no other file under `agent-design/` is
edited. The research is in [`../mcp-apps/`](../mcp-apps) and the new
feature document
[`../agent-interactive-views.md`](../agent-interactive-views.md).

*Revised the same day.* The first version assumed Keel was headless and
treated MCP Apps mainly as a way to reach other vendors' chat hosts.
Jonathan's correction: **the Keel ecosystem owns most of the agent, the
UI and the MCP servers**, and the aim is to exploit the full breadth of
the spec. So Keel is a **host** as well as a client and a server, and
almost every feature of the spec has a use. Part A maps each feature to
Keel; Part B is the proposals.

## Where Forge, Keel and Lens stand today

- **Keel speaks MCP `2026-07-28` through its own client** (decision row
  "MCP revision", 2026-11-11), so the ADK-Java limits behind
  `artifacts.md` §8 ("one text block, no `structuredContent`") and
  `generative.md` §5a (the split "blocked on a version ceiling") no
  longer bind Keel. Both are still written as if they did.
- **Keel already supports artifacts from MCP servers** (Jonathan,
  2026-11-12): a server returns an artifact ref, and the agent has tools
  to query or manipulate the artifact without ingesting the data. Tools
  and the harness may both mint artifacts (2026-11-11).
- **Keel owns a UI** (Jonathan, 2026-11-12) as well as the agent and
  most servers. The design documents describe the UI only as an entry
  point (`manual` triggers from "chat commands, UI buttons", `run_as:
  invoker` sessions); what it renders is not designed yet.
- **Lens already has the right data shapes**: `table://` refs, a
  `table` artifact kind, and charts as `*.vl.json` Vega-Lite specs
  citing a `table://` ref and "rendered by the destination" (`data.md`
  §2a, §2b, §2e). The Keel UI can be that destination.

**What owning all three ends changes.** Most of the hard parts of MCP
Apps exist because host, server and view are written by different
parties who don't trust each other. When Keel writes the host and the
server, it can (a) trust first-party views more than third-party ones,
with the trust bound to a pinned template digest, (b) fill the gaps the
spec leaves (persistence, supersession, view-to-view, metering) in the
host instead of in every view, and (c) still render the same views in
Claude, ChatGPT, VS Code and Microsoft 365 Copilot, because it is the
standard.

---

# Part A. Every feature, and what Keel does with it

"Use" is the recommendation. **Now**: worth building in the first
slice. **Next**: once the first slice works. **Later**: wait for a
trigger. **No**: decided against, with the reason.

### A1. Server side: resources and tool metadata

| Feature | What Keel does with it | Use |
|---|---|---|
| `ui://` resource, `text/html;profile=mcp-app` | First-party servers ship views: Lens answer, chart, table explorer, run progress, Forge plan and review views (B6) | Now |
| Template declared up front, separate from data | Pin the HTML by digest at `:discover` like a tool description; a changed template is `tools_drift` (B2, B4) | Now |
| `_meta.ui.resourceUri` on a tool | Every first-party tool that produces something a person reads gets a view | Now |
| `visibility: ["model","app"]` / `["app"]` | App-only tools for paging, re-query, drill-down, polling, saving view state; never grantable to an agent (B2) | Now |
| `_meta.ui.csp` (`connectDomains`, `resourceDomains`, `frameDomains`, `baseUriDomains`) | First-party views declare **nothing**: libraries bundled, data through tools. Third-party views get what they declare, after policy (B5) | Now |
| `_meta.ui.permissions` (camera, mic, geolocation, clipboard) | Clipboard write only (copy SQL, copy figure); the rest refused by policy | Now (clipboard) |
| `_meta.ui.domain` | Keel assigns stable per-server origins itself (B5); a server's own `domain` is honoured only when it matches Keel's format | Now |
| `prefersBorder` | Honoured | Now |
| Text fallback in `content` | Kept, always: Slack, Jira, GitHub and terminals still get Markdown | Now |
| Per-request capability check (`getUiCapability`) | First-party servers return the same tools either way and vary only `_meta`; no text-only tool variants to maintain | Now |
| Listing-level vs read-level `_meta.ui` | Listing-level for first-party views, so policy can review CSP at `:discover` without reading | Now |

### A2. Host side: rendering and context

| Feature | What Keel does with it | Use |
|---|---|---|
| Sandboxed cross-origin iframe, host-served document with CSP headers | Keel UI serves each view from `{server-hash}.views.<keel-domain>` with CSP as headers; single-iframe, streamed (B5) | Now |
| `hostContext.theme`, 36 style variables, fonts | Map Keel's design tokens onto the standard variables, in `light-dark()`; first-party views use only those | Now |
| `displayMode` inline / fullscreen / pip | Inline in the conversation or run page; fullscreen for dashboards and diffs; pip for a running investigation's progress | Now |
| `containerDimensions`, `size-changed` | Flexible height with a max inline; fixed in fullscreen | Now |
| `locale`, `timeZone`, `platform`, touch, safe areas | Passed from the session; dates in charts render in the user's zone | Now |
| `toolInfo` (the tool and call id) | Lets a view know which call it renders; Keel adds the run id under `_meta` | Now |
| `tool-input-partial` (streaming arguments) | Show a chart or SQL as the model writes the spec, before the query runs | Next |
| `tool-input`, `tool-result`, `tool-cancelled` | Standard; `cancelled` carries Keel's stop reasons (budget, refusal, user stop) | Now |
| `host-context-changed` | Theme toggle, panel resize | Now |
| `ui/resource-teardown`, `request-teardown` | Keel always sends teardown and waits, unlike Claude web; views save state first | Now |

### A3. View to host: what a view may ask for

| Feature | What Keel does with it | Use |
|---|---|---|
| `tools/call` to the same server | Drill-down, paging, re-query, polling, saving state. Authorised as the run's principal, metered, recorded (B9) | Now |
| `resources/read` | Fetch large binaries (exported PDFs, images) and **artifact payloads** through a resource template over artifact refs | Now |
| `resources/list`, templates, `prompts/list` (in the SDK's `AppBridge`, not the spec table) | Let a view list a server's prompts as suggested follow-ups | Later |
| `ui/update-model-context` | The view tells the agent what the user is looking at (filters, selection, page). Keel shows it to the model as a **pinned, harness-framed view-state block**, newest view only, last write wins (B8) | Now |
| `ui/message` | "Ask about this", "Investigate this dip", "Approve this plan" buttons. A user turn **only after the user clicks**, attributed "via view X" (B8) | Now |
| `ui/open-link` | Open in the product, the warehouse console or the PR | Now |
| `ui/download-file` (draft) | CSV, PNG, SVG, PPT exports, sent as a `ResourceLink` to an artifact, never as an inline blob (B11) | Now |
| `ui/request-display-mode` | Granted within what the view declared | Now |
| `notifications/message` (logging) | Into the run's event log at debug level | Now |
| `sampling/createMessage` (draft) | First-party views only: "explain this cell", "summarise this table", on the economy tier and the run's budget. Refused for third-party views (B12) | Later |

### A4. Host to view: app-provided tools (draft)

| Feature | What Keel does with it | Use |
|---|---|---|
| `app.registerTool`, view `tools/list` / `tools/call` | **The agent drives the view the user has open**: set a filter, select rows, highlight an anomaly, switch chart type, scroll to a figure. Only in interactive runs with a live view (B7) | Next |
| `tools/list_changed` from the view | Tools appear and disappear with view state | Next |
| Long-running app tools via tasks | The view returns the server's task handle | Next |
| WebMCP interop | Keel's views use `registerTool`; WebMCP is ignored until a browser ships it | No |

### A5. Lifecycle gaps the spec leaves, filled by the host

| Gap | Keel host behaviour | Use |
|---|---|---|
| Several live copies of one view | The host supersedes: only the newest view per `(server, resourceUri, view key)` is live; older ones are greyed and their `ui/*` requests refused. No `BroadcastChannel` election in every view (B10) | Now |
| State lost on remount | A host-provided state store: an app-only `keel/view_state` tool keyed by `(run, view id)`, server-side, so state survives devices and reloads (B10) | Now |
| Views from history | A run's views are artifacts (B4), so reopening a run or a chat remounts each view from the recorded call and pinned template | Now |
| View-to-view | A dashboard view that hosts several chart views would need it; out of scope | Later |
| Opening an app without a prompt | **Standing views**: a view mounted from a saved call with `{}` or saved arguments, pinned in the Keel UI (Claude's "entry points", done natively). A weekly-revenue trigger's output becomes a pinned dashboard (B13) | Next |

### A6. Negotiation and protocol

| Feature | What Keel does with it | Use |
|---|---|---|
| Per-request client capabilities under `2026-07-28` | The Keel UI's runs declare `io.modelcontextprotocol/ui`; Jira, PR and Slack runs don't (B3) | Now |
| `server/discover` extensions | Recorded in the server snapshot | Now |
| Deprecated flat `_meta["ui/resourceUri"]`, `openai/outputTemplate` | Read on third-party servers, never written | Now |
| Tasks extension | Long investigate stages behind a view (B6) | Now |

---

# Part B. Proposals

## Summary

| # | Proposal | Role | Would amend | Recommendation |
|---|---|---|---|---|
| 1 | Server `structuredContent` that isn't an artifact ref is minted as one; it never enters context | client | `artifacts.md` §8; `generative.md` §5a; `data.md` §2d | Adopt now |
| 2 | Honour `visibility`; pin `_meta.ui` and the template digest in the snapshot | client | `keel/tools-and-agents.md` §4a, §4b | Adopt now |
| 3 | Declare the UI extension per run, only when the Keel UI (or another renderer) will show the result | client | `keel/tools-and-agents.md` §4a; `keel/run-spec.md` | Adopt now |
| 4 | A view is a run artifact, remountable from history | client, host | `artifacts.md` §5.1; `keel/outputs.md` §7a; `run.schema.json` | Adopt now |
| 5 | **The Keel UI is an MCP Apps host**: origins, CSP, bridge, policy | host | new `keel/views.md` | **Discuss scope** |
| 6 | First-party views for Lens and Forge, starting with Lens answer and chart | server | `lens-on-keel/`; `data.md` §2e; `forge-on-keel/` | Adopt with 5 |
| 7 | The agent can drive a live view through app tools | host, agent | `keel/views.md`; `keel/tools-and-agents.md` §4b | Next |
| 8 | What a view says to the agent: view state as a pinned block, messages only on a click | host, agent | `formats.md`; `keel/views.md` | Adopt with 5 |
| 9 | Rules for traffic a view starts: authority, metering, audit, binding | host, server | `keel/authority.md`; `keel/triggers-and-runs.md` §10 | Adopt with 5 |
| 10 | Host-level supersession and view state | host | `keel/views.md` | Adopt with 5 |
| 11 | Downloads from artifacts | host | `keel/views.md`; `artifacts.md` §6 | Adopt with 5 |
| 12 | Sampling for first-party views only | host | `keel/views.md`; `models.md` | Later |
| 13 | Standing views pinned in the UI | host | `keel/triggers-and-runs.md` | Next |
| 14 | The same servers render in Claude, ChatGPT, VS Code and Copilot | server | `keel/api.md`; `keel/authority.md` §8 | Discuss |
| 15 | Not now: WebMCP, third-party sampling, view-to-view, A2UI | — | `future.md` | Record |

---

## 1. Treat `structuredContent` as an artifact the server didn't mint

Keel's servers already return artifact refs. This covers the servers
that don't, mostly third-party ones built for MCP Apps hosts. Lift
`artifacts.md` §8's "one text block, no `structuredContent`" rule, and
handle a result like this:

- the model sees the projection of `content` that `formats.md` defines;
- a `structuredContent` payload is **minted as an artifact** by the
  harness (`table://` when tabular, `artifact://` otherwise), so it gets
  the same ref and query tools as one a Keel server returned;
- `structuredContent` **never enters the model's context**, even when
  `content` is empty (then the stub names the artifact and its size);
- the **view still receives the full `CallToolResult`**, including
  `structuredContent`, because the host pushes it to the iframe. The
  model and the view read different projections of one call.

**Why.** Hosts disagree on whether `structuredContent` reaches the model
(`mcp-apps/catalogue.md` §1d), so Keel picks the rule. Third-party data
servers built for MCP Apps (Paddle, Amplitude) put rows there. **Cost:**
small; the store, stub and query tools exist.

## 2. Honour `visibility`, and pin the view in the snapshot

- At `:discover`, visibility defaults to `["model", "app"]` when absent,
  so ordinary tools are unaffected. A tool whose **explicit** visibility
  lacks `"model"` is recorded as `app_only`. A `ToolRef` naming it is
  refused at publish (a new rule beside R4 and R8), so it is never in an
  agent's grant, loaded, deferred or revealed.
- `_meta.ui.resourceUri`, `_meta.ui.visibility` **and the digest of the
  `ui://` HTML** join the per-tool digest. A tool that gains a view,
  becomes app-only, or changes its view's code is `tools_drift`, so a
  server cannot change code running beside a user's conversation
  without a reviewed snapshot change. This is the spec's "predeclared
  resource review" (hash and allow-list templates) done Keel's way.

## 3. Declare the UI extension per run

Keel's client sends
`io.modelcontextprotocol/ui: {mimeTypes: ["text/html;profile=mcp-app"]}`
in a request's capabilities **only when the run's result will reach a
renderer**: runs started from the Keel UI, and (with proposal 14)
requests from another host. Jira, PR and Slack-origin runs don't
declare it. Simplest form: a template-level `views: true` flag, since a
template's entry surface is fixed. This is Codex's pass-through rule
(`mcp-apps/catalogue.md` §1c), and under `2026-07-28` capabilities
travel per request, so one deployment serves both kinds of run from the
same servers.

## 4. A view is a run artifact

When a called tool carries `_meta.ui.resourceUri` and the run declared
the extension, the harness records a `view` artifact:

```jsonc
{ "kind": "view", "view_id": "vw_…",
  "server": "mcp:lens", "tool": "lens_answer", "call_id": "…",
  "resource_uri": "ui://lens/answer", "resource_digest": "sha256:…",
  "display_mode": "inline", "arguments": { … },
  "result": { "content": […], "structured": "artifact://…" },
  "first_party": true }
```

`Run.outcome`'s artifact list carries it. The Keel UI mounts views from
these records, so reopening a run, a chat or a pinned dashboard shows
the same view on any device. It is Codex's "presentation captured from
the invoked descriptor", plus Claude's lesson that the transcript, not
client mount time, is the source of truth.

## 5. The Keel UI is an MCP Apps host *(discuss scope)*

A new `keel/views.md` would specify:

- **Origins.** Each server's views get a stable origin,
  `{sha256(server_id)[:32]}.views.<keel-domain>`, served by Keel with
  CSP as HTTP headers. Single sandboxed iframe, streamed from a
  host-served endpoint (the spec's faster pattern), `allow-scripts
  allow-same-origin`, no `allow-downloads`, no `allow-forms` unless
  declared. Views of different servers never share an origin.
- **CSP.** The spec's default plus declared domains, filtered by a
  deployment allow-list; `form-action 'none'` and domain validation as
  Open WebUI does. First-party views get the default only.
- **Bridge.** `@modelcontextprotocol/ext-apps` `AppBridge` (or
  `@mcp-ui/client`'s `AppRenderer`) in the UI; a Keel backend endpoint
  proxies the view's `tools/call` and `resources/read` to the server
  through Keel's MCP client, so every call passes the same authority,
  snapshot and audit path as the agent's calls (B9).
- **Host capabilities offered.** `serverTools`, `serverResources`,
  `openLinks`, `downloadFile`, `logging`, `message`,
  `updateModelContext`, `sandbox.permissions.clipboardWrite`; display
  modes inline, fullscreen, pip; `sampling` later and first-party only.
- **Trust tiers.** *First-party*: a Keel-owned server whose template
  digest is pinned in a published snapshot. *Third-party*: everything
  else. The tier decides CSP, sampling, how `ui/message` is presented,
  and whether app tools need approval (B7–B9, B12).
- **Policy per deployment.** Which servers may render at all, the
  domain allow-list, size cap on templates (Open WebUI uses 5 MB).

**What to settle.** What the Keel UI is today (a chat surface, a run
console, or both) and which surfaces it must render in; whether Slack
and Teams should link to the Keel UI for the interactive version.

## 6. First-party views

Ordered by value for the data use case.

| View | Server | What it shows | App-only tools |
|---|---|---|---|
| `ui://lens/answer` | Lens | The answer with claims; each figure expands to its query and table; charts inline | `lens_table_page`, `lens_requery` |
| `ui://keel/vega` | shared | Any `*.vl.json` that `data.md` §2e accepted; data from the cited `table://` ref, inlined up to a cap, else paged | `table_page` (a thin wrapper over the existing artifact query tools) |
| `ui://keel/table` | shared | A `table://` explorer: sort, filter, page, column profile | `table_page`, `table_profile` |
| `ui://lens/progress` | Lens | A running `lens.investigate` stage: steps, queries run, partial findings (pip mode); polls a task handle | `run_status` |
| `ui://forge/plan` | Forge | The plan with its acceptance criteria; "Approve" and "Request changes" send `ui/message` on click, bound to the plan digest (`formats.md` §6) | — |
| `ui://forge/review` | Forge | Findings grouped by risk tier, each linked to its diff hunk | `finding_detail` |

Design rules from `mcp-apps/data-analysis.md` §5 apply: `content` is a
summary, never rows; the model writes a spec and a binding, not data;
interactions go through app-only read-only tools; view state goes back
through `update-model-context`; every view has a text fallback and a
link. The `ui://keel/vega` renderer is the one-tool answer to Lloyd
Richards' 8.2k tokens of per-chart schemas.

## 7. The agent drives a live view *(next)*

With app-provided tools, a first-party view registers tools such as
`set_filter`, `select_rows`, `highlight`, `set_chart_type`,
`scroll_to_claim`. While the view is live in an interactive run, the
agent sees them, namespaced `view:<view_id>/<tool>`, as a dynamic group
(`keel/tools-and-agents.md` §4b): added on mount, removed on teardown.

- `readOnlyHint: true` tools on first-party views need no approval;
  anything else asks the user. Third-party view tools always ask.
- Limits: Claude's (64 tools, 45 s per call, 100,000 characters of
  result) are a good default.
- They never appear in hands-off runs, which have no live view, and are
  never part of a published snapshot.

This is what turns a chart into something the user and the agent work
on together: "show only EMEA" changes the chart the user is looking at
instead of drawing a new one.

## 8. What a view says to the agent

- **`ui/update-model-context`** becomes a **pinned view-state block**,
  harness-framed and marked as coming from view X of server Y, the run
  steering doc's "pinned state notice" (`agent-run-steering.md` §1).
  Last write wins, newest instance only, sent with the next turn, and
  dropped when the view is torn down. Size-capped. For third-party views
  it is framed as untrusted data like a tool result.
- **`ui/message`** is a user turn **only when the user clicked** in a
  first-party view; Keel records "via view X" as its provenance. For
  third-party views it prefills the input box, as VS Code does. Caps as
  Claude's: 8,000 characters, no automatic sends, a cooldown after a
  decline.
- A first-party "Approve" from `ui://forge/plan` is an `approve` answer
  bound to the plan digest, so the existing binding rule applies.

## 9. Rules for traffic a view starts

- **Authority.** Every view call runs as the run's principal under the
  run's delegation, never wider. App-only tools are read-only unless a
  template names them as writes with an approval.
- **Metering.** View calls count against the run's budget and a
  per-view rate limit, as `view_call` run events. This answers Rill's
  reviewer's "unmetered query cost" objection up front.
- **Audit.** View calls are in the run record. The DeepSeek Harness
  plugin's bridge calls "never reach the session JSONL"; that is the
  failure to avoid.
- **Binding.** A view's callbacks are bound to the **run (or view)**,
  the server and the tool that opened it, and every `table://` a view
  pages is checked against that run's artifacts. Open WebUI's HMAC
  covers only `[server_id, tool_name]`, so two answers from the same
  tool would share a binding; Keel's adds the run identity.

## 10. Supersession and state in the host

- **Supersession.** The host marks older views of the same
  `(server, resourceUri, view key)` as superseded: greyed, and their
  `update-model-context`, `ui/message` and app tools refused. The view
  key comes from the server in `_meta` (Claude's server-minted key), so
  ordering is by call, not by mount time.
- **State.** An app-only `keel/view_state` get/put tool, provided by the
  host and keyed by `(run, view_id)`, stores small JSON server-side.
  Views stop needing `localStorage`, and state follows the user across
  devices. It is in the run record, so it is reviewable.

## 11. Downloads from artifacts

`ui/download-file` with a `ResourceLink` to an artifact (CSV of a
`table://`, PNG or SVG of a chart, a generated PPTX or PDF). The host
resolves it through `artifacts.md` §6's fetch path with the user's
authority and shows a confirmation, sanitising the file name. No large
blobs travel through `postMessage`.

## 12. Sampling for first-party views *(later)*

A first-party view may call `sampling/createMessage` for small, local
help ("explain this column", "summarise these 20 rows") on the economy
tier, against the run's budget, without tools. Third-party views get no
sampling. Wait until a view needs it.

## 13. Standing views *(next)*

A saved call (server, tool, arguments, principal) can be pinned in the
Keel UI and opens without a prompt, the way Claude's entry points open
an app from the Artifacts page. A trigger's output (for example
`weekly-revenue.trigger.json`) becomes a pinned dashboard that remounts
the latest run's view. Tools used this way must accept `{}` and show a
useful default.

## 14. The same servers in other hosts *(discuss)*

Because these are standard views, Keel's first-party servers render in
Claude, ChatGPT, VS Code, Microsoft 365 Copilot and Cursor if exposed as
a remote MCP endpoint (Streamable HTTP, OAuth). The cost is a public
endpoint, invoker delegation minted from the host's OAuth identity
instead of a Keel session, and rows leaving through a third-party host
(cap previews; governance per deployment). Host variance applies: VS
Code is inline only. Worth doing only if users live in those hosts.

## 15. Not now

- **WebMCP**: no browser ships it; `registerTool` covers Keel's views.
- **Sampling or app-tool auto-approval for third-party views.**
- **View-to-view communication**: not in the spec; a dashboard of views
  can be one view.
- **A2UI or AG-UI**: MCP Apps covers server-owned views, and the hosts
  that matter speak it.

## Questions for the discussion

1. What is the Keel UI today, and which parts of it should render views
   (chat, run pages, a dashboard area)?
2. Is the first slice B1–B6 with the Lens answer and chart views right,
   and B7 (the agent driving a view) next?
3. Should first-party views get more trust (no approval for read-only
   app tools, `ui/message` as a real user turn on click)?
4. Do Lens users also need Claude, ChatGPT or Copilot (B14), or is the
   Keel UI enough?
5. May rows reach third-party hosts at all, and with what cap?
