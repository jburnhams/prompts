# Crush

- **Type**: Coding agent (Charm's terminal AI coding agent)
- **License**: FSL-1.1-MIT (source-available, converts to MIT after 2 years
  per version)
- **Source**: https://github.com/charmbracelet/crush
- **Retrieved from**: `main` branch,
  `internal/agent/templates/` (2026-07-10)

Crush's prompts are Go templates (`.tpl`) plus a few plain Markdown tool
descriptions, rendered at runtime with session-specific data. This is the
complete contents of the `templates/` directory. Crush also reads
`AGENTS.md`/`CRUSH.md`/`CLAUDE.md`/`GEMINI.md` files from the working
directory for project-specific instructions, layered on top of these.

## Files

- `coder.md.tpl` — the main system prompt: persona, critical rules
  (autonomy, conciseness, no unsolicited comments, git/commit constraints,
  security-only-defensive stance, skill loading), and tool-use guidance.
- `initialize.md.tpl` — prompt used the first time Crush runs in a new
  project (e.g. to bootstrap a `CRUSH.md`).
- `task.md.tpl` — prompt for a delegated sub-task/sub-agent run.
- `summary.md` — prompt for summarizing conversation history.
- `title.md` — prompt for auto-generating a session title.
- `agentic_fetch_prompt.md.tpl` — prompt for the web-fetch sub-agent (fetch
  + summarize/answer questions about a URL).
- `agent_tool.md` — tool description for the general-purpose search
  sub-agent ("Task"-style tool).
- `agentic_fetch.md` — tool description for the agentic-fetch tool itself.

## Tool surface

- **Shell**: `bash` — the `description` parameter is **mandatory** on
  every bash call ("CRITICAL: The `description` parameter is REQUIRED
  for all bash tool calls. Always provide it"), a stricter requirement
  than most sources' softer "explain non-trivial commands" framing.
- **Search**: `glob`/`grep`/`ls`/`view` are explicitly the tool set given
  to the delegated search sub-agent (see below) — the main agent
  presumably has direct access to the same tools plus editing ones, per
  `agent_tool.md`'s framing.
- **Editing**: `edit`/`multiedit` — with an explicit denial of tools that
  don't exist in Crush ("Never attempt 'apply_patch' or 'apply_diff' -
  they don't exist"), i.e. real evidence a model trained on another
  tool's conventions (Codex's `apply_patch`, or a generic "apply_diff"
  some other agent might expose) will hallucinate it here if not
  explicitly told not to.
- **Web fetch — two tiers, not one**: a plain `fetch` tool ("use fetch for
  raw content or API responses") plus a separate, more expensive
  `agentic_fetch` **sub-agent** that can "extract, summarize, and answer
  questions" about a URL rather than just returning raw bytes — a
  cost/capability tradeoff made explicit in the tool description itself,
  not left for the model to guess.
- **Code execution**: none beyond `bash`.
- **Multimodal**: not addressed in what's collected here.
- **Sandbox/isolation**: not specified — runs directly on the user's
  machine.
- **Extensibility**: skills (loaded via `view` on a matching skill's
  location, mandatory before acting per the critical rules), plus
  `agent_tool.md`'s general-purpose search delegate (Task-style,
  read-only-scoped).

## Sub-agents

Two sub-agents, both with their **complete system prompts captured as
separate template files** (`task.md.tpl`, `agentic_fetch_prompt.md.tpl`)
— alongside Copilot Chat, one of only two sources in this collection
with the sub-agent's own prompt text available, not just the
orchestrator-side tool description.

- **Search sub-agent** (`agent_tool.md` describes it; `task.md.tpl` is
  its system prompt) — scoped to exactly `glob, grep, ls, view` (no
  editing, no bash). Its prompt is strikingly terse-by-design: "you
  should be concise, direct, and to the point, since your responses will
  be displayed on a command line interface... One word answers are
  best... You MUST avoid text before/after your response, such as 'The
  answer is <answer>.'" — a much harder terseness constraint than the
  main `coder.md.tpl` persona uses for the orchestrator itself. Also
  mandates absolute (not relative) file paths in its output, presumably
  because the result gets folded into a different working context than
  the one the sub-agent ran in.
- **`agentic_fetch` web sub-agent** (`agentic_fetch_prompt.md.tpl`) — a
  persona swap to "a web content analysis agent for Crush," with its own
  tool subset (`web_search`, `web_fetch`, plus `grep`/`view` for large
  fetched-content files) and a fully specified output contract: answer
  first, then a mandatory `## Sources` section listing every URL that
  contributed — plus a worked example decomposing one broad question
  ("Rust vs Go for web services") into four narrower searches. This is
  the same fetch-vs-agentic_fetch tiering noted in "Tool surface" above,
  but here grounded in the sub-agent's actual instructions rather than
  just the tool description's one-line cost/capability tradeoff note.
- **Protocol**: both sub-agent prompts inject the same `<env>` block
  (working directory, platform, date — `task.md.tpl` adds git-repo
  status) that the main `coder.md.tpl` prompt gets, so sub-agents share
  the orchestrator's environment context even though they run under a
  fully different persona and reduced tool set. Neither file describes
  concurrency rules or how the orchestrator should handle the returned
  text — unlike Gemini CLI's explicit file-conflict concurrency mandate
  or Claude Code's "launch multiple agents concurrently" instruction,
  parallel-sub-agent guidance isn't captured in what's collected here.

## Compaction

Already fully captured in this folder's `summary.md`, not previously
written up as its own section. See
[`agent-context-compaction.md`](../agent-context-compaction.md) for the
cross-source comparison this feeds into.

- **The bluntest "you will lose everything" framing in this
  collection**: "This summary will be the ONLY context available when
  the conversation resumes. Assume all previous messages will be lost.
  Be thorough." No transcript-lookup recovery pointer is offered the
  way Claude Code's and Copilot Chat's compaction prompts provide — the
  summary genuinely is treated as the sole surviving record, not a
  lossy pointer into a still-readable full history.
- **A 5-section structured template**, the shortest of the structured
  templates surveyed but still opinionated about content: Current State
  (exact user request, progress, current work, specific next steps —
  explicitly "not vague"), Files & Changes (modified/read/not-yet-touched,
  with file paths and line numbers), Technical Context (architecture
  decisions and *why*, patterns followed, commands that worked vs.
  failed and why), Strategy & Approach (why this approach over
  alternatives, gotchas, assumptions, blockers), Exact Next Steps.
- **The "Exact Next Steps" section is explicitly example-driven about
  what NOT to do**: "Don't write 'implement authentication' — write:
  1. Add JWT middleware to src/middleware/auth.js:15..." — a concrete
  before/after example baked into the prompt itself, not just an
  abstract instruction to be specific.
- **No length limit stated** — "err on the side of too much detail
  rather than too little. Critical context is worth the tokens" — the
  opposite instinct from sources that cap summary output tokens
  (Codex's minimal prompt, OpenCode's 4,096-token cap, Claude Code's
  20,000-token summary budget).
- **No trigger/threshold information captured** — same caveat as Goose:
  this is the prompt text alone, not the surrounding Go orchestration
  code that would show what actually decides when to compact.

## Turn output: session titles

Already fully captured in this folder's `title.md`, not previously
written up as its own section. See
[`agent-turn-output.md`](../agent-turn-output.md) for the cross-source
comparison this feeds into.

- **Generated from the first message only**: "You will generate a
  short title based on the first message a user begins a conversation
  with" — a one-shot decision at session start, not something
  reconsidered as the conversation evolves.
- **Concrete, code-adjacent format rules stated directly in the
  prompt**: same language as the user's message, ≤50 characters, one
  line, no quotes or colons, and — notably — "the entire text you
  return will be used as the title," meaning there's no separate
  parsing/extraction step expected on the code side; the model's raw
  output is the title verbatim.
- No trigger/model information captured beyond the prompt text itself
  (not confirmed whether this runs on a separate cheap model or the
  main session model).

## Self-verification and testing

See [`agent-self-verification.md`](../agent-self-verification.md) for
the cross-source comparison this feeds into. Crush is prompted-only
(§7 there) but by far the densest example of that bucket found in this
collection — testing/verification language recurs at nearly every
structural checkpoint of `coder.md.tpl`, with no code-level enforcement
confirmed in these prompt-only files.

- **Named as a top-level critical rule**: `<critical_rules>` (the block
  explicitly framed as overriding everything else) states plainly,
  "**TEST AFTER CHANGES**: Run tests immediately after each
  modification."
- **A per-edit cadence, not just end-of-task**: the `<workflow>`
  section's "While acting" list runs "After each change: run tests" /
  "If tests fail: fix immediately" — closer to Jules's per-action gate
  (synthesis doc §6) than to a single pre-submit check, though here
  it's instruction-only, with no tool blocking the next edit if a test
  wasn't actually run.
- **A separate "Before finishing" checklist**, distinct from the
  per-edit rule above: "Verify ENTIRE query is resolved... Cross-check
  the original prompt and your own mental checklist; if any feasible
  part remains undone, continue working instead of responding. Run
  lint/typecheck if in memory. Verify all changes work."
- **A dedicated `<task_completion>` block** spells out think →
  implement → verify as three explicit phases, closing with: "Re-read
  the original request and verify each requirement is met. Check for
  missing error handling, edge cases, or unwired code. Run tests to
  confirm the implementation works. Only say 'Done' when truly done -
  never stop mid-task."
- **A dedicated `<testing>` block is the richest concentration of this
  language in the prompt**, and is the one place in this entire
  collection where a prompt uses the term "self-verification"
  explicitly: "Use self-verification: write unit tests, add output
  logs, or use debug statements to verify your solutions... If tests
  fail, fix before continuing... For formatters: iterate max 3 times to
  get it right; if still failing, present correct solution and note
  formatting issue." That "max 3 times" clause is a bounded-retry cap,
  unusually specific for a purely prompted (§7) mechanism.
- **A mechanically-sourced input, worth distinguishing from a true
  gate (§8-adjacent)**: when `.Config.LSP` is populated, tool output
  automatically includes lint/typecheck diagnostics alongside normal
  results — a real non-LLM signal injected into context — but nothing
  in the captured prompt blocks completion if the model just ignores
  it; the instruction ("Fix issues in files you changed") is still
  purely prompted, so this stops short of a genuine §2 deterministic
  gate.
- **Persisted across sessions**: `memory_instructions` treats
  "Build/test/lint commands" as first-class content worth remembering,
  reinforcing test-running as a standing habit rather than a one-off
  ask.
- No separate-LLM judge/reviewer call and no `/review`-style command
  exist anywhere in this folder — the two sub-agent prompts
  (`task.md.tpl`, `agentic_fetch_prompt.md.tpl`) are read-only
  (`glob`/`grep`/`ls`/`view` only, per `agent_tool.md`), so neither
  could run or verify code even in principle.

## Permissions and approval

See [`agent-permissions-approval.md`](../agent-permissions-approval.md)
for the cross-source comparison this feeds into. No named discrete
modes — instead a continuous, principle-based policy built on a short
enumerated stop-list, layered with hardcoded named-action gates for a
handful of specific git operations.

- **The general heuristic is consequence-based, not command-pattern-
  based**: `<decision_making>`'s "Make decisions autonomously" list
  ("Search to find the answer... Try most likely approach... make the
  most reasonable assumptions... and proceed instead of waiting for
  clarification") is bounded by an explicit stop-list — "Only
  stop/ask user if: Truly ambiguous business requirement / Multiple
  valid approaches with big tradeoffs / **Could cause data loss** /
  Exhausted all attempts and hit actual blocking errors." This is the
  cleanest example in this doc's survey of continuous, LLM-judged risk
  classification stated directly as prompt text rather than a static
  list.
- **A separate, stronger tier: named-action rules inside
  `<critical_rules>`, explicitly framed as overriding everything
  else**: "**NEVER COMMIT**: Unless user explicitly says 'commit'."
  / "**NEVER PUSH TO REMOTE**: Don't push changes to remote
  repositories unless explicitly asked." / "**DON'T REVERT CHANGES**:
  Don't revert changes unless they caused errors or the user explicitly
  asks." These read as per-instance, ask-every-time rules — nothing in
  the prompt suggests a standing "yes" persists once a user has
  approved a commit or push once.
- **A scoping rule that functions as a soft tool-level allowlist**:
  "Never use `curl` through the bash tool it is not allowed use the
  fetch tool instead" — forcing network calls through one specific
  tool rather than raw shell, enforced entirely at the prompt level (no
  evidence of code-level enforcement in these files).
- **A transparency requirement for risky commands, distinct from a
  hard block**: "When running non-trivial bash commands (especially
  those that modify the system): Briefly explain what the command does
  and why you're running it... Simple read-only commands (ls, cat,
  etc.) don't need explanation." A binary read-only-vs-system-modifying
  split, but the consequence of "risky" here is a mandatory one-line
  explanation in the model's own output, not necessarily a UI approval
  pause — the actual approval mechanism, if any, would live in Crush's
  tool-call layer outside these prompt files.
- **Sandbox/isolation**: confirmed absent — runs directly on the user's
  machine, no containerization referenced anywhere in the captured
  files.

## Git and version control

See [`agent-git-vcs.md`](../agent-git-vcs.md) for the cross-source
comparison this feeds into. The most fully worked-out example in this
collection of an explicit, standing git policy embedded directly in a
"critical rules" block — a two-tier system: continuous LLM judgment
for general risk, plus three hardcoded named-action gates specifically
for git.

- **A named policy triad, stated as rules that override everything
  else**: "**NEVER COMMIT**: Unless user explicitly says 'commit'...
  **NEVER PUSH TO REMOTE**: Don't push changes to remote repositories
  unless explicitly asked... **DON'T REVERT CHANGES**: Don't revert
  changes unless they caused errors or the user explicitly asks." This
  is the inverse of a checkpoint system — a rule constraining when the
  *agent itself* may undo its own changes, not an automatic
  pre-edit snapshot mechanism. The closest thing to a stated safety
  valve is the general decision-making stop-list's "Could cause data
  loss" trigger (covered under Self-verification/Permissions above),
  which governs destructive git operations the same way it governs
  any other high-consequence action.
- **A real capture gap on commit-message format**: the commit rule
  points to a named template — "follow the `<git_commits>` format from
  the bash tool description exactly, including any configured
  attribution lines" — but that template isn't present in this
  folder; `coder.md.tpl` is only the main persona template, and the
  bash tool's own description (where `<git_commits>` presumably lives,
  possibly including a co-author trailer analogous to Claude Code's)
  is a separate file not captured here.
- **No PR-creation tool, no `gh` invocation guidance, and no PR
  description template found anywhere** — push is gated the same
  per-instance, explicit-ask-only way as commit, with no promotion to
  a standing approval once granted once.
- **No worktree isolation**: the two sub-agents (search, web-fetch)
  inherit the identical `<env>` block as the main agent
  (`WorkingDir`/`IsGitRepo`/`Platform`/`Date`), implying they operate
  against the same working tree rather than an isolated copy, with no
  concurrency/conflict-avoidance guidance stated for parallel
  sub-agents.
- **Git as a read-only research tool, not just a modification
  target**: "Use `git log` and `git blame` for additional context when
  needed," and a `<bash_commands>` example combining inspection
  commands (`git status && git diff HEAD && git log -n 3`) — purely
  informational usage, separate from the write-gated triad above.
- **A live git-status snapshot is injected into every prompt**: the
  `<env>` block includes "Is directory a git repo" and "Git status
  (snapshot at conversation start - may be outdated)" — passive
  context, not a behavioral rule, but worth noting as the one place
  git state reaches the model automatically rather than via a tool
  call.
- No branch-naming convention, no force-push policy, no
  protected-branch language found anywhere.

## Memory, learnings, and retrospectives

See [`agent-memory-learning.md`](../agent-memory-learning.md) for the
cross-source comparison this feeds into. Crush has no memory tool, but
it is one of the few sources whose prompt gives the model a **content
taxonomy for what belongs in the instruction file**, and it threads
"check memory" through the rest of the workflow rather than mentioning
it once.

- **`<memory_instructions>`, in full**: "Memory files store commands,
  preferences, and codebase info. Update them when you discover:
  Build/test/lint commands / Code style preferences / Important codebase
  patterns / Useful project information." Four categories, phrased as
  discovery triggers — the same shape as Amp's `AGENTS.md` content list
  and a compressed version of Qoder's four-category taxonomy.
- **Memory is wired into the operating rules, not siloed**: "FOLLOW
  MEMORY FILE INSTRUCTIONS: If memory files contain specific
  instructions, preferences, or commands, you MUST follow them" sits in
  the numbered core rules; the testing section says "Check memory for
  test commands" and "**Suggest adding commands to memory if not
  found**" (the ask-a-human write path again); the workflow says "Check
  memory for stored commands" and "Run lint/typecheck if in memory";
  and the ambiguity rule says to "make the most reasonable assumptions
  based on project patterns **and memory files**" rather than stopping
  to ask.
- **The files themselves** are `AGENTS.md`/`CRUSH.md`/`CLAUDE.md`/
  `GEMINI.md` loaded from the working directory (see the Tool surface
  section above), with `initialize.md.tpl` bootstrapping a `CRUSH.md`
  by first looking for existing rule files from *other* vendors
  (`.cursor/rules/*.md`, `.cursorrules`,
  `.github/copilot-instructions.md`, `claude.md`, `agents.md`) — the
  same cross-vendor import idea Claude Code's `/init` implements.
- **No machine-written store and no retrospective**: "memory" here always
  means the human-owned instruction file, and nothing distils a finished
  session.

## Context-file loading

Read 2026-08-30 from `internal/config/config.go`, `internal/config/load.go`,
`internal/agent/prompt/prompt.go` and the copy of `coder.md.tpl` stored
here, at `1ea2714`.

- **Sixteen default context paths, and the list is mostly
  case-variants.** `defaultContextPaths` =
  `.github/copilot-instructions.md`, `.cursorrules`, `.cursor/rules/`,
  `CLAUDE.md`, `CLAUDE.local.md`, `GEMINI.md`, `gemini.md`, `crush.md`,
  `crush.local.md`, `Crush.md`, `Crush.local.md`, `CRUSH.md`,
  `CRUSH.local.md`, `AGENTS.md`, `agents.md`, `Agents.md`. Enumerating
  casings is Crush's substitute for case-insensitive lookup.
- **The list is sorted, then compacted, then deduped again by lowercased
  path — and the sort is what makes the casings safe.**
  `load.go:601-604` does `append(defaults, user...)`, `slices.Sort`,
  `slices.Compact`; `prompt.go:loadContextFiles` then keys a map on
  `strings.ToLower(expanded)` and skips repeats. ASCII sort puts
  `CRUSH.md` before `Crush.md` before `crush.md`, so the uppercase variant
  claims the shared lowercase key first and the file is found on a
  case-sensitive filesystem. Two consequences fall out of this that are
  worth stating plainly:
  - **User-configured `context_paths` do not take precedence** — they are
    appended to the defaults and then sorted into the same alphabetical
    list, so their position in the prompt is an accident of their name.
  - **Load order is alphabetical, not by authority**: `.cursor/rules/`,
    `.cursorrules`, `.github/copilot-instructions.md`, then `AGENTS.md`,
    `CLAUDE.md`, `CRUSH.md`, `GEMINI.md`. Crush's own eponymous file lands
    third among the four, purely because `C` sorts where it does.
- **A directory entry is walked recursively and every file in it is loaded**
  (`processContextPath` → `filepath.WalkDir`), with no extension filter and
  no depth limit — so `.cursor/rules/` contributes its whole subtree,
  binary files included, as UTF-8 strings.
- **Working-directory only. No ancestor walk, no subdirectory discovery, no
  JIT loading, no imports, no frontmatter, no size cap.**
  `filepathext.SmartJoin(WorkingDir, p)` and one `os.Stat`.
- **Global paths are a separate list**, defaulting to
  `<crush config dir>/CRUSH.md` and `<parent of config dir>/AGENTS.md`,
  also sorted; they render into a different template block.
- **Envelope is XML-ish, and unescaped.** `coder.md.tpl`:

  ```
  # Project-Specific Context
  Make sure to follow the instructions in the context below.
  <project_context>
  <file path="{{.Path}}">
  {{.Content}}
  </file>
  ...
  </project_context>
  ```

  with `<user_preferences>` for the global tier, introduced as "personal
  content added by the user that they'd like you to follow no matter what
  project you're working in". The template is executed with Go's
  **`text/template`, not `html/template`** (`prompt.go:12`), so neither
  `.Path` nor `.Content` is escaped: a path containing `"` breaks the
  attribute, and a context file containing `</file>` closes its own block.
- **`initialize_as`** (default `AGENTS.md`) names which file `/init` writes,
  independently of which files are read — so a project can be initialized
  into `docs/LLMs.md` while still reading all seventeen defaults.

## Vision and multimodal

**Correction.** `agent-tool-surfaces.md` §5 listed Crush under "not
addressed at all." The `view` tool reads images
(`internal/agent/tools/view.go`, read 2026-08-30 @ `1ea2714`).

**Capability travels to the tool through `context.Context`.**
`internal/agent/tools/tools.go` defines `SupportsImagesContextKey` and
`GetSupportsImagesFromContext(ctx)`; `internal/agent/agent.go:875` sets it
per call from `largeModel.CatwalkCfg.SupportsImages`. Both `view.go` and
`mcp-tools.go` consult it. This is a different placement from the other
harnesses in this collection — Cline, Roo Code and Zed strip images at
request-build time; Crush refuses at the tool, returning a text error that
**names the model**:

```
This model (%s) does not support image data.
```

Cheaper and clearer for that call, at the cost that the image never enters
history — switching to a sighted model mid-session does not recover the
earlier look (contrast Cline's explicit note that it does).

**MIME is sniffed from magic bytes, not the extension**, with the reason in
a comment:

> Some tools save files with a mismatched extension (e.g. pinchtab writes
> JPEG bytes to a .png file). Providers like Anthropic strictly validate the
> media type against the base64 magic bytes and 400 on mismatch, so prefer
> the sniffed type whenever it identifies a supported image format.

A screenshot pipeline produces exactly these files, so this is a rule worth
copying rather than a curiosity. Images are also subject to the same
`MaxViewSize` cap as text, refused with `Image file is too large (%d bytes).
Maximum size is %d bytes` before any read.

**No browser and no screenshot tool.** `internal/ui/image/image.go` is a
terminal renderer, not a model-facing capability. The two-tier
`fetch`/`agentic_fetch` split documented under Tool surface remains Crush's
only web access.
