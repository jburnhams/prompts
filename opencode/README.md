# OpenCode

- **Type**: Coding agent (terminal-based, multi-provider)
- **License**: MIT
- **Source**: https://github.com/anomalyco/opencode (formerly `sst/opencode`;
  the GitHub org was renamed)
- **Retrieved from**: `dev` branch (the repo's default branch),
  `packages/opencode/src/session/` (2026-07-10)

OpenCode selects a different base system prompt per model family/provider
(see `system.ts`'s `provider()` function), then layers on repo-discovered
instructions (`AGENTS.md`/`CLAUDE.md` via `instruction.ts`), skills, MCP
context, and mode-specific reminders (e.g. plan mode).

## Files

- `system.ts` — provider → prompt-variant selection logic, plus environment
  block assembly (model, cwd, platform, date).
- `instruction.ts` — walks the filesystem for `AGENTS.md`/`CLAUDE.md` files
  and folds their contents into the prompt.
- `prompt/default.txt` — fallback system prompt (base "build" agent
  persona/rules/tone, used when no provider-specific variant matches).
- `prompt/anthropic.txt` — variant for Claude models.
- `prompt/gpt.txt` / `prompt/codex.txt` / `prompt/beast.txt` — variants for
  GPT-4/GPT-5/o1/o3/Codex models (`beast.txt` is used for the reasoning
  "o-series" models).
- `prompt/gemini.txt` — variant for Gemini models.
- `prompt/kimi.txt`, `prompt/trinity.txt`, `prompt/meta.txt`,
  `prompt/copilot-gpt-5.txt` — variants for Kimi, Trinity, and other
  provider/model families.
- `prompt/plan.txt`, `prompt/plan-mode.txt`, `prompt/plan-reminder-anthropic.txt`
  — prompts/reminders for the read-only "plan" agent mode.
- `prompt/build-switch.txt` — short reminder injected when switching from
  plan mode back into the "build" (editing) agent.

Not included: `prompt.ts` (~1600 lines) — the session/agentic-loop
orchestrator that wires prompts, tools, and streaming together. It's mostly
implementation code with only a small amount of embedded prompt text
(`MAX_STEPS_PROMPT` etc.), so it's out of scope for this collection.

## Tool surface

- **Shell**: `Bash` — non-trivial commands must be explained to the user
  before running, "especially important when... making changes to the
  user's system."
- **Search**: separate `grep` and `glob` tools (named explicitly in the
  worked example), plus a delegated `Task` tool "to reduce context usage"
  for open-ended search.
- **Code execution**: none beyond `Bash` — no dedicated Python/Node
  execution tool.
- **Browser/web**: `WebFetch`, but scoped narrowly in this prompt to
  self-documentation ("first use the WebFetch tool... from opencode
  docs") — not framed as a general research tool here.
- **Multimodal**: not addressed in `default.txt`.
- **Sandbox/isolation**: not in the prompt text; see
  [`../github-pr-bots/opencode-review/`](../github-pr-bots/opencode-review)
  for the GitHub Action's execution context.
- **Extensibility**: MCP support (`MCP.Service` in `system.ts`) and a
  skills system (`Skill.Service`), both conditionally injected only when
  something is actually configured/available — same "don't pad the prompt
  with unused capability text" instinct as Pi's dynamic tool listing.

## Sub-agents

**Correction to an earlier version of this doc**: this folder only
stores the prompt *text* files, and a first pass concluded the `Task`
tool's schema/protocol simply wasn't captured here. It's more than
uncaptured — reading the actual implementation directly
(`packages/opencode/src/tool/task.ts` and `packages/opencode/src/agent/`,
live on `openai/opencode`'s `dev` branch, not stored in this folder)
shows the Task tool is genuinely **more sophisticated than Claude
Code's stateless one-shot design**, closer in spirit to Codex CLI's
addressable `spawn_agent` family (see `codex/README.md`) but built on a
different primitive: a generic `BackgroundJob` state machine, not a
purpose-built agent-session protocol.

- **Tool ID is literally `"task"`.** Parameters: `description` (3-5
  word label), `prompt` (the task), `subagent_type`, an optional
  `task_id` ("resume a previous task... the task will continue the same
  subagent session as before instead of creating a fresh one"), and —
  gated behind an experimental flag — `background` ("Run the agent in
  the background. You will be notified when it completes. DO NOT sleep,
  poll, or proactively check on its progress").
- **Genuinely stateful, not just resumable-after-completion**: calling
  `task` again with an already-running `task_id` doesn't error or
  block — it gets **queued onto the still-live job** (`background.extend()`)
  and returns immediately. That's a real "send a follow-up to a running
  sub-agent" capability, the same category of thing as Codex's
  `send_input`, not documented anywhere a prompt-text-only read could
  have found it.
- **A race between completion and background-promotion**: by default,
  a `task` call races the job finishing against the job being
  *promoted* to background (`Effect.raceFirst`) — if the user interrupts
  a foreground task rather than killing it, it can detach and keep
  running, later injecting its result back into the parent session as a
  synthetic follow-up message rather than a tool result. Interrupting
  (not promoting) genuinely cancels the child.
- **Named agent registry with real tool-scope and prompt differences**
  (`agent/agent.ts`): built-ins are `build`/`plan` (primary agents, not
  delegates), `general` (subagent, no custom prompt — reuses the
  orchestrator's own base prompt, "execute multiple units of work in
  parallel"), and `explore` (subagent, its **own dedicated system
  prompt**, read-only permission set — grep/glob/list/bash/webfetch/
  websearch/read allowed, everything else denied). A sub-agent's
  `prompt` field, when set, **entirely replaces** rather than appends to
  the model-family base prompt (`session/llm/request.ts`); `general`
  (no custom prompt) falls through to the same base prompt the
  orchestrator uses.
- **Custom sub-agents via Markdown files** — `{agent,agents}/**/*.md`
  with YAML frontmatter, functionally the same convention as Claude
  Code's `.claude/agents/*.md`, confirmed intentional: a code comment in
  `config/markdown.ts` explicitly notes "other coding agents like claude
  code allow invalid yaml in their frontmatter."
- **Recursion denied by default, not silently allowed**:
  `subagent-permissions.ts`'s `deriveSubagentSessionPermission()` denies
  a spawned sub-agent's own `task` tool (and `todowrite`) by default
  unless its specific agent type's ruleset explicitly grants it — the
  `plan` agent, for instance, is allowed to spawn `general` but nothing
  else. A different, more granular position than either Goose's
  blanket "cannot spawn additional subagents" ban or Amp's apparently
  unrestricted recursion.
- **No hard concurrency/file-lock mechanism** — only a prompt-level
  instruction ("avoid working with the same files or topics") backing
  parallel Task-tool calls; safety comes from the permission-ask
  ruleset on individual file edits, not a same-file mutex across
  sub-agents.
- **The richer async/background protocol is explicitly experimental**
  (`OPENCODE_EXPERIMENTAL_BACKGROUND_SUBAGENTS`) — the tool's schema
  itself changes shape depending on the flag; only the resume-and-extend
  path is unconditionally reachable.
- **The Claude-lineage-only prompt-instruction finding still holds** as
  a separate, correct observation: the *persona-prompt instructions* to
  use the Task tool ("prefer to use the Task tool in order to reduce
  context usage," etc.) appear only in `default.txt`, `anthropic.txt`,
  `trinity.txt`, and `meta.txt` — absent from `gpt.txt`, `codex.txt`,
  `beast.txt`, `gemini.txt`, `kimi.txt`, `copilot-gpt-5.txt`. The tool
  itself is available regardless of model family; only the prompt-level
  encouragement to reach for it varies.
