# Local compute: what Forge takes from the local-compute research

Source: [`../agent-local-compute.md`](../agent-local-compute.md),
[`../data-agents/hyperparam/`](../data-agents/hyperparam),
[`../code-mode/`](../code-mode) and
[`../cloudflare-agents/`](../cloudflare-agents).

Admitted under the standing rule: **an item earns a place only if it
changes a contract the design already has.**

This pass is mostly **amendments**, not additions. Three of the four
things it looked like the research would contribute turned out to be
already specified — and one thing it would have contributed is
explicitly forbidden by a decision this design already made and gave
reasons for. §3 records that audit, because the near-misses are more
useful than the adoptions.

---

## 1. The one sentence this pass reduces to

> **A ref's lifetime must be at least as long as the lifetime of the
> claims that depend on it.**

`artifacts.md` §5.5 already gets the first hop right: `expires="persist"`
is set by the harness when an artifact is *referenced by something that
outlives the run* — named in a `Complete` report's `evidence`, or posted
through `AddComment` — and **the model never sets it; it falls out of the
reference.** That is exactly the right mechanism.

It is one hop, and a provenance graph is not.

---

## 2. Adopted into v1

Six changes. **None adds a tool or a scheme.** Five amend existing
contracts; one records a decision the design had left open.

### 2a. `persist` propagates along provenance

**Amends `artifacts.md` §5.5.** The current rule persists what is
referenced. The amendment:

> **`persist` is transitive along `produced_by` and `inputs`.** When the
> harness marks an artifact `persist`, it marks that artifact's
> provenance closure `persist` too.

This fixes a bug in [`data.md`](./data.md) §2f, which is mine and which
this audit surfaced. That section's completion gate requires that *"every
`table://` among them must have a `produced_by` that resolves"* — and it
is checked at the end of the run, when everything is still alive. Under
the one-hop rule, the cited table then persists and its inputs do not, so
**the gate verifies a property that the lifetime rule immediately stops
preserving.** A week later the report cites a table whose derivation has
expired, and the gate that was supposed to make the run reproducible
passed on a run that is not.

Transitivity is the minimum fix and it is cheap: the closure is a walk
over refs minted during the run, which §2f already performs. It is
garbage collection with `Complete.evidence` and `AddComment` bodies as
the roots, and the provenance edges as reachability — a model that is
well understood, rather than a new lifetime concept.

**What it does not do** is widen scope. Cross-run artifacts beyond
`persist` stay out of v1 per `artifacts.md` §10, for the reason given
there: gated on a use case, not on substrate.

### 2b. Sliding expiry, on the `persist` tier only

**Amends `artifacts.md` §5.5.** `expires="run"` is unchanged — a run is
short and last-use expiry within it means nothing. The amendment applies
one tier up:

> A `persist` artifact expires **after a configurable period from last
> use**, not from mint. Any resolution counts as a use, including one
> that reads only the stub. Minting a derived artifact counts as a use of
> its inputs.

The second sentence is the one that matters. If only byte-reads refresh
the clock, a ref that is passed between tools without being read can
expire mid-chain, and the failure is silent until something tries to
resolve it. If minting does not count as a use of its inputs, §2a's
closure decays from the leaves inward.

Sliding rather than fixed because the access pattern is the signal: a
table someone keeps coming back to is live, and a dead end is not. This
is the mechanism `../cloudflare-agents/operations.md` records as
`expirePaused({maxAgeMs})` — anything that waits needs a reaper — applied
to storage instead of to approvals.

### 2c. A table's expiry error carries its shape

**Extends `artifacts.md` §5.5.** That section is already right that
**expiry is a recoverable, self-describing error, never a null**, and its
worked example names the recovery through `origin`:

```
<error tool="Read" ref="artifact://img_7f3a2b9c">
! This artifact is no longer available (run-scoped, and this run did not mint it).
! Re-fetch its source with FetchJira issue_key="PROJ-1234" to mint it again.
</error>
```

That works because an ingested attachment has a source to re-fetch. **A
derived table does not.** Its `origin` is a `bash:` call from a run that
is over; re-running it is not recovery, and may not be reproducible at
all if the upstream data has moved.

So for `kind="table"`, the expiry error keeps the shape and the
provenance rather than only the address:

```
<error tool="Read" ref="table://tbl_9c4e21a0">
! Expired 2026-11-04 (persist, last used 2026-09-12). The rows are gone; the shape is not.
! 1840293 rows, 7 cols: order_id int64 · region string · ordered_at timestamp
!   · revenue float64 (422 null) · currency string · is_refunded bool · channel string (737408 null)
! produced_by artifact://txt_0a19bb4c (expired) · inputs table://tbl_1188ef40 (expired), file:///data/regions.csv
! Not re-derivable: its inputs have expired too.
</error>
```

A few hundred bytes, and it buys three things the current error cannot:
**"expired" is distinguishable from "never existed"**, which is otherwise
a confusing failure six months later; the audit question *what was this
number computed from* stays answerable after the bytes are gone; and
**whether re-derivation is possible is stated** rather than left for the
model to discover by trying.

The `persist`/`run` distinction and the last-use date are in the text for
the same reason `artifacts.md` §2c echoes resolved refs: the difference
between *what I asked for* and *what I got* should never be silent.

### 2d. A local cache tier, keyed on the ref

**Extends `artifacts.md` §6** (fetching bytes). New, and it does not
disturb anything above it.

> Where Forge runs in a browser, resolved artifact bytes may be cached
> locally. **The cache is never authoritative.** Its key is the ref
> itself. A local hit still registers a use against the store (§2b).

Three constraints, each from an existing decision or a checked fact:

- **The cache key is the ref, not a content hash.** `artifacts.md` §5.2
  rules out content-derived ids because *"content-derived ids leak
  equality across artifacts (two tickets attaching the same screenshot
  become linkable)"*. A content-addressed cache reintroduces exactly that
  equality, inside the browser, where §7's `trust` boundary is weakest.
  Refs are immutable and unique, so they are a perfectly good key and
  the leak does not arise.
- **Immutability makes it correct for free.** No revalidation is ever
  needed — an artifact never changes. The only failure mode is a miss.
- **Local is a cache because the browser enforces it.** Default web
  storage is *best-effort* and evicted under pressure;
  `navigator.storage.persist()` opts out but is granted on vendor
  heuristics (WebKit ties it to Home-Screen-app status). Treating browser
  storage as authoritative would be a bug waiting for a low-disk laptop,
  so this is the only honest model rather than a preference.

The keep-alive on a local hit is what stops the two tiers disagreeing:
without it, the store GCs an artifact the tab still holds, and the model
successfully reads a ref locally and then gets an expiry error passing
the same ref to a remote tool.

### 2e. The data tool does not join; refs do the reducing

**Amends [`data.md`](./data.md) §2c.** That section gave `table://` a
`:sql:` selector and assumed cross-table queries were fine. They are not,
and the reason is not the one you would guess.

> **`:sql:` binds exactly one table.** A join across two `table://` refs
> is not expressible in the data tool. Joining happens locally, over
> artifacts already fetched.

The DoS argument for this is the weaker half: a single-table query DoSes
perfectly well (`SELECT *`, a non-sargable predicate, an `ORDER BY` on an
unindexed column), and the things that actually bound cost — caps,
timeouts, and walking the plan before executing — are needed either way.
What is true is that **one table is easy to bound and a join is vastly
harder**, so a join raises the *variance* of cost past what a cap can
hold.

The correctness argument is the strong one. A join failure is **silent**:
fan-out on a duplicated key inflates every downstream `SUM`; an inner
join on a nullable key drops rows; a `VARCHAR`/`BIGINT` key mismatch
coerces. All of them execute and return a plausible number. Schema
linking is a top error class in the text-to-SQL literature (~27.6% on
Spider 2.0; incorrect table selection 22.4%/35.0% of *semantic* errors on
BIRD/Spider) — though note that two recent papers are specifically about
**pervasive annotation errors in those benchmarks**, so the direction is
sound and the magnitudes are not.

And fetching separately makes the failure visible for free, which is what
`../agent-data-analysis.md` §9d records that **no harness does**: if the
inputs are 1,840 and 12 rows and the local join produces 4,201, the
fan-out is a number in a stub at the moment it happens. One large query
destroys that evidence before anyone can look at it.

**The push-down this costs is recovered by one addition**, and it fits
the ref system rather than working around it:

> An artifact ref may appear as a **filter operand**:
> `:sql:SELECT … WHERE customer_id IN table://tbl_1188ef40#customer_id`
>
> The harness resolves the ref to a key list and inlines it. The list
> length is checked against a cap **before** anything is issued; over the
> cap is a refusal naming the cap and telling the model to narrow the
> first fetch.

That is a client-driven semi-join. It gets the selectivity that makes a
400M-row fact table tractable, without the model writing a join, and it
is bounded in the way a join is not — because the key count is a number
the harness can see in advance. What it deliberately does not cover is
many-to-many fact-to-fact, which is the case you least want written
blind.

**This is a start-closed decision, not a permanent one.** The relaxation
path, in order: joins on a declared primary key, then on any indexed
column, each gated on the plan walk being able to bound the result.

### 2f. Focused tools, with Code Mode named as the escape hatch

The design had left this open, and the research settles it in the
direction the existing surface already points.

> The data tool surface is **specific tools** — list, describe, fetch —
> not a general `execute(code)`. Code Mode is not in v1.

The deciding argument is the **UDF seam**. A model-backed function inside
a query is registered by the harness and merely *named* by the model:

```javascript
executeSql({ query: 'SELECT name, AI_SCORE(description) AS score FROM products',
             functions: { AI_SCORE: { apply: async (t) => completions(…) } } })
```

So the capability surface inside the query language is exactly what the
deployment chose to expose, and **no sandbox is required, because no
model-authored code runs.** Against that, a general `execute` buys
expressiveness and immediately costs the iframe, the CSP, the
unpreemptable `while(true)`, and — per Cloudflare's own SDK — the ability
to gate on approval at all on the AI-SDK path.

It also keeps a property `artifacts.md` §8 depends on: with focused
tools the harness sees *what the model asked for* as structured
arguments. A program is opaque until it runs.

The corollary, adopted with it: **a model-backed UDF is a spend
ceiling, not a feature.** `LIMIT 5` really is five inferences, and the
unbounded query is textually identical to the cheap one. The cap belongs
where the plan is walked, before execution.

---

## 3. Already in the design, and one thing it forbids

The most useful part of this pass. Four things the research suggested
adopting, checked against what is already specified:

| Research suggests | Status |
|---|---|
| Artifacts cited by a completed run should outlive it | **Already `artifacts.md` §5.5.** `expires="persist"` on reference, set by the harness, never by the model. Adopted here only as *transitive* (§2a) |
| Expiry should leave something behind rather than a dangling ref | **Already §5.5.** *"Expiry is a recoverable, self-describing error, never a null."* Extended here only for the derived-table case, where `origin` cannot state recovery (§2c) |
| The store should be durable so refs survive the process | **Already §5.5.** *"The backing store is durable object storage … `persist` genuinely persists rather than meaning 'until the container goes away'."* |
| Cache and dedupe artifacts by content hash | **Forbidden, with reasons.** §5.2: *"content-derived ids leak equality across artifacts (two tickets attaching the same screenshot become linkable)"*. §2d keys on the ref instead |

Three of four were already right, which is the argument for doing this
audit before writing rather than after.

---

## 4. Promoted and deferred

**To `future.md`, with a trigger:** **Code Mode**, as the escape hatch
for what focused tools cannot express — reshaping beyond SQL, joining a
query result to a non-tabular tool's output, multi-step orchestration.
The trigger is the first task where a data run needs two tool results
combined in a way no selector expresses. If it lands, the sandbox is the
tier-2 shape (`../agent-local-compute.md` §4): an opaque-origin iframe
with `default-src 'none'` in an injected CSP, providers as function
parameters rather than globals, and a Worker inside the frame so a
synchronous loop is terminable. And per
`../code-mode/cloudflare.md`, approval inside a program is a solved
problem via a durable tool-call log and abort-and-replay — which is
substantial machinery this design does not have and should not build
speculatively.

**To `future.md`, unchanged in substance:** the pure-TS engine as the
`table://` resolver. `../data-agents/hyperparam/`'s `AsyncDataSource` is
the interface `data.md` §2a specified abstractly, in forty lines, with
two honest pushdown booleans (`appliedWhere`, `appliedLimitOffset`). It
is an implementation note, not a design change — the ref contract is
already substrate-neutral, which is the whole point of §2a — but it is
the concrete thing to build against, and worth recording so the next
person does not re-derive the interface.

**Deferred:** running Forge's loop in a browser at all. §2d specifies the
cache tier so the artifact contract is ready for it; nothing else in this
design assumes a server, except `Bash`, which assumes a machine.

---

## 5. Considered and rejected

**A separate `Describe` or `Profile` tool for tables.** Rejected again,
for the reason `data.md` §5 gave: `Read` is already a converting reader
and a profile is what reading a relation should produce.

**Content-addressed artifact ids, for cache dedup.** §3. The cache gets
the property it wanted (a stable key) from the ref itself.

**Writable refs, so a local join could write `table://` directly.**
`artifacts.md` §10 rules out write-through refs to keep "code Forge can
read but does not own goes through a proposal, never an edit" structural.
A derived table is minted by the harness on spill (`data.md` §2d), which
is the existing path and does not need a writable scheme.

**Persisting everything by default.** Tempting given durable storage, and
it defeats the sentence §5.5 exists to enforce: *"which keeps the store
from becoming a place things are kept just in case."* §2a widens
persistence along a graph the design already tracks; it does not remove
the condition.

**`navigator.modelContext` / WebMCP.** Assessed and parked with re-check
triggers — [`../code-mode/webmcp.md`](../code-mode/webmcp.md). It solves
a browsing problem, not an internal-tooling one.

---

## 6. What this does not change

- **The scheme set stays closed at seven** (six, plus `table://` from
  `data.md` §2a). No `http(s)://`, and the absence is still the security
  property.
- **The tool surface stays at eleven.** Nothing here adds a tool.
- **MCP wire shape** — `artifacts.md` §8's rule is unchanged: one text
  block, no `structuredContent`, never rely on anything but block zero.
- **`trust` semantics** — §7 unchanged. A cached artifact keeps the
  `trust` it was minted with; caching is a transport optimisation and
  never a trust upgrade.
- **Run scope as the default.** §2a and §2b operate on the `persist`
  tier. Cross-run widening beyond `persist` remains out of v1.

---

## 7. Supersessions and decision rows

**All of these are applied in the target documents**, not left as a
patch against them — this document is the argument, and the amended
sections are the design. Each target cross-links back to the section
here that changed it.

| Document | Change |
|---|---|
| `artifacts.md` §5.5 | `persist` becomes **transitive** along `produced_by`/`inputs` (§2a); **sliding expiry from last use** on the `persist` tier, with "any resolution counts, and minting counts as a use of inputs" (§2b); the expiry error for `kind="table"` carries shape and provenance (§2c) |
| `artifacts.md` §6a | a local cache tier, keyed on the ref, never authoritative, a hit registers a use (§2d) — a new subsection under **6. Fetching bytes** |
| `artifacts.md` §7 | one sentence: a cached artifact keeps the `trust` it was minted with (§6) |
| `data.md` §2c | **`:sql:` binds one table**; joins are not expressible; an artifact ref may appear as a filter operand with a pre-issue cap (§2e) |
| `data.md` §2f | the provenance gate is unchanged, but is only *sound* given §2a — recorded here because the gap was in this design, not in the research |
| `tools.md` | the data surface is focused tools, not `execute(code)` — in **What is deliberately *not* configurable**, since it is a contract other things depend on rather than a tunable; and the model-backed UDF spend ceiling, in the implementation contract next to the existing cap rules (§2f) |
| `future.md` | Code Mode with its trigger and sandbox tier; the pure-TS resolver as the implementation note (§4) |
| `eval.md` | metrics: expired-ref-hit rate on `persist` artifacts (a high rate means the sliding window is too short); local cache hit rate; fan-out ratio on local joins |
| `README.md` | decision rows for §2a, §2e and §2f |
