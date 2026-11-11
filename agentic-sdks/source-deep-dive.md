<!-- Pandoc conversion of ../agentic_sdks_mcp_deep_dive.docx (added to the repo by Jonathan, 2026-11-11), kept so the text can be diffed and cited. The .docx is the original. -->

# Executive assessment

**Thesis.** The main design decision is no longer which Python package
supplies an LLM tool-calling loop. It is which layer owns execution,
context, capability discovery, durability and security. Deep Agents is
compelling because it offers a reusable *agent harness* with a virtual
filesystem, context compression, subagent delegation and progressive
disclosure, while remaining model-agnostic. The practical MCP advantage
arises from combining that harness with LangChain's evolving MCP adapter
and tool-selection middleware---not from MCP alone. \[1--5\]

**Recommendations.** For application APIs, typed data and relatively
bounded agents, start with **Pydantic AI** or **OpenAI Agents SDK**. For
explicit, recoverable orchestration, use **LangGraph**. For long-running
filesystem- and tool-heavy work, evaluate **Deep Agents** alongside
**Claude Agent SDK**. Use **Deep Agents Code (**`dcode`**)** as a
ready-made coding agent and, potentially more valuable, as a reference
implementation of the harness. When deploying across many MCP servers,
use a layered design: *authorised catalog → dynamic discovery/deferral →
compact model-visible results → separately retained artifacts*. \[1,
6--9\]

**Bottom line.** The interesting LangChain innovation is not a single
API. It is that tool-schema pressure, tool-result pressure and
long-horizon state are addressed by three different, composable
mechanisms. This also creates configuration complexity and surprising
failure modes: a tool can be discovered yet still unavailable to the
model; a file can be visible to the agent yet ephemeral; an interrupted
operation can execute again after resumption. \[2--5\]

## Reading guide and evidence standard

This report distinguishes **documented behaviour** from **design
recommendation** and **inference**. It reflects public documentation and
project releases checked on **10 November 2026**. The MCP adapter
namespace is marked **beta** in the current LangChain documentation and
may change. Exact model identifiers, version gates and transport
behaviour should be checked against installed versions before
deployment. Benchmark scores below are historical and should not be
treated as cross-model rankings. \[3, 5, 10\]

# 1. The taxonomy: framework, runtime, harness, protocol

Four categories routinely get conflated.

-   **Agent SDK/framework:** provides a model loop, tools, prompts,
    typed inputs/outputs, and hooks. Examples: Pydantic AI, OpenAI
    Agents SDK, LangChain `create_agent`.
-   **Workflow runtime:** owns durable state transitions, checkpoints,
    interrupts, resumability and branch execution. LangGraph is the
    obvious Python example; Temporal, DBOS or Restate can serve similar
    purposes with different guarantees.
-   **Agent harness:** supplies working strategies above the loop:
    shell/filesystem tools, context offloading, memory, skills,
    subagents, model-specific profiles and approval surfaces. Deep
    Agents, Claude Agent SDK, and newer Pydantic AI Harness and
    Microsoft Harness Agent belong in this category.
-   **Interoperability protocol:** MCP describes how clients discover
    and invoke server-provided tools and other context capabilities. It
    is not, by itself, a scheduler, sandbox, memory store, permission
    system or context-window optimizer. \[1, 6--9, 11\]

A robust architecture can use all four: MCP for external capabilities,
an SDK/harness for agent decision-making, a workflow runtime for
resumability, and an execution sandbox or service boundary for side
effects.

## 1.1 Python landscape at a glance

  ---------------------------------------------------------------------------------
  **Offering**      **Primary             **Best fit**            **Principal
                    abstraction**                                 trade-off**
  ----------------- --------------------- ----------------------- -----------------
  LangChain         Minimal agent +       General tool-using      Long-horizon
  `create_agent`    middleware            agents                  behaviour is
                                                                  assembled
                                                                  separately

  LangGraph         Graph execution       Recovery, branching,    More
                    runtime               approvals, explicit     infrastructure
                                          state                   and graph design

  Deep Agents SDK   Opinionated harness   Long tasks,             Complex
                    over                  context-heavy tools,    interaction among
                    LangChain/LangGraph   files, delegation       middleware and
                                                                  backends

  Deep Agents Code  Finished terminal     Coding, reference       CLI-product
                    coding agent          harness, shell + MCP    conventions; not
                                                                  an SDK substitute

  Claude Agent SDK  Claude Code harness   Autonomous coding and   Claude-centric;
                    as Python/TS library  computer workflows      runtime
                                                                  integration and
                                                                  isolation

  Pydantic AI       Typed agent SDK,      Python services,        Choose and
                    durable integrations  structured outputs,     compose the
                    and harness features  testable interfaces     higher-level
                                                                  capabilities

  OpenAI Agents SDK Runner, tools,        Straightforward         Less explicit
                    handoffs, tracing and application agents      workflow control
                    MCP                                           than LangGraph

  Google ADK        Agents,               Google-oriented         More platform
                    graph/parallel        applications            surface and
                    workflows, runtime                            architectural
                                                                  options

  Microsoft Agent   Agents, workflows and Azure/.NET/Python       Large and
  Framework         harness               enterprise stacks       still-evolving
                                                                  abstraction
                                                                  surface

  CrewAI            Crews, role           Role-based              Role
                    orchestration and     collaboration           proliferation can
                    flows                                         create
                                                                  unnecessary agent
                                                                  hops

  LlamaIndex        Retrieval, data       Document/data-centric   Less central when
                    tooling and agents    agents                  retrieval is not
                                                                  the problem
  ---------------------------------------------------------------------------------

**Caution:** These are architectural fit judgments, not controlled
benchmarks. Current Pydantic AI and Microsoft offerings include harness
features; the old shorthand that only Claude or Deep Agents supply a
harness is outdated. \[6--9, 11--14\]

# 2. The LangChain stack: what owns what?

Think of the ecosystem as layered rather than as competing brand names:

>     Your application / frontend / policy
>                      |
>            Deep Agents harness                 dcode (terminal product)
>            skills, files, subagents            TUI, sessions, CLI, MCP config
>                      |                              |
>            LangChain create_agent <-------------- SDK
>            model, tools, middleware
>                      |
>            LangGraph runtime
>            state, checkpoint, streaming, interrupts
>                      |
>            Model APIs | MCP servers | backend storage | sandbox
>                      |
>            LangSmith (observability / evals / deployment)

**LangChain** supplies model/tool interfaces and middleware.
**LangGraph** supplies execution semantics and state. **Deep Agents**
configures a higher-level harness using those layers. **Deep Agents
Code** packages it into a terminal product. **LangSmith** offers
tracing, evaluation and deployment options; **Managed Deep Agents** adds
managed runtime infrastructure. None of these layers makes an external
MCP server trustworthy. \[1, 2, 15\]

### Deep Agents' key concepts

1.  **Filesystem as context infrastructure.** Agent-visible `ls`,
    `read_file`, `write_file`, `edit_file`, `glob`, `grep` and related
    operations are mounted against a backend abstraction, not
    necessarily the host disk. The model can progressively inspect
    material without reading it all into the prompt. \[2, 4\]
2.  **Subagents as context boundaries.** A supervisor delegates work to
    isolated workers; each worker can consume extensive tool output
    while returning a concise synthesis. The newer system also documents
    forked, asynchronous and dynamic subagent patterns. \[1, 16\]
3.  **Skills and memory are different.** Skills provide on-demand
    procedural instructions (and optionally tools). Memory is retained
    context. Both can be expressed as files but have different loading
    semantics. \[2, 17\]
4.  **Middleware owns behaviours.** Summarisation, offloading, tool
    selection, tool retries, approvals, call budgets and
    provider-specific affordances are separate interventions around
    agent/model/tool calls. \[4, 5\]
5.  **Execution backends are swappable.** The same logical path may map
    to thread state, a persistent store, a real directory, or a remote
    sandbox. This is powerful---and a source of persistence
    misunderstandings. \[4\]

## 2.1 The filesystem is not necessarily a filesystem

The default `StateBackend` is *thread-scoped virtual state*. Files
persist across turns only insofar as the thread's state is retained
through its checkpointer; they are not automatically ordinary files on
the developer's disk. A `FilesystemBackend` maps file operations to a
configured real directory. A `StoreBackend` gives cross-thread
persistence when backed by suitable storage. A `CompositeBackend` routes
prefixes to different backends; sandbox backends can additionally offer
execution. \[4\]

For example, use `/workspace/` for real project files, `/memories/` for
durable cross-thread state and `/large_tool_results/` for transient
internal context. Routing all paths to the current directory is rarely a
good default: it mixes private internal artifacts with project files and
risks leaking data into git or backup systems. \[4\]

## 2.2 Context compression: two distinct operations

**Offloading** handles excess content: current documentation gives a
default threshold of **20,000 tokens** for large tool results and tool
inputs. For oversized results, Deep Agents stores the full content in
its configured backend and returns a path plus an initial **10-line
preview** to the model. The agent can later `grep` or `read_file`
relevant sections. Oversized file-write inputs have a different
truncation path, involving older history as context pressure rises.
\[2\]

**Summarisation** handles accumulated *conversation history*. At a
context threshold (illustratively 85% of model input context),
`SummarizationMiddleware` replaces older model-visible history with an
LLM-generated summary, while preserving an archive in the filesystem and
keeping persisted state history available for replay. These are not
interchangeable operations. \[2\]

**Limit:** The original MCP response still traverses the MCP transport
and reaches the Python process before offloading. Automatic offloading
reduces **future LLM context**, not network bytes, transient RAM, server
work or data-access risk. Large multimodal payloads may need separately
designed retention and retrieval. \[2, 3\]

# 3. MCP fundamentals: what it can and cannot do

MCP defines capabilities exposed by a server and consumed by a client.
In an agent application, server tools become agent-callable operations,
usually with JSON-schema inputs and structured or unstructured outputs.
MCP also defines resources, prompts and client/server interaction
patterns, but a given framework adapter may implement only a subset of
the protocol surface. Do not assume that connecting a server
automatically exposes all MCP prompts, resources, sampling or roots as
normal tools. \[3, 18\]

A standard Deep Agents MCP pipeline looks like this:

>     MCP server(s)
>       └─ tool catalog + schemas + call results
>               ↓
>     LangChain MCPAdapter / FastMCP client
>       └─ adapted LangChain tool objects
>               ↓
>     Discovery and selection / deferral middleware
>       └─ only authorised/relevant tool schemas reach model
>               ↓
>     Deep Agents model → tool call → Python execution
>               ↓
>     ToolMessage: visible content + optional artifact + status
>               ↓
>     Context offload, approval, tracing, further reasoning

The newly documented `langchain.mcp.MCPAdapter` requires
`langchain[mcp]>=1.4.0` and is currently **beta**. It uses FastMCP for
underlying connection management, authentication and protocol
negotiation. Older deployments may use the separately packaged
`langchain-mcp-adapters`; code samples should not silently mix the two
APIs. \[3, 19\]

# 4. Tool explosion: discovery, deferral and progressive disclosure

**Tool discovery** means learning which tools exist. **Tool deferral**
means not sending their complete schemas to the model until needed.
**Tool selection** means choosing a small active subset. A system may do
one without the other.

## 4.1 Provider-native tool search

LangChain exposes `ProviderToolSearchMiddleware`: tools named in
`searchable_tools`, or marked with `extras={"defer_loading": True}`, are
hidden initially and surfaced through the provider's server-side tool
search. Current LangChain documentation lists compatible Anthropic
Claude Sonnet 4+/Opus 4+/Haiku 4.5+ and OpenAI GPT-5.5+ families; other
providers raise an error. The tool schemas are still discovered in
Python and must be filtered for access rights. \[5\]

**What it buys you:** lower prompt-schema overhead when many MCP servers
offer overlapping APIs, and potentially better selection precision.
**What it does not buy:** provider portability, automatic authorisation,
zero-cost search, or a guarantee that the model finds the right tool.
Test recall as well as token savings.

## 4.2 Model-independent selection fallback

`LLMToolSelectorMiddleware` uses an LLM to choose a bounded active set
of tools before a main model call (for example `max_tools=3` with an
`always_include` allowlist). This is broader in model compatibility, but
incurs an additional inference, and tool descriptions may still be
represented in the selector's input. It trades latency/cost for a
smaller main-agent schema. \[5\]

A third option is **explicit capability routing**: choose server/tool
bundles based on a trusted user role and task classification before
constructing the agent. This is less glamorous than semantic discovery
and often preferable for a strict enterprise permission model.

## 4.3 Skill-scoped tools: more interesting than generic search

Skills add *semantic activation*: the agent first sees a compact skill
description and reads the relevant `SKILL.md` only when needed. In
recent Deep Agents, `metadata.include_tools` gates associated tools
until the skill is read. The value is a **space-separated string**, not
a YAML array. `SkillsMiddleware` can resolve friendly logical names to
dynamically named MCP tools (and can return multiple MCP tools for one
alias). The documentation gives a `deepagents>=0.7.22` minimum for skill
tools. \[17\]

>     ---
>     name: incident-triage
>     description: Investigate production incidents and correlate alerts with deploys.
>     metadata:
>       include_tools: incident_read deploy_lookup log_search
>     ---
>     Use read-only evidence tools first. Do not restart services without approval.

**Practical advantages:** workflows can advertise a capability without
exposing every underlying implementation; permissions and per-user
catalogs can be applied when resolving tools; different servers can
implement the same logical skill. **Important nuance:** adding a skill
or disclosing an MCP tool is *not* permission enforcement. Server-side
authorisation still matters. Tool availability can also change after
conversation summarisation, so test the reactivation path. \[17\]

## 4.4 What dcode adds

`dcode` automatically discovers `.mcp.json` configurations at user and
project scope, connects servers, lists tool status with `/mcp`, supports
OAuth and project-level trust controls, and runs the agent from a
terminal interface. Its **2 November 2026 v0.2.3 changelog explicitly
adds MCP tool-schema deferral through provider-native tool search**. Its
23 October v0.2.1 release added skill-scoped MCP tools. These are *dcode
product features*, not evidence that all configurations of the bare SDK
automatically defer every MCP schema. \[10, 20\]

# 5. Large MCP results: four different data paths

Consider a database MCP tool returning 50,000 rows. The obvious
implementation returns a giant JSON string to the model. It is usually
the wrong abstraction. There are four better approaches, serving
different purposes.

  -----------------------------------------------------------------------------------------------------------
  **Technique**            **What model   **Where full data        **Good for**            **Limits**
                           sees**         lives**                                          
  ------------------------ -------------- ------------------------ ----------------------- ------------------
  Server-side              Compact query  MCP server/database      Almost every large      Requires server
  pagination/aggregation   results                                 dataset                 API design

  Deep Agents automatic    Path + preview Configured backend       Oversized textual tool  Threshold-based;
  offload                                                          result                  result enters
                                                                                           Python first

  MCP `structuredContent`  Chosen visible `ToolMessage.artifact`   Machine-readable return Artifact
  → artifact               content        in app state             values                  availability is
                                                                                           not durable blob
                                                                                           storage

  Explicit artifact handle Summary +      Dedicated artifact       Huge/binary/sensitive   Must implement
  / object store           URI/opaque id  service                  outputs                 access control and
                                                                                           expiry
  -----------------------------------------------------------------------------------------------------------

LangChain's MCP adapter maps **model-visible MCP content** to standard
content blocks and attaches MCP `structuredContent` to a
`ToolMessage.artifact` rather than automatically turning it all into
model-visible text. The application can inspect the structured artifact
after execution. This is separate from the Deep Agents large-tool-output
middleware. \[19\]

### Recommended interface for an expensive MCP query

Instead of `query_database() -> giant_json`, return a compact result
contract: record count, schema, query id, 10--20 sample rows, an opaque
artifact id, expiry, and narrow follow-up operations such as
`inspect_result`, `aggregate_result` and `get_rows(offset, limit)`.
Store full results on the server or in an authorised object store. This
eliminates model-context pressure *and* avoids transferring enormous
payloads to Python in the first place.

**Do not confuse** a virtual path such as `/large_tool_results/...` with
a durable URL. A model-only filesystem reference has neither external
sharing semantics nor guaranteed lifetime. Choose persistence according
to auditability, sensitivity and volume. \[2, 4\]

# 6. Advanced MCP integration features and caveats

## 6.1 Multiple servers, namespacing, transport and discovery cache

`MCPAdapter` can use one server, an MCP configuration fleet, or a
FastMCP `ClientGroup`. Separate clients let distinct servers have
independent authentication and protocol negotiation; namespacing
prevents duplicate tool names such as `search`. The documentation also
discusses shared HTTP connection pooling and tool-catalog caching with
`list_tools(cache_mode=...)`. Caching respects supported server hints
and must be partitioned by principal. \[21\]

Important operational distinction: most adapted tools are **re-entrant**
and may open a client connection for each invocation. A supposedly
"connected" server does not imply a persistent session across all calls.
If a tool needs continuity, explicitly manage it and test what happens
on reconnect. Modern and legacy MCP servers can have different protocol
negotiation paths, requiring separate clients rather than forcing one
common mode. \[21\]

## 6.2 Human-in-the-loop through MCP annotations

MCP tool metadata may include `read_only_hint` or `destructive_hint`;
LangChain exposes these hints in tool metadata. Middleware can use them
to request approval for potentially dangerous calls. This is useful for
automatic policy *suggestions*, but server metadata is not a trust
boundary: the server can misclassify its own tool. Use an independent
policy keyed by identity, action, resource and arguments, and enforce it
again server-side. \[19, 22\]

## 6.3 Elicitation becomes a LangGraph interrupt

When an MCP server requests user input during a tool call, the LangChain
adapter can surface **elicitation** as a LangGraph `interrupt`. The app
displays the request, saves state, then resumes with
`Command(resume=...)` and the matching `thread_id`. This creates a
natural UI integration for user-facing approval/input requests. \[19\]

The documented caveat is significant: resuming an elicitation **reruns
the tool from the beginning**. Any action taken *before* elicitation can
repeat. Put confirmation before irreversible work, assign idempotency
keys, and record completed side effects independently of conversation
state. Also note that modern sessionless MCP handling **does not
automatically support sampling or roots requests** over the same
mechanism: the adapter documents errors for those unsupported requests.
\[19\]

## 6.4 Multimodality, errors, and status

An MCP image or file content block can become a LangChain `image` or
`file` block visible to a suitable model. A server-reported
`isError=True` becomes a tool message with error status, allowing the
agent to diagnose and retry. Large-image handling is not equivalent to
the text offloading policy; retaining images externally and giving tools
for crop, inspect and extract is a separate design task. \[2, 19\]

## 6.5 MCP trust boundaries

Three surfaces need isolation: **MCP servers** (API permissions and data
egress); **tool content** (untrusted data capable of prompt injection);
and **execution** (shell/filesystem access in the agent sandbox).
Project `.mcp.json` is particularly sensitive because it can spawn local
commands or interpolate environment variables into headers. `dcode`
implements project-level trust gates; an SDK deployment must implement
its own equivalent if it accepts user-supplied server configuration.
\[20, 23\]

# 7. Reference Python patterns

The following examples use the **new beta** `langchain.mcp` API, not the
legacy adapters package. They are representative code patterns derived
from current documentation; version-pin and integration-test before
production use.

## 7.1 MCP + Deep Agents + provider tool search

>     import asyncio
>     from deepagents import create_deep_agent
>     from langchain.mcp import MCPAdapter
>     from langchain.agents.middleware import ProviderToolSearchMiddleware
>
>     async def main():
>         async with MCPAdapter("https://docs.langchain.com/mcp") as adapter:
>             tools = await adapter.list_tools()
>             agent = create_deep_agent(
>                 model="anthropic:claude-sonnet-5",
>                 tools=tools,
>                 middleware=[
>                     ProviderToolSearchMiddleware(
>                         searchable_tools=[t.name for t in tools]
>                     )
>                 ],
>             )
>             result = await agent.ainvoke({
>                 "messages": [{"role": "user", "content":
>                               "Compare LangGraph checkpoint backends"}]
>             })
>             print(result["messages"][-1].content)
>
>     asyncio.run(main())

This discovers the schemas in Python but defers their provider-side
availability; it does *not* dynamically provision new MCP servers,
enforce least privilege, or guarantee that every tool is appropriate for
the user. For large fleets, filter by principal **before** constructing
`tools`. \[3, 5\]

## 7.2 Keep project files and internal results separate

>     from deepagents import create_deep_agent
>     from deepagents.backends import (
>         CompositeBackend, StateBackend, FilesystemBackend
>     )
>
>     agent = create_deep_agent(
>         model="anthropic:claude-sonnet-5",
>         backend=CompositeBackend(
>             default=StateBackend(),
>             routes={
>                 "/workspace/": FilesystemBackend(
>                     root_dir="/srv/agent-workspace", virtual_mode=True
>                 )
>             },
>         ),
>     )

In this configuration, `/workspace/` maps to real disk and internal
paths remain thread-scoped virtual state. For durable audit artifacts,
introduce a separately managed storage backend; do not assume
`StateBackend()` is durable in the absence of an appropriate
checkpointer. \[4\]

## 7.3 A defensible MCP output contract

>     # Illustrative MCP server-side response schema (not a library API)
>     {
>       "summary": "12,481 matching records",
>       "columns": ["timestamp", "service", "error_code"],
>       "sample": [{"service": "api", "error_code": "E504"}],
>       "artifact_id": "query_opaque_4f91",
>       "expires_at": "2026-11-10T12:00:00Z",
>       "next": ["aggregate_result", "get_rows", "inspect_result"]
>     }

The agent receives compact context; the app retains a typed artifact;
the server controls retrieval, pagination and access. For high-stakes
data, the result handle should be tenant-bound and non-guessable.
Reauthorisation must happen on every follow-up request.

# 8. Deep Agents Code vs Claude Code / Claude Agent SDK

The product comparison is more meaningful if held at the same level:
**Deep Agents Code vs Claude Code** as end-user coding agents, or **Deep
Agents SDK vs Claude Agent SDK** as embeddable harnesses.

  -------------------------------------------------------------------------
  **Dimension**           **Deep Agents SDK /     **Claude Agent SDK /
                          dcode**                 Claude Code**
  ----------------------- ----------------------- -------------------------
  Runtime                 Python LangChain +      Claude Code's agent loop,
                          LangGraph; dcode adds   exposed through SDK
                          TUI and local server    
                          process                 

  Models                  Broad provider and      Claude family across
                          local/open-weight       supported Anthropic/cloud
                          support                 routes

  Files                   Virtual, local, store,  Working directory in
                          sandbox/custom backend  agent execution
                                                  environment

  MCP                     LangChain MCPAdapter;   Built-in MCP connectivity
                          dcode config, trust and and provider-specific
                          OAuth                   tool search

  Progressive disclosure  Skills, skill-scoped    Skills and tool search in
                          tools, provider tool    Claude harness
                          search                  

  Durable state           LangGraph checkpoints,  Session
                          storage backends        persistence/resumption;
                                                  operational semantics
                                                  differ

  Control                 Middleware,             Hooks, permissions, SDK
                          source-level harness    integration; core harness
                          changes, backend swaps  less open

  Strongest case          Custom, model-agnostic  Mature Claude-centric
                          applications and        coding/autonomy workflows
                          harness experiments     
  -------------------------------------------------------------------------

**Judgment:** Claude Agent SDK offers a deeply integrated and relatively
cohesive harness; Deep Agents gives more architectural degrees of
freedom and better inspectability. That flexibility imposes the usual
tax: you own the quality of integrations, sandbox, permissions and
model-specific tuning. The LangChain comparison page is authored by
LangChain, so treat its comparative framing as vendor perspective, not
independent measurement. \[1, 7, 24\]

# 9. Benchmark evidence: what Terminal-Bench actually tells us

The clearest published Deep Agents Code-era numbers concern
**Terminal-Bench 2.0**, an older 89-task benchmark. In December 2025
LangChain reported Deep Agents CLI with Claude Sonnet 4.5 at **44.9% and
40.4%** across two trials (**42.65% mean**), describing the result as
comparable to Claude Code on that vintage benchmark. In February 2026
LangChain reported raising its GPT-5.2-Codex configuration from **52.8%
to 66.5%** using harness-only changes. \[25, 26\]

The 13.7-point increase is valuable evidence that harness design
matters. Reported interventions included richer environment context,
explicit testing/verification guidance, time budgeting, error-pattern
analysis and variable reasoning effort. Constant maximum reasoning
effort performed worse under timeout constraints than a more adaptive
allocation. \[26\]

**What it does not prove:** that Deep Agents is currently the best
coding agent, or that one harness beats another after holding the model,
task set, compute, costs, tool access and repeat count fixed. Do not
compare historical Terminal-Bench 2.0 percentages directly to current
Terminal-Bench 4.1. A score from one provider/model and a different
score from another are not a controlled harness comparison. \[25--27\]

### Better internal evaluation plan

-   Fix identical model and model-version, task set, environment
    snapshot, timeout, budget and run count.
-   Compare *bare agent*, *Deep Agents default*, *Deep Agents with
    deferred MCP*, *Deep Agents with server-side pagination*, and
    *dcode* where appropriate.
-   Measure solve rate, total token input (including tool schemas), p95
    time, MCP discovery latency, selection recall, repeated calls,
    offloaded-result retrieval success, cost and policy violations.
-   Include deliberately hostile MCP outputs, stale catalog entries,
    large binary payloads, network resets, user-input interrupts and
    resumption after a side effect.

# 10. Production design for a large MCP estate

For 20--200 MCP tools spread over internal services, the safest
architecture is a small *trusted control plane* around an agent, not an
unbounded catalog directly connected to a powerful model.

>     User identity and request
>            |
>     Policy + catalog registry  -----> authorised MCP server/tool IDs
>            |                                    |
>     Capability router                    auth / pooling / discovery cache
>            |                                    |
>     Deep Agents (small permanent tool set) <---- filtered, deferred schemas
>            |
>     Model calls + MCP invocation
>            |
>     Result normaliser ----> artifact store / state / database
>            |                  (tenant, TTL, audit, encryption)
>     Preview + query id
>            |
>     Subagents / selective reads / synthesis
>            |
>     Validation + approval gates --> effectful tools

### Design rules

1.  **Keep a small permanent core**: catalog/search, inspect artifact,
    read paginated output, request approval. Everything else is eligible
    for capability activation.
2.  **Separate discovery from authorisation.** Tools must be filtered by
    caller and tenant *before* becoming model-visible, including when a
    skill dynamically resolves its tool names.
3.  **Optimise at the source.** Prefer server-side filtering,
    aggregation and pagination before relying on the 20,000-token
    offloader.
4.  **Treat artifacts as first-class application data.** Store origin
    server, identity, timestamp, schema, content hash, expiry and
    retention class. A virtual file path alone is not an audit artifact.
5.  **Make side effects idempotent.** For elicitation, retries, timeouts
    and graph resumption, use stable operation IDs and an external
    record of completed work.
6.  **Use bounded subagents.** Give investigators read-only tools;
    reserve destructive mutations for a small, separately approved path.
7.  **Log decision quality, not just LLM output.** Capture catalog size,
    deferred schema tokens, chosen tools, offload trigger, file
    retrieval and retries. Redact secrets and sensitive MCP payloads in
    traces.
8.  **Sandbox executable code.** Deep Agents' logical filesystem API and
    a remote execution container solve different problems; neither
    automatically secures an untrusted MCP server.

# 11. Where Deep Agents is genuinely innovative---and where it is not

**Differentiators worth attention**

-   Filesystem-mediated context engineering is a consistent mechanism
    shared by tools, memory and subagents, not a one-off "summarise long
    text" helper.
-   Skill-scoped tools create a second dimension of progressive
    disclosure beyond provider search: *capability relevance* can
    determine *schema exposure*.
-   Provider-native search, LLM selector fallback and deterministic
    filtering can coexist. This permits experimenting with
    tool-selection cost, latency and recall.
-   Model profiles and middleware make harness tuning inspectable;
    Terminal-Bench work shows the magnitude of the potential performance
    effect.
-   dcode exposes a realistic integrated product with sessions, config,
    MCP trust gates, shell, skills, sandboxes and debugging tools. \[2,
    5, 10, 17, 26\]

**Not unique / not solved**

-   MCP discovery and OAuth are protocol/client capabilities; many SDKs
    support them.
-   Tool-result offloading does not solve oversized transport, binary
    retention, prompt injection, long-term permissioning or server-side
    authorisation.
-   Stateful workflow execution, exactly-once side effects and business
    transaction semantics remain application/runtime concerns.
-   Model agnosticism is imperfect: native tool-search providers,
    reasoning effort controls, caching and skill-tool injection differ
    materially by model.
-   Pydantic AI, Microsoft Agent Framework and Claude's SDK now compete
    more directly in the harness space than older comparison matrices
    suggest. \[5--9, 11, 19\]

# 12. Practical selection matrix

  ------------------------------------------------------------------------------
  **Your project**               **Start here**          **Add when required**
  ------------------------------ ----------------------- -----------------------
  Typed application service, few Pydantic AI             MCP integration,
  dozen tools                                            durable workflow
                                                         orchestration

  OpenAI-centric API agent with  OpenAI Agents SDK       MCP, tracing, separate
  handoffs                                               worker for long jobs

  Explicit                       LangGraph               Deep Agents harness for
  recovery/approvals/branching                           long context-heavy
                                                         steps

  Heavy research across many MCP Deep Agents SDK         Tool search,
  servers                                                skill-scoped tools,
                                                         object-store artifacts

  Coding agent with portable     dcode                   Sandboxing, project MCP
  models                                                 trust, controlled
                                                         evaluation

  Claude-first autonomous coding Claude Agent SDK        Strong isolation,
                                                         permissions and
                                                         execution oversight

  Regulated enterprise           Workflow engine +       Human approval,
  transactions                   constrained SDK         server-side
                                                         authorisation, audit
                                                         log
  ------------------------------------------------------------------------------

**Final recommendation.** For an MCP-heavy Python system, prototype
**Deep Agents +** `MCPAdapter` **+** `ProviderToolSearchMiddleware`,
plus a test harness measuring real tool-schema savings and selection
quality. Use skill-scoped capability activation where domain boundaries
are meaningful, and redesign the largest MCP tools to return compact
handles and server-side query operations. Do not treat offloading,
schema deferral or an agent filesystem as substitutes for security and
reliable business execution.

# Sources and further reading

Numbers refer to public documentation or primary project publications;
vendor comparisons and self-reported benchmarks are labelled as such in
the text.

\[1\] LangChain, *Deep Agents overview*.
<https://docs.langchain.com/oss/python/deepagents/overview>

\[2\] LangChain, *Context engineering in Deep Agents*.
<https://docs.langchain.com/oss/python/deepagents/context-engineering>

\[3\] LangChain, *MCP overview (new MCPAdapter beta)*.
<https://docs.langchain.com/oss/python/langchain/mcp>

\[4\] LangChain, *Deep Agents filesystem backends*.
<https://docs.langchain.com/oss/python/deepagents/backends>

\[5\] LangChain, *Prebuilt middleware: provider tool search / LLM
selector / filesystem*.
<https://docs.langchain.com/oss/python/langchain/middleware/built-in>

\[6\] Pydantic, *Pydantic AI overview / harness*.
<https://pydantic.dev/docs/ai/overview/>;
<https://pydantic.dev/docs/ai/harness/>

\[7\] Anthropic, *Claude Agent SDK overview*.
<https://code.claude.com/docs/en/agent-sdk/overview>

\[8\] OpenAI, *Agents SDK quickstart / MCP*.
<https://openai.github.io/openai-agents-python/quickstart/>;
<https://openai.github.io/openai-agents-python/mcp/>

\[9\] Google, *Agent Development Kit*. <https://adk.dev/>

\[10\] LangChain, *Deep Agents Code changelog*, including v0.2.3.
<https://github.com/langchain-ai/deepagents/blob/main/libs/code/CHANGELOG.md>

\[11\] Microsoft, *Microsoft Agent Framework overview*.
<https://learn.microsoft.com/en-us/agent-framework/overview/>

\[12\] CrewAI, *Introduction and MCP integration*.
<https://docs.crewai.com/en/introduction>

\[13\] LlamaIndex, *Framework overview*.
<https://developers.llamaindex.ai/python/framework/>

\[14\] Pydantic, *Deferred tools*.
<https://pydantic.dev/docs/ai/tools-toolsets/deferred-tools/>

\[15\] LangChain, *Deep Agents monorepo README*.
<https://github.com/langchain-ai/deepagents>

\[16\] LangChain, *Subagents*.
<https://docs.langchain.com/oss/python/deepagents/subagents>

\[17\] LangChain, *Deep Agents skills and skill tools*.
<https://docs.langchain.com/oss/python/deepagents/skills>

\[18\] Model Context Protocol, *Official specification and protocol
concepts*. <https://modelcontextprotocol.io/>

\[19\] LangChain, *MCP tools: outputs, artifacts, annotations,
elicitation*.
<https://docs.langchain.com/oss/python/langchain/mcp/tools>

\[20\] LangChain, *Deep Agents Code MCP tools and trust*.
<https://docs.langchain.com/oss/deepagents/code/mcp-tools>

\[21\] LangChain, *MCP connections, caching, pooling and protocol eras*.
<https://docs.langchain.com/oss/python/langchain/mcp/connections>

\[22\] LangChain, *Human-in-the-loop*.
<https://docs.langchain.com/oss/python/deepagents/human-in-the-loop>

\[23\] LangChain, *dcode threat model*.
<https://github.com/langchain-ai/deepagents/blob/main/libs/code/THREAT_MODEL.md>

\[24\] LangChain, *Deep Agents comparison with Claude Agent SDK* (vendor
comparison).
<https://docs.langchain.com/oss/python/deepagents/comparison>

\[25\] LangChain, *Evaluating Deep Agents CLI on Terminal Bench 2.0* (5
December 2025).
<https://www.langchain.com/blog/evaluating-deepagents-cli-on-terminal-bench-2-0>

\[26\] LangChain, *Improving Deep Agents with harness engineering* (17
February 2026).
<https://www.langchain.com/blog/improving-deep-agents-with-harness-engineering>

\[27\] Terminal-Bench, *Official benchmark site* (benchmark version must
be checked). <https://www.tbench.ai/>
