# CodeAct with Hyperlight

- **Type**: Agent orchestration pattern (not a coding agent itself — a
  tool-use *strategy* any agent built on Microsoft's Agent Framework can
  opt into), paired with a sandboxed code-execution backend
- **License**: MIT
- **Source**: https://github.com/microsoft/agent-framework
- **Retrieved from**: `main` branch,
  `python/packages/hyperlight/agent_framework_hyperlight/` (2026-07-10)
- **Announced**: https://devblogs.microsoft.com/agent-framework/codeact-with-hyperlight/

**CodeAct** is the pattern (from the "Executable Code Actions Elicit
Better LLM Agents" line of research — also what OpenHands's `CodeActAgent`
in this collection is named after) of having the model write a short
Python program that chains multiple tool calls together, instead of
round-tripping one tool call at a time. Microsoft's implementation pairs
it with **Hyperlight**, a micro-VM runtime: each `execute_code` call runs
in a fresh, millisecond-startup VM with no filesystem/network access
except what's explicitly allow-listed.

The blog post itself only shows a placeholder system prompt
("You are a helpful assistant.") with a note that "CodeAct instructions
are injected programmatically" — the actual instruction text lives in
`_instructions.py`, fetched here directly.

## What makes this distinct from everything else in this collection

The CodeAct instructions and the `execute_code` tool description are
**not static text** — both are generated fresh per run from the sandbox's
actual configured capabilities (which tools are registered, whether a
filesystem is mounted, which network domains are allow-listed). No other
source in this collection dynamically renders its *sandbox capability
description* into the prompt like this — closest comparisons are Gemini
CLI's sandbox-type-conditional paragraphs (macOS Seatbelt vs. container;
see `coding-agent-approaches.md` §3) and Bolt.new's static WebContainer
constraints section, but both of those are close to fixed text with minor
branching, not fully assembled from a live tool/capability registry the
way this is.

**Scope note**: this folder name and its original research covered one
specific feature of Microsoft's Agent Framework — CodeAct plus
Hyperlight sandboxing. The framework turns out to have an entirely
separate, more significant feature area for **multi-agent
orchestration** (as opposed to what one agent does internally), covered
in its own section below after being missed in the original pass — see
[`agent-subagent-architectures.md`](../agent-subagent-architectures.md)
for how it fits into this collection's broader sub-agent survey.

## Files

- `_instructions.py` — the two prompt-building functions:
  - `build_codeact_instructions()` — the short instructions injected into
    the agent's system prompt: "you have one primary tool: execute_code,"
    prefer one call per request, must `print(...)` to surface output
    (the sandbox doesn't return the last expression's value — a real gotcha
    worth knowing if adapting this).
  - `build_execute_code_description()` — the (much longer) dynamic tool
    description itself: documents the in-sandbox `call_tool(name, **kwargs)`
    built-in, lists every registered sandbox tool with its params, and
    renders the current filesystem/network policy in prose (e.g. "Outbound
    network access is allowed only for these configured targets:
    `api.example.com`: GET, POST.").
- `_provider.py` — `HyperlightCodeActProvider`, the integration point that
  calls `build_instructions()` and injects the result into the agent's
  context before each run via `context.extend_instructions(...)`.

## Tool surface

The one source in this collection where "tool surface" is *itself* the
whole product — not a fixed list, but a **rendering of whatever the
sandbox is currently configured with**, regenerated per run.
- **Execution — the single primary tool**: `execute_code`, one Python
  program per call, run inside a fresh Hyperlight micro-VM. Individual
  sandbox tools are exposed to the *code*, not to the model, via a
  `call_tool(name, **kwargs)` built-in — the model chains multiple
  registered tools together inside one program instead of one
  model-visible tool call per turn, the core CodeAct idea. A real gotcha
  flagged explicitly: the sandbox doesn't return the last expression's
  value, so the code must `print(...)` to surface anything.
- **Registered sandbox tools — variable, not fixed**: whatever
  `FunctionTool`s the host application registers; `_format_tool_summaries`
  renders each one's name/description/parameters into the tool
  description text at build time, so the model only ever sees the tools
  actually available in that deployment (says "No tools are currently
  registered" if none are).
  - `tools_visible_to_model` is itself a config flag — some deployments
    additionally expose the registered tools directly to the model
    (alongside `execute_code`), others hide them entirely behind
    `call_tool`, changing which usage note gets rendered.
- **Filesystem — off by default, then policy-rendered**: no filesystem
  access at all unless `filesystem_enabled`; when on, a fixed `/input`
  (read) / `/output` (write, auto-attached to the tool result)
  convention, plus an optional mounted workspace root and arbitrary extra
  mounted paths — all spelled out in prose generated from the actual
  mount config, not hardcoded text.
- **Network — allow-listed per target, per method**: off by default
  ("Outbound network access is unavailable because no allow-listed
  targets are configured"); when configured, each allowed domain is
  rendered with its permitted HTTP methods (e.g. "`api.example.com`: GET,
  POST").
- **Search/browser/multimodal**: none built into the pattern itself —
  entirely dependent on whatever tools the host application registers
  into the sandbox.
- **Sandbox/isolation**: the headline feature — Hyperlight micro-VMs,
  millisecond startup, no filesystem/network by default, everything
  explicitly allow-listed. Compare Bolt.new's WebContainer (browser-based
  sandbox with a fixed 39-command allowlist, static text) and Gemini
  CLI's macOS-Seatbelt-or-container split (also prompt-conditional, but
  branching over ~2 fixed descriptions rather than assembled from a live
  capability registry).

## Multi-agent orchestration (a separate feature area, missed originally)

CodeAct is about what **one** agent does inside a single tool call.
Microsoft's Agent Framework separately ships — as its own installable
package, `agent-framework-orchestrations`
(`python/packages/orchestrations/agent_framework_orchestrations/`, a
sibling of the `hyperlight` package this folder documents, both reached
via lazy import shims in `agent_framework/core`) — a genuinely
sophisticated layer for how **multiple** agents relate to each other.
This is architecturally siloed from CodeAct (no code cross-references
either direction) but **compositionally connected**: every orchestration
participant just needs to satisfy a `SupportsAgentRun` protocol
(`id`/`name`/`description`/`run()`), and `Workflow.as_agent()` lets a
whole *orchestration* satisfy that same protocol — so a CodeAct-using
agent can be one participant in an orchestration, and an entire
orchestration (a Magentic team, a Handoff swarm) can itself become one
tool-callable participant nested inside a larger structure. A concrete
sample (`magentic_workflow_as_agent.py`) confirms this nesting is a real,
demonstrated pattern, not just a theoretical possibility.

Five named, `Builder`-configured patterns, all compiling down to a
shared `Workflow` graph-execution engine (`agent_framework/_workflows`):

- **Sequential** — participants run one after another; each sees the
  full accumulated conversation by default (a flag switches this to
  "only the immediately-prior response"). Last participant's output is
  the workflow output unless `output_from` names someone else.
- **Concurrent** — the same input is broadcast to every participant in
  parallel, each with an *isolated* conversation history (not shared);
  results converge via a default aggregator (pulls each participant's
  final message) or a custom combination callback.
- **Handoff** — decentralized, model-driven routing. Allowed handoffs
  are injected into each agent's own toolset as synthetic
  `handoff_to_{target_id}` tools; a middleware intercepts calls to them
  and redirects the turn. Conversation is a single shared thread,
  broadcast to all participants after every turn (internal handoff
  plumbing stripped before broadcast). Positioned explicitly (per the
  framework's own AutoGen-migration guide) as the successor to AutoGen's
  `Swarm` pattern.
- **GroupChat** — a central orchestrator owns history and decides turn
  order, either via a plain selection function or an LLM-based manager
  that outputs a structured "next speaker + terminate?" decision each
  round.
- **Magentic** — the most sophisticated of the five, modeled on
  Magentic-One: a manager agent builds and maintains a structured "task
  ledger" (facts + plan, via a dedicated three-stage prompt sequence),
  runs an inner loop producing a "progress ledger" each round (task
  satisfied? loop detected? next speaker + instruction?), detects
  stalls and can trigger a full replan-and-reset, and synthesizes a
  final answer from the complete history once the ledger reports the
  task done. Optional human plan-sign-off before execution begins. The
  framework's own samples position this for open-ended research tasks
  — directly matching the pattern's public "deep research" use case.

Each pattern differs in whether participants share one conversation
(Handoff, GroupChat) or run isolated (Concurrent), and in how a final
result is determined (last-speaker, aggregator, live-per-turn,
full-history, or synthesized-by-manager) — there is no single unifying
protocol across the five, each is a genuinely distinct design. A general
single-agent "run until done" loop (`agent_framework/_harness`, with
its own todo-list, tool-approval, and "judge"-pattern self-evaluation
machinery) is a separate, orthogonal runtime concern — closer to a
coding agent's own inner ReAct loop than to any of the five
multi-agent patterns above. See
[`agent-subagent-architectures.md`](../agent-subagent-architectures.md)
for how Handoff/GroupChat/Magentic compare to every other source's
sub-agent design in this collection — none of the other 16 sources
there implement anything resembling GroupChat or Magentic's
ledger-driven replanning.

## Self-verification: the "judge" pattern, in full

See [`agent-self-verification.md`](../agent-self-verification.md) for
the cross-source comparison this feeds into — this framework's judge is
the clearest, most fully-specified LLM-as-checker mechanism found
anywhere in this collection.

`AgentLoopMiddleware.with_judge()` (`agent_framework/_harness/_loop.py`)
is a factory building a `should_continue`/`next_message` pair for the
general single-agent "run until done" loop, backed by a **second,
fully separate chat-client call** — it does not route through the
wrapped agent's own pipeline, tools, or session at all.

- **Structured verdict, with a text-marker fallback**: `JudgeVerdict`
  (`answered: bool`, `reasoning: str`) requested via structured output
  when the judge's model supports it; falls back to parsing literal
  `VERDICT: DONE`/`VERDICT: MORE` markers otherwise, with anything
  ambiguous or missing treated as "more work needed" — a fail-closed
  default.
- **Checked against the original request, not a todo list**: the judge
  is sent the original user messages verbatim and asked whether they've
  been "fully addressed" — an optional `criteria` list augments this
  (injected both as extra instructions for the working agent *and* into
  the judge's own prompt) but doesn't replace the original-request
  anchor.
- **Failure produces a nudge, not a restart**: on a "not answered"
  verdict, the judge's own `reasoning` is fed back as a new user turn —
  "An evaluator reviewed your previous response and judged that it does
  not yet fully address the original request. Evaluator feedback:
  {feedback}. Revise and continue..." The conversation either
  accumulates normally or restarts from the original input plus a
  progress log, depending on a `fresh_context` setting.
- **Deliberately capped tighter than non-judge loops**: 5 iterations by
  default versus 10 for a plain loop, checked *before* invoking the
  judge so an expensive judge call is skipped once the cap fires — the
  framework's own docstring calls judge calls out as "costly and
  probabilistic," a rare case of a scaffold explicitly budgeting for
  the cost of checking its own work, not just the work itself.
- **Optional, never wired in by default**: `create_harness_agent()`
  only attaches this middleware when a caller explicitly passes
  `loop_should_continue` — the judge is one of several interchangeable
  strategies, alongside non-LLM alternatives defined in the same file
  (`todos_remaining()` — loop while a todo list has open items;
  `background_tasks_running()`).
- **A self-aware security warning, stated directly in the judge's own
  docstring**: using a judge is called out as introducing "a second
  external LLM boundary" — a route for data exfiltration or indirect
  prompt injection, since the judge's feedback text gets fed straight
  back into the working agent's context as an ordinary user turn. No
  other source in this collection's self-verification survey documents
  this specific risk (a verification mechanism itself becoming an
  injection vector) as explicitly as this one does.
