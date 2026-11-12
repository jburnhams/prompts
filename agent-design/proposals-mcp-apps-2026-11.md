# Proposals from the MCP Apps deep dive (2026-11-12)

**Status: proposals only, none adopted.** Jonathan asked to discuss
before anything changes, so no other file under `agent-design/` is
edited. The research is in [`../mcp-apps/`](../mcp-apps) and the new
feature document
[`../agent-interactive-views.md`](../agent-interactive-views.md).

## Where Forge, Keel and Lens stand today

- **Keel speaks MCP `2026-07-28` through its own client** (decision row
  "MCP revision", 2026-11-11), so the ADK-Java limits that shaped
  `artifacts.md` §8 ("one text block, no `structuredContent`, never rely
  on anything but block zero") and `generative.md` §5a (the split
  "blocked on a version ceiling") no longer bind Keel. Both rules are
  still written as if they did.
- **Keel is headless.** Results leave through sinks (`keel/outputs.md`
  §7b), rendered as Markdown per channel. Nothing in Keel renders HTML,
  and nothing in Keel is exposed to other hosts as an MCP server.
- **Lens already has the right data shapes.** `table://` refs, a `table`
  artifact kind, and charts as `*.vl.json` Vega-Lite specs that cite a
  `table://` ref and are "rendered by the destination" (`data.md` §2a,
  §2b, §2e). What it lacks is a destination that renders them.
- **Tools and the harness may both mint artifacts** (confirmed
  2026-11-11), so storing a view's payload is not a new mint path.

MCP Apps touches Keel in two directions. **As a consumer**, Keel's MCP
client meets servers that offer views and app-only tools, and has to
decide what the model sees and what it declares. **As a producer**,
Lens could be an MCP server whose answers render as views in Claude,
ChatGPT, Microsoft 365 Copilot, VS Code and Cursor. The first is
needed whatever is decided about the second.

## Summary

| # | Proposal | Direction | Would amend | Recommendation |
|---|---|---|---|---|
| 1 | Allow the `content` / `structuredContent` split in Keel's client; `structuredContent` is minted as an artifact, never put in context | consumer | `artifacts.md` §8; `generative.md` §5a; `data.md` §2d | Adopt now |
| 2 | Honour `visibility`: app-only tools are never grantable to a model; `_meta.ui` is part of the snapshot digest | consumer | `keel/tools-and-agents.md` §4a, §4b; `tools.md` | Adopt now |
| 3 | Declare `io.modelcontextprotocol/ui` per run, only when the run's result has a renderer | consumer | `keel/tools-and-agents.md` §4a; `keel/run-spec.md` | Adopt with 4 |
| 4 | Record a view as a run artifact, with its template pinned by digest | consumer and producer | `artifacts.md` §5.1; `keel/outputs.md` §7a, §7b; `run.schema.json` | Adopt with 3 |
| 5 | **Expose Lens as a remote MCP server whose answers are views** | producer | new `lens-on-keel/mcp-server.md`; `keel/api.md`; `keel/authority.md` §8 | **Discuss** |
| 6 | One chart view, `ui://keel/vega`, for any `*.vl.json` citing `table://` | producer | `data.md` §2e | Adopt if 5 is |
| 7 | Rules for traffic a view starts: authority, metering, provenance, audit | both | `keel/authority.md`; `keel/triggers-and-runs.md` §10; `agent-content-provenance` rules in `formats.md` | Adopt if 5 is |
| 8 | Not now: Keel as a rendering host, app-provided tools, sampling from views | — | `future.md` | Record |

---

## 1. Allow the split, and store `structuredContent` as an artifact

**What.** Lift `artifacts.md` §8's "one text block, no
`structuredContent`" rule for Keel's MCP client. The rule for a call
result becomes:

- the model sees the projection of `content` that `formats.md` already
  defines (text blocks, refs as text);
- a `structuredContent` payload is **minted as an artifact** by the
  harness (`table://` when it is tabular, `artifact://` otherwise) and
  the result's stub cites it;
- `structuredContent` is **never appended to the model's context**,
  including when `content` is empty. An empty `content` gets a stub
  that names the artifact and its size.

**Why.** It is what `generative.md` §5a and
`agent-tool-result-transport.md` called "the field's cleanest answer",
and the blocker that kept it in `future.md` is gone. The deep dive adds
two reasons. Hosts disagree on whether `structuredContent` reaches the
model (Claude, for app tools: only when there is no text; Open WebUI: appended whenever
it differs; `mcp-apps/catalogue.md` §1d), so Keel should pick a rule
rather than inherit one. And data servers built for MCP Apps put rows
in `structuredContent` (Paddle, Rill, `cohort-heatmap`), so Lens will
meet them as a consumer.

**Cost.** A change to the client's result handling and to
`artifacts.md` §8's wording. `data.md` §2d's spill already does the
same thing for tabular text, so the stub grammar exists.

## 2. Honour `visibility`, and pin `_meta.ui` in the snapshot

**What.**

- At `:discover`, a tool whose `_meta.ui.visibility` lacks `"model"` is
  recorded as `app_only` in the snapshot. A `ToolRef` naming it is
  refused at publish (a new rule, alongside R4 and R8), so it can never
  be in an agent's grant, loaded, deferred or revealed.
- `_meta.ui.resourceUri` and `_meta.ui.visibility` join the per-tool
  digest. A change is `tools_drift` like a changed annotation: a tool
  that becomes app-only, or gains a view, has changed what it is.
- `_meta` is never shown to the model (it already isn't; this makes it
  explicit).

**Why.** The spec makes the first point a MUST for any host, and Codex
and the Vercel AI SDK both do it in the catalogue before the model
sees anything. App-only tools exist to be called by a view (Rill's
`chart_data`, ext-apps' `read_data_bytes`); a model that can see them
gets tool-schema tokens for nothing and a tool whose arguments were
never meant for it. This is needed even if nothing else here is
adopted, because servers Lens already uses may start shipping them.

**Cost.** Small: a filter, a rule and two digest fields.

## 3. Declare the UI extension per run, only when someone can render

**What.** Keel's client sends
`io.modelcontextprotocol/ui: {mimeTypes: ["text/html;profile=mcp-app"]}`
in a request's client capabilities **only when the run's result will
reach a renderer** (proposal 5's MCP endpoint, or a future console),
recorded on the run as `views: enabled`. Jira, PR and Slack-origin runs
never declare it. The snapshot is discovered both ways for servers
whose `server/discover` lists the extension, and a run pins the one
matching its declaration.

**Why.** This is Codex's pass-through rule (`mcp-apps/catalogue.md`
§1c), and under `2026-07-28` it is free: capabilities travel per
request, so one deployment can serve headless and interactive runs
from the same servers. Declaring it everywhere would tell servers to
return view-shaped results to runs that cannot show them; the spec's
fallback rules say they should still be useful, but a server that
checks the capability (as the SDK's `getUiCapability` encourages) will
give a headless run its best text instead.

**Open point.** Whether two snapshots per server is worth it, or
whether `views` should be a property of a template version instead of a
run. A template-level flag is simpler and loses nothing for Lens, whose
entrypoints are fixed per trigger.

## 4. A view is a run artifact, with its template pinned

**What.** When a called tool carries `_meta.ui.resourceUri` and the run
declared the extension, the harness records a **`view` artifact**:

```jsonc
{ "kind": "view",
  "server": "mcp:warehouse", "tool": "chart_metric", "call_id": "…",
  "resource_uri": "ui://warehouse/chart",
  "resource_digest": "sha256:…",      // the HTML fetched at :discover
  "display_mode": "inline",
  "arguments": { … },
  "result": { "content": […], "structured": "table://tbl_…" } }
```

`Run.outcome`'s artifact list carries it, so sinks and continuations
can address it. The `ui://` HTML is fetched once at `:discover` and
pinned by digest like a tool description, which is the spec's
"predeclared resource review" (hash and allow-list templates) done the
Keel way.

**Why.** It is Codex's "presentation captured from the invoked
descriptor": a renderer that reads the run later (proposal 5's host, a
console, a review UI) can mount the view exactly as it was. And pinning
the template means a server cannot change the code that runs next to a
user's conversation without a snapshot change.

## 5. Lens as a remote MCP server whose answers are views *(discuss)*

**What.** Keel serves a remote MCP endpoint (Streamable HTTP, OAuth) per
deployment, exposing a pipeline entrypoint as a tool. For Lens:

| Tool | Visibility | What it does |
|---|---|---|
| `lens_ask` | model, app | Starts the `lens` pipeline as the invoking user. Returns `content`: the answer's Markdown with its claims (what `answer.v1` already produces). `structuredContent`: claims with their refs, chart specs, and small table previews. `_meta.ui.resourceUri: ui://lens/answer`. If the run hands off to `lens.investigate`, it returns a task handle (`2026-07-28` tasks extension) and the view polls. |
| `lens_table_page` | **app** | A page of a `table://` ref the answer cites, read-only, under the same delegation. |
| `lens_requery` | **app** | Re-run a chart's query with a different grain, filter or top-N; read-only; metered (proposal 7). |
| `lens_run_status` | **app** | Progress of a long investigate stage, for the view to show. |

The view `ui://lens/answer` shows the answer, renders charts (proposal
6), lets the user open any figure to see the query and table behind it,
and reports what the user is looking at with
`ui/update-model-context`, so the host model's next turn can ask about
it. Text-only hosts (Claude Code, terminals, Slack via a Keel sink) get
the Markdown and a link.

**Why.** It puts Lens's answers, with live charts and provenance, into
every major chat host without building a UI per surface. It is the
shape the best data apps converged on (Rill, Hex;
`mcp-apps/data-analysis.md` §1–3): the model writes a spec and a
binding, the server queries, the view re-queries through app-only
tools. And it matches what Lens already has: claims citing refs,
`table://`, and Vega-Lite specs waiting for a destination.

**What it costs, and the questions to settle first.**

1. **Is a chat host the surface?** Today Lens answers through Keel's
   chat trigger and sinks. If its users live in Slack or Teams, this
   buys little (Teams users reach it through Microsoft 365 Copilot, but
   only in declarative agents). If they live in Claude, ChatGPT or
   Copilot, it is the main way to reach them.
2. **Keel becomes an MCP server.** That is a new public endpoint with
   OAuth, and the invoker delegation (`authority.md` §8) has to be
   minted from the host's OAuth identity instead of a chat session.
   Claude's app tools and entry points require a remote server anyway.
3. **Data leaves through the host.** Rows in `structuredContent` go to
   Anthropic, OpenAI or Microsoft, and may reach their model (proposal
   1's finding). Previews should be capped and pages fetched through
   `lens_table_page`; whether any rows may go at all is a governance
   decision per deployment.
4. **The long-run mismatch.** A view can be torn down at any time, but
   `lens.investigate` takes minutes. The task handle (and Claude's
   "start the work and return immediately, register a second tool that
   reports the outcome") covers it.
5. **Host variance.** VS Code is inline only; Claude can pin the view
   as an entry point. The view must work at both ends.

## 6. One chart view for every Vega-Lite spec

**What.** A single template, `ui://keel/vega`, renders any `*.vl.json`
that `data.md` §2e's validating write path accepted. The spec arrives
in `structuredContent` with its `table://` data inlined up to a cap;
above the cap the view fetches pages through `lens_table_page`. The
view bundles Vega-Lite, so its CSP declares no external domains.

**Why.** `data.md` §2e chose a declarative spec "rendered by the
destination", with a PNG as the step down when the destination can't.
An MCP Apps host is the destination that can. One generic renderer
avoids the per-chart-type tools that cost Lloyd Richards ~8.2k tokens
of schemas, and the `unknown_field` and `no_data_ref` refusals already
guarantee the spec cites real columns rather than embedding rows.

## 7. Rules for what a view starts

If proposal 5 goes ahead, Keel is the server behind views it does not
control. The rules, from `agent-interactive-views.md` §2:

- **Authority.** Every call from a view runs as the run's principal
  under the run's delegation, never wider. App-only tools must be
  read-only (`readOnlyHint: true`) unless a template says otherwise and
  names an approval.
- **Metering.** View calls count against the run's budget and a
  per-view rate limit, and are recorded as `view_call` run events. This
  is Rill's reviewer's objection, answered before it is asked.
- **Provenance.** Nothing a view sends is the user speaking. If Keel
  ever hosts views (proposal 8), `ui/message` needs the user's
  agreement and `ui/update-model-context` is framed as untrusted
  server-authored data, as `formats.md` frames tool results.
- **Audit.** A view's calls are in the run record. The DeepSeek Harness
  plugin's bridge calls "never reach the session JSONL"; that is the
  failure to avoid.
- **Binding.** A view's callback is bound to the run and tool that
  opened it (Open WebUI's HMAC over server and tool is one way), so a
  view from one answer cannot page another answer's tables.

## 8. Not now, with the reason

- **Keel as a rendering host** (a run console using `AppBridge` or
  `@mcp-ui/client`). Useful for reviewing runs, but Keel has no UI and
  Lens's users would see the views in their own host. Record in
  `future.md` with the trigger "Keel gains a run console".
- **App-provided tools** (the model calling the view). They exist only
  while an iframe is loaded, so a hands-off run cannot rely on them, and
  Claude ships them to a limited set of organisations.
- **Sampling from a view** (`sampling/createMessage`, draft). It would
  let server-written code spend Keel's model budget. Sampling is
  deprecated in `2026-07-28`, and nothing in Keel's design offers it to
  servers, so a view should not get it either.
- **A2UI or AG-UI.** Neither is in the hosts Lens would target, and
  MCP Apps already covers the server-owns-the-view case.

## Questions for the discussion

1. Where do Lens's users ask data questions now, and where should they
   in a year: Slack or Teams through Keel, or Claude, ChatGPT,
   Microsoft 365 Copilot or VS Code?
2. Is a public, OAuth-protected Keel MCP endpoint acceptable?
3. May rows leave through a third-party host at all, and if so, what
   cap on previews?
4. Should proposals 1 and 2 go ahead now on their own? They are needed
   as a consumer whatever happens to 5.
5. Should Forge's coding and review use cases get views? This document
   assumes not: their surfaces are GitHub and Jira, which render
   neither.
