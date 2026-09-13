# Jupyter MCP Server — resources, results, and the output projection

Everything below is from `jupyter_mcp_server/resources.py`,
`results.py` and `utils.py` at `v2.1.15`. The comments are quoted at
length because they are the best-argued prose in this collection about
*why* a tool result should be a handle.

## 1. The three resource templates

```python
NOTEBOOK_RESOURCE = "notebook://{name}"
CELL_RESOURCE     = "notebook://{name}/cells/{cell_id}"
OUTPUT_RESOURCE   = "notebook://{name}/cells/{cell_id}/outputs/{index}"

NOTEBOOK_TTL_MS = 5_000
OUTPUT_TTL_MS   = 60_000
NOTEBOOK_MIME   = "application/x-ipynb+json"
```

Registered with descriptions aimed at the model:

| Resource | Description |
|---|---|
| `notebook` | "A notebook in use, as nbformat JSON. Cells and outputs are resources of their own." |
| `notebook-cell` | "One cell by its nbformat id, with its outputs listed rather than inlined." |
| `notebook-cell-output` | "One output of one cell, with its own MIME type. **Read it only if you need the bytes.**" |

Each declares an audience and a cache hint:

```python
@mcp.resource(
    resources.OUTPUT_RESOURCE,
    name="notebook-cell-output",
    description="One output of one cell, with its own MIME type. Read it only if you need the bytes.",
    annotations=audience_annotations(AUDIENCE_ASSISTANT),
    meta={CACHE_META_KEY: {"ttlMs": resources.OUTPUT_TTL_MS, "cacheScope": SCOPE_PRIVATE}},
)
```

The notebook and cell resources are for `["assistant", "user"]`; an
output is for the **assistant alone**, and the docstring says why:

> The audience is the assistant alone: a person reads outputs in their
> notebook, where they are rendered, not through a URI.

The differing TTLs are reasoned, not guessed:

> Held longer than the notebook because an output does not change — a
> re-run *replaces* a cell's outputs rather than editing one, and the new
> ones are at new positions.

## 2. The cell document: outputs listed, not inlined

`cell_document()` is the load-bearing function. Verbatim:

```python
def cell_document(name: str, index: int, cell: Any) -> str:
    """One cell, as JSON rather than as the tools' readable text.

    A resource is read by a program. The tools' `=====Cell 3 | type: code=====`
    banner is for a person reading a transcript, and an agent parsing it back
    into fields is an agent that will get it wrong on the first cell whose
    source contains the word "Cell".
    """
    return json.dumps(
        {
            "id": str(getattr(cell, "id", "")),
            "index": index,
            "cell_type": cell.cell_type,
            "source": cell.get_source("raw"),
            "execution_count": getattr(cell, "execution_count", None),
            # The outputs are *listed*, not inlined: their URIs and their
            # types, so an agent can decide which to read. Inlining them here
            # would make reading a cell cost whatever the cell printed, which
            # is the thing these resources exist to avoid.
            "outputs": [
                {
                    "index": position,
                    "mimeType": output_mime(output),
                    "uri": (
                        f"notebook://{name}/cells/"
                        f"{getattr(cell, 'id', '')}/outputs/{position}"
                    ),
                }
                for position, output in enumerate(getattr(cell, "outputs", []) or [])
            ],
        },
        indent=2,
    )
```

**This is the answer to "can an MCP tool hand back a ref instead of a
payload".** Reading a cell costs the source plus one line per output. The
model sees that output 0 is `image/png` and output 1 is `text/plain`, and
fetches neither, one, or both. Nothing about it is an extension: it is
`resources/read` and `resource_link`, used as specified.

Two secondary points the docstring makes and most implementations miss:

- **A resource is read by a program; a tool result is read by a model.**
  They should not be the same string. The banner format is for the
  transcript; the JSON is for the fetch.
- **Round-tripping your own human-readable format is a bug waiting for
  the right input.** The named failure — a cell whose source contains the
  word "Cell" — is exactly the class of bug
  [`../../agent-tool-call-dialects.md`](../../agent-tool-call-dialects.md)
  catalogues for delimiter-based formats.

## 3. Choosing the MIME type

```python
def output_mime(output: Any) -> str:
    """The output's own MIME type, not `text/plain` for everything.

    An image read as text is a screenful of base64 in the agent's context,
    and the agent cannot tell that is what happened. The type is what lets a
    client decide whether to render it, save it or leave it alone.
    """
    ...
    data = output.get("data")
    if isinstance(data, dict) and data:
        # The richest representation the cell produced. `text/plain` is the
        # fallback every kernel attaches, so preferring it would throw away
        # the image in every image output.
        for candidate in data:
            if candidate != "text/plain":
                return str(candidate)
        return "text/plain"
    return "text/plain"
```

*"An image read as text is a screenful of base64 in the agent's context,
and the agent cannot tell that is what happened"* is the same failure
[`../../agent-vision-multimodal.md`](../../agent-vision-multimodal.md)
names the image-in-a-tool-result bug — reached from the server side
rather than the client side, and prevented by the same move: keep the
type, and let it decide the routing.

## 4. The tool-side projection, which is deliberately lossier

`utils.extract_output()` builds what goes into a *tool result* (as
opposed to a resource read), and it degrades on purpose:

```python
if "image/png" in data:
    if ALLOW_IMG_OUTPUT:
        return ImageContent(type="image", data=data["image/png"], mime_type="image/png")
    else:
        return "[Image Output (PNG) - Image display disabled]"
...
if "text/html" in data:
    return "[HTML Output]"
else:
    return f"[{output_type} Data: keys={list(data.keys())}]"
```

Three grades of degradation, all **stated in-band**: a real image block
when images are on, a labelled placeholder when they are off, and — for
HTML and anything unrecognised — a placeholder that names the MIME keys
that were available. The last is the good one: `[display_data Data:
keys=['application/vnd.plotly.v1+json', 'text/html', 'text/plain']]`
tells a model both that something exists and what it is, and the URI to
fetch it is one resource read away.

Between those, a preference for the *richest readable text*:

```python
# For IPython.display.* objects the kernel emits a bundle whose text/plain
# is only the bare object repr (e.g. "<IPython.core.display.Markdown object>")
# while the real content lives in a richer key; get_mimebundle_text prefers
# text/markdown, text/latex, application/json (pretty-printed) over an
# object-repr text/plain, and falls back to text/plain otherwise.
```

`<IPython.core.display.Markdown object>` is the single most common piece
of useless text a notebook agent sees, and this is the fix.

## 5. The `_meta` discipline

```python
#: Where a result's cache hints live (SEP-2549). The protocol's namespace,
#: not this server's: a client caches on the standard key or not at all.
CACHE_META_KEY = "io.modelcontextprotocol/cache"

#: `session` is the same answer for everyone talking to this server;
#: `private` is one caller's and must never be shared by a proxy.
SCOPE_SESSION = "session"
SCOPE_PRIVATE = "private"

#: The namespace this server's own `_meta` keys live under. Namespaced because
#: `_meta` is shared with the protocol and with every other extension: a bare
#: `cell_id` would be a collision waiting to happen.
META_NAMESPACE = "io.jupyter-mcp"
```

Two rules, both right: **use the protocol's namespace for protocol
concerns**, and **namespace your own**. `../../agent-tool-result-transport.md`
§6 records `_meta["anthropic/maxResultSizeChars"]` as the only per-tool
cap negotiation found in any client; this is the same mechanism used for
caching, and — unlike that one — on a standard key rather than a vendor's.

## 6. Why it is all in one file

`results.py` opens with the reasoning, which is the most transferable
thing here:

> A `tools/call` may answer with `content` — text and images, for a person
> and for the model to read — and with `structuredContent`, the same answer as
> data. **A server cannot know which of the two a client puts in front of the
> model**, and the Core Primitives Working Group is redesigning that contract for
> exactly that reason. Content annotations (`audience`, `priority`) are in
> the same discussion, and may be deprecated outright if nobody adopts them.
>
> So the shape is built here and nowhere else. When the redesign lands, or
> annotations go, this file changes and the eighteen tools do not.

That is the operational consequence of the finding in
[`../../agent-tool-result-transport.md`](../../agent-tool-result-transport.md)
§3f — five clients, five different projections, none of them negotiable —
and the correct response to it: **treat the wire shape as a single
replaceable adapter, not as something your tools know about.**

The server also implements `resources/subscribe` and
`resources/unsubscribe`, which matters for the live case: a notebook a
human is editing while an agent watches it.
