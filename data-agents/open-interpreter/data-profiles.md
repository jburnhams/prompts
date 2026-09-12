# Open Interpreter — the two data profiles

`interpreter/terminal_interface/profiles/defaults/` ships 28 profiles.
Two are about data, and between them they demonstrate both halves of the
SQL question this collection keeps running into: **does the agent get a
SQL tool, or does it get SQL through Python?**

Both answer *through Python*. Neither ships a `run_sql` tool.

## `llama31-database.py` — "chat with a database"

Configures a local Ollama model against a Postgres instance. The
connection string is built in Python from environment variables and then
**interpolated into the prompt**:

```python
interpreter.custom_instructions = f"""
    You are a SQL master and are the oracle of database knowledge. You are obsessed with SQL. You only want to discuss SQL. SQL is life.
    Recap the plan before answering the user's query.
    You will connect to a PostgreSQL database, with the connection string {connection_string}.
    Remember to only query the {db_name} database.
    Execute valid SQL commands to satisfy the user's query.
    Write all code in a full Python script. When you have to re-write code, redo the entire script.
    Execute the script to get the answer for the user's query.
    **YOU CAN EXECUTE SQL COMMANDS IN A PYTHON SCRIPT.***
    Get the schema of '{db_name}' before writing any other SQL commands. It is important to know the tables. This will let you know what commands are correct.
    Only use real column names.
    ***You ARE fully capable of executing SQL commands.***
    Be VERY clear about the answer to the user's query. They don't understand technical jargon so make it very clear and direct.
    Today's date is {date.today()}.
    You should respond in a very concise way.
    You can do it, I believe in you.
    """
```

Also set: `interpreter.llm.supports_functions = False`,
`context_window = 7000`, `offline = True`,
`computer.import_computer_api = False`.

What this profile is really documenting is **what you have to write into
a prompt when you decline to build a tool**:

- *"Get the schema of `{db_name}` before writing any other SQL commands"*
  — schema discovery as an instruction, because there is no
  `describe_table` tool to make it a call.
- *"Only use real column names"* — hallucination control as an
  instruction, because nothing validates the SQL against a schema.
- *"Remember to only query the `{db_name}` database"* — scope enforcement
  as an instruction, because the connection is a superuser-ish DSN handed
  to `exec`.
- *"Write all code in a full Python script. When you have to re-write
  code, redo the entire script"* — a whole-file edit policy, invented
  because `supports_functions = False` means diffing is unavailable.

Every one of those is a place where
[`../postgres-mcp/`](../postgres-mcp) has a mechanism instead of a
sentence. The prompt's two shouted assertions that the model *is* capable
of executing SQL (`**YOU CAN EXECUTE SQL COMMANDS IN A PYTHON SCRIPT.***`,
`***You ARE fully capable of executing SQL commands.***`) are a tell:
they exist because a 7B-class model kept refusing, and an instruction is
the only lever available. The closing `You can do it, I believe in you.`
is the same lever.

The credentials-in-the-prompt pattern is worth flagging as a
**negative** example: the DSN, including any password, is rendered into
the system message and therefore into every request, every log and any
transcript. `../../agent-permissions-approval.md` treats secret handling
as a harness responsibility precisely so this cannot happen.

## `snowpark.yml` — "chat with a warehouse"

The other half: a YAML profile whose `custom_instructions` is a **tutorial
with runnable snippets**, teaching the model a specific client library
rather than constraining it.

```yaml
custom_instructions: '''
You are going to be connecting to Snowflake, the cloud data platform. You can use the Snowpark API to interact with Snowflake. Here are some common tasks you might want to do:
- Connect to Snowflake
- Run a query

You can use the Snowpark API to do these tasks. To create a session with snowpark, you have to first import the session object from snowpark and pandas, like so:
```python
from snowflake.snowpark import Session
import pandas as pd
```
If this doesnt work, you may need to run the following commands to install snowpark and pandas:
```python
!pip install snowflake-snowpark-python
!pip install pandas
...
```

Then, you can create a dictionary with the necessary connection parameters and create a session. You will access these values from the
environment variables:
```python
snowflake_account = os.getenv("SNOWFLAKE_ACCOUNT")
snowflake_user = os.getenv("SNOWFLAKE_USER")
...
```
'''
```

Here the credentials are read from the environment *inside the executed
code* rather than interpolated into the prompt — the correct pattern, and
the contrast with the Postgres profile is instructive given they ship
side by side.

The library tutorial in the prompt is what a **skill** is for. This
profile is a skill that predates the format: capability-specific guidance
that should load when the task touches Snowflake and otherwise cost
nothing. Loaded unconditionally as `custom_instructions`, it is paying
its whole token cost on every turn of every conversation, including the
ones about CSV files. [`../data-formulator/`](../data-formulator)'s
`load_skill` and [`../marimo/`](../marimo)'s deferred capabilities are
both answers to that.
