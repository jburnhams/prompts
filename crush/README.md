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
