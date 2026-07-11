# Google Antigravity

- **Type**: Coding agent (Google's agentic IDE, plus a terminal
  sibling — see below) · **Vendor**: Google
- **Status**: closed source (leaked)
- **Mirror sources**:
  - `Fast Prompt.txt`, `planning-mode.txt` —
    https://github.com/x1xhlol/system-prompts-and-models-of-ai-tools/tree/main/Google/Antigravity
    (2026-07-10)
  - `CLI Prompt.md` —
    https://github.com/asgeirtj/system_prompts_leaks/blob/main/Google/antigravity-cli.md
    (2026-07-11), a separate, independently-maintained aggregator from
    the x1xhlol one used everywhere else in this collection.

**Two real products, one shared harness, captured separately.** Google
launched Antigravity 2.0 in May 2026 as the official successor to
Gemini CLI (which is being sunset for non-enterprise users), shipping
simultaneously as a desktop IDE, a terminal CLI (`agy`), an SDK, and a
managed API tier. The terminal CLI's own GitHub repo
(`google-antigravity/antigravity-cli`) is a binary-distribution shell
only — no source, no prompt templates — so it doesn't qualify for this
collection's main `sources/` list; both captures here remain `leaked/`.
Diffing `CLI Prompt.md` against `Fast Prompt.txt` (451 vs. 611 lines):
same opening identity line, but the CLI capture drops the XML
structural tags (`<identity>`, `<user_information>`, `<tool_calling>`)
present in the IDE version, and — more substantively — has **zero**
mentions of `browser_subagent` or the Knowledge Subagent (both
GUI-dependent features documented below), consistent with a genuinely
distinct terminal-harness variant of the same underlying prompt rather
than a re-mirror of the same file. It does carry its own
`<planning_mode_artifacts>` section with a "Walkthrough" file
convention (`<appDataDir>/brain/<conversation-id>/walkthrough.md`) not
present in what's captured for the IDE.

## Files
- `Fast Prompt.txt` — IDE prompt for a lower-latency/"fast" response
  mode.
- `planning-mode.txt` — IDE prompt for a planning-first mode.
- `CLI Prompt.md` — the terminal (`agy`) harness's own system prompt;
  no accompanying tool-schema/JSON file was found for this capture.

## Tool surface

See [`agent-tool-surfaces.md`](../../agent-tool-surfaces.md) for the
cross-source comparison this feeds into. `Fast Prompt.txt` carries a
full 23-tool schema (`namespace functions {...}`, lines 320-611);
`planning-mode.txt` and `CLI Prompt.md` only name tools in prose, no
schema captured for either.

- **A four-tool async/terminal stack, more granular than any other
  source's shell-execution design surveyed for the tool-surfaces
  doc**: `run_command` (propose a command, `SafeToAutoRun`/
  `WaitMsBeforeAsync` params, live-rendered OS/shell string in its own
  docstring — "Operating System: windows. Shell: powershell") paired
  with three separate tools — `command_status` (poll by `CommandId`),
  `read_terminal` (read output by `Name`+`ProcessID`), and
  `send_command_input` (stdin injection or `Terminate`, explicitly for
  "REPLs, interactive commands, and long-running processes").
- **Exact tool-name matches to Windsurf's documented surface** —
  `grep_search`, `codebase_search`, `view_code_item`, `search_web`,
  `read_url_content`, `write_to_file` all appear verbatim in both
  sources' tool lists, a strong signal Antigravity's IDE tool layer is
  Windsurf-derived infrastructure (consistent with Google's 2025
  acquisition of Windsurf's team/technology) — worth reading alongside
  `leaked/windsurf/README.md` rather than as coincidental convergence.
- **Mandatory review/lint-linkage metadata baked into the edit-tool
  schema itself**: both `replace_file_content` and
  `multi_replace_file_content` carry a `Complexity` field ("A 1-10
  rating of how important it is for the user to review this change")
  and a `TargetLintErrorIds` field as required schema fields, not
  prompted-only guidance — a stronger, more structural version of the
  "attach lint IDs to an edit" pattern found elsewhere in this
  collection (e.g. Windsurf's own passive labeling parameter).
- **`generate_image` does both generation and editing** — up to 3
  source `ImagePaths` for image-editing mode, used explicitly for both
  UI mockups and "assets for use in an application," alongside literal
  MCP client tools (`list_resources`/`read_resource`).
- **`CLI Prompt.md` has no captured tool schema at all — genuinely no
  shell tool is even named in prose**, confirmed via full-text grep
  (no `run_command`/`bash`/named-shell-tool string anywhere). The only
  shell-adjacent content is a worked example teaching the model to
  `grep`/`head` its own conversation-transcript file (see Compaction
  below) — real shell access plausibly exists, but neither its name
  nor schema is part of what got captured, a genuine gap rather than
  evidence of absence.
- **No sandbox/isolation** — `run_command` executes real PowerShell on
  the user's actual machine.

## Sub-agents

See [`agent-subagent-architectures.md`](../../agent-subagent-architectures.md)
for the cross-source comparison this feeds into. All three files
handle sub-agents completely differently — a notable data point on its
own about how unstable this feature is even within one product family:
`Fast Prompt.txt` has two fixed, fully-schematized, purpose-built
sub-agents; `planning-mode.txt` has none at all (confirmed absent via
full-file grep); `CLI Prompt.md` has a single generic, model-
extensible delegation primitive with no fixed named agents shown.

- **`browser_subagent`** (`Fast Prompt.txt` only) — spawns "an agent
  similar to you, with a different set of tools, limited to tools to
  understand the state of and control the browser," given a free-text
  `Task` description and a human-readable `TaskName`/`RecordingName`
  used to group and label its steps in the UI. Distinctive features:
  every browser interaction is "automatically recorded and saved as
  WebP videos to the artifacts directory" ("the ONLY way you can
  record a browser session video/animation" — a capability not
  mentioned anywhere else in this collection), a `waitForPreviousTools`
  flag for sequencing it against other tool calls, and an explicit
  post-condition requirement: "After the subagent returns, you should
  read the DOM or capture a screenshot to see what it did" — the
  orchestrator is told not to trust the sub-agent's self-report alone
  for browser state, unlike most other sources' "the agent's outputs
  should generally be trusted" framing.
- **The Knowledge Subagent** (`Fast Prompt.txt` only) — not
  model-invoked at all; described as "a separate KNOWLEDGE SUBAGENT
  that reads the conversations and then distills the information into
  new KIs [Knowledge Items] or updates existing KIs as appropriate."
  This runs as a background/asynchronous process over past
  conversation history, producing a persistent knowledge base the
  *orchestrator* later reads (via KI summaries, falling back to raw
  conversation logs only when no relevant KI exists) — closer in
  spirit to Windsurf's `create_memory`/`trajectory_search` (persistent
  cross-session memory) than to a synchronous delegate-and-report
  sub-agent, but implemented as its own distillation agent rather than
  a callable memory-write tool the main agent invokes directly.
- **`CLI Prompt.md`'s generic framework — structurally novel, not
  matching any existing category in this collection's typology**: a
  `<subagents>` section (lines 99-111) bundles three capabilities.
  `invoke_subagent` invokes a pre-registered subagent by name (none
  enumerated in what's captured — unlike `browser_subagent`'s
  fully-specified schema, no parameter list or named example exists
  here). `define_subagent` is a genuinely dynamic, **model-driven
  capability to create new subagent definitions scoped to the current
  conversation** — "Agents defined by the define_subagent tool are
  available for the duration of this conversation." No other source
  in this collection's sub-agent survey shows a model-invocable
  "define a new agent type on the fly" tool. `send_message` addresses
  another agent by "conversation ID" (returned by `invoke_subagent`),
  with an explicit carve-out: "Do NOT use send_message to communicate
  with the user. Instead, output visible text to communicate with the
  user."
- **A "reactive wakeup, no polling" notification model, stated as a
  general property of the whole messaging system**: "After launching a
  subagent, you do NOT need to poll or check your inbox in a loop. The
  system will automatically notify you when the subagent sends a
  message. Simply proceed with other work or stop calling tools, and
  you will be notified when there is a message to process."
- **No stated concurrency-safety or turn-limit rules** for any of the
  three mechanisms found across the three files, unlike Gemini CLI's
  or Amp's explicit parallel/serial policies — the same gap the
  original README noted for `browser_subagent`/Knowledge Subagent now
  extends to the CLI's generic mechanism too.

## Compaction

See [`agent-context-compaction.md`](../../agent-context-compaction.md)
for the cross-source comparison this feeds into. No compaction
trigger, summarization prompt/template, or numeric threshold was found
in any of the three files — but the "dual-context architecture"
already gestured at in earlier research is confirmed in full detail,
and reads as a structurally distinct recovery philosophy from
everything else in this collection.

- **Two parallel access mechanisms, KI-first**: "There are two
  mechanisms through which you can access relevant context. 1.
  Conversation Logs and Artifacts, containing the original information
  in the conversation history 2. Knowledge Items (KIs), containing
  distilled knowledge on specific topics" — "Search for relevant KIs
  first. Only read the conversation logs if there are no relevant
  KIs."
- **A corpus-level, not session-level, instance of the "anchor and
  update" incremental-summarization pattern** — "Individual KIs can be
  updated or expanded over multiple conversations," generated by the
  Knowledge Subagent, which "distills... into new KIs or updates
  existing KIs as appropriate." This collection's compaction doc
  otherwise documents anchor-and-update only at the single-conversation
  level (Pi's `UPDATE_SUMMARIZATION_PROMPT`, OpenCode's
  `<previous-summary>`); Antigravity's KI system incrementally updates
  a **persistent, cross-conversation, per-topic** knowledge base
  instead — the same idea one level up.
- **A bare declared token ceiling with no surrounding mechanism**:
  `Fast Prompt.txt` has `<budget:token_budget>200000</budget:token_budget>`
  — no proactive-check logic, no reserved buffer, no described trigger
  accompanies it, unlike every source in this collection's numeric-
  threshold table that pairs a number with an actual pipeline. Absent
  entirely from the other two files.
- **The raw log is never deleted and is directly agent-reachable on
  demand — a fifth recovery-philosophy variant for this doc**: the
  conversation log persists as `transcript.jsonl` on disk
  (`<appDataDir>/brain/<conversation-id>/.system_generated/logs/`) and
  is reachable via ordinary tools in the IDE, or literal shell commands
  in the CLI — `CLI Prompt.md` gives worked examples: `grep
  "invoke_subagent" .../transcript.jsonl` to find spawned sub-agents,
  `head` to view the conversation's start. This differs from
  OpenHands's append-only log (retained but "not confirmed reachable
  by the agent itself mid-conversation") and from Windsurf's
  externalize-to-memory strategy (the memory tool is a *write* path,
  not a query path into the original record) — here the raw record is
  both durable *and* directly queryable by the agent, with the KI
  system as a curated index into it rather than a replacement for it.
- **A dangling "checkpoint" reference, worth flagging so it isn't
  mistaken for a documented mechanism**: `CLI Prompt.md` twice
  mentions "history before the last checkpoint" as a reason to consult
  the raw transcript — implying *some* compaction-like event exists in
  the product, but no `/compact` command, no summarization prompt, and
  no trigger condition accompanies either mention. A confirmed capture
  gap, not a documented feature.
- **A related capture gap**: `CLI Prompt.md` references "KI summaries"
  as an already-understood concept (line 174) but never itself defines
  what a KI or the Knowledge Subagent is anywhere in its 451 lines —
  either the full CLI prompt has a matching definition block this leak
  didn't capture, or the concept is injected at runtime from elsewhere.

## Turn output

See [`agent-turn-output.md`](../../agent-turn-output.md) for the
cross-source comparison this feeds into.

- **Title generation — not found, but titles clearly exist upstream of
  the prompt**: `Fast Prompt.txt`'s `<persistent_context>` few-shot
  example hands the model *already-generated* conversation titles
  ("SYSTEM: Here are some recent conversation IDs and titles:") rather
  than asking it to produce one — confirms titles are a real UI
  concept populated outside what any of these three prompts control.
- **Reasoning/thinking display — confirmed absent** across all three
  files (no `reasoning_effort`/`thinkingConfig`/display-toggle
  mechanism of any kind).
- **Baseline prompted narration differs materially in content across
  files, not just wording** — `Fast Prompt.txt`/`planning-mode.txt`
  share near-identical Formatting/Proactiveness/Helpfulness guidance;
  `CLI Prompt.md`'s `<communication_style>` is shorter and adds two
  CLI-only rules: "Provide a summary of your work when you end your
  turn" (a thin instance of this doc's "third kind of summary" §1c
  pattern — a per-turn recap, though with no character limit or
  anti-heading rule the way Cursor's version has one) and a mandatory
  clickable-file-link requirement ("You MUST create clickable links
  for all files and code symbols... using the `file://` scheme") that
  in the IDE prompts is scoped only to markdown *artifacts*, not
  ordinary chat — the CLI generalizes a convention the IDE keeps
  narrower.
- **A structurally novel narration/communication-gating mechanism,
  found only in `planning-mode.txt`**: the `task_boundary`/
  `notify_user` "task view UI" system. `task_boundary` sets
  `TaskName`/`TaskSummary`/`TaskStatus`/`Mode` (∈ PLANNING/EXECUTION/
  VERIFICATION) — critically, `TaskStatus` "should describe the NEXT
  STEPS, not the previous steps" (prospective, not the retrospective
  "explain what you just did" framing every other narration mechanism
  in this collection uses). `notify_user` is "the only way to
  communicate with the user when you are in an active task" — ordinary
  assistant messages become literally invisible: "regular messages are
  invisible. You MUST use notify_user." Doesn't fit this doc's
  title-gen/reasoning-display/prose-narration/schema-embedded-
  narration typology — closest to a fifth category: a dedicated
  stateful tool that gates the communication channel itself, getting
  its own three-value state machine.

## Self-verification and testing

See [`agent-self-verification.md`](../../agent-self-verification.md)
for the cross-source comparison this feeds into. Richness is uneven:
`Fast Prompt.txt` has almost nothing; `planning-mode.txt` and `CLI
Prompt.md` share what is essentially the same Verification Plan /
Walkthrough template word-for-word in places — direct textual evidence
of shared lineage between the IDE's planning mode and the CLI, beyond
the identity-line match noted above.

- **`Fast Prompt.txt` — a permission grant, not a mandate**: "As an
  agent, you are allowed to be proactive, but only in the course of
  completing the user's task... you can edit the code, verify build
  and test statuses, and take any other obvious follow-up actions" —
  the same §7 (prompted-only) shape as Claude Code's non-ant-gated
  "Autonomous work" section. A separate, epistemically distinct
  "verify" appears in the KI system ("Always verify: Use the
  references in metadata.json to check original sources") — about not
  trusting cached *knowledge*, not code correctness; kept distinct so
  it isn't miscounted.
- **A shared Verification Plan template**, identical across
  `planning-mode.txt` and `CLI Prompt.md`: "## Verification Plan —
  Summary of how you will verify that your changes have the desired
  effects. ### Automated Tests - Exact commands you'll run, browser
  tests using the browser tool, etc. ### Manual Verification - Asking
  the user to deploy to staging and testing, verifying UI changes on
  an iOS app etc."
- **A severity-gated retry/escalation policy tied to the task-mode
  state machine — a candidate new pattern for this doc's typology**:
  "If you find minor issues or bugs during testing, stay in the
  current TaskName, switch back to EXECUTION mode... Only create a new
  TaskName if verification reveals fundamental design flaws that
  require rethinking your entire approach — in that case, return to
  PLANNING mode." Not a flat reproduce-fix-verify loop (§1), not a
  deterministic gate (§2), not a separate-LLM judge (§3) — a two-tier
  branch on *what kind* of failure was found, minor vs. fundamental,
  each routed to a different recovery mode.
- **The Walkthrough artifact — a candidate "artifact-as-verification-
  record" pattern, not matching any of this doc's existing
  categories**: a required, persistent markdown file
  (`<appDataDir>/brain/<conversation-id>/walkthrough.md`) documenting
  "Changes made / What was tested / Validation results," with embedded
  screenshots/recordings as evidence, explicitly *updated* rather than
  recreated on related follow-up work. Distinct from Jules's read-PR-
  comment tools (this is authored evidence, not received feedback) and
  from a chat-message or tool-call-payload verdict — the completion
  deliverable is a durable, evidence-embedding file.
- **This whole pipeline is scoped to complex/planned work only**: `CLI
  Prompt.md` explicitly excludes "investigatory," "trivially simple
  and one-off," and "minor follow-up" work — "you continue your work
  WITHOUT making a plan or requesting user review" — meaning trivial
  edits get no verification-artifact requirement under this mechanism
  at all.
- **A near-miss worth flagging so it isn't mistaken for a risk-
  classification mechanism**: a `[!CAUTION]` Markdown-alert formatting
  example reading "High-risk actions that could cause data loss or
  security vulnerabilities" is purely an artifact-styling example (how
  to format a warning callout in a written document), not a functioning
  risk tier.

## Permissions and approval

See [`agent-permissions-approval.md`](../../agent-permissions-approval.md)
for the cross-source comparison this feeds into.

- **A hard-scoped filesystem boundary, confirmed present in both IDE
  files and confirmed absent from `CLI Prompt.md`**: "You are not
  allowed to access files not in active workspaces. You may only
  read/write to the files in the workspaces listed above," with one
  explicit, self-referential exception (a config/KI directory,
  restricted "ONLY for usage specified in your system instructions").
  `CLI Prompt.md` has no `<user_information>` section and no
  equivalent restriction anywhere — confirmed via full-text grep — a
  genuine, quotable capability/scope difference between the terminal
  and IDE harnesses, not just tag-stripping.
- **`SafeToAutoRun` — the same self-assigned risk-tag shape (and
  exact field name) as Windsurf's**: `run_command`'s schema (`Fast
  Prompt.txt` only) — "Set to true if you believe that this command is
  safe to run WITHOUT user approval." No external check on the tag's
  honesty is described; enforcement lives entirely in what the client
  does with the boolean. The exact field-name match to Windsurf (see
  Tool surface above) is worth reading as further evidence of shared
  lineage, not independent convergence.
- **A rule/policy mechanism embedded as inline annotations in
  user-authored workflow files, not a separate config format** — `//
  turbo` and `// turbo-all` comments inside `.agent/workflows/*.md`
  files override the model's normal per-call `SafeToAutoRun` judgment:
  "If a workflow step has a '// turbo' annotation above it, you can
  auto-run the workflow step... This annotation ONLY applies for this
  single step... If a workflow has a '// turbo-all' annotation
  anywhere, you MUST auto-run EVERY step." Present in both
  `Fast Prompt.txt` and `planning-mode.txt`; **confirmed absent from
  `CLI Prompt.md`** (no `<workflows>` section at all).
  A distinct mechanism from Codex's Starlark rules or Gemini CLI's
  TOML tiers — source-code-comment-style annotations inside a
  markdown workflow file, not a separate policy config.
  A `<user_rules>` placeholder ("The user has not defined any custom
  rules") confirms a CLAUDE.md/Cursor-rules-style injection point
  exists in both IDE prompts; **`CLI Prompt.md` instead has a
  populated `<guidelines>` tag baked directly into the system prompt**
  rather than sourced from a placeholder — whether this is the CLI's
  rename of the same mechanism (now populated) or a genuinely
  different, non-user-configurable rule isn't resolvable from the text
  alone.
- **A human-confirmation gate on the *plan*, a third instance of
  user-gated authority beyond this doc's existing §9 pair**: "STOP and
  wait for the user's explicit approval before proceeding to
  execution" (`CLI Prompt.md`); "If user requests changes to your
  plan, stay in PLANNING mode, update the same implementation_plan.md,
  and request review again... until approved" (`planning-mode.txt`).
  §9 currently documents human authority over *completed work*
  (Replit, Warp); this is human authority over the *plan*, before
  execution starts — a related but distinct axis.

## Git and version control

See [`agent-git-vcs.md`](../../agent-git-vcs.md) for the cross-source
comparison this feeds into. **Confirmed near-total absence across all
three files** — no commit-message convention, no commit-timing policy,
no checkpoint/undo system, no worktree isolation, no branch-naming
rule, no PR/push workflow. `Fast Prompt.txt`'s full 23-tool schema has
zero git-specific tools among them (no `git_status`/`git_diff`/
`create_pr`) — a real negative signal, not just absence of prose;
`run_command` (generic shell) is presumably how any git operation a
user requests would actually happen, but nothing in any of the three
prompts gives the model git-specific policy or guardrails. The only
git-adjacent string matches are incidental: `grep_search`'s
description analogizes its output to `git grep -nI` (a format
comparison, not a git feature), and `CLI Prompt.md`'s "checkpoint"
references (see Compaction above) turn out to mean a
conversation/session save-point, not a git-based code checkpoint —
worth explicitly distinguishing from `agent-git-vcs.md`'s §3
(OpenCode's/Gemini CLI's shadow-git checkpoint systems), since the
terminology overlap invites exactly that confusion. This places
Antigravity alongside Cursor, Windsurf, Warp, and Replit in this doc's
"confirmed near-total absence" bucket — the fifth leaked source with a
rich tool surface elsewhere but genuine git thinness.
