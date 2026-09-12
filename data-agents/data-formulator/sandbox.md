# Data Formulator — the sandbox, and what a tool returns

`py-src/data_formulator/sandbox/`. Three backends behind one abstract
base, and the base's return contract is the interesting part.

## The contract: a tool returns a DataFrame

```python
class Sandbox(ABC):
    """Base class for code-execution sandboxes."""

    @abstractmethod
    def run_python_code(
        self,
        code: str,
        workspace,
        output_variable: str,
    ) -> dict:
        """Execute a Python script and return the resulting DataFrame.

        The script runs with the workspace directory as its working
        directory (read-only).  Scripts can therefore read files directly
        via e.g. ``pd.read_csv("file.csv")``.
        ...
        Returns
        -------
        dict
            ``{'status': 'ok', 'content': DataFrame}``  on success, or
            ``{'status': 'error', 'content': str}``    on failure.
        """
```

**The execution tool's success value is a `pandas.DataFrame`, not text.**
The model named a variable (`output_variable`); the harness lifts that
object out of the namespace and carries it onward as a typed value —
into the renderer, into the workspace as a new table, into the next
action's `input_tables`.

This is the in-process version of the question the artifact discussion in
[`../../agent-design/artifacts.md`](../../agent-design/artifacts.md) is
really asking. The model never sees the frame's bytes and never encodes
them; it sees whatever projection the next step needs. Compare
[`../vanna/`](../vanna), which does the same across a process boundary by
writing a CSV and returning the filename, and
[`../pandasai/`](../pandasai), which does it by requiring the generated
code to assign a typed `result` dict.

The `{'status': 'ok'|'error', 'content': ...}` envelope is worth noting
against `isError` in MCP: a discriminated union where the error case is a
*string* and the success case is a *value*. Simple, and it forces every
caller to branch.

## Three backends, and the honest name

| Backend | What it is |
|---|---|
| `docker_sandbox.py` | container per execution — the real isolation |
| `local_sandbox.py` | subprocess + CPython audit hooks — the default |
| `not_a_sandbox.py` | `exec()` in-process, no restrictions |

Calling the third one `not_a_sandbox` is a small act of engineering
honesty worth copying. A file named `local_sandbox.py` and a file named
`unsafe_local.py` get chosen differently in a hurry.

## `addaudithook`, and the ordering trick

`local_sandbox.py` runs the script in a separate process
(`multiprocessing.Process` + `Pipe`) and installs a CPython audit hook
(`sys.addaudithook`) in that process. Abridged:

```python
# Scrub sensitive environment variables before accepting any code.
# Legitimate sandbox code (pandas/numpy transforms) never needs these.
_SENSITIVE_PATTERNS = ("KEY", "SECRET", "TOKEN", "PASSWORD", "CREDENTIAL", "CONNECTION_STRING")
for _key in list(os.environ):
    if any(p in _key.upper() for p in _SENSITIVE_PATTERNS):
        del os.environ[_key]

# Pre-import heavy libraries BEFORE audit hooks so that libraries
# needing ctypes/dlopen (e.g., scipy/sklearn -> BLAS) can load freely.
import numpy, pandas, duckdb
# pandas defers these until read_parquet() is actually called, which
# would otherwise import them while the audit hook is active.
import pyarrow, pyarrow.parquet, pyarrow.dataset
import scipy
from sklearn import linear_model, cluster, tree, ensemble, svm, neighbors, decomposition, preprocessing

def block_mischief(event, arg):
    # Block file writes (only allow reading)
    if event == "open" and type(arg[1]) == str and arg[1] not in ("r", "rb"):
        raise IOError("file write forbidden")
    # Restrict file reads to the workspace directory during code execution.
    if (event == "open" and arg[1] in ("r", "rb") and _allowed_workspace[0] is not None):
        resolved = os.path.realpath(arg[0])
        if (not resolved.startswith(_allowed_workspace[0])
                and not resolved.startswith(_allowed_lib_prefixes)
                and resolved not in _allowed_runtime_files):
            raise IOError(f"file read outside workspace forbidden: {arg[0]}")
    _blocked_prefixes = ("subprocess", "shutil", "winreg", "webbrowser")
    if event.split(".")[0] in _blocked_prefixes:
        raise IOError("potentially dangerous, filesystem-accessing functions forbidden")
    # We intentionally do NOT add "os" to _blocked_prefixes because libraries
    # like pandas/numpy rely on safe os.* audit events (os.listdir, os.scandir,
    # os.stat) that share the same prefix.
    _blocked_os_events = frozenset({
        "os.system", "os.exec", "os.spawn", "os.fork",
        "os.kill", "os.killpg", "os.startfile",
        "os.putenv", "os.unsetenv",
    })
```

Four techniques here, all of which generalise past this codebase:

**Pre-import before arming.** An audit hook strict enough to be useful
will block the `dlopen` that scipy needs for BLAS. The fix is to warm
every allowed library into `sys.modules` *before* installing the hook —
including `pyarrow.parquet`, which pandas lazily imports inside
`read_parquet()` and would otherwise import under the hook. This is the
kind of detail that decides whether a sandbox ships or gets disabled.

**Scrub the environment, and say why.** Removing anything matching
`KEY|SECRET|TOKEN|PASSWORD|CREDENTIAL|CONNECTION_STRING` before accepting
code, with a one-line justification (*"legitimate sandbox code never needs
these"*) that makes the rule reviewable. Contrast Open Interpreter's
Postgres profile, which puts a DSN in the system prompt.

**Allowlist by directory, with the library paths carved out.** Reads are
confined to the workspace *plus* stdlib/site-packages/`_MEIPASS`, resolved
through `os.path.realpath` so a symlink cannot walk out. Writes are
refused outright — the tool's output is a returned DataFrame, so the
script has nothing legitimate to write.

**Prefix-blocking with a stated exception.** `os.*` is *not* blocked
wholesale, because pandas depends on `os.listdir` / `os.scandir` /
`os.stat`; the dangerous members are enumerated instead. The comment
explaining the non-obvious omission is what stops a later contributor
"fixing" it.

The prompt-level allowlist in `core/SKILL.md` ("Not allowed: matplotlib,
plotly, seaborn, requests, subprocess, os, sys, io") and this hook are
**two independent layers saying nearly the same thing**, which is the
right relationship: the prompt keeps the model from wasting a turn, the
hook keeps the failure from mattering. Note they are not identical —
matplotlib is barred by prompt only, because the ban on drawing is a
product decision, not a security one.
