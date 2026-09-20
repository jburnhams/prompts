# squirreling-mcp — the three tools

`src/mcpHandler.js` at `5b62736`. Tool text is verbatim; the string
concatenation is the source's own.

```js
export const protocolVersion = '2025-06-18'
export const serverInfo = { name: 'squirreling-mcp', version: '0.1.0' }
```

## `query`

```js
export const queryTool = {
  name: 'query',
  title: 'SQL Query',
  description: 'Execute a SQL query against files (parquet, csv, jsonl), Apache Iceberg tables, or postgres tables.'
    + ' Identifiers in the FROM clause are dispatched by shape: extension `.parquet`/`.csv`/`.jsonl`/`.ndjson` loads a file; an identifier with `/` in it loads an Iceberg table (directory containing a `metadata/` subdirectory); a bare name like `users` or `public.users` resolves to a postgres table when the server is configured with DATABASE_URL.'
    + ' Supports ANSI SQL: WHERE, ORDER BY, LIMIT, GROUP BY, JOIN, aggregate functions, etc.'
    + ' Wrap column names containing spaces in double quotes ("column name").'
    + ' String literals must be single-quoted.'
    + ' Examples:'
    + '\n - SELECT * FROM "https://s3.hyperparam.app/dataset.parquet" LIMIT 10'
    + '\n - SELECT country, COUNT(*) AS n FROM "/path/to/file.parquet" GROUP BY country'
    + '\n - SELECT a.id, b.name FROM "a.parquet" a JOIN "b.parquet" b ON a.id = b.id'
    + '\n - SELECT * FROM "https://host/warehouse/db/table" LIMIT 10  -- Iceberg table'
    + '\n - SELECT id, email FROM users WHERE created_at > \'2024-01-01\' LIMIT 50  -- postgres'
    + '\n\nResults are returned as a markdown table. String cells are truncated to 1000'
    + ' characters by default (10000 if truncate=false). Truncated columns are marked'
    + ' "(truncated)" in the header.',
  inputSchema: {
    type: 'object',
    properties: {
      query: {
        type: 'string',
        description: 'SQL query string. Tables in FROM clauses are either file paths/URLs (quoted as identifiers) or, when DATABASE_URL is configured, bare postgres table names.',
      },
      truncate: {
        type: 'boolean',
        description: 'Truncate long string cells to 1000 chars (default true). Set false to allow up to 10000 chars per cell.',
        default: true,
      },
    },
    required: ['query'],
  },
}
```

**The FROM clause is the ref namespace.** There is no `open_table`, no
handle, no session. A path, an `https://` URL, an Iceberg directory and
a bare Postgres name are all just identifiers, disambiguated **by
shape** — extension, then presence of `/`, then fallback. One tool
reaches five source types, and a join across two of them is ordinary
SQL.

That is the same collapse `../../agent-design/artifacts.md` §1 makes
when it folds `ReadSource` into `Read` and lets the scheme carry
"where the bytes come from". Here the scheme is implicit in the
identifier's shape rather than explicit, which is cheaper to write and
worse to extend — a new source type has to find an unclaimed shape.

**Five worked examples in the description**, one per source type,
including the cross-file join. This is the single most effective thing a
SQL tool description can carry, and it is where most of the description's
length goes.

**The truncation policy is in the description, with its own parameter.**
`truncate` is a per-call model-facing dial between 1,000 and 10,000
characters per *cell* — not per result. Long-text columns (the agent-trace
use case this stack was built for) are the target.

## `describe_table`

```js
export const describeTableTool = {
  name: 'describe_table',
  title: 'Describe Table',
  description: 'Return the schema (column names, types when available, and row count when cheap) of a table without scanning rows.'
    + ' Use this to plan a query before issuing one.'
    + ' The `table` argument follows the same dispatch rules as the `query` tool: a path or URL ending in `.parquet`/`.csv`/`.jsonl`/`.ndjson` describes a file; an identifier with `/` describes an Iceberg table; a bare name like `users` or `public.users` describes a postgres table when DATABASE_URL is configured.'
    + '\n\nReturns a short markdown block with `Table:`, optional `Rows:`, and a column table.',
  inputSchema: {
    type: 'object',
    properties: {
      table: {
        type: 'string',
        description: 'Table identifier — same syntax as a FROM-clause identifier in the `query` tool.',
      },
    },
    required: ['table'],
  },
}
```

Three phrases doing real work:

- **"without scanning rows"** — states the cost, which is what makes it
  choosable over `SELECT * … LIMIT 5`.
- **"row count when cheap"** — honest about a property that is free in
  Parquet footer metadata, free in Iceberg manifests, and a table scan in
  CSV. The tool declines to promise what it cannot deliver uniformly.
- **"Use this to plan a query before issuing one"** — the ordering rule,
  in the description rather than in a system prompt.

This is `../../agent-design/data.md` §2b's default projection arriving
independently: reading a relation should answer *what is in this table*
in O(columns), and rows are the expensive special case.

## `list_tables`

```js
export const listTablesTool = {
  name: 'list_tables',
  title: 'List Tables',
  description: 'Enumerate tables/files available to query.'
    + '\n\nUsage:'
    + '\n - With no argument: list user tables in the configured postgres database (requires DATABASE_URL).'
    + '\n - With `path` set to a local directory: list files in that directory whose extensions match a supported file source (.parquet/.csv/.jsonl/.ndjson). Subdirectories are not recursed.'
    + '\n\nIceberg-warehouse and HTTP/S3 listings are not implemented; supply the explicit table URL to the `query` tool for those.',
  inputSchema: {
    type: 'object',
    properties: {
      path: {
        type: 'string',
        description: 'Optional local directory path to list. Omit to list postgres tables.',
      },
    },
  },
}
```

**"Subdirectories are not recursed"** and **"Iceberg-warehouse and
HTTP/S3 listings are not implemented"** — two unimplemented capabilities
named in the model-facing text, the second with the workaround. Compare
[`../jupyter-mcp/`](../jupyter-mcp)'s `list_files`, which bounds the same
context-bomb risk with a schema constraint (`max_depth` `le=3`) instead.
Both work; the schema bound is harder to ignore, the prose is cheaper to
write and also tells the model what to do instead.

## Resolution: plan first, then bind

`src/runSqlQuery.js` does something worth lifting. It parses and **plans**
the SQL, walks the plan for scan nodes, and resolves each table
identifier to an `AsyncDataSource` *before* executing:

```js
/**
 * Recursively collect table identifiers (file paths or URLs) from all Scan/Count
 * nodes in a query plan. Squirreling's planner treats unknown table names as
 * scans, so any path or URL the user puts in the FROM clause shows up here.
 */
function scanTables(plan) { … }
```

```js
/** @type {Record<string, import('squirreling').AsyncDataSource>} */
const tables = {}
await Promise.all([...tableNames].map(async name => {
  tables[name] = await resolveTable(name, { pool })
}))
```

So the set of things a query will touch is **known before a byte is
read**, from the plan rather than from the query string. That is the
natural place to put an allowlist, an approval prompt, or a
cost estimate — none of which this server does, but all of which this
shape makes straightforward. A regex over the SQL text would not.

## Result handling, and where the streaming is lost

```js
const maxRows = 100
…
const results = await collect(executeSql({ tables, query }))
const queryTime = (performance.now() - startTime) / 1000

if (results.length === 0) {
  return `Query executed successfully but returned no results in ${queryTime.toFixed(1)} seconds.`
}

const rowCount = results.length
const maxChars = truncate ? 1000 : 10000
let content = `Query returned ${rowCount} row${rowCount === 1 ? '' : 's'} in ${queryTime.toFixed(1)} seconds.\n\n`
content += markdownTable(results.slice(0, maxRows), maxChars)
if (rowCount > maxRows) {
  content += `\n\n... and ${rowCount - maxRows} more row${rowCount - maxRows === 1 ? '' : 's'} (showing first ${maxRows} rows)`
}
return content
```

Four observations, in ascending order of importance.

**It reports elapsed time to the model.** `in 0.4 seconds` on every
result. Cheap, and the only instance in this collection of a data tool
telling the model what its last call cost in wall clock.

**The exact row count is stated even when the rows are not shown.** So
`Query returned 41022 rows` followed by 100 of them — the model knows the
shape of what it did not see. Same property as
[`../vanna/`](../vanna)'s `metadata.row_count`.

**The truncation notice does not name a next call.** `... and 40922 more
rows (showing first 100 rows)` tells the model what was lost and gives it
nothing to do about it. There is no cursor, no offset parameter, no ref.
The only recovery is to rewrite the SQL with a `LIMIT`/`OFFSET` the model
has to invent. Set against Open Interpreter's *"You should try again and
use `computer.ai.summarize(output)`"* and Vanna's *"FOR VISUALIZE_DATA USE
FILENAME: …"*, this is the weakest of the three, and it is in the
best-engineered engine here.

**`collect()` throws the streaming away.** The engine's whole design is
`AsyncGenerator` rows that arrive before the source is fully read — and
the MCP boundary buffers all of them into an array to count and slice.
A 40,000-row result is fully materialised in the server to show 100 rows.

That last one is the finding. **The engine layer and the result-transport
layer are independent, and a good engine does not give you a good result
contract for free.** Everything `../../agent-design/data.md` §2b–§2d
specifies — mint a `table://` ref, default to column summaries, page with
a selector — sits exactly on this seam, and nothing about squirreling
prevents it; `executeSql` already returns `{ columns, numRows, maxRows,
rows() }`, which is a ref stub with the payload still attached.
