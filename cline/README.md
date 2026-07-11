# Cline

- **Type**: Coding agent (VS Code / JetBrains / CLI extension)
- **License**: Apache-2.0
- **Source**: https://github.com/cline/cline
- **Retrieved from tag**: [`v3.20.4`](https://github.com/cline/cline/tree/v3.20.4/src/core/prompts) (2026-07-10)

Cline later restructured its repo into a monorepo (`apps/`, `sdk/`) where the
system prompt is composed differently. `v3.20.4` is the last tag with the
classic, single-file prompt layout, so it's used here for a clean read.

## Files

- `system.ts` — entry point; picks a prompt variant based on model family and
  assembles it with live context (cwd, shell, MCP servers, browser support).
- `model_prompts/claude4.ts` — the full system prompt used for Claude 4 models
  (tool definitions, rules, capabilities, objective).
- `model_prompts/claude4-experimental.ts` — an experimental variant of the
  above.
- `responses.ts` — templates for tool-result / error messages fed back to the
  model mid-conversation (not the system prompt itself, but part of the
  overall prompting strategy).

## Tool surface

- **Shell**: `execute_command` — generic, "tailor your command to the
  user's system," one command per tool call (this version predates native
  parallel tool-calling; see `coding-agent-approaches.md` §4).
- **Search**: `search_files` (regex-based), `list_files`, and
  `list_code_definition_names` — the last one lists source-definition
  symbols (classes/functions) rather than raw text matches, a lightweight
  AST-adjacent capability distinct from plain grep.
- **Code execution**: none beyond the shell.
- **Browser/web**: `browser_action` — a full **vision-based, Puppeteer
  browser control tool**: launch → click/type/scroll by pixel coordinate
  read off a returned screenshot → close. Explicitly exclusive ("only the
  `browser_action` tool can be used" while a browser session is open, no
  interleaving with other tools) and conditionally included via the
  `supportsBrowserUse` parameter passed into `SYSTEM_PROMPT()` — only
  shown to the model if the underlying provider/model actually supports
  image input.
- **Multimodal**: implicit in `browser_action` — every browser action
  except `close` returns a screenshot the model must visually interpret
  to pick click coordinates.
- **Sandbox/isolation**: none described — runs directly on the user's
  machine/VS Code environment.
- **Extensibility**: `use_mcp_tool`/`access_mcp_resource`/
  `load_mcp_documentation` for MCP servers, plus `new_task` for spawning a
  follow-on task and `plan_mode_respond` for its plan/act mode split.

## Turn output: session titles

Sourced from the live upstream repo's current monorepo layout (not the
`v3.20.4` tag stored in this folder) — see
[`agent-turn-output.md`](../agent-turn-output.md) for the cross-source
comparison this feeds into.

**Confirmed absence, not just unchecked**: Cline generates no AI
session title at all. `HistoryItem` (both the VS Code extension and the
newer CLI SDK) has only a raw `task`/`prompt` string field — no
dedicated title field exists in the data model. The CLI's history
rendering falls back to `metadata?.title || prompt || "Untitled"`,
truncated to 40 characters — and `metadata.title` is populated only by
an explicit user command (`cline history update --title`), never by an
LLM call. Fork-session titling is pure string manipulation (reuse the
source title or first message text, append " (fork)") — confirmed by
reading the function body directly, no model call inside it. The
cheapest possible answer to "how do you title a session": don't
generate one, format the raw first message instead.

## Sub-agents

**Cline has no sub-agent delegation tool in this snapshot** — `new_task`
is a different, easily-confused mechanism worth calling out explicitly:
it doesn't launch a second, independent agent that reports back. It
generates "a detailed summary of the conversation so far" (explicit
five-part structure: current work, key technical concepts, relevant
files/code, problem solving, pending tasks/next steps) and hands that
summary to the **user** as a preview, who can then choose to start a
*fresh conversation* preloaded with it, or keep chatting in the current
one. It's a context-compaction / session-handoff tool aimed at working
around context-window limits across a single continuous task, not a
parallel-delegation or divide-and-conquer mechanism — the new "task" runs
in place of the current one, not alongside it, and there's no
orchestrator/sub-agent relationship or result-passing-back protocol at
all. Contrast this directly with Claude Code's `Task` tool (see
`leaked/claude-code/README.md`), which spawns a genuinely separate agent
that returns a report *to* the still-running orchestrator.

## Compaction

See [`agent-context-compaction.md`](../agent-context-compaction.md) for
the cross-source comparison this feeds into. All evidence lives in
`responses.ts:7-16` — nothing relevant elsewhere in the folder. Cline
turns out to layer **three separate, structurally distinct
context-management mechanisms**, none of which call each other in what's
captured here, on top of the session-handoff `new_task` tool documented
above:

- **Silent, non-summarized truncation — no LLM call at all**:
  `contextTruncationNotice()` — "Some previous conversation history with
  the user has been removed to maintain optimal context window length.
  The initial user task and the most recent exchanges have been
  retained for continuity, while intermediate conversation history has
  been removed." Keep-first-and-last, drop-the-middle, with the dropped
  middle simply gone — no summary is generated to stand in for it. This
  is more primitive than every other compaction mechanism surveyed in
  this collection, which all either run real LLM summarization or a
  heuristic trim that still preserves some semantic content (OpenCode's
  `prune`, Claude Code's `microcompact`); Cline's plain deletion has no
  recovery story at all, not even a lossy one.
- **A separate, real LLM-summarization path — gated on explicit user
  approval, not silent**: `condense()` — "The user has accepted the
  condensed conversation summary you generated... It's crucial that you
  respond by ONLY asking the user what you should work on next. You
  should NOT take any initiative or make any assumptions about
  continuing with work... you should NOT reference information outside
  of what's contained in the summary for this response." This confirms
  a distinct, model-generated summary the user must accept before it
  takes effect — a third trigger shape not matching this doc's existing
  "proactive silent" vs. "reactive-on-error" vs. "manual command"
  categories: **model-proposes, user-approves**. The prompt that
  actually asks the model to generate the summary in the first place
  isn't in any captured file — only this post-acceptance acknowledgment
  is — so the summarization prompt's shape (structured vs. free text)
  is unconfirmed.
- **A distinctive post-compaction behavioral lockdown**: unlike every
  other surveyed source's post-compaction instruction (which is about
  *how to resume work*), Cline's explicitly tells the model *not* to
  resume work — no suggesting file changes, no reading files, just ask
  what to do next. No other source in this collection's compaction
  survey does this.
- **A narrower, targeted dedup, scoped only to file reads**:
  `duplicateFileReadNotice()` — "This file read has been removed to
  save space in the context window. Refer to the latest file read for
  the most up to date version of this file." Conceptually a narrow
  cousin of Claude Code's `microcompact` (heuristic placeholder
  replacement of stale tool output) but limited to file-read results
  specifically, not general tool output.
- **Distinct from `new_task`** (above): `new_task` ends the current
  task and starts a genuinely new, separate conversation; these three
  mechanisms all operate *within* the same ongoing task, trimming its
  history in place. Cline has (at least) four separate answers to "the
  context is getting too full" — silent deletion, approved
  summarization, targeted dedup, and full session handoff — rather than
  one unified compaction pipeline.

## Self-verification and testing

See [`agent-self-verification.md`](../agent-self-verification.md) for
the cross-source comparison this feeds into. One of the thinner §7
(prompted-only) instances surveyed — no TESTING/VALIDATION section, no
bounded-retry pattern, no "hidden tests" language anywhere across any
of the three system-prompt variants (`system.ts`, `model_prompts/
claude4.ts`, `model_prompts/claude4-experimental.ts`).

- **`attempt_completion`'s gate is procedural, not a correctness
  check**: its description says the tool "CANNOT be used until you've
  confirmed from the user that any previous tool uses were successful,"
  and instructs the model to ask itself in `<thinking>` tags whether
  that's true before calling it — but the "success" being confirmed is
  whether the last tool call went through (did the file write actually
  happen), not whether the resulting code is correct. Entirely
  prompted; no structural check in `system.ts`/`responses.ts` was found
  blocking the call the way Roo Code's `AttemptCompletionTool.ts` does.
- **Verification is otherwise folded into the browser tool, and only
  optionally**: "This tool may be useful at key stages of web
  development tasks... to verify the result of your work. You can
  analyze the provided screenshots to ensure correct rendering..." —
  conditional on browser support (`supportsBrowserUse`) and phrased as
  something the model might choose to do ("if you want to test your
  work"), not a mandate.
- **A passive, automatic linter-surfacing channel exists but isn't a
  gate**: `responses.ts`'s post-edit tool-result templates
  (`fileEditWithUserChanges`/`fileEditWithoutUserChanges`) both append
  a `newProblemsMessage` — the system prompt tells the model the tool
  result "may include... Linter errors that may have arisen due to the
  changes you made, which you'll need to address." Diagnostics are
  surfaced automatically after every edit, but nothing forces the model
  to act on them before declaring the task done.
