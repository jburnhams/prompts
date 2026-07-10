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
