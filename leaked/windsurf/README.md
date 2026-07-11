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

## Self-verification and testing

See [`agent-self-verification.md`](../../agent-self-verification.md) for
the cross-source comparison this feeds into. **Effectively absent** —
the weakest of any source checked for this doc so far, closer to the
doc's "Absences" list than to §7's "prompted-only" bucket, despite
having by far the richest tool surface in this collection (30 tools,
including full browser automation and deployment).

- The nearest thing to a "check your work" instruction only covers
  *debugging*, not post-edit verification: "When debugging, only make
  code changes if you are certain that you can solve the problem.
  Otherwise, follow debugging best practices: 1. Address the root cause
  instead of the symptoms. 2. Add descriptive logging statements...
  3. Add test functions and statements to isolate the problem." That's
  diagnostic-testing-to-isolate-a-bug advice, not a check that a fix is
  actually correct once made.
- After finishing, the prompt authorizes *demonstrating* the change
  rather than *verifying* it: "proactively run terminal commands to
  execute the USER's code for them... Run the app and try uploading and
  searching for photos" — showing the app work is framed as a UX nicety
  for the user to see, with no instruction to check the output for
  errors or treat a failure as blocking.
- No test-runner tool, no build-checking tool, and — despite the size of
  the tool surface — no `read_lints`-equivalent diagnostic tool exists;
  the only "lint" reference anywhere in `tools-wave-11.txt` is a passive
  labeling parameter on `replace_file_content` ("IDs of lint errors this
  edit aims to fix... they'll have been given in recent IDE feedback"),
  which attributes an edit to a lint fix rather than actively checking
  for one.
- `check_deploy_status` only confirms a deployment build succeeded — an
  infrastructure-status check, not a code-correctness one, and is
  explicitly gated behind an existing `deploy_web_app` call and user
  request rather than run proactively.
- No SWE-bench-lineage reproduce/fix/verify echo, no "don't modify the
  tests" instruction, no bounded-retry cap on fix loops (contrast
  Cursor's and Devin's 3x caps), no `/review`-style command, no
  mandatory pre-completion reflection tool (contrast Devin's `<think>`
  checkpoint) — none of it is present anywhere in these two files.

## Compaction and turn output

See [`agent-context-compaction.md`](../../agent-context-compaction.md)
and [`agent-turn-output.md`](../../agent-turn-output.md) for the
cross-source comparisons these feed into.

- **Compaction — a genuinely novel strategy, not a fit for the doc's
  existing typology: sidestep recovery by externalizing before
  compaction happens, rather than engineering a better summary at
  compaction time.** The `<memory_system>` block states the underlying
  problem in stronger terms than any other source surveyed: "Remember
  that you have a limited context window and ALL CONVERSATION CONTEXT,
  **including checkpoint summaries, will be deleted**. Therefore, you
  should create memories liberally to preserve key context." Two things
  make this distinctive:
  - **Even the summary isn't trusted to survive** — a stronger claim
    than this doc's other "the summary is the only surviving record"
    findings (Crush, Gemini CLI), since here the survivor itself is
    stated to eventually go too.
  - **The prescribed mitigation is a separate, persistent, queryable
    memory store** (`create_memory`), written to proactively and
    without waiting for a natural break point: "You DO NOT need USER
    permission to create a memory... You DO NOT need to wait until the
    end of a task... You DO NOT need to be conservative about creating
    memories." Rather than one better compaction pipeline, the design
    bet is continuous externalization of important facts *before* any
    compaction/deletion event, via a durable store outside the
    conversation entirely.
  - A second, related recovery mechanism: `trajectory_search` lets the
    model semantically search its own **past session history** on
    demand ("Call this tool when the user @mentions a @conversation")
    — a queryable retrieval tool, distinct from both this doc's "static
    pointer back to the transcript" pattern and its "sole surviving
    summary" pattern; a third recovery-philosophy variant.
  - What's *not* captured: the actual checkpoint-summarization prompt
    text, trigger logic, or any token-budget number — "checkpoint" is
    used as an established term, implying real orchestration exists,
    just not represented in this extraction.
- **Title generation — not captured**, despite the richest tool
  surface in this collection. No conversation-naming instruction
  anywhere; all "title"-adjacent hits are unrelated (a deployed
  server's display name, a memory entry's title, the mandatory
  per-tool-call `toolSummary` field below, a fetched webpage's HTML
  `<title>`).
- **Reasoning display — absent**, no analog to Devin's `<think>` tool
  or Cursor's thinking-narration references found in either file.
- **A structurally novel narration mechanism, worth flagging for
  `agent-turn-output.md`'s narration-vs-native-block distinction**: a
  `toolSummary` argument is **required as the first parameter on every
  one of the 30 tools** — "Brief 2-5 word summary of what this tool is
  doing... you must specify this argument first over all other
  arguments." Every other "narrate before acting" instruction surveyed
  in this collection (Gemini CLI's "Explain Before Acting," Codex's
  streaming narration, OpenCode's `beast.txt` rule) is free text the
  model chooses to emit in its message, sitting outside the tool
  call's own schema. Windsurf instead embeds the narration requirement
  directly into the tool call's JSON schema as a required field — the
  model cannot call a tool at all without populating a short action
  label as a structured argument. A fourth narration mechanism, not
  matching either "native reasoning block" or "free-text prompted
  narration": **schema-embedded narration**.
