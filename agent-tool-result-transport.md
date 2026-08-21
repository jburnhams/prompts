# Tool result transport

How a tool result gets from the process that produced it into the model's
context — and what to do when it shouldn't go there at all.

This sits one layer to the side of the rest of the tool docs in this
collection. [`agent-tool-call-dialects.md`](./agent-tool-call-dialects.md)
covers the wire format of a *call*;
[`agent-tool-implementations.md`](./agent-tool-implementations.md) covers
what a tool *does* and what shape its answer takes;
[`agent-tool-surfaces.md`](./agent-tool-surfaces.md) covers which tools
exist. None of them covers the step in between: a result crosses a process
boundary, gets re-encoded one or more times, and is *projected* into the
conversation by code that neither the tool author nor the model author
wrote. That step is where MCP lives, and it is where the two questions this
doc exists to answer come up:

1. **Escaping.** MCP is JSON-RPC. Tool payloads are frequently code, diffs,
   logs and other quote-and-newline-heavy text. Does the model end up
   reading `\"foo\\n\"`, and how much does that cost?
2. **Payloads that shouldn't be in context at all.** A 40 MB CSV, a PNG, a
   database dump. Is there an established way to keep the bytes out of the
   conversation, hand the model a reference it can act on, and separately
   mark something as *for the user*?

The short answers: **(1) is mostly a myth with two real exceptions, both of
them client-side and both measurable**, and **(2) is more solved than it
looks — the same handle-plus-stub pattern has been arrived at six times
over, once by the current MCP specification itself and once by the stack
[`agent-design/`](./agent-design) targets.**

Sources read for this doc, with commits, are in
[`sources.md`](./sources.md). Everything in §3 is from source code read on
2026-08-21; everything in §2 and §7 is from the specification and vendor
documentation; the numbers in §1 are measured here and carry a stated
tokenizer caveat.

---

## 1. Where JSON actually shows up, and which of it the model sees

The intuition that "MCP is JSON, therefore the model reads escaped JSON" is
wrong, but only because it collapses three different layers. They behave
completely differently and only two of them cost anything.

**Layer 1 — the transport.** `{"type":"text","text":"line1\nline2"}` on
stdio or Streamable HTTP. The client parses this before anything else
happens. `\n` becomes a newline in a JavaScript string; nothing is
tokenised. **This layer is free**, and it is the layer people worry about.

**Layer 2 — the provider's tool-result rendering.** After the client has a
result, it puts it into the next model request, and the provider's own
prompt assembly decides what that looks like as text. This is where the
first real cost is, and it is a property of the *provider*, not of MCP:

| Provider path | Tool result carrier | Escaping the model sees |
|---|---|---|
| Anthropic Messages API | `tool_result` content: a string, or text/image blocks | none — text survives byte-for-byte |
| Gemini / Vertex `FunctionResponse` | `response`: a Struct (a JSON object) | the payload is JSON-serialised into the prompt, so newlines, tabs and quotes in it are escaped |
| Harmony, Qwen3/Hermes, GLM and the other in-band dialects | a text span in a `tool`-role turn | none — the dialect writes raw text (see `agent-tool-call-dialects.md` §"three envelope roles") |

This collection already recorded the Gemini case from the other end:
[`agent-design/adk.md`](./agent-design/adk.md) §2c, which notes that it is
"only partly an MCP effect (Gemini's function-response part is structured
regardless — Anthropic's API, by contrast, takes a raw string tool
result)." That framing is right and is the general rule: **if escaping
reaches the model, look at the provider and the client, not at MCP.**

**Layer 3 — what the tool itself put inside the payload.** This is where
nearly all the damage is, and unlike the other two it is entirely
self-inflicted. Two shapes:

- a document (file body, diff, log) serialised *into* a JSON string field
  rather than carried as its own text block;
- a client that hands the model the whole result envelope
  (`JSON.stringify(result)`), so the model reads MCP's own schema — `type`
  tags, `isError`, base64 and all — as prose. §3 shows two shipping clients
  that do exactly this.

### 1a. What escaping costs, measured

Measured with `tiktoken` 0.14.0, encoding `o200k_base`, on real files from
this repository. **Caveat, and it is not a small one:** `o200k_base` is
OpenAI's tokenizer, not Claude's or Gemini's. The direction of every result
below is safe; the magnitudes are approximate, and anyone making a decision
on a 10% margin should re-run this on their own tokenizer. Re-deriving it
is cheap — the inputs are files in this repo and the whole method is:

```python
import json, base64, tiktoken
enc = tiktoken.get_encoding("o200k_base")          # swap for your tokenizer
t = lambda s: len(enc.encode(s))
src = open("agent-design/formats.md").read()[:20000]
numbered = "".join(f"{i+1}\t{l}\n" for i, l in enumerate(src.split("\n")))
for name, s in [("raw", src), ("numbered", numbered)]:
    print(name, t(s), t(json.dumps(s)), t(base64.b64encode(s.encode()).decode()))
```

| Payload | Raw | JSON-escaped as a string | Ratio |
|---|---|---|---|
| Markdown prose (`agent-design/formats.md`, first 20 KB) | 4,833 | 5,352 | **1.11×** |
| Lark grammar (`omp/hashline-grammar.lark`) | 248 | 287 | **1.16×** |
| Synthetic JSON records (50 rows, quotes + `\n` + `\t` in values) | 2,302 | 2,803 | **1.22×** |
| TypeScript with tabs, template literals and a regex full of backslashes | 1,512 | 1,838 | **1.22×** |
| …the same TypeScript, **double**-encoded | 1,512 | 2,235 | **1.48×** |
| …the same TypeScript, base64 | 1,512 | 3,904 | **2.58×** |
| Markdown prose, base64 | 4,833 | 17,456 | **3.61×** |

And, for comparison, the framing this collection's own design uses instead
of escaping — a `<decimal><TAB>` prefix on every content line
(`agent-design/formats.md` §8a):

| Transformation | Cost |
|---|---|
| Line-number prefixes on 20 KB of markdown | 4,833 → 5,455 (**1.13×**) |
| JSON-escaping *that* | 5,455 → 6,180 (**1.13× more**) |

Five things fall out of this table:

1. **Single-level escaping is a tax, not a catastrophe.** 11% on prose,
   22% on quote-heavy code. Real, worth avoiding, not worth restructuring a
   protocol over.
2. **The cost tracks the character mix, not the size.** Prose is cheap to
   escape; code with tabs, quotes and backslashes is twice as expensive.
   The payloads a coding agent handles are the expensive ones — which is
   why this reads as a bigger problem to agent authors than the average
   number suggests.
3. **Double-encoding is where it starts to hurt** (1.48×), and
   double-encoding is exactly the shape you get when an MCP server wraps an
   upstream JSON API: the API's JSON becomes a string inside the server's
   JSON. This is the single most common avoidable mistake in the wild.
4. **Base64 in a text block is the actual disaster** — 2.5–3.6×, on top of
   which the model cannot *do* anything with the bytes. §5.
5. **Line-number framing costs about the same as escaping** (1.13× vs
   1.11×) and buys properties escaping destroys: byte-exact match for
   `Edit`, citable line numbers, and unambiguous delimiting. This is the
   strongest quantitative support yet for the rule
   `agent-tool-implementations.md` §5b states qualitatively — *"Nobody
   escapes file content, and nobody should… line-number prefixes are the
   escaping mechanism."* You are not choosing between "escaped" and
   "free"; you are choosing between two ~1.1× framings, one of which
   breaks your edit tool.

### 1b. The escaping problem is worse on the argument side

Worth stating because it is the asymmetry most discussions miss. On the
*result* side the tool author controls the encoding and can choose text
blocks. On the *argument* side the model has to **emit** valid escaped
JSON, and a malformed escape is a failed call rather than a slightly
expensive one. That is the finding this collection already carries from
OMP's author (`agent-tool-implementations.md` §3g, `README.md`): a scalar
parameter is delimiter-matched and needs no escaping at all, while "an
array or object forces escaped JSON into the same slot", and nested or
heterogeneous schemas degrade reliability multiplicatively. Codex ships
`apply_patch` as a Lark-grammar freeform tool with *"do not wrap the patch
in JSON"* in its description for precisely this reason.

So the ordering of concerns is: **argument schemas first (correctness),
payload encoding second (cost), transport never.**

---

## 2. What MCP actually specifies

Worth stating precisely, because much of the folklore is about a version of
the protocol that no longer exists.

The **current revision is `2026-07-28`**. Any document in this collection
that reasons about MCP sessions, `initialize`, or `resources/subscribe` is
describing `2025-11-25` or earlier.

### 2a. The result model

A `tools/call` result carries three things:

- **`content`** — an **array** of blocks, in five types:

  | Type | Carries | Notes |
  |---|---|---|
  | `text` | `text: string` | the workhorse |
  | `image` | `data` (base64) + `mimeType` | |
  | `audio` | `data` (base64) + `mimeType` | |
  | `resource` (embedded) | a resource inline: `text` **or** `blob` (base64), plus `uri`/`mimeType` | |
  | `resource_link` | `uri`, `name`, `description`, `mimeType` — **and no payload** | the client fetches it later via `resources/read`; explicitly not guaranteed to appear in `resources/list` |

- **`structuredContent`** — since `2025-06-18`, a JSON value validated
  against the tool's optional `outputSchema`. As of `2026-07-28` it may be
  *any* JSON value, not just an object.
- **`isError`** — the model-visible error channel, distinct from JSON-RPC
  protocol errors. The spec is explicit that these are for different
  audiences: protocol errors are structural and the model probably can't
  fix them; `isError` results carry "actionable feedback that language
  models can use to self-correct". That is this collection's
  errors-are-instructions rule, in the spec.

Two channels most people don't use:

- **`annotations`** on *every* content type: `audience` (`["user"]`,
  `["assistant"]`, or both), `priority` (0–1), and `lastModified`. This is
  the protocol's own answer to "who is this block for" — including
  "return this to the user, not to the model". It is under-implemented, but
  it exists and it is free to emit.
- **`_meta`** — an open extension bag. In practice this has become the
  not-for-the-model channel: OpenAI's Apps SDK routes widget data through
  `_meta` specifically so it reaches the UI without entering model context
  (people pass API keys through it), and MCP Apps (§8) links a tool to its
  UI resource through it. Anthropic uses it for a client-specific cap
  annotation (§6). None of that is guaranteed by the core spec, and there
  are open reports of hosts dropping custom `_meta` — treat it as a
  convention with good adoption, not a contract.

### 2b. The `2026-07-28` rewrite, and why it matters here

The revision that landed this year is a large one, and three of its changes
bear directly on this doc:

- **Protocol-level sessions are gone**, along with `Mcp-Session-Id` and the
  `initialize` handshake. The replacement is stated as a design rule:
  *"Servers that need cross-call state use explicit, server-minted handles
  passed as ordinary tool arguments."* §7 is about what that means.
- **Long-running work moved out of core into the `io.modelcontextprotocol/tasks`
  extension**: a server returns a durable poll handle (`resultType: "task"`,
  a `taskId`, a TTL and a poll interval), the client polls `tasks/get`, and
  results are retrieved later. Call-now, fetch-later, with a handle in the
  middle.
- **Sampling, Roots and Logging are deprecated**, with a twelve-month
  window. If any design here was planning to lean on server-initiated
  sampling, stop.

Also landed: `icons`, deterministic `tools/list` ordering explicitly
justified by *prompt-cache hit rates*, `ttlMs`/`cacheScope` on list
results, and `x-mcp-header` for mirroring primitive tool parameters into
HTTP headers so intermediaries can route without parsing the body.

### 2c. The gap the spec leaves open, and it is the important one

**MCP specifies the *shape* of a result. It does not specify the
*projection* of that result into model context.** There is no normative
text saying whether `structuredContent` is shown to the model, what happens
to a `resource_link`, how five content blocks are concatenated, or what a
client does with an audio block a text-only model can't read.

That is not an oversight so much as a division of labour — the same one
`agent-tool-implementations.md` §1 describes for tools generally, where a
result has three consumers (model text / harness record / human rendering)
and the mapping between them is the harness's job. But it means every
client invents the projection, and §3 is what they invented.

---

## 3. Five projections, read from source

Read on 2026-08-21 unless noted. Paths and commits in `sources.md`.

### 3a. OpenCode — two projections, deliberately opposite

`packages/opencode/src/mcp/catalog.ts` and
`packages/opencode/src/tool/code-mode.ts` (`ba72a6f`).

The **model-facing** path (`convertTool`) hands the whole `CallToolResult`
to the tool runtime and synthesises text from `structuredContent` **only
when `content` is empty**:

```ts
if (result.content.length > 0 || result.structuredContent === undefined || result.structuredContent === null)
  return result
return { ...result, content: [{ type: "text" as const, text: JSON.stringify(result.structuredContent) }] }
```

The **program-facing** path — OpenCode ships a Code Mode tool, *"Run a
confined orchestration script with access to connected MCP tools"*, where
MCP tools are presented to a sandboxed program as a `server.tool` tree —
uses a function named, exactly, `projectMcpResult`, and its precedence is
**the reverse**: `structuredContent` wins outright if present, and text
blocks are the fallback.

That contrast is the finding. The same codebase deliberately picks
`content`-first for a model reading prose and `structuredContent`-first for
a program doing field access, which is precisely the split
[SEP-1624](https://github.com/modelcontextprotocol/modelcontextprotocol/issues/1624)
proposes to write into the spec (§4) — arrived at independently, and
implemented rather than argued.

`projectMcpResult` is also the best-designed binary handling read for this
doc. It takes a `collect(attachment)` callback, and routes by block type:

- `text` → appended to the text the program sees;
- `image` / `audio` → **out of the text path entirely**, into an
  `attachments` array on the tool result as a `data:` URL;
- embedded `resource` → `.text` if it has one, otherwise the `blob` becomes
  an attachment with a filename derived from the last path segment of the
  URI;
- `resource_link` → kept as text, with the reasoning in a comment worth
  quoting: *"A link is a reference, not fetchable media; hand it to the
  program instead of the attachment channel."*

And when a call returned only binary, the program gets a **stub, not the
bytes**: `` `[${files} ${noun}${files === 1 ? "" : "s"} attached to the result]` ``.
That is the whole §5/§7 pattern in one function — the program learns the
result's *shape*, the bytes travel a separate channel, and the user-facing
surface renders them.

### 3b. Roo Code — MCP-aware, and silently lossy

`src/core/tools/UseMcpToolTool.ts`, `processToolContent` (`b867ec9`).

```ts
if (item.type === "text")     return item.text
if (item.type === "resource") { const { blob: _, ...rest } = item.resource; return JSON.stringify(rest, null, 2) }
if (item.type === "image")    { /* pushed to an images[] array as a data: URL */ return "" }
return ""
```

Blocks joined with `\n\n`; `isError` prefixes `"Error:\n"`.

What that means in practice:

- **text blocks are passed through raw** — correct, and the reason this
  client doesn't have an escaping problem for its most common case;
- **an embedded resource is `JSON.stringify`d** — so a file's contents
  delivered as an embedded text resource arrives at the model *escaped*,
  while the identical bytes in a plain text block do not. One client, two
  encodings for the same payload, decided by which block type the server
  chose;
- **the `blob` field is destructured away** — binary in an embedded
  resource is dropped, and the model is told nothing;
- **`resource_link` and `audio` fall through to `return ""`** — dropped,
  silently;
- **`structuredContent` is never read** — dropped, silently.

The silence is the defect, not the dropping. Dropping a `resource_link` is
a defensible product decision; dropping it without a note puts this in the
same class as the failure `agent-tool-implementations.md` §5b flags in
Gemini CLI's `read_many_files` — *"The model can therefore ask for six
files, receive four, and not be told."* A tool result that omits part of
what the server sent should say so; a one-line note (`! 1 resource link
omitted: <uri>`) costs nothing and converts an invisible failure into a
recoverable one.

### 3c. Cline — the whole envelope, stringified

`sdk/packages/core/src/extensions/mcp/` (`fb60f9e`).

```ts
export type McpToolCallResult = unknown;
```

The SDK's MCP adapter (`tools.ts`) wraps each server tool with
`createTool({ … execute: () => provider.callTool(…) })` and returns the
`CallToolResult` **as the tool's output, untyped**. There is no MCP-aware
flattening at this layer at all. Downstream, in
`session/persisted-tool-result-content.ts`, a tool output becomes the
`content` of a `tool_result` message (`llms/messages.ts`: `content: string
| Array<TextContent | ImageContent | FileContent>`) by this rule:

```ts
if (typeof output === "string") return output;
if (Array.isArray(output))      return output as ToolResultContent["content"];
return JSON.stringify(output) as ToolResultContent["content"];
```

A `CallToolResult` is an object, not a string and not an array. So it takes
the third branch, and the model reads the envelope: `{"content":[{"type":
"text","text":"…escaped…"}],"structuredContent":{…},"isError":false}`.
That is layer-3 double-encoding (§1a: ~1.48× on code-shaped payloads) plus
the schema tax of the `type`/`isError` scaffolding, plus — if the server
followed the spec's backwards-compatibility SHOULD — the payload twice
(§4).

Two caveats, stated because the claim is unflattering. First, this is the
newer SDK path; Cline's older VS Code `use_mcp_tool` path had MCP-aware
handling, and which path a given install uses was not established here.
Second, the file is named for *persistence*; it is used by the agent
message codec whose output is the LLM message type, which is why it is
read as the model-facing path, but a targeted runtime check would settle it
better than reading will.

### 3d. Google ADK — two languages, two different projections

Already recorded in `sources.md` and analysed in `agent-design/adk.md` §2;
restated here because it is the sharpest available example of §2c's gap.

- **Java** (`AbstractMcpTool.wrapCallResult`): a *lossy flatten*. One text
  block becomes `{"text_output":[{"text": …}]}` — but only after ADK tries
  to parse the text as JSON and substitutes the parsed map if it succeeds.
  `isError` keeps **only block zero** and prefixes it with a fixed
  `"Tool execution failed. Details: "`. Any non-`TextContent` block —
  image, audio, embedded resource — becomes an **error**.
- **Python** (`mcp_tool.py`): `response.model_dump()` of the entire
  `CallToolResult`. The whole envelope, same as Cline.

Same protocol, same vendor, same release train, two incompatible
projections. If a design targets ADK, "what the model sees" is a function
of which language binding is deployed — and `agent-design/adk.md`'s
standing rule (one text block per result, no `structuredContent`, never
rely on anything but block zero surviving) is the correct defensive
posture against exactly this.

### 3e. Claude Code — the projection includes a spill

Documented rather than source-read (`code.claude.com/docs/en/mcp`, read
2026-08-21).

- warning at **10,000 tokens** of MCP tool output (threshold fixed);
- default cap **25,000 tokens**, raised with `MAX_MCP_OUTPUT_TOKENS`;
- per-tool opt-out: a server sets `_meta["anthropic/maxResultSizeChars"]`
  in its `tools/list` entry, which raises that tool's threshold up to a
  hard ceiling of **500,000 characters**, independently of the environment
  variable;
- image content is **exempt from the char annotation but not from the
  token cap** — the docs say so twice, which suggests it surprised people;
- and the sentence that matters most: without the annotation, *"results
  that exceed the default threshold are **persisted to disk and replaced
  with a file reference in the conversation**."*

That last is the artifact pattern (§7) already wired to MCP results in a
shipping client, and it generalises the same harness's internal
`maxResultSizeChars` spill that `agent-tool-implementations.md` §6a
records for built-in tools — including the carve-out that makes it work
(`Read` gets `maxResultSizeChars: Infinity`, because spilling a read
creates a circular `Read`→file→`Read` loop).

### 3f. The comparison

| | text blocks | embedded resource | binary | `resource_link` | `structuredContent` | oversized |
|---|---|---|---|---|---|---|
| **OpenCode** (model path) | raw | passed through | passed through | passed through | fallback only, when `content` empty | — |
| **OpenCode** (Code Mode) | raw, joined | `.text`, else attachment | **attachment channel** + stub | as text | **preferred** | — |
| **Roo Code** | raw, `\n\n` | `JSON.stringify`, blob stripped | image → image block; blob → **dropped silently** | **dropped silently** | **dropped silently** | — |
| **Cline** (SDK path) | inside `JSON.stringify(result)` | ditto | ditto, base64 as text | ditto | ditto | — |
| **ADK Java** | flattened; parsed as JSON if it parses | **error** | **error** | **error** | not forwarded | — |
| **ADK Python** | inside `model_dump()` | ditto | ditto, base64 as text | ditto | ditto | — |
| **Claude Code** | rendered | — | native image blocks | — | forwarded (see §5) | **spill to disk + file reference** |

Read down the columns rather than across the rows. **Three of the seven
projections put a JSON envelope in front of the model** — Cline's
`JSON.stringify` of the whole result, ADK Python's `model_dump()` of the
whole result, and ADK Java's `{"text_output": …}` wrapper — two drop
content without saying so, one errors on anything non-text, and exactly
one (OpenCode's Code Mode) routes binary out of the text path *and*
leaves a stub behind. A server author writing against "the MCP spec" is
writing against all of these at once, which is the practical reason the
recommendations in §9 are mostly about being boring.

### 3g. The collection's own blind spot

Worth recording as a method note. This collection documents MCP across
25-plus sources — but as an **extensibility axis**: which harnesses support
it, how servers are configured, how permissions scope them
(`agent-tool-surfaces.md`, `agent-permissions-approval.md`). Before this
pass, exactly one source note anywhere in the repo recorded what a harness
*does with an MCP result*: Roo Code's `README.md`, on extracting image
content. The transport layer was invisible because every doc stopped at the
tool boundary. Anyone auditing a harness should ask the projection question
directly — it is not visible from the tool list, the prompt, or the config.

---

## 4. `structuredContent` vs `content`: a spec-mandated duplication

The `2025-06-18` revision introduced `structuredContent` and, for
backwards compatibility, a SHOULD: *"a tool that returns structured content
SHOULD also return the serialized JSON in a TextContent block."* It is
still there in `2026-07-28`.

The consequence is unavoidable arithmetic: **any client that forwards both
fields to the model pays for the payload twice**, and the spec asks servers
to make that possible on every call.

[SEP-1624](https://github.com/modelcontextprotocol/modelcontextprotocol/issues/1624)
is the proposal to fix the guidance, and its survey of client behaviour is
the useful part:

- **Cursor** shifted to preferring `content` for model input;
- **VS Code** favours `structuredContent`;
- **most other clients ignore `structuredContent` entirely**;
- **some forward both**, "creating redundant context".

Its worked example: the same email-tool result costs **284 tokens** as
`structuredContent` and **189 tokens** as prose `content` — a 33%
difference *before* any duplication. The proposed split is the one
OpenCode implemented on its own (§3a): `content` is "model-oriented output
optimized for readability and token efficiency… preferred for
conversational agents", `structuredContent` is "machine-oriented output for
programmatic tool use, code generation, type-safe orchestration, and strict
schema validation." As of this pass the SEP is open, not merged.

There is also an open discussion
([#1710](https://github.com/modelcontextprotocol/modelcontextprotocol/issues/1710))
for a *configurable response format* — the client asking for `text`,
`structured`, or `both`. That is the same idea as the verbosity control
Anthropic's own tool-design guidance recommends and that
`agent-tool-implementations.md` §5a already records: a `response_format`
enum whose `concise` mode cost **72 tokens vs 206** for the same Slack
result.

**The practical rule for a server author today:** decide who your tool is
for. If it is for a model to read, put a compact rendering in `content` and
either omit `structuredContent` or accept that some clients will show both.
If it is for a program (Code Mode, an orchestration script, a typed SDK),
`structuredContent` is the right home and the text block should be a
*summary*, not the same JSON again. Emitting both, identical, is the one
choice that is wrong for every consumer.

---

## 5. Binary, and the one rule that matters

**Base64 must never reach the model as text.** It costs 2.5–3.6× the
underlying bytes (§1a), it is unreadable, and it displaces context that
could have held the answer.

The best available field measurement of getting this wrong is
[DesktopCommanderMCP #521](https://github.com/wonderwhy-er/DesktopCommanderMCP/issues/521):
a server returned an image with base64 in `structuredContent` alongside a
native image block; the client serialised `structuredContent` as text; a
single 146 KB PNG cost **106,356 tokens** versus **39,199** for the
built-in read of the same file — **2.7×**, for identical visual output.
Both sides are at fault in an instructive way. The client shouldn't
stringify a field it is already rendering natively; the server shouldn't
put bytes in a field whose projection it cannot predict. §3f is why the
server cannot predict it.

The alternatives, in descending order of preference:

1. **A native typed block** — `image` / `audio` — so the client can route
   it to a real multimodal content block. Note that this closed a gap on
   the Gemini path during the window this collection has been running:
   Gemini 3 added multimodal `FunctionResponse.parts` with `inline_data`,
   so a function response carrying an image is now a supported path rather
   than the error `agent-design/adk.md` §2b describes.
2. **A `resource_link`** — a URI plus a name and MIME type, no payload.
   The cheapest thing a tool can return, and the only content type designed
   as a pointer. Its problem is §3f: it is the *least* uniformly handled
   block type, and two of the seven projections drop it silently.
3. **A separate attachment channel** with a stub in the text —
   OpenCode's `[3 images attached to the result]`. This is the most robust
   because the stub survives even when the channel doesn't.
4. **An artifact handle** — §7.

And whatever is chosen: **say what was done.** A dropped blob, a downscaled
image, a truncated stream. The read-tool teardown recorded in
`agent-tool-implementations.md` §5 makes the same point from the file side
— a downscaled image must disclose its scale factor, because "nothing in
the pixels records that the image was resized on the way in", and every
coordinate the model computes afterwards is confidently wrong.

---

## 6. Caps

Covered in depth for built-in tools in `agent-tool-implementations.md` §6;
the MCP-specific additions are:

- **The cap is the client's, not the server's**, and the server usually
  cannot see it. Claude Code's 25,000-token default (§3e) is invisible to
  the server that just produced 40,000 tokens of database schema.
- **`_meta["anthropic/maxResultSizeChars"]` is the only per-tool
  negotiation of a cap found in this pass**, in any client. It is
  vendor-specific, it lives in the *tool declaration* rather than the
  result, and it is capped at 500,000 chars. Worth knowing it exists;
  not worth designing around.
- **Pagination is the server's job and almost nobody does it.** MCP has
  cursor pagination for `tools/list`, `resources/list` and friends — and
  nothing at all for tool *results*. A tool returning 10,000 rows has to
  invent its own `offset`/`limit`, and the truncation-notice discipline
  from `agent-tool-implementations.md` §6a applies unchanged: **every
  truncation states the next call**, and notices live at the edges of the
  payload, never in the elided middle.
- **The throw-vs-truncate finding transfers.** Claude Code's measured
  result — a hard error yields a ~100-byte tool result while truncation
  yields 25K tokens at the cap, so error rate fell but mean tokens rose —
  is the argument for `isError: true` with a recovery instruction over a
  silently clipped success. MCP's error channel is explicitly specified for
  this ("actionable feedback that language models can use to
  self-correct"), so use it.

---

## 7. Artifacts: handles instead of payloads

The idea — *store the payload out of context, give the model a reference
plus a description of the payload's shape, and give it tools to operate on
the reference* — is not speculative. Six mechanisms exist across four
independent groups — three of them inside MCP itself, three in shipping
harnesses — and they agree on more than they disagree.

### 7a. The precedents

| Source | Handle | What the model gets instead | Scope / lifetime |
|---|---|---|---|
| **MCP `2026-07-28`, "Stateful Tools"** (non-normative but in-spec) | server-minted opaque id returned by a creation tool, passed back as an ordinary argument | whatever the creation tool's text says (`"Created basket bsk_a1b2c3"`) | server-defined; the spec says **state it in the tool description** |
| **MCP `resource_link`** | a `uri` | `name`, `description`, `mimeType` | client fetches via `resources/read` |
| **MCP tasks extension** (`io.modelcontextprotocol/tasks`) | `taskId` | status, TTL, poll interval | durable, TTL-bounded; `tasks/get` retrieves the result later |
| **Claude Code** | a file path on disk | a preview plus the path | session/workspace |
| **OMP** | `artifact://<id>` | paged reads through the *same* `read` tool and the *same* selector grammar as files (`:N-M`, `:raw:N-M`) | session |
| **Google ADK** | a filename, versioned | nothing, until the model calls `LoadArtifactsTool` | session by default; `user:` prefix widens to all sessions for that user; `InMemory` or GCS backend |

Plus the school that avoids the question by not putting results in context
at all: **code execution / programmatic tool calling**, where intermediate
results live in a sandbox and only what the program returns is seen —
Anthropic's measured 43,588 → 27,297 average tokens (−37%) on research
tasks, Cloudflare's Code Mode, OpenCode's Code Mode tool read in §3a, and
DeepSeek's Code Mode which this collection already records for saying the
sentence plainly: *intermediate tool results never enter the
conversation*.

### 7b. The six decisions an artifact system forces

Synthesised from the above; this is the part not written down anywhere
else.

1. **Who mints, and when.** Automatic on overflow (Claude Code: over a
   threshold, spill and rewrite the result) or explicit (ADK: a tool calls
   `save_artifact`). Automatic never forgets; explicit is intentional and
   lets the tool choose the representation rather than accepting a byte
   cut. The two compose — mint explicitly when the tool knows better,
   spill automatically as a backstop — but automatic minting is the one
   that needs the carve-out in §7c, because a tool that reads the store
   must never spill into it.
2. **Naming and scope.** ADK's split is the most developed: a bare
   filename is scoped to `(app, user, session)`, a `user:` prefix widens
   it to `(app, user)`. The MCP spec's guidance pulls the other way —
   handles should be **opaque**, because "handles that encode internal
   structure invite parsing or guessing." Both are right for their
   context: a name the model chose should be legible; an id the server
   minted should not be guessable. If handles are bearer tokens (an
   unauthenticated server), the spec is explicit that they need real
   entropy.
3. **What the stub says.** The load-bearing decision, and the one most
   implementations get thinnest. The stub replaces the payload, so it must
   carry everything needed to decide *whether to fetch* and *what to fetch*
   — shape without content. Rows and columns for a table; size, MIME and
   dimensions for a blob; the count and the first page for a list. The
   sharpest precedent is in `agent-tool-implementations.md` §5, where any
   notebook cell output over 10,000 characters is replaced **by a `jq`
   pointer** — an address *and the means to query it* — and the
   generalisation offered there is the right one: *"when a payload's
   existence and shape are what the model needs and its contents are not,
   return an address and the means to query it."*
4. **The operation set.** A handle with only "load it all back" is a
   deferral, not a solution — the tokens arrive one turn later. What makes
   it a solution is operations that reduce: page, filter, aggregate,
   convert, diff. OMP's answer is the most economical: `artifact://` is a
   URI scheme the existing `read` tool already understands, with the same
   selector grammar as files, so the operation set costs **zero new tool
   definitions**. ADK's `LoadArtifactsTool` is the other shape, and its
   redeeming property is the temporariness in (6).
5. **Lifetime, and what expiry looks like.** The MCP spec is unusually
   concrete: state the retention policy **in the creation tool's
   description** so the model can see it when deciding to create state, and
   make a call against an expired handle *"a tool execution error that says
   so, so the model can recover by creating a new one."* Expiry is a
   recoverable, self-describing error, not a null.
6. **Whether loading is permanent.** ADK's `LoadArtifactsTool` appends the
   artifact **to that request only** — it is not written into conversation
   history. That is a materially better contract than a file path, because
   it makes an expensive load a one-turn cost rather than a permanent one,
   and it is free on that stack.

### 7c. Two traps this collection has already documented

Both apply directly and neither is obvious:

- **The circular spill.** Claude Code sets `maxResultSizeChars: Infinity`
  on `Read` specifically because "persisting creates a circular
  Read→file→Read loop" — spill a read to a file and the model reads the
  file, which spills, forever. Any tool whose job is *reading the store the
  artifacts live in* must be exempt from spilling into that store.
- **The stub that outlives its referent.** `agent-tool-implementations.md`
  §7 records the production deadlock where a per-line clamp, a
  read-before-write ledger and an unchanged-file dedup — each correct
  alone — lock a model into an infinite re-read loop, and the
  "consume-on-hit" cache rule that stops a dedup stub pointing into
  context that compaction has since eaten. An artifact stub is the same
  object: a pointer in the transcript whose target has independent
  lifetime. It must survive compaction, or fail loudly when it doesn't.

---

## 8. Marking something as *for the user*

The last piece of the question, and the one with the clearest protocol
answer that nobody uses.

- **`annotations.audience: ["user"]`** on any content block. Spec-level,
  free, present since `2025-06-18` on every content type, and exactly the
  semantics wanted: *this block is for the human, not the model.* Paired
  with `priority` (0–1). Adoption is the problem — none of the seven
  projections in §3f was found to read it.
- **`_meta`** as the client-only channel (§2a): the OpenAI Apps SDK
  convention, where `_meta` reaches the widget and never enters model
  context.
- **MCP Apps (SEP-1865)** — the standardised version of that: a server
  publishes an HTML view as a `ui://` resource with mimeType
  `text/html;profile=mcp-app`, links it to a tool through `_meta`, and the
  host renders it in a locked-down iframe with a CSP that blocks external
  network requests, so the view must be self-contained. Bidirectional
  JSON-RPC between the view and the host. Reached stable **2026-01-26**
  and is supported by Claude (web and desktop), VS Code Insiders, Goose and
  Postman. This is the most mature "return it to the user" mechanism in
  the ecosystem.
- **Harness-side file channels.** Claude Code's current tool surface
  carries the file-shaped equivalent — a send-file tool that takes a list
  of paths plus a `display` hint (`render` inline vs `attach` as a
  download card) and a `status` (`proactive` when the agent initiated,
  `normal` when replying) — and a publish-an-artifact tool for pages. Not
  MCP, but the same three decisions: *who is it for*, *render or attach*,
  *did the user ask for it*. **Provenance caveat**: this is observed from
  a live session's own tool surface (2026-08-21, the remote/web
  execution environment), not from a file stored in
  [`leaked/claude-code/`](./leaked/claude-code) — the captures there are
  v2.1.172 and predate these tools. Treat it as a dated observation of a
  shipping surface, at the same evidence tier as a live probe rather than
  a source read.
- **OpenCode's `attachments`** (§3a) — the internal version: a tool result
  may carry an attachment list alongside its text output, and the text
  gets a stub.

The design point across all five: **audience is a property of a content
block, not of a tool call.** A single result routinely contains something
for the model (a summary), something for the user (a chart), and something
for neither (a cursor). Any format that can only mark the whole result will
push the other two into the model's context by default.

---

## 9. What to do, if you are writing one

**As a server author**, in priority order:

1. **Never base64 into text.** Use a typed block, a link, or a stub.
2. **Never serialise a document into a JSON string.** `content` is an
   array — return N text blocks. If the payload is code or a diff, frame
   it with a line-number prefix rather than escaping it
   (`agent-design/formats.md` §8a; ~1.13× and it keeps byte-exactness).
3. **Never double-encode.** If you are proxying a JSON API, parse it and
   re-render; don't pass its JSON through as a string.
4. **Pick one of `content` / `structuredContent` per tool and say why.**
   Prose for models, structure for programs. Emitting both, identical, is
   wrong for every consumer (§4).
5. **Write errors as instructions**, in `isError: true` results rather
   than protocol errors, and prefer erroring over silently truncating.
6. **Paginate, and state the next call in the truncation notice.**
7. **If the payload is large, return a handle and a stub that describes
   its shape** — and state the retention policy in the creating tool's
   description (§7b).
8. **Emit `annotations.audience`** even though few clients read it. It is
   free, it is the correct semantics, and it costs one field.
9. **Assume nothing about projection.** §3f is your consumer set.

**As a client author:**

1. **Never `JSON.stringify` a `CallToolResult` into the conversation.**
   Write a named projection function; OpenCode's `projectMcpResult` is a
   good model.
2. **Never drop a content block silently.** If you don't support
   `resource_link` or `audio`, say so in the result text.
3. **Route binary out of the text path**, and leave a stub behind.
4. **Don't forward both `content` and `structuredContent`** to the model
   unless you have measured that you want to pay twice.
5. **Cap, and spill rather than dump** — with a carve-out for the tool
   that reads the spill store.

---

## 10. What this changes for this collection's own design

Tracked in [`agent-design/`](./agent-design); recorded here so the
cross-references are one hop.

- `agent-design/adk.md` §2b's "images and PDFs become errors" is a
  statement about ADK Java's `wrapCallResult`, and remains true there — but
  its forward-looking half ("it forecloses the obvious later move of
  returning a screenshot") is now out of date on the model side: Gemini 3
  supports multimodal `FunctionResponse.parts`, so the ceiling is the
  binding, not the API.
- §2c's escaping note is confirmed and can now be priced: ~1.11× on the
  design's tag-framed prose, ~1.22× on the code-shaped payloads `Read`
  returns. That is a real but bounded cost, and it does **not** change the
  §8a framing decision, because the alternative framings cost the same.
- The design's standing ADK rule (one text block, no `structuredContent`,
  never rely on anything but block zero) is validated by §3f from a
  direction it didn't anticipate: it is also the right defensive posture
  against *other* clients' projections, not just ADK's.
- Artifacts are a genuine gap in the design and are now tracked in
  `agent-design/future.md`, with ADK's `ArtifactService` as the substrate
  and OMP's "same tool, new URI scheme" as the model-facing shape.
- **The design cannot target `2026-07-28`, and the reason generalises.**
  Read from source on 2026-08-21: `adk-java` at HEAD (`c1bda9c`) pins
  `<mcp.version>1.1.2</mcp.version>`; the MCP Java SDK's
  `ProtocolVersions.java` declares exactly four constants —
  `2024-11-05`, `2025-03-26`, `2025-06-18`, `2025-11-25` — in both 1.1.2
  and in 2.0.1, the latest release. There is no `MCP_2026_07_28`
  anywhere. Java is a **Tier 2** SDK, which commits to new protocol
  features "within 6 months" against Tier 1's "before the spec release";
  the four SDKs that shipped `2026-07-28` on publication day were the
  Tier 1 four (TypeScript, Python, C#, Go). So the realistic path to the
  current revision runs through a Java SDK release around January 2027
  *and then* an `adk-java` bump off the 1.1.x line.

  The transferable part is not the dates. It is that **a design's usable
  protocol version is set by its SDK's tier and its framework's pin, not
  by the specification** — two dependencies deep, neither of them
  announced in the design's own documents. Anyone reasoning about MCP
  capabilities from the spec alone is reasoning about a protocol their
  code cannot speak. The corollary that made this cheap rather than
  painful for `agent-design/`: every rule in it is written against the
  protocol's *shape* — text blocks, an error flag, named fields — which
  is stable from `2024-11-05` through `2026-07-28`, so a three-revision
  lag is a scheduling fact and not a design constraint. `adk.md` §0
  carries the full accounting.

---

## 11. Open questions

Things this pass could not settle from documentation and source alone. Each
needs one real call against a running stack.

- **What does an ADK-rendered function response actually look like in the
  prompt?** `agent-design/adk.md` §9 already lists this; §1a now gives it a
  budget to be measured against (is the observed inflation ~1.1×, or does
  the Struct envelope add more?).
- **Which of the §3f projections read `annotations.audience`?** None was
  found to, but absence of the string in the files read is weaker evidence
  than a probe.
- **Does any client implement `resource_link` end-to-end** — tool returns a
  link, client fetches via `resources/read`, content reaches the model —
  without the model having to ask? OpenCode passes the link through as
  text, which puts the fetch on the model.
- **Cline's two paths.** §3c reads the SDK path; the VS Code path differed.
  Which one a given install uses, and whether the SDK path is now the
  default, wants a runtime check rather than more reading.
- **Does the `2026-07-28` statelessness change break existing servers in
  practice**, and how are clients handling the backwards-compatibility
  probe? The spec describes it; the field hasn't been surveyed here.
- **Is the o200k_base proxy honest for Claude?** §1a's ratios should be
  re-run on the target tokenizer before any number here is used as a
  budget.
