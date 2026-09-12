# Vanna 2.0

- **Type**: text-to-SQL, rebuilt as an agent framework · **Vendor**:
  Vanna.AI · **Licence**: MIT
- **Source**: https://github.com/vanna-ai/vanna — `main` @ `365d061`,
  tag `v2.0.2` (2026-02-02)
- **Retrieved**: 2026-09-12

Vanna 1.x was a RAG-over-SQL library: embed schema and example queries,
retrieve, generate SQL, run it. 2.0 is a different program — a tool-using
agent framework with a **dual-channel result type**, a component system
for rendering, and capabilities injected by the host.

It earns its place here for one function. `RunSqlTool.execute` is the
clearest worked example anywhere in this collection of the pattern the
artifacts design is reaching for: **run the query, write the result to a
file, hand the model a truncated preview plus the filename, hand the UI a
typed component, and put the shape in metadata.**

## Files

| File | Upstream path | What it is |
|---|---|---|
| [`run-sql-tool.md`](./run-sql-tool.md) | `src/vanna/tools/run_sql.py`, `src/vanna/core/tool/models.py` | The tool, its result type, and the three channels it writes to |

## `ToolResult`: the model and the user get different things

```python
class ToolResult(BaseModel):
    """Result from tool execution.

    Changes:
    - `result_for_llm`: string that will be sent back to the LLM.
    - `ui_component`: optional UI payload for rendering in clients.
    """

    success: bool = Field(description="Whether execution succeeded")
    result_for_llm: str = Field(description="String content to send back to the LLM")
    ui_component: Optional["UiComponent"] = Field(default=None, description="Optional UI component for rendering")
    error: Optional[str] = Field(default=None, description="Error message if failed")
    metadata: Dict[str, Any] = Field(default_factory=dict)
```

And the UI payload is itself two-tiered:

```python
class UiComponent(BaseModel):
    """Base class for UI components streamed to client.

    This wraps both rich and simple component representations,
    allowing tools to return structured UI updates.
    """
    rich_component: Any = Field(..., description="Rich component for advanced rendering")
    simple_component: Optional[Any] = Field(None, description="Simple component for basic rendering")
```

So every tool call produces up to **four** distinct projections:

| Channel | Consumer | Example for a `SELECT` |
|---|---|---|
| `result_for_llm` | the model | 1,000 chars of CSV + the filename + the next step |
| `ui_component.rich_component` | a capable client | `DataFrameComponent` — sortable, filterable, paginated, exportable |
| `ui_component.simple_component` | a degraded client (SMS, plain text) | `SimpleTextComponent` with the same text the model got |
| `metadata` | the harness/audit log | `row_count`, `columns`, `query_type`, `output_file` |

This is the explicit version of the thing
[`../../agent-tool-result-transport.md`](../../agent-tool-result-transport.md)
§3f says MCP servers *cannot* do: decide what the model sees separately
from what the user sees. Vanna can, because it owns both ends. An MCP
server cannot, which is exactly why jupyter-mcp's `results.py` exists and
why its comments are so careful about `audience`.

The **rich/simple pair** is the useful refinement over a single UI
payload: it is graceful degradation declared at the point of production
rather than negotiated at the point of rendering. The same discipline
`../../agent-generative-output.md` reduces to *emit the most structured
representation the destination can hold, and where it can't, degrade one
step and say so* — here, both steps are emitted at once and the client
picks.

A `ToolSchema` also carries `access_groups`, so tool visibility is a
function of who is asking — permissioning at the level of the surface
rather than the call.

## Also present: an `ArtifactComponent`

```python
class ArtifactComponent(RichComponent):
    """Component for displaying interactive artifacts that can be rendered externally."""

    type: ComponentType = ComponentType.ARTIFACT
    artifact_id: str = Field(default_factory=lambda: f"artifact_{uuid.uuid4().hex[:8]}")
    content: str  # HTML/SVG/JS content
    artifact_type: str  # "html", "svg", "visualization", "interactive", "d3", "threejs"
    title: Optional[str] = None
    description: Optional[str] = None
    editable: bool = True
    fullscreen_capable: bool = True
    external_renderable: bool = True
```

A second open-source artifact channel to set alongside
[`../../librechat/`](../../librechat): here delivered as a **typed tool
result** rather than an in-band fenced directive. The three boolean
capability flags (`editable`, `fullscreen_capable`,
`external_renderable`) are the part worth noting — the producer declares
what the consumer may do with it, which is the same job the `audience`
annotation does in MCP and the same job `display: render | attach` does
in this session's own file-sending tool.
