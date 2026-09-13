# Open Interpreter — kernel output → model content

## The IOPub projection

From `interpreter/core/computer/terminal/languages/jupyter_language.py`
(`v0.4.2`), the listener that turns kernel messages into the harness's
internal message format. Abridged to the dispatch:

```python
if msg["msg_type"] == "stream":
    line, active_line = self.detect_active_line(content["text"])
    if active_line:
        message_queue.put({"type": "console", "format": "active_line", "content": active_line})
    message_queue.put({"type": "console", "format": "output", "content": line})

elif msg["msg_type"] == "error":
    content = "\n".join(content["traceback"])
    ansi_escape = re.compile(r"\x1B\[[0-?]*[ -/]*[@-~]")
    content = ansi_escape.sub("", content)          # strip colour codes
    message_queue.put({"type": "console", "format": "output", "content": content})

elif msg["msg_type"] in ["display_data", "execute_result"]:
    data = content["data"]
    if "image/png" in data:
        message_queue.put({"type": "image", "format": "base64.png", "content": data["image/png"]})
    elif "image/jpeg" in data:
        message_queue.put({"type": "image", "format": "base64.jpeg", "content": data["image/jpeg"]})
    elif "text/html" in data:
        message_queue.put({"type": "code", "format": "html", "content": data["text/html"]})
    elif "text/plain" in data:
        message_queue.put({"type": "console", "format": "output", "content": data["text/plain"]})
    elif "application/javascript" in data:
        message_queue.put({"type": "code", "format": "javascript", "content": data["application/javascript"]})
```

Three things to take from it.

**The `elif` chain is a priority order over the MIME bundle, and it is
the right one.** A kernel emits *several* representations of the same
object; picking `text/plain` first would mean every plot arrives as
`<Figure size 640x480 with 1 Axes>`. Picking the image first is what
makes a matplotlib figure reach a vision model. (Compare
[`../jupyter-mcp/`](../jupyter-mcp), which formalises exactly this as
`output_mime()` with the comment *"`text/plain` is the fallback every
kernel attaches, so preferring it would throw away the image in every
image output."*)

**`error` is flattened into `output`.** The traceback becomes ordinary
console text, distinguishable only by looking like a traceback. There is
no `isError` equivalent reaching the model — so the model's only signal
that the cell failed is the prose. ANSI stripping is correct and
frequently forgotten; escape codes are pure token cost and actively
confuse models that have not seen many of them.

**Matplotlib is forced to `Agg`.** From the constructor comment:

```
# Use Agg, which bubbles everything up as an image.
# Not perfect (I want interactive!) but it works.
```

This is the plumbing that makes plots arrive at all — an interactive
backend would open a window on the user's machine and emit nothing to
IOPub. Every kernel-backed agent in this folder does the equivalent.

## Truncation

`interpreter/core/utils/truncate_output.py`, verbatim:

```python
def truncate_output(data, max_output_chars=2800, add_scrollbars=False):
    needs_truncation = False

    message = f"Output truncated. Showing the last {max_output_chars} characters. You should try again and use computer.ai.summarize(output) over the output, or break it down into smaller steps.\n\n"

    if add_scrollbars:
        message = (
            message.strip()
            + f" Run `get_last_output()[0:{max_output_chars}]` to see the first page.\n\n"
        )

    # Remove previous truncation message if it exists
    if data.startswith(message):
        data = data[len(message) :]
        needs_truncation = True

    if len(data) > max_output_chars or needs_truncation:
        data = message + data[-max_output_chars:]

    return data
```

Default `max_output = 2800` characters — roughly 700 tokens, an order of
magnitude tighter than the 25,000-token cap
[`../../agent-tool-result-transport.md`](../../agent-tool-result-transport.md)
§3e records for Claude Code, and appropriate to a loop that expects many
small steps rather than a few large ones.

Four details worth stealing:

- **Keeps the tail.** For a REPL that is right: the traceback and the
  final `print` are at the end. For a file read it would be wrong. A
  harness with both needs both policies, keyed on the tool.
- **The notice names a recovery action** — summarise, or take smaller
  steps — rather than just announcing the loss. This is the discipline
  [`../../agent-tool-implementations.md`](../../agent-tool-implementations.md)
  §6a calls "every truncation states the next call".
- **The notice is idempotent.** It strips a previous notice before adding
  one, so re-truncated content does not accumulate banners.
- **The `add_scrollbars` path is dead**, and the source says why:
  *"This won't work because truncated code is stored in
  interpreter.messages"* — the full output was never kept, so the offer
  to page back to the head cannot be honoured. An honest comment about a
  real constraint: **paging requires the harness to retain what it
  elided**, which is the whole argument for a ref-and-store design rather
  than a truncate-in-place one.
