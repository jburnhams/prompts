# E2B Code Interpreter

- **Type**: sandboxed code-execution service with a Jupyter kernel ·
  **Vendor**: E2B · **Licence**: Apache-2.0 (SDK), MIT
  (`chart_data_extractor`)
- **Source**: https://github.com/e2b-dev/code-interpreter — `main` @
  `f56a1ed` (2026-09-10)
- **Retrieved**: 2026-09-12

The execution substrate under several harnesses in this folder
(jupyter-mcp lists it as one of ten backends). It earns its own entry for
**two custom Jupyter MIME types** that answer the user-facing question
"how does a result get out of a sandbox in a form a model can use?"
better than anything else read here.

## The `Result` type: one cell, every representation

`template/server/api/models/result.py`:

```python
class Result(BaseModel):
    """
    Represents the data to be displayed as a result of executing a cell in a Jupyter notebook.
    ...
    """
    type: OutputType = OutputType.RESULT

    text: Optional[str] = None
    html: Optional[str] = None
    markdown: Optional[str] = None
    svg: Optional[str] = None
    png: Optional[str] = None
    jpeg: Optional[str] = None
    pdf: Optional[str] = None
    latex: Optional[str] = None
    json: Optional[dict] = None
    javascript: Optional[str] = None
    data: Optional[dict] = None
    chart: Optional[dict] = None
    extra: Optional[dict] = None
    "Extra data that can be included. Not part of the standard types."

    is_main_result: Optional[bool] = None
    "Whether this data is the result of the execetution. Data can be produced by display calls of which can be multiple in a cell."
```

```python
self.text = data.pop("text/plain", None)
self.html = data.pop("text/html", None)
...
self.data  = data.pop("e2b/data", None)
self.chart = data.pop("e2b/chart", None)
self.extra = data          # whatever MIME types were left
```

Three design choices worth carrying:

- **Every representation is kept, none is chosen.** Unlike Open
  Interpreter's `elif` chain or jupyter-mcp's `output_mime()`, E2B does
  not pick — it hands the caller a typed record with a populated field
  per available MIME type, plus `formats()` to enumerate them. Selection
  is the *client's* decision, made with full information. That is the
  right split for a service: the sandbox does not know whether the model
  on the other end has vision.
- **`extra` catches unknown MIME types instead of dropping them.** A
  plotly bundle, a Vega-Lite spec, an ipywidget — all survive.
- **`is_main_result` distinguishes the cell's value from its
  `display()` calls.** A cell can emit many outputs; exactly one is the
  expression value. Without this flag a consumer has to guess by
  position.

## `e2b/data` and `e2b/chart`: extending the MIME bundle

`template/startup_scripts/0002_data.py` registers two IPython formatters:

```python
class E2BDataFormatter(BaseFormatter):
    format_type = Unicode("e2b/data")
    print_method = ObjectName("_repr_e2b_data_")
    _return_type = (dict, str)

    def __call__(self, obj):
        # IPython invokes every registered formatter for every displayed
        # object. Gate on sys.modules so a non-DataFrame output (e.g. an
        # int from `1 + 1`) doesn't pay the pandas import cost — a
        # pandas.DataFrame can only exist if the user already imported
        # pandas.
        pandas = sys.modules.get("pandas")
        if pandas is None or not isinstance(obj, pandas.DataFrame):
            return super().__call__(obj)

        result = obj.to_dict(orient="list")
        for key, value in result.items():
            result[key] = [
                v.isoformat() if isinstance(v, pandas.Timestamp) else v for v in value
            ]
        return result


class E2BChartFormatter(BaseFormatter):
    format_type = Unicode("e2b/chart")
    print_method = ObjectName("_repr_e2b_chart_")
    _return_type = (dict, str)

    def __call__(self, obj):
        if sys.modules.get("matplotlib") is None:
            return super().__call__(obj)
        from matplotlib.pyplot import Figure
        if not isinstance(obj, Figure):
            return super().__call__(obj)
        from e2b_charts import chart_figure_to_dict
        try:
            return chart_figure_to_dict(obj)
        except:
            return {}
```

**This is the idea the rest of this collection has been circling.** The
Jupyter display protocol already has an extension point — a MIME bundle
whose keys are open — and E2B uses it to add two types that are neither
text nor pixels:

- `e2b/data` — a DataFrame as `{column: [values]}`, columnar, with
  `Timestamp` normalised to ISO strings. Not a repr, not an HTML table:
  **the values**.
- `e2b/chart` — a matplotlib `Figure` *deconstructed back into data*.

The `sys.modules.get(...)` gate is a small but real engineering detail:
IPython runs every registered formatter against every displayed object,
so a naive `import pandas` inside the formatter would make `1 + 1` pay
the pandas import. Checking `sys.modules` is sound because the object
*cannot* be a DataFrame unless pandas is already imported.

## Reversing a plot into a chart object

`chart_data_extractor/e2b_charts/` walks the matplotlib `Axes` and
reconstructs a typed description:

```python
class ChartType(str, enum.Enum):
    LINE = "line"
    SCATTER = "scatter"
    BAR = "bar"
    PIE = "pie"
    BOX_AND_WHISKER = "box_and_whisker"
    SUPERCHART = "superchart"
    UNKNOWN = "unknown"


class Chart(BaseModel):
    type: ChartType
    title: Optional[str] = None
    elements: List[Any] = Field(default_factory=list)


class Chart2D(Chart):
    x_label: Optional[str] = None
    y_label: Optional[str] = None
    x_unit: Optional[str] = None
    y_unit: Optional[str] = None
```

Units are **parsed out of the axis label with a regex** — the convention
`"Speed (m/s)"` or `"Speed [m/s]"`:

```python
regex = r"\s\((.*?)\)|\[(.*?)\]"
if self.x_label:
    match = re.search(regex, self.x_label)
    if match:
        self.x_unit = match.group(1) or match.group(2)
```

And the elements carry the actual values:

```python
class PointData(BaseModel):
    label: str
    points: List[Tuple[Union[str, float], Union[str, float]]]

class BarData(BaseModel):
    label: str
    group: str
    value: float
```

`PointChart` additionally captures `x_ticks`, `x_tick_labels`, `x_scale`
(`linear`/`log`), and the same for y — so a log axis is legible as such
rather than as surprisingly-compressed numbers. Dates are normalised
(`date` → `isoformat()`, `numpy.datetime64` → seconds resolution). The
bar extractor even infers orientation from the containers and flips the
axis labels to match.

**Why this matters.** Sending a chart to a model has two bad options: a
PNG (a vision model can read it approximately, a text model not at all,
and either way "what was the value in March?" is a guess) or the source
code (which says what was requested, not what was rendered — a filter
that silently dropped rows is invisible). `e2b/chart` is a third:
**the chart as a queryable object** — title, axis labels, units, tick
positions, scale type, and every plotted point with its series label.
A model can answer "which series peaks first" exactly, cheaply, and
without vision.

Set against the rest of this folder, it completes the spectrum of what a
chart *is* on the wire:

| Representation | Example | Model can read values? | Renders? |
|---|---|---|---|
| PNG / base64 | Open Interpreter, jupyter-mcp | approximately, with vision | yes |
| Source code | LIDA's evaluator | no — only the intent | no |
| Declarative spec + data | Data Formulator `visualize` | yes | yes, by the harness |
| **Reversed figure** | **`e2b/chart`** | **yes, exactly** | **no — it is a description of one already drawn** |
| Screenshot of the rendered page | marimo `ctx.screenshot()` | approximately, with vision | it *is* the render |

The last two are complements, not competitors: `e2b/chart` tells you what
the numbers were, the screenshot tells you whether the legend collided.

A third startup script (`0003_images.py`) exists alongside these, and the
same extension mechanism is what a harness would use to add, say,
`app/vnd.parquet-ref` — a MIME type whose payload is a handle rather than
a value. Nothing in the protocol prevents it; E2B simply hasn't needed
it.
