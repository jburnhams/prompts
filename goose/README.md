# Goose

- **Type**: Coding agent (Block's general-purpose, extensible AI agent — CLI
  + desktop)
- **License**: Apache-2.0
- **Source**: https://github.com/block/goose
- **Retrieved from**: `main` branch,
  `crates/goose/src/prompts/` (2026-07-10)

Goose's prompts are Jinja2-style templates (`{% if %}` / `{{ var }}`)
rendered by its Rust core, covering the main system prompt plus a set of
task-specific prompts used for sub-features (planning, recipes, session
naming, compaction, etc). This is the complete contents of the `prompts/`
directory.

## Files

- `system.md` — the main system prompt (persona, extensions/tools framing,
  operating rules).
- `tiny_model_system.md` — a shorter system prompt variant for small/local
  models.
- `subagent_system.md` — system prompt used when Goose spawns a sub-agent to
  handle a delegated task.
- `plan.md` — prompt for "plan mode" (produce a plan before executing).
- `recipe.md` — prompt for generating/following a Goose "recipe" (a
  reusable, shareable YAML task definition — the feature block.com credits
  with scaling Goose internally).
- `compaction.md` — prompt used to summarize/compact long conversation
  history.
- `session_name.md` — prompt for auto-generating a short session title.
- `apps_create.md` / `apps_iterate.md` — prompts for Goose's app-building
  mode (scaffolding vs. iterating on an existing app).

Not included: `permission_judge.md`, which was empty (0 bytes) at the
retrieved commit.

## Tool surface

- **Shell**: not fixed — `{{shell}}` is a template variable filled in at
  runtime (so it adapts to whatever the OS/user actually has: bash, zsh,
  PowerShell, etc.), the only source in this collection whose base prompt
  treats "which shell" as a variable rather than assuming one.
- **Tools generally**: `system.md` names **no built-in tools at all** —
  everything comes from dynamically-loaded **Extensions** ("Extensions
  provide additional tools and context from different data sources and
  applications. You can dynamically enable or disable extensions"), each
  contributing its own tools and, optionally, its own `### Instructions`
  block folded into the prompt. There's also a stated soft limit —
  `extension_tool_limits` triggers a suggestion to disable some
  extensions if the user exceeds a configured extension/tool count,
  because "exceeding recommended limits" degrades "tool selection
  accuracy" — the only source in this collection with an explicit
  too-many-tools warning built into the prompt logic itself.
- **Small/local-model fallback — a genuinely different tool-calling
  convention**: `tiny_model_system.md` abandons structured tool calling
  entirely for a `$`-prefixed plain-text shell convention ("To run a
  shell command, start a new line with $: `$ ls`"), text-parsed rather
  than API-native — directly comparable to mini-swe-agent's and
  Live-SWE-agent's text-block action parsing (see
  [`agent-tool-surfaces.md`](../agent-tool-surfaces.md)), but chosen here
  specifically for *weaker models*, not as a general design philosophy.
- **Code execution**: whatever the active extensions provide — nothing
  fixed in the base prompt.
- **Browser/web, multimodal**: not addressed in the base prompt (would
  come from extensions).
- **Sandbox/isolation**: not specified.

## Sub-agents

`subagent_system.md` is a complete, standalone system prompt swapped in
"when Goose spawns a sub-agent to handle a delegated task" — the third
source in this collection (with Copilot Chat and Crush) whose sub-agent
prompt text is fully captured, not just the orchestrator-side tool
description that triggers delegation.

- **Explicit identity and provenance**: opens with "You are a specialized
  subagent within the goose AI framework... You were spawned by the main
  goose agent to handle a specific task efficiently" — the sub-agent is
  told directly that it *is* a sub-agent and who spawned it, more
  self-aware framing than Copilot Chat's or Crush's sub-agent prompts,
  which describe a role ("execution research assistant," "web content
  analysis agent") without naming the spawning relationship itself.
- **A stated security boundary specific to recursion**: listed as one of
  five core characteristics — "Security: Cannot spawn additional
  subagents." Goose is the only source in this collection that states a
  no-recursive-delegation rule explicitly in the sub-agent's own prompt,
  rather than leaving nesting depth unaddressed.
- **Turn/timeout bounding via template variables**: `{{max_turns}}` is
  interpolated directly into the prompt text ("The maximum number of
  turns to respond is {{max_turns}}"), plus an optional `{{subagent_id}}`
  for tracking and `{{task_instructions}}` for the delegated task itself
  — all Jinja2-style fill-ins, consistent with the rest of Goose's
  template-based prompt system (see `{{shell}}` in "Tool surface" above).
- **Tool-efficiency framed as the sub-agent's primary constraint**: "Use
  tools only when absolutely necessary... Avoid exploratory tool usage
  unless explicitly required... Stop using tools once you have sufficient
  information" — a cost-consciousness instruction pushed down into the
  sub-agent itself, rather than left to the orchestrator's choice of
  when to delegate (contrast Gemini CLI's concurrency/conflict rules,
  which live entirely on the orchestrator side).
- **Communication contract**: markdown-formatted responses, clear
  progress updates, an explicit "this should be the last message you
  generate" instruction for the final summary/report — functionally
  similar to Copilot Chat's forced `<final_answer>` cutoff, but stated as
  a soft convention here rather than a hard turn-budget mechanism with an
  injected nudge message.

## Compaction

Already fully captured in this folder's `compaction.md`, not previously
written up as its own section. See
[`agent-context-compaction.md`](../agent-context-compaction.md) for the
cross-source comparison this feeds into.

- **Explicitly framed as removing only "the most verbose parts"**, not
  a full rewrite from scratch: "Generate a version of the below
  messages with only the most verbose parts removed... Include user
  requests, your responses, all technical content, and as much of the
  original context as possible" — closer to lossy compression of the
  existing transcript than Claude Code's/Copilot Chat's "produce a
  fresh structured handoff document" framing, though the output format
  below is still fairly structured.
- **Explicitly addressed to "you" (the agent), not a human reader**:
  "Use framing and tone knowing the content will be read [by] an agent
  (you) on a next exchange" and "this summary will only be read by you
  so it is ok to make it much longer than a normal summary you would
  show to a human" — an unusually direct statement that the summary's
  audience is the model itself, not something a user will ever see.
  Consistent with "Do not exclude any information that might be
  important to continuing a session working with you."
- **A private `<analysis>` reasoning pass before the output**, same
  pattern as Claude Code's stripped `<analysis>` scratchpad and Gemini
  CLI's `<scratchpad>` — chronological review, then per-part logging of
  goals/method/decisions/file-and-code-details, explicitly told to
  confirm completeness before finalizing.
- **A 9-section structured template**: User Intent, Technical Concepts,
  Files + Code, Errors + Fixes, Problem Solving, User Messages (with an
  instruction to truncate long tool-call arguments/results but keep the
  messages themselves), Pending Tasks, Current Work, and a conditional
  Next Step ("include only if directly continues user instruction" —
  i.e. don't invent a next step that isn't actually implied).
- **An explicit no-invention guardrail**: "No new ideas unless user
  confirmed" — the summarizer is told not to introduce plans or
  suggestions that weren't already part of the conversation.
- **No trigger/threshold information captured** — this file is the
  prompt text alone; what actually decides *when* to compact (a token
  budget check, a reactive error, a manual command) lives in
  surrounding Rust orchestration code not fetched into this collection,
  unlike the sources above where the trigger logic itself was
  independently investigated.
