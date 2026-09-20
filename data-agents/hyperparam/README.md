# Hyperparam / HypStack

- **Type**: pure-JavaScript data stack, built for browsers *and* agent
  sandboxes · **Vendor**: Hyperparam (Kenny Daniel) · **Licence**: MIT
  throughout
- **Source**: `github.com/hyparam/{squirreling,hyparquet,icebird,hyparquet-writer,hightable,squirreling-mcp}`
- **Read**: 2026-09-20, at the commits in the table below
- **Paper**: [*A Query Engine for the Agents*](https://arxiv.org/html/2605.27785),
  arXiv:2605.27785v1, 27 May 2026

The direct answer to "could we give the model TS data tools and compute
in the browser?" — because it is that, already shipped, with a paper
arguing the case and an MCP server wrapping the same engine for
server-side use.

| Repo | Version | Commit | Deps | What |
|---|---|---|---|---|
| [`squirreling`](https://github.com/hyparam/squirreling) | `0.16.6` | `4652ffc` (2026-09-17) | **0** | Streaming async SQL engine, ~13 KB |
| [`hyparquet`](https://github.com/hyparam/hyparquet) | `1.31.1` | `3c8626b` (2026-09-17) | **0** | Parquet reader over HTTP range requests, ~9.7 KB gz |
| [`icebird`](https://github.com/hyparam/icebird) | `0.8.29` | `3a0c5fb` (2026-09-18) | 4 (own stack) | Apache Iceberg client, time travel |
| [`hyparquet-writer`](https://github.com/hyparam/hyparquet-writer) | — | `0998a1d` (2026-09-05) | — | Parquet writer, <100 KB |
| [`hightable`](https://github.com/hyparam/hightable) | — | `0989abd` (2026-03-10) | React | Virtualized grid, millions of rows, async cell loading |
| [`squirreling-mcp`](https://github.com/hyparam/squirreling-mcp) | `0.1.0` | `5b62736` (2026-04-30) | `pg` | The same engine as an MCP server |

Also in the org and not read here: `hypgrep` (full-text index over
Parquet), `hypvector` (embedding search over Parquet), `hypaware` (OTLP
collector), `hyllama` (GGUF metadata).

## Files

| File | What it is |
|---|---|
| [`squirreling-mcp-tools.md`](./squirreling-mcp-tools.md) | The three MCP tool definitions, verbatim, plus the result-handling code and its caps |
| [`engine-contracts.md`](./engine-contracts.md) | `AsyncDataSource`, `AsyncRow`/`AsyncCell`, the UDF contract, and the supported SQL surface — quoted from the README and the source |

## Why it is in this collection

**1. It is the same code in three places.** `squirreling` runs in a
browser tab, in Node, and inside `squirreling-mcp` as a stdio or
Streamable-HTTP MCP server. The engine does not know which. That is the
property that makes "one data tool surface, deployed wherever the data
is" a real option rather than a diagram.

**2. Zero dependencies and no code generation.** Verified at `4652ffc`:
`grep -rn "new Function\|eval(" squirreling/src` returns nothing — the
only `import(` hits are JSDoc type annotations. The engine parses SQL to
an AST and walks it. **Model-written SQL never becomes JavaScript**,
which is a materially smaller surface than any harness that hands model
output to an interpreter (`../../agent-data-analysis.md` §10b's
allowlist problem does not arise, because there is nothing to allow).

**3. The SQL is read-only by construction.** No `INSERT`, `UPDATE`,
`DELETE`, `CREATE` or `DROP` exists in the grammar. Compare
[`../postgres-mcp/`](../postgres-mcp), which achieves the same end by
parsing with `pglast` and validating against an allowlist of statement
node types — necessary there, because the engine underneath can write.

**4. Cell-level laziness makes an `llm()` UDF affordable.** Rows are
`AsyncGenerator`s and cells are async thunks `() => Promise<T>`, so an
expensive cell only fires when a downstream operator demands it. The
paper's claim:

> A query like `SELECT llm('classify', content) FROM traces LIMIT 5`
> makes exactly five API calls regardless of predicate matches.

This is the one thing in the stack that **cannot** be ported to a
WebAssembly engine. From the paper's discussion of the alternative:

> In the DuckDB-WASM path, execution is vectorized in morsels, but scalar
> UDF calls still cross the WASM boundary synchronously from the engine's
> perspective: a long-running awaited call inside a UDF such as an `llm()`
> inference stalls that path.

**5. `describe_table` before `query` is in the tool description.** The
MCP server tells the model to plan against the schema rather than
`SELECT *` — the same discipline `../data-formulator/`'s
`inspect_source_data` and `../btw/`'s `skim` arrive at, here stated as
*"Use this to plan a query before issuing one."*

## The benchmark, and how to read it

The paper reports, against DuckDB-WASM on agent-analyst tasks:

| Measure | Hyperparam | DuckDB-WASM |
|---|---|---|
| Cost per ten-task pass | **$0.067** | $0.203 |
| Filter-bounded queries with LLM UDFs | **300× faster** | — |
| Sort-bounded queries (async pipelining) | **192× faster** | — |
| Cold start | **0.6 s** | 19 s |
| Bundle | <70 KB gzipped (three libraries) | tens of MB |

**This is vendor-run and vendor-reported**, by the author of the
libraries being measured, and no independent replication was found in
this pass. Read it the way `../../sources.md` reads the Stencil
benchmarks: the *mechanism* behind each number is checkable even where
the number is not. Cold start is a property of shipping 70 KB of JS
versus instantiating a multi-megabyte WASM module, and the LLM-UDF
speedups follow from async operators versus a synchronous UDF boundary —
both are architectural, not tuning. The cost figure depends on a task
mix chosen by the vendor and should be treated as illustrative.

The fair statement of the trade: **DuckDB-WASM is a much more complete
analytical engine.** It has a query optimizer, spill-to-disk, far more
of the SQL surface, and years of correctness work. Squirreling is a
streaming interpreter with pushdown hints and no optimizer. For an agent
issuing small-to-medium reducing queries against remote columnar files,
the latter's start-up and async properties dominate. For a heavy local
analytical workload they do not.

## What it does *not* solve

`squirreling-mcp` returns results as a **markdown table capped at 100
rows** with `... and N more rows (showing first 100 rows)` — no ref, no
cursor, no artifact, nothing to page with. It is the naive result
contract, in the best-engineered engine in this folder, which is a
useful confirmation that the engine layer and the result layer are
genuinely separate problems. The ref contract in
[`../../agent-design/data.md`](../../agent-design/data.md) §2b–2d is
what would sit on top.
