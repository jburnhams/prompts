# PandasAI

- **Type**: natural-language interface over dataframes and SQL sources ·
  **Vendor**: Sinaptik AI · **Licence**: MIT (core)
- **Source**: https://github.com/sinaptik-ai/pandas-ai — `main` @
  `bbbb771` (2025-10-28)
- **Retrieved**: 2026-09-12

Kept for one thing: the clearest example of a **typed return contract
imposed on generated code**, with a corrective re-prompt per contract
violation.

## The contract

`core/prompts/templates/generate_python_code_with_sql.tmpl`:

```jinja
<tables>
{% for df in context.dfs %}
{% include 'shared/dataframe.tmpl' with context %}
{% endfor %}
</tables>

{% include 'shared/sql_functions.tmpl' with context %}

{% if last_code_generated and context.memory.count() > 0 %}
Last code generated:
{{ last_code_generated }}
{% else %}
Update this initial code:
```python
# TODO: import the required dependencies
import pandas as pd

# Write code here

# Declare result var: {% include 'shared/output_type_template.tmpl' with context %}
```
{% endif %}
{% include 'shared/vectordb_docs.tmpl' with context %}
{{ context.memory.get_last_message() }}

At the end, declare "result" variable as a dictionary of type and value in the following format:
{% include 'shared/output_type_template.tmpl' with context %}


Generate python code and return full updated code:

### Note: Use only relevant table for query and do aggregation, sorting, joins and grouby through sql query
```

and `shared/output_type_template.tmpl`:

```jinja
{% if not output_type %}
type (possible values "string", "number", "dataframe", "plot"). Examples: { "type": "string", "value": f"The highest salary is {highest_salary}." } or { "type": "number", "value": 125 } or { "type": "dataframe", "value": pd.DataFrame({...}) } or { "type": "plot", "value": "temp_chart.png" }
{% elif output_type == "number" %}
type (must be "number"), value must int. Example: { "type": "number", "value": 125 }
{% elif output_type == "string" %}
type (must be "string"), value must be string. Example: { "type": "string", "value": f"The highest salary is {highest_salary}." }
{% elif output_type == "dataframe" %}
type (must be "dataframe"), value must be pd.DataFrame or pd.Series. Example: { "type": "dataframe", "value": pd.DataFrame({...}) }
{% elif output_type == "plot" %}
type (must be "plot"), value must be string. Example: { "type": "plot", "value": "temp_chart.png" }
{% endif %}
```

**Four result types, and the caller can pin one.** When the application
knows it wants a number, `output_type="number"` narrows the template to a
single branch — so the contract is *parameterised by the call site*, not
fixed by the prompt. The union branch (no `output_type`) is shown with
one worked example per type, which is the right way to express a
discriminated union to a model.

The corresponding response classes are `StringResponse`,
`NumberResponse`, `DataFrameResponse`, `ChartResponse`, `ErrorResponse`.
`ChartResponse.value` is a path or a data URI, and the class carries
`save()`, `show()` and `get_base64_image()` — i.e. **the type determines
what the host can do with the value**, which is the point of typing it.

The scaffold move from [`../lida/`](../lida) appears here too, in weaker
form: the first turn hands the model a skeleton with `# TODO: import the
required dependencies` / `# Write code here` / `# Declare result var:`
and says *"Update this initial code"*; later turns pass
`last_code_generated` instead. Editing beats authoring, and the harness
never has to parse a free-form response for which part is the program.

## Contract violations get their own repair prompts

Two of the three correction templates exist purely to enforce contracts
the model broke:

`correct_output_type_error_prompt.tmpl` ends:

```
Fix the python code above and return the new python code but the result type should be: {{output_type}}
```

`correct_execute_sql_query_usage_error_prompt.tmpl` ends:

```
Fix the python code above and return the new python code but the code generated should use execute_sql_query function
```

Both share the same body — tables, SQL functions, the conversation, the
code, the error — and differ only in the final instruction. This is
worth noting as a pattern: **one repair prompt per violated invariant**,
rather than a single generic "it failed, fix it". The model is told which
rule it broke, which is a much stronger signal than a stack trace.

## SQL is an injected function, not a tool

`shared/sql_functions.tmpl`:

```jinja
The following functions have already been provided. Please use them as needed and do not redefine them.
<function>
def execute_sql_query(sql_query: str) -> pd.DataFrame
    """This method connects to the database, executes the sql query and returns the dataframe"""
</function>
{% if context.skills|length > 0 %}
{% for skill in context.skills %}
{{ skill }}
{% endfor %}
{% endif %}
```

A **function signature as a tool declaration**, inside the code
environment. The model writes `df = execute_sql_query("SELECT …")` in the
middle of a pandas program; the harness supplies the implementation and
therefore controls the connection, the credentials and the row limits.
The same slot takes user-registered "skills" — additional pre-provided
functions, declared the same way.

This is the fourth distinct answer to "how does an agent reach SQL" in
this folder, and the tidiest:

| Approach | Source |
|---|---|
| SQL as a first-class MCP tool | [`../postgres-mcp/`](../postgres-mcp) |
| SQL as a library call inside the sandbox (DuckDB) | [`../data-formulator/`](../data-formulator), [`../marimo/`](../marimo) |
| SQL as a string inside a Python script the model writes end-to-end | Open Interpreter's Postgres profile |
| **SQL as a pre-provided function injected into the code environment** | **PandasAI, and it is also what Code Mode generalises** |

The last is the one that composes: the result is a DataFrame in the
model's own namespace, so a join between a query result and a CSV is
ordinary pandas rather than a tool-chaining problem.

The closing note on the main template — *"Use only relevant table for
query and do aggregation, sorting, joins and grouby through sql query"* —
is the **push-down rule**: make the database do the heavy work, don't
`SELECT *` and aggregate in pandas. Every harness here that offers both
engines states some version of it (Data Formulator's "prefer plain
pandas… only use DuckDB when the dataset is very large" is the same rule
from the other end, with the threshold set differently).

## SQL safety, by AST

`helpers/sql_sanitizer.py` parses with `sqlglot` rather than matching
strings:

```python
def is_sql_query_safe(query: str, dialect: str = "postgres") -> bool:
    try:
        infected_keywords = [
            r"\bINSERT\b", r"\bUPDATE\b", r"\bDELETE\b", r"\bDROP\b",
            r"\bEXEC\b", r"\bALTER\b", r"\bCREATE\b", ...
        ]
```

…and identifier sanitisation that round-trips through the parser:

```python
def sanitize_view_column_name(relation_name: str) -> str:
    return (
        parse_one(".".join(list(map(sanitize_sql_table_name, relation_name.split(".")))))
        .transform(quote_identifiers)
        .sql()
    )
```

A hybrid: a real parser for identifier quoting, a keyword blocklist for
statement safety. The blocklist half is the weaker half — it is the
approach [`../postgres-mcp/`](../postgres-mcp) rejects in favour of
validating the parsed statement tree against an allowlist of statement
*types*. A blocklist of keywords must enumerate every dangerous
construct; an allowlist of node types has to enumerate the safe ones,
which is a much shorter and much more stable list.
