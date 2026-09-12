# Jupyter MCP Server (Datalayer)

- **Type**: MCP server over a live Jupyter server · **Vendor**: Datalayer,
  Inc. · **Licence**: BSD-3-Clause
- **Source**: https://github.com/datalayer/jupyter-mcp-server — `main` @
  `a259155`, tag `v2.1.15` (2026-09-12)
- **Retrieved**: 2026-09-12

The most carefully-built **result and resource layer** in this
collection, and the source that most directly answers the question
"could an MCP tool write the artifact and return a ref?" — because it
already does.

18 tools, three resource templates, a capabilities resource, and a module
(`results.py`) whose docstring explains *why* the wire shape is built in
exactly one place. Ten pluggable execution backends are documented
(Jupyter server, JupyterHub, Colab, Kaggle, E2B, Modal, Daytona,
Cloudflare, CoreWeave, Datalayer) behind the same tool surface.

## Files

| File | Upstream path | What it is |
|---|---|---|
| [`tool-descriptions.md`](./tool-descriptions.md) | `jupyter_mcp_server/server.py` | All 18 tool names, their MCP annotations, and the model-facing description text for the ones that carry policy |
| [`resources-and-results.md`](./resources-and-results.md) | `jupyter_mcp_server/{resources,results}.py`, `utils.py` | The three resource templates, the output projection, the cache/audience metadata, and the reasoning behind each — quoted, because the comments are the documentation |

## Why it matters here

**Outputs are resources, addressed individually.** The three templates:

```
notebook://{name}
notebook://{name}/cells/{cell_id}
notebook://{name}/cells/{cell_id}/outputs/{index}
```

Reading a cell returns its outputs **listed, not inlined** — each with its
own `mimeType` and `uri`. The source says exactly why:

> A tool result says an output exists, how big it is and what type it is.
> An agent that needs the bytes asks for them here; an agent that only
> needed to know the cell succeeded does not pay for them. A cell that
> printed a megabyte otherwise spends a megabyte of context every time
> anybody reads it.

That is the artifact pattern from
[`../../agent-tool-result-transport.md`](../../agent-tool-result-transport.md)
§7, implemented inside MCP with no extensions, no vendor `_meta`, and no
out-of-band store — just `resources/read`. It is the concrete precedent
for the design question in
[`../../agent-design/artifacts.md`](../../agent-design/artifacts.md).

**Cell ids, not indices.** Every cell tool accepts `cell_id`, and the
error text teaches the distinction:

> No cell with id `{cell_id}` in this notebook. Cell ids are on every
> cell result; an index is not an id.

The reason is concurrency, stated plainly: *"An index is a position in a
document somebody else is editing: between reading the notebook and
reading 'cell 4', cell 4 may be a different cell. The nbformat 4.5 id is
not."* Same class of problem as a stale line number in a code edit, and
the same answer — address by identity, not position. Several tools also
take an explicit `notebook_name` to avoid racing a shared
"current notebook" pointer.

**Two execution surfaces with a prompt-level rule between them.** This is
the finding the rest of the folder corroborates. `execute_code` runs in
the kernel and is *not saved to the notebook*; `insert_execute_code_cell`
appends a durable cell. The description of the ephemeral one carries a
prohibition:

> Under no circumstances should you use this tool to:
> 1. Import new modules or perform variable assignments that affect
>    subsequent Notebook execution

That is a **transaction boundary written as a prompt rule**: probe with
the ephemeral tool, commit with the durable one, never let a probe change
state the notebook depends on. [`../data-formulator/`](../data-formulator)
draws the same line between "inspection tools" and "actions";
[`../marimo/`](../marimo) draws it between the scratchpad and
`marimo._code_mode`. Three independent implementations, one rule.

**Annotations are used properly.** Every tool declares
`readOnlyHint` / `destructiveHint` / `idempotentHint` / `openWorldHint`,
and the values are *thought about*: `execute_cell` is
`destructiveHint=True, idempotentHint=False, openWorldHint=True` (it runs
arbitrary code that may touch the network); `move_cell` is destructive but
closed-world; `clear_cell_output` is destructive but idempotent. Compare
[`../matlab-mcp/`](../matlab-mcp), which factors the same four flags into
four named constructors.

**Protocol-standard cache hints.** Resources carry
`_meta["io.modelcontextprotocol/cache"]` with a TTL and a scope
(`private` for the notebook — "a proxy that shared this answer would hand
somebody else's work to whoever asked next"; outputs held longer than the
notebook because *a re-run replaces a cell's outputs rather than editing
one*). The server's own keys live under `io.jupyter-mcp/`, namespaced
deliberately: *"a bare `cell_id` would be a collision waiting to
happen."*

**And it says out loud that the contract is unstable.** `results.py`
opens by noting that a server cannot know whether a client shows the
model `content` or `structuredContent`, that the Core Primitives Working
Group is redesigning that, and that annotations *"may be deprecated
outright if nobody adopts them"* — so the shape is built in one file and
the eighteen tools never touch it. That is the correct engineering
response to §3f of the transport doc ("the server cannot predict the
projection"): **do not spread an unstable contract across your tools.**
