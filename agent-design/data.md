# Data analysis: what Forge takes from the data-agent research

Source: [`../agent-data-analysis.md`](../agent-data-analysis.md) and the
thirteen harnesses in [`../data-agents/`](../data-agents).

Admitted under the same rule as [`generative.md`](./generative.md): **an
item earns a place only if it changes a contract the design already
has.** Everything else is noted and left out.

The headline: **a data-analysis entrypoint costs this design zero new
tools.** That is not a coincidence and not a brag — it is what
[`artifacts.md`](./artifacts.md) bought when it made refs the universal
address space and `Read` a converting reader. A table is a thing at a
ref; profiling it is a read; querying it is a read with a selector;
charting it is a validating write. Four operations the design already
specifies, pointed at a new `kind`.

What it does cost: **one new scheme, one new artifact kind, three new
selectors, one new validating write path, and a third entrypoint.**

---

## 1. The one sentence the pass reduces to

Four harnesses, built by four teams for four products, independently
enforce the same boundary:

| | Probe (invisible, free, uncommitted) | Commit (visible, sequential, durable) |
|---|---|---|
| jupyter-mcp | `execute_code` | `insert_execute_code_cell` |
| marimo | the kernel scratchpad | `cm.get_context()` |
| Data Formulator | inspection tools | actions |
| Claude.ai container | `/home/claude` | `/mnt/user-data/outputs` + `present_files` |

Generalised, and adopted as a standing rule:

> **The probe/commit rule.** A call that only gathers information is
> invisible to the destination, uncommitted, and safe to make in any
> number. A call that changes what a human will see is visible, durable,
> and taken one at a time. The two must be different calls, and the model
> must be able to tell which is which from the tool name alone.

Read against the existing surface, Forge was already implementing it and,
as with the structured-representation rule, did not know it was an
instance of anything:

| Forge tool | Probe or commit | Already right? |
|---|---|---|
| `Read`, `Grep`, `List`, `FetchJira` | probe | yes |
| `Bash` | **either, and the tool cannot tell** | **no — §2c** |
| `Edit`, `Write` | commit (to the branch) | yes |
| `AddComment`, `AskUser`, `Complete` | commit (to a human) | yes |
| `Task` | probe — stateless, results return to the orchestrator only | yes, and this is why it is parallel-safe |
| `InspectImage` | probe | yes |

The one row that fails is `Bash`, and it fails in the way that matters
for data: `python analyse.py > /dev/null` and `python
write_report_to_the_pr.py` are the same call shape. §2c is the minimum
fix; the rest is left to the permission layer, which is where it belongs.

Two things follow from the rule that are worth stating because the
sources make them concrete:

**Probes must be genuinely free of consequence, not merely undisplayed.**
marimo's scratchpad is a *shallow copy* of kernel globals, and the skill
is honest that `df.drop(..., inplace=True)` still escapes. A probe
channel that can mutate is a commit channel with bad labelling.

**Commits are sequential because of epistemics, not concurrency.** Data
Formulator argues it rather than asserting it: *"each action's result
shapes your next decision — the chart you'd draw next depends on what
this one reveals — so choosing two at once would make the second a blind
guess."* Forge's `AddComment` and `Complete` are already once-per-run or
once-per-finding; the rule now says why.

---

## 2. Adopted into v1

Six changes. **None adds a tool.** Five are extensions to contracts in
`artifacts.md` and `tools.md`; one is a new entrypoint that reuses the
existing core.

### 2a. `table://` joins the closed scheme set

`artifacts.md` §2a's scheme table gains one row:

| Scheme | Example | Immutable? | Resolver |
|---|---|---|---|
| `table://` | `table://tbl_9c4e21a0` | **yes** | run store, columnar backing |

A `table://` ref names **an immutable, columnar, schema-carrying
relation**. Physically it is a parquet file in the run store; nothing
above the resolver depends on that, and a deployment backed by a
warehouse can resolve one to a temporary table instead.

It is a separate scheme from `artifact://` rather than a `kind` under it
because `artifacts.md` §2c makes immutability a property of the *scheme*
and §5.4 makes the legal operation set a property of the `kind`. A table
supports operations (`:sql:`, `:cols:`) no other artifact supports, and
the model should be able to see that from the ref itself without reading
a stub.

**Why a scheme and not just "a parquet file in scratch".** Three things
the file path cannot carry, all of which the sources found the hard way:

- **The schema, without opening it.** `agent-data-analysis.md` §6a: the
  overwhelmingly common question about a table is *what is in it*, and the
  answer is O(columns), not O(rows). A path answers neither.
- **Exact row count.** Vanna's `metadata` carries `row_count` exactly
  while the model sees ten rows, which is what lets the model choose
  between "show me" and "aggregate first". A truncated preview alone
  cannot support that choice.
- **Immutability.** `artifacts.md` §4's strongest argument is that page
  two comes from an immutable snapshot of what page one came from. A
  scratch file a later `Bash` call can overwrite kills that.

### 2b. A `table` artifact kind, with its own stub

`artifacts.md` §5.3's stub grammar, extended. Compare the existing `text`
and `image` stubs; the attributes that differ are the ones a relation has
and a blob does not.

```
<artifact id="tbl_9c4e21a0" kind="table" mime="application/vnd.apache.parquet"
          bytes="18442119" rows="1840293" cols="7"
          origin="bash:call_7c21" produced_by="artifact://txt_0a19bb4c"
          inputs="table://tbl_1188ef40,file:///data/regions.csv"
          trust="generated" expires="run">
  order_id     int64      1840293 non-null, 1840293 distinct
  region       string     1840293 non-null, 14 distinct: EMEA, NA, APAC, …
  ordered_at   timestamp  1840293 non-null, 2024-01-01 … 2026-08-31
  revenue      float64    1839871 non-null (422 null), min 0.00 max 184220.55 mean 271.18
  currency     string     1840293 non-null, 3 distinct: USD, EUR, GBP
  is_refunded  bool       1840293 non-null, 4.1% true
  channel      string     1102885 non-null (737408 null), 6 distinct: web, app, …
! 1840293 rows. Read table://tbl_9c4e21a0:rows:1-20 for rows, or :sql:<query> to aggregate.
</artifact>
```

Three decisions in that block.

**The default projection is column summaries, not rows.** This is btw's
distinction, and it is the single most transferable piece of guidance in
the whole pass:

> `"skim"` is the most information-dense format … To glimpse the data
> column-by-column, use `"glimpse"`. This is particularly helpful … when
> pairings of entries in individual rows aren't particularly important …
> To get a json representation of the data, use `"json"` … particularly
> helpful when the pairings among entries in specific rows are important
> to demonstrate.

Column summaries answer *what is in this table* in O(columns) — type,
null count, cardinality, range, top categories. Rows answer *what does a
record look like*, with intra-row co-occurrence intact, and are needed
rarely and in small numbers. Forge makes the cheap one the default and
the expensive one a selector, which is the same shape as `Read`'s
line-window default.

**Null counts are shown, always, even when zero.** `1839871 non-null (422
null)` and `1840293 non-null` are both stated. A model shown only
non-null counts has to subtract to notice the problem; a model shown
"422 null" notices. This is the cheapest available defence against the
class of silent error `agent-data-analysis.md` §9a catalogues, and it
costs one clause per column.

**`produced_by` and `inputs` are new attributes, and they are the
provenance fix.** `artifacts.md` §5.3 already has `origin`
("provenance *and* the address to recover from"), which for a `bash:`
result names the call. That is not enough for a table: the thing a human
re-running the analysis needs is **the code, and what it read**.
`produced_by` is a ref to the script or query; `inputs` is the refs it
consumed. Together they make every table in a run a node in a graph whose
leaves are source data — which is §2f's completion gate, and the answer
to `agent-data-analysis.md` §12's open problem 5.

**What is deliberately not in the stub:** partition or sort order. It is
real information (§11c of the topic doc lists it) and it is backend
specific; adding it to the grammar now would be specifying against one
resolver. Deferred to `future.md`.

### 2c. Three selectors, and one of them is SQL

`artifacts.md` §2b's selector table, extended. All three apply to
`table://` only.

| Selector | Meaning |
|---|---|
| `:rows:1-20` | rows by position, as delimited text |
| `:cols:region,revenue` | restrict the summary (or the rows) to named columns |
| `:sql:SELECT region, sum(revenue) FROM t GROUP BY 1 ORDER BY 2 DESC LIMIT 10` | a query over this table, bound as `t` |

`:sql:` is the important one and it needs defending, because it looks
like a tool smuggled in as a string.

**It is a reducing operation, which is the entire criterion in
`artifacts.md` §5.4**: *"A handle whose only operation is 'load it all
back' is a deferral."* For text the reducing operations are a line range
and `Grep`. Neither reduces a relation usefully — `Grep` over a parquet
file is meaningless, and rows 1–20 of 1.8 million answer nothing. The
reducing operation for a relation is a query. Without it, `table://`
would be a handle you can only page through, which is the deferral the
section warns against.

**The result of `:sql:` is itself a ref**, minted under §2d, so an
aggregation that returns 14 rows comes back inline and one that returns
400,000 comes back as a stub. Same rule, no special case.

**It terminates.** `artifacts.md` §4a's rule is *"a read carrying a
selector never spills"* — but `:sql:` can legitimately produce something
large. The rule is amended to the narrower, correct form:

> **A read carrying a selector never spills, except `:sql:`, whose
> result is a new ref and is therefore subject to §4 like any other
> result.**

The recursion still terminates in one step by construction: the stub of a
`:sql:` result names `:rows:` and `:sql:` on the *new* ref, and an
unranged re-read returns the same stub idempotently.

**Read-only is structural, not a check.** The query binds one immutable
input as `t` and can only produce a new ref. There is no connection to
write to, no table to drop, and no statement type to validate — which is
a stronger position than Postgres MCP's `pglast` allowlist because it
does not depend on getting the allowlist right. Where a deployment
resolves `table://` to a live warehouse rather than a file, the allowlist
becomes necessary again and Postgres MCP's is the reference
implementation: **allowlist statement node types, and allowlist
functions**, because `SELECT pg_read_file('/etc/passwd')` is a perfectly
good `SelectStmt`.

### 2d. Tabular results spill to `table://`, not to text

`artifacts.md` §4 says any non-write result over `spill_threshold_chars`
is stored and returned as a stub. One clause is added:

> **A spilled result whose payload is tabular — a query result, a CSV or
> parquet file the run produced, a dataframe a script serialised — is
> minted as `table://`, not `artifact://`.** The harness decides by
> format, not by the model's say-so.

Why this is not cosmetic: a 400,000-row query result spilled as
`artifact://txt_…` is recoverable only by line range. The same result
spilled as `table://` is queryable. The difference is whether the next
question costs a scan-and-parse in a `Bash` call or one selector.

The detection is deliberately mechanical — a parquet magic number, a CSV
that parses with a stable column count, a JSON array of flat objects.
Anything ambiguous stays `artifact://`, because a wrong guess is worse
than no guess: a `table://` stub asserts a schema, and an asserted schema
that is wrong is exactly the kind of confident-and-incorrect input the
rest of the design works to avoid.

### 2e. `Write` gains a validating path for chart specs

`generative.md` §2b established a closed refusal vocabulary on every
validating write path. Chart specs get one.

**The rule, in the data-mode prompt and enforced by the write path:**

> **Forge does not draw.** A visualization is written as a declarative
> spec citing a `table://` ref. Writing a `.png`, `.jpg` or `.svg`
> produced by a plotting library is refused.

A file written to `*.vl.json` is validated at write time against the
Vega-Lite schema **and against the columns of the `table://` refs it
cites**, and refused with a closed vocabulary:

| Refusal | Meaning |
|---|---|
| `spec_invalid` | not valid against the chart schema |
| `unknown_field` | an encoding names a column the cited table does not have |
| `no_data_ref` | the spec embeds literal rows instead of citing a ref |
| `type_mismatch` | an encoding's declared type contradicts the column's |

This is the structured-representation rule (`generative.md` §1) applied
to the one output Forge did not have a ladder for:

| Output | Most structured form | One step down |
|---|---|---|
| A chart | **a spec citing a `table://` ref, rendered by the destination** | **a rendered PNG attached, and the result says the destination could not render the spec** |

Three things this buys, all observed in
[`../data-agents/data-formulator/`](../data-agents/data-formulator):

- **The chart is an object, not a picture.** It can be re-styled without
  re-running anything, embedded by reference in a later report, and — the
  part that matters for a review agent — *read* by a subsequent run.
- **`unknown_field` catches at write time what would otherwise be a
  rendering artefact.** A chart encoding a column that does not exist is
  the commonest chart bug and is silent in most pipelines.
- **`no_data_ref` keeps the data out of the spec**, which is what keeps
  the spec small enough to live in a comment body and keeps provenance
  intact.

The honest cost, stated because Data Formulator pays it too: **the
harness now owns a division of labour that free code did not have.** Once
the renderer bins the histogram, a model that pre-bins in pandas produces
a chart that renders happily and is wrong. Data Formulator's answer is an
explicit per-chart-type rule list (*"do NOT pre-bin in Python — pass the
raw quantitative field on `x`. Pre-aggregating gives wrong bin widths"*),
and Forge needs the equivalent in the data-mode prompt. That list is
real prompt weight and is the main argument against this adoption; it is
outweighed by the chart being inspectable at all.

Note what is *not* adopted: Data Formulator's thirty-chart-type
vocabulary with per-type encoding channels. Forge cites Vega-Lite, which
already has a grammar and a schema, and validates against that. Inventing
a parallel chart-type enum would be a second vocabulary for the same
idea — the mistake `artifacts.md` §1 was written to undo.

### 2f. The completion gate gets a provenance half

`generative.md` §2c added a **computed** half to the completion gate —
checks the harness runs, rather than asks the model to attest. An
analysis run gets one more:

> **Every ref named in `Complete.evidence` must resolve, and every
> `table://` among them must have a `produced_by` that resolves. A report
> whose numbers came from a table with no recorded provenance fails the
> gate.**

This is cheap (a graph walk over refs minted during the run), mechanical,
and it closes `agent-data-analysis.md` §12's problem 5 — the gap nobody
in the sources fills. It also does something the coding modes get for
free and the data mode otherwise would not: **it makes the run
reproducible by construction.** A coding run's output is a branch, and
the branch *is* the evidence. An analysis run's output is a claim, and a
claim with no trace back to a query is an assertion.

What it deliberately does not do: check that the numbers are *right*.
Nothing can. See §5.

**And the prompted half comes free from a pass that landed the same day.**
The Codex re-read added a **completion audit** to the coding prompt
(`README.md`'s *Claiming `done`* row; `../agent-self-verification.md`
§13) — derive the task's requirements, name the evidence that would prove
each, then look, with uncertain and indirect counted as not done. The
`analyse` entrypoint inherits it unchanged, and the half of it that
matters most here is the anti-shrinking clause: *quietly narrowing what
`done` meant to fit what got finished* is the characteristic failure of
an analysis run whose question turned out to be harder than it looked.
"I couldn't get revenue by cohort, so here is revenue by month" is a
completed-looking run that answered a different question, and no
provenance check catches it — the refs all resolve. The two halves
divide cleanly: the audit tests whether the claim matches the question,
the gate tests whether the numbers trace to data.

### 2g. A third entrypoint: `analyse`

`README.md`'s "two entrypoints, one core" becomes three. The core tool
set is **unchanged** — same eleven tools, same schemas.

```
     ┌────────▼─────────┐   ┌──────────▼──────────┐   ┌─────────▼─────────┐
     │   Coding agent    │   │    Review agent      │   │  Analysis agent   │
     │  (archetype 2)     │   │  (archetype 4/5)     │   │  (archetype 2)    │
     │                    │   │                      │   │                   │
     │ Jira ticket in →   │   │  PR diff in →        │   │ A question in →   │
     │ implement, verify, │   │  fixed team of       │   │ refs + a report   │
     │ leave branch ready │   │  specialists         │   │ out               │
     │                    │   │                      │   │                   │
     │ 2 modes:           │   │                      │   │ 2 modes:          │
     │ plan · implement   │   │                      │   │ explore · answer  │
     └────────────────────┘   └──────────────────────┘   └───────────────────┘
```

It is archetype 2 for the same reason the coding entrypoint is: the
consumer of the output is a Jira comment or a PR, not a chat window. The
two modes mirror `plan`/`implement`:

- **`explore`** — read-only against the data. Profile, query, and
  conclude with either a structured finding ("here is what the data
  supports"), an `AskUser`, or a plan for an `answer` run. Mints
  `table://` refs; writes no files, posts no charts.
- **`answer`** — the default. Produces the deliverable: a report in
  `Complete.report` and/or an `AddComment` body, citing chart specs and
  table refs.

**Why this is a third entrypoint and not a coding mode.** The tools are
identical; the *completion contract* is not. A coding run ends with a
branch whose tests pass. An analysis run ends with a claim and its
provenance, and §2f's gate is what checks it. Different gate, different
entrypoint — the same reason review is separate.

**Why not a fixed team, like review.** Review fans out to specialists
because `code-review-approaches.md` §5–6 establishes that a single pass
misses findings and a second independent pass catches them. The analogous
result for analysis does not exist in the sources. LIDA's
generate→evaluate→repair is the nearest thing, and its evaluator scores
*chart code* on six dimensions — which is a review of the artifact, not
of the analysis. Until there is a reason to believe a second analyst
catches what the first missed, the dynamic `Task` delegation the coding
entrypoint uses is the right default, and it is already there.

---

## 3. One rule to state once, not four times

§1's probe/commit rule lands in `tools.md`'s implementation contract,
once, with back-references — the same treatment `formats.md` §8 gave the
structured-representation rule.

The four places the design was already implementing it (`Task`'s
statelessness, the read tools' parallel-safety, `AddComment`'s
once-per-finding discipline, `Complete`'s singularity) get one-line
back-references rather than restating it. The one place it was *not*
implemented — `Bash` — gets §2c's minimum fix and a note that the
permission layer owns the rest.

---

## 4. Promoted and deferred

### 4a. Promoted to `future.md` with a stated shape

**A kernel-backed session, for an interactive surface.** Everything in
v1 is stateless: scripts run under `Bash`, state lives in refs. That is
the right default for a hands-off agent, and `agent-data-analysis.md` §3
is the argument — a persistent namespace the model cannot see diverges
from its transcript every turn, and all four known fixes cost something.
A stateless run has the problem by construction-free.

But the notebook surface is real, and if Forge ever drives one, the
contract is already known from the sources and should be written down
now rather than improvised:

- The **commit boundary is mandatory** and should be enforced by the
  namespace, not by a prompt rule — marimo's scratchpad (a shallow copy
  of globals, top-level bindings discarded) over jupyter-mcp's *"Under no
  circumstances should you use this tool to … perform variable
  assignments that affect subsequent Notebook execution"*. Two
  implementations, one with a mechanism.
- **Durable edits are transactional** — queue, apply on clean exit,
  discard on raise (marimo's `cm.get_context()`).
- **The live runtime is the source of truth, and the file on disk is
  not.** Any harness attached to a live process must say this explicitly
  and must name the tool that *looks* like it would work and doesn't
  (`Write` against the `.py`).
- **Kernel state is rendered into context by the harness**, filtered to
  public names, not probed by the model. marimo's `## Available variables
  from other cells:` with `value_type` and `preview_value`.
- **Blast-radius before a destructive op** — `ctx.graph.descendants(cid)`
  before a delete. This one generalises past notebooks and is worth
  lifting wherever the harness knows a dependency graph.

**A semantic layer.** `agent-data-analysis.md` §8: open source has
schema, the closed products (Cortex Analyst, Genie) have *meaning* — a
YAML model of logical tables, columns, relationships and business terms,
plus a verified-query repository of human-curated question/SQL pairs.
Nothing in the sources here has it, and Forge cannot invent it: the whole
value is that a human wrote down what "active customer" means.

The design already knows where that belongs. It is a repo-resident,
reviewable context artifact, and
[`context-files.md`](./context-files.md)'s tiering plus
[`artifacts.md`](./artifacts.md)'s `(source repo, ref)` keying is the
mechanism. Deferred because the content, not the plumbing, is the hard
part.

**Cost governance.** Not one source reasons about what a query costs.
Postgres MCP has the ingredients (`explain_query` before running,
`get_top_queries` after) and no harness makes the agent look first. For a
deployment pointed at a cloud warehouse this is the difference between a
tool and an incident, and it is a `Bash`-adjacent permission question
rather than a tool question.

**Big data.** Everything in v1 assumes a table fits on one machine.
`table://` is deliberately resolver-shaped so that a warehouse deployment
can resolve a ref to a temporary table rather than a parquet file — the
scheme survives, the backing does not. Nothing else is designed for it.

**Partition and sort order in the table stub.** §2b. Real, backend
specific, premature.

### 4b. Deferred with a reason, not adopted

**Shape assertions** (`agent-data-analysis.md` §12, problem 1) — row
counts across a join, null counts after a merge, groupby cardinality
against expectation. These are the cheapest catch for the commonest
silent failure in analysis, and **no source does them**. They are
deferred rather than adopted because it is not yet clear whether they
belong in the prompt (a discipline the model follows), in the `table://`
stub (the harness computes and shows them, which §2b partly does by
always showing null counts), or in the completion gate (a computed check,
like §2f). The right answer is probably the second, and probably looks
like: *when a `table://` is minted from inputs, the stub states the row
count of each input alongside its own.* A fan-out then shows up as a
number the model can see, for free, at the moment it happens.

**A streaming or paginated result channel** — MCP has no result
pagination at all and nobody streams partial answers. Not Forge's to fix.

---

## 5. Considered and rejected

**A `Describe` tool.** The single most common data operation, present in
one form or another in five sources. Rejected because `artifacts.md` §3
already makes `Read` a converting reader, and a profile is exactly what
reading a relation should produce. Adding `Describe` would fail the
design's own granularity rule (`tools.md`: split a primitive when the
split changes a *harness* answer — permission class, destructiveness,
concurrency safety, result shape) on three of four counts, and the fourth
— result shape — is satisfied by §2b's stub. **This is the adoption that
would have been easiest to wave through and is the one the ref system
most clearly already covers.**

**A `Query` or `Sql` tool.** Same reasoning: `:sql:` is a selector,
selectors are `Read`'s, and a relation's reducing operation belongs in
the same grammar as a file's line range. A separate tool would also
re-raise the question `artifacts.md` §1 settled — *where do the bytes
come from* is what a scheme encodes, not what a tool name should.

**A `Chart` tool.** Tempting, and Data Formulator's `visualize` is a good
design. Rejected because in Forge a chart is not a *surface the agent
renders to* — the surfaces are `AddComment` and `Complete`, and
`generative.md` §2a already made their bodies accept refs. So a chart is
a thing written and then cited, which makes it a `Write` (§2e) and a
reference, both of which exist. Data Formulator needs the tool because
its chart *is* its committing action; Forge's committing actions are
already elsewhere.

**Data Formulator's chart-type vocabulary.** Thirty types with per-type
encoding channels and a "critical rules" list. Excellent, and a second
vocabulary for something Vega-Lite already has a schema for. §2e.

**MetaGPT's `CHECK_DATA_PROMPT`.** A generated cell that prints kernel
state, injected back as context. Ingenious, and solves a problem v1 does
not have (§4a). Noted there for whenever it does.

**Per-task-type guidance fragments** (MetaGPT's `EDA_PROMPT`,
`FEATURE_ENGINEERING_PROMPT` …), keyed on a planner-assigned label.
Genuinely good — conditional prompt loading decided by the plan rather
than by the model mid-turn, which is cheaper and more predictable than a
skill. Rejected for v1 only because Forge has no skill or capability
mechanism at all yet (`generative.md` §2e defers skills), and this would
be the second half of a mechanism whose first half does not exist. It is
the strongest argument in this pass *for* building that mechanism.

**Personas on goal generation** (LIDA). The only handle in the sources on
*what question is worth asking*. Rejected because Forge's analysis
entrypoint is given a question; it does not generate goals. If an
exploratory mode is ever added that does, this is the first thing to
reach for.

**An `origin`-style `purpose` argument on `Bash`** (Data Formulator's
required one-sentence progress string). Rejected: Forge is hands-off,
so there is no progress feed for it to populate, and a required field
whose only consumer does not exist is pure token cost. Worth revisiting
the moment there is an interactive surface — it is the cheapest
enforceable version of "narrate before you act", because a schema field
cannot be skipped.

**Special-value integer codes** (Positron: `NULL: 0, NA: 1, NaN: 2,
NaT: 3, None: 4, +INF: 10, -INF: 11`). A genuinely good piece of
transport design that solves a real ambiguity — `"NA"` as a country code
versus a missing value. Rejected for v1 because Forge's `:rows:` output
is delimited text read by a model, not a grid read by a program, and the
model does better with `NA` than with `1`. **Adopted in spirit instead**:
the §2b stub states null counts per column, which is where the
information actually changes a decision. Revisit if `table://` ever gets
a programmatic consumer.

---

## 6. What this document does not change

- **The tool surface.** Still eleven tools, same schemas. `Read`, `Grep`
  and `Write` gain behaviour against a new scheme; none gains a
  parameter.
- **The MCP wire shape.** `artifacts.md` §8's rule stands unchanged:
  **one text block, no `structuredContent`, never rely on anything but
  block zero.** This pass re-confirmed why. MCP *does* specify
  `resource_link` and embedded `blob` resources — the premise that it
  cannot carry binaries is not quite right — but `agent-tool-result-transport.md`
  §3f's finding is unmoved: two of seven client projections drop
  `resource_link` silently, and ADK-Java turns any non-`TextContent`
  block into an error. A `table://` ref inside an `<artifact>` stub is
  strictly better than a `resource_link` a client may discard.

  For a Forge MCP *server* talking to other people's clients, the
  recommendation is different and is in `agent-data-analysis.md` §11c:
  `resource_link` for the handle, `structuredContent` against a declared
  `outputSchema` for schema/rows/preview/provenance, `annotations.audience`
  to separate the bytes from the preview — **plus a text line saying what
  it is**, so a client that drops the link still leaves the model
  something actionable. That is defensive duplication, and it is the
  correct response to a projection you cannot see. jupyter-mcp is the
  worked example.
- **Orchestration.** No new sub-agent types, no new fan-out. §2g.
- **The review entrypoint.** LIDA's rubric is a review of a chart, and
  it belongs to whoever adds chart review; it does not change
  `review.md`'s finding schema or its specialist/validator split.

---

## 7. Supersessions and decision rows

| Document | Change |
|---|---|
| `artifacts.md` §2a | `table://` added to the closed scheme set (§2a) |
| `artifacts.md` §2b | `:rows:`, `:cols:`, `:sql:` selectors added (§2c) |
| `artifacts.md` §4 | tabular spills mint `table://` (§2d) |
| `artifacts.md` §4a | the termination rule gains the `:sql:` exception, narrowing "a read carrying a selector never spills" (§2c) |
| `artifacts.md` §5.3 | `table` stub grammar; `produced_by` and `inputs` attributes (§2b) |
| `artifacts.md` §5.4 | the operation set for `kind="table"` |
| `tools.md` | `Write` gains the chart-spec validating path and its refusal vocabulary (§2e); the probe/commit rule lands in the implementation contract (§3) |
| `system-prompts.md` | a third entrypoint prompt, `analyse`, with modes `explore` and `answer` (§2g); the no-drawing rule and the renderer division-of-labour list (§2e) |
| `formats.md` | `<artifact kind="table">` block shape (§2b); `Complete.report` for an analysis run |
| `generative.md` §1 | the ladder gains a chart row (§2e) |
| `future.md` | kernel-backed sessions, the semantic layer, cost governance, big data, partition order (§4a) |
| `eval.md` | metrics: fraction of analysis runs passing the provenance gate; mean rows read per `table://` ref (a high number means the default projection is wrong) |
| `README.md` | the two-entrypoint diagram becomes three (§2g) |
