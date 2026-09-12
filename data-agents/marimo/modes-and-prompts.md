# marimo — prompt assembly

From `marimo/_server/ai/prompts.py` (477 lines) at `1793fe5`.

## Mode intros, verbatim

```python
base_intro = (
    "You are Marimo Copilot, an AI assistant integrated into the marimo notebook code editor.\n"
    "Your primary function is to help users create, analyze, and improve data science notebooks using marimo's reactive programming model.\n"
)
```

**`manual`**

```
## Capabilities
- Answer questions and provide guidance using only your internal knowledge and the notebook context provided by the user.

## Limitations
- You do NOT have access to any external tools, plugins, or APIs.
- You may not perform any actions beyond generating text and code suggestions.
```

**`ask`**

```
## Capabilities
- You can use a set of read-only tools to gather additional context from the notebook or environment (e.g., searching code, summarizing data, or reading documentation).
- You may use these tools ONLY to gather information, not to modify code or state.

## Limitations
- All tool use is strictly read-only. You may not perform write, edit, or execution actions.
- You must always explain to the user why you are using a tool before invoking it.
```

**`agent`**

```
You are in agent mode - you have autonomy to resolve the user's query by using the tools provided. Please keep going until the user's query is completely resolved, before ending your turn and yielding back to the user. Only terminate your turn when you are sure that the problem is solved.

## Agent Mode
- You are encouraged to edit existing cells in the notebook or add new cells.
- You should do the following things after editing the notebook:
	 1. Use the lint notebook tool to check for errors and lint issues
	 2. Run stale cells tool to run the code
	 3. If there are errors in cells you have added, edit the existing cell. Don't add new cells to correct errors.
- If you say you're about to do something, actually do it in the same turn (run the tool call right after).
- Group code into logical cells, eg. functions should be in separate cells and all the calls will be in one cell. When asked for explanations or summaries, use markdown cells with proper formatting.

## Capabilities
- You can use a set of read and write tools to gather additional context from the notebook or environment (e.g., searching code, summarizing data, or reading documentation) and to modify the notebook (e.g., adding cells, editing cells, deleting cells).
## Limitations
- You must always explain to the user why you are using a tool before invoking it.
```

**`code_mode`**

```
You are in code mode - you have access to the notebook's kernel and can execute code.
```

The `Capabilities` / `Limitations` pair is generated from one switch, so
the two can't drift. `agent`'s "keep going until the user's query is
completely resolved" is the standard persistence paragraph (near-verbatim
across several sources in this collection); what marimo adds is the
**three-step post-edit verification** and the same-turn rule.

## Kernel state → context

Three formatters build the context block. This is how a notebook harness
answers the question a stateful kernel creates: *the model's transcript
and the kernel's namespace are different things, and the model can only
see one of them.*

```python
def _format_variables(variables) -> str:
    variable_info = "\n\n## Available variables from other cells:\n"
    for variable in variables:
        if isinstance(variable, VariableContext):
            if _is_private_variable := variable.name.startswith("_"):
                continue
            variable_info += f"- variable: `{variable.name}`\n"
            variable_info += f"  - value_type: {variable.value_type}\n"
            variable_info += f"  - value_preview: {variable.preview_value}\n"
```

```python
def _format_schema_info(tables) -> str:
    schema_info = "\n\n## Available schema:\n"
    for schema in tables:
        schema_info += f"- Table: {schema.name}\n"
        for col in schema.columns:
            schema_info += f"  - Column: {col.name}\n"
            schema_info += f"    - Type: {col.type}\n"
            if col.sample_values:
                samples = ", ".join(f"{v}" for v in col.sample_values)
                schema_info += f"    - Sample values: {samples}\n"
```

Name, type, preview for variables; name, type, sample values per column
for tables. **Private (`_`-prefixed) variables are filtered out** — the
same rule the reactive graph uses for what is notebook-level, applied to
what the model is told about. The agent sees the public surface of the
namespace, not the whole namespace.

Compare the three other answers to the same problem in this folder:

| Harness | How the model learns what is in the kernel |
|---|---|
| **marimo** | harness introspects and renders it into context every turn |
| **MetaGPT DI** | model is prompted to *write a cell* that prints it (`CHECK_DATA_PROMPT`) |
| **jupyter-mcp** | model calls `execute_code` with `print(x)` / `df.head()` on demand |
| **Data Formulator** | not applicable — no persistent namespace to diverge |

Only the first is free of the risk that the model forgets to look.

There is also `_format_plain_text`, which fronts user-attached context
with a mention-resolution instruction:

```python
return f"If the prompt mentions @kind://name, use the following context to help you answer the question:\n\n{plain_text}"
```

— a scheme-shaped mention syntax (`@kind://name`) resolved by the harness
before the model sees it, which is the same move as the ref grammar in
[`../../agent-design/artifacts.md`](../../agent-design/artifacts.md) §2
arriving from the UI side.

## Per-language rules

Two dicts: `language_rules` (for modes that emit one cell at a time) and
`language_rules_multiple_cells` (for agent mode), the latter falling back
to the former per language.

**Python:**

```
1. For matplotlib: use plt.gca() as the last expression instead of plt.show().
2. For plotly: return the figure object directly.
3. For altair: return the chart object directly. Add tooltips where appropriate. You can pass polars dataframes directly to altair (e.g., alt.Chart(df)).
4. Include proper labels, titles, and color schemes.
5. Make visualizations interactive where appropriate.
6. If an import already exists, do not import it again.
7. If a variable is already defined, use another name, or make it private by adding an underscore at the beginning.
```

Rules 1–3 are the marimo equivalent of Open Interpreter forcing the `Agg`
backend: in a reactive notebook a cell's *last expression* is its output,
so `plt.show()` produces nothing and `plt.gca()` produces the plot. Rules
6–7 are the dataflow contract leaking into style guidance — necessary,
because violating them is a hard error (`Multiply-defined names`), not a
lint.

**SQL, single-cell:** `The SQL must use duckdb syntax.`

**SQL, multi-cell (agent mode):**

```
1. SQL cells start with df = mo.sql(f"""<your query>""") for DuckDB, or df = mo.sql(f"""<your query>""", engine=engine) for other SQL engines. You should always write queries inline as the code snippet above, do not use variables to store queries.
2. This will automatically display the result in the UI. You do not need to return the dataframe in the cell.
3. The SQL must use the syntax of the database engine specified in the `engine` variable. If no engine, then use duckdb syntax.
```

**SQL is a Python cell with a `mo.sql()` call in it**, not a separate
tool and not a separate cell type at the protocol level. Same conclusion
as Data Formulator (DuckDB in the sandbox) and pandasai (an injected
`execute_sql_query` function) reached by a different route: the model
writes one language, and SQL is a string inside it.

"Do not use variables to store queries" exists so the query text is
statically visible in the cell — for the reader, and for marimo's own
parser. An f-string interpolating a variable would defeat both.

**Markdown:** `Use double dollar signs ($$) for ALL mathematical
expressions … Do NOT use single dollar signs or square brackets for
math.` A renderer constraint, stated as a rule, because the failure is
silent (the math renders as literal text).
