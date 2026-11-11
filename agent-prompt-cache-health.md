# Prompt-cache health: keeping the prefix still, and noticing when it moves

*Added 2026-11-11, from the agentic-SDK deep dive
([`agentic-sdks/`](./agentic-sdks)). Sources and SHAs are in
[`sources.md`](./sources.md), "Agentic SDKs (read 2026-11-11)".*

Prompt caching pays only while the cacheable prefix (tools, then system,
then message history) is byte-identical from one request to the next.
Everything else in this collection that touches caching is about
**keeping** the prefix still: deferred tools that arrive as messages
rather than array entries ([`agent-deferred-tool-loading.md`](./agent-deferred-tool-loading.md)
§2), context files that avoid a timestamp in the header
([`agent-context-file-loading.md`](./agent-context-file-loading.md)),
Keel's mid-conversation tool changes. This document adds the other half,
which no source in the collection had until now: **noticing** that the
prefix moved, from the provider's own numbers, and telling a real
collapse from an expired cache.

## 1. What moves a prefix

From the sources read so far, the ways a harness breaks its own cache:

| Cause | Example | Who avoids it, and how |
|---|---|---|
| Tools reordered or changed mid-run | a server connects late and its tools join the array | Claude Code: names arrive as a message, definitions by reference (`agent-deferred-tool-loading.md` §2) |
| Something volatile in the system prompt | a timestamp, a git status, a fresh context-file header | Claude Code reuses a stored header (`agent-design/context-files.md`) |
| Guidance injected at the front | a reminder appended to the instructions | Pydantic AI Harness `SystemReminders`: a request-scoped system prompt **at the tail**, after the cache breakpoint (§3) |
| A past injected message deleted | clearing old reminders from history | `SystemReminders` on Anthropic sends `clear_at` instead, so every copy stays on the wire and costs nothing once cleared; deleting one "would invalidate every thinking block after it on models with preserved thinking" |
| A subagent given its own system prompt when it could reuse the parent's | a forked child with new instructions | Deep Agents `mode="fork"`: the fork keeps the parent's system prompt unchanged and gets its own instructions "with the task after the history", because changing it would "stop the fork from reusing the parent's cached prompt prefix" (`agentic-sdks/deepagents.md` §7) |
| A pinned notice rewritten in place | an updated goal status edited into an earlier message | dcode: "Earlier bounded notices remain unchanged for prompt-cache stability"; a fresh notice is appended and supersedes them (`THREAT_MODEL.md` TB12) |
| Provider-specific blocks left in history after a model switch | Anthropic tool-search blocks sent to OpenAI | dcode `_portable_history` strips the other provider's blocks before each call; the cache is lost anyway, but the request is valid |
| Compaction | the history is replaced by a summary | by design; a detector should not warn (§2) |

## 2. Detecting a collapse: `WarnOnCacheBusts`

Pydantic AI Harness (`docs/harness/warn-on-cache-busts.md`) is the only
implementation found. It observes; it changes nothing.

**The signal.** Each response reports `cache_read_tokens` and
`cache_write_tokens`. The monitor tracks the **established prefix**,
`cache_read + cache_write`, which grows as the conversation grows.
"Because message history is append-only, a stable prefix means each
request for that model reads back at least what the previous one cached,
so any real shortfall is the observable signature of a collapse,
including a partial one, where a change deep in the history moves only
the tail of the prefix."

**The threshold.** Warn when a request falls short of the established
prefix by more than 5% of it **and** by at least 2,000 tokens, "the
thresholds Claude Code uses for a prompt-cache miss" (per the Pydantic
docs; not checked in Claude Code's source). Then re-baseline to what the
collapsing request established, and stay quiet until a healthy read-back,
so "a prefix that moves on every request … warns once, not on every
request".

**The classification.** A shortfall has two causes the token counts
cannot separate: the prefix moved, or the cache expired. The provider's
retention window separates them, timed from the same model's previous
request:

| `reason` | Meaning | Warns |
|---|---|---|
| `unexpected` | Retention should still be active, so the prefix moved | yes |
| `unknown` | The provider publishes no retention window | yes |
| `ttl_expired` | The gap exceeded the retention window | no |
| `compacted` | Provider-native compaction replaced history | no |
| `unreported` | No cache usage reported (caching off, or a full miss on read-only reporters) | no |

**The keys.** Marks are kept per `(provider, endpoint, model)`, so a
fallback or a per-step model change starts its own mark instead of
warning, and switching back compares against that model's own prefix.
Marks are also kept per **conversation**, so the first request of a
continued run is checked against what the previous run cached: "That is
where a moved prefix most often hides: history rewritten between turns,
or a tool or instruction that differs from one turn to the next."
Idle conversations are forgotten after 24 hours.

**Two edge cases it handles.** A response that ran a provider-native
tool (web search, code execution) may report cache reads summed over the
provider's internal calls, so it is judged but cannot raise the mark. A
request of 4,096+ input tokens to a model that caches only on request,
with no caching configured, gets a separate `CacheNotEnabledWarning`
once.

## 3. Placing injected text so it does not move the prefix

The general rule the sources converge on: **anything the harness adds
mid-run goes at the tail, and stays put once sent.**

- Pydantic's reminders are request-scoped by default (seen on the
  request they fire on, not after) and conversation-scoped when an
  obligation must outlast that step. Either way they are appended.
- Pydantic's trajectory judge mints its feedback element's `ref` once
  and stores it, "so later requests resend both parts unchanged"
  ([`agent-run-steering.md`](./agent-run-steering.md) §3).
- Keel's harness notes ride in the tool result they concern
  ([`agent-design/models.md`](./agent-design/models.md) §2), which is
  already the tail.

## 4. Consequences for Forge

- Keel already keeps its prefix still by construction: the tools array
  and system prompt are fixed for a run, and reveals are mid-conversation
  `tool_addition` messages ([`agent-design/keel/tools-and-agents.md`](./agent-design/keel/tools-and-agents.md)
  §4b). What it lacks is the check that this holds in production.
  `eval.md` has no cache metric at all.
- The detector is cheap (two numbers per response, per model key) and
  observe-only, so it can ship as a run event and an eval metric without
  touching a prompt. Proposal 2 in
  [`agent-design/proposals-agentic-sdks-2026-11.md`](./agent-design/proposals-agentic-sdks-2026-11.md).
- A retry attempt is a new conversation in Keel (fresh transcript), so
  marks start clean there. A resumed `AskUser` run does carry the
  suspended transcript (`agent-design/formats.md` §5), but a reply
  usually lands hours later, past any retention window, so it would
  classify as `ttl_expired`. The check that matters for Keel is the one
  inside a run.
