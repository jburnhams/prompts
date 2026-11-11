# The other SDKs the deep dive names

Read 2026-11-11. SHAs in [`../sources.md`](../sources.md). Each section
says what the SDK adds to what this collection already had, and stops
there; none of them needed a folder of its own.

## 1. OpenAI Agents SDK (`openai/openai-agents-python`, 0.24.0)

The deep dive files it under "straightforward application agents". The
current SDK is more than that: it has a **sandbox agent** harness.

- **`SandboxAgent` + `Manifest`** (`docs/sandbox_agents.md`,
  `docs/sandbox/guide.md`): the workspace is declared as data. A
  manifest lists entries (local directories, files, git repos, mounts)
  with Unix permissions and the sandbox `User`s that exist; `run_as`
  picks the identity model-facing tools run under. `SnapshotSpec` and
  session state let a later run resume the same workspace. Clients run
  it locally (with a warning: on Linux `UnixLocalSandboxClient` "adds no
  OS-level confinement"), in Docker, or on hosted sandboxes. This is the
  closest any SDK comes to Keel's `workspace` block in a `RunSpec`
  (`../agent-design/keel/run-spec.md` §3).
- **Skills load lazily from a host directory or git** and are copied into
  the sandbox only when requested.
- **Memory** (`docs/sandbox/memory.md`): a run segment is appended to a
  conversation file; when the sandbox session closes, phase 1 extracts a
  summary and raw notes per conversation and phase 2 consolidates them
  into `MEMORY.md` and a short `memory_summary.md` that is injected at
  the next start. Reads are progressive: summary, then index, then the
  rollout summaries. `Memory(generate=None)` is recommended for
  "subagents, checkers, or one-off tool agents" that "do not add much
  signal". The Keel memory proposal (`../agent-design/keel/memory.md`)
  already covers this shape.
- **Approvals fail closed on unreadable arguments** (`docs/human_in_the_loop.md`):
  a callable `needs_approval` rule is *not called* when the arguments are
  missing, empty, whitespace, malformed JSON, a JSON non-object, or
  contain `NaN`/`Infinity`; the call goes to manual approval. A paused
  run serialises as `RunState` and resumes after decisions, across
  handoffs and nested `Agent.as_tool()` runs.
- **Guardrails** are input, output and tool guardrails. A tripwire
  raises and halts the run. Tool input guardrails normally run *after*
  approval; `pre_approval_tool_input_guardrails=True` runs them before
  the person is asked, so a call a check would refuse never reaches a
  person.
- **MCP** (`docs/mcp.md`): `tool_filter`, per-tool `require_approval`
  (`always`/`never` or a map) with an `on_approval_request` callback,
  `cache_tools_list`, and `failure_error_function` for the model-visible
  error text (`None` raises instead). Guardrail lists set on a local MCP
  server attach to every tool it exposes.

## 2. Claude Agent SDK (`anthropics/claude-agent-sdk-python`, 0.2.180)

The Python SDK runs the **bundled Claude Code CLI as a subprocess**
(`_bundled/`) and speaks to it over stdio. So its harness is Claude
Code's, whose prompts this collection tracks release by release
(`../leaked/claude-code/`). What the SDK adds is the embedding surface
in `ClaudeAgentOptions` (`types.py`): `allowed_tools`/`disallowed_tools`,
`permission_mode`, `can_use_tool` (a Python callback per call),
`permission_prompt_tool_name` (route permission prompts to an MCP tool),
`max_turns`, `max_budget_usd`, `fallback_model`, `resume` and
`session_id`, `setting_sources`, and in-process SDK MCP servers. Hook
events are Claude Code's (`PreToolUse`, `PostToolUse`,
`PostToolUseFailure`, `UserPromptSubmit`, `Stop`, `SubagentStart`,
`SubagentStop`, `PreCompact`, `Notification`, `PermissionRequest`), and
hook input now carries the effective reasoning effort ("after any
downgrade for the selected model").

The deep dive's comparison ("core harness less open") is accurate: the
loop, compaction and tool set are not replaceable from the SDK, only
gated and observed. dcode copies the hook names and plugin variables
(`deepagents.md` §9), which makes Claude Code plugins a de facto
cross-harness format.

## 3. Microsoft Agent Framework (`microsoft/agent-framework`, `f145644`)

Already covered for orchestration patterns
(`../agent-subagent-architectures.md` §7), the judge loop
(`../agent-self-verification.md`), CodeAct (`../codeact-hyperlight/`)
and compaction strategies. New since the last read:
`agent_framework/_harness/_agent.py`, **`create_harness_agent()`**, "a
pre-configured bundled agent with batteries included": function
invocation, per-service-call history persistence, compaction, and
context providers for todo, mode, memory (file-backed) and skills, plus
`BackgroundAgentsProvider` ("Creating a background task does not block
… Always wait for outstanding tasks to finish before you finish
processing") and a tool-approval provider. Nothing in it is new to this
collection; it confirms the deep dive's point that the harness layer is
now standard equipment.

## 4. CrewAI (`crewAIInc/crewAI`, `4254a83`)

Roles, crews and flows, as the deep dive says. One mechanism is worth
recording as a contrast: `LLMGuardrail` (`lib/crewai/src/crewai/tasks/llm_guardrail.py`)
validates a task's output with a second agent and retries the task up
to `guardrail_max_retries` on failure. The validation prompt pastes the
raw task output straight into the query:

> Ensure the following task result complies with the given guardrail.
> Task result: {task_output.raw} Guardrail: {self.description} […]
> Focus only on identifying issues — do not propose corrections.

No delimiters, no statement that the result is untrusted, one verdict
for the whole output. Deep Agents' rubric grader (`deepagents.md` §4) is
the same idea with framing, per-criterion verdicts and a coverage check.
`HallucinationGuardrail` is a no-op placeholder in the open-source
package.

## 5. LlamaIndex (`run-llama/llama_index`, `baeabbf`)

Retrieval-first, as the deep dive says. Its `AgentWorkflow`
(`llama-index-core/llama_index/core/agent/workflow/`) implements
handoff as a tool with an allow-list per agent (`can_handoff_to`). The
`llama-index-tools-mcp-discovery` integration queries an external "MCP
Discovery" server for tools by natural-language description; it needs a
self-hosted server and is 90 lines of client. Nothing here for Forge.

## 6. Google ADK

Forge's build substrate, covered in depth in
[`../agent-design/adk.md`](../agent-design/adk.md). Not re-read.
