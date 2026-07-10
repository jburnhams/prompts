# Skills / plugins

A third category, structurally different from the other two:

- `../<tool>/` folders hold **full system prompts** for standalone coding
  agents — the entire persona/rules/tool-definitions that run the whole
  agent.
- `../leaked/` holds leaked versions of the same thing for closed products.
- **This folder** holds **Claude Code "skills"/plugins**: small,
  self-contained prompt files (usually Markdown with YAML frontmatter)
  that define a single slash command or subagent — e.g. "review my
  uncommitted changes" — rather than an entire agent. They're invoked
  within an existing agent (Claude Code) rather than being the agent
  itself.

These are officially published by their authors (not leaked), but "open
source" doesn't uniformly apply — check each source's license note, since
it ranges from MIT to Anthropic's source-available commercial terms.

## Sources so far

| Folder | Publisher | License |
|---|---|---|
| [`agent37/`](./agent37) | [agent37-platform](https://github.com/agent37-platform/agent37-skills-collection) | MIT |
| [`anthropic/`](./anthropic) | [Anthropic](https://github.com/anthropics/claude-code) | Source-available (not OSI open source) |
