# Cloudflare `@cloudflare/codemode`

- **Type**: Code Mode implementation with two executors, one of them
  browser-native · **Vendor**: Cloudflare · **Licence**: MIT
- **Source**: https://github.com/cloudflare/agents — `main` @ `c076e4c`
  (2026-09-18), `packages/codemode/`, `examples/codemode-browser/`,
  `docs/agents/codemode.md`
- **Retrieved**: 2026-09-20
- **Also**: [blog.cloudflare.com/code-mode](https://blog.cloudflare.com/code-mode/),
  [code-mode-mcp](https://blog.cloudflare.com/code-mode-mcp/),
  [developers.cloudflare.com/agents/tools/codemode](https://developers.cloudflare.com/agents/tools/codemode/how-it-works/)

The most complete readable implementation of Code Mode, and the only one
in this collection that ships a **browser** executor alongside a
server one. `examples/codemode-browser/` is a working app where the
model's generated JavaScript runs in a sandboxed iframe in the user's
tab, with no server-side executor at all.

## The tool the model sees

One tool. From `packages/codemode/src/browser-tool.ts`:

```ts
const DEFAULT_DESCRIPTION = `Execute code to achieve a goal.

Available:
{{types}}

Write an async arrow function in JavaScript that returns the result.
Do NOT use TypeScript syntax — no type annotations, interfaces, or generics.
Do NOT define named functions then call them — just write the arrow function body directly.

Example: async () => { const r = await codemode.searchWeb({ query: "test" }); return r; }`;
```

```ts
return {
  name: "codemode",
  description,
  inputSchema: {
    type: "object",
    properties: {
      code: {
        type: "string",
        description: "JavaScript async arrow function to execute"
      }
    },
    required: ["code"]
  },
  outputSchema: {
    type: "object",
    properties: {
      result: { description: "The return value of the executed code" },
      logs: {
        type: "array",
        items: { type: "string" },
        description: "Console output captured during execution"
      }
    },
    required: ["result"]
  },
  execute: async ({ code }) =>
    runCode({ code, executor, providers: resolvedProviders })
};
```

Four things in that tiny prompt are load-bearing, and three of them are
prohibitions:

- **`{{types}}` is a substitution point**, filled with TypeScript
  declarations generated from each tool's JSON Schema. The catalogue is
  rendered as a type, not as a tool list.
- **"Do NOT use TypeScript syntax"** — because the sandbox runs the
  string through `new Function`, and a type annotation is a syntax error.
  The model is shown TypeScript declarations and told to write
  JavaScript, which is a genuinely confusing instruction and is stated
  bluntly because of it.
- **"Do NOT define named functions then call them"** — the runtime
  evaluates `return (<code>)` and immediately invokes the result, so the
  string must *be* an expression. A declaration returns `undefined`.
- **One worked example**, showing `await`, the provider namespace, and an
  explicit `return`.

The output schema separates `result` from `logs` — console output is
captured rather than leaked into the return value, so a chatty program
does not corrupt its own answer.

On the server path the catalogue is not even inlined; the docs give the
model discovery methods instead:

```ts
codemode.search(query: string): Promise<SearchOutput>;
codemode.describe(target: string): Promise<DescribeOutput>;
```

> This keeps the complete tool catalog out of the initial model context.

And the generated declaration shape:

```ts
type ListPullRequestsInput = {
	owner: string;
	repo: string;
	state?: "open" | "closed";
};

declare const github: {
	list_pull_requests(input: ListPullRequestsInput): Promise<ListPullRequestsOutput>;
};
```

## The browser executor, in full

`packages/codemode/src/iframe-executor.ts`:

```ts
/**
 * IframeSandboxExecutor — a browser-native Executor that runs LLM-generated
 * code in a sandboxed iframe using postMessage for tool dispatch.
 *
 * Zero dependencies — uses only browser APIs (iframe, postMessage, CSP).
 */
```

```ts
const DEFAULT_CSP =
  "default-src 'none'; script-src 'unsafe-inline' 'unsafe-eval';";
const DEFAULT_TIMEOUT = 30000;
```

```ts
function buildSrcdoc(csp: string): string {
  const runtimeScript = escapeInlineScript(createIframeSandboxRuntimeScript());
  const safeCsp = escapeHtmlAttribute(csp);

  return `<!DOCTYPE html>
<html>
<head>
<meta http-equiv="Content-Security-Policy" content="${safeCsp}">
</head>
<body>
<script>
${runtimeScript}
</script>
</body>
</html>`;
}
```

with

```ts
iframe.sandbox.add("allow-scripts");
```

**Five layers, each doing one job:**

| Layer | What it stops |
|---|---|
| `sandbox="allow-scripts"` with **no `allow-same-origin`** | opaque origin — no access to the host page's DOM, storage, cookies or same-origin fetches |
| `default-src 'none'` in an injected CSP `<meta>` | **all network egress** — `connect-src` inherits from `default-src`, so `fetch`, WebSocket, `sendBeacon` and image pings are dead |
| `script-src 'unsafe-inline' 'unsafe-eval'` | nothing — this is the deliberate hole that lets generated code run at all |
| `postMessage` + a per-execution **nonce**, checked on both sides | cross-talk between concurrent executions, and messages from anywhere but `parent` |
| 30 s timeout, iframe torn down after | a program that hangs on an await |

The CSP is delivered as a `<meta http-equiv>` inside `srcdoc` rather
than as a header, which is the only option for a `srcdoc` frame — and it
works because a CSP meta tag is honoured even if later script tries to
rewrite it.

Tool dispatch crosses the boundary as messages, and the providers are
injected as **function parameters** rather than globals:

```ts
const fn = new Function(...providerNames, "return (" + code + ")")(
  ...providerProxies
);
Promise.resolve(fn())
  .then((result: unknown) => {
    post({ type: "execution-result", nonce, result: { result, logs } });
  })
```

So `codemode` is a parameter name in the generated function's scope, not
a property of `globalThis`. A program cannot enumerate `globalThis` to
discover capabilities it was not handed — a small, cheap property that
falls out of the calling convention.

The inbound guard is two lines and both matter:

```ts
window.addEventListener("message", (event) => {
  if (event.source !== parent) return;
  …
  if (message.nonce !== activeNonce) return;
```

## What the vendor says it does not do

`docs/agents/codemode.md`, verbatim:

> - Code runs in **isolated Worker sandboxes** — each execution gets its own Worker instance
> - External network access (`fetch`, `connect`) is **blocked by default** at the runtime level
> - Tool calls are dispatched via Workers RPC, not network requests
> - Execution has a configurable **timeout** (default 60 seconds)
> - Console output is captured separately and does not leak to the host
> - Browser iframe execution runs in a sandboxed iframe with a restrictive CSP by
>   default. It uses nonce-scoped internal messages, but **its timeout cannot preempt
>   tight synchronous loops like `while (true) {}` because those block the browser
>   event loop.**

> ## Current limitations
>
> - **Tool approval (`needsApproval`) is not supported yet.** Tools with
>   `needsApproval: true` or a `needsApproval` function are excluded from codemode
>   instead of pausing execution for approval. Support for approval flows within
>   codemode is planned. For now, use approval-required tools through standard AI
>   SDK tool calling instead.
> - Requires Cloudflare Workers environment for `DynamicWorkerExecutor`
> - Limited to JavaScript execution
> - The `zod-to-ts` dependency bundles the TypeScript compiler, which increases Worker size
> - LLM code quality depends on prompt engineering and model capability

The `while (true) {}` caveat is the one to internalise for a browser
design. An iframe shares the host page's event loop unless the browser
has put it in its own process, so a synchronous infinite loop **hangs the
user's tab** and no timeout can reach it. The available mitigations are a
Worker *inside* the iframe (which moves the loop off the main thread and
makes `terminate()` effective) or accepting that an accidental `while`
costs the user a reload. Neither is in the box.

And the approval gap is the structural one. Excluding approval-gated
tools rather than pausing mid-program is the honest choice — but it means
**Code Mode and a human-in-the-loop are currently mutually exclusive**,
which is a real constraint for any design that treats approval as a tier
rather than a switch (`../agent-permissions-approval.md`).

One more line from the browser path, worth quoting because it is the kind
of thing usually left implicit:

> JSON Schema is used for prompt/type generation only and is not enforced
> at runtime.

The declarations the model reasons against are documentation. Nothing
validates the arguments a program actually passes.

## The argument, in the vendor's words

From [the blog](https://blog.cloudflare.com/code-mode/):

> LLMs have an enormous amount of real-world TypeScript in their training
> set, but only a small set of contrived examples of tool calls.

> Making an LLM perform tasks with tool calling is like putting
> Shakespeare through a month-long class in Mandarin and then asking him
> to write a play in it.

The efficiency half is the more checkable claim: in a tool-call chain
each intermediate result passes through the model purely to be forwarded
to the next call, and a program chains them locally instead. That is the
same observation `../agent-tool-result-transport.md` §7 records as "the
school that avoids the question by not putting results in context at
all", arrived at from the latency side.

## Why it matters for a data agent specifically

The server executor needs Cloudflare Workers. **The browser executor
needs nothing** — it is ~200 lines over `iframe`, `postMessage` and CSP,
with zero dependencies, and it is MIT. For a harness that already runs
an agent loop in TypeScript in the page, this is the whole sandbox
layer, and the tools it dispatches to can be ordinary in-page functions:

> **Client (`src/client.tsx`):**
>
> - `createBrowserCodeTool()` from `@cloudflare/codemode/browser`
> - `IframeSandboxExecutor` for sandboxed browser execution
> - `useAgentChat({ tools, onToolCall })` to execute the client-side codemode tool
> - browser-memory project/task tools and a `getPageInfo` browser-only tool

Note the last item. `getPageInfo` is a tool that **only exists in the
browser** — it reads the live page. That is the thing a server-side MCP
tool surface structurally cannot offer, and it is the argument for the
browser executor being more than a cost optimisation.
