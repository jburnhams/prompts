# Artifacts: a session store, and a stub in place of the payload

**Status: promoted from `future.md` into scope.** That entry gated the
artifact store on "a real case," predicting the `medium.md` §2e dependency
index would be the first. A better case arrived earlier and from a
direction the entry did not anticipate: **Jira and PR attachments**. A
ticket for a UX change carries a mockup; a bug report carries a screenshot
of the broken screen; a PR description and its review threads carry
before/after images. Forge is a hands-off agent whose entire input is a
ticket and a PR, so this is not an edge case — it is a routine property of
its two entrypoints, and today both fetch tools drop it silently.

Attachments are also a *harder* case than a large query result, in a way
that settles the design rather than complicating it. A 40k-row result has a
useful prefix, so truncate-and-narrow is a real recovery. **A binary has no
useful prefix.** There is no first 10% of a PNG. So the store cannot be an
overflow backstop bolted onto the caps in `tools.md`; it has to be the
primary representation for a class of payload, minted before the model sees
anything.

Background and precedents: `../agent-tool-result-transport.md` §5 (binary,
and the one rule that matters) and §7 (artifacts, the six decisions, the two
traps). Image-specific tooling built on this substrate: [`vision.md`](./vision.md).

---

## 1. The rule

> **Bytes never enter the model's context by default. A reference plus the
> payload's shape does. Tools operate on the reference as easily as on a
> path.**

Three corollaries that decide most of what follows:

- **A tool that produces a binary returns a stub, always** — not "when
  large," not "if a flag is set." There is no size at which inlining a PNG
  is the right answer, because base64 as text costs 2.5–3.6× the bytes and
  is unreadable (`agent-tool-result-transport.md` §1a; the field's best
  measurement of getting this wrong is a single 146 KB PNG costing 106,356
  tokens against 39,199 for the same image handled natively — 2.7×, for
  identical visual output).
- **Looking is a separate, explicit act** with its own cost, its own tool
  and its own record in the run log. This is the same reasoning
  `tools.md` applies to `Bash`: the expensive, stateful thing gets its own
  name.
- **A reference is as usable as a path.** If the model has to think about
  where an artifact lives, or learn a second grammar to read one, the store
  has failed. §4 is mostly about making `artifact://` behave like a path.

---

## 2. The six decisions, answered

`agent-tool-result-transport.md` §7b sets out the six decisions an artifact
system forces. Answering them in order is the fastest way to specify this.

### 2.1 Who mints, and when

**Three minting paths, and the first is the new one.**

| Path | Trigger | Who decides |
|---|---|---|
| **Ingest** | any binary or oversized field on a fetched issue, PR, or comment | nobody — the harness, at fetch time, unconditionally |
| **Spill** | any tool result over `spill_threshold_chars` | the harness, automatically (`tools.md`'s existing rule) |
| **Explicit** | a tool that knows it produced a durable payload | the tool |

**Ingest minting is unconditional and complete.** `FetchJira` and the PR
fetch return **every** attachment as a stub — not a selection, not the ones
that look relevant, not only the ones under a size cap. The model cannot
choose what to fetch before it knows what exists, and a fetch tool that
silently omits three of five attachments produces an agent that confidently
reasons about a ticket it has not seen. The cost of completeness is
bounded and small: a stub is ~40 tokens, so a ticket with twelve
attachments costs ~500 tokens to enumerate and nothing to ignore.

This is a deliberate split from the field. Every harness surveyed in
`../agent-vision-multimodal.md` mints on *overflow* or on a *user paste*;
none mints on *ingest*, because none of them ingests a tracker issue. §16 of
that doc records the clean negative: no PR-review bot in the collection
handles images in PR bodies or comments at all.

**The circular-spill carve-out applies.** `Read` is already exempt from
spilling (`tools.md`: spilling a read to a file the model then reads back is
circular). The exemption extends to any tool reading the store —
`Read` over `artifact://`, and every `InspectImage` op. A tool whose job is
reading artifacts must never mint one.

### 2.2 Naming and scope

```
artifact://img_7f3a2b9c
artifact://txt_04d1e8f2
artifact://bin_9a55c130
```

**A three-letter kind prefix plus an opaque suffix.** The MCP spec's
guidance is that handles should be fully opaque, because "handles that
encode internal structure invite parsing or guessing." That guidance is
written for handles that are *bearer tokens against a remote server*; these
are neither — the store is run-local and the id grants nothing an authorised
caller doesn't already have. Against that, the prefix buys two things worth
more than the risk: the model can tell from a bare reference in its own
earlier reasoning whether an `InspectImage` call is even legal, and a human
reading a run record can too. Deliberate deviation, recorded as one.

The suffix is random, not derived from content or origin. Content-derived
ids would leak equality across artifacts (two tickets attaching the same
screenshot become linkable), and origin-derived ids would encode a URL the
model should be reading from the stub instead.

**Scope is the run, not the session.** ADK's `ArtifactService` offers
`(app, user, session)` with a `user:` prefix widening to all of a user's
sessions. Forge has no interactive session and no user in the loop, so the
run is the only meaningful boundary — and a narrower default is the safer
one for content that arrives from outside the org (§5). One widening exists
and it is explicit: `persist` (§2.5).

### 2.3 What the stub says

The load-bearing decision. The stub replaces the payload, so it must carry
enough to decide **whether to look** and **what to ask** — shape without
content. It uses `formats.md` §8a's existing block grammar unchanged:
tag-framed, attributes carry facts, `!` lines carry notes.

```
<artifact id="img_7f3a2b9c" kind="image" mime="image/png" bytes="284117"
          dims="2880x1620" name="broken-checkout.png"
          origin="jira:PROJ-1234#attachment-10021" author="c.nolan@example.com"
          created="2026-08-27T14:02:11Z" trust="internal" expires="run">
! Not loaded. InspectImage id="img_7f3a2b9c" to look at it.
</artifact>
```

Every attribute earns its place:

| Attribute | Why the model needs it |
|---|---|
| `kind` | which operations are legal |
| `mime`, `bytes` | whether looking is affordable; whether it will be downscaled |
| `dims` | **the one that decides the call.** A 2880×1620 screenshot will be downscaled and its small text may not survive; a region crop is the right first call. Without dimensions the model cannot tell a full-page screenshot from an icon |
| `name` | the human's own label, which is usually the best available description — `broken-checkout.png` says more than any metadata the harness could synthesise |
| `origin` | provenance, and the address to re-fetch from if the artifact is gone |
| `author`, `created` | who attached it and when — decides trust (§5) and staleness ("the screenshot predates the fix") |
| `trust` | `internal` \| `external` \| `generated` — see §5 |
| `expires` | `run` \| `persist` |

For a text artifact the shape attributes change and nothing else does:
`kind="text" lines="41022" bytes="3914004" encoding="utf-8"`, with the first
page of content inside the block rather than a `!` note. This is the
notebook-cell precedent generalised (`agent-tool-implementations.md` §5:
*when a payload's existence and shape are what the model needs and its
contents are not, return an address and the means to query it*).

**Stubs appear in three places**, all of them existing structures:

1. **The task envelope.** `formats.md` §1a's `<ticket>` block carries the
   `FetchJira` output; attachment stubs ride inside it, so a coding run
   knows on turn one what images the ticket has. Same for §1b's
   `<pull_request>`.
2. **Tool results.** A `FetchJira` or PR fetch made mid-run returns them
   inline.
3. **Nowhere else.** A stub is minted once per artifact per run; a second
   fetch of the same issue returns the same ids rather than re-minting, so
   the model's earlier references stay valid.

### 2.4 The operation set

A handle whose only operation is "load it all back" is a deferral, not a
solution — the tokens arrive one turn later. The operations must *reduce*.

**Text-shaped artifacts cost zero new tools.** OMP's answer is the one to
copy and `future.md` already committed to it: `artifact://<id>` is a URI
scheme `Read` understands, taking the same selector grammar as a path.
`Read` already has a path parameter, a range concept, a paging contract and
a truncation-notice discipline; an `artifact:` scheme reuses all four.

```json
{"files": [{"path": "artifact://txt_04d1e8f2", "start_line": 4000, "end_line": 4200}]}
```

**Image-shaped artifacts need a second door, and that is the whole
justification for a new tool.** `Read`'s reducing operation is a line range,
and an image has no lines. The operations that reduce an image are a region
crop, a text extraction and a delegated question — none of which fit a path
plus two integers. `InspectImage` is specified in [`vision.md`](./vision.md)
§3.

That is the tool-count accounting in full: **one new tool**, admitted
because the existing one's reducing grammar provably does not apply, which
is the bar `tools.md` §1 sets.

### 2.5 Lifetime, and what expiry looks like

**Default `expires="run"`.** The run is the scope (§2.2), and a hands-off
agent has no later session to serve.

**`expires="persist"` is set by the harness when, and only when, an artifact
is referenced by something that outlives the run** — an evidence artifact
named in a `Complete` report, or an image posted through `AddComment`. The
model never sets this; it falls out of the reference. That keeps the store
from becoming a place things are kept "just in case," which is how artifact
stores rot.

**Expiry is a recoverable, self-describing error, never a null.** MCP's
guidance is unusually concrete here and it is right: a call against an
expired or missing handle is a tool execution error that says so and names
the recovery.

```
<error tool="InspectImage" id="img_7f3a2b9c">
! This artifact is no longer available (run-scoped, and this run did not mint it).
! Re-fetch its source with FetchJira issue_key="PROJ-1234" to mint it again.
</error>
```

The `origin` attribute on the stub is what makes that recovery statable, and
is the reason it is on the stub at all.

### 2.6 Whether loading is permanent

**No — and this is the decision that does the most work.**

ADK's `LoadArtifactsTool` appends a loaded artifact **to that request only**;
it is never written into conversation history. `agent-tool-result-transport.md`
§7b calls this "a materially better contract than a file path," and for
images it is better still, because it dissolves a problem the research
found nobody solving: in `../agent-vision-multimodal.md` §8, screenshots
accumulate in every harness that takes them, and only Gemini CLI evicts
anything — with a bespoke supersession pass that exists solely because its
snapshots were written into history in the first place.

So: **a look is one turn by default.** The image is attached to the request
that asked for it and is gone from the next one, leaving the stub and
whatever the model wrote down. No supersession machinery, no eviction pass,
no accumulation. Pinning is the exception, requested explicitly, and
`vision.md` §4 says which role justifies it.

Two consequences worth stating plainly:

- **The model must write down what it saw.** A one-turn look that produces
  no notes is a wasted call. The tool description says so, and the
  system-prompt workflow reinforces it.
- **Re-looking is legal and cheap to reason about.** Because a look is not
  permanent, "look again at region X" is an ordinary call rather than a
  confession that the first one was wasted.

---

## 3. The two traps, handled

Both are documented in `agent-tool-result-transport.md` §7c and both apply
here.

**The circular spill** — handled by the carve-out in §2.1: no tool that
reads the store may mint into it.

**The stub that outlives its referent** — the more subtle one. A stub is a
pointer in the transcript whose target has an independent lifetime, which is
the same object as the dedup stub that produced the production deadlock in
`agent-tool-implementations.md` §7. Three rules keep it safe:

1. Artifacts are keyed to the run record, and a run's artifacts live exactly
   as long as the run does. There is no window in which a stub is valid and
   its referent is not, within a run.
2. Compaction may remove a stub from context; it never removes the artifact.
   A model that has forgotten an artifact exists re-fetches its source, gets
   the same id back (§2.3), and continues.
3. The failure direction that remains — a reference the model reconstructs
   from memory after compaction ate the stub — fails loudly per §2.5, with
   the re-fetch call named. It never silently returns nothing.

---

## 4. Fetching: how bytes get into the store

The one part of this with no usable prior art in the collection, because
every harness surveyed reads images from local disk or from a user's paste.
Ours arrive over the network, from URLs that require credentials.

**That is a credentialed fetch against a URL that a third party may have
influenced**, which is the textbook SSRF escalation. The closest prior art
is OpenHands's `image_inline.py` (`../agent-vision-multimodal.md` §16), and
it is a good template that has to be tightened because it does not carry
credentials:

- **Never fetch a URL the model supplied.** Fetches are keyed by artifact
  id, and the id maps to a URL the *harness* recorded at ingest from the
  tracker's own API response. The model cannot name a target, so it cannot
  redirect one.
- **The URL must match the configured tracker/forge host** before any
  connection, and credentials are attached per-host, never carried across a
  redirect.
- **Redirects are followed manually, revalidating each hop** against both
  the host allowlist and an IP block-list (loopback, private, link-local,
  multicast, reserved), with a hop cap. Following redirects automatically is
  how the host check gets bypassed.
- **Size cap before decode**, enforced on the response stream rather than
  after buffering.
- **Content type is decided by magic bytes, not by the extension or the
  `Content-Type` header.** From Crush (`../agent-vision-multimodal.md` §6):
  attachment pipelines routinely produce JPEG bytes named `.png`, and
  providers validate the media type against the bytes and reject on
  mismatch. The `mime` attribute on the stub is the sniffed value; when it
  disagrees with the filename, the stub says so in a `!` note.
- **Fetch is lazy, minting is eager.** Ingest mints a stub from the
  tracker's attachment *metadata* — which the issue API already returns, so
  it costs no extra request. Bytes are fetched on first `InspectImage` or
  `Read`. A ticket with twelve attachments therefore costs twelve stubs and
  zero downloads unless the model looks.

That last point is what makes "return all attachments, always" affordable,
and it is why the answer to the user-facing question — *should the fetch
tools return everything?* — is yes without qualification.

---

## 5. Trust, and why it is an attribute of an artifact

`trust` takes three values and is set by the harness at mint time, never by
the model:

| Value | Source | Posture |
|---|---|---|
| `internal` | attached by an authenticated member of the org | untrusted *content*, ordinary provenance |
| `external` | attached by a reporter outside the org, or by any account the harness cannot resolve to a member | untrusted content, hostile-capable provenance |
| `generated` | produced by this run (a screenshot Forge took) | self-produced |

Everything in the store is untrusted content in the sense the rest of this
design uses the word — `context-files.md` and `review.md` already nonce-wrap
repo-controlled text, and an attachment is strictly weaker than that. What
`trust` adds is a distinction the nonce cannot express, because **an image
cannot be nonce-wrapped at all.** A nonce works by being unforgeable in the
text stream; pixels are not in the text stream. Instructions rendered into
an image are invisible to every text scanner in the field
(`../agent-vision-multimodal.md` §12 — the longest browser-safety block
anywhere lists only text heuristics: hidden text, Base64, DOM attributes).

So the mitigations available are different in kind, and they are specified
in `vision.md` §5: provenance stated in the sentinel text that frames the
image, image-derived text confined to the untrusted envelope, and — the
strong one — the vision sub-model as a containment boundary, since it holds
no tools to be hijacked into using and returns text the parent treats as
data.

---

## 6. What this changes elsewhere in the design

| Document | Change |
|---|---|
| `future.md` | The artifact-store entry is promoted out of "gated on a real case"; the two decisions it deferred (automatic vs explicit minting, stub survival under compaction) are answered in §2.1 and §3 |
| `tools.md` | `Read` accepts `artifact://<id>` as a path; the spill carve-out extends to artifact-reading tools; `InspectImage` joins the tool set (spec in `vision.md`) |
| `formats.md` | New `<artifact>` block in §8; §2's `FetchJira` output gains an `attachments` array; §1a/§1b envelopes carry stubs inside `<ticket>`/`<pull_request>` |
| `adk.md` §2b | The note "should be revisited before any work that assumes multimodal tool results" is now due. Gemini 3+ accepts images in `functionResponse.parts`; ADK-Java's `AbstractMcpTool.wrapCallResult` still errors on any non-`TextContent`. **Prerequisite: subclass it to convert `ImageContent` into an inline part.** One class, already scoped there |
| `eval.md` | Two metrics: fraction of runs that looked at an attachment they should have, and mean images-per-run held in context (which the one-turn default should keep near zero) |
| `review.md` | Review mode inherits attachment stubs on the PR and on comment threads — including re-review threads, where "here's what it looks like now" is exactly where a screenshot lands |

---

## 7. v1 versus direction

**v1 is the substrate plus images, and nothing else.**

- Ingest minting for Jira and PR attachments, complete and unconditional.
- The `<artifact>` stub block.
- `artifact://` as a `Read` path scheme for text artifacts.
- `InspectImage` with the three ops in `vision.md` §3.
- Run-scoped lifetime, one-turn loads, `persist` on reference.
- The fetcher in §4.

**Explicitly not v1:**

- **Spill minting.** `tools.md`'s caps and truncation notices have not yet
  been shown to fail, and `future.md`'s argument stands: an artifact store
  filling with spilled `Bash` output is the unused-escape-hatch surface.
  Ingest minting alone justifies the store; spill can follow evidence.
- **Cross-run artifacts.** No `persist` beyond the reference rule above, and
  no user-scoped widening. Revisit when `medium.md` §3f's stateful
  re-review sessions land, which is the first thing that genuinely wants an
  artifact to outlive a run.
- **Non-image binaries as anything but opaque.** A PDF attachment gets a
  stub and no operations in v1 — it is legal to have an artifact the model
  can only see the shape of. PDF page extraction is the obvious second
  `kind` and is deferred until a ticket demonstrably needs it.
- **An audience channel.** Still separable, still tracked in `future.md`.
  `Complete` and `AddComment` remain the user-facing route, and an evidence
  artifact reaches a human by being referenced there.
