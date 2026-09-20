# Squirreling — the engine contracts

From the `squirreling` README and `src/` at `4652ffc` (`0.16.6`). These
are the interfaces a harness would implement against, and three of them
map onto contracts
[`../../agent-design/data.md`](../../agent-design/data.md) already
specifies.

## The self-description

> Squirreling is a streaming async SQL engine in pure JavaScript. Built
> for the browser from the ground up: streaming input and output,
> pluggable data sources, and lazy async cell evaluation. This makes
> Squirreling ideal for querying data from network sources, APIs, or LLMs
> where latency and cost matter.
>
> - **Standard SQL**: Full SQL support for querying data (read-only)
> - **Async UDFs**: User-defined functions can call APIs or models
> - **Tiny**: 13 kb bundle, zero dependencies, instant startup
>
> The key idea is **cell-level lazy evaluation**: rows are native
> AsyncGenerators and cells are async thunks `() => Promise<T>`. This
> means expensive operations only execute for cells that actually appear
> in your query results. Unlike WebAssembly databases, Squirreling is
> fully async with true streaming during network fetches.

"Full SQL support for querying data **(read-only)**" is a grammar
property, not a policy: there is no DML or DDL to reject.

## The result type

```typescript
interface QueryResults {
  columns: string[]
  numRows?: number
  maxRows?: number
  rows(): AsyncGenerator<AsyncRow>
}
interface AsyncRow {
  columns: string[]
  cells: Record<string, AsyncCell>
}
type AsyncCell = () => Promise<SqlPrimitive>
```

```javascript
const { rows } = executeSql({
  tables: { users },
  query: 'SELECT * FROM users',
})

for await (const { cells } of rows()) {
  console.log(`User id=${await cells.id()}, name=${await cells.name()}`)
}
```

**`QueryResults` is a ref stub with the payload still attached.**
`columns` + `numRows` is exactly what an artifact stub carries
(`data.md` §2b), and `rows()` is the deferred fetch. A harness that
wanted a `table://` ref would return the first three fields and hold the
generator — no adaptation needed, because the shape is already split
between shape-of-the-answer and the-answer.

`collect()` is provided for the eager case and is what
[`squirreling-mcp`](./squirreling-mcp-tools.md) uses, losing the
property.

## Async UDFs

```javascript
const rows = await collect(executeSql({
  tables: { products },
  query: 'SELECT name,AI_SCORE(description) AS score FROM products',
  functions: {
    AI_SCORE: {
      apply: async (text) => completions(`Rate the following product description from 1 to 10: ${text}`),
      arguments: { min: 1, max: 1 },
    },
  },
}))
```

> Because Squirreling uses lazy cell evaluation, the `AI_SCORE` function
> only executes for cells that are actually materialized. Combined with
> `LIMIT` or `WHERE`, you can efficiently query expensive operations.

Three things follow, and the third is a design problem rather than a
feature.

**The UDF is registered by the harness, not declared by the model.** The
model writes `AI_SCORE(description)` in SQL; the harness supplies
`apply`. So the capability surface inside the query language is exactly
what the deployment chose to expose — the same shape as
[`../pandasai/`](../pandasai)'s injected `execute_sql_query` function,
and the same shape as Cloudflare's connector globals
([`../../code-mode/`](../../code-mode)). **This is the natural seam for
capability control in a SQL-only design**: no sandbox required, because
the model never writes the code that runs.

**`arguments: { min, max }`** is an arity contract checked by the engine,
which is the whole of the type checking available. There is no return
type and no argument type.

**An unbounded `llm()` UDF is an unbounded spend.** `SELECT
AI_SCORE(description) FROM products` with no `LIMIT` and no selective
`WHERE` fires one inference per row. Laziness makes the *bounded* case
cheap (`LIMIT 5` really is five calls) and does nothing about the
unbounded one — if anything it makes the mistake easier to make, because
the query that costs $4,000 looks exactly like the query that costs
$0.004. Nothing in the engine caps it. A harness exposing a model-backed
UDF needs its own ceiling, and that is a design decision rather than an
integration detail.

## `AsyncDataSource` — the resolver interface

```typescript
interface ScannableDataSource {
  numRows?: number
  columns: string[]
  scan(options: ScanOptions): ScanResults
}

interface ScanOptions {
  columns?: string[] // columns to scan (undefined means all)
  where?: ExprNode
  limit?: number
  offset?: number
  signal?: AbortSignal
}

interface ScanResults {
  rows(): AsyncIterable<AsyncRow> // async iterable of rows
  appliedWhere: boolean // WHERE filter applied at scan time?
  appliedLimitOffset: boolean // LIMIT and OFFSET applied at scan time?
}
```

> The `scan()` method returns a `ScanResults` object containing a row
> stream and flags indicating which query hints were applied by the data
> source. This allows optional push down optimizations like filtering,
> limiting, and offsetting at the data source level when possible. Set
> `appliedWhere` or `appliedLimitOffset` to `true` if the data source
> handled them, `false` if the engine should apply them.

```typescript
const customSource: AsyncDataSource = {
  numRows: 1000000,
  columns: ['id', 'name', 'active'],
  scan({ columns, where, limit, offset, signal }) {
    return {
      rows: fetchAllRows({ columns, signal }),
      appliedWhere: false,      // source returned all rows, engine will filter
      appliedLimitOffset: false, // source returned all rows, engine will limit/skip
    }
  },
}
```

**This is the `table://` resolver interface, already written.**
`data.md` §2a says a `table://` ref resolves through a resolver and
"nothing above the resolver depends on the backing"; this is the concrete
shape that claim needs, and it is about forty lines of type.

The part worth stealing outright is **the two pushdown booleans**.
Pushdown is normally either a capability the engine must interrogate up
front or an optimisation the source silently may or may not have done —
and getting it wrong means either a correctness bug (filter applied
twice, or never) or a full scan nobody intended. Declaring per call
*"here are the rows, and here is what I already did to them"* makes the
engine's compensating work mechanical and lets the same source be lazy
for cheap hints and eager for expensive ones. A Parquet source pushes
column projection and row-group skipping; a CSV source pushes nothing;
a Postgres source pushes everything. Same interface, honest about
itself each time.

`signal: AbortSignal` on every scan is the other detail: cancellation is
in the contract rather than bolted on, which is what makes a runaway
query in a browser tab recoverable.

## The SQL surface

Quoted from the README's own list, because the coverage is the argument
for taking it seriously as an engine rather than as a toy:

> - `SELECT` statements with `DISTINCT`, `WHERE`, `ORDER BY`, `LIMIT`, `OFFSET`
> - `WITH` clause for Common Table Expressions (CTEs)
> - Subqueries in `SELECT`, `FROM`, `WHERE`, and correlated subqueries
> - `JOIN` operations: `INNER JOIN`, `LEFT JOIN`, `RIGHT JOIN`, `FULL JOIN`, `CROSS JOIN`, `POSITIONAL JOIN`, `LATERAL VIEW [OUTER] EXPLODE(...)`, with `ON` or `USING (col, ...)` conditions
> - `GROUP BY` and `HAVING` clauses, including `GROUP BY ALL`
> - Set operations: `UNION`, `UNION ALL`, `INTERSECT`, `INTERSECT ALL`, `EXCEPT`, `EXCEPT ALL`
> - Expressions: `CASE`, `CAST`, `TRY_CAST`, `BETWEEN`, `IN`, `LIKE`, `IS NULL`, `IS NOT NULL`, string concatenation `||`
> - Subscript access: zero-based array indexing `col[0]`, struct field access `col['field']`, and chains like `col[0].field`

Function families: aggregate (including `MEDIAN`, `PERCENTILE_CONT`,
`APPROX_QUANTILE`, `STDDEV_POP`/`SAMP`, `ARRAY_AGG`, `STRING_AGG`),
window (`ROW_NUMBER`, `LAG`, `LEAD`), string, math, trig, date
(`DATE_TRUNC`, `DATE_DIFF`, `EXTRACT`, `INTERVAL`), JSON
(`JSON_VALUE`/`_QUERY`/`_EXTRACT`/`_KEYS`), array, regex, **spatial**
(`ST_Intersects`, `ST_Contains`, `ST_DWithin`, …), conditional, and UDFs.

What is *not* there and matters for analysis: no `PIVOT`/`UNPIVOT`, a
window-function set limited to three, no `QUALIFY`, no statistical
aggregates beyond quantiles and standard deviation (no `CORR`,
`REGR_*`), and no optimizer. The window gap is the one most likely to
bite an analysis agent — ranking within groups is a routine ask and
`ROW_NUMBER` alone covers only part of it.

## Quoting rules, stated for the model

> - Single quotes for string literals: `'hello world'`
> - Double quotes for identifiers with spaces or special characters: `"column name"`
> - Escape quotes by doubling: `'can''t'` or `"col""name"`

Worth noting because identifier quoting is the single most common
mechanical failure in model-written SQL, and because the `FROM
"https://…/file.parquet"` convention means **every remote table in this
dialect is a double-quoted identifier** — so the rule is load-bearing
rather than an edge case. [`../data-formulator/`](../data-formulator)
ships the same guidance for DuckDB with the non-ASCII case spelled out.
