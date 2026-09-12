# MetaGPT — Data Interpreter

- **Type**: plan-then-execute data-science agent · **Vendor**: DeepWisdom /
  FoundationAgents · **Licence**: MIT
- **Source**: https://github.com/FoundationAgents/MetaGPT — `main` @
  `11cdf46` (2026-01-21). Files under `metagpt/prompts/di/`,
  `metagpt/prompts/task_type.py`, `metagpt/strategy/task_type.py`
- **Retrieved**: 2026-09-12

The "Data Interpreter" role: a plan of typed tasks, executed one at a
time into **a single continuous Jupyter kernel**, with a reflection loop
on failure. Two mechanisms here are not found anywhere else in this
folder.

## 1. Task types carry injected guidance

```python
class TaskType(Enum):
    """By identifying specific types of tasks, we can inject human priors (guidance) to help task solving"""

    EDA = TaskTypeDef(name="eda", desc="For performing exploratory data analysis", guidance=EDA_PROMPT)
    DATA_PREPROCESS = TaskTypeDef(
        name="data preprocessing",
        desc="For preprocessing dataset in a data analysis or machine learning task ONLY,"
             "general data operation doesn't fall into this type",
        guidance=DATA_PREPROCESS_PROMPT,
    )
    FEATURE_ENGINEERING = TaskTypeDef(name="feature engineering", desc="Only for creating new columns for input data.", guidance=FEATURE_ENGINEERING_PROMPT)
    MODEL_TRAIN = TaskTypeDef(name="model train", desc="Only for training model.", guidance=MODEL_TRAIN_PROMPT)
    MODEL_EVALUATE = TaskTypeDef(name="model evaluate", desc="Only for evaluating model.", guidance=MODEL_EVALUATE_PROMPT)
    IMAGE2WEBPAGE = TaskTypeDef(name="image2webpage", desc="For converting image into webpage code.", guidance=IMAGE2WEBPAGE_PROMPT)
    OTHER = TaskTypeDef(name="other", desc="Any tasks not in the defined categories")
```

The planner labels each step with a type; the executor prepends that
type's `guidance` to the code-writing prompt. **Conditional prompt
loading keyed on a planner-assigned label** — the same economics as a
skill, decided by the plan rather than by the model mid-turn, and
therefore cheaper and more predictable. The docstring states the thesis
plainly: *"By identifying specific types of tasks, we can inject human
priors (guidance) to help task solving."*

The guidance itself is domain scar tissue. `EDA_PROMPT` is two lines;
the interesting ones are longer. From `DATA_PREPROCESS_PROMPT`:

```
- Monitor data types per column, applying appropriate methods.
- Ensure operations are on existing dataset columns.
- Avoid writing processed data to files.
- **ATTENTION** Do NOT make any changes to the label column, such as standardization, etc.
- Prefer alternatives to one-hot encoding for categorical data.
- Only encode or scale necessary columns to allow for potential feature-specific engineering tasks (like time_extract, binning, extraction, etc.) later.
- Each step do data preprocessing to train, must do same for test separately at the same time.
- Always copy the DataFrame before processing it and use the copy to process.
```

From `FEATURE_ENGINEERING_PROMPT`:

```
- Generate as diverse features as possible to improve the model's performance step-by-step.
- Avoid creating redundant or excessively numerous features in one step.
- Exclude ID columns from feature generation and remove them.
- Each feature engineering operation performed on the train set must also applies to the dev/test separately at the same time.
- **ATTENTION** Do NOT use the label column to create features, except for cat encoding.
- Use the data from previous task result if exist, do not mock or reload data yourself.
- Always copy the DataFrame before processing it and use the copy to process.
```

Three themes recur across all six and are worth lifting out, because they
are the *content* of "data analysis expertise" reduced to rules:

- **Leakage.** "Do NOT make any changes to the label column"; "Do NOT use
  the label column to create features"; "Each step … must also apply to
  the dev/test separately". Every one is a target-leakage or
  train/test-skew guard. These are the errors that produce a model with
  0.99 validation accuracy and no value, and they are invisible in the
  output.
- **Continuity of state.** "Use the data from previous task result if
  exist, **do not mock or reload data yourself**" appears in three of the
  six. A model that cannot see the kernel's namespace will helpfully
  re-read the CSV and silently discard four steps of preprocessing.
- **Aliasing.** "Always copy the DataFrame before processing it" in two.
  A pandas in-place mutation in step 4 changes what step 2 produced, and
  nothing says so.

`MODEL_TRAIN_PROMPT` is the outlier — it is a *capability advertisement*
rather than a set of guards ("you have access to XGBoost, CatBoost …",
"Avoid the use of SVM because of its high training time", "feel free to
use models of any complexity"), ending with a statement of the user's
preferences ("your user prioritizes results and is highly focused on
model performance"). Different genre, same slot.

## 2. `CHECK_DATA_PROMPT` — the model writes its own state probe

```
# Background
Check latest data info to guide subsequent tasks.

## Finished Tasks
```python
{code_written}
```end

# Task
Check code in finished tasks, print key variables to guide your following actions.
Specifically, if it is a data analysis or machine learning task, print the the latest column information using the following code, with DataFrame variable from 'Finished Tasks' in place of df:
```python
from metagpt.tools.libs.data_preprocess import get_column_info

column_info = get_column_info(df)
print("column_info")
print(column_info)
```end
Otherwise, print out any key variables you see fit. Return an empty string if you think there is no important data to check.

# Constraints:
- Your code is to be added to a new cell in jupyter.

# Instruction
Output code following the format:
```python
your code
```
```

The printed output is then folded back in as:

```
# Latest Data Info
Latest data info after previous tasks:
{info}
```

This is the **third distinct answer** in this folder to the problem a
persistent kernel creates — that the model's transcript and the kernel's
namespace drift apart:

| Harness | Mechanism |
|---|---|
| marimo | harness introspects the namespace and renders it every turn |
| jupyter-mcp | model probes on demand with `execute_code` |
| **MetaGPT DI** | **harness prompts a second model call to write a probe cell, runs it, and injects the output** |
| Data Formulator | no persistent namespace; the problem does not arise |

MetaGPT's is the most expensive (an extra LLM call and an extra cell per
task) and the least reliable (the model may print the wrong things, or
return the empty string). But it is the only one that works when the
harness **cannot introspect the runtime** — which is the general case for
a remote sandbox, a database session, or a Spark cluster. The escape
hatch matters: *"Return an empty string if you think there is no
important data to check"* is what stops it firing on every step.

Note also the constraint: *"Your code is to be added to a new cell in
jupyter"* — the probe is a durable notebook cell, not an ephemeral one.
Compare jupyter-mcp, which would make exactly this an `execute_code`
call, and the reasoning behind that choice ("do not perform variable
assignments that affect subsequent Notebook execution" — a `print` does
not, so it qualifies).

## 3. The interpreter system message

```
As a data scientist, you need to help user to achieve their goal step by step in a continuous Jupyter notebook.
Since it is a notebook environment, don't use asyncio.run. Instead, use await if you need to call an async function.
If you want to use shell command such as git clone, pip install packages, navigate folders, read file, etc., use Terminal tool if available. DON'T use ! in notebook block.
Don't write all codes in one response, each time, just write code for one step or current task.
While some concise thoughts are helpful, code is absolutely required. Always output one and only one code block in your response.
```

Five lines, four of which are environment quirks (`asyncio.run` fails
under an already-running loop; `!` shell escapes are discouraged in
favour of a real tool; one step at a time; exactly one code block). The
last is a **parser contract** — the harness extracts the first fenced
block — and it is stated as a rule because the failure is a silent
mis-parse rather than an error.

The structural prompt around it is small and slot-shaped:

```
# User Requirement
{user_requirement}

# Plan Status
{plan_status}

# Tool Info
{tool_info}

# Constraints
- Take on Current Task if it is in Plan Status, otherwise, tackle User Requirement directly.
- Ensure the output new code is executable in the same Jupyter notebook as the previous executed code.
- Always prioritize using pre-defined tools for the same functionality.
```

## 4. Reflection with a worked example

On failure the harness re-prompts with a fixed two-part contract —
`[reflection on previous impl]` then `[improved impl]` — primed by a
`DEBUG_REFLECTION_EXAMPLE` in which a trivial `add` function subtracts.
The example is deliberately beneath the model's level: it is teaching the
*format and the move* (diagnose in prose, then rewrite in full), not the
debugging. The final instruction guards the common failure:

> Don't forget to write code for steps behind the error step.

A model given an error and a program tends to return only the fixed
fragment; in a kernel, the rest of the cell never ran.

The reflection system message also carries a single environment-specific
repair recipe, which is the kind of thing that only gets written after
watching a hundred runs:

> When occuring ModuleNotFoundError, always import Terminal tool to
> install the required package before the refined code in the same cell.

## 5. Role guidance (`data_analyst.py`)

Numbered instructions appended to a shared role prompt. The routing rules
are the interesting part:

```
6. Carefully consider how you handle web tasks:
 - Use SearchEnhancedQA for general information searching …
 - Use Browser for reading, navigating, or in-domain searching within a specific web …
 - Use DataAnalyst.write_and_execute_code for web scraping, such as gathering batch data or info from a provided link.
 - Write code to view the HTML content rather than using the Browser tool.
7. When you are making plan. It is highly recommend to plan and append all the tasks in first response once time, except for 7.1.
7.1. When the requirement is inquiring about a pdf, docx, md, or txt document, read the document first through either Editor.read WITHOUT a plan. After reading the document, use RoleZero.reply_to_human if the requirement can be answered straightaway, otherwise, make a plan if further calculation is needed.
8. Don't finish_current_task multiple times for the same task.
9. Finish current task timely, such as when the code is written and executed successfully.
10. When using the command 'end', add the command 'finish_current_task' before it.
```

Rule 6 is a **three-way disambiguation between overlapping capabilities**
— search, browse, scrape — resolved by what the user is trying to get
(an answer / a page / a batch), not by what the tools are called. Any
harness with both a browser and a code tool needs this paragraph, and
most don't have it.

Rules 7/7.1 encode a cost decision: plan everything up front *except*
when the task might be answerable by a single read, in which case read
first and skip planning. Rules 8–10 are state-machine hygiene, and their
existence is a small indictment of the state machine.
