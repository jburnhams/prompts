# Google Antigravity

- **Type**: Coding agent (Google's agentic IDE, plus a terminal
  sibling — see below) · **Vendor**: Google
- **Status**: closed source (leaked)
- **Mirror sources**:
  - `Fast Prompt.txt`, `planning-mode.txt` —
    https://github.com/x1xhlol/system-prompts-and-models-of-ai-tools/tree/main/Google/Antigravity
    (2026-07-10)
  - `CLI Prompt.md` —
    https://github.com/asgeirtj/system_prompts_leaks/blob/main/Google/antigravity-cli.md
    (2026-07-11), a separate, independently-maintained aggregator from
    the x1xhlol one used everywhere else in this collection.

**Two real products, one shared harness, captured separately.** Google
launched Antigravity 2.0 in May 2026 as the official successor to
Gemini CLI (which is being sunset for non-enterprise users), shipping
simultaneously as a desktop IDE, a terminal CLI (`agy`), an SDK, and a
managed API tier. The terminal CLI's own GitHub repo
(`google-antigravity/antigravity-cli`) is a binary-distribution shell
only — no source, no prompt templates — so it doesn't qualify for this
collection's main `sources/` list; both captures here remain `leaked/`.
Diffing `CLI Prompt.md` against `Fast Prompt.txt` (451 vs. 611 lines):
same opening identity line, but the CLI capture drops the XML
structural tags (`<identity>`, `<user_information>`, `<tool_calling>`)
present in the IDE version, and — more substantively — has **zero**
mentions of `browser_subagent` or the Knowledge Subagent (both
GUI-dependent features documented below), consistent with a genuinely
distinct terminal-harness variant of the same underlying prompt rather
than a re-mirror of the same file. It does carry its own
`<planning_mode_artifacts>` section with a "Walkthrough" file
convention (`<appDataDir>/brain/<conversation-id>/walkthrough.md`) not
present in what's captured for the IDE.

## Files
- `Fast Prompt.txt` — IDE prompt for a lower-latency/"fast" response
  mode.
- `planning-mode.txt` — IDE prompt for a planning-first mode.
- `CLI Prompt.md` — the terminal (`agy`) harness's own system prompt;
  no accompanying tool-schema/JSON file was found for this capture.

## Sub-agents

Two sub-agents in `Fast Prompt.txt`, doing two genuinely different jobs —
one interactive/synchronous, one an asynchronous background process the
orchestrator only ever sees the *output* of:

- **`browser_subagent`** — spawns "an agent similar to you, with a
  different set of tools, limited to tools to understand the state of
  and control the browser," given a free-text `Task` description and a
  human-readable `TaskName`/`RecordingName` used to group and label its
  steps in the UI. Distinctive features: every browser interaction is
  "automatically recorded and saved as WebP videos to the artifacts
  directory" ("the ONLY way you can record a browser session
  video/animation" — a capability not mentioned anywhere else in this
  collection), a `waitForPreviousTools` flag for sequencing it against
  other tool calls, and an explicit post-condition requirement: "After
  the subagent returns, you should read the DOM or capture a screenshot
  to see what it did" — the orchestrator is told not to trust the
  sub-agent's self-report alone for browser state, unlike most other
  sources' "the agent's outputs should generally be trusted" framing.
- **The Knowledge Subagent** — not model-invoked at all; described as "a
  separate KNOWLEDGE SUBAGENT that reads the conversations and then
  distills the information into new KIs [Knowledge Items] or updates
  existing KIs as appropriate." This runs as a background/asynchronous
  process over past conversation history, producing a persistent
  knowledge base the *orchestrator* later reads (via KI summaries,
  falling back to raw conversation logs only when no relevant KI
  exists) — closer in spirit to Windsurf's `create_memory`/
  `trajectory_search` (persistent cross-session memory) than to a
  synchronous delegate-and-report sub-agent, but implemented as its own
  distillation agent rather than a callable memory-write tool the main
  agent invokes directly.
- **No stated concurrency-safety or turn-limit rules** for either
  sub-agent in what's captured here, unlike Gemini CLI's or Amp's
  explicit parallel/serial policies.
