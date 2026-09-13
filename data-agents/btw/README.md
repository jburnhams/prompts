# btw (Posit)

- **Type**: R-side toolkit for connecting an R session to an LLM ·
  **Vendor**: Posit PBC · **Licence**: MIT
- **Source**: https://github.com/posit-dev/btw — `main` @ `473d1d8`,
  version `1.5.0` (2026-09-09)
- **Retrieved**: 2026-09-12

The R ecosystem's answer, and it is a genuinely different one: **the
default surface is introspection, and code execution is off.**

> btw helps R users work with Large Language Models, whether you're
> pasting context into ChatGPT, chatting with an AI assistant in your IDE,
> or building LLM-powered applications.
>
> The challenge: LLMs need context about your R environment to be helpful
> — your data structures, the packages you're using, relevant
> documentation.

Three delivery modes share one tool registry: copy context to the
clipboard for an external chat (`btw()`), run an assistant in the IDE
(`btw_app()`), or expose the tools over MCP (`R/mcp.R`).

## The tool registry

~26 tool families under `R/tool-*.R`, grouped by prefix:

| Group | Tools |
|---|---|
| `env` | describe environment, **describe data frame** |
| `docs` | package help, function help, vignettes, package NEWS |
| `files` | list, read, search, write, edit, patch, replace |
| `session` / `sessioninfo` | platform, attached/loaded/installed packages, is-package-installed |
| `pkg` | devtools (`load_all`, `test`, `check`, `document`), covr, package source |
| `ide` | read current editor |
| `git` / `github` | repository context |
| `cran` | search CRAN, package info |
| `web` | fetch |
| `agent` | subagent, custom agents |
| `skills` | skill loading |
| `run` | **run R code — disabled by default** |

The ratio is the point: **one execution tool against twenty-five
introspection tools.** Everything a Python-side harness would do by
writing `print(...)` into a kernel, btw does by calling a typed function
that returns a formatted string.

## Four projections of a data frame, with stated selection criteria

`btw_this.data.frame`'s `format` argument, from the roxygen docs:

> - `"skim"` is the most information-dense format for describing the data.
>   It uses and returns the same information as `skimr::skim()` but
>   formatting as a JSON object that describes the dataset.
> - To glimpse the data column-by-column, use `"glimpse"`. This is
>   particularly helpful for getting a sense of data frame column names,
>   types, and distributions, **when pairings of entries in individual rows
>   aren't particularly important**.
> - To just print out the data frame, use `print()`.
> - To get a json representation of the data, use `"json"`. This is
>   particularly helpful **when the pairings among entries in specific rows
>   are important to demonstrate**.

And the model-facing version, narrowed to two:

```r
format = ellmer::type_enum(
  paste(
    "The output format of the data frame: 'skim' or 'json'. 'skim' is the most information-dense and is the default.",
    "",
    "* skim: Returns a JSON object with information about every column in the table.",
    "* json: Returns the data frame as JSON",
    sep = "\n"
  ),
  values = c("skim", "json"),
  required = FALSE
),
max_rows = ellmer::type_integer(
  "The maximum number of rows to show in the data frame. Defaults to 5. Only applies when `format=\"json\"`."
, required = FALSE),
max_cols = ellmer::type_integer(
  "... Defaults to 100. Only applies when `format=\"json\"`."
, required = FALSE),
```

**This is the best statement in the collection of what "show me the data"
actually means.** The distinction it draws — *column summaries* versus
*rows* — is exactly the one that matters and is almost never surfaced:

- `skim` answers "what is in this table": per column, type, missingness,
  quantiles, a histogram sparkline, top categories. Information-dense,
  fixed size regardless of `nrow`, and the right default for almost every
  question.
- `json` answers "what does a record look like": a handful of whole rows,
  with the **co-occurrence between fields** intact. You need it when the
  question is about relationships within a row, and you need almost none
  of it.

Every other harness in this folder hard-codes one answer.
[`../data-formulator/`](../data-formulator)'s `inspect_source_data`
returns "schema, field-level statistics, and sample rows" — all three,
always. [`../marimo/`](../marimo) renders name/type/preview.
[`../lida/`](../lida) computes a summary and never shows a row. btw makes
it the model's choice and tells it how to choose. The
`max_rows`/`max_cols` defaults (5 and 100) cap the expensive branch, and
the description states that they apply only to it.

Note also the two-level documentation: the human-facing roxygen has four
formats with nuanced guidance; the model-facing enum has two, with the
default named. **The model is offered a smaller, sharper choice than the
user is** — good practice, and rarely done deliberately.

## Consent as a tool argument

`btw_tool_ide_read_current_editor`:

```r
#' @param consent Boolean indicating whether the user has consented to reading
#'   the current file. The tool definition includes language to induce LLMs to
#'   confirm with the user before calling the tool. Not all models will follow
#'   these instructions. Users can also include the string `@current_file` to
#'   induce the tool.
```

```r
if (!consent) {
  cli::cli_abort("Please ask the user for consent before reading from the editor.")
}
```

A `consent` boolean that the *model* sets, gating a tool that reads the
user's open editor — and the documentation admits the weakness in the
same breath: *"Not all models will follow these instructions."*

This is worth recording precisely because it is **the wrong place for
consent** and the authors know it. The model asserting that the user
consented is not evidence that they did; it is a self-signed
attestation. `../../agent-permissions-approval.md` and
[`../../openclaw/`](../../openclaw)'s consent-assertion problem cover the
general case. What btw has that most don't is the honest annotation and a
second, real path (`@current_file`, typed by the user), so the mechanism
degrades to a genuine signal when someone uses it.

## `run_r` is off by default, and the reasons are written down

```r
#' @section Security Considerations:
#' Executing arbitrary R code can pose significant security risks, especially
#' in shared or multi-user environments. Furthermore, neither \pkg{shinychat}
#' (as of v0.4.0) or nor \pkg{ellmer} (as of v0.4.0) provide a mechanism to
#' review and reject the code before execution. Even more, the code is executed
#' in the global environment and does not have any sandboxing or R code
#' limitations applied.
#'
#' It is your responsibility to ensure that you are taking appropriate measures
#' to reduce the risk of the LLM writing arbitrary code. ...
#' At this time, we do not recommend that you enable this tool in a publicly-
#' available environment without strong safeguards in place.
```

Enabled by an option (`btw.run_r.enabled`), an environment variable
(`BTW_RUN_R_ENABLED`), an explicit `btw_tools("run")`, or a `tools:` /
`options:` entry in a project's `btw.md` file — four paths, all opt-in,
one of them per-project.

Three facts stated that most harnesses leave implicit: **no approval
gate exists in the surrounding stack**, **the code runs in the global
environment**, and **there is no sandbox**. Compare
[`../data-formulator/`](../data-formulator)'s three-tier sandbox with a
file literally named `not_a_sandbox.py`. Both are being honest; btw is
being honest about having nothing, which is the harder disclosure.

"Runs in the global environment" is the specific danger and the exact
inverse of [`../marimo/`](../marimo)'s scratchpad: the agent's
exploratory code can silently rebind the user's variables. marimo
discards top-level bindings; btw does not.

The return type is worth noting on its own:

> This tool runs R code and returns results as a list of
> `ellmer::Content()` objects. It captures text output, **plots**,
> messages, warnings, and errors. Code execution stops on the first error,
> returning all results up to that point.

A typed multi-part return — text, images, conditions — rather than a
string, which is the same shape as [`../e2b/`](../e2b)'s `Result` and the
thing Open Interpreter's `SubprocessLanguage` R backend cannot do. When
the harness is written *in* the language, plots come back for free.

## `btw.md`: a project context file with a tool manifest

```md
---
tools:
  - run_r
---
```

or

```md
---
options:
  run_r:
    enabled: true
---
```

A repo-resident file that configures **which tools exist** and what the
assistant is told, not just what it knows — the tool-manifest variant of
the context-file question in
[`../../agent-context-file-loading.md`](../../agent-context-file-loading.md).
`AGENTS.md` and `CLAUDE.md` carry instructions; `btw.md` carries
instructions *and* capability configuration. Given that the file is
checked into a repository, that is also a supply-chain surface worth
noting: a cloned project can turn on arbitrary code execution by adding
three lines — which is why the global option can veto it.
