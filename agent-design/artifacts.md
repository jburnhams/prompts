# Refs and artifacts: one address space, handles instead of payloads

**Status: central to v1, not deferred.** An earlier draft of this document
(same session) promoted the artifact store out of `future.md` on the
strength of Jira and PR attachments, but kept it narrow: attachments in,
images out, spill minting explicitly deferred. That was too small. The store
is not a place attachments go — it is one half of a single addressing
scheme that every read tool speaks, and the other half is that **anything
readable is named by a ref, whatever it is and wherever it lives.**

Two rules, and everything else here follows from them:

> **1. One address space.** A working-tree file, a file in another repo at a
> pinned SHA, a dependency's source, a Jira attachment, a past run's
> transcript and a stored tool result are all named the same way and read by
> the same tools. Only the scheme differs.
>
> **2. Bytes never enter context by default.** A non-write result that is
> non-trivial comes back as a **ref plus a preview of its shape**. Reads
> reduce; the payload stays out of the conversation until something asks a
> narrower question.

Background: `../agent-tool-result-transport.md` §5 (binary) and §7 (the six
decisions an artifact system forces, answered in §5 below). Image-specific
tooling: [`vision.md`](./vision.md).

---

## 1. Why this is a simplification, not an addition

The design was already growing a second, parallel addressing vocabulary
without noticing. `medium.md` §2e proposes `SearchSource`/`ReadSource` for
source outside the working tree, keyed by a `scope` string that is already a
URI in all but syntax — `repo:workspace/slug@ref`, `artifact:group:name`,
`class:com.example.Foo`, and later `run:<run-id>`. Alongside it,
`context-files.md` resolves every context tier to a `(source repo, ref)`
pair, and this document's earlier draft added `artifact://`.

Three vocabularies for the same idea. Unifying them **removes two tools**
rather than adding any:

| Was | Becomes |
|---|---|
| `ReadSource(scope, path, offset, limit)` | `Read({path: "git://acme/payments@a1b2c3d/src/Bill.java", …})` |
| `SearchSource(scope, pattern, glob, …)` | `Grep({pattern, path: "git://acme/payments@a1b2c3d"})` |

And it is what `tools.md`'s own granularity rule already required. That rule
says split a primitive when the split changes a **harness** answer —
permission class, destructiveness, concurrency safety, result shape.
`ReadSource` against `Read` changes none of the four: both are read-only,
both are non-destructive, both return file text in the same block. The only
difference is *where the bytes come from*, which is precisely what a scheme
encodes. Under the design's own stated rule, `ReadSource` should never have
been a separate tool; the ref system is what makes that visible.

**The honest cost**, stated because the medium.md entry raised it: a local
read is microseconds and a remote one is a network call, and collapsing them
hides that difference behind one tool name. Two mitigations, neither
perfect. The ref is self-describing — a model that wrote `git://` knows it
reached off-machine. And `Read`'s description keeps the ordering guidance
that entry already specified: local first, always; a remote scheme is for
code that *isn't* in the tree, never a second way to read code that is.
Latency is not a harness answer in the granularity rule's sense, but it is a
real property, and this is the trade being made rather than a cost being
denied.

---

## 2. The ref grammar

```
<scheme>://<locator>[:<selector>]
```

with a bare path (`src/parser/index.ts`) as the shorthand for the working
tree, which stays the overwhelmingly common case and gets the shortest form.

### 2a. Schemes are a closed set

| Scheme | Example | Immutable? | Resolver |
|---|---|---|---|
| *(bare path)* | `src/parser/index.ts` | no | working tree |
| `file://` | `file:///tmp/scratch/repro.py` | no | local filesystem, scratch dir included |
| `git://` | `git://acme/payments@a1b2c3d/src/Bill.java` | **yes at a SHA**, no at a branch | code host / search index |
| `dep://` | `dep://com.acme:billing:4.2.1/com/acme/Bill.java` | yes | build manifest → source jar |
| `artifact://` | `artifact://txt_04d1e8f2` | yes | run store |
| `run://` | `run://2026-08-14T09-22Z-7f3a/transcript` | yes | run archive |

**There is no `http://` or `https://` scheme, and that is the load-bearing
security property of the whole system.** A universal ref namespace sounds
like it hands the model a fetcher; it does not, because every scheme
resolves through a configured resolver with its own auth and its own scope
enforcement, and none of them takes a hostname from the model. The
consequences are worth spelling out because they are what make "any ref can
go into a tool call" safe:

- **The model can never name a network target.** `jira://…` is deliberately
  absent for the same reason: a Jira attachment is reachable only as
  `artifact://<id>`, an id the harness minted from a URL *it* recorded from
  the tracker's API. The model addresses the artifact, never the URL behind
  it (§6).
- **Resolvers enforce the run's existing scope.** `git://` resolves only
  within the repositories the run is authorised for; a ref naming another
  org's private repo fails as unauthorised, not as not-found, and never
  reaches a network call with credentials attached.
- **`dep://` versions come from the build manifest, never the model.** This
  is `medium.md` §2e's rule, preserved verbatim: the lockfile or POM already
  knows exactly what is on the classpath, so a coordinate without a version
  resolves deterministically and a coordinate *with* a version that
  disagrees with the manifest is an error.

### 2b. Selectors

One grammar, keyed to what the payload actually has, adopted from OMP's
`read` (the only harness in the collection that unified files, archives,
databases, documents and internal URIs behind one tool and one selector
syntax):

| Selector | Applies to | Meaning |
|---|---|---|
| `:120-260`, `:120-`, `:120` | anything with lines | inclusive line range |
| `:p4-6` | PDF | pages |
| `:Sheet2`, `:Sheet2!A1:D80` | spreadsheets | sheet, optionally a cell range |
| `:path/inside` | archives | a member |
| `:raw` | anything | bypass conversion (§3), return bytes as text |

A selector is optional everywhere. Its absence means "the whole thing,"
which is what triggers §4's spill when the whole thing is large.

### 2c. Immutability is a property of the ref, and it is visible

`git://acme/payments@a1b2c3d/...` is immutable; `git://acme/payments@main/...`
is not. `artifact://`, `dep://` and `run://` always are. This matters twice:
the resolver caches immutable refs indefinitely and mutable ones not at all,
and — the part the model needs — **a result block echoes the resolved ref,
so a read against `@main` reports back the SHA it actually got.** That is
the same discipline `formats.md` §8a already applies to paths (echo the
resolved path, not the string the model passed) and the same one
`context-files.md` applies to context tiers, extended to a namespace where
the difference between "what I asked for" and "what I got" can be a week of
commits.

---

## 3. `Read` is a converting reader

The second thing that collapses. An earlier draft gave images an
`extract_text` operation; that was too narrow by exactly the same margin as
the rest of it. **Extracting text is what `Read` does to anything that is
not already text**, and the format is a resolver detail, not a tool.

| MIME | What `Read` returns |
|---|---|
| text, source code | verbatim, `cat -n` line-prefixed (`formats.md` §8a) |
| PDF | extracted text per page, `:p4-6` to select; OCR when there is no text layer, and the block says which happened |
| xlsx / csv / tsv | the sheet as delimited text; `:Sheet2` selects, and the block names every sheet so a first read is a table of contents |
| docx | extracted text |
| html | reader-mode text; `:raw` for the markup |
| image | **OCR'd text plus dimensions** — reading a screenshot of a stack trace gives you the stack trace |
| archive | member listing; `:path/inside` reads one member |
| notebook | cells with outputs |
| unsupported binary | no content, shape only, and a note saying so |

Three rules keep this from becoming a lie:

- **Every conversion is announced.** The block says what it did — `converted
  from application/pdf, 14 pages, text layer` versus `…, no text layer, OCR`
  — because a model that cannot tell extracted text from OCR'd text cannot
  calibrate how much to trust an odd-looking identifier.
- **`:raw` always exists as the escape hatch**, for the cases where the
  conversion is the problem.
- **Conversion never silently loses structure without saying so.** A
  spreadsheet with formulas reports that it is showing values; a PDF with
  columns reports that reading order is best-effort.

`extract_text` therefore does not exist as a named operation anywhere in the
tool surface. It is the default behaviour of the one read tool, for every
scheme and every format.

---

## 4. Non-trivial results come back as refs

**Rule: any non-write tool result over `spill_threshold_chars` is stored as
an artifact and returned as a stub plus a preview.** This supersedes the
earlier draft's deferral of spill minting ("explicitly not v1"), and it
replaces — rather than sits alongside — the truncation-with-footer contract
in `tools.md`.

That replacement is a strict improvement, and the reasoning is worth
recording because it revises a decision that was made on measurement.
`README.md`'s decision log has a *Caps vs errors on oversized reads* row
resting on Claude Code's experiment #21841: truncating an explicit
over-limit read instead of erroring dropped tool-error rate but raised mean
tokens, because an error result costs ~100 bytes and a truncated one costs a
full page nobody asked for. That experiment compared two options. **A
spill-to-ref is a third that was not on the table**, and it dominates both:

| | Tokens now | Recovery call | Stable under change |
|---|---|---|---|
| Truncate + footer | a full page | `start_line: 2001` against a **mutable file** | no |
| Hard error | ~100 bytes | narrower call, nothing learned | n/a |
| **Spill to ref** | a preview you choose the size of | `artifact://txt_x:2001-4000` | **yes** |

The third column is the one that is genuinely new. Under truncation, a
paged read is a sequence of calls against a file that may change between
them; under spill, page two comes from an immutable snapshot of the thing
page one came from. That kills a race nobody in the collection handles.

**What stays from the old contract:** the footer discipline is unchanged in
spirit — every capped result still states what it showed, how much exists,
and *the exact next call* — the next call now just names a ref. And an
explicit request for more than a cap allows is still an error rather than a
silently shortened success.

**What does not spill:**

- **Writes.** `Edit` and `Write` return status. A ref is a handle on
  something to read; there is nothing to read back from an edit.
- **Small results.** Below the threshold, inline, as today. Most reads.
- **Anything read *from* the store.** §5.1's carve-out.

### 4a. The termination rule

The obvious hazard is the circular spill `agent-tool-result-transport.md`
§7c documents: spill a read to a store, the model reads the store, that
spills, forever. Claude Code disables spilling on `Read` entirely to avoid
it. The ref system needs a sharper rule than "exempt the read tool," because
here the read tool is *also* the store's reader.

> **A read carrying a selector never spills. A read without one may.**

Since every spill stub's recovery line names a *ranged* call
(`artifact://txt_x:2001-4000`), the recursion terminates in exactly one
step, by construction rather than by exemption. An unranged read of an
artifact that is over threshold returns the same stub again with its
preview — idempotent, not a loop — and the note says to narrow.

---

## 5. The six decisions

`agent-tool-result-transport.md` §7b sets out the six decisions an artifact
system forces. Answered in order.

### 5.1 Who mints, and when

| Path | Trigger | Decided by |
|---|---|---|
| **Ingest** | any attachment on a fetched issue, PR or comment | the harness, unconditionally, at fetch time |
| **Spill** | any non-write result over threshold | the harness, automatically (§4) |
| **Explicit** | a tool that knows it produced a durable payload | the tool |

**Ingest minting is unconditional and complete.** `FetchJira` and the PR
fetch return **every** attachment as a stub — not a selection, not only the
ones under a size cap. The model cannot choose what to look at before it
knows what exists, and a fetch that silently omits three of five attachments
produces an agent confidently reasoning about a ticket it has not seen.
Completeness is affordable because **minting is eager and fetching is
lazy**: a stub is built from the attachment metadata the issue API already
returns, so twelve attachments cost twelve stubs and zero downloads.

No harness in the collection mints on ingest, because none of them ingests a
tracker issue — `../agent-vision-multimodal.md` §16 records the clean
negative that no PR-review bot in the field handles images at all.

**Carve-out:** a read *from* the store never mints into it (§4a makes this
structural rather than a special case).

### 5.2 Naming and scope

`artifact://img_7f3a2b9c` — a three-letter kind prefix plus an opaque
suffix. MCP's guidance is that handles should be fully opaque, because
"handles that encode internal structure invite parsing or guessing"; that is
written for handles that are bearer tokens against a remote server, and
these are neither. Against it, the prefix lets the model tell from a bare
ref whether an image operation is legal, and lets a human read a run record.
Deliberate deviation, recorded as one.

The suffix is random rather than content- or origin-derived: content-derived
ids leak equality across artifacts (two tickets attaching the same
screenshot become linkable), origin-derived ids encode a URL the model
should be reading from the stub.

**Scope is the run.** Forge has no interactive session, so the run is the
only meaningful boundary, and a narrower default is safer for content from
outside the org (§7). One widening exists and is explicit: `persist` (§5.5).

### 5.3 What the stub says

The load-bearing decision. The stub replaces the payload, so it carries
enough to decide **whether to look** and **what to ask** — shape without
content. It reuses `formats.md` §8a's block grammar unchanged.

```
<artifact id="img_7f3a2b9c" kind="image" mime="image/png" bytes="284117"
          dims="2880x1620" name="checkout-broken-mobile.png"
          origin="jira:PROJ-1234#attachment-10021" author="c.nolan@example.com"
          created="2026-08-27T14:02:11Z" trust="internal" expires="run">
! Not loaded. Read artifact://img_7f3a2b9c for its text, or InspectImage to look at it.
</artifact>
```

```
<artifact id="txt_04d1e8f2" kind="text" mime="text/plain" bytes="3914004"
          lines="41022" origin="bash:call_7c21" trust="generated" expires="run">
1	  Compiling billing v4.2.1
2	  Compiling gateway v1.0.0
…
! Showed lines 1-40 of 41022. Read artifact://txt_04d1e8f2:41-500 to continue.
</artifact>
```

Every attribute earns its place: `kind` says which operations are legal;
`mime`/`bytes` say whether looking is affordable; `dims` is the attribute
that decides the call for an image (a 2880-wide screenshot will be
downscaled and its small text may not survive, so a crop is the right first
move); `lines` does the same job for text; `name` is the human's own label
and usually the best description available; `origin` is provenance *and* the
address to recover from; `author`/`created` decide trust and staleness;
`trust` is §7; `expires` is §5.5.

This is the notebook-cell precedent generalised
(`agent-tool-implementations.md` §5: *when a payload's existence and shape
are what the model needs and its contents are not, return an address and the
means to query it*).

### 5.4 The operation set

A handle whose only operation is "load it all back" is a deferral — the
tokens arrive one turn later. The operations must reduce, and after §2 and
§3 they are simply **the read tools**:

- `Read` with a selector — ranges, pages, sheets, members.
- `Grep` over a ref — including over an artifact, which is how a 41k-line
  build log gets useful.
- `InspectImage` — the only genuinely new tool, and only because `Read`'s
  reducing grammar (a line range) does not apply to pixels. `vision.md` §3.

Total new tool count for the whole system: **one**, against two removed
(§1).

### 5.5 Lifetime, and what expiry looks like

Default `expires="run"`. `expires="persist"` is set by the harness when an
artifact is referenced by something that outlives the run — named in a
`Complete` report's `evidence`, or posted through `AddComment`. The model
never sets it; it falls out of the reference, which keeps the store from
becoming a place things are kept just in case.

**Expiry is a recoverable, self-describing error, never a null** — MCP's
guidance, and right:

```
<error tool="Read" ref="artifact://img_7f3a2b9c">
! This artifact is no longer available (run-scoped, and this run did not mint it).
! Re-fetch its source with FetchJira issue_key="PROJ-1234" to mint it again.
</error>
```

The `origin` attribute is what makes that recovery statable, and is why it
is on the stub.

### 5.6 Whether loading is permanent

**No.** ADK's `LoadArtifactsTool` appends a loaded artifact to *that request
only*, never to conversation history — free on the target stack and, as
`agent-tool-result-transport.md` §7b says, materially better than a file
path. For text this is invisible (the model read a range; the range is in
the transcript because it is text). For images it is the decision that does
the most work: **a look is one turn by default**, which dissolves the
screenshot-accumulation problem `../agent-vision-multimodal.md` §8 found
nobody solving, rather than building an eviction pass for it. `vision.md` §4
covers pinning, the exception.

---

## 6. Fetching bytes

The one part with no usable prior art: every harness surveyed reads images
from local disk or a user's paste, while ours arrive over the network from
URLs requiring credentials — a credentialed fetch against a URL a third
party may have influenced, which is the textbook SSRF escalation. The
closest template is OpenHands's `image_inline.py`
(`../agent-vision-multimodal.md` §16), tightened because it carries no
credentials:

- **The model never names a fetch target.** Fetches are keyed by artifact
  id; the id maps to a URL the *harness* recorded at ingest from the
  tracker's own API response. This is why there is no `http://` scheme
  (§2a) — the property is structural, not a validation rule.
- **Host allowlist before connection**, credentials attached per-host and
  never carried across a redirect.
- **Redirects followed manually, revalidating each hop** against the host
  allowlist and an IP block-list (loopback, private, link-local, multicast,
  reserved), with a hop cap. Automatic redirect following is how a host
  check gets bypassed.
- **Size cap enforced on the response stream**, before decode.
- **Content type from magic bytes**, not the extension or the
  `Content-Type` header — Crush's finding
  (`../agent-vision-multimodal.md` §6): attachment pipelines routinely
  produce JPEG bytes named `.png`, and providers reject on mismatch. The
  stub's `mime` is the sniffed value, with a `!` note when it disagrees with
  the filename.

---

## 7. Trust

`trust` is set by the harness at mint time, never by the model:

| Value | Source |
|---|---|
| `internal` | attached by an authenticated member of the org |
| `external` | attached by a reporter outside the org, or an account the harness cannot resolve |
| `generated` | produced by this run — a spilled result, a screenshot |

Everything in the store is untrusted *content* in the sense the rest of this
design uses the word; `context-files.md` and `review.md` already nonce-wrap
repo-controlled text, and an attachment is strictly weaker than that. What
`trust` adds is a distinction the nonce cannot express, because **an image
cannot be nonce-wrapped at all** — a nonce works by being unforgeable in the
text stream, and pixels are not in it. Mitigations are specified in
`vision.md` §5.

For text artifacts the nonce still applies and is used: a spilled build log
from `Bash` is `generated`; a file read from `git://` at an unpinned branch
of a repo Forge does not own is `external`, and is framed accordingly.

---

## 8. MCP: central in the namespace, not in the block type

The artifact URI namespace is the addressing every Forge MCP tool speaks —
refs go into tool calls and come back in results, uniformly, which is what
makes the tool surface small.

**What does not change is the wire shape.** MCP has a content type designed
exactly for this — `resource_link`, a URI plus name and MIME with no
payload — and the design cannot use it. `adk.md` §2's table is explicit:
ADK-Java's `AbstractMcpTool.wrapCallResult` turns **any** non-`TextContent`
block into an error, and `resource` is named alongside `image` and `audio`.
`agent-tool-result-transport.md` §3f independently found `resource_link` to
be the *least* uniformly handled block type in the field, with two of seven
client projections dropping it silently.

So the standing rule holds unchanged: **one text block, no
`structuredContent`, never rely on anything but block zero.** A ref travels
as text inside the `<artifact>` stub. The model sees a URI; the protocol
sees a string. Nothing is lost — a `resource_link` the client drops is
strictly worse than a URI in text the model can read and pass back.

The one binding change remains the one already scoped in `adk.md` §2b:
subclassing `AbstractMcpTool` to convert `ImageContent` into a Gemini inline
part, needed only for `InspectImage`'s `view` (`vision.md` §7).

---

## 9. What this changes elsewhere

| Document | Change |
|---|---|
| `tools.md` | `Read` and `Grep` take a ref of any scheme, with selectors; `Read` becomes a converting reader (§3); the truncation contract becomes the spill contract (§4); `InspectImage` added |
| `medium.md` §2e | **Superseded.** `SearchSource`/`ReadSource` are not new tools; their `repo:`/`artifact:`/`class:`/`run:` scopes become `git://`/`dep://`/`run://` schemes on the existing tools. The entry's *substance* survives intact — phasing, the build-manifest resolution rule, the local-first ordering guidance, the no-silent-decompilation rule — as resolver requirements rather than tool designs |
| `formats.md` | `FetchJira.attachments`; `<artifact>` block (§8g); `Complete.evidence`; result blocks echo the **resolved** ref |
| `future.md` | The artifact-store entry is promoted; its two deferred decisions are answered here (§5.1, §4a) |
| `adk.md` | §2b's subclass is a v1 prerequisite for `view` only; §2's non-`TextContent` rule is why `resource_link` is unused (§8) |
| `context-files.md` | Its `(source repo, ref)` keying is the same namespace; the context service is a `git://` resolver by another name, and the two should share one resolver |
| `eval.md` | Metrics: fraction of results returned as refs, mean ref-follow depth (a ref nobody follows is a stub that should have been inline), and image-in-context count |
| `review.md` | §1c — attachments on the PR and its threads |

---

## 10. v1

**In:**

1. The ref grammar (§2), all six schemes, with `git://`/`dep://` resolvers
   phased as `medium.md` §2e already phases them.
2. `Read` as a converting reader (§3) — text, PDF, spreadsheets, docx,
   html, images-as-OCR, archives, notebooks.
3. Spill-to-ref for every non-write result over threshold (§4), replacing
   truncation-with-footer, with the selector termination rule.
4. Ingest minting for Jira and PR attachments, complete and unconditional.
5. `<artifact>` stubs, run-scoped lifetime, `persist` on reference,
   one-turn loads.
6. `InspectImage` (`vision.md`), the single new tool.
7. The fetcher (§6) and `trust` (§7).

**Out, with reasons:**

- **Cross-run artifacts** beyond `persist`. No user-scoped widening.
  Revisit with `medium.md` §3f's stateful re-review sessions, the first
  thing that genuinely wants an artifact to outlive a run.
- **Write-through refs.** No scheme is writable. `Edit`/`Write` take
  working-tree paths only, which keeps the "code Forge can read but does not
  own goes through a proposal, never an edit" rule of `medium.md` §4a
  structural rather than prompt-enforced.
- **`http(s)://`.** Not a gap — the absence is the security property (§2a).
  `WebFetch` remains a separate, separately-governed tool in `medium.md`
  §2d if and when it lands.
- **Decompiled sources under `dep://`.** `medium.md` §2e's rule stands: say
  no source jar exists rather than silently decompiling, because decompiled
  line numbers lie.
