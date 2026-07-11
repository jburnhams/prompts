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

**Correction**: even at the `0.60.0` tag used here, the same
`codeact_agent/prompts/` directory holds seven *more* Jinja2 files never
fetched into this folder — `system_prompt_interactive.j2`,
`system_prompt_long_horizon.j2`, `system_prompt_tech_philosophy.j2`,
`in_context_learning_example_suffix.j2`, `microagent_info.j2`,
`security_risk_assessment.j2`, and the (non-empty, contrary to the note
above being about a different file) `user_prompt.j2`. Naming suggests
alternate top-level operating modes (interactive vs. long-horizon vs. a
"tech philosophy" variant) plus a security-risk-assessment fragment and
a microagent-info fragment — none read in full. Flagged here rather than
silently left as a gap.

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

## Sub-agents

Not previously covered in this collection's sub-agent survey — a
prompt-text-only pass on the files stored here would have missed
delegation entirely, since none of the three captured `.j2` files
mention it. OpenHands has had a real delegation mechanism at every
stage of its history, both at the `0.60.0` tag used for the prompt
files above and — after a major restructure — in the successor repo
that now holds the actual agent implementation,
[`OpenHands/software-agent-sdk`](https://github.com/OpenHands/software-agent-sdk).
Everything below is sourced from reading those two repos directly
(MIT-licensed, ordinary open source), not from files stored in this
folder.

**At `0.60.0`** (`openhands/events/action/agent.py`,
`openhands/controller/agent_controller.py`): `AgentDelegateAction`
(fields: `agent` — a target agent *class name*, `inputs: dict`,
`thought`) hands control to a freshly-instantiated agent of that type,
wrapped in its own nested `AgentController(is_delegate=True,
delegate_level = parent.delegate_level + 1)`. Cooperative-blocking, not
threaded: the parent controller's `step()` is a no-op while a delegate
is active, so only one delegate runs at a time. The parent never sees
the delegate's individual steps — only a single `AgentDelegateObservation
(outputs: dict)` once the delegate finishes. No distinct system prompt
for delegate-mode: a delegate just runs its own agent type's normal
prompt (confirmed by reading `browsing_agent.py` directly — no
`is_delegate`-conditional prompt logic found). Agent types available at
this tag: `codeact_agent` (primary, the one prompted here),
`browsing_agent`, `visualbrowsing_agent` (screenshot+accessibility-tree
browsing), `loc_agent` (repo-as-graph code localization, exposes
`search_code_snippets`/`get_entity_contents`/`explore_tree_structure`),
`readonly_agent` (grep/glob/view/think/finish only, explicitly rejects
MCP tools), and `dummy_agent` (scripted, no LLM calls, for framework
tests). **A docs/code mismatch worth flagging as its own finding**:
`agenthub/README.md`'s example prose describes a "Delegator Agent" that
forwards to micro-agents like "RepoStudyAgent"/"VerifierAgent" — neither
exists in the actual `agenthub/` directory at this tag. Legacy/aspirational
documentation, not a real feature — exactly the kind of trap a
"read the README, not the code" pass would fall into.

**In the new SDK**, delegation was redesigned rather than dropped, and
became **three coexisting mechanisms**:

- **`openhands.tools.delegate`** — `spawn` (start a named, addressable
  sub-agent, kept alive in `self._sub_agents[agent_id]`) + `delegate`
  (send a new message to an already-spawned agent by id — repeatable,
  stateful, the same shape as Codex's `send_input`). Concurrency is
  **real and threaded**: `DelegateExecutor._delegate_tasks` runs
  multiple named sub-agents' `.run()` calls on separate Python threads
  and joins them, capped at `max_children: int = 5`.
- **`openhands.tools.task`** (`TaskToolSet`) — wired into the default
  tool set (`get_default_tools(enable_sub_agents=True)`). One task per
  call via `subagent_type` (default `"general-purpose"`), with a
  `resume: <task_id>` parameter to re-attach to a specific prior
  sub-agent conversation. Its tool description reads as closely
  modeled on Claude Code's own Task tool phrasing ("Launch a subagent
  to handle complex, multi-step tasks autonomously... each delegation
  has overhead — use them when the task genuinely benefits from a
  separate agent... A single grep, find, or cat command would answer
  your question — just run it yourself").
- **`openhands.tools.workflow`** (`WorkflowToolSet`) — the standout
  finding here: a small orchestration DSL exposed to the model as a
  Python sandbox — `wf.run_agent(...)`, `wf.map_agents(items, prompt,
  max_concurrency=...)`, `wf.reduce_agent(items, prompt, ...)`,
  `wf.pipeline(items, *stages)` (staged and non-barriered — a fast item
  can reach a later stage while a slow item is still on an earlier
  one), `wf.flatten(values)`. `max_concurrency` defaults to 8, capped
  1–64. Guardrails are deliberate: only documented `wf` methods are
  callable, and `ExceptionGroup` is intentionally *not* exposed by name
  in the sandbox, forcing `map_agents` failures through plain
  `except Exception` or agent-returned error sentinels rather than
  partial `except*` handling. This is a materially different design
  point from every other source's single spawn/delegate primitive in
  this collection — a constrained map-reduce/DAG engine for sub-agents,
  not just a way to fire one off.
- **Sub-agent system prompts are a documented suffix, not a swap**: a
  spawned agent's `AgentDefinition.system_prompt` (the Markdown body of
  its definition file) is applied via `AgentContext(system_message_suffix=...)`
  — appended to the base system message, not replacing it. Four
  built-in agent-definition files exist (`openhands-tools/openhands/tools/preset/subagents/`):
  `general-purpose` (default — terminal + file_editor + task_tracker),
  `bash-runner` (instructed to never dump raw command output, report
  only pass/fail + failure reasons), `code-explorer` (forbids any
  file-modifying command, whitelists specific read-only shell commands),
  `web-researcher` (a three-tool Tavily-search/fetch/browser workflow
  with "never spend more than 2 actions on a blocked site"). Custom
  agent types are first-class beyond these four, discovered from
  `.agents/agents/*.md` (project, then user, then SDK-builtin
  precedence) — the same Markdown+YAML-frontmatter convention OpenCode
  independently converges on (see `../opencode/README.md`).
- **Recursion**: none of the four built-in agent definitions include
  the `task` or `delegate` tool in their own tool list, so built-in
  sub-agents can't recurse by default (inferred from their frontmatter,
  not an explicit code-level prohibition) — recursion becomes reachable
  only if a *custom* agent definition deliberately grants itself one of
  those tools.
- **A separate, unrelated "many parallel sessions" layer**:
  `openhands/app_server/` (still in the original `All-Hands-AI/OpenHands`
  repo) is a FastAPI server hosting many independent sandboxed
  conversations for the cloud product — the "run OpenHands on 50
  different issues at once" kind of parallelism, structurally unrelated
  to the in-conversation `delegate`/`task`/`workflow` mechanisms above.
