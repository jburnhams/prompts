# WebMCP — `navigator.modelContext`

> **Status: PARKED. Not useful to this project today. Do not spend time
> here unless one of the re-check triggers below fires.**
>
> Assessed 2026-09-20. Kept as a placeholder so the question does not get
> re-opened from scratch.

## What it is, in three sentences

A browser API that lets a **web page register tools with the browser's
agent**, so an agent can call into whatever the page can do. The tool
object is MCP-shaped — `name`, `description`, `inputSchema`, `execute` —
and registration is scoped to an `AbortSignal`, so tools appear and
disappear with the UI that owns them.

```ts
navigator.modelContext.registerTool(
  {
    name: "scroll_to_section",
    description: "Scroll the page to a named section",
    inputSchema: { type: "object", properties: { id: { type: "string" } }, required: ["id"] },
    async execute({ id }) {
      document.getElementById(String(id))?.scrollIntoView({ behavior: "smooth" });
      return "ok";
    }
  },
  { signal: controller.signal }
);
```

W3C **Community Group** work, with Google, Microsoft, Mozilla and Apple
participating. Shipped in Chrome 146 Canary behind a flag (2026-02-10);
Chrome 149 origin trial (May 2026); stable rollout expected Q4 2026. The
March 2026 revision removed `provideContext()`/`clearContext()`, leaving
`registerTool()`/`unregisterTool()` as the only way to declare tools.

## Why it is not useful to us

**1. It solves a problem we do not have.** WebMCP's actual value is
letting a page *you do not control* offer tools to an agent — a browsing
story. Our agent runs its own loop in the page and already has a
TypeScript MCP client against a real MCP server. For tools that live in
our own page, the agent can simply **call the functions**. WebMCP would
add a browser-mediated indirection between our code and our code.

**2. It is one vendor's preview wearing a standards badge.** A Community
Group report is not a W3C Recommendation, and participation is not
implementation. Chromium behind a flag is the only shipping engine.

**3. The tooling authors say not to.** Cloudflare's adapter
(`packages/agents/src/experimental/webmcp.ts`, read at `c076e4c`) opens
with:

```
 * !! WARNING: EXPERIMENTAL — DO NOT USE IN PRODUCTION                  !!
 * !! This API is under active development and WILL break between       !!
 * !! releases. Google's WebMCP API (navigator.modelContext) is still   !!
 * !! in early preview and subject to change.                           !!
 * !! If you use this, pin your agents version and expect to rewrite    !!
 * !! your code when upgrading.                                         !!
```

**4. "The page can register tools" is also the threat model.** A tool
surface assembled from whatever the current page declares is one an
untrusted page can influence — names, descriptions and schemas all
become attacker-controlled text reaching the model. Bounded for a
first-party internal app by who can publish to the origin; not bounded
for an agent that browses. Adopting it would pull
`../agent-context-file-loading.md`'s untrusted-input handling into a
place it currently does not need to reach.

## The one thing worth borrowing now

**`AbortSignal`-scoped registration.** Tying a tool's lifetime to a
controller — so the tool surface is a function of what is currently on
screen, and a component unregisters on unmount without a separate
teardown path — is a good pattern and needs **none** of this API. It
works against a plain in-page tool registry today.

## Re-check triggers

Revisit only if one of these is true:

- **We need an agent to drive third-party pages.** This is the one that
  actually changes the answer — at that point WebMCP is the difference
  between scraping a DOM and calling a declared tool.
- **It reaches Baseline / cross-browser stable** — two independent
  engines shipping unflagged, and a Recommendation rather than a CG
  report.
- **A first-party surface we do not control starts offering tools** and
  we want to consume them.

Until then: the TS MCP client against a real server is the right shape,
and in-page tools are ordinary function calls.

## Where the detail lives

Read from source in `cloudflare/agents` @ `c076e4c` —
`packages/agents/src/experimental/webmcp.ts` and `examples/webmcp/`,
`examples/webmcp-react/`. Status facts above are from secondary sources
as of 2026-09-20 and will age; the API shape is from the adapter and
example.

Related, and *not* parked: [`cloudflare.md`](./cloudflare.md) (the Code
Mode browser executor, which is directly useful) and
[`../cloudflare-agents/`](../cloudflare-agents).
