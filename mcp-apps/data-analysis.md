# MCP Apps for data analysis

*What the data-facing apps in [`catalogue.md`](./catalogue.md) §3a
actually do, and the design rules they imply. Compiled 2026-11-12.*

The MCP Apps overview names "exploring complex data" first among its
use cases ("show me sales by region … an interactive map where users
click regions to drill down"), and two of Claude's nine launch partners
(Hex, Amplitude) are analytics products. Ten months in, the data apps
fall into three shapes, and only one of them keeps rows out of the
model.

## 1. Three shapes

| Shape | The model sends | The server returns | Rows in the model's context? | Examples |
|---|---|---|---|---|
| **A. Model draws** | the rows themselves, as tool arguments, plus chart options | an echo for the view | **yes, twice** (written as arguments, then in history) | MCP Dashboards, Lloyd Richards' render tools, ChartBrick |
| **B. Server queries, view renders** | a question, or a query and a chart spec | a summary in `content`, rows in `structuredContent` | no, if the host honours the split (see `catalogue.md` §1d) | Paddle, `cohort-heatmap`, Amplitude |
| **C. Spec plus binding, view re-queries** | a chart spec and a **binding to a semantic layer** (metric, range, filter, grain) | rows, field metadata, theme; later re-queries go through an **app-only tool** | no, and the view's interactions don't cost model turns | Rill, AWS AgentCore demo, `system-monitor` |

Shape A is the cheapest to build and the worst for data analysis: it
puts every row into context, it lets the model invent or round numbers
on the way into the chart, and the chart has no provenance. It is the
same "rows through the model" failure that
[`../agent-generative-output.md`](../agent-generative-output.md) §4
catalogues for artifact generation.

Shape C is what an analytics vendor with a semantic layer builds, and
it is the one that matches what this collection already recommends for
data agents (`../agent-design/data.md` §2e: "a declarative spec citing a
`table://` ref, rendered by the destination").

## 2. Rill, read closely

Rill's PR #10016 (merged 2026-11-07) is the most complete data app
found, and the review thread is as useful as the code.

- **The model writes a spec and a binding, never rows.** The Flint
  `chart_spec` says what to draw; the `data` binding names a metrics
  view, time range, filter and grain. The server runs the query.
- **The view owns cheap interactions.** Grain, top-N and comparison
  changes go through `chart_data`, an app-only tool. The model is not
  asked, and its tool list does not grow.
- **The view tells the model what the user is looking at.**
  `ui/update-model-context` sends the current view state, so "why did
  March dip?" in the next turn refers to what is on screen.
- **Text-only hosts still get an answer**: a Markdown table and an
  "Open in Rill" link that replays the call into the product.
- **A skill travels with the server.** An always-apply `rill-charts`
  skill arrives in a tool's instructions to guide chart choice.
- **The reviewer's three objections** were one tool name with two
  schemas, feature gating spread over several flags, and **unmetered
  query cost from `chart_data`**, since a view can call it in a loop
  without the model or the user seeing a call. The fix was to count
  `chart_data` in the `tool_call` metric. "Throttling is an MCP-wide
  question" was left open.

## 3. Hex: an agent behind the view

Hex's connector shows the other end of the spectrum. The view shows **a
different agent's reasoning** (Hex's thinking steps), then a carousel of
its charts and tables with citations, and can continue a Hex Thread.
Claude, the host model, sees a text summary. Two agents, one view, and
the view is the only place the user sees the inner one's evidence.

That is directly analogous to a Keel run handing results back to a chat
host, and it is the pattern [`../agent-interactive-views.md`](../agent-interactive-views.md)
§5 calls *a run behind a view*.

## 4. What breaks

- **Rows leak through `content`.** The official
  `customer-segmentation` example returns
  `content: [{type: "text", text: JSON.stringify(data)}]` beside the
  same `structuredContent`, so on most hosts the whole dataset reaches
  the model. `cohort-heatmap` does it right with a formatted summary.
- **`structuredContent` is not reliably private.** Open WebUI appends it
  to the model's context as JSON when it differs from the text.
- **Schemas cost context.** One render tool per chart type cost Lloyd
  Richards about 8.2k tokens of tool definitions. A single tool taking a
  grammar-level spec (Vega-Lite, Flint) avoids it.
- **Bundle size.** About 1 MB per React widget. The template is cached
  by URI, so this is paid once per host per version, not per call.
- **Many live copies.** Every call mounts a new iframe, and each can
  keep pushing `update-model-context`. Claude's documented fix is a
  server-minted `{createdAt, seq}` key in `structuredContent` and a
  `BroadcastChannel` election, so only the newest view of one dashboard
  stays live. Client mount time is the wrong key, because a reopened
  conversation lazy-mounts old views after new ones.
- **State is lost on remount.** "When a view loads again, it starts
  from your HTML, so store on your server anything that you need to
  keep." The ext-apps pattern is `localStorage` keyed by a server-minted
  `viewUUID` in `_meta`.
- **Unmetered views.** App-only tools are invisible to the model and,
  in Claude, show the user no approval. Query cost and rate limits are
  the server's problem.
- **Host variance.** Paddle's changelog says support "varies between AI
  agents, and between products from the same provider". VS Code renders
  inline only, so a dashboard designed for fullscreen is cramped there.

## 5. Design rules a data app should follow

Drawn from the sources above; each is cheap and each prevents a failure
seen in §4.

1. **`content` is a summary a person could act on** (the headline
   figure, the range, the row count, what was filtered), never the rows.
2. **Rows go in `structuredContent` only up to a size you are content
   for the model to see**, and anything larger is paged through an
   app-only tool.
3. **The model writes a spec and a binding, not data.** Validate the
   spec against the columns the binding returns before rendering.
4. **Interactive changes go through app-only, read-only tools**, metered
   and rate-limited on the server, with the same authorisation as the
   call that opened the view.
5. **Report view state with `ui/update-model-context`**, in a compact
   front-matter-plus-prose form (the ext-apps pattern), and only from
   the newest instance.
6. **Give every view a text fallback and a link out** to where the full
   analysis lives.
7. **Mint ordering and identity keys on the server** and put them in the
   result, because the transcript is the only thing every device and
   every remount agrees on.
8. **Declare the narrowest CSP**; bundle chart libraries rather than
   loading them from a CDN, so the view needs no `resourceDomains`.
