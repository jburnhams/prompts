# Positron — the Data Explorer protocol

- **Type**: data-science IDE (VS Code fork) · **Vendor**: Posit PBC ·
  **Licence**: Elastic-2.0
- **Source**: https://github.com/posit-dev/positron — `main` @ `340c418`
  (2026-09-12). Files under `positron/comms/`
- **Retrieved**: 2026-09-12

Not an agent. Included for one thing: **the machine-readable contract a
data viewer exposes**, which is what "chat with a file browser / data
grid / viewer" would actually have to be built on.

Positron's IDE panes talk to language kernels (Python *and* R) over
OpenRPC "comms". Six are published as JSON-RPC schemas in
`positron/comms/`: `data_explorer`, `variables`, `plot`, `connections`,
`help`, `ui`. They are generated into TypeScript, Python and Rust, so the
same contract holds across every backend.

## The Positron Assistant is no longer open

`extensions/copilot/src/extension/prompts/node/base/positronAssistant.tsx`
is now only a call site:

```tsx
try {
    const positron = require('positron') as typeof import('positron');
    return await positron.ai.generateAssistantPrompt(request);
} catch {
    return undefined;
}
```

with the comment:

> Positron supplies the Positron-specific context for this prompt via the
> `positron` API, provided by the Positron extension host at runtime. It
> is absent when Copilot Chat runs outside Positron (or in simulation
> tests), so guard the lookup and skip this element rather than failing
> the whole chat request.

`extensions/positron-assistant` is not in the OSS tree at this commit, so
the prompt text itself is unavailable. Set that alongside
[`../open-interpreter/`](../open-interpreter)'s pivot to a coding agent:
**both of the category's most visible open-source efforts have moved
their data-analysis agent logic out of public source since 2024.** That
is worth knowing when weighing how much of this folder is "the field" and
how much is "what remains readable".

What is still open — and is arguably the more reusable half — is the
protocol below.

## `data_explorer`: fifteen methods

| Method | Summary (verbatim) |
|---|---|
| `open_dataset` | "Request to open a dataset given a URI" |
| `get_schema` | "Request subset of column schemas for a table-like object" |
| `search_schema` | "Search table schema with column filters, optionally sort results" |
| `get_data_values` | "Request data from table columns with values formatted as strings" |
| `get_row_labels` | "Request formatted row labels from table" |
| `get_column_profiles` | "Async request for a statistical summary or data profile for batch of columns" |
| `set_row_filters` | "Row filters to apply (or pass empty array to clear row filters)" |
| `set_column_filters` | "Set or clear column filters on table, replacing any previous filters" |
| `set_sort_columns` | "Set or clear the columns(s) to sort by, replacing any previous sort columns" |
| `export_data_selection` | "Export data selection as a string in different formats like CSV, TSV, HTML" |
| **`convert_to_code`** | **"Converts filters and sort keys as code in different syntaxes like pandas, polars, data.table, dplyr"** |
| **`suggest_code_syntax`** | **"Suggest code syntax for code conversion based on the current backend state"** |
| `set_dataset_import_options` | re-import a file-based source with different options |
| `open_data_explorer` | "Creates a new, independent data explorer comm for the same underlying data. The new comm has its own state (filters, sort…)" |
| `get_state` | "Request the current backend state (table metadata, explorer state, and features)" |

Read as a tool surface, this is **a viewer that an agent could drive
directly**, and it is more considered than any dataframe tool in this
folder. Five things stand out.

### 1. `convert_to_code` — the UI-to-reproducibility bridge

The user (or an agent) filters and sorts by manipulating a grid;
`convert_to_code` turns that interaction state into a **pandas / polars /
data.table / dplyr expression**, and `suggest_code_syntax` picks the
idiom that fits the session's backend.

This is the missing piece in every "chat with a dashboard" design. Direct
manipulation is a fast, low-error way to specify a subset — much better
than a model guessing a predicate — but it produces no artifact. Converting
it to code makes the manipulation **reviewable, re-runnable, and
pasteable into a notebook cell**, and it gives an agent a way to *read*
what the user did rather than being told about it.

It also happens to be the general answer to the R/Python question:
**one protocol, one interaction model, an idiom chosen per session.**
Nothing above the comm layer knows or cares which language is running.

### 2. Filters are a closed vocabulary, not predicates

```json
"row_filter_type": {
  "enum": ["between", "compare", "is_empty", "is_false", "is_null",
           "is_true", "not_between", "not_empty", "not_null",
           "search", "set_membership"]
},
"column_filter_type": { "enum": ["text_search", "match_data_types"] }
```

Eleven row filters and two column filters, enumerated. An agent
manipulating the view cannot inject SQL or R because there is no
expression to inject into — it selects a filter type and supplies typed
operands. That is a much stronger safety property than sanitising a
string, and it comes free with the schema. The cost is expressiveness: a
filter this vocabulary cannot express has to become code.

### 3. Profiles are a batched, async, named menu

```json
"column_profile_type": {
  "enum": ["null_count", "summary_stats",
           "small_frequency_table", "large_frequency_table",
           "small_histogram", "large_histogram"]
}
```

`get_column_profiles` takes an array of `{column_index, profiles[]}` and
a `callback_id` — **one request covering many columns and many profile
kinds, answered asynchronously.** The `small_`/`large_` pairs are a
cost/detail dial exposed as distinct types rather than as a numeric
parameter, which makes the cheap default obvious.

Compare [`../btw/`](../btw)'s `skim` (everything, always) and
[`../data-formulator/`](../data-formulator)'s `inspect_source_data`
(schema + stats + samples, always). Positron is the only one that lets
the caller ask for *exactly* `null_count` on forty columns and nothing
else — which is the actual shape of most profiling questions.

### 4. Special values get integer codes

From `data_explorer.md`:

> ### get_data_values
>
> Non-special values are returned formatted as strings.
>
> Special values such as `NULL`, `NA`, etc. are encoded with integer codes.
> The currently supported special value codes are:
>
> * NULL: 0
> * NA: 1
> * NaN (Not a number): 2
> * NaT (Not a time): 3
> * None (such as Python None): 4
> * +INF: 10
> * -INF: 11

A small, sharp piece of transport design. Once every value is a formatted
string, `"NA"` is ambiguous — it could be a two-letter country code, a
missing value, or a string that happens to read "NA". Out-of-band integer
codes remove the ambiguity without a second parallel array of null flags,
and the gap between 4 and 10 leaves room for more null-ish kinds without
disturbing the numeric ones.

Every harness in this folder that serialises a dataframe to CSV or JSON
for the model has this problem and none of them address it. A model
reading `revenue,NA` cannot distinguish missing from the string, and
`NaN` versus `None` versus `NaT` carries real diagnostic information
about *how* the data is broken.

### 5. Capabilities are negotiated, per feature, per backend

`get_state` returns "table metadata, explorer state, **and features**",
where each RPC's features list carries a `support_status` per supported
type (e.g. `get_column_profiles_features.supported_types` is an array of
`{profile_type, support_status}`). A DuckDB backend, a pandas backend and
an R `data.frame` backend genuinely differ in what they can compute, and
the front end asks rather than assuming.

That is the pattern MCP's `capabilities` reaches for and mostly leaves at
the whole-server level: here it is **per method and per enum member**.
[`../jupyter-mcp/`](../jupyter-mcp)'s `capabilities` resource is the
closest analogue in this folder — *"what this server can do, and where
each answer came from"* — and it exists for the same reason: a client
needs to know what it is talking to before it builds a request.

## `variables`: the kernel namespace as a protocol

| Method | Summary |
|---|---|
| `list` | List all variables |
| `inspect` | Inspect a variable |
| `view` | **Request a viewer for a variable** |
| `query_table_summary` | Query table summary |
| `clipboard_format` | Format for clipboard |
| `clear` / `delete` | Clear all / delete named variables |

`view` is the interesting one: it **promotes a variable into a Data
Explorer comm**. So "show me `df`" is a protocol operation, not a
convention — and an agent could issue it, putting a grid in front of the
user without generating any code at all.

Read together, `variables.list` + `data_explorer.get_column_profiles` +
`convert_to_code` is a complete, language-neutral tool surface for a data
agent: *what exists, what is in it, and what code reproduces the view I
just built.* No harness in this folder uses it that way. It is the
clearest available sketch of what a viewer-native data agent would be
built on, and it already ships for two languages.
