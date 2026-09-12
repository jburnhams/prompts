# Jupyter MCP Server — tools

All 18, from `jupyter_mcp_server/server.py` at `v2.1.15`. Annotation
values are as declared. Description text is the tool's docstring, which
FastMCP surfaces to the model.

## The surface

| Tool | `readOnly` | `destructive` | `idempotent` | `openWorld` |
|---|---|---|---|---|
| `list_files` | ✓ | | ✓ | |
| `list_kernels` | ✓ | | ✓ | |
| `list_notebooks` | ✓ | | ✓ | |
| `read_notebook` | ✓ | | ✓ | |
| `read_cell` | ✓ | | ✓ | |
| `connect_to_jupyter` | | ✓ | ✓ | ✓ |
| `use_notebook` | | ✓ | ✓ | |
| `unuse_notebook` | | ✓ | ✓ | |
| `restart_notebook` | | ✓ | | |
| `insert_cell` | | ✓ | | |
| `overwrite_cell_source` | | ✓ | ✓ | |
| `edit_cell_source` | | ✓ | | |
| `delete_cell` | | ✓ | | |
| `move_cell` | | ✓ | | |
| `clear_cell_output` | | ✓ | ✓ | |
| `execute_cell` | | ✓ | | ✓ |
| `insert_execute_code_cell` | | ✓ | | ✓ |
| `execute_code` | | ✓ | | ✓ |

Five read-only tools, thirteen that change something. Note that the two
tools which merely *rearrange* the document (`move_cell`, `delete_cell`)
are closed-world, while the three that *run* anything are open-world —
the flag is tracking "can this reach the network", which is what it is
for.

## The descriptions that carry policy

### `execute_code` — the ephemeral surface

> Execute code directly in a kernel (not saved to notebook).
>
> If `use_sandbox` selected an active sandbox, this tool executes on that
> sandbox instead of a Jupyter kernel. This allows agents to switch between
> kernel-backed and sandbox-backed execution using the same execute_code API.
>
> Targets the current activated notebook's kernel by default. Pass kernel_id
> to execute in a specific kernel directly — including raw kernels with no
> notebook attached.
>
> Recommended to use in following cases:
> 1. Execute Jupyter magic commands(e.g., `%timeit`, `%pip install xxx`)
> 2. Performance profiling and debugging.
> 3. View intermediate variable values(e.g., `print(xxx)`, `df.head()`)
> 4. Temporary calculations and quick tests(e.g., `np.mean(df['xxx'])`)
> 5. Execute Shell commands in Jupyter server(e.g., `!git xxx`)
>
> Under no circumstances should you use this tool to:
> 1. Import new modules or perform variable assignments that affect subsequent Notebook execution
> 2. Execute dangerous code that may harm the Jupyter server or the user's data without permission

The five-and-two structure is worth copying wholesale. The positives are
all *probes* — measure, inspect, peek, install, shell out. The first
prohibition is not about safety at all: it is about **keeping the
notebook a reproducible artifact**. If the model imports pandas via
`execute_code`, every subsequent cell works in this session and none of
them work when a human re-runs the notebook from the top. The notebook
would be a lie.

The second prohibition ("dangerous code… without permission") is the
weaker half — an instruction where the tool annotations and the host's
approval flow are the mechanism.

Also note the backend transparency: the same tool name runs against a
Jupyter kernel or an E2B/Modal/Daytona sandbox. The model is told this,
which is right — it changes what `!git` will find — but the *choice* is
the operator's, not the model's.

### `insert_execute_code_cell` — the durable surface

> Insert a cell at specified index from the currently activated notebook
> and then execute it with timeout and return it's outputs. It is a
> shortcut tool for insert_cell and execute_cell tools, recommended to
> use if you want to insert a cell and execute it at the same time

A composite of two tools it does not replace. Worth noting against the
granularity rule in
[`../../agent-design/tools.md`](../../agent-design/tools.md): this split
is justified by **round-trips**, not by any harness answer — insert and
execute have the same permission class, same destructiveness, same result
shape. It is a latency optimisation, and the description says so
honestly rather than pretending to be a distinct capability.

### `read_notebook` — two projections, and when to use each

> Read a notebook and return index, source content, type, execution count
> of each cell.
>
> Using brief format to get a quick overview of the notebook structure
> and it's useful for locating specific cells for operations like delete
> or insert.
> Using detailed format to get detailed information of the notebook and
> it's useful for debugging and analysis.
>
> It is recommended to use brief format with larger limit to get a
> overview of the notebook structure, then use detailed format with exact
> index and limit to get the detailed information of some specific cells.

`brief` renders each cell as its first line plus
`...(N lines hidden)` (`Cell.get_overview()`); `detailed` renders full
source. Both paginate (`start_index`, `limit`).

This is **the outline-then-zoom pattern applied to a document rather than
a codebase**, with the recommended strategy stated in the description
rather than left for the model to discover: wide-and-shallow first,
narrow-and-deep second. The same shape as a good `Read` with offset/limit,
and the same reason.

### `use_notebook` — explicit session state

> Use a notebook and activate it for following cell operations.
> All cell operations will be performed on the currently activated notebook.
> Activate new notebook will deactivate the previously activated notebook.
> Reactivate previously activated notebook using same notebook_name and notebook_path.

A **modal tool surface**: most of the other seventeen operate on
"whatever is active", so this one call re-points them all. Cheap in
tokens (no `notebook` argument on every call) and a classic source of
mistakes when two clients share a server — which is exactly why the
mutating tools *also* accept an explicit `notebook_name`:

> Target this specific connected notebook instead of the currently
> activated one. Use when multiple clients share this server, to avoid
> racing the shared 'current notebook' pointer. Omit to use the currently
> activated notebook.

Modal by default, addressable when it matters. That is the right
resolution of the ergonomics/safety trade, and it is stated in the
description so the model knows when to reach for the explicit form.

### `list_files`

> List all files and directories recursively in the Jupyter server's file
> system. Used to explore the file system structure of the Jupyter server
> or to find specific files or directories.

Parameters: `path`, `max_depth` (`ge=0, le=3`), `start_index`, `limit`,
`pattern` (glob). The **hard depth ceiling of 3** is the notable part —
not a default the model can raise, a schema bound. A recursive listing
of a data-science working directory is the classic context bomb
(`.ipynb_checkpoints`, `node_modules`, a `data/` tree with 40,000
partition files), and the schema simply forbids asking for it.
