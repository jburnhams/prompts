# Browser: Code Mode over raw CDP, and a base64 redactor

`docs/agents/browse-the-web.md`, `packages/agents/src/browser/` at
`c076e4c`. Marked experimental.

Two things here matter to this collection, and they are unrelated to each
other. The first is a genuinely different answer to "how does an agent
drive a browser". The second is a shipped fix for a bug
`../agent-vision-multimodal.md` documents at length.

## One tool, and it is not `click`

> Browser tools give your agents full access to the Chrome DevTools
> Protocol (CDP) through the code mode pattern. **Instead of a fixed set
> of browser actions (click, screenshot, navigate), the LLM writes code
> that runs CDP commands against a live browser session** — accessing all
> domains, commands, events, and types in the protocol.
>
> One durable tool is provided:
>
> - **`browser_execute`** — run sandboxed code against a live browser via
>   the `cdp` connector. Executions are recorded on a durable codemode
>   runtime (abort-and-replay), so a run can pause for approval and resume
>   **with its browser session intact**.

```javascript
async () => {
  const { targetId } = await cdp.send({
    method: "Target.createTarget",
    params: { url: "https://example.com" }
  });
  const { sessionId } = await cdp.attachToTarget({ targetId });
  const { root } = await cdp.send({ method: "DOM.getDocument", sessionId });
  const { outerHTML } = await cdp.send({
    method: "DOM.getOuterHTML",
    params: { nodeId: root.nodeId },
    sessionId
  });
  await cdp.send({ method: "Target.closeTarget", params: { targetId } });
  return outerHTML;
};
```

Every browser agent in `../agent-vision-multimodal.md` — Gemini CLI's
browser sub-agent, the leaked `claude-for-chrome` surface, Manus,
Windsurf — ships a **fixed verb set**: navigate, click, type, screenshot,
scroll, read. The verbs are chosen by the harness author, and anything
outside them is unreachable.

This ships **the protocol**, not a verb set. The consequences are the
Code Mode consequences, sharpened by CDP being unusually large:

- **The action space is the whole protocol.** Accessibility tree, network
  waterfall, performance traces, coverage, memory profiling, emulation —
  all reachable without the SDK author having anticipated them. The
  listed use cases include "network waterfalls, console errors,
  performance traces" and "Core Web Vitals, JavaScript profiling, memory
  analysis", none of which a click/type/screenshot surface can express.
- **Multi-step interactions cost one round trip.** Create target, attach,
  get document, extract, close — one `browser_execute`, not five tool
  calls with the DOM node id passing through the model each time.
- **Discovery is a call, not a catalogue.** CDP has hundreds of methods
  across dozens of domains; inlining that would be absurd.

> To discover protocol surface, the model calls **`cdp.spec()`** — the
> live, normalized CDP protocol description (domains with commands,
> events, and types) — or uses the runtime's built-in `codemode.search` /
> `codemode.describe`.

`cdp.spec()` is capability discovery against a **live** protocol, so the
model gets whatever Chrome it is actually attached to supports rather
than what was true when the SDK shipped. Same shape as
[`../data-agents/matlab-mcp/`](../data-agents/matlab-mcp)'s
`detect_matlab_toolboxes`, at much larger scale.

And the durable-runtime integration gives it something no other browser
agent here has: **a browser run can pause for approval and resume with
the session intact.** "Ask before you submit this form" is expressible,
because [the Code Mode runtime](../code-mode/cloudflare.md) re-runs the
code with prior CDP calls served from the log.

The costs are real and mostly unstated by the vendor. CDP is verbose and
stateful — `sessionId` threading, target lifecycle, and a failure mode
where a forgotten `Target.closeTarget` leaks a tab. A fixed verb set is
harder to use wrongly. And there is no accessibility-first affordance:
the model must know to ask for the AX tree rather than the DOM, where a
purpose-built browser tool can make that the default.

There is a `quick-actions.ts` alongside it, so the design is not purely
protocol-level — but the documented surface is the one tool.

## The base64 redactor

`packages/agents/src/browser/ai.ts`. This is the part to steal.

`../agent-vision-multimodal.md` records the **image-in-a-tool-result
bug**: Chat Completions cannot carry an image in a tool result, the
converter `JSON.stringify`s it, and the model "treats it as ~50KB of
opaque text and hallucinates the image's actual contents" — a failure
that never errors. A CDP surface makes this acute, because
`Page.captureScreenshot` returns base64 in an ordinary result object and
so do a dozen other methods.

Two mechanisms, and they work together.

**Screenshots are a typed output, routed to a real image block:**

```ts
interface BrowserScreenshotOutput {
  type: "browser_screenshot";
  mediaType: string;
  data: string;
}
```

**Everything else base64 is redacted with its size stated:**

```ts
const BASE64_REDACTION_THRESHOLD = 4096;
const MAX_REDACTION_DEPTH = 20;
const MAX_REDACTION_NODES = 10_000;
```

```ts
function base64Redaction(value: string, mediaType?: string, minimumLength?: number): string {
  const details = base64Details(value, minimumLength);
  if (!details) return value;
  const type = mediaType ?? details.mediaType;
  return `[base64${type ? ` ${type}` : ""} data omitted: ${details.chars.toLocaleString()} chars, approximately ${details.bytes.toLocaleString()} bytes]`;
}
```

So the model sees
`[base64 image/png data omitted: 1,234,568 chars, approximately 925,926 bytes]`
instead of a megabyte of opaque text.

Five details worth copying verbatim into any harness that returns
structured tool results:

**1. It verifies the string is actually base64 before redacting.**

```ts
const dataUrl = /^data:([^;,]+)(?:;[^;,]*)*;base64,([A-Za-z0-9+/]*={0,2})$/i.exec(value);
const encoded = dataUrl?.[2] ?? value;
if (encoded.length % 4 !== 0 || !/^[A-Za-z0-9+/]*={0,2}$/.test(encoded)) {
  return null;
}
```

Length divisible by four, charset check, padding parsed. A long minified
JS bundle or a hex blob is not redacted. Redacting by length alone would
eat legitimate content.

**2. The placeholder states the media type and the size, in both units.**
`chars` is what it would have cost in context; `bytes` is what the thing
actually is. A model deciding whether to ask for the bytes through
another channel can act on either. This is
`agent-tool-implementations.md` §6a's "every truncation states what it
showed and how much exists", applied to a redaction.

**3. The threshold is 4096 characters**, not zero — short base64 (an
icon, a nonce, a hash) passes through, because round-tripping it is
cheaper than the placeholder.

**4. The walk is bounded, with its own placeholders.**
`MAX_REDACTION_DEPTH = 20` → `[nested value omitted]`;
`MAX_REDACTION_NODES = 10_000` → `[remaining values omitted]`. A CDP
result can be a deep object graph, and a sanitiser that can be made to
hang on its own input is a denial of service in the safety layer.

**5. Binary types are skipped, with the reason in a comment:**

```ts
// Binary values cross the sandbox boundary as Uint8Array/ArrayBuffer —
// walking them would rebuild them as index-keyed plain objects. The same
// is true of Date/Map/Set, whose own enumerable entries are empty.
if (
  current instanceof ArrayBuffer ||
  ArrayBuffer.isView(current) ||
  current instanceof Date ||
  current instanceof Map ||
  current instanceof Set
) {
  return current;
}
```

A generic recursive sanitiser over a `Uint8Array` turns a 900 KB buffer
into `{"0":137,"1":80,"2":78,...}` — strictly worse than the base64 it was
trying to prevent. This is the kind of bug that ships, and the comment is
why it did not.

## Where this lands

`../agent-vision-multimodal.md` §3's finding is that harnesses handle
capability-gated degradation with placeholder strings that **differ in
whether the model can act on them**, and the rule it extracts is *strip
at request-build time, keep the real image in history, say what you did*.
This is the most complete implementation of that rule found since, and it
adds two things that section does not have: **verify before you redact**,
and **bound the traversal**.

It also sharpens a claim in that doc. The image-in-a-tool-result bug is
usually framed as a *client converter* problem. Here it is handled
**server-side, at the tool boundary**, by the SDK producing the result —
which is the only place that can tell a screenshot (route it) from an
incidental base64 blob (redact it). The client cannot make that
distinction, and neither can the model.
