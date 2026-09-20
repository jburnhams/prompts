# WebMCP — `navigator.modelContext`

- **Type**: browser API for a **page** to register tools with an agent ·
  **Vendor**: W3C Community Group (Google, Microsoft, Mozilla, Apple
  participating)
- **Status at time of reading (2026-09-20)**: shipped in Chrome 146
  Canary behind a flag (2026-02-10); Chrome 149 origin trial (May 2026);
  stable rollout expected Q4 2026. **Early preview, not a cross-browser
  standard.**
- **Source read**: `cloudflare/agents` @ `c076e4c` —
  `packages/agents/src/experimental/webmcp.ts`, `examples/webmcp/`

Not Code Mode, but the other half of the same question. Code Mode asks
*how does the model invoke a capability*; WebMCP asks *where do the
capabilities come from when there is no server*.

## The API

From `examples/webmcp/src/client.tsx`:

```tsx
function registerInPageTools(
  tools: InPageToolDef[]
): { name: string; controller: AbortController }[] {
  if (!navigator.modelContext) return [];
  const registered: { name: string; controller: AbortController }[] = [];
  for (const tool of tools) {
    const controller = new AbortController();
    navigator.modelContext.registerTool(
      {
        name: tool.name,
        description: tool.description,
        ...(tool.inputSchema ? { inputSchema: tool.inputSchema } : {}),
        execute: async (input) => tool.execute(input)
      },
      { signal: controller.signal }
    );
    registered.push({ name: tool.name, controller });
  }
  return registered;
}
```

And a worked in-page tool from the adapter's own docstring:

```ts
navigator.modelContext?.registerTool({
  name: "scroll_to_section",
  description: "Scroll the page to a named section",
  inputSchema: {
    type: "object",
    properties: { id: { type: "string" } },
    required: ["id"]
  },
  async execute({ id }) {
    document.getElementById(String(id))?.scrollIntoView({ behavior: "smooth" });
    return "ok";
  }
});
```

Three design points:

**The tool shape is MCP's.** `name`, `description`, `inputSchema` (JSON
Schema), `execute`. A page tool and a server tool are the same object;
only the transport differs — which is the property that makes "one tool
definition, two deployments" plausible in the first place.

**Registration is `AbortSignal`-scoped.** `{ signal: controller.signal }`
ties a tool's lifetime to a controller, so a React component can register
on mount and unregister on unmount without a separate teardown API. The
tool surface becomes a function of what is currently on screen.

**`execute` is an ordinary in-page closure.** It has the DOM, the
session, the user's sign-in. That is the capability a server-side MCP
tool cannot have, and also the reason the security model is contentious.

Per the March 2026 spec revision, `provideContext()` and `clearContext()`
were removed; `registerTool()` / `unregisterTool()` are the only way to
declare tools.

## The adapter, and its warning

`packages/agents/src/experimental/webmcp.ts` opens with the loudest
comment in anything read for this collection:

```
 * !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
 * !! WARNING: EXPERIMENTAL — DO NOT USE IN PRODUCTION                  !!
 * !!                                                                   !!
 * !! This API is under active development and WILL break between       !!
 * !! releases. Google's WebMCP API (navigator.modelContext) is still   !!
 * !! in early preview and subject to change.                           !!
 * !!                                                                   !!
 * !! If you use this, pin your agents version and expect to rewrite    !!
 * !! your code when upgrading.                                         !!
 * !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
```

> WebMCP adapter for Cloudflare Agents SDK.
>
> Bridges tools registered on an McpAgent server to Chrome's native
> navigator.modelContext API, so browser-native agents can discover
> and call them without extra infrastructure.

```ts
const handle = await registerWebMcp({ url: "/mcp" });
// Later, to clean up:
await handle.dispose();
```

The recommended pattern in the docstring is a **mix**: bridge the remote
MCP server's tools into the page, then register page-local tools
alongside them, so the agent sees one surface.

> @example Mix in-page tools with bridged tools (recommended pattern)
>
> 1. Register page-local tools — things only the page can do

## What it changes, and what to be careful about

For a browser-resident agent this removes the last piece of required
infrastructure: the page can hand the agent its own capabilities
directly, and a remote MCP server's tools can be bridged in next to
them without the agent knowing which is which.

Two cautions worth writing down before building on it.

**It is one vendor's preview with a standards label.** A W3C *Community
Group* report is not a W3C Recommendation, participation is not
implementation, and the only shipping engine is Chromium behind a flag.
The adapter's own authors pin their version and expect to rewrite. Any
design that depends on it needs a path that works without it — which,
for an agent that already has its own tool loop in the page, is simply
calling the functions directly.

**"The page can register tools" is also the threat model.** A tool
surface assembled from whatever the current page declares is a tool
surface an untrusted page can influence — tool names, descriptions and
schemas all become attacker-controlled text reaching the model.
`../agent-context-file-loading.md` treats exactly this class of input as
untrusted and the collection's nonce-wrapper pattern applies unchanged.
For a first-party internal application the risk is bounded by who can
publish to the origin; for an agent that browses, it is not.
