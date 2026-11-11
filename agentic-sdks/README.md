# Agentic SDKs and harnesses (LangChain Deep Agents, Pydantic AI, and the rest)

- **Type**: agent SDKs, workflow runtimes and harness libraries, read for
  how they solve the harness problems this collection catalogues. Not
  stored for their system prompts, though the prompts that matter are
  quoted.
- **Prompted by**: `agentic_sdks_mcp_deep_dive.docx` at the repo root
  (added 2026-11-11). A plain-text copy is in
  [`source-deep-dive.md`](./source-deep-dive.md).
- **Read**: 2026-11-11, from source at the SHAs in
  [`../sources.md`](../sources.md), "Agentic SDKs (read 2026-11-11)".
- **Licenses**: Deep Agents MIT; LangChain and LangGraph MIT; Pydantic AI
  and Pydantic AI Harness MIT; OpenAI Agents SDK MIT; Claude Agent SDK
  MIT (the SDK wrapper; the bundled CLI is not); Microsoft Agent
  Framework MIT; CrewAI MIT; LlamaIndex MIT.

## What the source document argues

The deep dive's thesis is that the choice is no longer which package
runs the tool-calling loop but **which layer owns execution, context,
capability discovery, durability and security**. It splits the field
into four layers (agent SDK, workflow runtime, agent harness,
interoperability protocol), argues that LangChain's real contribution is
three separate mechanisms for three pressures (tool-schema size,
tool-result size, long-horizon state), and ends with a production design
for a large MCP estate: an authorised catalogue, then discovery and
deferral, then compact model-visible results, with full results kept
separately.

Every one of those positions already has a counterpart in Keel or
Forge, and the comparison is in
[`../agent-design/proposals-agentic-sdks-2026-11.md`](../agent-design/proposals-agentic-sdks-2026-11.md)
§0. What the document adds is a set of **libraries this collection had
never read**, and reading them turned up mechanisms the document does
not mention. Those are the useful part.

## The files

| File | What |
|---|---|
| [`deepagents.md`](./deepagents.md) | Deep Agents SDK 0.7.35 and Deep Agents Code (`dcode`) 0.2.7: the middleware stack, harness profiles per model, the rubric grader, goal criteria drafting, skill-scoped tools, offload paths, fork subagents, and dcode's threat model |
| [`langchain-langgraph.md`](./langchain-langgraph.md) | LangChain 1.5 middleware (provider tool search, the LLM tool selector, the risk classifier, context editing) and the new `langchain.mcp` adapter (results, metadata, elicitation as an interrupt); LangGraph's durability modes and node replay |
| [`pydantic-ai-harness.md`](./pydantic-ai-harness.md) | Pydantic AI's capability model and the Harness library's 80+ capabilities, read for the ones no other source has: the trajectory judge, cache-safe system reminders, cache-bust detection, the approval reviewer, step persistence with a tool-effect ledger, deferred tools |
| [`other-sdks.md`](./other-sdks.md) | OpenAI Agents SDK (sandbox agents, manifests, memory), Claude Agent SDK, Microsoft Agent Framework's harness agent, CrewAI's LLM guardrail, LlamaIndex |
| [`source-deep-dive.md`](./source-deep-dive.md) | The source document, as text |

New concepts went into two new feature documents,
[`../agent-run-steering.md`](../agent-run-steering.md) and
[`../agent-prompt-cache-health.md`](../agent-prompt-cache-health.md), and
into sections of four existing ones (listed in `changelog.md`,
2026-11-11).

## The document's claims, checked against source

The document is careful to separate documented behaviour from inference,
and most of it holds. Where the source differs, the source wins.

| Claim | Verdict | Where checked |
|---|---|---|
| Large tool results offload at a default of 20,000 tokens | **Holds** (`tool_token_limit_before_evict=20000`, at 4 chars per token) | `deepagents/middleware/filesystem.py` |
| Offloaded results come back as "a path plus an initial 10-line preview" | **Corrected**: 5 head lines and 5 tail lines with a truncation marker between, each line clipped to 1,000 characters, and a note telling the model to read with `offset`/`limit` | `deepagents/middleware/_message_eviction.py` (`_create_content_preview`, `PREVIEW_LINE_CHAR_LIMIT`) |
| Summarisation triggers at "illustratively 85%" of input context | **Holds as the default** when the model has a profile: trigger 0.85, keep 0.10. Without a profile: 170,000 tokens, keep 6 messages | `deepagents/middleware/summarization.py` (`compute_summarization_defaults`) |
| Offloading reduces future context, not transport bytes | **Holds**, and the SDK adds a third path the document misses: on a provider context-overflow error, the trailing tool-result batch is clipped or offloaded and the request retried | `_overflow_clip.py` |
| `metadata.include_tools` is a space-separated string | **Holds**; a YAML list or a comma-separated string is logged as a warning, not accepted | `middleware/skills.py` |
| Tool availability can change after summarisation | **Holds, and it is by design**: a skill's tools are gated on a read of its `SKILL.md` being present in the transcript the model call sees, recomputed on every call | `middleware/_skill_tools.py` |
| dcode 0.2.3 (2026-11-02) adds MCP schema deferral through provider tool search | **Holds**; it is applied only on verified native endpoints, and history is scrubbed of the other provider's search blocks when the model changes | `deepagents_code/provider_tool_search.py` |
| `MCPAdapter` is beta, built on FastMCP | **Holds** (`langchain` 1.5.0) | `langchain/mcp/adapter.py` |
| Resuming an elicitation reruns the tool from the beginning | **Holds, and the reason is the protocol, not LangChain**: under MCP `2026-07-28` a server that needs input returns `InputRequiredResult` and the client **retries the `tools/call`** with answers. The adapter drives that loop itself so each round is one LangGraph `interrupt()` | `langchain/mcp/elicitation.py` |
| Sampling and roots are not supported over that path | **Holds**: "Only elicitation is answered. Sampling, roots, and continuation rounds are refused rather than half-served" | same |
| MCP `structuredContent` goes to `ToolMessage.artifact`, not model-visible text | **Holds** (`MCPToolArtifact`) | `langchain/mcp/tools.py` |
| `read_only_hint` / `destructive_hint` reach tool metadata | **Holds**, under an `mcp` namespace with server identity beside it | same |
| LangGraph resumption reruns the interrupted node | **Holds**: "The graph resumes from the start of the node, **re-executing** all logic" | `langgraph/types.py` (`interrupt`) |
| Pydantic AI and Microsoft now ship harness layers | **Holds**, and understated: Pydantic AI Harness lists 80+ capabilities; Microsoft's `create_harness_agent` is in core | `pydantic-ai/docs/harness/index.md`; `agent_framework/_harness/_agent.py` |
| Terminal-Bench 2.0: 52.8% → 66.5% from harness-only changes | **Not re-checked** (vendor blog); cited as the document reports it | — |

## What the document does not mention, and this pass found

The mechanisms worth carrying forward, each with its file:

1. **A grader that cannot shrink the rubric** (Deep Agents
   `RubricMiddleware`). When the agent would stop, a separate grader
   scores the transcript against a caller rubric; the first grading pass
   freezes the criterion *names*, and a later verdict that covers fewer
   criteria is retried once and, if still short, a `satisfied` verdict is
   downgraded and flagged `unverified`. [`deepagents.md`](./deepagents.md) §4.
2. **Acceptance criteria drafted and frozen before the work starts**
   (dcode `/goal`). A bounded, read-only criteria agent turns a goal into
   2–5 observable bullets with rules against invented requirements and
   against bullets that only restate the goal. [`deepagents.md`](./deepagents.md) §5.
3. **A live trajectory judge** (Pydantic AI Harness). A second model
   reads a sliding window of the run every N requests and either does
   nothing or sends a correction, framed with a random `ref` so a forged
   correction in a tool result is disowned. [`pydantic-ai-harness.md`](./pydantic-ai-harness.md) §2,
   [`../agent-run-steering.md`](../agent-run-steering.md).
4. **Prompt-cache collapse detection from the provider's own numbers**
   (Pydantic AI Harness `WarnOnCacheBusts`), with a classification that
   separates a moved prefix from an expired cache.
   [`../agent-prompt-cache-health.md`](../agent-prompt-cache-health.md).
5. **Per-model harness profiles** (Deep Agents). Prompt suffixes, tool
   description overrides, tool exclusions and extra middleware keyed by
   exact model id, with a rule that required scaffolding cannot be
   excluded. Deep Agents 0.7 removed its authored base prompt; what is
   left is per-model. [`deepagents.md`](./deepagents.md) §2.
6. **A tool-effect ledger** (Pydantic AI Harness `StepPersistence`): a
   call with a `started` record and no terminal one is
   `unknown_after_crash`. [`pydantic-ai-harness.md`](./pydantic-ai-harness.md) §6.
7. **Fork subagents that keep the parent's system prompt** so the fork
   reuses the cached prefix, with the fork's own instructions delivered
   with the task. [`deepagents.md`](./deepagents.md) §7.
