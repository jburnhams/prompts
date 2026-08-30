# Building this on Java ADK: fit, compromises, workarounds

The rest of this folder specifies the agent we want. This document is
about the substrate we intend to build it on — **Google's Java ADK
(`google/adk-java`), with every tool exposed over MCP** — and it exists so
that substrate concerns never leak into the design itself. Nothing here
changes `tools.md`, `formats.md`, or `system-prompts.md`. Where ADK can't
do what the design asks, the gap is named, the compromise is stated, and
the workaround (usually a small override, since we're willing to fork
behaviour) is written down.

Read it as three lists: **what lands unchanged**, **what needs an
override**, and **what to verify against a running stack** before trusting
it.

Grounded in `adk-java` at `8049f7e` (read 2026-07-31; paths in
[`../sources.md`](../sources.md)), with §0's dependency pin re-read at
`c1bda9c` (2026-08-19) alongside the MCP Java SDK at `v1.1.2`/`v2.0.1`. **Java ADK is not Python ADK.** Several
behaviours below differ between them — the Java MCP result conversion in
particular is materially different and lossier — so nothing here should be
inferred from Python examples, docs, or blog posts, and all of it should
be re-checked on a version bump.

---

## 0. Which MCP are we even speaking?

Numbered zero because it precedes every other decision here, and because
the answer is not the one anybody wants.

**The design targets MCP `2025-11-25`, and cannot target `2026-07-28`
today.** The gap is two layers deep, and neither layer is ours:

| Layer | State on 2026-08-21 | Ceiling it imposes |
|---|---|---|
| The specification | `2026-07-28` is current | — |
| **MCP Java SDK** | latest release `2.0.1` (2026-08-19); `ProtocolVersions.java` declares exactly four constants — `2024-11-05`, `2025-03-26`, `2025-06-18`, `2025-11-25`. There is **no `MCP_2026_07_28`** | `2025-11-25` |
| **`adk-java`** | pins `<mcp.version>1.1.2</mcp.version>` at HEAD (`c1bda9c`, 2026-08-19) — the 1.1.x line, a major version behind the SDK's own latest, though 1.1.2 does carry the `2025-11-25` constant | `2025-11-25`, and only if ADK negotiates it |

And the timeline is not short. Java is a **Tier 2** SDK, not Tier 1. Tier 1
(TypeScript, Python, C#, Go) commits to shipping new protocol features
*before* a spec release; **Tier 2 commits to "within 6 months"** and to an
80% conformance pass rate. The four SDKs that shipped `2026-07-28` support
on publication day were the Tier 1 four. On the published commitment,
`2026-07-28` reaches the Java SDK by roughly **January 2027**, and reaches
*us* only after `adk-java` also moves off the 1.1.x line.

**What this costs, concretely: nothing the design wanted.** Working
through the revision's changes against `tools.md` and `formats.md`:

- **Statelessness, `server/discover`, `resultType`, `ttlMs`/`cacheScope`,
  MRTR** — all *server obligations* we don't have to meet yet, and all
  things a per-run stdio server gets nothing from. Being late here is
  free.
- **The one thing worth wanting is already ours.** The revision's
  "Stateful Tools" guidance — server-minted handles instead of protocol
  sessions — is a *replacement* for a mechanism this design never used.
  §6's per-run process already makes the process boundary the state
  boundary. We arrive at the destination without taking the journey.
- **The one thing genuinely deferred is the tasks extension**
  (`io.modelcontextprotocol/tasks`): durable poll handles for long-running
  calls, which is the protocol-native version of background `Bash`
  returning a pid and a log path. Extensions are explicitly **not required
  at any tier**, so this may never arrive on this stack. §7's note that
  the Java MCP path has no progress-notification plumbing stands, and
  background `Bash` stays exactly as `tools.md` describes it.
- **`2026-07-28` does move one argument in our favour** — see §5.

**The rule that follows**, and it is the reason this section exists rather
than a footnote: **write the design against the protocol's *shape*, not
its revision.** Every rule in `tools.md` and `formats.md` §8 is expressed
in terms of text blocks, an error flag, and named fields — concepts stable
across `2024-11-05` through `2026-07-28`. Nothing in the design depends on
a handshake, a session id, or a feature added after `2025-06-18`. That is
what makes a three-revision lag a scheduling fact rather than a design
constraint, and it is worth preserving deliberately: **do not adopt a
protocol feature into the design before the SDK we are pinned to can
speak it.** The corollary is the honest one — re-read this section on
every `adk-java` bump, because the pin is the thing that will move first
and silently.

---

## 1. What lands unchanged

The first-order intuition holds: the model sees tools, not a transport.

- **Tool names survive.** Java's `McpToolset` takes a `toolFilter` (a name
  list or a `ToolPredicate`) but has no name-prefix option, so `Read`,
  `List`, `Grep` stay callable under the names their own descriptions
  cross-reference.
- **Schemas pass through raw.** `AbstractMcpTool.declaration()` puts the
  MCP `inputSchema` straight into `FunctionDeclaration.parametersJsonSchema`
  (and any `outputSchema` into `responseJsonSchema`), rather than
  re-modelling it into a narrower type. `additionalProperties: false`,
  nested objects, enums and arrays should survive — see §5 for the one
  construct that won't.
- **Descriptions are the server's**, which suits the design: the config
  section of `tools.md` renders numbers into description text, and the
  server owns both.
- **Our result *text*** — the block formats in `formats.md` §8 — is
  carried intact inside the envelope; it is the envelope around it that
  changes (§2).
- **The seams the implementation contract assumes exist.**
  `beforeToolCallback` can inspect and rewrite arguments or return a
  substitute result without running the tool; `afterToolCallback` can
  replace the response; `BaseToolset.getTools(ReadonlyContext)` builds the
  tool list per invocation; `processLlmRequest` can adjust the outgoing
  request. That is enough to implement every client-side gate the design
  describes.

---

## 2. The result envelope — the largest single mismatch

`AbstractMcpTool.wrapCallResult` converts an MCP `CallToolResult` into the
`Map<String, Object>` the model receives. Its behaviour, read from source:

| Case | What the model gets |
|---|---|
| One text block | `{"text_output": [{"text": "<our block>"}]}` — but first ADK **tries to parse our text as JSON** (`objectMapper.readValue(...)`); if it parses, the parsed map is used instead |
| Several content blocks | one entry per block in the `text_output` list |
| `isError: true` | `{"error": "Tool execution failed. Details: <text of the FIRST block only>"}` |
| Empty content | `{}` — an empty map |
| Any non-`TextContent` (image, audio, resource) | `{"error": "Tool 'X' returned content that is not TextContent.", "content_details": "<toString of the content list>"}` |

Five consequences, in descending order of how much they matter:

**2a. Errors get a generic prefix and lose everything past the first
block.** The design's errors-are-instructions rule survives — our text
does appear after `Details:` — but it arrives wrapped in a fixed
"Tool execution failed." string. *Compromise*: acceptable as-is.
*Workaround if it dilutes the instruction*: an `afterToolCallback` that
rewrites `{"error": "Tool execution failed. Details: X"}` back to
`{"error": X}`. Either way, **never split an error across content
blocks** — only block zero is read.

**2b. Images and PDFs are not merely unsupported, they become errors.**
Anything that isn't `TextContent` yields an error mentioning
`content_details`. The v1 design doesn't return images (`Read` reports
binary files by status, per `formats.md` §8b), so this costs nothing
today — but it forecloses the obvious later move of returning a
screenshot or a diagram inline, and it should be revisited before any
work that assumes multimodal tool results. *Workaround if needed*:
subclass `AbstractMcpTool` and convert `ImageContent` into a Gemini inline
part rather than an error.

> **Dated 2026-08-21.** The *ceiling* named above has moved and the
> workaround is now the supported path rather than a hack: Gemini 3 and
> later accept multimodal `parts` with `inlineData` inside a
> `functionResponse`, so a function response carrying an image is a
> first-class shape at the model layer. What remains true is the
> statement about `AbstractMcpTool`: the Java binding still errors, so
> **the binding is the ceiling, not the API**. That makes this a
> subclass-one-class problem rather than a re-architecture, and it
> changes the calculus for anything that wants to return a screenshot.
> See `../agent-tool-result-transport.md` §5.

> **Now due, 2026-08-30.** [`vision.md`](./vision.md) specifies image
> artifacts the model can `view`, so this is no longer a forward-looking
> note: **the `AbstractMcpTool` subclass converting `ImageContent` into a
> Gemini inline part is a v1 prerequisite.** It is the only prerequisite,
> and it fails soft — without it, `InspectImage`'s `extract_text` and
> `ask` ops work unchanged (both return text) and only `view` is
> unavailable, which is a coherent degraded mode rather than a blocker.

**2c. Our text is JSON-escaped on the way to the model.** The function
response is a struct, so newlines become `\n`, tabs `\t`, and quotes in
source code `\"`. This erodes the premise behind `formats.md` §8a that
file content reaches the model byte-for-byte, which `Edit`'s exact-match
contract leans on. Two honest notes: it is only partly an MCP effect
(Gemini's function-response part is structured regardless — Anthropic's
API, by contrast, takes a raw string tool result), and models handle
escaped payloads routinely. *Compromise*: accept it, and treat "does
`Edit` still land first-try on files with tabs, quotes and backslashes"
as an explicit eval rather than an assumption. The `Edit` description's
existing "strip the line number and the tab, keep everything after it"
rule is already doing adjacent work.

> **Priced, 2026-08-21.** This is now a number rather than a worry.
> Measured in `../agent-tool-result-transport.md` §1a: JSON-escaping
> costs **1.11×** on tag-framed prose of the kind `formats.md` §8
> specifies and **1.22×** on the quote-and-tab-heavy source `Read`
> actually returns. Two conclusions follow. First, it is a bounded tax,
> not a reason to change transport. Second — and this is the one that
> settles the §8a debate rather than deferring it — **line-number
> framing costs 1.13×, the same as escaping**, so the design was never
> choosing between a free framing and an expensive one; it was choosing
> between two framings of equal cost, one of which preserves `Edit`'s
> byte-exact match and one of which destroys it. The eval named above is
> still the right eval; its result just has a smaller decision hanging
> on it than it looked. The same doc's §3f is the other update worth
> carrying: the standing rule below (one text block, no
> `structuredContent`, never rely on anything but block zero) turns out
> to be the correct defensive posture against *every* client's
> projection, not just ADK's.

**2d. Never return bare JSON as the text payload.** ADK tries to parse
every text block as JSON and, if it succeeds, hands the *parsed map* to
the model — reflowing key order and number formatting, and silently
turning a document into a data structure. Our formats are tag-framed text
(`<file …>`, `<tree …>`), which will never parse as JSON, so this is
currently harmless. It becomes a trap the moment anyone returns a
fact-shaped payload "as JSON text" per the output-format policy: wrap it
in the tagged text, or put it in `structuredContent`, but never emit it
bare.

**2e. Empty content becomes `{}`.** The design forbids silent emptiness,
so this should be unreachable — every "nothing found" case in
`formats.md` §8 is specified to return an explicit note. Treat `{}` as a
bug signal: an `afterToolCallback` that converts it into an explicit
"tool returned no content" note makes the failure visible rather than
mysterious.

**Recommended standing rule for our servers**: one `TextContent` block per
result, no `structuredContent` for model-facing tools (see §3), and never
rely on ordering or on anything but block zero surviving.

---

## 3. `structuredContent` is not the harness channel

The implementation contract's three-channel split (model text / harness
record / human rendering) looks like it maps onto MCP's
`content` + `structuredContent`. It doesn't, on this stack:

- Java ADK's `wrapCallResult` ignores `structuredContent` entirely — it
  only ever reads `content`. So a harness record put there would be
  *invisible* to ADK, not merely redundant. (Python ADK has the opposite
  problem: it dumps the whole result, so `structuredContent` gets
  duplicated *into* the model's context. Two different failure modes for
  the same idea — another reason not to build on it.)
- **Workaround, and the recommended shape anyway**: the harness record
  travels out of band. The server writes it to the run's own state and
  logs; the post-run `git status` cross-check and the `Complete` report
  reconciliation read it from there. The three-channel split survives
  intact; only its plumbing moves off the wire.

---

## 4. Retries make non-idempotent tools dangerous

`McpTool.runAsync` wraps the call in
`.retryWhen(errors -> errors.delay(100ms).take(3).doOnNext(reinitializeSession))`
— **up to three retries with a fresh session on any exception from
`callTool`**. For a read that is a convenience. For `Write`, `Edit`,
`Bash` and especially `AddComment` it is a correctness hazard: a transport
timeout *after* the server has already applied the change (or posted the
comment, or run the command) produces a duplicate on retry. `AddComment`
is the sharp end for *visibility* — it is externally visible, and a
double-posted review comment is exactly the noise the whole validator
pipeline exists to prevent — but **`Bash` is the sharp end for blast
radius**, and it is the one the obvious fix does not cover:

- `Bash` is the only tool here that can do something the harness cannot
  see or undo. A retried `git commit`, `mvn deploy`, migration script or
  `curl -X POST` runs twice, and the second run's failure ("nothing to
  commit", "tag already exists") is what reaches the model, not the first
  run's success.
- **Workaround 2 below cannot gate it.** Retry-on-`idempotentHint` needs a
  per-tool annotation, and §7's own table already states the problem:
  "`Bash` read-only-ness" is a *per-call* classification while "MCP
  annotations are per-tool". There is no annotation that means "idempotent
  when the command is `git status`, not when it is `git push`". So `Bash`
  is annotated non-idempotent wholesale — which disables the retry for
  read-only commands too, and that is the correct trade: the retry buys a
  transport-flake recovery the model can perform itself by calling again,
  and costs a duplicated side effect it cannot detect.
- Which means **workaround 1 is not "the durable fix", it is the only
  fix** for `Bash`, and the design should treat it as mandatory rather
  than preferred.

This is the single most important thing to override.

*Workarounds, in the order to apply them:*

1. **Idempotency keys, server-side — mandatory, not preferred.** Every
   call carries the invocation's tool-call id (via MCP `_meta`, or an
   explicit parameter); the server records applied call-ids and returns
   the original result for a repeat rather than re-applying. This is the
   durable fix, it's independent of ADK's behaviour, and per the `Bash`
   case above it is the *only* fix for the tool with the largest blast
   radius. It has a second payoff the design needs anyway: it is what
   makes **spill-to-scratch retry-safe**. Without it, three retries of a
   truncated `Bash` write three log files and hand the model a path to
   whichever attempt happened to finish; with it, the retry returns the
   first attempt's result and the first attempt's path. `tools.md`'s
   spill rule states the naming requirement (scratch filenames are
   derived from the tool-call id) so the two mechanisms agree even before
   the key is wired up.
2. **Retry only what's safe.** Subclass `McpTool` (or wrap the toolset) so
   the retry policy is keyed off the tool's MCP annotations — retry when
   `idempotentHint`/`readOnlyHint` is set, surface the error otherwise.
   Our own servers set those annotations, so this is cheap.
3. **Make the failure legible either way**: when a retry does fire on a
   mutating tool, log it loudly enough that a duplicated side effect is
   diagnosable after the fact.

**The retry policy also decides which MCP channel our errors travel on.**
`tools.md`'s errors-are-instructions rule says what an error must *say*;
this is where it acquires a wire requirement. MCP has two error
mechanisms, and the choice is not stylistic:

- a **tool execution error** — a normal result with `isError: true` —
  which the spec says clients **SHOULD** hand to the model, described in
  the spec as "actionable feedback that language models can use to
  self-correct";
- a **protocol error** — a JSON-RPC error — which clients only **MAY**
  pass on, and which the spec reserves for malformed requests and unknown
  tools, "issues with the request structure itself that models are less
  likely to be able to fix".

Every error this design defines is the first kind: "file does not exist,
did you mean X", "found 3 matches for `old_string`", "only part of this
file has been read". None of them is a request-structure problem, and all
of them are written to be acted on. **So they are returned as `isError:
true` results and never thrown as protocol errors** — on the audience
argument alone, and on this stack for a second reason: a protocol error
surfaces as an exception, and an exception is precisely what `retryWhen`
keys off. A deterministic `ENOENT` thrown as a protocol error would be
retried three times with a fresh session each time before reaching the
model as the instruction it was from the start — 300 ms and three round
trips spent re-deriving a failure that was never going to change. The
design's most frequent errors would be its most retried ones. (The
exception-on-protocol-error step is inferred from the retry predicate
being untyped; §9 carries it as a thing to confirm.)

---

## 5. Schema expressiveness: the conditional-requirement blocks

`tools.md` uses JSON Schema `allOf`/`if`/`then` twice, both times to make
a conditional requirement schema-enforced rather than prose: `Task`
requires `role` when `subagent_type` is `reviewer` and `finding` when it
is `validator`; `AddComment` requires `anchor` when `suggestion` is true.

Java ADK passes the schema through untouched, so the constraint reaches
the model API — but **function-declaration schemas are not evaluated as
full JSON Schema by the model backend**, and conditional keywords are the
least likely to be honoured. (ADK's own `Claude.java` carries normalisation
code for `allOf`/`anyOf`/`oneOf`/`prefixItems`, which is direct evidence
that these keywords need per-backend handling rather than passing through
cleanly.)

**The protocol has since moved in our favour, which sharpens where the
blame sits.** MCP `2026-07-28` loosened `inputSchema`/`outputSchema` to
permit *any* JSON Schema 2020-12 keywords, and added explicit `$ref`
resolution requirements and resource bounds on composition keywords
(SEP-2106). So `allOf`/`if`/`then` are not merely tolerated by the
protocol, they are sanctioned by it. Nothing changes for us today — §0's
ceiling means we speak `2025-11-25` — but it settles the attribution: the
constraint is **entirely the model backend's function-declaration
subset**, not MCP and not ADK's pass-through. That matters for where a
fix would go if the backend ever rejects the keywords outright: at the
declaration boundary, per-backend, which is exactly where ADK's own
`Claude.java` normalisation already lives.

*Compromise*: keep the blocks in the published schema — they document
intent and cost nothing — but **do not rely on them**. The server
validates the same conditions and returns an instructional error
("`subagent_type: reviewer` requires `role`; pass one of bugs, security,
conventions"), which is where the design's error-as-instruction rule
covers the gap. *Verify* (§8) whether the backend rejects the keywords
outright; if it does, strip them at the server's declaration boundary
rather than weakening the design document.

---

## 6. Advertising is not enforcement

`toolFilter` controls which tools ADK exposes to the model. It does not
stop the server executing a filtered-out tool if something calls it. The
design's structural narrowing is therefore only half-implementable
client-side:

| Design rule | ADK-side | Server-side (the real gate) |
|---|---|---|
| `Edit`/`Write` unregistered in `plan` runs | `toolFilter` omits them | start a server with no write tools for that run |
| `AddComment` unregistered in `implement` runs | `toolFilter` omits it | same |
| review sub-agents get no `Bash` | separate toolset per agent | separate server process |
| git-write blocklist | — | inside the Bash server, always |

`BaseToolset.getTools(ReadonlyContext)` is the clean place for the
client-side half, since it is invocation-scoped rather than static.

**The corollary that shapes deployment**: one MCP server process per run,
started with that run's mode and configuration. That makes the process
boundary the state boundary — the read-before-edit cache lives and dies
with the run —

> **This decision has since acquired a second justification it wasn't
> made for.** MCP `2026-07-28` **removed protocol-level sessions
> outright** — no `initialize` handshake, no `Mcp-Session-Id`, and a
> stated replacement rule: servers needing cross-call state use explicit
> server-minted handles passed as ordinary tool arguments. A design that
> had parked the read-before-edit cache in *session* state would now be
> broken twice over: once because the protocol no longer has sessions,
> and once because §4's retry policy calls `reinitializeSession` on every
> attempt, so the cache would be discarded by the very mechanism meant to
> recover from a flake. Keeping it in process state dodges both without
> anyone having planned to. Two consequences worth writing down: **do not
> "simplify" this into a shared long-lived server** — that is the change
> that would reintroduce both problems and a cross-run state-leak besides;
> and note that one process per run with a fixed tool set is *not* in
> tension with `2026-07-28`'s "`tools/list` MUST NOT vary per-connection"
> rule, since the variation here is between processes, not between
> connections to one process.

That cache now holds the bytes of every file read this run (`tools.md`'s
read-before-edit rule), not a set of paths, so the per-run process is
also carrying real memory: a run that reads a hundred files at the 64 KB
per-entry ceiling is holding a few MB, which is fine for one process per
run and would not be for a shared long-lived one. Hashing rather than
retaining the bytes is the obvious economy, and it costs the `Write` gate
its ability to distinguish "clamped but complete" from "genuinely
partial" only if the hash is taken over the *displayed* text rather than
the raw file — so hash the raw bytes if this ever matters.

It matches the config precedence in `tools.md` too, where
per-run overrides are server-start parameters rather than anything the
model can see. It also forces one non-obvious constraint: **the file tools
and `Bash` must be served by the same process**, because `Bash` can
invalidate the read state that `Edit` depends on. Splitting them across
servers fragments exactly the state the contract relies on, and would
break the deferred read-dedup upgrade (`medium.md` §2g) outright.

---

## 7. Where each harness-side rule actually lives

The implementation contract assumes a harness. On this stack that harness
is split across three places, and getting the split right is most of the
integration work:

| Contract rule | Home | Why there |
|---|---|---|
| Tolerant input parsing (`tools.md`'s alternate-forms table) | **Server** | It receives the raw args; the advertised schema stays strict on the wire |
| Normalisation telemetry | Server | Same place the normalising happens |
| Read-before-edit state | Server | Needs to see both file tools and `Bash` |
| Caps, truncation footers, spill-to-scratch | Server | They shape the result text, which is the server's output |
| Per-call classification (concurrency by path, `Bash` read-only-ness) | Server, with `beforeToolCallback` as a client-side gate | MCP annotations are per-tool, not per-call |
| Sanitising untrusted content from *third-party* MCP servers (Jira, Bitbucket) | **`afterToolCallback`** | Our servers can't sanitise someone else's output |
| Backstop caps on third-party results | `afterToolCallback` | Same reason |
| Turn budget, context high-water mark, final-turn nudge | **Agent loop** | Not a tool concern at all |
| `AskUser`/`Complete` terminating the run | Agent loop | The tool returns; the loop decides the run is over (`formats.md` §5) |
| Post-run `git status` cross-check | Agent loop / harness | Runs after the loop ends |

Two ADK details worth knowing for the last rows: `BaseTool` carries an
`isLongRunning` flag that MCP-derived tools don't set, and the Java MCP
path has no progress-notification plumbing (Python's does). Background
`Bash` therefore stays exactly as `tools.md` describes it — return a pid
and a log path, poll with ordinary commands — rather than becoming a
streaming tool.

---

## 8. What we would override, concretely

A short list, all small, in the order they'd be needed:

1. **`AbstractMcpTool.wrapCallResult`** (subclass): flatten
   `{"text_output": [{"text": X}]}` to a single-key payload, pass error
   text through unprefixed, never return `{}`, and skip the
   parse-text-as-JSON step entirely.
2. **`McpTool.runAsync`'s retry policy**: annotation-gated, so mutating
   tools don't silently re-run (§4) — with `Bash` annotated
   non-idempotent wholesale, since its read-only-ness is per-call and no
   annotation can express that. Server-side idempotency keys (§4,
   workaround 1) are the half of this that actually has to ship; the
   annotation gate is defence in depth.
3. **A run-scoped `BaseToolset`**: `getTools(ReadonlyContext)` returns the
   surface for this run's mode, pointing at the server started for it.
4. **`afterToolCallback`**: sanitiser and cap backstop for third-party
   servers.
5. Optionally **`beforeToolCallback`**: a client-side mirror of the
   server's own gates, for defence in depth on the write path.

Everything else — the tools themselves, their descriptions, their limits,
their result formats — is ours to write on the server side, unchanged from
the design.

---

## 9. To verify against a running stack

Nothing below is guesswork-free from source alone; each needs one real
call to settle, and each could change a decision above:

- Does the model backend **accept `parametersJsonSchema` containing
  `allOf`/`if`/`then`**, ignore it, or reject the declaration outright
  (§5)?
- How is the `Map<String, Object>` function response **actually
  serialised into the prompt** — how much escaping and envelope noise
  does the model really see, and does it change with model version (§2c)?
  This one now has a **budget to fail against** rather than being
  open-ended: `../agent-tool-result-transport.md` §1a measures
  JSON-escaping at ~1.11× on tag-framed prose and ~1.22× on the
  code-shaped payloads `Read` returns. Observed inflation materially
  above that means something is double-encoding — which is a bug to find,
  not a cost to accept. `eval.md` carries it as a measured quantity.
- **Does a JSON-RPC protocol error surface as an exception on the
  `callTool` path**, and therefore trip §4's `retryWhen`? The retry
  predicate is untyped, so this is the inference the
  errors-travel-as-`isError` rule rests on. If it holds, a protocol error
  costs three retries before reaching the model; if it doesn't, the rule
  still stands on the spec's audience argument alone, but with less
  urgency.
- **Which protocol version does the pinned stack actually negotiate?**
  §0 establishes the ceiling from source (`adk-java` pins MCP Java SDK
  1.1.2; the SDK's `ProtocolVersions` tops out at `2025-11-25`), but the
  negotiated value on a live connection is what decides it. Re-check on
  every `adk-java` bump — the pin is what will move first and silently.
- Does `Edit` still land first-try on files heavy in **tabs, quotes and
  backslashes** once the content has been through that envelope? This is
  the eval that decides whether §2c is a note or a problem.
- What is the **per-call timeout** on the MCP client path, and can it be
  set per tool? `Bash` legitimately runs for minutes;
  `SseServerParameters` defaults a five-minute SSE read timeout, and a
  stdio path may differ.
- Does a **failed tool call still consume a turn** in the agent loop, and
  does the loop's own error handling interact with the retry in §4?
- **Java/Python parity drift**: these two implementations already differ
  in MCP result handling. Re-read `AbstractMcpTool` on every ADK upgrade;
  it is the file most likely to change under us.
