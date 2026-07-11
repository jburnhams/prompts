# Warp

- **Type**: Coding agent (agentic terminal) · **Vendor**: Warp
- **Status**: closed source (leaked)
- **Mirror source**: https://github.com/x1xhlol/system-prompts-and-models-of-ai-tools/tree/main/Warp.dev (2026-07-10)

## Files
- `Prompt.txt` — system prompt.

## Self-verification and testing

See [`agent-self-verification.md`](../../agent-self-verification.md) for
the cross-source comparison this feeds into. Absent as an autonomous
mechanism, and structurally distinctive in *why*: the whole "# Task
completion" section is built around **not** auto-verifying.

- "Do exactly what was requested by the user, no more and no less! ...
  if a user asks you to fix a bug, once the bug has been fixed, don't
  automatically commit and push the changes without confirmation.
  Similarly, don't automatically assume the user wants to run the build
  right after finishing an initial coding task."
- The one carve-out inverts every other §7 example in this collection:
  verification is offered, not performed — "it is also acceptable to
  ask the user if they'd like to lint or format the code after the
  changes have been made," and confirming a fix "typically ensur[es]
  valid compilation... or by writing and running tests," but only after
  *asking if the user wants* that check. Every other prompted-only
  source in this doc instructs the agent to verify on its own
  initiative; Warp explicitly requires permission first.
- This sits in tension with the prompt's own general default: "bias
  toward action to address the user's query. If the user asks you to do
  something, just do it, and don't ask for confirmation first" —
  verification is carved out as the specific exception to that bias.
- No SWE-bench-lineage echo, no bounded-retry cap, no deterministic
  gate, no judge call, no `/review` command, no hook system — the tool
  set here (`run_command`, `read_files`, `grep`, `file_glob`,
  `edit_files`, `create_file`) has no completion-gating logic anywhere.

## Compaction and turn output

See [`agent-context-compaction.md`](../../agent-context-compaction.md)
and [`agent-turn-output.md`](../../agent-turn-output.md) for the
cross-source comparisons these feed into. Nothing found for either
topic in `Prompt.txt`'s 162 lines — a targeted keyword search (summar-,
compact, context window, token, truncat, title, session name, rename,
thinking, reasoning, scratchpad) turned up only unrelated hits about
**file-reading** truncation ("This can only respond with 5,000 lines of
the file. If the response indicates that the file was truncated, you
can make a new request to read a different line range"). Given Warp's
terminal app visibly supports long-running, named agent sessions, this
reads as a capture gap — this single, short, general-purpose system
prompt almost certainly doesn't carry whatever context-management and
session-naming logic lives in the surrounding app, not evidence either
mechanism is genuinely absent from the product.
