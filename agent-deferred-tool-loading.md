# Deferred tool loading: how Claude Code adds tools without breaking the cache

Written 2026-10-22. Question: is Claude Code's deferred-tool mechanism a meta
tool that adds new tools, and how does it avoid invalidating the prompt
cache? Short version: **yes, a meta tool (`ToolSearch`), but it adds
*definitions to the conversation*, not entries to the tools array.** The
tools array never changes. That is the whole trick.

Sources, read 2026-10-22: Anthropic's [tool search
docs](https://platform.claude.com/docs/en/agents-and-tools/tool-use/tool-search-tool)
and [tool use with prompt
caching](https://platform.claude.com/docs/en/agents-and-tools/tool-use/tool-use-with-prompt-caching);
Claude Code's [MCP
docs](https://code.claude.com/docs/en/mcp) (the "Scale with MCP tool search"
section); the `ToolSearch` tool description and the deferred-name notices
visible in this session; and this collection's
[`leaked/claude-code/deferred-tools.md`](./leaked/claude-code/deferred-tools.md).
Statements marked *inferred* are not in a source.

## 1. Two layers

**Layer 1: the API (`defer_loading` and `tool_reference`).**

- The client sends **every** tool definition in `tools` on **every** request,
  deferred ones included, each flagged `defer_loading: true`. The API needs
  them server-side to run searches and expand references.
- Deferred tools are **excluded from the system-prompt prefix.** At least one
  tool must stay non-deferred (the search tool is one); the docs recommend
  keeping the 3–5 most used non-deferred.
- When the model searches, the API returns `tool_reference` blocks, then
  "appends a `tool_reference` block inline in the conversation" and expands it
  into the full definition before the model sees it. Later turns re-expand the
  same references throughout history, so a discovered tool stays usable
  without searching again.
- Two search variants are built in: regex (`tool_search_tool_regex_20251119`,
  Python `re.search`, 200-char pattern limit) and BM25 (natural language,
  500-char query). Both search names, descriptions, argument names and
  argument descriptions. Default 5 results per search.
- You can write your own search tool. Return `tool_reference` blocks inside an
  ordinary `tool_result`; every referenced tool must still be in `tools`.

**Layer 2: Claude Code (`ToolSearch`, a client tool).**

- The `ToolSearch` tool takes a query: `select:Read,Edit` for exact names, a
  keyword query, or `+slack send` to require a name term. Its description
  tells the model deferred tools "appear by name in `<system-reminder>`
  messages", that until fetched "only the name is known", and that once a
  schema appears in the result the tool is "callable exactly like any tool
  defined at the top of the prompt". *Inferred:* because its syntax is neither
  regex nor BM25, it is the custom-search pattern above, returning
  `tool_reference` blocks. The gateway docs confirm Claude Code's requests
  carry `defer_loading` fields and `tool_reference` blocks.
- **Built-in tools are deferred too, not only MCP.** The 23 listed in
  `leaked/claude-code/deferred-tools.md` include `Cron*`, `Task*`,
  `EnterPlanMode`, `Monitor`, `WebFetch`, `WebSearch`. The always-present core
  is small (Read, Edit, Bash, Grep and the like) plus `ToolSearch` itself.
- At session start the model sees tool **names** (and MCP server
  **instructions**), nothing else. The server's instructions are the "when to
  search for this" hint, so the docs tell server authors to write them
  carefully.

## 2. Why the cache survives

The cache is a prefix hierarchy, `tools` → `system` → `messages`; a change at
one level invalidates it and everything after. Modifying tool definitions
invalidates all three. Five choices keep that from happening:

1. **The prefix is constant.** Deferred definitions are not in it. Docs:
   "The prefix is untouched, so prompt caching is preserved … you can start a
   conversation with a small set of always-loaded tools (cached), let the
   model discover additional tools as needed, and keep the same cache hit
   across every turn."
2. **Discovery lands at the tail.** The expansion is appended in the message
   history, where new content always goes. Cost is one cache write for the new
   tokens, not a re-read of everything.
3. **Name lists are messages, not system prompt.** When an MCP server finishes
   connecting mid-session, Claude Code "lists the server's tool names to
   Claude on its next request in the same turn". This session shows the same
   thing: "The following deferred tools are now available via ToolSearch"
   arrived as a notice after start. Late arrivals are an append, never a
   rewrite of the system prompt. *Inferred:* the same reason the server's
   tool definitions can be added to the `tools` array without moving the
   prefix, since they are flagged deferred and excluded from it.
4. **Cache breakpoints sit on a non-deferred tool.** A deferred tool cannot
   carry `cache_control` (the API returns 400).
5. **Hysteresis.** With `ENABLE_TOOL_SEARCH=auto` (defer once definitions
   reach 10% of the context window; `auto:N` changes the percentage), "tool
   search was already on in this conversation and stayed on" even if the
   total later falls below the threshold. A threshold that could flip
   mid-conversation would flip the prefix.

What still invalidates the cache, per the docs: changing a non-deferred tool,
toggling web search or citations, changing `tool_choice` or
`disable_parallel_tool_use` (messages cache), changing thinking or effort
settings. Not in the table but implied: caches are per model, so a model
switch loses it. *Not stated anywhere I found:* what happens to loaded
`tool_reference` blocks when Claude Code compacts the history. If the
summary drops them, the model has to search again; check before relying on
it.

## 3. Configuration and limits worth copying

| Item | Claude Code behaviour |
|---|---|
| Default | MCP tools deferred, on models Opus 4 / Sonnet 4 / Haiku 4.5 and later; earlier models load everything upfront |
| `ENABLE_TOOL_SEARCH` | unset/`true` always defer; `auto`, `auto:N` threshold mode; `false` load all upfront |
| Exemptions | `alwaysLoad: true` per server; `_meta["anthropic/alwaysLoad"]` per tool from the server author; the user's setting can override the author's |
| Description caps | 4,096 characters for server instructions and for tools loaded upfront; 16,384 for tools loaded via search. Search matches only the capped text, so put search words first |
| Fallbacks | Foundry-on-Azure rejects tool search, so tools load upfront; behind a gateway, v2.1.305+ retries without tool search after an unrecognised 400/422 |
| Disabling | deny `ToolSearch` in permissions and MCP tools load upfront |
| Evidence | Anthropic reports ~85% fewer tool-definition tokens in a five-server setup and MCP-eval gains of 49%→74% (Opus 4) and 79.5%→88.1% (Opus 4.5); these are Anthropic's own internal numbers |
| Cost | one extra round trip per discovery; the model must decide to search |

## 4. Consequences for Forge

- **`Expand` is this mechanism.** Forge's focused data tools
  (chart spec, profile, fetch, table ops) sit in the fixed, cached `tools`
  array flagged deferred. The overview line "N more sources, `Expand` reveals
  them" is the name list. A model-called `Expand` returns `tool_reference`
  blocks. Nothing is added to the array mid-run. Data *sources* need none of
  this: they are text in the `Expand` result, and the SQL tool already
  accepts any granted source name.
- **"Hidden" is "deferred and unannounced."** A tool the model was never told
  about can still be revealed by the harness if a harness-triggered result
  carries a `tool_reference` for it. *Unverified:* that a harness-built tool
  result may carry references the model did not ask for. The docs show it only
  for a custom search tool's result. The two knobs are then independent:

  | | Pulled by the model | Pushed by the harness |
  |---|---|---|
  | **Announced by name** | deferred tool, found via search | harness says "tool X now available" |
  | **Not announced** | a free-text request to the search tool | hidden tool revealed by a trigger |

- **Provider portability decides the fallback.** Server-side deferral needs
  the Claude API or a gateway that forwards `defer_loading` and
  `tool_reference`. Where it is missing, a small tool set loads upfront.
  Appending tools to the array mid-run on such a provider would invalidate
  the cache, so Forge should not do it; reveal by upfront load or by a new
  run (the escalation path) instead.
- **Cheap models and search.** Haiku 4.5 and 5.5 are on the supported list.
  The advisor docs show Haiku under-calls optional tools, and the same risk
  applies to searching. Keep the quick-answer core non-deferred (3–5 tools)
  and use harness pushes for what the cheap model must not miss.
- **Sub-agents load independently.** Claude Code's workflow note says
  schemas "load on demand per agent", so a delegate does not inherit the
  parent's loaded set. The same would apply to Forge's `Task` children.
- **A rule to add to the design:** the tools array and the system prompt are
  fixed for a run; anything that changes during a run goes in messages. This
  generalises OpenClaw's "prompt-state mutations default to deferred
  invalidation" (`agent-context-compaction.md` §7) from a rule about
  skills and memory to the whole tool surface.

## 5. Other providers (added 2026-10-22)

**OpenAI (Responses API, `gpt-5.4` and later).** Source: the
[tool search guide](https://developers.openai.com/api/docs/guides/tools-tool-search).
Add `{"type": "tool_search"}` to `tools` and set `defer_loading: true` on
functions or MCP servers. Differences from Anthropic's:

- **Namespaces are the unit.** Before loading, the model sees only a
  namespace's name and description; `defer_loading` applies to the functions
  inside. OpenAI says its models are trained mainly on namespaces and MCP
  servers and advises under 10 functions per namespace.
- **Two modes.** *Hosted* (`execution: "server"`): OpenAI searches the tools
  declared in the request. *Client-executed* (`execution: "client"`): the
  model emits a `tool_search_call` with a `call_id` and a `goal`, the
  application looks the tools up and returns a `tool_search_output`. The
  docs state client mode "can also return tools that weren't in the original
  request", so the registered set is not fixed up front.
- **Cache.** Discovered tools are "injected at the end of the context window";
  "changing the loaded tool set partway through a conversation breaks the
  cache from that point on". An `additional_tools` input item with
  `role: "developer"` makes tools callable from a specific point, and its
  position must be preserved when round-tripping.
- Not documented for Chat Completions. Codex has its own client-side BM25
  `tool_search` (`codex/README.md`).

**Bedrock `Converse`.** No server-side deferral (the Anthropic docs say
`InvokeModel` only). Forge on Converse has three honest options:

1. **Load a small core upfront.** The cheap-start set is 3–4 tools, so the
   cost is small.
2. **Hand off at a run boundary.** `HandOff` ends the run with a handoff and the
   next run starts with a different tools array (and a higher tier). A new
   run has no cache to lose, and Forge's runs are one-shot already. This is
   the default for big runs. For a small economy run, `Expand` may instead
   grow the array once, to a fixed bundle, and take one cache miss on a small
   prefix (`agent-design/models.md` §4a).
3. **A fixed `CallTool(name, args)` dispatcher** with schemas delivered as text
   in a tool result. The array never changes, but the harness validates
   arguments itself and the model loses native schema enforcement, which a
   cheap model feels most. Use only if mid-run expansion is needed.

*Not verified:* how Bedrock orders and invalidates cache checkpoints for
`toolConfig` changes. Assume the same tools → system → messages prefix
order until checked.
