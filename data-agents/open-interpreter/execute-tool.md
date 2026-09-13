# Open Interpreter — the `execute` tool and the language registry

## The tool schema

Verbatim from `interpreter/core/llm/run_tool_calling_llm.py` (`v0.4.2`):

```python
tool_schema = {
    "type": "function",
    "function": {
        "name": "execute",
        "description": "Executes code on the user's machine **in the users local environment** and returns the output",
        "parameters": {
            "type": "object",
            "properties": {
                "language": {
                    "type": "string",
                    "description": "The programming language (required parameter to the `execute` function)",
                    "enum": [
                        # This will be filled dynamically with the languages OI has access to.
                    ],
                },
                "code": {
                    "type": "string",
                    "description": "The code to execute (required)",
                },
            },
            "required": ["language", "code"],
        },
    },
}
```

The comment is the interesting part: **the enum is populated at runtime**
from the languages actually available on the machine, so the model is
never offered a backend that would fail on invocation. This is the
cheapest possible version of capability-gated tool exposure, and it is
rarer than it should be — most multi-language harnesses list every
language they support and let the failure happen at call time.

## The language registry

From `interpreter/core/computer/terminal/terminal.py`:

```python
self.languages = [
    Ruby,
    Python,
    Shell,
    JavaScript,
    HTML,
    AppleScript,
    R,
    PowerShell,
    React,
    Java,
]
```

Dispatch is by name **or alias** (`py` → Python), case-insensitively.

Two base classes sit under these:

| Base | Backends | Mechanism | Rich output? |
|---|---|---|---|
| `JupyterLanguage` | Python | `jupyter_client.KernelManager`, real kernel, full MIME bundle over IOPub | yes — PNG, JPEG, HTML, JavaScript |
| `SubprocessLanguage` | R, Ruby, Shell, JavaScript, PowerShell, AppleScript, Java | long-lived subprocess, stdout/stderr scraping, injected line markers | **no** — text only |
| *(neither)* | HTML, React | rendered, stateless — "starts from 0 every time" | rendered to the user, not to the model |

### What `SubprocessLanguage` does to your code

`R.preprocess_code` rewrites every line of the model's program before
running it:

```python
for i, line in enumerate(lines, 1):
    processed_lines.append(f'cat("##active_line{i}##\\n");{line}')

processed_code = f"""
tryCatch({{
{processed_code}
}}, error=function(e){{
    cat("##execution_error##\\n", conditionMessage(e), "\\n");
}})
cat("##end_of_execution##\\n");
"""
```

Three things are being bought with this: a progress cursor (which line is
running), an error channel distinguishable from ordinary stdout, and a
completion sentinel so the reader knows when to stop. Three things are
being paid: line numbers in any R error no longer match the model's
source, a `cat` in the user's own code can forge a marker, and `tryCatch`
changes the program's semantics (an error no longer propagates).

The Python path needs none of this because the kernel protocol already
carries execution state, errors and completion as typed messages. **The
gap between "we have a protocol" and "we scrape stdout" is the whole
difference between the host language and the others**, and it is why
"should the agent speak R?" is usually really "is there a kernel?".
