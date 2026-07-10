# OpenHands (formerly OpenDevin)

- **Type**: Coding agent (autonomous software engineer)
- **License**: MIT
- **Source**: https://github.com/All-Hands-AI/OpenHands
- **Retrieved from tag**: [`0.60.0`](https://github.com/All-Hands-AI/OpenHands/tree/0.60.0/openhands/agenthub/codeact_agent/prompts) (2026-07-10)

`main` has since moved/renamed these prompt files (the project is mid
restructure), so a recent stable tag is used instead. Prompts are Jinja2
templates for the `CodeActAgent`.

## Files

- `system_prompt.j2` — the main system prompt (role, environment, tool-use
  guidelines, coding conventions).
- `additional_info.j2` — injects repo/runtime context (working dir, repo
  instructions, etc.) into the conversation.
- `in_context_learning_example.j2` — a worked few-shot example demonstrating
  the expected agent behavior/tool-call format.

Note: `user_prompt.j2` also exists in this directory but was empty at the
retrieved tag, so it isn't included.
