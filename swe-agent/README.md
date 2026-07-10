# SWE-agent

- **Type**: Coding agent (autonomous GitHub issue resolver, Princeton NLP)
- **License**: MIT
- **Source**: https://github.com/SWE-agent/SWE-agent
- **Retrieved from**: `main` branch, `config/default.yaml` (2026-07-10)

SWE-agent defines its prompts inline in a YAML config rather than in Python
source. `default.yaml` includes the system template, instance (task) template,
and the full custom tool/command definitions the agent can call (bash-like
filesystem and search commands, file editor, submit, etc).

## Files

- `default.yaml` — full agent config: system prompt, instance prompt,
  next-step templates, and tool/command definitions.
