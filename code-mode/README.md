# Code Mode

A sixth category: harnesses that replace a **tool list** with a **typed
API and a sandbox**. The model writes a program against generated
declarations instead of emitting one tool call per step, and intermediate
results never enter the conversation.

The pattern has converged from four directions in about a year, and this
collection now covers all four — two as full sources elsewhere, one read
here, one documented from its published description.

| Implementation | Where it is covered | Shape |
|---|---|---|
| **Cloudflare** `@cloudflare/codemode` | [`cloudflare.md`](./cloudflare.md) — **read from source here** | One `codemode` tool; connectors become sandbox globals; V8-isolate or iframe executor |
| **Codex** `tool_mode: "code_mode_only"` | [`../codex/README.md`](../codex) | The registry is not exposed as tools at all; `gpt-6-astra`'s whole surface is one JS-execution tool |
| **DeepSeek** Code Mode | [`../deepseek-harness/`](../deepseek-harness) | Every tool advertised as a compiling `.d.ts` with declared return types; asks for a program, not a call |
| **Anthropic** "code execution with MCP" | [`anthropic-pattern.md`](./anthropic-pattern.md) — published description, no source | MCP tools become TypeScript files on a filesystem the model imports |

The SDK Cloudflare's implementation lives in is read in full in
[`../cloudflare-agents/`](../cloudflare-agents).

Also here: [`webmcp.md`](./webmcp.md) — `navigator.modelContext`, the
W3C Community Group API that lets a **page** register tools with the
browser. Not Code Mode, but the other half of the same question for an
in-browser agent: where do the tools come from when there is no server.

## Why it is a category and not a footnote

The three claims the four implementations share, in their own words:

**Models are better at code than at tool calls.** Cloudflare states the
mechanism as training-data asymmetry:

> LLMs have an enormous amount of real-world TypeScript in their training
> set, but only a small set of contrived examples of tool calls.

**Intermediate results should not pass through the model.** This is the
sentence `../deepseek-harness/` lets the collection finally say plainly,
and it is the real economic argument: in a tool-call chain, every
intermediate payload is decoded by the model purely to be re-encoded into
the next call. Anthropic's published figure for one representative
workflow is **150,000 tokens → 2,000**.

**The tool catalogue belongs on disk, not in context.** Cloudflare
replaces the catalogue with `codemode.search()` / `codemode.describe()`;
Anthropic replaces it with a filesystem the model lists and reads.
Both are progressive disclosure applied to the tool surface rather than
to instructions — the same move as
[`../data-agents/data-formulator/`](../data-agents/data-formulator)'s
`load_skill`, one level down.

## What the collection already said about this

`../agent-tool-implementations.md` §5 distinguishes the two consumers of
a tool result — "Model, prose" versus "Model, programmatic" — and notes
that Code Mode hands the frozen value straight to the program, with the
cookbook's rule that **"Code Mode must never parse"** a human-readable
string. `../agent-tool-result-transport.md` §7 lists code execution as
"the school that avoids the question by not putting results in context at
all."

What this folder adds is the *delivery* layer those two docs assume: how
the declarations get generated, what the sandbox actually is, and what
the model is told.

## The honest caveats, collected

Each implementation names its own limits, and they rhyme:

- **Approval flows do not survive the boundary.** Cloudflare excludes any
  tool with `needsApproval` from codemode entirely rather than pausing
  mid-program. A program that calls five tools is one approval decision
  with five consequences, and nobody has solved presenting that.
- **Schemas are for the prompt, not the runtime.** Cloudflare's browser
  path says so outright: *"JSON Schema is used for prompt/type generation
  only and is not enforced at runtime."*
- **Determinism is a replay problem.** Cloudflare's durable replay
  requires connector calls "to occur in the same order", so
  `Promise.all()` — the thing you reach for in a program — risks replay
  divergence.
- **It is still one language.** "Limited to JavaScript execution."
