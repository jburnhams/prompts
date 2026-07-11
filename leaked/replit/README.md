# Replit Agent

- **Type**: Coding/app-building agent · **Vendor**: Replit
- **Status**: closed source (leaked)
- **Mirror source**: https://github.com/x1xhlol/system-prompts-and-models-of-ai-tools/tree/main/Replit (2026-07-10)

## Files
- `Prompt.txt` — system prompt.
- `Tools.json` — tool/function definitions.

Note a likely provenance mismatch worth flagging: `Prompt.txt`'s
`<identity>` names itself "**Replit Assistant**," a chat-based
proposal system with no bash/execution capability of its own (edits are
proposed via `<proposed_file_replace_substring>`-style XML tags), while
`Tools.json` contains `bash`, deployment tools, and workflow tools —
the surface of the more autonomous **Replit Agent** product. These
appear to be two different snapshots bundled under one leaked source,
not one consistent extraction.

## Self-verification and testing

See [`agent-self-verification.md`](../../agent-self-verification.md) for
the cross-source comparison this feeds into. `Prompt.txt` itself has
**zero** verification/testing language anywhere in its 138 lines — the
entire self-verification story for this source lives in `Tools.json`'s
tool descriptions, and it's a genuinely distinctive pattern: evidence is
gathered mechanically, but the final pass/fail call is handed to the
**human user**, not to the model or to any deterministic check.

- **Three "feedback tools" share one shape** — run/observe the app,
  capture objective evidence, then ask the user one targeted question
  and wait:
  - `web_application_feedback_tool`: "captures a screenshot and checks
    logs to verify whether the web application is running... If the
    application is running, the tool displays the app, asks user a
    question, and waits for user's response. Use this tool when the
    application is in a good state and the requested task is complete."
  - `shell_command_application_feedback_tool`: "execute interactive
    shell commands and ask questions about the output or behavior of
    CLI applications... to test and verify the functionality of
    interactive CLI applications... where user input and real-time
    interaction are required."
  - `vnc_window_application_feedback`: the same pattern for desktop
    apps viewed via VNC.
  None of these fit this collection's existing categories cleanly: not
  a deterministic gate (no blocking precondition — the tool just
  displays results), not a separate-LLM judge (the judge is the human),
  not prompted-only (there's a concrete, tool-mediated evidence-capture
  step). Best described as **automated evidence-gathering paired with a
  mandatory human-confirmation gate** — a pattern not seen phrased this
  way elsewhere in the collection.
- **Completion itself is explicitly deferred to the user, not
  self-assessed**: `report_progress` — "Call this function once the
  user explicitly confirms that a major feature or task is complete. Do
  not call it without the user's confirmation." `suggest_deploy` goes
  further, asserting verification happened without checking it: "Use
  this tool once you've validated that the project works as expected...
  Once this tool is called, there is no need to do any follow up steps
  or verification" — "you've validated" is asserted by the model, not
  mechanically confirmed by the tool.
- **One genuinely deterministic, non-LLM check exists but is narrow**:
  `check_database_status` — "Check if given databases are available and
  accessible... verify the connection and status of specified
  databases." A real mechanical check, but a standalone diagnostic, not
  wired to gate any "done" signal.
- No SWE-bench-lineage echo, no separate-LLM-judge call, no
  `/review`-style command, no hook-based gate. The only rollback
  primitive found is `str_replace_editor`'s single-file `undo_edit` —
  not verification-triggered.

## Compaction and turn output

See [`agent-context-compaction.md`](../../agent-context-compaction.md)
and [`agent-turn-output.md`](../../agent-turn-output.md) for the
cross-source comparisons these feed into. Nothing found for either
topic in either file (checked separately per the provenance-mismatch
note above). No context-window/token-budget language, no handoff/resume
concept, no session-title/rename field or generation logic anywhere in
`Prompt.txt` or `Tools.json`.

- **A near-miss worth flagging so it isn't mistaken for a title
  mechanism**: `Prompt.txt`'s "Summarizing Proposed Changes" section
  defines a `<proposed_actions summary="...">` tag capped at 58
  characters, and `Tools.json`'s `report_progress` tool has a similarly
  constrained `summary` field. Both are **per-turn action summaries**
  ("what did this turn's edits do"), not session-title generation
  ("what should this whole session/task be called") — a structurally
  adjacent but distinct kind of thing from every title mechanism this
  collection has found elsewhere (Goose's/Crush's/OpenCode's/Claude
  Code's one-shot session-naming calls).
- `report_progress`'s formatting rules are also unusually specific for
  something embedded in a tool-parameter description rather than the
  system prompt: "maximum of 5 items... no more than 30 words... Put a
  ✓ before every item you've done recently and → for the items in
  progress... Avoid technical terms, as users are non-technical. Don't
  use emojis." Prompted-narration-style constraints, just relocated to
  a tool schema instead of prompt text.
- No thinking/reasoning-display language anywhere — `Prompt.txt`'s
  proposal-only "Assistant" framing has no visible agent-loop/reasoning
  mechanism at all, and `Tools.json` is pure tool schema.
- Given the provenance mismatch already noted, and that neither file is
  runtime/orchestration code, both absences read as capture gaps rather
  than confirmed design choices — Replit Agent's known
  checkpoint/project-naming UI strongly suggests the relevant logic
  just isn't in what was extracted here.
