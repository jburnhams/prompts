# What this design takes from the Cloudflare Agents SDK

Source: [`../cloudflare-agents/`](../cloudflare-agents) (11 files),
[`../code-mode/cloudflare.md`](../code-mode/cloudflare.md).

Admitted under the standing rule: **an item earns a place only if it
changes a contract the design already has.**

This fold is late. The research folder has existed through three passes
and `agent-design/` referenced it four times, all incidentally — so the
largest single source read in this collection had never been asked the
question every other source was asked. That is what this document is
for.

Cloudflare is a **different kind of source** from the rest. Every other
harness here is a process with a filesystem; this one is a Durable
Object with SQLite, and the interesting consequences are the ones where
that substrate forced an answer to a question the process-shaped
harnesses can leave implicit. Where a finding is *only* true because of
Durable Objects it is recorded and not adopted — §5 has those.

---

## 1. The one sentence this pass reduces to

> **A capability the model is told about and a capability the model
> actually has should be derived from the same fact.**

Cloudflare gets this structurally in three separate places, and each
time the mechanism is the same: *do not write down what the agent can
do; compute it from what is wired up.* `agents/context` derives the
prompt block **and** the tool surface from one provider declaration, so
"the checks are structural, not nominal" and an agent with only
read-only blocks gets no mutation tools at all. `run_skill_script` is
registered only if a script runner exists. `_buildThinkCapabilityBlock`
assembles the capability paragraph from the turn's actual `ToolSet`.

This design has the inverse problem in a specific place, and §2a fixes
it.

---

## 2. Adopted into v1

Five changes. **None adds a tool.** Four amend existing contracts; one
adds a bounded fallback to a tool that currently has none.

### 2a. The capability paragraph is computed from the tool set

**Amends [`system-prompts.md`](./system-prompts.md), and settles the
open half of `README.md`'s *per-model prompt variation* row.**

That row adopts Codex's shape — one canonical prompt per mode, with
**capability-conditional subtraction by heading** as the upgrade path —
and prices the cost honestly: *"headings become an interface … so a
rename silently stops removing anything."* Cloudflare ships the other
mechanism, and it does not have that failure:

```ts
const hasWorkspaceTools = ["read","write","edit","list","find","grep","delete"]
  .some((toolName) => toolNames.has(toolName));
const hasExecuteTool = toolNames.has("execute");
const hasFetchTools = [...toolNames].some((name) => name.startsWith("fetch_"));
```

> - Do not claim access to capabilities that are not exposed as tools in this turn.

The amendment:

> **The prompt's capability statements are generated from the turn's
> tool set, not written into the prompt text.** A capability line
> appears when its tool is present and is absent otherwise. The prompt
> body states behaviour — how to decide, what `done` means, how to
> report — and never enumerates the tool surface in prose.

Three reasons this is the better half of the pair, and one reason the
Codex mechanism still stays:

- **There is no name to drift.** A set-membership test against tool
  names is checked by the same thing that registers the tool. A heading
  match is checked by nobody.
- **It fixes a live inconsistency rather than a hypothetical one.**
  `tools.md`'s *"The tool set is configuration, not a constant"* is
  already true of this design — a deployment may remove a tool — and
  the prompts currently describe the eleven as though they were fixed.
  A deployment that drops `Task` today gets a prompt that still talks
  about delegating.
- **The closing line is the actual safety property.** "Do not claim
  access to capabilities that are not exposed as tools in this turn" is
  the one-line version of a failure this collection keeps finding: an
  agent that narrates an action it has no tool for. It costs nothing
  and it belongs in all three entrypoint prompts.
- **Subtraction by heading is still the mechanism for behavioural
  sections** — a planning section, a destructive-actions section — which
  are not keyed on a tool's presence and cannot be generated from one.
  The two compose: generate the capability paragraph, subtract
  behavioural sections. `README.md`'s row is narrowed, not replaced.

**Prefix stability is the cost, and it is already paid.** Anything
generated per turn sits in the cached prompt prefix. Cloudflare handles
this with `freezeSystemPrompt()` and a skill-set `fingerprint`; here the
tool set is fixed for a run by construction, so the generated block is
constant within the run and the prefix is stable where it matters.

### 2b. `Edit` gains a whitespace-normalised retry, and it flags itself

**Amends [`tools.md`](./tools.md)'s `Edit`.**

`Edit` is exact-match-or-fail, which `../agent-tool-implementations.md`
§4 shows is the near-universal choice and which this design adopted for
the right reason. The finding is that Cloudflare's *isn't* the fuzzy
matching its docs advertise — it is a strictly narrower fallback with
three guards ([`../cloudflare-agents/implementation.md`](../cloudflare-agents/implementation.md)
§1):

```ts
function normalizeWhitespace(s: string): string {
  return s.replace(/[ \t]+/g, " ").replace(/\r\n/g, "\n");
}
```

> **On zero exact matches only, `Edit` retries once with runs of spaces
> and tabs collapsed and CRLF normalised. The retry must also match
> uniquely — two normalised matches is a refusal, not a choice. A
> successful normalised edit is reported as such in the result.**

Why this is worth the complexity, when exact-match-or-fail is otherwise
a good rule:

- **It cannot override a successful exact match**, because it only runs
  when there were none. The exact path is untouched.
- **The failure it fixes is the harness's, not the model's.**
  `formats.md` §8a already normalises line endings on read and restores
  them on write, and `tools.md` §*Line numbering* makes `Read`'s output
  the thing `Edit` matches against. A model that copies a span out of a
  `Read` result and gets a whitespace mismatch is failing on a
  round-trip artefact, and retrying is cheaper than another `Read`.
- **It is bounded in a way real fuzzy matching is not.** No edit
  distance, no scoring, no threshold to tune. The set of strings that
  match after normalisation is small and describable.
- **The ambiguity guard is the load-bearing part.** Normalisation can
  merge two previously-distinct regions, and `"ambiguous"` refuses
  rather than picking. Without it this would be the silent corruption
  the earlier write-up wrongly accused it of being.

**The residual risk is stated, because it is real.** Normalisation
collapses indentation, so in Python, YAML or a Makefile a span can
match at a different nesting depth. Two consequences follow, and both
are adopted with the rule: the result **must** carry the flag so it is
countable, and `eval.md` gets the counter (§4). If normalised edits
correlate with review findings, the fallback goes.

This also slots into an existing rule rather than sitting beside it:
`tools.md`'s repair ladder (*"Repairs are ordered, and the order is part
of the contract"*) is exactly where a normalised retry belongs — it is
one more ordered repair, after the exact attempt and before the error.

### 2c. Aged media is evicted to a ref, and the marker is the ref

**Amends [`artifacts.md`](./artifacts.md) §5.6 and
[`vision.md`](./vision.md) §4.**

§5.6 decides that **a look is one turn by default** — a loaded artifact
is appended to *that request only*, never to conversation history — and
says this "dissolves the screenshot-accumulation problem
`../agent-vision-multimodal.md` §8 found nobody solving, rather than
building an eviction pass for it."

That is right for artifacts *this design mints*, and it does not cover
the case where a large image arrives inside a **tool result** and is
therefore already in the transcript. `vision.md` §4's pinning exception
is the other way in. Cloudflare has both cases and solves them the same
way ([`implementation.md`](../cloudflare-agents/implementation.md) §2):

```ts
return `[evicted ${media}${bytes} bytes; preserved at ${path}]`;
```

The amendment:

> **A transcript payload that has aged past the recent window is
> replaced, in place, by a ref and its metadata.** The bytes are stored
> first; the replacement states media type, size and the ref that
> resolves it. **Bytes are never dropped**, only moved. Text parts are
> never evicted.

This is not a new mechanism — it is the ref system pointed at the
transcript instead of at tool results, and the marker is an
`artifacts.md` stub in all but name. Four rules come with it, each
lifted because the source states the failure it prevents:

- **There is no drop-the-bytes mode.** Cloudflare deprecated its own
  option into a documented no-op rather than leaving a config key that
  loses data. An evicted payload that is merely gone turns a recoverable
  read into a null, which `artifacts.md` §5.5 forbids for artifacts and
  should equally forbid here.
- **The retention window is clamped against its own misconfiguration** —
  never shorter than the window the model replays at full fidelity, "so
  a misconfigured low value can never strip content the model still
  sees". Same shape as `tools.md`'s refused-path list, which a
  deployment may extend and may never empty.
- **The marker format is a wire contract.** Old markers must keep
  resolving after a storage change; Cloudflare states byte-identity
  across its own replatform as a requirement.
- **Text is never evicted: it is the conversation.** The rule that keeps
  this from becoming lossy compaction by another name.

And the bounded walk comes with it — `MAX_WALK_DEPTH`, "so hostile tool
output cannot recurse forever" — which is the same rule the base64
redactor uses and which `tools.md`'s sanitisation path needs stated
once: **a sanitiser that can be hung by its own input is a denial of
service in the safety layer.**

### 2d. Two caps, on two axes, and a header allowlist

**Amends `artifacts.md` §6 (fetching bytes) and `tools.md`'s cap rules.**

§6 is this design's most carefully specified security surface and it
already has the important half: the model never names a fetch target,
ids map to harness-recorded URLs, host allowlist, manual redirects with
per-hop revalidation, size cap on the stream before decode, magic-byte
content typing. Cloudflare's fetch tool
([`implementation.md`](../cloudflare-agents/implementation.md) §7) agrees
on all of it and adds three things §6 does not have:

> - **A transport cap and a context cap are separate numbers.**
>   `maxBytes` bounds what is downloaded; `maxModelChars` bounds what
>   reaches the model. A payload may be fully fetched and largely
>   withheld.
> - **The model may set an explicit allowlist of request headers**, and
>   nothing else. Default: `accept`, `accept-language`, `range`.
> - **Redirect policy is a three-value enum** — `allowlisted`,
>   `same-origin`, `none` — not a boolean.

The first is the one this design actually needs. `tools.md`'s cap rules
are written as a single ceiling per call, and §6's "size cap enforced on
the response stream, before decode" is a transport bound doing duty for
both. They are different decisions: a 900 KB PNG that must be fetched
and must not be serialised into context is the normal case for
`InspectImage`, and one number cannot express it.

The header allowlist is small and buys something specific: `range` on
the list is what makes a **bounded partial fetch** expressible at all,
which is the fetch-side equivalent of `Read`'s offset/limit. Nothing
else in this collection names which headers a model may set.

Two more details adopted with them, both cheap:

- **Misconfiguration fails loudly.** Cloudflare refuses to construct the
  tool with neither an allowlist nor a binding, rather than defaulting
  to open. `tools.md`'s not-configurable list should say the host
  allowlist may be narrowed and may never be empty — the same shape as
  the refused-path rule already there.
- **The block event is as observable as the served one** — `onEvent`
  fires once per fetch, "success or failure/block". A blocked fetch that
  logs nothing is the case you most want to see.

And §6's block-list bullet gains two implementation traps rather than a
rewrite, because getting this wrong is silent
([`implementation.md`](../cloudflare-agents/implementation.md) §8):
`startsWith("fe80")` matches only `fe80::/16` and lets `fe81::`–`febf::`
through (the correct test is `/^fe[89ab][0-9a-f]/`), and IPv4-mapped
IPv6 has a hex form the WHATWG URL parser does not canonicalise, so both
`::ffff:10.0.0.1` and `::ffff:a00:1` must be handled. Plus the policy
that should be explicit: **a URL that fails to parse is blocked**, not
passed through.

### 2e. Compaction needs a second budget, and a degradation says what it did not damage

**Amends `generative.md` §2b's refusal vocabulary; the compaction half
lands in `future.md`.**

Two small things, both from failure modes this design has not written
down. The first has no home in v1 — **this design has no compaction at
all**, which was checked rather than assumed — so it is recorded with
the `future.md` item it would belong to, where it is the non-obvious
half of building one.

> **A compaction pass that frees nothing must not be retried.**
> Proactive and reactive compaction carry **separate** budgets: the
> reactive one bounds retries of a failed turn, the proactive one bounds
> compactions within a single step loop.

The reason is the whole finding, and it is one line in Cloudflare's
source: *"a no-op compaction would repeat on every step, so the cap
stops the guard from compacting … on each one."* A threshold-triggered
compaction that cannot shorten the history is an infinite loop, and the
retry budget for a *failed turn* does not bound it because the turn
never fails. `../agent-context-compaction.md` catalogues triggers and
does not have this.

Carried with it, because it is the reason the two layers exist: a
between-turns compaction check cannot save a long tool-heavy turn that
overflows mid-flight. If this design ever adds compaction, it needs both
a between-turns trigger and an in-flight one, and the in-flight one
should key on **reported usage** rather than on a provider's error
string.

Second, a wording rule for `generative.md` §2b's refusal vocabulary:

> **A degradation states what it did *not* damage.**

Cloudflare's hydration failure reads *"The agent is starting with an
empty in-memory message view; **persisted history is untouched.**"* The
existing rule says a refusal names what happened and what to do; this
adds the clause that stops a recoverable degradation being read as data
loss. It costs a sentence and it is the difference between a model
retrying and a model giving up.

---

## 3. Already in the design

Checked before writing, in the discipline [`local.md`](./local.md) §3
established. Cloudflare converges with this design in six places, which
is worth recording because convergence on a different substrate is
evidence:

| Cloudflare | Already here |
|---|---|
| `read/write/edit/list/find/grep/delete/bash` as the built-in surface | `tools.md`'s eleven. Same surface, reached on a Durable Object instead of a process |
| Skills: catalog line per skill, body on `activate_skill` | `context-files.md` §12 + `generative.md` §2e — read instructions, execute code, never `Read` the executable into context |
| `SkillRunContext` — a script gets a capability object, `tools` resolves only what the runner was given | The same calling convention as `artifacts.md`'s refs: a callee reaches what it was handed, not what it can name |
| Closed error vocabularies (`FetchErrorCode`, the skills refusals) | `generative.md` §2b's closed `refusal` codes |
| Every failure returns a value, never throws — "so the agent loop is never broken by an exception" | `tools.md`'s *"errors are instructions"* and *"they travel as tool-execution errors, never as protocol errors"* |
| Approval that outlives the connection — "even from a dashboard with no live socket" | `AskUser`: suspend the run, resume on reply. `../cloudflare-agents/think.md` reaches the same conclusion from the opposite direction, with durable machinery this design leaves to the harness |

The last row is the strongest convergence in the collection and worth
stating as such: two designs, one on Durable Objects and one on a
hands-off pipeline, independently concluded that **pausing for a human
is a storage operation, not a held connection.**

---

## 4. Promoted and deferred

**To `eval.md`, adopted now:** a **normalised-edit counter** — the
fraction of `Edit` calls that succeeded only after whitespace
normalisation (§2b), split by file type. This is the kill switch for
§2b, and the split matters: a rise concentrated in Python or YAML is the
indentation risk showing up, where a rise spread evenly is a `Read`
round-trip problem worth fixing upstream instead. Also an
**evicted-bytes counter** and the re-read rate on evicted refs (§2c) — a
high re-read rate means the retention window is too short and eviction
is costing more than it saves.

**To `future.md`, with triggers:**

- **Non-destructive compaction — summaries as read-time overlays.**
  Cloudflare stores a compaction as a row (`from_message_id`,
  `to_message_id`, `summary`) and applies it when reading the path, so
  the originals survive
  ([`implementation.md`](../cloudflare-agents/implementation.md) §5).
  Every compaction in `../agent-context-compaction.md` is a destructive
  rewrite. The trigger is this design acquiring compaction at all;
  the note is that if it does, **overlays are the shape to build**,
  because reversibility is nearly free at write time and impossible to
  retrofit.
- **The idempotency ledger for consequential tools.** Cloudflare's
  `action()` adds four things to a tool — idempotency by stable key,
  inline *or* durable approval, per-turn authorization grants, and
  delivery metadata "without changing what the model sees". The first is
  the one this design will need: `AddComment` is its only outbound write
  and `adk.md` §4 already notes transport-level retries re-execute a
  tool. `tools.md`'s tool-call-id-derived spill filename is the
  half-measure that exists today. The trigger is a second outbound
  write, or the first duplicate comment in production.
- **A tool-precedence order.** Cloudflare documents seven tool sources
  and states that later overrides earlier, with extension tools
  namespaced and client tools winning — *"no other source in this
  collection documents a tool-precedence order"*. v1 has one source, so
  there is nothing to order. The trigger is the second source: MCP
  tools, a skill surface, or per-deployment additions. Record now that
  the answer is **an explicit order plus namespacing for the least
  trusted source**, because the alternative is discovering the order
  from a collision.

**Deferred, with the reason:** `beforeToolCall` returning a
`ToolCallDecision` (deny / rewrite / allow) evaluated on every entry
path. The mechanism is right and the guarantee — *"hooks fire on every
turn regardless of entry path"* — is the thing that makes a policy
unbypassable. This design has one entry path per mode today, so the
guarantee is free and the hook is unnecessary machinery. It becomes live
the moment a second way into a turn exists.

---

## 5. Considered and rejected

**Durable-Object-shaped durability**: fibers, hibernation-surviving
turns, `getAgentByName` as an address, dynamic agents as facets. All
genuinely good and all **properties of the substrate**, not of the
design. `adk.md` is where substrate capabilities belong, and Forge's
hands-off archetype gets the same property a different way: a run that
suspends and exits has nothing to keep alive.

**A2A as a delegation shape.** `../cloudflare-agents/interop.md` is
right that it is a fourth shape after in-process, stateless `Task` and
dynamic agents — delegation across an organisational boundary, where you
learn the far agent's capabilities by fetching a document. It is also a
*discoverability* decision, and `README.md`'s posture is that Forge is
invoked by a pipeline, not discovered by peers. No use case, so no
adoption; recorded here rather than in `future.md` because the trigger
would be an organisational change, not a technical one.

**x402 / an agent that can pay.** The finding transfers and the
mechanism does not: `wrapFetchWithPayment(fetch)` makes the
least-gated primitive an agent has into a spending one, with no approval
in the path. This design's answer is already structural — there is no
`http(s)://` scheme and the model never names a fetch target
(`artifacts.md` §2a, §6) — so the primitive cannot be wrapped. Worth
keeping as the sharpest statement of why that absence is a security
property: **if an agent can pay, `fetch` is a destructive tool, and
nothing in the wrapper's shape says so.**

**Code Mode over raw CDP**, and Code Mode generally. Already settled by
[`local.md`](./local.md) §2f and held in `future.md` with a trigger. The
CDP variant is the most interesting version of it — the action space is
the protocol rather than a verb set — and it sharpens rather than
changes that decision: the cost of a fixed verb set is real, and it is
still the right trade for a design whose harness must see what was asked
for before it runs.

**Client tools identified by the absence of an `execute` function.**
Elegant — *"a schema with no implementation is, by definition, something
someone else implements"* — and it does not compose downward: a
delegated child cannot use them, because there is no socket to a browser
from inside a headless sub-agent turn. Forge's runs are headless by
construction. Recorded as a design idea worth remembering, with no place
to put it.

---

## 6. What this does not change

- **The tool surface stays at eleven.** Nothing here adds a tool. §2b
  amends `Edit`'s repair ladder; §2d amends caps; §2c amends what
  happens to a payload already in the transcript.
- **The scheme set stays closed.** §2c's eviction marker is an existing
  `artifact://` ref, not a new scheme.
- **Exact-match-or-fail remains `Edit`'s contract.** §2b adds an ordered
  repair after the exact attempt fails, which `tools.md` already has a
  mechanism for; it does not make matching fuzzy.
- **The prompt body is still hand-authored per mode.** §2a generates the
  capability paragraph only. Behaviour, the completion audit, and the
  persistence rule are prose and stay prose.
- **`artifacts.md` §5.6's one-turn default is unchanged.** §2c covers
  the payload that arrived in a tool result and is therefore already in
  history — the case §5.6 does not reach.

---

## 7. Supersessions and decision rows

All applied in the target documents, each cross-linking back.

| Document | Change |
|---|---|
| `system-prompts.md` | the capability paragraph is generated from the turn's tool set, with the "do not claim access to capabilities not exposed as tools" line in all three entrypoint prompts (§2a) |
| `tools.md` | `Edit` gains a whitespace-normalised retry as an ordered repair, with an ambiguity guard and a self-flagging result (§2b); transport cap and context cap separated (§2d); a model-settable header allowlist; the host allowlist joins the may-narrow-never-empty list (§2d) |
| `artifacts.md` §5.6 | aged transcript payloads are evicted to a ref, bytes never dropped, text never evicted, marker format a wire contract (§2c) |
| `artifacts.md` §6 | two caps on two axes; redirect policy as a three-value enum; the two IPv6 block-list traps and fail-closed-on-parse-failure (§2d) |
| `vision.md` §4 | pinning interacts with eviction: a pinned image is exempt from the aged-media pass (§2c) |
| `generative.md` §2b | a degradation states what it did *not* damage (§2e) |
| `future.md` (compaction item) | the two-budget rule and the two-trigger rule land here rather than in a compaction section, because **this design has none** — checked, not assumed (§2e) |
| `eval.md` | normalised-edit rate split by file type; evicted bytes and re-read rate on evicted refs (§4) |
| `future.md` | compaction overlays, the idempotency ledger, tool-precedence order — each with a trigger (§4) |
| `README.md` | decision rows for §2a, §2b and §2d; the per-model-prompt-variation row is **narrowed**, not superseded — generation for capabilities, subtraction for behavioural sections |
