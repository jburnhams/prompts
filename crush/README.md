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
