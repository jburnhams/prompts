# Local compute: where the agent's code runs, and in what language

A follow-on to [`agent-data-analysis.md`](./agent-data-analysis.md),
written against one question: **if the harness is already TypeScript, can
the data tools be TypeScript too — and if so, does the computation still
need a server?**

The answer is yes and no respectively, and the interesting part is not
either answer but what falls out of them. Sources read for this pass:
[`data-agents/hyperparam/`](./data-agents/hyperparam),
[`data-agents/arquero/`](./data-agents/arquero),
[`code-mode/`](./code-mode) and — for the SDK Cloudflare's Code Mode
ships inside — [`cloudflare-agents/`](./cloudflare-agents).

**Contents**

- [§1 The three-way split this pass is about](#1-the-three-way-split-this-pass-is-about)
- [§2 Pure JS vs WASM, and why the gap is architectural](#2-pure-js-vs-wasm-and-why-the-gap-is-architectural)
- [§3 Code Mode has converged from four directions](#3-code-mode-has-converged-from-four-directions)
- [§4 Sandboxes, under a blast-radius threat model](#4-sandboxes-under-a-blast-radius-threat-model)
- [§5 SQL-as-data or JS-as-code](#5-sql-as-data-or-js-as-code)
- [§6 One implementation, three deployments](#6-one-implementation-three-deployments)
- [§7 What breaks when you move compute into the tab](#7-what-breaks-when-you-move-compute-into-the-tab)
- [§8 Open problems](#8-open-problems)

---

## 1. The three-way split this pass is about

Three decisions usually get made as one and are independent:

| | Options |
|---|---|
| **Where the bytes are scanned** | the user's tab · a co-located server · a warehouse |
| **What language the engine is written in** | the harness's language · WASM · a native binary elsewhere |
| **What the model emits** | a tool call · a SQL string · a program |

`agent-data-analysis.md` answered the third for the Python world
(§4: both a general `execute` and focused tools, the focused ones
justified by cost) and largely assumed the first two. This pass is about
the combination that the Python world cannot reach: **the engine written
in the same language as the harness, running wherever the harness runs,
with the model writing SQL or a program against it.**

The reason it matters is not elegance. It is that an engine written in
the harness's own language can be **moved to the data** — into the tab
when the data is in the tab, into the MCP server when it is behind a
warehouse — without a second implementation and without the model's tool
surface changing.

---

## 2. Pure JS vs WASM, and why the gap is architectural

The obvious way to get SQL into a browser is DuckDB-WASM, and it is a
much more complete analytical engine than anything written in plain
JavaScript: an optimizer, spill-to-disk, years of correctness work, and
far more SQL surface. For heavy local analytics it is the right answer.

For an *agent*, [`data-agents/hyperparam/`](./data-agents/hyperparam)
makes a case that it is not, and two of the three arguments hold up
independently of the vendor's benchmark.

**Cold start.** 0.6 s against 19 s, which is a property of shipping
~70 KB of JavaScript versus instantiating a multi-megabyte WASM module,
not of tuning. For a tab that opens and asks one question, this is the
whole experience.

**Async all the way down.** This is the load-bearing one. Squirreling's
rows are `AsyncGenerator`s and its cells are async thunks
`() => Promise<T>`, so an expensive cell only fires when a downstream
operator demands it:

> A query like `SELECT llm('classify', content) FROM traces LIMIT 5`
> makes exactly five API calls regardless of predicate matches.

The alternative cannot do this, and the paper is specific about why:

> In the DuckDB-WASM path, execution is vectorized in morsels, but scalar
> UDF calls still cross the WASM boundary synchronously from the engine's
> perspective: a long-running awaited call inside a UDF such as an `llm()`
> inference stalls that path.

A vectorized engine's whole performance model assumes operators are
synchronous and cheap. An `await` inside one is a category error, and no
amount of engineering inside the WASM module fixes it — **the boundary
is the problem**. So "model inference as a SQL function" is available to
a pure-JS engine and structurally unavailable to a compiled one.

**Cost and throughput** are the third argument (3× lower cost per task
pass; 300× on filter-bounded LLM-UDF queries; 192× on sort-bounded) and
are **vendor-run and vendor-reported**, by the author of the libraries
being measured, with no independent replication found. The mechanism
behind each is checkable even where the number is not.

The honest summary: **pure JS wins on start-up, async, and size; WASM
wins on analytical completeness.** For an agent issuing small reducing
queries against remote columnar files, the first three dominate. For a
long-lived analytical session over local data they do not.

One more thing the pure-JS stack gets for free, and it is not a
performance property: **no code generation anywhere**. Verified across
`squirreling/src` at `4652ffc` — no `eval`, no `new Function`; the only
`import(` hits are JSDoc annotations. Model-written SQL is parsed to an
AST and interpreted. Compare [`data-agents/arquero/`](./data-agents/arquero),
where verb expressions are AST-verified against a closed `op.*`
vocabulary and *then compiled* — safe, but resting on the completeness of
a verifier rather than on the absence of an interpreter.

---

## 3. Code Mode has converged from four directions

Four independent implementations now replace a tool list with a typed API
and a sandbox, and this collection covers all four
([`code-mode/`](./code-mode)):

| | Discovery | Sandbox | What the model writes |
|---|---|---|---|
| **Cloudflare** | `codemode.search()` / `.describe()` | V8 isolate, or **an iframe in the user's tab** | an async arrow function |
| **Anthropic** | a filesystem of `.ts` wrappers the model `ls`/`cat`s | server-side execution environment | a TS program with imports |
| **Codex** | — (`tool_mode: "code_mode_only"`) | host JS execution tool | a program |
| **DeepSeek** | every tool as a compiling `.d.ts` | — | a program, not a call |

Their shared claims, in their own words:

> LLMs have an enormous amount of real-world TypeScript in their training
> set, but only a small set of contrived examples of tool calls.
> *(Cloudflare)*

> Every intermediate result must pass through the model. … For a 2-hour
> sales meeting, that could mean processing an additional 50,000 tokens.
> *(Anthropic)*

The two discovery answers are the same idea bound to different
substrates. Anthropic's filesystem reuses a skill the model has in
abundance and a tool surface a coding agent already has — `Read`,
`Grep`, `List` over a directory of declarations, at which point
**the tool catalogue is a repository** and everything the collection
knows about reading one efficiently applies. Cloudflare's method calls
are what you use when there is no filesystem, which is the browser.

Two caveats that recur and are worth carrying into any design:

- **Schemas are documentation, not enforcement.** Cloudflare's browser
  path says it outright: *"JSON Schema is used for prompt/type generation
  only and is not enforced at runtime."*
- **Approval composes with a program, via replay — on one path.**
  Cloudflare's connector layer marks a tool `requiresApproval`; the run
  aborts at that call, the action is recorded pending, and on approval
  the *same code re-runs* with every prior call served from a durable
  log. Tools handed in through the AI-SDK path carrying `needsApproval`
  are instead silently filtered out. So the hard problem — one approval
  decision inside a program with five consequences — has a shipped
  answer, and which answer you get depends on how you wired the tools.
  [`code-mode/cloudflare.md`](./code-mode/cloudflare.md).

---

## 4. Sandboxes, under a blast-radius threat model

Most writing on sandboxing untrusted JS assumes an adversary. For an
internal deployment the threat model is different and much more
tractable: **the model is not hostile, it is careless** — a wrong join
that scans a terabyte, a runaway loop, a `DELETE` where a `SELECT` was
meant, a well-intentioned `fetch` to an internal service nobody expected.
The job is bounding the damage of a mistake, not defeating an attacker.

That reframing changes the answer. Under an adversarial model the
recommendation is QuickJS-in-a-worker plus OS-level confinement. Under a
blast-radius model, tiers:

| Tier | Mechanism | Bounds | Does not bound |
|---|---|---|---|
| 0 | call TS functions directly | nothing | anything |
| 1 | Web Worker | DOM access, main-thread hangs | **network egress** — `fetch` is available |
| 2 | **sandboxed iframe + CSP** | DOM, storage, cookies, **all network** | synchronous CPU |
| 3 | Worker *inside* a sandboxed iframe | the above **plus** hangs (`terminate()` works) | memory |
| 4 | QuickJS / isolated-vm | a determined adversary | — |

**Tier 2 is Cloudflare's shipped browser executor**, ~200 lines, zero
dependencies, MIT, and it is the sweet spot for this threat model:

```ts
const DEFAULT_CSP =
  "default-src 'none'; script-src 'unsafe-inline' 'unsafe-eval';";
```

```ts
iframe.sandbox.add("allow-scripts");   // note: no allow-same-origin
```

`allow-scripts` without `allow-same-origin` gives an opaque origin — no
host DOM, no storage, no cookies. `default-src 'none'` in a CSP injected
as a `<meta>` into the `srcdoc` document kills `connect-src` with it, so
`fetch`, WebSocket, `sendBeacon` and image pings are all dead. The meta
tag is honoured even if later script rewrites it. Tools reach out over
`postMessage` with a per-execution nonce checked on both sides, and the
providers are passed as **function parameters**, not globals:

```ts
const fn = new Function(...providerNames, "return (" + code + ")")(
  ...providerProxies
);
```

so a program cannot enumerate `globalThis` to find capabilities it was
not handed.

**The gap tier 2 leaves is the one that matters most for carelessness,**
and Cloudflare names it:

> its timeout cannot preempt tight synchronous loops like `while (true) {}`
> because those block the browser event loop.

An accidental infinite loop hangs the user's tab and no timeout can
reach it. Tier 3 — a Worker inside the iframe — is the fix, and it is not
in the box. For a data agent this is not hypothetical: a cartesian join
over two large scans is an ordinary model mistake and looks exactly like
a hang.

Three things worth knowing even under a relaxed model:

- **A Web Worker is not a network boundary.** It is a separate realm with
  no DOM, which is a stability property. It has `fetch`.
- **ShadowRealm is Stage 2.7**, not shipped, and the TC39 material is
  explicit that it is not a security boundary anyway.
- **`node:vm` is not a sandbox** — the Node docs say so — and `vm2` was
  deprecated in 2023 after 20+ CVEs. Server-side, the options are
  `isolated-vm`, QuickJS-in-a-worker, or a real process boundary.

And the cheapest control is not a sandbox at all: **plan the query before
you run it.** `squirreling-mcp` parses and plans the SQL, then walks the
plan for scan nodes to resolve table identifiers, so the set of things a
query will touch is known before a byte is read:

```js
/**
 * Recursively collect table identifiers (file paths or URLs) from all Scan/Count
 * nodes in a query plan.
 */
function scanTables(plan) { … }
```

That is where an allowlist, a cost estimate or an approval prompt
belongs. A regex over the SQL text would not do it, and a sandbox does
not help — the query is *authorised*, it is just expensive.

---

## 5. SQL-as-data or JS-as-code

The sharpest fork in this pass, and the sources land on both sides.

**SQL as data.** The model emits a string. The harness parses it, plans
it, can inspect what it touches, and hands it to an interpreter. No
codegen anywhere. Squirreling's grammar has no DML or DDL at all, so
read-only is a property of the language rather than of a policy — a
stronger position than [`data-agents/postgres-mcp/`](./data-agents/postgres-mcp)'s
`pglast` allowlist, which is necessary precisely because the engine
underneath *can* write.

**JS as code.** The model emits a program. Maximum expressiveness —
reshaping, iteration, calling three tools and joining their results,
anything SQL cannot say. Requires a real sandbox, and the four-way
convergence in §3 says this is where the field is going.

What tips the balance is that they are not alternatives at the same
level. **SQL is the reducing operation on a table; a program is the
orchestration around it.** A design can have both, and the interesting
observation is that the seam between them already exists in the engine
contract:

```javascript
executeSql({
  tables: { products },
  query: 'SELECT name, AI_SCORE(description) AS score FROM products',
  functions: {
    AI_SCORE: { apply: async (text) => completions(`…${text}`), arguments: { min: 1, max: 1 } },
  },
})
```

**The UDF is registered by the harness and named by the model.** The
model writes `AI_SCORE(description)` in a SQL string; it never writes the
function body. So the capability surface *inside* the query language is
exactly what the deployment chose to expose — no sandbox required,
because no model-authored code runs. That is the same shape as
[`data-agents/pandasai/`](./data-agents/pandasai)'s injected
`execute_sql_query` and as Cloudflare's connector globals, and it is the
cheapest capability-control mechanism in this collection.

**Which makes the `llm()` UDF a governance question, not a feature.**
Laziness makes the bounded case genuinely cheap — `LIMIT 5` is five
calls — and does nothing about the unbounded one. `SELECT
AI_SCORE(description) FROM products` with no `LIMIT` fires one inference
per row, and the query that costs $4,000 is textually indistinguishable
from the one that costs $0.004. Nothing in the engine caps it. Any
harness exposing a model-backed UDF needs its own ceiling, enforced
where the plan is walked, before execution.

---

## 6. One implementation, three deployments

The property that makes all of this worth doing: an engine written in the
harness's language is **the same code** in three places, and the model's
tool surface does not change between them.

| Deployment | Engine runs in | Tools reach the model via | Data leaves the machine? |
|---|---|---|---|
| **In the tab** | the page (or its sandbox) | direct calls, or `navigator.modelContext` | **no** |
| **Co-located server** | Node next to the data | MCP | within the boundary |
| **Warehouse** | resolver pushes down | MCP | query only |

`squirreling-mcp` is the middle row, shipped: the same `squirreling` that
runs in a browser, wrapped as a stdio or Streamable-HTTP MCP server, with
three tools — `query`, `describe_table`, `list_tables`.

Three consequences.

**The `FROM` clause becomes the ref namespace.** There is no
`open_table`, no handle, no session — a local path, an `https://` URL, an
Iceberg directory and a bare Postgres name are all identifiers,
disambiguated by shape. One tool reaches five source types and a join
across two of them is ordinary SQL. This is the same collapse
`agent-design/artifacts.md` §1 makes when it folds `ReadSource` into
`Read` and lets a scheme carry "where the bytes come from" — arrived at
independently, and implicitly rather than explicitly, which is cheaper to
write and harder to extend.

**Pushdown is negotiated per call, honestly.** The resolver interface is
forty lines of type, and the part to copy is the two booleans:

```typescript
interface ScanResults {
  rows(): AsyncIterable<AsyncRow>
  appliedWhere: boolean       // WHERE filter applied at scan time?
  appliedLimitOffset: boolean // LIMIT and OFFSET applied at scan time?
}
```

A Parquet source pushes column projection and row-group skipping; a CSV
source pushes nothing; a Postgres source pushes everything. Same
interface, saying what it actually did each time, so the engine's
compensating work is mechanical. Most systems make pushdown either an
up-front capability interrogation or a silent optimisation, and both fail
differently.

**Privacy stops being a claim and becomes a fact.** Anthropic's Code Mode
lists "intermediate results stay in the execution environment" as a
benefit of server-side sandboxing. Run the same pattern in the user's
browser and the intermediate results never leave the user's machine —
the execution environment *is* the machine. For regulated or internal
data this is a different argument from token efficiency, and a stronger
one.

And there is a capability the server surface structurally cannot offer.
Cloudflare's browser example ships `getPageInfo` alongside its data
tools — a tool that reads the live page. Whatever the user is currently
looking at is addressable by the agent only if the agent is in the tab.

---

## 7. What breaks when you move compute into the tab

Not everything survives the move, and the failures are not where you
expect.

**The engine streams; the MCP boundary does not.** Squirreling's entire
design is rows that arrive before the source is fully read — and
`squirreling-mcp` calls `collect()`, materialising a 40,000-row result in
the server to show 100 rows of it. The engine layer and the result
layer are independent, and a good engine does not give you a good result
contract for free.

**The result contract is the gap, and it is the same gap as before.**
`squirreling-mcp` returns a markdown table capped at 100 rows with
`... and 40922 more rows (showing first 100 rows)` — no cursor, no
offset, no ref. The only recovery is to rewrite the SQL with a
`LIMIT`/`OFFSET` the model has to invent. Everything
`agent-data-analysis.md` §6c said about preview-plus-handle applies
unchanged; nothing about a JS engine makes it easier or harder.

Worth noting that the fix is nearly free, because the engine's own return
type is already a ref stub with the payload attached:

```typescript
interface QueryResults {
  columns: string[]
  numRows?: number
  maxRows?: number
  rows(): AsyncGenerator<AsyncRow>
}
```

`columns` + `numRows` is the shape; `rows()` is the deferred fetch.

**Artifacts become tab-local and mortal.** A run that mints intermediate
tables in the browser has a provenance graph that dies with the tab. Any
design whose completion gate requires refs to resolve
(`agent-design/data.md` §2f) needs either a spill path to durable storage
or a browser-local variant of the gate. This is the sharpest conflict
between the local-compute model and the hands-off run model.

**Approval does not compose with a program.** §3. If approval is a tier
rather than a switch, Code Mode is currently the wrong shape for anything
that needs one, and the available answer is the boring one: keep
approval-gated capabilities out of the program and behind ordinary tool
calls.

**And the tab can hang.** §4. The one failure mode a blast-radius model
cares most about is the one tier 2 does not cover.

---

## 8. Open problems

**1. Nobody has an approval story for a program.** Excluding gated tools
is the current answer everywhere. The interesting design is presenting a
*plan* of intended effects for approval before the program runs, which
the plan-walking in §4 makes plausible for SQL and not obviously for JS.

**2. Cost governance is still missing, and now it is worse.** The
previous pass recorded that no data harness reasons about what a query
costs. A model-backed UDF inside a query makes an unbounded spend a
one-line mistake. The ingredients exist — plan-walking, `numRows`,
`EXPLAIN` on the warehouse path — and nothing assembles them.

**3. Window functions and reshaping are thin.** Squirreling has
`ROW_NUMBER`, `LAG`, `LEAD` and no `PIVOT`/`UNPIVOT`, no `QUALIFY`, no
`CORR`/`REGR_*`. Arquero has the reshaping and the statistics and no
async. Neither alone covers ordinary analysis; the honest answer today is
both, or SQL plus a program.

**4. Streaming results to a model is still unsolved.** `agent-data-analysis.md`
§12 listed this and was wrong about the cause: the engines *can* stream
— `rows()` is an `AsyncGenerator` — and the protocol cannot carry it.
MCP has no result pagination or streaming for tool results at all
(`agent-tool-result-transport.md` §6). The gap is in the transport, not
the compute.

**5. WebMCP is one vendor's preview wearing a standards badge.** Chrome
146 Canary behind a flag, origin trial in 149, a W3C *Community Group*
report rather than a Recommendation. The Cloudflare adapter's own header
says **"DO NOT USE IN PRODUCTION … WILL break between releases."** Any
design depending on it needs a path that works without it — which, for an
agent that already runs its own loop in the page, is calling the
functions directly.
