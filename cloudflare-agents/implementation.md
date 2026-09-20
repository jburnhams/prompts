# What the source says that the docs do not

`packages/think/src/` and `packages/agents/src/` at `c076e4c`.

The first three passes over this SDK were **documentation-led**, and the
two best findings in this folder — the base64 redactor
([`browser.md`](./browser.md)) and the gated `SkillRunContext`
([`skills.md`](./skills.md)) — were both things the docs did not mention
and the source did. That is the argument for this file.

Scale, for calibration: `packages/agents/src` is ~100k lines,
`packages/think/src` ~28k excluding tests, and `think.ts` alone is
**16,962 lines**. Everything below is from reading targeted parts of
those, chosen where implementation decides something the prose leaves
open.

**One correction lands here.** [`think.md`](./think.md) repeated the
docs' "`edit` supports fuzzy matching" and built an argument on it about
silent corruption. The source says otherwise, and §1 is the retraction.

---

## 1. `edit` — exact first, whitespace-normalised fallback, and it says so

`packages/think/src/tools/workspace.ts`. The model-facing description is
the **exact-match** discipline, not a fuzzy one:

```ts
description:
  "Make a targeted edit to a file by replacing an exact string match. " +
  "Provide the old_string to find and new_string to replace it with. " +
  "The old_string must match exactly (including whitespace and indentation). " +
  "Use an empty old_string with new_string to create a new file.",
```

The control flow is a four-way decision, and each branch is an error the
model can act on:

```ts
const occurrences = countOccurrences(content, old_string);
if (occurrences === 0) {
  // Try fuzzy match — normalize whitespace and look again
  const fuzzyResult = fuzzyReplace(content, old_string, new_string);
  if (fuzzyResult === "ambiguous") {
    return {
      error:
        "old_string matches multiple locations after whitespace normalization. " +
        "Include more surrounding context to make the match unique."
    };
  }
  if (fuzzyResult !== null) {
    await ops.writeFile(path, fuzzyResult);
    return { path, replaced: true, fuzzyMatch: true, lines: … };
  }
  return {
    error:
      "old_string not found in file. Make sure it matches exactly, " +
      "including whitespace and indentation. Read the file first to verify."
  };
}

if (occurrences > 1) {
  return {
    error:
      `old_string appears ${occurrences} times in the file. ` +
      "Include more surrounding context to make the match unique."
  };
}
```

and "fuzzy" means exactly one thing:

```ts
function normalizeWhitespace(s: string): string {
  return s.replace(/[ \t]+/g, " ").replace(/\r\n/g, "\n");
}
```

Runs of spaces and tabs collapse to one space; CRLF becomes LF. **No
edit distance, no token similarity, no scoring.** The normalised search
is then located in the normalised content, checked for a *second*
occurrence (`"ambiguous"`), and `mapToOriginal` walks both strings in
parallel to recover the original byte offsets so the replacement
preserves the file's real surrounding whitespace.

Five properties, all of which the one-line doc description hides:

- **Exact is tried first and must be unique.** `occurrences > 1` is an
  error naming the count. This is the same rule as every exact-match
  harness in `../agent-tool-implementations.md` §4.
- **The fallback only fires on zero matches**, so it can never override
  a successful exact match.
- **The fallback has its own uniqueness guard.** Whitespace
  normalisation can merge two previously-distinct regions; `"ambiguous"`
  is that case, and it refuses rather than picking one.
- **The result says it happened**: `fuzzyMatch: true`. A caller — or an
  eval — can count fuzzy edits and treat a rise as a signal.
- **The two failure messages differ and both name the fix.** Not found →
  "Read the file first to verify". Multiple → "Include more surrounding
  context".

So the previous write-up's "a fuzzy edit that matches the *wrong* region
is a silent corruption" is wrong twice over: whitespace-only
normalisation cannot match a semantically different region the way
similarity scoring can, and it is not silent.

The honest residual risk is narrower and worth stating: normalisation
collapses indentation, so in a whitespace-significant language
(Python, YAML, Makefiles) a search string can match a region at a
*different nesting depth*. `mapToOriginal` preserves the file's
surrounding bytes, so the damage is bounded to the replaced span — but
the replaced span may not be the one intended, and `fuzzyMatch: true` is
the only signal.

## 2. Aged-media eviction — the screenshot problem, solved and shipped

`packages/think/src/media-eviction.ts`, 340 lines. The file header is
itself the design document, and the distinction it opens with is the one
`../agent-tool-result-transport.md` and `../agent-context-compaction.md`
keep needing:

> This is deliberately not how Sessions stores a message, and the two must
> not be confused:
>
>   - Row chunking is a **STORAGE** detail. A message too large for one SQLite
>     row is split across continuation rows and reassembled on read, byte
>     for byte. Invisible to the model and lossless.
>   - Media eviction is a **CONTEXT** decision. Once a screenshot has aged out
>     of the recent window, re-sending it on every turn is pure cost, so
>     Think removes it from the conversation and leaves a marker naming a
>     Workspace file. Visible to the model and lossy on purpose — the agent
>     reads the file back with the workspace `read` tool when it actually
>     needs the picture again.
>
> The bytes are written to the Workspace RAW (not as a `data:` URL string)
> with their real mime type, so `read` recognises `image/*` and puts a real
> image back into the model's context.

and closes with the rule that makes it safe:

> Plain text parts are never evicted: they are the conversation itself.

`../agent-vision-multimodal.md` §8 records the screenshot-accumulation
problem and finds nobody solving it. **This is the solution**, and it is
about 340 lines.

The marker:

```ts
export function evictionMarker(
  bytes: number,
  path: string,
  mediaType?: string
): string {
  const media = mediaType ? `${mediaType}, ` : "";
  return `[evicted ${media}${bytes} bytes; preserved at ${path}]`;
}
```

So the model sees
`[evicted image/png, 925926 bytes; preserved at /attachments/evicted/msg_7f3a-0.png]`
— **a ref with metadata**, arrived at independently, for context
management rather than for tool results. And the path is deterministic:

```ts
export function evictedFilePath(messageId: string, index: number, mediaType: string | undefined): string {
  return `/attachments/evicted/${messageId}-${index}.${extensionFor(mediaType)}`;
}
```

Seven implementation decisions worth copying:

**1. There is no drop-the-bytes mode, and the option that offered one is
deprecated into a no-op.**

```ts
/**
 * @deprecated Ignored. Evicted bytes are always preserved in the Workspace
 * under `/attachments/evicted/`; there is no drop-the-bytes mode. Accepted
 * so existing configurations keep compiling.
 */
externalizeToWorkspace?: boolean;
```

A footgun removed without breaking the build — the config key still
parses, it just cannot do the dangerous thing any more.

**2. The retention window is clamped against its own misconfiguration.**

> Messages at the tail of the active path that are never evicted.
> Think clamps this to at least the read-time window the model replays at
> full fidelity, so **a misconfigured low value can never strip content the
> model still sees.**

**3. The marker format is a wire contract, and stability is stated.**

> The exact marker Think has always written. Old and new markers are
> byte-identical, so a transcript evicted before and after the Sessions
> replatform reads the same and **old markers keep resolving**.

**4. The walk is bounded against hostile input** — the same rule as the
base64 redactor, and the comment says why:

```ts
/** Nested tool-output walks stop here so hostile output cannot recurse forever. */
const MAX_WALK_DEPTH = 8;
```

**5. The cheap gate runs before any decode.**

```ts
// A `data:` URL is always larger than its payload, so the cheap string
// length rules out small values before any decoding happens.
if (url.length < minPartBytes) return null;
```

with a separate predicate, `hasEvictableMedia`, that "decodes nothing —
this is the in-memory gate that decides whether a pass is worth
scheduling".

**6. Each pass is bounded and resumable.** `maxRowsPerPass` (default 64)
— "Bounds how long a single pass can take; remaining rows are picked up
by the next pass." Incremental GC rather than a stop-the-world sweep.

**7. Nothing is mutated and nothing is written speculatively.**
"Returns a new message — the input is never mutated, and nothing is
written when nothing qualifies."

Two eviction sites, not one: a `file` part whose `url` is a large
`data:` URL becomes a text marker, *and* large `data:` strings nested
anywhere inside a tool part's `output` are replaced **in place**, "so
tool-specific `toModelOutput` handlers still work". The second is the
one that matters in practice — the header notes screenshots "commonly
arrive that way".

## 3. The system prompt is assembled from the tools actually present

`think.ts`, `_buildThinkCapabilityBlock`. Every line is conditional on a
tool being in this turn's `ToolSet`:

```ts
const hasWorkspaceTools = ["read","write","edit","list","find","grep","delete"]
  .some((toolName) => toolNames.has(toolName));
const hasExtensionTools = toolNames.has("load_extension") || toolNames.has("list_extensions");
const hasExecuteTool = toolNames.has("execute");
const hasFetchTools = [...toolNames].some((name) => name.startsWith("fetch_"));
```

and the block it builds ends with the line that makes the whole thing a
safety property rather than a token saving:

```ts
lines.push(
  "- Do not claim access to capabilities that are not exposed as tools in this turn."
);
```

Selected verbatim lines:

> - You can inspect and edit the agent workspace using the available file tools.
> - Use the tools exposed in this turn when they materially improve accuracy or let you act on the user's request. **Treat tool descriptions and schemas as the source of truth.**
> - If sandboxed execution is available, prefer it for safe, bounded checks or coordinated multi-step operations.
> - If fetch tools are available, use them to read allowlisted HTTP resources (documentation, APIs). **They are read-only and bounded; respect their allowlist and do not assume access to other URLs.**

This is [`context-blocks.md`](./context-blocks.md)'s *"the checks are
structural, not nominal"* applied to **prompt text** rather than to the
tool surface, and it is the other answer to the per-model prompt
variation question `../agent-design/README.md` settles by adopting
Codex's subtraction-by-heading. Codex removes a named section when a
capability is absent, which makes headings an interface — rename one and
the removal silently stops working. This **adds** lines keyed on tool
presence, so there is no heading to drift and the conditional is a set
membership test.

Idempotent by string check, which is crude and works:

```ts
if (baseSystem.includes("You are running inside a Think agent.")) {
  return baseSystem;
}
```

The default fallback prompt (`getSystemPrompt()`, "ignored when context
blocks are configured") is worth having in full for the collection's
prompt comparisons:

> You are a careful, capable assistant helping the user complete their task.
>
> Use available tools when they materially improve accuracy or let you act on the user's request. Before changing code, understand the relevant context: existing patterns, dependencies, tests, and nearby conventions.
>
> Keep changes focused on the user's request. Prefer small, idiomatic edits over broad rewrites or new abstractions. Do not introduce new dependencies, secrets, destructive actions, or persistent side effects unless the user clearly asks or approves.
>
> When the task is complex, briefly state your approach and keep the user informed with concise progress updates. If you modify code, verify with the smallest relevant test, build, typecheck, lint, or runtime check available, and **report any checks you could not run.**
>
> Be direct and useful in your final response: summarize the outcome, mention important files or commands, and call out real blockers or risks.

Five paragraphs, and the bolded clause is `../agent-design/`'s
completion-audit discipline in seven words.

## 4. Context overflow: two layers, and neither matches a provider string

`think.ts`, `ContextOverflowConfig`. `../agent-context-compaction.md`
catalogues proactive triggers (token thresholds, turn counts). This
ships **both** directions with the seam between them stated:

> Compaction (`compactAfter()`) is only checked between turns, so a
> long, tool-heavy turn can grow past the window before the next check;
> the provider then rejects the request.

- **Reactive backstop** — on an error classified `context_overflow`,
  "discard the truncated partial, run `session.compact()`, and re-run
  the turn from the compacted history". The partial is deliberately not
  persisted: *"keeping the cut-off assistant message would orphan it
  beside the recovered answer (and duplicate any tool work the retry
  re-issues)"*.
- **Proactive guard** — before each step, read the *previous* step's
  `usage.inputTokens` and compact if it crosses
  `maxInputTokens * (headroom ?? 0.9)`. "Keys off usage (every provider
  reports it), not provider error strings."

Three details that are the actual engineering:

**The fallback when a provider omits `inputTokens`** is
`usage.totalTokens` (input + output) — *"a safe over-approximation that
compacts slightly early rather than missing the threshold"*. A stated
direction to err, with the reason.

**Two independent budgets, because they fail differently.**
`maxRetries` bounds the reactive path; `maxCompactions` bounds the
proactive one, and the comment says why it must exist separately:

> a no-op compaction would repeat on every step, so the cap stops the
> guard from compacting (and emitting `chat:context:compacted`) on each
> one.

A compaction that frees nothing is an infinite loop unless something
counts it. That failure mode is not in `../agent-context-compaction.md`.

**Provider knowledge is real, opt-in, and outside the core.** The type
comment claims *"Think ships **no** provider-specific string/code
matching"*, and forty lines later there is a regex matching six
providers' overflow messages. Not a contradiction — the resolution is
the design point:

> Think ships this as an explicitly-imported helper rather than wiring
> it into core, so the framework default stays free of provider strings.

```ts
const CONTEXT_OVERFLOW_PATTERN =
  /prompt is too long|context[_ ]length[_ ]exceeded|maximum context length|exceeds the maximum number of tokens|input token count|reduce the length of|input is too long|too many (?:input )?tokens|context window/i;
```

with the precision/recall trade argued rather than assumed:

> This default deliberately favors **recall over precision**: a missed
> overflow means no recovery (the feature's whole point), whereas a false
> positive self-heals — the retry hits the same non-overflow error, the
> budget is spent, and it surfaces terminally anyway. The vaguest
> fragment (`reduce the length`) is anchored to `of` to match the real
> OpenAI phrasing without matching unrelated prose.

The classification enum itself is a closed vocabulary —
`context_overflow | rate_limit | transient | fatal | unknown` — with
only the first acted on and the middle two marked "reserved for future
backoff/retry policies".

## 5. Compaction is non-destructive: summaries are overlays, not rewrites

`packages/agents/src/sessions/core.ts`. The session is a **tree**, and
compaction does not rewrite it:

> - Non-destructive compaction (summaries replace ranges at read time)

A compaction is a row in `cf_agents_session_compactions`
(`session_id, id, seq, summary, from_message_id, to_message_id,
created_at`), and reading the active path cuts it into segments:

> The path is first cut into segments — a compaction overlay, or a run of
> [rows] …

> Compaction overlays are honored **without planning them up front**. An
> [iteration] … stops in the messages after the last compaction never
> pays for that.

Every compaction implementation in `../agent-context-compaction.md`
replaces messages with a summary and loses the originals. This one keeps
them and applies the summary **at read time**, which buys three things
that design cannot have: a compaction is reversible, two different
read policies can disagree about the same stored history, and the
originals remain available to an audit after the model has stopped
seeing them.

It pairs with the tree: branching plus read-time overlays means the same
stored messages can be read at different compaction levels on different
branches.

A related operational note, from the startup path in `think.ts` — the
degradation message when the stored transcript cannot be hydrated:

> The agent is starting with an empty in-memory message view; persisted
> history is untouched. If the error is SQLITE_NOMEM, the stored
> transcript is too large to hydrate (**often inline base64 media in tool
> results**) — compact or clear the session to recover.

The same root cause as §2, surfacing as a startup failure, with the
remedy in the message. Note "persisted history is untouched" — the
degradation says what it did *not* damage.

## 6. `ensureValidContinueCheckpoint` — the transcript is not the request

`think.ts`. A small function carrying a constraint worth knowing:

```ts
const CONTINUE_CHECKPOINT_PROMPT =
  "Continue your previous response from exactly where it left off. Do not repeat any of it.";
```

> Continuing a partial assistant turn (e.g. after a deploy interrupts a
> stream) replays a transcript whose final message is that partial
> assistant message — an "assistant prefill". Modern chat models reject
> this: Anthropic Claude 4.6+ returns a 400 (*"This model does not
> support assistant message prefill. The conversation must end with a
> user message."*). To reach a valid continue checkpoint across providers
> we append an ephemeral user message. **This shapes only the model
> request; it is never persisted to the transcript.**

Two things. The **concrete provider constraint** — durable resumption of
a mid-stream turn is not just a storage problem, because the obvious
replay is a shape the provider rejects. And the **fix's discipline**: a
message that exists in the request and not in the history. The
request-shaping/history-storing split is the same one §2 opens with, and
`../agent-design/artifacts.md` §5.6 reaches independently for images
("a look is one turn by default" — appended to *that request only*,
never to history).

## 7. The fetch tool: a target is a tool, and the model may set three headers

`packages/think/src/tools/fetch.ts`, 1,109 lines. Positioned in its own
header comment:

> A conservative, opt-in HTTP read capability for Think agents. It is
> deliberately read-only (GET), allowlisted, and bounded. **It is NOT a
> general-purpose HTTP client and NOT an SSRF primitive** — mutations and
> rendered-page automation live elsewhere.

The shape is the interesting part. Rather than one `fetch(url)` gated by
a check, **each configured target generates its own tool**:

> Named binding targets. Each entry generates a `fetch_<name>` tool with
> the binding, allowlist, and fixed headers baked in.

```ts
allowlist: ["https://developers.cloudflare.com/**"],
bindings: {
  docsApi: { binding: env.DOCS_API, allowlist: ["/v1/docs/**"] }
}
```

So the model calls `fetch_docsApi` with a *path*, and the origin,
credentials and fixed headers are not in the model's reach at all. The
generic `fetch_url` is registered **only** if a public allowlist is
configured, and a configuration with neither fails loudly:

```
createFetchTools requires a non-empty `allowlist` or at least one `bindings` target.
```

Seven defaults that read as a checklist:

```ts
const DEFAULT_MAX_BYTES = 1_000_000;
const DEFAULT_MAX_MODEL_CHARS = 24_000;
const DEFAULT_TIMEOUT_MS = 10_000;
const DEFAULT_MODEL_HEADER_ALLOWLIST = ["accept", "accept-language", "range"];
const DEFAULT_ACCEPT =
  "text/markdown, text/plain;q=0.9, application/json;q=0.8, text/html;q=0.5, */*;q=0.1";
```

- **Two caps on different axes.** `maxBytes` is a transport bound;
  `maxModelChars` is a context bound. Collapsing them is the usual
  mistake — a 900 KB download that must not reach the model is a
  different limit from a 900 KB download that must not happen.
- **A header allowlist for the model.** Three headers: `accept`,
  `accept-language`, `range`. Nothing else in this collection names
  which headers a model may set, and `range` being on the list is what
  makes a bounded partial read expressible.
- **Content negotiation biased toward cheap context**, with the tail
  that stops it backfiring: *"Markdown-first, but still accepts
  everything (`*/*;q=0.1`) so a strict content-negotiating server never
  answers 406."*
- **Redirects are a three-value policy** — `"allowlisted" | "same-origin"
  | "none"`, defaulting to `allowlisted`.
- **A closed error vocabulary**, which is `../agent-design/generative.md`
  §2b's rule shipped for a fetch tool:

```ts
export type FetchErrorCode =
  | "disallowed_url" | "disallowed_redirect" | "timeout" | "aborted"
  | "non_2xx" | "unsupported_content_type" | "invalid_json"
  | "too_large" | "request_failed";
```

- **`spillToWorkspace`** (default `false`) — large or binary bodies
  become a file rather than a result.
- **`onEvent` fires once per fetch, success or failure or block**, so a
  blocked fetch is as observable as a served one.

## 8. The SSRF block-list, with its own historical bug documented

`packages/agents/src/mcp/client/index.ts`. `../agent-design/artifacts.md`
§6 specifies "an IP block-list (loopback, private, link-local,
multicast, reserved)" abstractly. This is that list implemented, and two
of its comments are traps worth knowing before writing one:

```ts
/**
 * fe80::/10 — IPv6 link-local (RFC 4291 §2.5.6).
 *
 * The /10 boundary fixes the first 10 bits (1111111010), which means valid
 * first hextets range from fe80 through febf. …
 *
 * Historical bug: `startsWith("fe80")` only matched the narrower fe80::/16
 * prefix and let fe81::/feab::/febf:: slip through. See issue #1325.
 */
const IPV6_LINK_LOCAL = /^fe[89ab][0-9a-f]/;
```

```ts
// IPv4-mapped IPv6 (::ffff:x.x.x.x or ::ffff:XXYY:ZZWW).
// The WHATWG URL parser does NOT canonicalize hex-form tails to dotted
// form — [::ffff:a00:1] stays as "::ffff:a00:1" and will only be caught
// by the hex branch. Both forms must therefore be handled here.
```

Plus two policy choices stated rather than implied:

```ts
catch {
  return true; // Malformed URLs are blocked
}
```

> Loopback (::1) and unspecified (::) are NOT blocked here:
>   - ::1 is intentionally allowed (parallel to 127.x.x.x for local dev)
>   - :: (== [::]) is blocked via BLOCKED_HOSTNAMES at the hostname level

**Fail closed on a parse failure**, and an allowed exception documented
at the point where a reader would otherwise assume a bug.

## 9. What this file changes about the folder's conclusions

- [`think.md`](./think.md)'s fuzzy-matching claim is **retracted** (§1).
- `../agent-vision-multimodal.md` §8's "nobody solves screenshot
  accumulation" is **false as of this source** (§2).
- `../agent-context-compaction.md` gains two mechanisms it does not
  have: non-destructive read-time overlays (§5) and the no-op-compaction
  loop that makes a second budget necessary (§4).
- The `../agent-design/README.md` decision on per-model prompt variation
  gains a **second mechanism** to weigh against subtraction-by-heading:
  addition keyed on tool-set membership (§3).

The broader lesson is the one this file opens with. The documentation
describes *what the SDK offers*; the source is where the **failure modes
it has already hit** are written down, usually in a comment next to the
line that fixes them. For a collection whose subject is what goes wrong
in agent harnesses, that is the higher-yield read.
