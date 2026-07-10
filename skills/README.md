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

Several were surfaced via a
[Reddit thread](https://www.reddit.com/r/ClaudeAI/comments/1q5a90l/so_i_stumbled_across_this_prompt_hack_a_couple/)
about an "adversarial code review" prompting technique, which linked to a
handful of skill collections built around the same idea. Not included from
that thread: [BMAD-METHOD](https://github.com/bmad-code-org/BMAD-METHOD) is
included (see `bmad-code-review/`), but its wider framework (34+ workflows
beyond code review) is out of scope here; `bl-agent-debater` (a general
multi-agent debate CLI, not code-review-specific) and the referenced blog
post (Steve Yegge's "Rule of Five") aren't prompt sources and weren't added.

Each source's README documents not just the prompt text but the
**scaffolding** around it — how it builds context (diff format, what else
gets pulled in besides the diff), what tools it has, and how/where output
gets delivered — since that materially changes what these actually do in
practice, and varies a lot between sources.

## Sources so far

| Folder | Publisher | License | Notes |
|---|---|---|---|
| [`agent37/`](./agent37) | [agent37-platform](https://github.com/agent37-platform/agent37-skills-collection) | MIT | Pre-commit review of local changes |
| [`anthropic/`](./anthropic) | [Anthropic](https://github.com/anthropics/claude-code) | Source-available (not OSI open source) | PR review, PR review toolkit, background security hooks |
| [`turingmind/`](./turingmind) | [TuringMind AI](https://github.com/turingmindai/turingmind-code-review) | MIT | Pre-commit review, quick + deep modes |
| [`bmad-code-review/`](./bmad-code-review) | [BMad Code, LLC](https://github.com/bmad-code-org/BMAD-METHOD) | MIT | Part of a larger agile-dev framework; most elaborate scaffolding here (4-step state machine, pluggable review layers, spec cross-referencing) |
| [`claude-code-cookbook/`](./claude-code-cookbook) | [wasabeef](https://github.com/wasabeef/claude-code-cookbook) | Apache-2.0 | Looser, example-driven rather than a fixed pipeline |
