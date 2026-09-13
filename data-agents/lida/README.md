# LIDA (Microsoft)

- **Type**: visualization-generation pipeline · **Vendor**: Microsoft
  Research (Victor Dibia) · **Licence**: MIT
- **Source**: https://github.com/microsoft/lida — `main` @ `d892e20`
  (2024-03-02)
- **Retrieved**: 2026-09-12

The oldest source in this folder and the one whose structure has aged
best. LIDA is not an agent — it is a **fixed five-stage pipeline** with a
separate prompt per stage:

```
summarize → goals → (scaffold) generate → evaluate → repair
                                    └── explain, edit, recommend, infographic
```

Worth reading now for three things: the **summary-not-data** rule, the
**code scaffold** as a third point between free code and a declarative
spec, and a **six-dimension self-evaluation rubric** that is the closest
thing in this collection to a chart code review.

## 1. The data never enters the prompt — a summary does

`Summarizer.get_column_properties` walks the DataFrame and builds, per
column: `dtype` (normalised to `number` / `boolean` / `date` /
`category` / `string`), `std`/`min`/`max` for numerics, sample values,
and cardinality. The category test is a ratio, not a threshold on count:

```python
elif dtype == object:
    try:
        pd.to_datetime(df[column], errors='raise')
        properties["dtype"] = "date"
    except ValueError:
        if df[column].nunique() / len(df[column]) < 0.5:
            properties["dtype"] = "category"
        else:
            properties["dtype"] = "string"
```

An LLM pass then annotates that skeleton:

```
You are an experienced data analyst that can annotate datasets. Your instructions are as follows:
i) ALWAYS generate the name of the dataset and the dataset_description
ii) ALWAYS generate a field description.
iii.) ALWAYS generate a semantic_type (a single word) for each field given its values e.g. company, city, number, supplier, location, gender, longitude, latitude, url, ip address, zip code, email, etc
You must return an updated JSON dictionary without any preamble or explanation.
```

**Two-stage summarisation — deterministic statistics first, semantics
second** — is the pattern. The stats are cheap, exact and computed; the
semantic type is a judgement and costs a model call. Every downstream
prompt sees only the summary, never rows.

The `semantic_type` field is doing the same job as Data Formulator's
`field_metadata` and Positron's column profiles: **telling the renderer
what a number means**. `longitude` is not a quantity to average; a
`zip code` is not an integer to sum.

## 2. The scaffold: the model fills in blanks

`ChartScaffold.get_template` returns a **partial program** per library,
and the model may only complete the marked regions:

```python
f"""
import matplotlib.pyplot as plt
import pandas as pd
<imports>
# plan -
def plot(data: pd.DataFrame):
    <stub> # only modify this section
    plt.title('{goal.question}', wrap=True)
    return plt;

chart = plot(data) # data already contains the data to be plotted. Always include this line. No additional code beyond this line."""
```

with instructions:

> Solve the task carefully by completing ONLY the `<imports>` AND `<stub>`
> section. Given the dataset summary, the plot(data) method should generate
> a {library} chart ({goal.visualization}) that addresses this goal:
> {goal.question}. **DO NOT WRITE ANY CODE TO LOAD THE DATA. The data is
> already loaded and available in the variable data.**

Five libraries get a scaffold — matplotlib, seaborn, ggplot (plotnine),
altair, plotly — each with its own return contract ("must return a
matplotlib object (plt)", "must return a ggplot object (chart)"). The
shared instructions carry hard-won specifics:

> If the solution requires a single value (e.g. max, min, median, first,
> last etc), ALWAYS add a line (axvline or axhline) to the chart, ALWAYS
> with a legend containing the single value (formatted with 0.2F). If using
> a `<field>` where semantic_type=date, YOU MUST APPLY the following
> transform before using that column i) convert date fields to date types
> using `data[''] = pd.to_datetime(data[<field>], errors='coerce')`, ALWAYS
> use `errors='coerce'` ii) drop the rows with NaT values
> `data = data[pd.notna(data[<field>])]` iii) convert field to right time
> format for plotting. ALWAYS make sure the x-axis labels are legible (e.g.,
> rotate when needed).

**This is the third position on the "who draws" spectrum**, and it is
under-used:

| Position | Model emits | Harness controls | Example |
|---|---|---|---|
| Free code | a whole program | nothing | Open Interpreter, jupyter-mcp |
| **Scaffold** | **the blanks** | **imports, entry point, title, return value, the `chart = plot(data)` line** | **LIDA** |
| Declarative spec | data + encodings | the entire rendering | Data Formulator |

The scaffold keeps the model's expressive power (any matplotlib call is
available inside `<stub>`) while making the *contract* unbreakable — the
function signature, the variable that holds the data, the title, the
return value, and the guarantee that nothing runs after `chart =
plot(data)`. It is the cheapest way to get a predictable artifact out of
free-form code generation, and it composes with an existing plotting
library rather than requiring a renderer to be built.

## 3. The six-dimension rubric

`VizEvaluator`'s system prompt, verbatim:

```
You are a helpful assistant highly skilled in evaluating the quality of a given visualization code by providing a score from 1 (bad) - 10 (good) while providing clear rationale. YOU MUST CONSIDER VISUALIZATION BEST PRACTICES for each evaluation. Specifically, you can carefully evaluate the code across the following dimensions
- bugs (bugs):  are there bugs, logic errors, syntax error or typos? Are there any reasons why the code may fail to compile? How should it be fixed? If ANY bug exists, the bug score MUST be less than 5.
- Data transformation (transformation): Is the data transformed appropriately for the visualization type? E.g., is the dataset appropriated filtered, aggregated, or grouped  if needed?
- Goal compliance (compliance): how well the code meets the specified visualization goals?
- Visualization type (type): CONSIDERING BEST PRACTICES, is the visualization type appropriate for the data and intent? Is there a visualization type that would be more effective in conveying insights? If a different visualization type is more appropriate, the score MUST be less than 5.
- Data encoding (encoding): Is the data encoded appropriately for the visualization type?
- aesthetics (aesthetics): Are the aesthetics of the visualization appropriate for the visualization type and the data?

You must provide a score for each of the above dimensions.  Assume that data in chart = plot(data) contains a valid dataframe for the dataset. The `plot` function returns a chart (e.g., matplotlib, seaborn etc object).

Your OUTPUT MUST BE A VALID JSON LIST OF OBJECTS in the format:

```[
{ "dimension":  "bugs",  "score": x , "rationale": " .."}, { "dimension":  "transformation",  "score": x, "rationale": " .."}, { "dimension":  "compliance",  "score": x, "rationale": " .."},{ "dimension":  "type",  "score": x, "rationale": " .."}, { "dimension":  "encoding",  "score": x, "rationale": " .."}, { "dimension":  "aesthetics",  "score": x, "rationale": " .."}
]
```
```

Then `VizRepairer` takes `feedback` (the evaluation), the goal, the
summary and the original code, and returns a full program — under the
same scaffold.

Two things to note against
[`../../code-review-approaches.md`](../../code-review-approaches.md):

**The score-forcing clauses are the mechanism.** *"If ANY bug exists, the
bug score MUST be less than 5"* and *"If a different visualization type
is more appropriate, the score MUST be less than 5"* exist because
LLM judges regress to 7/10. Pinning specific findings to specific score
ranges is the same move as requiring a severity label to be justified,
and it is what makes the score usable as a **gate** rather than as
decoration.

**It is a review agent for charts, and it is separate from the author.**
Generate → evaluate → repair, with the evaluator seeing the code and the
goal but not the author's reasoning. That is the specialist/validator
split Forge's review mode uses, applied to a visualization. The
difference — and the limitation — is that the evaluator sees **the code,
not the picture**. A legend that collides, an axis that overflows, a
colour scale that is illegible in dark mode: none of those are visible in
the source. [`../marimo/`](../marimo)'s `ctx.screenshot()` is what closes
that gap, seven years later.

## 4. Goals, and personas

`GoalExplorer` turns a summary into `n` structured goals:

```
You are a an experienced data analyst who can generate a given number of insightful GOALS about data, when given a summary of the data, and a specified persona. The VISUALIZATIONS YOU RECOMMEND MUST FOLLOW VISUALIZATION BEST PRACTICES (e.g., must use bar charts instead of pie charts for comparing quantities) AND BE MEANINGFUL (e.g., plot longitude and latitude on maps where appropriate). They must also be relevant to the specified persona. Each goal must include a question, a visualization (THE VISUALIZATION MUST REFERENCE THE EXACT COLUMN FIELDS FROM THE SUMMARY), and a rationale (JUSTIFICATION FOR WHICH dataset FIELDS ARE USED and what we will learn from the visualization). Each goal MUST mention the exact fields from the dataset summary above
```

```json
[
    { "index": 0,  "question": "What is the distribution of X", "visualization": "histogram of X", "rationale": "This tells about "}
]
```

The default persona when none is supplied is *"A highly skilled data
analyst who can come up with complex, insightful goals about data"*.

The repeated demand for **exact field names from the summary** (stated
three times in one paragraph) is grounding-by-repetition, and it is the
same problem Data Formulator solves with *"Never output placeholder
identifiers like your_table_name"*. A goal that names a column that
doesn't exist fails two stages later, in generated code, as a
`KeyError` — far from where it was introduced.

The **persona** parameter is the notable design idea, and one no other
source here has: the same summary yields different goals for a CFO, a
supply-chain analyst and a journalist. It is a cheap, honest handle on
"what question is worth asking", which is otherwise the least
tractable part of autonomous analysis.
