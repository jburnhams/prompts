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

## Tool surface

- **Shell**: unspecified/generic — the prompt talks about "commands"
  generically, combining "multiple bash commands into one" and using
  `sed`/`grep` for bulk edits, without naming a specific shell.
- **Search**: plain `find`/`grep`/`git` commands with "appropriate
  filters" — no ripgrep preference stated (unlike Codex; see
  [`agent-tool-surfaces.md`](../agent-tool-surfaces.md)).
- **Code execution**: none beyond the shell itself — no dedicated
  Python/Node execution tool described.
- **Browser/web**: not in this prompt directly; `<EXTERNAL_SERVICES>`
  says to prefer platform APIs (GitHub/GitLab/Bitbucket) "unless the user
  asks otherwise or your task requires browsing," implying browser
  capability exists in the wider product but isn't detailed here.
- **Multimodal**: not addressed.
- **Sandbox/isolation**: not specified in this prompt — OpenHands'
  runtime sandboxing is configured outside the prompt text.
- **Distinctive**: the only source in this collection with an explicit
  process-management safety rule ("Do NOT use general keywords with
  commands like `pkill -f server`... find the exact PID first").
