# Code Mode

A sixth category: harnesses that replace a **tool list** with a **typed
API and a sandbox**. The model writes a program against generated
declarations instead of emitting one tool call per step, and intermediate
results never enter the conversation.

The pattern has converged from four directions in about a year, and this
collection now covers all four (six, with the two added 2026-11-09) — two as full sources elsewhere, one read
here, one documented from its published description.

| Implementation | Where it is covered | Shape |
|---|---|---|
| **Cloudflare** `@cloudflare/codemode` | [`cloudflare.md`](./cloudflare.md) — **read from source here** | One `codemode` tool; connectors become sandbox globals; V8-isolate or iframe executor |
| **Codex** `tool_mode: "code_mode_only"` | [`../codex/README.md`](../codex) | The registry is not exposed as tools at all; `gpt-6-astra`'s whole surface is one JS-execution tool |
| **DeepSeek** Code Mode | [`../deepseek-harness/`](../deepseek-harness) | Every tool advertised as a compiling `.d.ts` with declared return types; asks for a program, not a call |
| **Anthropic** "code execution with MCP" | [`anthropic-pattern.md`](./anthropic-pattern.md) — published description, no source | MCP tools become TypeScript files on a filesystem the model imports |
| **Claude Code** `REPL` (2.1.318–2.1.319) | [below](#claude-codes-repl-and-pis-codemode-read-2026-11-09); pieces in [`../leaked/claude-code/piebald-2.1.319/`](../leaked/claude-code/piebald-2.1.319) | One persistent sealed JS context; every tool and MCP tool is an async function; scripts are dispatched with receipts; child agents are started from code |
| **Pi** `@earendil-works/pi-codemode` | [below](#claude-codes-repl-and-pis-codemode-read-2026-11-09) — package README read | QuickJS (WASI) in a worker thread per execution; tool calls recorded in `result.calls`; persistence returned as writes for the host to apply |

The SDK Cloudflare's implementation lives in is read in full in
[`../cloudflare-agents/`](../cloudflare-agents).

Also here: [`webmcp.md`](./webmcp.md) — `navigator.modelContext`, the
W3C Community Group API that lets a **page** register tools with the
browser. Not Code Mode, but the other half of the same question for an
in-browser agent: where do the tools come from when there is no server.
**Assessed and parked** — it solves a browsing problem, not an
internal-tooling one, and an agent already running its own loop in the
page can just call the functions. That file records the re-check
triggers so the question does not get re-opened from scratch.

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

## Claude Code's REPL and Pi's codemode (read 2026-11-09)

Two more implementations shipped in the week to 2026-11-09. Claude Code's
is read from the prompt pieces in Piebald's extraction, not from code;
Pi's from its package README at `badlogic/pi-mono` `ea1cfcc4c8`.

**Claude Code's `REPL`.** The tool description's first instruction is
"Batch ALL operations into ONE REPL call", and the helper interface
explains why in cost terms rather than capability terms:

> each call is a full model round-trip — the whole conversation is
> re-read before your script runs … while the work inside a script …
> is comparatively free … So the expensive thing is coming back to
> decide, not doing more in one go.

Four details matter beyond the shape the other four implementations
share:

- **What returns to context is chosen by the program.** "What it returns
  is added to your context and stays there; the value itself stays in
  the REPL whether you return it or not." `console.*` goes to a bounded
  ring read back with `console.tail(n)`; `preview(out)` returns a prefix
  plus the size and path of the saved output. This is
  `../agent-tool-result-transport.md` §7's "results never enter the
  conversation", given a tool the model uses to decide case by case.
- **State is persistent, and its loss is announced.** Variables persist
  across calls "but not across a restart, a resume, a fork or a wake:
  the first result after one of those says so."
- **Scripts are dispatched.** A script still running after a short wait
  returns `(dispatched #N)`; its output arrives later as an event. "A
  receipt means the script is queued or running, so sending it again
  would run it twice." See `../agent-run-recovery.md` §5 for the same
  rule applied to MCP tasks.
- **Child agents are values in the program.** `spawnContext({name,
  initialPrompt, fork?})` returns only `{name, role}`; the handle is
  looked up as `contexts[name]`, which has `status`, `tail(n)`,
  `result()` and `log(text)` (inside a context, `contexts.lead` is the
  main thread). `listContexts()` reports each context's token cost. That is sub-agent orchestration written as code, not as
  tool calls (`../agent-subagent-architectures.md`).

**How auto mode gates a program.** `../agent-design/tools.md` rules out a
general `execute(code)` partly because "a program is opaque until it
runs", so the harness loses pre-execution gating. Claude Code's answer,
from three refusal reminders:

1. **The whole script is checked once, before it starts.** "Auto mode
   checks each piece of code as a whole before it starts."
2. **An inner call whose payload the check cannot read is refused.**
   Starting a sub-agent and sending a message to an agent are both
   refused inside a script, because "auto mode can't read the task that
   the code gives the sub-agent" (or "the text that the code sends"). The
   check can see the code that builds the string but not the string, and
   a sub-agent's task is an instruction to another model, not an
   argument to a tool. Both reminders add "This is not a judgment that
   the task is unsafe", and the remedy is to do the work directly with
   `Promise.all`, or for the user to leave auto mode.
3. **A rewrite voids the check.** "In Code Mode, auto mode doesn't run
   code after a hook changed its call from what you wrote. This also
   applies when a hook changed an earlier tool call in the same
   response." What was checked must be what runs.
4. **Outside auto mode, inner calls are asked one by one.** The
   hook-rewrite reminder offers Manual mode, "where they are asked about
   each of the code's tool calls that needs approval", and the timeout
   piece counts "time spent waiting on permission prompts" against the
   script's 600,000 ms deadline.

So there are two gates: a static review of the program, which can only
pass what it can see, and per-call approval at the boundary, which
Cloudflare's `requiresApproval` path also uses. The refusals mark the
calls that only the second gate can handle. This is the first
implementation in this folder that says which calls a pre-execution check
cannot cover.

**Codex: an incremental catalog.** Codex's `code_mode_only` surface gained
incremental tool definitions (#60157, #60163, #60188, `openai/codex`
`8703d32bd0`, read by commit message): added or changed entries are sent
as complete replacements, removals as explicit notices, and the full
catalog is restored after `exec` has been hidden. Runtime activation is
off by default. It is the Code Mode version of the deferred-loading
question (`../agent-deferred-tool-loading.md`).

**Pi's codemode.** QuickJS compiled to WASI runs each execution in a
worker thread, or in a Durable Object of a separately deployed Worker,
with one API across the three sandboxes. Tool calls are recorded in
`result.calls`, while host `globals` behave like tools but are not
recorded. There are no timers, `fetch`, `process`, modules or
`WebAssembly`. A script waiting on a promise nothing can settle fails at
once rather than hanging. Persistence is a result, not a side effect:
`store`/`load` read values the host passes in, a successful result
reports `storeWrites`, and "Failed executions report no writes." The
README says nothing about approval, so gating is presumably per call in
the host's tool `execute`. That is inferred, not read.

## What runs the program: interpreters and their bounds (read 2026-11-09)

None of these runs model code in a container. Each puts a JavaScript
engine next to the agent loop, gives it nothing but the tool functions,
and bounds it in-process or in a sidecar. The exception is DeepSeek,
which moved the other way. Read from code or shipped binary unless
marked.

| Implementation | Engine and library | Process boundary | Bounds | What the engine is denied |
|---|---|---|---|---|
| **Cloudflare** | A fresh Worker per execution (`DynamicWorkerExecutor`, a V8 isolate from the Worker Loader binding), or an iframe in the browser (`cloudflare.md`) | Separate isolate on Cloudflare; the user's tab | Isolate limits; 30 s iframe timeout, which cannot stop `while(true)` | No network (`default-src 'none'` CSP in the iframe); tools by RPC or `postMessage` |
| **Codex** | `v8` crate (rusty_v8, pinned to an `openai-oss-forks` fork at `=152.2.0`) built with `v8_enable_sandbox`, plus `deno_core_icudata` for ICU data only; not `deno_core` itself | A separate `codex-code-mode-host` process, reached over stdio or gRPC, with its own macOS signing entitlements | `terminate_execution()` from the host, an optional `max_heap_size_bytes`, a JIT switch (`--jitless`) | `console`, `Atomics`, `SharedArrayBuffer` and `WebAssembly` deleted from the global; code is one ES module (`exec_main.mjs`); globals are `tools`, `ALL_TOOLS`, `setTimeout`, `text`, `image`, `store`/`load`, `notify`, `yield_control`, `exit` |
| **Pi** | `quickjs-wasi` 3.6.2: QuickJS compiled to WASI (package README) | A worker thread per execution, or a Durable Object in a separate Worker | `timeoutMs`, `memoryLimitBytes` (heap), QuickJS's interrupt handler; a deadlocked script fails at once | No timers, `fetch`, `process`, modules or `WebAssembly`; `eval` only makes more code inside the VM |
| **Claude Code `REPL`** | The JavaScript runtime's own `node:vm` on Bun (JavaScriptCore), found in the shipped 2.1.319 binary | **None**: a `vm` context inside the Claude Code process | A **step budget** ("a step is one pass through a loop or one call of a function"), a per-turn wall clock (`runInContext(…, {timeout})`), a cap on tool calls per script, a 600 s script deadline | Global created with a `null` prototype; `codeGeneration: {strings: false, wasm: false}` (no `eval`, no `new Function`, no WASM); dynamic `import` rejected; `Promise.prototype` patched; values cloned across the boundary |
| **DeepSeek** (`run_code`, formerly Code Mode) | A fresh **Node process** per call, running erasable TypeScript with direct Node APIs (`dsh-ptc-runtime-node`; design note `2026-09-11-sandboxed-node-ptc-runtime.md` at `deepseek-ai/deepseek-harness` `fcc0ad4`) | **The same OS sandbox as Bash** (`ctx.sandbox`), with the process lifetime owned by `ctx.subprocess` | 120 s elapsed deadline (cap 600 s), V8 old-generation heap limit, bounded control-channel frames | Nothing at the language level, by design: an empty `process.env`, and the OS sandbox does the rest |

**Three findings.**

- **Claude Code's interpreter is not a security boundary, and it knows.**
  Node's own docs say `node:vm` is not one. Claude Code hardens the realm
  anyway: no string or WASM code generation, no imports, and an engine
  check at start-up. The check runs a probe in a fresh context to test
  whether a host-realm `Function.prototype` leaks through a resolved
  thenable. If the runtime fails it, the tool refuses to run: "the
  JavaScript engine under Claude Code failed Code Mode's engine check.
  Run Claude Code with the repository's pinned Bun". The real boundary
  is that every tool function the script calls goes through the normal
  permission checks and the Bash sandbox. The **step budget** is the
  unusual part. The counter's source is in the binary, and loops and
  function calls are charged against it, so the script source must be
  rewritten before it runs. The rewrite itself was not located; that
  part is inferred. A source-level step counter catches `while(true)`
  where a wall-clock timeout cannot, and the clock-stop message is
  honest about the remaining gap: "The step budget counts loops and
  calls, not the time one built-in call takes, such as a regular
  expression match over a long input."
- **Codex takes the opposite engineering choice for the same goal.** It
  embeds V8 directly in a separate host process, with V8's own sandbox
  enabled and dangerous globals deleted. Termination comes from outside
  the isolate. There is no instrumentation.
- **DeepSeek rejected the in-process realm explicitly.** Its design note
  lists "Use an in-process JavaScript realm" and "Copy Codex Code Mode's
  execution model" as alternatives considered and not taken. The reason
  is that it wants model programs to use Node APIs directly, and "A
  language-level realm does not enforce the filesystem and process
  policy required for direct Node APIs. OS confinement and a host-owned
  process lifetime are the required protections." It also records that
  a worker "isolates JavaScript state but does not apply the calling
  Session's OS sandbox policy", which is why it moved off workers.

**The choice these split on** is whether the program gets capabilities
of its own. If it gets only the tool functions (Cloudflare, Codex, Pi,
Claude Code), a lightweight interpreter beside the loop is enough, and
the container stays where `Bash` runs. If it gets the host's APIs
(DeepSeek), it needs the same OS confinement as `Bash`, which for Keel
means running it in the run's container. The Keel placement is in
`../agent-design/future.md`'s Code Mode item.

## The honest caveats, collected

Each implementation names its own limits, and they rhyme:

- **Approval flows survive the boundary on exactly one of Cloudflare's
  two paths.** AI-SDK tools carrying `needsApproval` are silently
  filtered out of the codemode surface; a connector tool marked
  `requiresApproval` pauses the run and resumes it via durable replay.
  The capability exists and is reached by a wiring decision the model
  cannot see. See [`cloudflare.md`](./cloudflare.md).
- **Schemas are for the prompt, not the runtime.** Cloudflare's browser
  path says so outright: *"JSON Schema is used for prompt/type generation
  only and is not enforced at runtime."*
- **Determinism is a replay problem.** Cloudflare's durable replay
  requires connector calls "to occur in the same order", so
  `Promise.all()` — the thing you reach for in a program — risks replay
  divergence.
- **It is still one language.** "Limited to JavaScript execution."
