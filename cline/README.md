# Cline

- **Type**: Coding agent (VS Code / JetBrains / CLI extension)
- **License**: Apache-2.0
- **Source**: https://github.com/cline/cline
- **Retrieved from tag**: [`v3.20.4`](https://github.com/cline/cline/tree/v3.20.4/src/core/prompts) (2026-07-10)

Cline later restructured its repo into a monorepo (`apps/`, `sdk/`) where the
system prompt is composed differently. `v3.20.4` is the last tag with the
classic, single-file prompt layout, so it's used here for a clean read.

## Files

- `system.ts` — entry point; picks a prompt variant based on model family and
  assembles it with live context (cwd, shell, MCP servers, browser support).
- `model_prompts/claude4.ts` — the full system prompt used for Claude 4 models
  (tool definitions, rules, capabilities, objective).
- `model_prompts/claude4-experimental.ts` — an experimental variant of the
  above.
- `responses.ts` — templates for tool-result / error messages fed back to the
  model mid-conversation (not the system prompt itself, but part of the
  overall prompting strategy).

## Tool surface

- **Shell**: `execute_command` — generic, "tailor your command to the
  user's system," one command per tool call (this version predates native
  parallel tool-calling; see `coding-agent-approaches.md` §4).
- **Search**: `search_files` (regex-based), `list_files`, and
  `list_code_definition_names` — the last one lists source-definition
  symbols (classes/functions) rather than raw text matches, a lightweight
  AST-adjacent capability distinct from plain grep.
- **Code execution**: none beyond the shell.
- **Browser/web**: `browser_action` — a full **vision-based, Puppeteer
  browser control tool**: launch → click/type/scroll by pixel coordinate
  read off a returned screenshot → close. Explicitly exclusive ("only the
  `browser_action` tool can be used" while a browser session is open, no
  interleaving with other tools) and conditionally included via the
  `supportsBrowserUse` parameter passed into `SYSTEM_PROMPT()` — only
  shown to the model if the underlying provider/model actually supports
  image input.
- **Multimodal**: implicit in `browser_action` — every browser action
  except `close` returns a screenshot the model must visually interpret
  to pick click coordinates.
- **Sandbox/isolation**: none described — runs directly on the user's
  machine/VS Code environment.
- **Extensibility**: `use_mcp_tool`/`access_mcp_resource`/
  `load_mcp_documentation` for MCP servers, plus `new_task` for spawning a
  follow-on task and `plan_mode_respond` for its plan/act mode split.

## Turn output: session titles

Sourced from the live upstream repo's current monorepo layout (not the
`v3.20.4` tag stored in this folder) — see
[`agent-turn-output.md`](../agent-turn-output.md) for the cross-source
comparison this feeds into.

**Confirmed absence, not just unchecked**: Cline generates no AI
session title at all. `HistoryItem` (both the VS Code extension and the
newer CLI SDK) has only a raw `task`/`prompt` string field — no
dedicated title field exists in the data model. The CLI's history
rendering falls back to `metadata?.title || prompt || "Untitled"`,
truncated to 40 characters — and `metadata.title` is populated only by
an explicit user command (`cline history update --title`), never by an
LLM call. Fork-session titling is pure string manipulation (reuse the
source title or first message text, append " (fork)") — confirmed by
reading the function body directly, no model call inside it. The
cheapest possible answer to "how do you title a session": don't
generate one, format the raw first message instead.

## Sub-agents

**Cline has no sub-agent delegation tool in this snapshot** — `new_task`
is a different, easily-confused mechanism worth calling out explicitly:
it doesn't launch a second, independent agent that reports back. It
generates "a detailed summary of the conversation so far" (explicit
five-part structure: current work, key technical concepts, relevant
files/code, problem solving, pending tasks/next steps) and hands that
summary to the **user** as a preview, who can then choose to start a
*fresh conversation* preloaded with it, or keep chatting in the current
one. It's a context-compaction / session-handoff tool aimed at working
around context-window limits across a single continuous task, not a
parallel-delegation or divide-and-conquer mechanism — the new "task" runs
in place of the current one, not alongside it, and there's no
orchestrator/sub-agent relationship or result-passing-back protocol at
all. Contrast this directly with Claude Code's `Task` tool (see
`leaked/claude-code/README.md`), which spawns a genuinely separate agent
that returns a report *to* the still-running orchestrator.

## Compaction

See [`agent-context-compaction.md`](../agent-context-compaction.md) for
the cross-source comparison this feeds into. All evidence lives in
`responses.ts:7-16` — nothing relevant elsewhere in the folder. Cline
turns out to layer **three separate, structurally distinct
context-management mechanisms**, none of which call each other in what's
captured here, on top of the session-handoff `new_task` tool documented
above:

- **Silent, non-summarized truncation — no LLM call at all**:
  `contextTruncationNotice()` — "Some previous conversation history with
  the user has been removed to maintain optimal context window length.
  The initial user task and the most recent exchanges have been
  retained for continuity, while intermediate conversation history has
  been removed." Keep-first-and-last, drop-the-middle, with the dropped
  middle simply gone — no summary is generated to stand in for it. This
  is more primitive than every other compaction mechanism surveyed in
  this collection, which all either run real LLM summarization or a
  heuristic trim that still preserves some semantic content (OpenCode's
  `prune`, Claude Code's `microcompact`); Cline's plain deletion has no
  recovery story at all, not even a lossy one.
- **A separate, real LLM-summarization path — gated on explicit user
  approval, not silent**: `condense()` — "The user has accepted the
  condensed conversation summary you generated... It's crucial that you
  respond by ONLY asking the user what you should work on next. You
  should NOT take any initiative or make any assumptions about
  continuing with work... you should NOT reference information outside
  of what's contained in the summary for this response." This confirms
  a distinct, model-generated summary the user must accept before it
  takes effect — a third trigger shape not matching this doc's existing
  "proactive silent" vs. "reactive-on-error" vs. "manual command"
  categories: **model-proposes, user-approves**. The prompt that
  actually asks the model to generate the summary in the first place
  isn't in any captured file — only this post-acceptance acknowledgment
  is — so the summarization prompt's shape (structured vs. free text)
  is unconfirmed.
- **A distinctive post-compaction behavioral lockdown**: unlike every
  other surveyed source's post-compaction instruction (which is about
  *how to resume work*), Cline's explicitly tells the model *not* to
  resume work — no suggesting file changes, no reading files, just ask
  what to do next. No other source in this collection's compaction
  survey does this.
- **A narrower, targeted dedup, scoped only to file reads**:
  `duplicateFileReadNotice()` — "This file read has been removed to
  save space in the context window. Refer to the latest file read for
  the most up to date version of this file." Conceptually a narrow
  cousin of Claude Code's `microcompact` (heuristic placeholder
  replacement of stale tool output) but limited to file-read results
  specifically, not general tool output.
- **Distinct from `new_task`** (above): `new_task` ends the current
  task and starts a genuinely new, separate conversation; these three
  mechanisms all operate *within* the same ongoing task, trimming its
  history in place. Cline has (at least) four separate answers to "the
  context is getting too full" — silent deletion, approved
  summarization, targeted dedup, and full session handoff — rather than
  one unified compaction pipeline.

## Self-verification and testing

See [`agent-self-verification.md`](../agent-self-verification.md) for
the cross-source comparison this feeds into. One of the thinner §7
(prompted-only) instances surveyed — no TESTING/VALIDATION section, no
bounded-retry pattern, no "hidden tests" language anywhere across any
of the three system-prompt variants (`system.ts`, `model_prompts/
claude4.ts`, `model_prompts/claude4-experimental.ts`).

- **`attempt_completion`'s gate is procedural, not a correctness
  check**: its description says the tool "CANNOT be used until you've
  confirmed from the user that any previous tool uses were successful,"
  and instructs the model to ask itself in `<thinking>` tags whether
  that's true before calling it — but the "success" being confirmed is
  whether the last tool call went through (did the file write actually
  happen), not whether the resulting code is correct. Entirely
  prompted; no structural check in `system.ts`/`responses.ts` was found
  blocking the call the way Roo Code's `AttemptCompletionTool.ts` does.
- **Verification is otherwise folded into the browser tool, and only
  optionally**: "This tool may be useful at key stages of web
  development tasks... to verify the result of your work. You can
  analyze the provided screenshots to ensure correct rendering..." —
  conditional on browser support (`supportsBrowserUse`) and phrased as
  something the model might choose to do ("if you want to test your
  work"), not a mandate.
- **A passive, automatic linter-surfacing channel exists but isn't a
  gate**: `responses.ts`'s post-edit tool-result templates
  (`fileEditWithUserChanges`/`fileEditWithoutUserChanges`) both append
  a `newProblemsMessage` — the system prompt tells the model the tool
  result "may include... Linter errors that may have arisen due to the
  changes you made, which you'll need to address." Diagnostics are
  surfaced automatically after every edit, but nothing forces the model
  to act on them before declaring the task done.

## Permissions and approval

See [`agent-permissions-approval.md`](../agent-permissions-approval.md)
for the cross-source comparison this feeds into. Built on a **binary
per-command self-tag**, not a tri-level classifier like OpenHands' —
plus a separate, unrelated static deny-list for file *paths*.

- **`execute_command`'s `requires_approval` boolean**: "Set to 'true'
  for potentially impactful operations like installing/uninstalling
  packages, deleting/overwriting files, system configuration changes,
  network operations, or any commands that could have unintended side
  effects. Set to 'false' for safe operations like reading
  files/directories, running development servers, building projects,
  and other non-destructive operations." The model self-classifies on
  every call; the tag is only consulted "in case the user has
  auto-approve mode enabled" — a client-side on/off toggle referenced
  by name and pointed at Cline's own public docs
  (`docs.cline.bot/features/auto-approve`), but never defined
  mechanically in the prompt itself.
- **A count-based escalation, distinct from any single command's risk
  level**: `autoApprovalMaxReached()` — "Auto-approval limit reached.
  The user has provided the following feedback to help guide you" —
  implies a numeric ceiling on consecutive auto-approved actions before
  the user must manually re-engage, an escalation trigger based on
  cumulative count rather than on a changed command or an individual
  risk tier.
- **Denial is an ordinary conversational turn, not a hard stop**:
  `toolDenied()` — "The user denied this operation" — surfaced back
  into the conversation as a tool-result string the model must react
  to.
- **A separate, persistent, path-scoped deny-list — `.clineignore`**,
  orthogonal to command-risk tagging: "Access to ${path} is blocked by
  the .clineignore file settings. You must try to continue in the task
  without using this file, or ask the user to update the .clineignore
  file." Real code enforces this, not just prompt convention —
  `formatFilesList()` calls `clineIgnoreController.validateAccess()`
  and visually marks blocked files with a lock symbol before the list
  even reaches the model. A static, gitignore-style pattern-matched
  mechanism, but scoped only to file *paths*, never to shell commands
  or arbitrary tool calls — Cline's closest analog to Claude Code's
  settings-file allow/deny arrays or OpenHands' risk tiers, just on a
  narrower axis.
- **Plan/Act mode is prompted, not structurally enforced — a real
  contrast with Claude Code's harness-typed `plan` mode** (see
  `leaked/claude-code/architecture-notes.md`'s Permission system
  section): the only stated tool-access rule is the inverse for ACT
  mode ("access to all tools EXCEPT the plan_mode_respond tool")
  — nothing in the captured text says PLAN mode *removes* access to
  `execute_command`/`write_to_file`. Mode transition is user-driven by
  convention only: the model can ask "the user to switch you back to
  ACT MODE" but has no dedicated forcing tool, unlike Claude Code's
  `ExitPlanMode`.
- **`attempt_completion`'s gate is procedural, not risk-based** —
  already covered under Self-verification above: a self-check on
  finishing, not on individual risky actions.
- **Sandbox/isolation**: none described — runs directly on the user's
  machine/VS Code environment, no complementary isolation layer to
  cross-reference against the approval mechanism.
- No PreToolUse-equivalent hook mechanism found anywhere in the four
  captured files — Cline's gate is entirely the `requires_approval`
  self-tag plus the client-side auto-approve setting, with
  `.clineignore` as the only other enforcement point.

## Git and version control

See [`agent-git-vcs.md`](../agent-git-vcs.md) for the cross-source
comparison this feeds into. Clean, confirmed-empty on five of six axes
(commit conventions, worktree isolation, branch rules, auto-commit
config, PR/push workflow) — `execute_command` is a fully generic shell
tool with no git-specific instruction anywhere in the four prompt
files. The sixth axis yields a real but narrower-than-expected finding.

- **The publicly-documented "Checkpoints" feature is named but never
  mechanically specified**: the word appears exactly once, inside a
  list of Cline-docs sub-pages the model is told to fetch if asked
  "can Cline do..." ("`features` (Auto approve, Checkpoints, Cline
  rules, Drag & Drop, Plan & Act, Workflows, etc)") — a bare topic
  label pointing at documentation, not a description of what the
  feature does. This is a genuine capture gap for that specific
  feature, not a confirmed absence of it — Cline's public docs
  independently confirm Checkpoints exists as a product feature.
- **A separate, directly-confirmed mechanism does exist, but it's
  narrower — automatic in-memory file-content reversion on two
  specific failure paths, not a git-based or browsable task-level
  snapshot system**: if a task resumes after an interrupted
  `replace_in_file`/`write_to_file`, "the file was reverted back to
  its original state before the interrupted edit"; if a SEARCH/REPLACE
  block fails to match, "the file was reverted to its original
  state," with the tool result literally re-embedding the pre-edit
  file content. Both fire automatically on failure, hold the pre-edit
  string in the harness's memory (no stash/shadow-commit language
  anywhere), and give the user no way to browse or select an arbitrary
  earlier state — a materially narrower mechanism than what
  "Checkpoints" implies publicly, with no indication in the prompt
  text that the two are even the same system.
- No commit tool, commit-message template, or co-author trailer
  anywhere — contrast directly with Claude Code's dedicated "#
  Committing changes with git" section.
- No `git worktree` or parallel-isolation concept — consistent with
  Cline having no sub-agent/parallel-task delegation mechanism at all
  in this snapshot (`new_task` is a session-handoff tool, not a
  parallel worker, per the Sub-agents section above).

## Memory, learnings, and retrospectives

See [`agent-memory-learning.md`](../agent-memory-learning.md) for the
cross-source comparison this feeds into. No memory-write tool appears in
the captured prompt-assembly layer; what Cline contributes is the
collection's most **promiscuous rules-file reader**.

- **Four rule sources, each with its own injected header** in
  `responses.ts`: a global `.clinerules/` directory ("where the user has
  specified instructions for all working directories"), a root-level
  `.clinerules/` directory, a root-level `.clinerules` file — and then
  two other vendors' files loaded as first-class inputs:
  `windsurfRulesLocalFileInstructions` (`.windsurfrules`) and
  `cursorRulesLocalFileInstructions` (`.cursorrules`). Roo Code, Crush,
  and Claude Code all read foreign rules files at *bootstrap* time;
  Cline reads them on **every** session, as ordinary context. Alongside
  these sits `.clineignore`, injected with the same header pattern —
  instruction files and access-control files sharing one delivery
  mechanism.
- **Everything is human-authored**: the captured files contain no
  create/update/delete memory vocabulary, no memory storage description,
  and no instruction to write anything back to `.clinerules`. Cline's
  widely-used "Memory Bank" is a *community convention* — a set of
  markdown files the user tells Cline to maintain via custom
  instructions ("update memory bank") — not a shipped mechanism visible
  in this capture, and the shipped `new_rule` tool is likewise outside
  what these files cover.
- **The stated motivation for the convention** is worth recording even
  though it is documentation rather than prompt text: Cline's memory
  resets completely between sessions, so all project knowledge must be
  externalized into files the next session re-reads. That is the same
  premise Windsurf's `<memory_system>` states — and the two products
  answered it in opposite ways (a database tool vs. a user-maintained
  file convention).

## Context-file loading

Read 2026-08-30 from `apps/vscode/src/core/context/instructions/user-instructions/`
(`rule-helpers.ts` 467 lines, `rule-conditionals.ts` 153,
`frontmatter.ts` 59, `external-rules.ts` 49) at `48d6385`, plus the
prompt-side assembly in the copies stored here (`system.ts`,
`responses.ts`).

- **Four rule families, all read from the workspace root**: `.clinerules`
  (file or directory), `.cursorrules` + `.cursor/rules/*.mdc`,
  `.windsurfrules`, and `AGENTS.md` — plus a global `.clinerules/`
  directory and a **remote** tier (`GlobalInstructionsFile[]`, org-pushed
  instructions that never touch the repo).
- **Per-file user toggles are the distinctive mechanism.** Every rules file
  has a boolean in workspace/global state (`localClineRulesToggles`,
  `localCursorRulesToggles`, `localWindsurfRulesToggles`,
  `localAgentsRulesToggles`, …); `synchronizeRuleToggles` reconciles the
  toggle map against what is actually on disk on each refresh, and
  `getRuleFilesTotalContentWithMetadata` skips any path whose toggle is
  explicitly `false`. Cursor's two valid locations are synchronized
  separately and `combineRuleToggles`d so neither drops the other's entries.
  No other harness in the collection offers per-file opt-out from the UI —
  the closest is Claude Code's `claudeMdExcludes` glob setting.
- **Frontmatter conditionals are a tiny DSL with deliberate fail
  directions.** `evaluateRuleConditionals` walks the frontmatter keys and
  runs a registered evaluator per key; **unknown keys are ignored** (forward
  compatibility). The only implemented key is `paths`:
  - a non-array / malformed value → **fail-open** (conditional ignored,
    rule loads);
  - `paths: []`, or patterns that trim to nothing → **fail-closed** (rule
    never loads) — documented as the explicit way to disable a rule from
    inside the file;
  - `paths` present but no candidate paths in the evaluation context →
    fail-closed ("no evidence => do not activate path-scoped rules");
  - omitted entirely → the evaluator never runs, so the rule is universal.
- **Candidate paths can come from the user's prose.** `extractPathLikeStrings`
  scrapes path-shaped tokens out of the message text to allow first-turn
  activation of a path-scoped rule before any file has been touched. It
  strips fenced code blocks first ("to avoid extracting paths from pasted
  code"), removes URLs, requires either a slash or a `name.ext` shape, drops
  tokens over 300 chars, and rejects absolute paths and anything containing
  `..`. It is the only mechanism in the collection that decides which rules
  to load by parsing the *user's* text rather than tool arguments or the
  file tree.
- **A YAML parse error is fail-open in an unusual way**: the rule is
  emitted with its **raw frontmatter fence left in**, and the comment gives
  the reason — "so the LLM can still see the author's intended scoping
  (e.g., `paths:`) and reason about it, even if it cannot be evaluated
  reliably due to invalid YAML." Everywhere else, frontmatter is stripped
  before the model sees it.
- **A UTF-8 BOM bug, fixed in the parser.** `stripUtf8Bom` runs before the
  frontmatter regex because Node's `utf-8` decode leaves `﻿` in place,
  so a file saved by Windows Notepad as "UTF-8 with BOM" never matched
  `^---` and silently lost its frontmatter (`cline/cline#12151`). The only
  encoding-level context-file bug documented anywhere in this collection.
- **Per-file envelope is a bare relative path line**: `<relative
  path>\n<trimmed body>`, joined by blank lines — the most minimal in the
  collection. The tier framing comes one level up, from `responses.ts`
  templates that name the source and its scope, e.g.
  `# .clinerules/\n\nThe following is provided by a root-level .clinerules/
  directory where the user has specified instructions for this working
  directory (<cwd>)\n\n<content>`, with sibling variants for the global
  directory, `.windsurfrules`, `.cursorrules` and `.cursor/rules`.
- **Assembly order is fixed in `addUserInstructions`** (`system.ts`):
  preferred language → global `.clinerules` → local `.clinerules` →
  `.cursorrules` → `.cursor/rules` → `.windsurfrules` → `.clineignore`,
  under `==== USER'S CUSTOM INSTRUCTIONS` with the softening clause "should
  be followed to the best of your ability **without interfering with the
  TOOL USE guidelines**" — an explicit subordination of repo instructions
  to the harness's own tool contract, which only Gemini CLI and Zed also
  state.
- **Activated conditional rules are reported back to the UI** with a
  `workspace:` / `global:` / `remote:` prefix and the patterns that matched,
  so a user can see *why* a rule fired. No other loader surfaces its
  activation reasoning.

## Vision and multimodal

Read from source on 2026-08-30 (`cline/cline` @ `48d6385`, now a monorepo:
`apps/vscode/src/services/browser/`, `sdk/packages/llms/`,
`sdk/packages/shared/src/llms/`). Cross-harness comparison in
[`agent-vision-multimodal.md`](../agent-vision-multimodal.md).

**`browser_action`: one tool, six actions, a state machine in prose.** The
tool description (`cline/system.ts`) carries what the schema cannot — every
action but `close` returns "a screenshot of the browser's current state,
along with any new console logs"; the sequence "**must always start with**
launching the browser at a URL, and **must always end with** closing"; and
an exclusivity lock: "While the browser is active, only the `browser_action`
tool can be used… if you run into an error and need to fix a file, you must
close the browser, then use other tools to make the necessary changes, then
re-launch the browser to verify the result." The viewport is interpolated
into the description from settings (`${browserSettings.viewport.width}x…`)
so the coordinate space the model is told about cannot drift from the one it
gets, and clicks are specified as "the **center of the element**, not on its
edges."

Every mention of the tool — the tool block, the capabilities bullet, the
generic-task rule, the worked verify-loop example in the objective section —
is gated behind the same `supportsBrowserUse` flag, four separate ternaries
in one file. A model without browser support is never told browsers exist.

**Screenshot capture** (`BrowserSession.ts`): WebP by default with a PNG
retry on empty output (`useWebp` constructor flag), console and `pageerror`
listeners attached per action and detached after, a `pWaitFor` on 500 ms of
log inactivity capped at 3 s before the shot is taken, navigation with
`waitUntil: ["domcontentloaded", "networkidle2"]` at a 7 s timeout followed
by a `waitTillHTMLStable` poll — with the reasoning in comments
("`networkidle0` may not ever resolve, and not waiting could return page
content too early before js has loaded"). Each action returns
`{screenshot, logs, currentUrl, currentMousePosition}`.

**The image-in-tool-result bug, and the fix.**
`sdk/packages/llms/src/providers/middleware/split-tool-images.ts` is the
clearest statement of this failure mode found anywhere:

> The OpenAI Chat Completions wire format does NOT support multimodal tool
> messages — `role:"tool"` content must be a single string. The
> `@ai-sdk/openai-compatible` chat-messages converter therefore just
> `JSON.stringify`s the parts array. The image bytes survive as escaped
> base64 inside a string, which the model treats as ~50KB of opaque text and
> hallucinates the image's actual contents.

The middleware runs on the typed `LanguageModelV4Prompt` *before* the wire
converter: media parts inside a tool result are replaced with the text
`(see following user message for image)`, and a synthetic `role:"user"`
message carrying typed file parts is inserted immediately after the tool
message — so every downstream converter (Chat Completions, Anthropic,
Mistral, Bedrock) renders it natively. The header records that this replaced
a fetch-interceptor doing the same rewrite post-converter, and why the
middleware position is better: no JSON round-trip per request, covers
converters with their own message mapping, decoupled from the SDK's wire
shape.

**Two placeholders, two meanings** (`sdk/packages/shared/src/llms/media.ts`):

```ts
IMAGE_OMITTED_PLACEHOLDER     = "[media omitted: invalid or exceeds size limit]"
IMAGE_UNSUPPORTED_PLACEHOLDER = "[Image attached — this model cannot view images]"
```

with a comment on the second that states the rule the rest of the field
should copy: *"Substituted for image content at request-build time when the
target model does not advertise image input. **The stored conversation
history keeps the real image, so switching to an image-capable model
restores it.**"*

**Media budget.** `DEFAULT_MAX_IMAGE_ENCODED_BYTES` 5 MB,
`DEFAULT_MAX_IMAGE_DECODED_BYTES` 6 MB, `DEFAULT_MAX_TOTAL_MEDIA_BYTES` 8 MB
per request, `SUPPORTED_IMAGE_MEDIA_TYPES` = png/jpeg/gif/webp, and six
typed failure reasons (`unsupported_media_type`, `media_type_mismatch`,
`invalid_base64`, `encoded_limit`, `decoded_limit`, `total_limit`). Remote
`http(s)` image URLs, whose byte size is unknown at formatting time, are
charged the **full per-image cap** — "so URL media doesn't count as free" —
the only conservative accounting for unknown-size media in this collection.
A `GeneratedMedia` schema covers model-produced image/audio/video/file with
a refinement asserting modality matches media type.
