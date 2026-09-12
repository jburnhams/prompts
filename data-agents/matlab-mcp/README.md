# MATLAB MCP Server (MathWorks)

- **Type**: vendor MCP server over a live MATLAB session · **Vendor**:
  MathWorks · **Licence**: Apache-2.0
- **Source**: https://github.com/matlab/matlab-mcp-server — `main` @
  `2e44b0a`, tag `v0.13.0` (2026-09-01). Written in Go.
- **Retrieved**: 2026-09-12

The answer to "what about MATLAB?", and more usefully, **what a language
vendor builds when it decides to be agent-addressable**. Announced
alongside a MATLAB Agentic Toolkit (a library of Agent Skills) in April
2026; the server itself is open.

The shape is worth noting because it is the same shape
[`../btw/`](../btw) arrives at for R and
[`../jupyter-mcp/`](../jupyter-mcp) for Python: **the language is reached
through a session, not through a code tool the harness owns**, and the
session's lifecycle is itself part of the tool surface.

## The tools

Two registration sets, single-session and multi-session.

**Single-session** (the server manages one MATLAB):

| Tool | Description (verbatim) |
|---|---|
| `evaluate_matlab_code` | "Evaluate a string of MATLAB code (`code`) in an existing MATLAB session. Optionally specify a project folder (`project_path`) to set as the current working folder before execution. Returns the command window output from code execution. **WARNING: Do not use `restoredefaultpath` as it will remove the MCP server functions from the path and break this tool's ability to communicate with MATLAB.**" |
| `run_matlab_file` | "Execute a MATLAB script file (`script_path`) in an existing MATLAB session and capture its command window output. The script runs with the working folder automatically set to the script's location. The script must exist and be a valid .m file. Returns the command window output or a success message if no output is generated." |
| `run_matlab_test_file` | "Execute a MATLAB test script (`script_path`) using MATLAB's built-in runtests function and return comprehensive test results. Designed specifically for MATLAB unit test files that follow MATLAB's testing framework conventions." |
| `check_matlab_code` | "Perform static code analysis on a MATLAB script (`script_path`) using MATLAB's built-in Code Analyzer function … Returns warnings about coding style, potential errors, deprecated functions, performance issues, and best practice violations. It also includes information about where each issue occurs and how it can be fixed in MATLAB. **This is a non-destructive, read-only operation that helps identify code quality issues without executing the script.**" |
| `detect_matlab_toolboxes` | "Returns information about installed MATLAB and toolboxes, including version numbers." |

**Multi-session** adds `start_matlab_session` (returns a `session_id`),
`stop_matlab_session`, `list_available_matlabs` ("List the installed
MATLAB versions on the host and their root directories"), and
`eval_in_matlab_session` (the same eval, keyed by `session_id`).

Three observations.

**The self-referential warning is the honest kind.** *"Do not use
`restoredefaultpath` as it will remove the MCP server functions from the
path and break this tool's ability to communicate with MATLAB."* The
bridge is implemented as MATLAB functions on the session's path, so a
perfectly ordinary MATLAB command severs the agent's own connection. The
description says so. Every harness that injects itself into the runtime
it controls has a command like this; almost none name it.

**`detect_matlab_toolboxes` is capability discovery as a tool.** MATLAB's
functionality is licensed per toolbox, so what the model can write
depends on what is installed *on this machine, under this licence*.
Rather than guessing and failing, the model asks. The equivalent for
Python is the import list, which every harness in this folder handles by
declaring an allowlist in the prompt — a static answer to a question that
is dynamic.

**`check_matlab_code` is a linter, exposed separately from execution and
labelled read-only.** Static analysis before you run is cheaper than a
failed run in any language; here it is also the only way to check a
script without the side effects of executing it. The pairing of a
read-only checker with a destructive evaluator is exactly the
inspection/action split from [`../data-formulator/`](../data-formulator),
arrived at from the language-tooling side.

## Annotations as named classes

`internal/adaptors/mcp/tools/annotations/annotations.go`:

```go
// annotations represents tool safety classification metadata.
// All fields are required and use plain bool types to ensure complete specification.
// This design insulates the codebase from MCP SDK's optional field semantics.
// The type is unexported to enforce construction via factory functions only.
type annotations struct {
	readOnly    bool
	destructive bool
	idempotent  bool
	openWorld   bool
}

// NewReadOnlyAnnotations creates annotations for tools that perform inspection
// or query operations without modifying state or executing user code.

// NewDestructiveAnnotations creates annotations for tools that execute code,
// modify state, or interact with external services.

// NewIdempotentWriteAnnotations creates annotations for tools that write or
// overwrite local state but produce the same result when called repeatedly
// with the same arguments (e.g. running an analysis that overwrites a results
// directory).

// NewReadOnlyOpenWorldAnnotations creates annotations for tools that query
// external services without modifying any state (local or remote). Do not use
// this for tools that mutate remote state: the read-only hint tells hosts they
// may skip user confirmation, so misusing it lets writes through silently.
```

This is the most disciplined handling of MCP's four annotation flags in
anything read for this collection, and the reasoning is all in the
comments:

- **Four booleans become four named classes.** Sixteen combinations are
  expressible; four are meaningful. A constructor per meaningful
  combination makes the choice a one-line decision at each call site and
  makes an unusual combination visible in review.
- **All fields required, plain `bool`.** MCP's SDK uses `*bool` for some
  flags, so "false" and "unspecified" are different. Forcing complete
  specification internally and converting at the boundary means a
  forgotten flag cannot silently mean "unknown".
- **The type is unexported.** You cannot hand-roll one.
- **The consequence of misuse is stated**: *"the read-only hint tells
  hosts they may skip user confirmation, so misusing it lets writes
  through silently."* That sentence is the whole argument for why
  annotations are a safety surface and not documentation.

## Custom tools: user-declared functions become MCP tools

From `guides/custom-tools.md`:

> You can expose any MATLAB functions as MCP tools defined in JSON files.
> The server loads your tool definitions at startup and registers them
> alongside the built-in tools. When your AI application calls a custom
> tool, the server executes the MATLAB function and returns the command
> window output. The MATLAB function must be on the MATLAB path. To update
> your tool definitions, edit the extension files and restart the server.
>
> Custom tool arguments support `string`, `number`, `integer`, and
> `boolean` data types.

```json
{
  "tools": [
    {
      "name": "greet_user",
      "title": "Greet User",
      "description": "Displays a greeting for the given user",
      "inputSchema": {
        "type": "object",
        "properties": {
          "name": { "type": "string", "description": "Name of the user to greet" },
          "age":  { "type": "number", "description": "Age of the user" }
        },
        "required": ["name", "age"]
      }
    }
  ],
  "signatures": {
    "greet_user": {
      "function": "greet_user",
      "input": { "order": ["name", "age"] }
    }
  }
}
```

Loaded with `--extension-file` (repeatable, also settable by environment
variable).

**The split between `tools` and `signatures` is the good idea.** `tools`
is the model-facing contract — name, title, description, JSON Schema.
`signatures` is the binding — which MATLAB function, and how named JSON
arguments map onto MATLAB's positional ones. Two audiences, two
documents, in one file. Renaming the MATLAB function does not change the
model's view; rewording the description does not touch the call.

This is the general answer to "one `execute` or many focused tools",
made operational: **ship one `execute`, and let the deployment declare
focused tools over its own domain functions.** The engineering team that
knows the codebase writes the schemas; the harness vendor doesn't have to
guess. Scalar-only arguments (`string`, `number`, `integer`, `boolean`)
keep the binding honest — no marshalling of matrices through JSON — and
the "restart the server to reload" constraint keeps the tool list stable
within a session, which matters because tool-list churn invalidates
prompt cache.

The obvious thing it does *not* do: the return is "the command window
output", i.e. text. A MATLAB function that produces a figure or a table
has no channel for it. Same asymmetry as Open Interpreter's R backend,
and the reason a language server bolted onto an agent usually stops at
text.
