# Vanna 2.0 — `RunSqlTool`

`src/vanna/tools/run_sql.py`. The `SELECT` branch of `execute()`,
abridged to the parts that matter, verbatim otherwise.

## The tool

```python
class RunSqlTool(Tool[RunSqlToolArgs]):
    """Tool that executes SQL queries using an injected SqlRunner implementation."""

    def __init__(
        self,
        sql_runner: SqlRunner,
        file_system: Optional[FileSystem] = None,
        custom_tool_name: Optional[str] = None,
        custom_tool_description: Optional[str] = None,
    ):
        ...

    @property
    def name(self) -> str:
        return self._custom_name if self._custom_name else "run_sql"

    @property
    def description(self) -> str:
        return (
            self._custom_description
            if self._custom_description
            else "Execute SQL queries against the configured database"
        )
```

```python
class RunSqlToolArgs(BaseModel):
    """Arguments for run_sql tool."""
    sql: str = Field(description="SQL query to execute")
```

One argument. Nine words of default description. Everything else is
injected: the `SqlRunner` (an abstract `async run_sql(args, context) ->
pd.DataFrame`), the `FileSystem`, and — notably — **the name and
description themselves are overridable at construction**, so a deployment
with three databases registers three tools called `run_sql_warehouse`,
`run_sql_crm`, `run_sql_events` with descriptions that name the domain.
That is the cheap and correct answer to "one SQL tool or one per
database", and it costs nothing at the schema level.

## The `SELECT` branch

```python
df = await self.sql_runner.run_sql(args, context)
query_type = args.sql.strip().upper().split()[0]

if query_type == "SELECT":
    if df.empty:
        result = "Query executed successfully. No rows returned."
        ...
        metadata = {"row_count": 0, "columns": [], "query_type": query_type, "results": []}
    else:
        results_data = df.to_dict("records")
        columns = df.columns.tolist()
        row_count = len(df)

        # Write DataFrame to CSV file for downstream tools
        file_id = str(uuid.uuid4())[:8]
        filename = f"query_results_{file_id}.csv"
        csv_content = df.to_csv(index=False)
        await self.file_system.write_file(filename, csv_content, context, overwrite=True)

        # Create result text for LLM with truncated results
        results_preview = csv_content
        if len(results_preview) > 1000:
            results_preview = (
                results_preview[:1000]
                + "\n(Results truncated to 1000 characters. FOR LARGE RESULTS YOU DO NOT NEED TO SUMMARIZE THESE RESULTS OR PROVIDE OBSERVATIONS. THE NEXT STEP SHOULD BE A VISUALIZE_DATA CALL)"
            )

        result = f"{results_preview}\n\nResults saved to file: {filename}\n\n**IMPORTANT: FOR VISUALIZE_DATA USE FILENAME: {filename}**"

        dataframe_component = DataFrameComponent.from_records(
            records=results_data,
            title="Query Results",
            description=f"SQL query returned {row_count} rows with {len(columns)} columns",
        )

        ui_component = UiComponent(
            rich_component=dataframe_component,
            simple_component=SimpleTextComponent(text=result),
        )

        metadata = {
            "row_count": row_count,
            "columns": columns,
            "query_type": query_type,
            "results": results_data,
            "output_file": filename,
        }

return ToolResult(
    success=True,
    result_for_llm=result,
    ui_component=ui_component,
    metadata=metadata,
)
```

## Six things to take from twenty lines

**1. The tool writes the artifact.** The model asked for SQL; it gets
back a file it never created and a name it never chose. The tool minted
`query_results_<8 hex>.csv` and put the bytes there. This is the
mechanism the artifact discussion in
[`../../agent-design/artifacts.md`](../../agent-design/artifacts.md) is
about, in its simplest possible form — a filename as the handle, a
`FileSystem` capability as the store.

**2. The preview and the handle travel together.** `result_for_llm` is
*both* a thousand characters of actual CSV *and* the filename. The model
can answer "what were the top three?" from the preview without a second
call, and can pass the whole thing onward without ever seeing it. Neither
alone would do: a bare handle costs a round-trip for every trivial
question; a bare preview cannot be chained.

**3. The truncation notice names the next call.** Not "output truncated"
but *"THE NEXT STEP SHOULD BE A VISUALIZE_DATA CALL"*, followed by
`**IMPORTANT: FOR VISUALIZE_DATA USE FILENAME: {filename}**`. Two
separate statements of the same instruction — the notice and the
trailing line — because it is the one thing that must survive.

**4. It pre-empts the summarise-everything reflex.** *"FOR LARGE RESULTS
YOU DO NOT NEED TO SUMMARIZE THESE RESULTS OR PROVIDE OBSERVATIONS."* A
model handed 1,000 characters of CSV will narrate it; the narration is
worthless when the next step renders the same data as a table. Worth
noting how rare this is: most truncation notices tell the model what was
lost, almost none tell it what not to do with what remains.

**5. `metadata` carries the real shape.** `row_count` and `columns` are
exact, not truncated — so the harness (and the audit log) knows the
result was 40,000 rows even though the model saw ten. The full
`results_data` is there too, for downstream tools that want the values
without re-reading the file.

**6. The dispatch is `sql.strip().upper().split()[0]`.** The branch
between "rows came back" and "rows were affected" is decided by the first
token of the model's SQL string. It works for the common case and is
wrong for a leading comment, a CTE (`WITH … SELECT`), or `EXPLAIN`. The
contrast with [`../postgres-mcp/`](../postgres-mcp) — which parses the
statement with `pglast` and validates the whole tree — is the contrast
between a heuristic and a parser, and it is worth being explicit that
**the heuristic is on the response-shaping path, not the security path**.
Vanna's read-only enforcement, if any, lives in the injected
`SqlRunner`'s connection, which is the right place for it.

## The error branch

```python
except Exception as e:
    error_message = f"Error executing query: {str(e)}"
    return ToolResult(
        success=False,
        result_for_llm=error_message,
        ui_component=UiComponent(
            rich_component=NotificationComponent(type=ComponentType.NOTIFICATION, level="error", message=error_message),
            simple_component=SimpleTextComponent(text=error_message),
        ),
        error=str(e),
        metadata={"error_type": "sql_error"},
    )
```

The database's error text goes to the model verbatim — which is right;
`column "revenu" does not exist … Perhaps you meant "revenue"` is the
most useful repair signal a text-to-SQL agent ever gets, and Postgres
writes it for you. The same text goes to the user as a UI notification,
and `error_type` is tagged for the audit trail.
