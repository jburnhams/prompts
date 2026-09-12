# Open Interpreter

- **Type**: local code-interpreter agent · **Vendor**: Open Interpreter /
  Killian Lucas · **Licence**: AGPL-3.0 at the version read
- **Source**: https://github.com/OpenInterpreter/open-interpreter —
  tag `v0.4.2` @ `13061d2` (2024-10-24)
- **Retrieved**: 2026-09-12

Included as the **archetype of the one-tool code interpreter**: a single
`execute(language, code)` function, ten language backends behind it, and
a system prompt short enough to quote in full.

## The 2026 pivot, which is itself the finding

`main` today (`2885d0d`, 2026-09-08) is **not this program**. Open
Interpreter has been rewritten in Rust as a Codex-derived *coding* agent
("A coding agent optimized for low-cost models"), with a `.codex/`
skills directory and a Bazel build. The Python code-interpreter is gone
from the default branch; `v0.4.2` is the last release that contains it.

That direction of travel — the most famous open-source "chat with your
data by running code" project ending up as a coding agent — is one of two
data points in this folder about the category's gravity. The other is
[`positron/`](../positron): Posit's data-science assistant leaving its
open-source repository entirely.

## Files

| File | Upstream path | What it is |
|---|---|---|
| [`system-message.md`](./system-message.md) | `interpreter/core/default_system_message.py` | The whole default system prompt, verbatim |
| [`execute-tool.md`](./execute-tool.md) | `interpreter/core/llm/run_tool_calling_llm.py`, `.../terminal/terminal.py` | The `execute` tool schema and the language registry |
| [`output-handling.md`](./output-handling.md) | `.../languages/jupyter_language.py`, `interpreter/core/utils/truncate_output.py` | How kernel messages become model-visible content, and the truncation rule |
| [`data-profiles.md`](./data-profiles.md) | `interpreter/terminal_interface/profiles/defaults/` | The two data-specific profiles that ship: Postgres-over-Ollama and Snowpark |

## What it gets right, and what it shows by failing

**One tool, `enum`-constrained language.** The tool description is one
sentence and the `language` enum is *filled in at runtime* from the
registry of installed backends — so the model's choice set is exactly the
set that will work. Ten backends ship: Python (a real Jupyter kernel),
Shell, JavaScript, HTML, R, PowerShell, AppleScript, React, Java, Ruby.

**The stateful-language rule, stated as a rule.** The prompt draws the
distinction the rest of this folder is organised around, and in 2024:

> for *stateful* languages (like python, javascript, shell, but NOT for
> html which starts from 0 every time) **it's critical not to try to do
> everything in one code block.** You should try something, print
> information about it, then continue from there in tiny, informed steps.

**Truncation from the tail, not the head.** `truncate_output` keeps the
**last** 2,800 characters, prepends a notice, and — unusually — names a
recovery action in the notice (`computer.ai.summarize(output)`). Keeping
the tail is the right call for a REPL, where the useful part of a long
output is the traceback or the final print; it is the wrong call for a
file read, where the useful part is the top. Few harnesses distinguish.

**The failure worth recording** is the R backend. Python gets a
`jupyter_client` kernel with a full MIME bundle; R gets
`SubprocessLanguage` — a long-running `R -q --vanilla` process that the
harness talks to over stdout, with per-line `cat("##active_line1##")`
markers injected into the user's code, a `tryCatch` wrapper, and an
`##end_of_execution##` sentinel. It works, and it can never return a
plot: there is no channel for one. That asymmetry — *the host language
gets rich output, every other language gets text* — recurs in every
multi-language harness in this folder.
