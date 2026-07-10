# Google Antigravity

- **Type**: Coding agent (Google's agentic IDE) · **Vendor**: Google
- **Status**: closed source (leaked)
- **Mirror source**: https://github.com/x1xhlol/system-prompts-and-models-of-ai-tools/tree/main/Google/Antigravity (2026-07-10)

## Files
- `Fast Prompt.txt` — prompt for a lower-latency/"fast" response mode.
- `planning-mode.txt` — prompt for a planning-first mode.

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
