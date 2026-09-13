# Postgres MCP Pro

- **Type**: database MCP server · **Vendor**: Crystal DBA · **Licence**:
  MIT
- **Source**: https://github.com/crystaldba/postgres-mcp — `main` @
  `15c8e33` (2026-08-15)
- **Retrieved**: 2026-09-12

The reference answer to **"what does a database tool surface look like
when someone has thought about it"**, and the contrast case for every
harness in this folder that reaches SQL through Python instead.

Nine tools, two access modes, and — the part worth copying — **the access
mode changes what the model is told, not just what the driver allows**.

## The tools

| Tool | `readOnlyHint` | What it does |
|---|---|---|
| `list_schemas` | ✓ | "List all schemas in the database" |
| `list_objects` | ✓ | "List objects in a schema" — `table` / `view` / `sequence` / `extension` |
| `get_object_details` | ✓ | "Show detailed information about a database object" |
| `explain_query` | ✓ | execution plan, optionally `ANALYZE`, optionally with **hypothetical indexes** |
| `analyze_workload_indexes` | ✓ | "Analyze frequently executed queries in the database and recommend optimal indexes" |
| `analyze_query_indexes` | ✓ | same, for up to 10 supplied queries |
| `analyze_db_health` | ✓ | a menu of named health checks |
| `get_top_queries` | ✓ | slowest / most resource-intensive, via `pg_stat_statements` |
| `execute_sql` | **mode-dependent** | see below |

Note the shape: **eight discovery/diagnosis tools and one execution
tool.** Everything a text-to-SQL agent normally does by writing
`SELECT … FROM information_schema.columns` is a first-class call with a
typed result. That is the strongest available argument for focused tools
over a general one in this domain — not that the general tool can't do
it, but that the schema query is written wrong often enough, and is
common enough, to be worth owning.

## The mode switch, and why it belongs in the description

```python
class AccessMode(str, Enum):
    """SQL access modes for the server."""
    UNRESTRICTED = "unrestricted"  # Unrestricted access
    RESTRICTED = "restricted"      # Read-only with safety features


async def get_sql_driver() -> Union[SqlDriver, SafeSqlDriver]:
    base_driver = SqlDriver(conn=db_connection)
    if current_access_mode == AccessMode.RESTRICTED:
        return SafeSqlDriver(sql_driver=base_driver, timeout=30)  # 30 second timeout
    else:
        return base_driver
```

and then, at registration time:

```python
if current_access_mode == AccessMode.UNRESTRICTED:
    mcp.add_tool(
        execute_sql,
        description="Execute any SQL query",
        annotations=ToolAnnotations(
            title="Execute SQL",
            destructiveHint=True,
        ),
    )
else:
    mcp.add_tool(
        execute_sql,
        description="Execute a read-only SQL query",
        annotations=ToolAnnotations(
            title="Execute SQL (Read-Only)",
            readOnlyHint=True,
        ),
    )
```

**Three things move together**: the driver (enforcement), the description
(what the model believes), and the annotations (what the host uses to
decide whether to prompt the user). Most servers move only the first, and
the result is a model that keeps writing `UPDATE` statements against a
read-only connection, burning turns on errors it was never told to
expect — and a host that cannot tell the two configurations apart.

This is the mechanism-side answer to the thing Open Interpreter's
Postgres profile does with prose (*"Remember to only query the
`{db_name}` database"*). See
[`../../agent-permissions-approval.md`](../../agent-permissions-approval.md)
for the general principle; this is the cleanest instance of it in a data
tool.

## `SafeSqlDriver`: an allowlist over the parse tree

```python
class SafeSqlDriver(SqlDriver):
    """A wrapper around any SqlDriver that only allows SELECT, ANALYZE, VACUUM, EXPLAIN SELECT, and
    SHOW queries.

    Uses pglast to parse and validate SQL statements before execution.
    All other statement types (DDL, DML etc) are rejected.
    Performs deep validation of the query tree to prevent unsafe operations.
    """

    ALLOWED_STMT_TYPES: ClassVar[set[type]] = {
        SelectStmt,           # Regular SELECT
        ExplainStmt,          # EXPLAIN SELECT
        CreateExtensionStmt,  # CREATE EXTENSION
        VariableShowStmt,     # SHOW statements
        VacuumStmt,           # VACUUM and ANALYZE statements
        PrepareStmt,          # PREPARE statement (for prepared queries)
        DeallocateStmt,       # DEALLOCATE statement
        DeclareCursorStmt,    # DECLARE CURSOR
        ClosePortalStmt,      # CLOSE
        FetchStmt,            # FETCH
        # ExecuteStmt,        # (commented out)
        # CopyStmt,           # COPY TO (for exporting query results - will be validated to ensure COPY FROM is not allowed)
        # DiscardStmt,        # DISCARD
        # CheckPointStmt,     # CHECKPOINT
        # ListenStmt, UnlistenStmt, VariableSetStmt
    }

    ALLOWED_FUNCTIONS: ClassVar[set[str]] = {
        "array_agg", "avg", "bit_and", "bit_or", "bool_and", "bool_or",
        "count", "every", "json_agg", "jsonb_agg", ...
    }
```

Four things to take:

**Allowlist of statement *node types*, not a blocklist of keywords.**
Compare [`../pandasai/`](../pandasai)'s
`[r"\bINSERT\b", r"\bUPDATE\b", …]`. A blocklist has to anticipate every
dangerous construct and loses to the first one it didn't think of; an
allowlist of ten node types is short, auditable, and closed. `pglast` is
Postgres's own parser, so the model's SQL is validated by the same
grammar that will execute it — no dialect gap to exploit.

**Functions are allowlisted too.** Statement type alone is not enough:
`SELECT pg_read_file('/etc/passwd')` is a perfectly good `SelectStmt`.
This is the "deep validation of the query tree" the docstring promises,
and it is the step most implementations skip.

**The commented-out entries are the design record.** `CopyStmt` with
*"will be validated to ensure COPY FROM is not allowed"*, `ExecuteStmt`
next to an allowed `PrepareStmt`, `VariableSetStmt` with *"will be
validated"* — each is a capability someone wanted, understood the risk
of, and left off pending the validation work. Keeping them visible is
better documentation of the threat model than a paragraph would be.

**A 30-second timeout is part of "safe".** Read-only is not the same as
harmless: an unbounded `SELECT` against a large table is a denial of
service on a shared warehouse. The timeout lives in the safe driver
precisely because the restricted mode is the one that will be pointed at
production.

## `explain_query` with hypothetical indexes

```python
hypothetical_indexes: list[dict[str, Any]] = Field(
    description="""A list of hypothetical indexes to simulate. Each index must be a dictionary with these keys:
    - 'table': The table name to add the index to (e.g., 'users')
    - 'columns': List of column names to include in the index (e.g., ['email'] or ['last_name', 'first_name'])
    - 'using': Optional index method (default: 'btree', other options include 'hash', 'gist', etc.)

Examples: [
    {"table": "users", "columns": ["email"], "using": "btree"},
    {"table": "orders", "columns": ["user_id", "created_at"]}
]
If there is no hypothetical index, you can pass an empty list.""",
    default=[],
)
```

Backed by HypoPG, with an installation check that returns a *message*
rather than an error when the extension is missing, and a guard that
refuses `analyze` and hypothetical indexes together (you cannot really
run a query against an index that doesn't exist).

This is a **counterfactual tool** — "what would happen if" — and it is
the only one in this collection. It is worth noticing as a category: the
model can test a hypothesis about a change without making the change.
The obvious analogue for a coding agent is a dry-run build or a
type-check against a proposed edit, and for a data agent, a query plan
against a proposed materialisation.

Two schema-design details worth copying: the parameter description
carries **two worked examples including a multi-column index**, and it
explicitly states what to pass in the null case (*"If there is no
hypothetical index, you can pass an empty list"*) — which is the single
most common source of a malformed call on an optional array parameter.
