# v0

- **Type**: AI app-building agent (React/Next.js focused) · **Vendor**: Vercel
- **Status**: closed source (leaked)
- **Mirror source**: https://github.com/x1xhlol/system-prompts-and-models-of-ai-tools/tree/main/v0%20Prompts%20and%20Tools (2026-07-10)

## Files
- `Prompt.txt` — system prompt.
- `Tools.json` — tool/function definitions.

## Sub-agents

A single search delegate, `SearchRepo` — "Launches a new agent that
searches and explores the codebase using multiple search strategies
(grep, file listing, content reading)," returning "relevant files and
contextual information" rather than raw matches. Functionally the same
shape as Crush's `agent_tool`/OpenCode's `Task`/Claude Code's
`general-purpose` agent type: a read-only, multi-strategy search
delegate meant to save the orchestrator's own context. The tool
description's one line of delegation guidance — "Delegate to subagents
when the task clearly benefits from a separate agent with a new context
window" — is one of the more explicit statements in this collection of
*why* sub-agents exist at all (context-window isolation), matching
Gemini CLI's "your own context window is your most precious resource"
framing but far more compressed. No system prompt for `SearchRepo`
itself, no stated concurrency rules, and no second sub-agent type (v0's
`SearchWeb` is a plain tool, not a delegate — see its description in
`Tools.json`, which reads like a conventional search-API wrapper rather
than "launches a new agent").
