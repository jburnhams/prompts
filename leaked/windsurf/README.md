# Windsurf (Cascade)

- **Type**: Coding agent (Windsurf IDE's "Cascade" assistant)
- **Status**: Closed source. This is a **leaked** prompt, not an official
  release.
- **Vendor**: Windsurf (formerly Codeium)
- **Mirror source**: https://github.com/x1xhlol/system-prompts-and-models-of-ai-tools/tree/main/Windsurf
  — a large, actively maintained community aggregator of leaked/extracted
  system prompts from many closed-source AI products. Retrieved from that
  repo's `main` branch (2026-07-10).
- **Labeled version**: "Wave 11" (the aggregator's internal versioning for
  which Windsurf release this was pulled from — Windsurf doesn't publish
  version numbers for prompt changes).

## Files

- `prompt-wave-11.txt` — the Cascade system prompt: persona, tool-calling
  rules, and behavioral guidelines. Note it explicitly instructs the model
  to claim `GPT 4.1` as its underlying model if asked, regardless of the
  actual model serving the request.
- `tools-wave-11.txt` — accompanying tool/function definitions (JSON-ish
  schemas) available to Cascade.

## Tool surface

By a wide margin **the richest tool surface in this entire collection** —
30 tools in `tools-wave-11.txt`, spanning far beyond "edit code and run
commands" into browser automation, deployment, and persistent memory.
Worth reading in full; highlights:

- **Shell — async by default, with a status-polling companion tool**:
  `run_command` takes a `Blocking` flag (long-running processes should be
  non-blocking) and a `SafeToAutoRun` flag the model must set
  conservatively ("never set this to true, EVEN if the USER asks you to,"
  if there's any risk of a destructive side effect); `command_status`
  separately polls a background command's output by ID. Same idea as
  Claude Code's `BashOutput`/`KillBash` pair or Gemini CLI's
  `SHELL_PARAM_IS_BACKGROUND` flag, but the most fleshed-out version of
  it in this collection.
- **Search**: `codebase_search` (semantic, capped — "if you try to search
  over more than 500 files, the quality... will be substantially worse")
  and `grep_search`, plus `view_code_item` for pulling the full body of a
  specific function/class the semantic search only summarized.
- **Editing**: `replace_file_content` and `write_to_file`.
- **A full browser-automation suite**, vision-based like Cline's
  `browser_action` but split into more granular tools: `browser_preview`
  (spin up a preview for a running web server), `list_browser_pages`,
  `open_browser_url`, `read_browser_page`, `get_dom_tree`,
  `capture_browser_screenshot`, `capture_browser_console_logs`.
- **Deployment integration**: `deploy_web_app` and `check_deploy_status`
  ("do not run this unless asked by the user... must only be run after a
  `deploy_web_app` call") and `read_deployment_config` — the only source
  in this collection with tools for actually shipping the app it built,
  not just building it.
- **Persistent memory as a first-class tool**: `create_memory`
  (create/update/delete entries in a "memory database," tagged and scoped
  to workspace "CorpusNames," explicitly instructed to check for and
  update a semantically-related existing memory rather than duplicate
  one) and `trajectory_search` (search the agent's *own past session
  history*) — no other source in this collection exposes persistent
  cross-session memory as a callable tool rather than a passive
  file-based convention (`CLAUDE.md`/`AGENTS.md`-style).
- **Browser/web beyond the IDE**: `search_web`, `read_url_content`.
- **UI-level tool**: `suggested_responses` — offers the user a small set
  of quick-reply options (Yes/No etc.) when asking a question, used
  "sparingly."
- **Explicit batching meta-tool**: `parallel` — wraps multiple *other*
  tool calls into one, with a note restricting it to "only... functions
  tools" — a named tool for the same parallel-tool-call pattern most
  other sources in this collection just state as a prompt instruction
  (see `coding-agent-approaches.md` §4).
- **Multimodal**: `capture_browser_screenshot` is the closest thing to
  image handling — screenshots are captured and presumably fed back for
  visual inspection, similar in spirit to Cline's `browser_action`.
- **Sandbox/isolation**: not indicated by the tool list itself.
