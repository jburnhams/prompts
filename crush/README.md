# Crush

- **Type**: Coding agent (Charm's terminal AI coding agent)
- **License**: FSL-1.1-MIT (source-available, converts to MIT after 2 years
  per version)
- **Source**: https://github.com/charmbracelet/crush
- **Retrieved from**: `main` branch,
  `internal/agent/templates/` (2026-07-10)

Crush's prompts are Go templates (`.tpl`) plus a few plain Markdown tool
descriptions, rendered at runtime with session-specific data. This is the
complete contents of the `templates/` directory. Crush also reads
`AGENTS.md`/`CRUSH.md`/`CLAUDE.md`/`GEMINI.md` files from the working
directory for project-specific instructions, layered on top of these.

## Files

- `coder.md.tpl` — the main system prompt: persona, critical rules
  (autonomy, conciseness, no unsolicited comments, git/commit constraints,
  security-only-defensive stance, skill loading), and tool-use guidance.
- `initialize.md.tpl` — prompt used the first time Crush runs in a new
  project (e.g. to bootstrap a `CRUSH.md`).
- `task.md.tpl` — prompt for a delegated sub-task/sub-agent run.
- `summary.md` — prompt for summarizing conversation history.
- `title.md` — prompt for auto-generating a session title.
- `agentic_fetch_prompt.md.tpl` — prompt for the web-fetch sub-agent (fetch
  + summarize/answer questions about a URL).
- `agent_tool.md` — tool description for the general-purpose search
  sub-agent ("Task"-style tool).
- `agentic_fetch.md` — tool description for the agentic-fetch tool itself.

## Tool surface

- **Shell**: `bash` — the `description` parameter is **mandatory** on
  every bash call ("CRITICAL: The `description` parameter is REQUIRED
  for all bash tool calls. Always provide it"), a stricter requirement
  than most sources' softer "explain non-trivial commands" framing.
- **Search**: `glob`/`grep`/`ls`/`view` are explicitly the tool set given
  to the delegated search sub-agent (see below) — the main agent
  presumably has direct access to the same tools plus editing ones, per
  `agent_tool.md`'s framing.
- **Editing**: `edit`/`multiedit` — with an explicit denial of tools that
  don't exist in Crush ("Never attempt 'apply_patch' or 'apply_diff' -
  they don't exist"), i.e. real evidence a model trained on another
  tool's conventions (Codex's `apply_patch`, or a generic "apply_diff"
  some other agent might expose) will hallucinate it here if not
  explicitly told not to.
- **Web fetch — two tiers, not one**: a plain `fetch` tool ("use fetch for
  raw content or API responses") plus a separate, more expensive
  `agentic_fetch` **sub-agent** that can "extract, summarize, and answer
  questions" about a URL rather than just returning raw bytes — a
  cost/capability tradeoff made explicit in the tool description itself,
  not left for the model to guess.
- **Code execution**: none beyond `bash`.
- **Multimodal**: not addressed in what's collected here.
- **Sandbox/isolation**: not specified — runs directly on the user's
  machine.
- **Extensibility**: skills (loaded via `view` on a matching skill's
  location, mandatory before acting per the critical rules), plus
  `agent_tool.md`'s general-purpose search delegate (Task-style,
  read-only-scoped).

## Sub-agents

Two sub-agents, both with their **complete system prompts captured as
separate template files** (`task.md.tpl`, `agentic_fetch_prompt.md.tpl`)
— alongside Copilot Chat, one of only two sources in this collection
with the sub-agent's own prompt text available, not just the
orchestrator-side tool description.

- **Search sub-agent** (`agent_tool.md` describes it; `task.md.tpl` is
  its system prompt) — scoped to exactly `glob, grep, ls, view` (no
  editing, no bash). Its prompt is strikingly terse-by-design: "you
  should be concise, direct, and to the point, since your responses will
  be displayed on a command line interface... One word answers are
  best... You MUST avoid text before/after your response, such as 'The
  answer is <answer>.'" — a much harder terseness constraint than the
  main `coder.md.tpl` persona uses for the orchestrator itself. Also
  mandates absolute (not relative) file paths in its output, presumably
  because the result gets folded into a different working context than
  the one the sub-agent ran in.
- **`agentic_fetch` web sub-agent** (`agentic_fetch_prompt.md.tpl`) — a
  persona swap to "a web content analysis agent for Crush," with its own
  tool subset (`web_search`, `web_fetch`, plus `grep`/`view` for large
  fetched-content files) and a fully specified output contract: answer
  first, then a mandatory `## Sources` section listing every URL that
  contributed — plus a worked example decomposing one broad question
  ("Rust vs Go for web services") into four narrower searches. This is
  the same fetch-vs-agentic_fetch tiering noted in "Tool surface" above,
  but here grounded in the sub-agent's actual instructions rather than
  just the tool description's one-line cost/capability tradeoff note.
- **Protocol**: both sub-agent prompts inject the same `<env>` block
  (working directory, platform, date — `task.md.tpl` adds git-repo
  status) that the main `coder.md.tpl` prompt gets, so sub-agents share
  the orchestrator's environment context even though they run under a
  fully different persona and reduced tool set. Neither file describes
  concurrency rules or how the orchestrator should handle the returned
  text — unlike Gemini CLI's explicit file-conflict concurrency mandate
  or Claude Code's "launch multiple agents concurrently" instruction,
  parallel-sub-agent guidance isn't captured in what's collected here.

## Compaction

Already fully captured in this folder's `summary.md`, not previously
written up as its own section. See
[`agent-context-compaction.md`](../agent-context-compaction.md) for the
cross-source comparison this feeds into.

- **The bluntest "you will lose everything" framing in this
  collection**: "This summary will be the ONLY context available when
  the conversation resumes. Assume all previous messages will be lost.
  Be thorough." No transcript-lookup recovery pointer is offered the
  way Claude Code's and Copilot Chat's compaction prompts provide — the
  summary genuinely is treated as the sole surviving record, not a
  lossy pointer into a still-readable full history.
- **A 5-section structured template**, the shortest of the structured
  templates surveyed but still opinionated about content: Current State
  (exact user request, progress, current work, specific next steps —
  explicitly "not vague"), Files & Changes (modified/read/not-yet-touched,
  with file paths and line numbers), Technical Context (architecture
  decisions and *why*, patterns followed, commands that worked vs.
  failed and why), Strategy & Approach (why this approach over
  alternatives, gotchas, assumptions, blockers), Exact Next Steps.
- **The "Exact Next Steps" section is explicitly example-driven about
  what NOT to do**: "Don't write 'implement authentication' — write:
  1. Add JWT middleware to src/middleware/auth.js:15..." — a concrete
  before/after example baked into the prompt itself, not just an
  abstract instruction to be specific.
- **No length limit stated** — "err on the side of too much detail
  rather than too little. Critical context is worth the tokens" — the
  opposite instinct from sources that cap summary output tokens
  (Codex's minimal prompt, OpenCode's 4,096-token cap, Claude Code's
  20,000-token summary budget).
- **No trigger/threshold information captured** — same caveat as Goose:
  this is the prompt text alone, not the surrounding Go orchestration
  code that would show what actually decides when to compact.

## Turn output: session titles

Already fully captured in this folder's `title.md`, not previously
written up as its own section. See
[`agent-turn-output.md`](../agent-turn-output.md) for the cross-source
comparison this feeds into.

- **Generated from the first message only**: "You will generate a
  short title based on the first message a user begins a conversation
  with" — a one-shot decision at session start, not something
  reconsidered as the conversation evolves.
- **Concrete, code-adjacent format rules stated directly in the
  prompt**: same language as the user's message, ≤50 characters, one
  line, no quotes or colons, and — notably — "the entire text you
  return will be used as the title," meaning there's no separate
  parsing/extraction step expected on the code side; the model's raw
  output is the title verbatim.
- No trigger/model information captured beyond the prompt text itself
  (not confirmed whether this runs on a separate cheap model or the
  main session model).
