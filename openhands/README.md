# OpenHands (formerly OpenDevin)

- **Type**: Coding agent (autonomous software engineer)
- **License**: MIT
- **Source**: https://github.com/All-Hands-AI/OpenHands
- **Retrieved from tag**: [`0.60.0`](https://github.com/All-Hands-AI/OpenHands/tree/0.60.0/openhands/agenthub/codeact_agent/prompts) (2026-07-10)

`main` has since moved/renamed these prompt files (the project is mid
restructure), so a recent stable tag is used instead. Prompts are Jinja2
templates for the `CodeActAgent`.

## Files

- `system_prompt.j2` — the main system prompt (role, environment, tool-use
  guidelines, coding conventions).
- `additional_info.j2` — injects repo/runtime context (working dir, repo
  instructions, etc.) into the conversation.
- `in_context_learning_example.j2` — a worked few-shot example demonstrating
  the expected agent behavior/tool-call format.

Note: `user_prompt.j2` also exists in this directory but was empty at the
retrieved tag, so it isn't included.

**Correction**: even at the `0.60.0` tag used here, the same
`codeact_agent/prompts/` directory holds seven *more* Jinja2 files never
fetched into this folder — `system_prompt_interactive.j2`,
`system_prompt_long_horizon.j2`, `system_prompt_tech_philosophy.j2`,
`in_context_learning_example_suffix.j2`, `microagent_info.j2`,
`security_risk_assessment.j2`, and the (non-empty, contrary to the note
above being about a different file) `user_prompt.j2`. Naming suggests
alternate top-level operating modes (interactive vs. long-horizon vs. a
"tech philosophy" variant) plus a security-risk-assessment fragment and
a microagent-info fragment — none read in full. Flagged here rather than
silently left as a gap.

## Tool surface

- **Shell**: unspecified/generic — the prompt talks about "commands"
  generically, combining "multiple bash commands into one" and using
  `sed`/`grep` for bulk edits, without naming a specific shell.
- **Search**: plain `find`/`grep`/`git` commands with "appropriate
  filters" — no ripgrep preference stated (unlike Codex; see
  [`agent-tool-surfaces.md`](../agent-tool-surfaces.md)).
- **Code execution**: none beyond the shell itself — no dedicated
  Python/Node execution tool described.
- **Browser/web**: not in this prompt directly; `<EXTERNAL_SERVICES>`
  says to prefer platform APIs (GitHub/GitLab/Bitbucket) "unless the user
  asks otherwise or your task requires browsing," implying browser
  capability exists in the wider product but isn't detailed here.
- **Multimodal**: not addressed.
- **Sandbox/isolation**: not specified in this prompt — OpenHands'
  runtime sandboxing is configured outside the prompt text.
- **Distinctive**: the only source in this collection with an explicit
  process-management safety rule ("Do NOT use general keywords with
  commands like `pkill -f server`... find the exact PID first").

## Sub-agents

Not previously covered in this collection's sub-agent survey — a
prompt-text-only pass on the files stored here would have missed
delegation entirely, since none of the three captured `.j2` files
mention it. OpenHands has had a real delegation mechanism at every
stage of its history, both at the `0.60.0` tag used for the prompt
files above and — after a major restructure — in the successor repo
that now holds the actual agent implementation,
[`OpenHands/software-agent-sdk`](https://github.com/OpenHands/software-agent-sdk).
Everything below is sourced from reading those two repos directly
(MIT-licensed, ordinary open source), not from files stored in this
folder.

**At `0.60.0`** (`openhands/events/action/agent.py`,
`openhands/controller/agent_controller.py`): `AgentDelegateAction`
(fields: `agent` — a target agent *class name*, `inputs: dict`,
`thought`) hands control to a freshly-instantiated agent of that type,
wrapped in its own nested `AgentController(is_delegate=True,
delegate_level = parent.delegate_level + 1)`. Cooperative-blocking, not
threaded: the parent controller's `step()` is a no-op while a delegate
is active, so only one delegate runs at a time. The parent never sees
the delegate's individual steps — only a single `AgentDelegateObservation
(outputs: dict)` once the delegate finishes. No distinct system prompt
for delegate-mode: a delegate just runs its own agent type's normal
prompt (confirmed by reading `browsing_agent.py` directly — no
`is_delegate`-conditional prompt logic found). Agent types available at
this tag: `codeact_agent` (primary, the one prompted here),
`browsing_agent`, `visualbrowsing_agent` (screenshot+accessibility-tree
browsing), `loc_agent` (repo-as-graph code localization, exposes
`search_code_snippets`/`get_entity_contents`/`explore_tree_structure`),
`readonly_agent` (grep/glob/view/think/finish only, explicitly rejects
MCP tools), and `dummy_agent` (scripted, no LLM calls, for framework
tests). **A docs/code mismatch worth flagging as its own finding**:
`agenthub/README.md`'s example prose describes a "Delegator Agent" that
forwards to micro-agents like "RepoStudyAgent"/"VerifierAgent" — neither
exists in the actual `agenthub/` directory at this tag. Legacy/aspirational
documentation, not a real feature — exactly the kind of trap a
"read the README, not the code" pass would fall into.

**In the new SDK**, delegation was redesigned rather than dropped, and
became **three coexisting mechanisms**:

- **`openhands.tools.delegate`** — `spawn` (start a named, addressable
  sub-agent, kept alive in `self._sub_agents[agent_id]`) + `delegate`
  (send a new message to an already-spawned agent by id — repeatable,
  stateful, the same shape as Codex's `send_input`). Concurrency is
  **real and threaded**: `DelegateExecutor._delegate_tasks` runs
  multiple named sub-agents' `.run()` calls on separate Python threads
  and joins them, capped at `max_children: int = 5`.
- **`openhands.tools.task`** (`TaskToolSet`) — wired into the default
  tool set (`get_default_tools(enable_sub_agents=True)`). One task per
  call via `subagent_type` (default `"general-purpose"`), with a
  `resume: <task_id>` parameter to re-attach to a specific prior
  sub-agent conversation. Its tool description reads as closely
  modeled on Claude Code's own Task tool phrasing ("Launch a subagent
  to handle complex, multi-step tasks autonomously... each delegation
  has overhead — use them when the task genuinely benefits from a
  separate agent... A single grep, find, or cat command would answer
  your question — just run it yourself").
- **`openhands.tools.workflow`** (`WorkflowToolSet`) — the standout
  finding here: a small orchestration DSL exposed to the model as a
  Python sandbox — `wf.run_agent(...)`, `wf.map_agents(items, prompt,
  max_concurrency=...)`, `wf.reduce_agent(items, prompt, ...)`,
  `wf.pipeline(items, *stages)` (staged and non-barriered — a fast item
  can reach a later stage while a slow item is still on an earlier
  one), `wf.flatten(values)`. `max_concurrency` defaults to 8, capped
  1–64. Guardrails are deliberate: only documented `wf` methods are
  callable, and `ExceptionGroup` is intentionally *not* exposed by name
  in the sandbox, forcing `map_agents` failures through plain
  `except Exception` or agent-returned error sentinels rather than
  partial `except*` handling. This is a materially different design
  point from every other source's single spawn/delegate primitive in
  this collection — a constrained map-reduce/DAG engine for sub-agents,
  not just a way to fire one off.
- **Sub-agent system prompts are a documented suffix, not a swap**: a
  spawned agent's `AgentDefinition.system_prompt` (the Markdown body of
  its definition file) is applied via `AgentContext(system_message_suffix=...)`
  — appended to the base system message, not replacing it. Four
  built-in agent-definition files exist (`openhands-tools/openhands/tools/preset/subagents/`):
  `general-purpose` (default — terminal + file_editor + task_tracker),
  `bash-runner` (instructed to never dump raw command output, report
  only pass/fail + failure reasons), `code-explorer` (forbids any
  file-modifying command, whitelists specific read-only shell commands),
  `web-researcher` (a three-tool Tavily-search/fetch/browser workflow
  with "never spend more than 2 actions on a blocked site"). Custom
  agent types are first-class beyond these four, discovered from
  `.agents/agents/*.md` (project, then user, then SDK-builtin
  precedence) — the same Markdown+YAML-frontmatter convention OpenCode
  independently converges on (see `../opencode/README.md`).
- **Recursion**: none of the four built-in agent definitions include
  the `task` or `delegate` tool in their own tool list, so built-in
  sub-agents can't recurse by default (inferred from their frontmatter,
  not an explicit code-level prohibition) — recursion becomes reachable
  only if a *custom* agent definition deliberately grants itself one of
  those tools.
- **A separate, unrelated "many parallel sessions" layer**:
  `openhands/app_server/` (still in the original `All-Hands-AI/OpenHands`
  repo) is a FastAPI server hosting many independent sandboxed
  conversations for the cloud product — the "run OpenHands on 50
  different issues at once" kind of parallelism, structurally unrelated
  to the in-conversation `delegate`/`task`/`workflow` mechanisms above.

## Compaction

Sourced from the live `OpenHands/software-agent-sdk` repo, not files
stored in this folder — see
[`agent-context-compaction.md`](../agent-context-compaction.md) for the
cross-source comparison this feeds into.

- **A genuinely pluggable `Condenser` abstraction** — the only source
  in this collection's compaction survey where the compression
  *strategy itself* is a swappable component, not a fixed algorithm.
  `CondenserBase` is an abstract base with a `"kind"` discriminator
  field; confirmed concrete implementations: `LLMSummarizingCondenser`
  (the real summarization strategy, detailed below), `NoOpCondenser`
  (returns the view unchanged — explicit opt-out), and
  `PipelineCondenser` (chains multiple condensers, short-circuiting if
  any stage decides to condense). Any `Agent` — top-level or a spawned
  sub-agent — selects its own condenser at config time.
- **Condensation is a first-class, non-destructive event in an
  append-only log, not a history rewrite**: a `Condensation` event is
  just another entry appended to the conversation's event log; the
  reduced "view" the LLM actually sees is computed on the fly by
  replaying `Condensation.apply()` (which removes specific
  `forgotten_event_ids` and splices in a summary) over the *full,
  never-deleted* persisted log. The complete original history — and
  the record of exactly which events were forgotten at each step —
  stays on disk indefinitely, even though nothing currently lets the
  agent itself re-query forgotten events mid-conversation.
- **The summarization prompt asks for structured prose, not JSON**: a
  Jinja2 template with named sections (`USER_CONTEXT`, `TASK_TRACKING`
  — explicitly told to preserve exact task IDs/statuses — `COMPLETED`,
  `PENDING`, `CURRENT_STATE`, plus `CODE_STATE`/`TESTS`/`CHANGES`/
  `DEPS`/`VERSION_CONTROL_STATUS` for code tasks specifically), with
  worked examples for both code and non-code tasks. Rendered and sent
  as a fully separate LLM call under its own `usage_id: "condenser"` so
  its token cost doesn't get folded into the main agent's usage stats.
- **Both proactive and hard-reactive triggers, explicitly named as
  such**: three condensation reasons checked each step — `EVENTS`
  (view size exceeds a max-event count), `TOKENS` (only if a token
  ceiling is configured, condenses down toward roughly half), and
  `REQUEST` (an explicit unhandled request event — the hard-trigger
  path). The SDK's own docs label the first two "soft" (can be
  deferred/retried next step) and the request path "hard." A dedicated
  emergency fallback (`hard_context_reset`) handles the case where
  normal condensation still can't fit — it summarizes the entire view
  in one shot, retrying up to 5 times with the event text shrunk by
  20% per attempt if the single call itself overflows.
- **A configurable "never forget" floor**: `keep_first` (default 4 in
  the SDK's standard preset) always preserves that many initial events
  verbatim — typically the original task framing — no matter how
  aggressively later history gets condensed.
- **A safety check against wasted/trivial condensation**:
  `minimum_progress` (default 0.1) requires at least 10% of the current
  view to actually be condensable, or the condenser raises rather than
  performing a no-op-adjacent summarization.
- **Every sub-agent gets its own fully independent condenser and event
  history** — confirmed by reading the delegation executor: a spawned
  sub-agent's `LocalConversation` is a brand-new event log, condensed
  on its own schedule, with only aggregate LLM-cost metrics (not
  events) merged back to the parent afterward. A code comment states
  the reasoning directly: sub-agents get a summarizing condenser by
  default "so deep runs auto-compact instead of erroring on context
  overflow" — condensation is treated as a correctness requirement for
  long delegated runs, not just a cost optimization. No cross-agent or
  orchestration-level (e.g. Magentic-style) shared condensation exists
  — each conversation in the delegation tree compacts in isolation.
- **Concrete numeric defaults**: the class-level default is
  `max_size=240`/`keep_first=2`, but the SDK's actual shipped preset
  overrides this to `max_size=80`/`keep_first=4` for both the top-level
  agent and any sub-agent that doesn't specify its own condenser.

## Self-verification and testing

See [`agent-self-verification.md`](../agent-self-verification.md) for
the cross-source comparison this feeds into.

- **Confirmed at the prompt level** (`system_prompt.j2`, stored in this
  folder): a numbered "TESTING"/"VERIFICATION" pair of rules — create
  tests to verify issues before implementing fixes, consider
  test-driven development for new features, don't write tests for
  non-functional changes, ask the user before investing in test
  infrastructure that doesn't exist, and "test your implementation
  thoroughly, including edge cases" if the environment supports it.
  Purely instructional — no code-level enforcement confirmed for this
  layer.
- **No dedicated review/verification sub-agent in the current SDK** —
  confirmed absence: the complete built-in sub-agent set is exactly
  `general-purpose`/`code-explorer`/`bash-runner`/`web-researcher`
  (already documented in "Sub-agents" above), no fifth
  "reviewer"/"verifier" agent exists.
- **Correction to what a filename might suggest**: the old (`0.60.0`)
  tag's `security_risk_assessment.j2` prompt file is **not** a
  self-review-of-completed-work mechanism — confirmed by reading it in
  full, it's a pre-execution risk-classification policy, requiring the
  agent to tag each proposed tool call's `security_risk` as
  LOW/MEDIUM/HIGH before running it. This gates *proposed actions*, a
  different concern from checking *completed* work — worth flagging
  since the name alone invites the opposite assumption.

## Turn output

See [`agent-turn-output.md`](../agent-turn-output.md) for the
cross-source comparison this feeds into. **Not found** in any of this
folder's three local prompt files (`system_prompt.j2`,
`additional_info.j2`, `in_context_learning_example.j2`) — a targeted
grep for title/thinking/reasoning/thought turned up nothing relevant.
The one "title" hit is unrelated to session naming: "When updating a
PR, preserve the original PR title and purpose, updating description
only when necessary" (`system_prompt.j2:46`).

This is a genuine capture gap, not a confirmed design choice, for two
independent reasons: this folder's Compaction section above is itself
sourced from the *live* `OpenHands/software-agent-sdk` repo rather than
anything stored locally, meaning this folder only ever held CodeAct-
agent prompt text, never harness/session-management code where a title
feature would live; and the Sub-agents section documents a separate
`openhands/app_server/` FastAPI layer "hosting many independent
sandboxed conversations for the cloud product" — exactly where
session-naming logic would plausibly live, and it isn't represented by
any file in this folder. The closest tangential hit is prompted
narration, not a reasoning-display mechanism: the TROUBLESHOOTING block
tells the model to "Document your reasoning process" after repeated
failed fix attempts — ordinary prose in a debugging workflow, not a
native thinking/reasoning content-block toggle.

## Permissions and approval

See [`agent-permissions-approval.md`](../agent-permissions-approval.md)
for the cross-source comparison this feeds into. This is the doc where
`security_risk_assessment.j2` — previously filed only as an
"adjacent-but-different" note under Self-verification above — is the
central finding, not a footnote. Sourced partly from live upstream
fetches (`raw.githubusercontent.com/All-Hands-AI/OpenHands` at tag
`0.60.0`), since this folder never stored the file itself or the
controller code that enforces it.

- **The full risk policy, context-dependent on execution mode**: three
  tiers (LOW/MEDIUM/HIGH), but the *definitions themselves* change via
  a Jinja conditional depending on whether the agent is running in CLI
  mode (host filesystem) or sandboxed/container mode — e.g. LOW is
  "Safe, read-only actions" in CLI mode vs. "Read-only actions inside
  sandbox" in container mode; HIGH is "elevated (`sudo`) commands,
  deleting critical files" in CLI mode vs. "connecting to host
  filesystem, privileged container ops" in container mode. A closing
  global rule overrides both: "Always escalate to **HIGH** if
  sensitive data leaves the environment." No other source checked for
  this doc couples its risk tiers this tightly to the actual isolation
  boundary in play.
- **The self-tag is advisory, not trusted by default — a genuine,
  operator-selectable static-vs-LLM-based choice**: the model's own
  `security_risk` tag is only *one* of three interchangeable
  `SecurityAnalyzer` implementations the harness can be configured
  with — `LLMRiskAnalyzer` (trusts the model's self-reported tag
  verbatim), `InvariantAnalyzer` (spins up a genuinely separate,
  Dockerized static policy-analysis server and evaluates the action
  trace independent of what the model claims), and a third,
  unexamined `GraySwanAnalyzer`. This is the clearest static-vs-
  LLM-based contrast found across every source checked for this doc —
  most sources pick one philosophy; OpenHands makes it a pluggable
  operator choice, the same "infrastructure over instruction" pattern
  this collection's other docs found distinguishing OpenHands's
  `Condenser` (compaction) and delegation system (sub-agents).
- **Fail-safe default when no analyzer is configured**: "When no
  security analyzer is configured, treat all actions as UNKNOWN
  risk... This is a fail-safe approach that ensures confirmation is
  required" — the system defaults to asking for *everything* rather
  than trusting the model's tag by omission.
- **Only HIGH (or UNKNOWN) actually pauses execution**: `confirmation_mode`
  is a single boolean (a global always-ask/never-ask switch, not a
  named-mode enum like Claude Code's six modes), scoped to five action
  types (`CmdRunAction`, `IPythonRunCellAction`,
  `BrowseInteractiveAction`, `FileEditAction`, `FileReadAction`). LOW
  and MEDIUM never pause even with `confirmation_mode` on — only a
  HIGH tag, or an UNKNOWN tag when no analyzer is configured at all.
- **An acknowledged rough edge in CLI mode**: in CLI mode, every
  runnable action of the gated types sets `AWAITING_CONFIRMATION`
  regardless of risk tier when `confirmation_mode` is on — the source
  code's own comment reads "this is not ideal... we should refactor,"
  meaning CLI mode is effectively closer to always-ask than the
  tri-level policy elsewhere suggests.
- **Scope/persistence**: risk assessment runs per-action, every time —
  no persistent "remember this decision" cache was found in the
  controller; `confirmation_mode` itself is a session/config-level
  toggle, not a per-rule persisted allowlist.
- **Distinct, narrower prompted rules also present in `system_prompt.j2`**:
  a `<SECURITY>` block on credential use ("Only use GITHUB_TOKEN and
  other credentials in ways the user has explicitly requested and would
  expect"), and a specific process-safety rule against broad `pkill`
  patterns ("Prefer using `ps aux` to find the exact process ID (PID)
  first, then kill that specific PID") — both prompted-only, no
  structural enforcement confirmed. The TROUBLESHOOTING block's "propose
  a new plan and confirm with the user before proceeding" on major
  issues is likewise a prompted, non-structural escalation trigger —
  detecting a "major issue" is left entirely to the model's judgment.
- No PreToolUse-equivalent hook mechanism or rule-file/allowlist
  concept exists in the local `.j2` files — the entire enforcement
  layer lives in `agent_controller.py`, mirroring Claude Code's split
  between silent prompt text and harness-internal gating, except that
  here the model *is* an active participant (it sets the tag), just
  not a trusted one.

## Git and version control

See [`agent-git-vcs.md`](../agent-git-vcs.md) for the cross-source
comparison this feeds into. The richest git policy of the general-
purpose (non-benchmark-harness) sources checked for this doc, entirely
concentrated in `system_prompt.j2`'s `<VERSION_CONTROL>` and
`<PULL_REQUESTS>` blocks.

- **A concrete co-author trailer convention with a fallback identity
  policy**: "If there are existing git user credentials already
  configured, use them and add Co-authored-by: openhands
  &lt;openhands@all-hands.dev&gt; to any commits messages you make. if a
  git config doesn't exist use "openhands" as the user.name and
  "openhands@all-hands.dev" as the user.email by default, unless
  explicitly instructed otherwise." A literal git-config policy,
  including a concrete username/email fallback, not just an
  attribution instruction.
- **Auto-commit is conditional, not gated strictly behind explicit
  request** — a real contrast with the push/PR rules below: "Use
  `git status` to see all modified files, and stage all files
  necessary for the commit. Use `git commit -a` whenever possible,"
  paired with an explicit don't-commit-junk rule ("Do NOT commit files
  that typically shouldn't go into version control (e.g., node_modules/,
  .env files...) unless explicitly instructed" — check `.gitignore` or
  ask if unsure). Commits happen when the agent judges it appropriate
  in the course of solving the task, not on every edit and not only on
  explicit request.
- **Push/PR creation is a hard request-gate, echoed twice**: "Do NOT
  make potentially dangerous changes (e.g., pushing to main, deleting
  repositories) unless explicitly asked to do so," restated in
  `<PULL_REQUESTS>` as "**Important**: Do not push to the remote
  branch and/or start a pull request unless explicitly asked to do
  so."
- **Branch-safety is a lightweight, name-keyed heuristic, not a real
  branch-protection check**: "You should work within the current
  branch... unless... the current branch is 'main', 'master', or
  another default branch where direct pushes may be unsafe" — a
  prompt-only proxy for protected-branch detection, keyed purely off
  branch name rather than any actual permissions/protection-rule
  lookup.
- **Session-hygiene rules for PRs not seen phrased this way
  elsewhere in this collection**: "create only ONE per session/issue
  unless explicitly instructed otherwise," "update it with new
  commits rather than creating additional PRs for the same issue," and
  "preserve the original PR title and purpose, updating description
  only when necessary" (the last already covered under Turn output
  above, in the title-generation context — repeated here because it's
  equally a git-workflow rule). No PR-description *template* and no
  self-review-before-opening step were found.
- **No worktree isolation found** — the closest analog is the
  single-clone, single-branch session-isolation rule above (stay on
  the checked-out branch), not multiple `git worktree` checkouts for
  parallel sub-agents; the Sub-agents section's `DelegateExecutor`/
  `WorkflowToolSet` concurrency is at the conversation/thread level,
  not the filesystem-checkout level, based on what's documented.
