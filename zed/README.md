# Zed

- **Type**: Coding agent (AI-native code editor's built-in Agent Panel)
- **License**: GPL-3.0-or-later (with Apache-2.0 components where marked)
- **Source**: https://github.com/zed-industries/zed
- **Retrieved from**: `main` branch,
  `crates/agent/src/templates/` (2026-07-11)

Genuinely open source — not a leak. Zed's agent prompts are Handlebars
(`.hbs`) templates, rendered by its Rust core, published directly
alongside the editor's own source code. Flagged by the user after
noticing a leaked mirror of one of these files (`zed.md`) circulating
on a third-party aggregator repo (`asgeirtj/system_prompts_leaks`) —
worth fetching the real thing directly rather than relying on the
leaked copy, the same correction this collection has now made for
several other sources initially assumed to need `leaked/` treatment.

## Files

- `system_prompt.hbs` — the main system prompt (277 lines): persona,
  communication style, formatting, tool use, task execution rules.
- `experimental_system_prompt.hbs` — a shorter, differently-organized
  variant (156 lines) gated behind an experimental flag, sharing the
  opening persona line verbatim with `system_prompt.hbs` but
  reorganizing/trimming several sections.
- `edit_file_prompt_diff_fenced.hbs` — a SEARCH/REPLACE diff-format
  editing prompt, used when tool calls are disabled ("Tool calls have
  been disabled. You MUST respond using the SEARCH/REPLACE diff format
  only").
- `edit_file_prompt_xml.hbs` — an alternate, XML-tag-based editing
  prompt for the same no-tool-calls scenario.
- `create_file_prompt.hbs` — a minimal new-file-from-scratch prompt:
  "You MUST respond with the file's content wrapped in triple
  backticks... Tool calls have been disabled."
- `diff_judge.hbs` — a separate-LLM-call judge prompt: given a `{{diff}}`
  and a list of `{{assertions}}`, scores 0-100 how well the diff
  satisfies each assertion, with a required `<analysis>`/`<score>`
  structure. See Self-verification below.

## Tool surface

Genuinely minimal in what's captured — the prompt describes tool-use
*discipline*, not a concrete tool list (no tool schema file was fetched
alongside these templates). From `system_prompt.hbs`'s `## Tool Use`
section (conditionally rendered only `{{#if (gt (len available_tools) 0)}}`,
confirming the available tool set is injected dynamically rather than
fixed in the prompt):

- **Parallel-by-default tool calling**, same framing as several other
  sources in this collection: "You can call multiple tools in a single
  response. If you intend to call multiple tools and there are no
  dependencies between them, make all independent tool calls in
  parallel... if some tool calls depend on previous calls... do NOT
  call these tools in parallel."
- **A `timeout_ms` discipline for long-running commands**: "specify
  `timeout_ms` to bound runtime. If a command times out, report that
  clearly and let the user decide whether to rerun it."
- **An explicit anti-re-verification rule**: "Do not waste tokens by
  re-reading files after calling `write_file`, `edit_file`, or similar.
  The tool call will fail if it didn't work." — trusts the tool's own
  success/failure signal rather than a defensive re-read.
- **A no-tool-calls fallback mode**, used by three of the six captured
  templates (`create_file_prompt.hbs`, `edit_file_prompt_diff_fenced.hbs`,
  `edit_file_prompt_xml.hbs`) — when tool calls are disabled, editing
  and file-creation both fall back to structured-text-in-the-response
  conventions instead (SEARCH/REPLACE diff blocks, XML tags, or raw
  fenced file content), each with its own dedicated prompt template
  rather than one shared fallback format. `edit_file_prompt_xml.hbs`
  uses `<old_text line=N>`/`<new_text>` pairs, structurally the same
  shape as `edit_file_prompt_diff_fenced.hbs`'s SEARCH/REPLACE blocks
  but XML-tagged rather than diff-marker-delimited — two independent
  prompt templates for the same underlying editing convention, gated
  on the same trigger (tool calls disabled).
- **`Agent Skills`** — a `skill` tool plus an `<available_skills>`
  list injected with `name`/`description`/`location` per entry,
  structurally close to Claude Code's own Skills system: "When a
  user's request matches a Skill's description, use the `skill` tool
  to retrieve the full instructions... If the Skill references
  additional files, use `read_file` to access them. Paths inside a
  Skill resolve relative to that Skill's directory." A code comment in
  the template itself explains a deliberate escaping asymmetry: `name`/
  `description` are HTML-escaped "as defense in depth," but `location`
  is deliberately *not* escaped "because it's a filesystem path the
  model passes back to `read_file` verbatim — escaping characters like
  `&` or `<` would corrupt the path."
- **Sandbox/isolation — see Permissions below for full detail**: a
  real, platform-specific terminal sandbox is documented in
  `system_prompt.hbs` (conditionally rendered via `{{#if sandboxing}}`),
  not absent as an earlier read of this file suggested.

## Sub-agents

See [`agent-subagent-architectures.md`](../agent-subagent-architectures.md)
for the cross-source comparison this feeds into. A "Multi-agent
delegation" section (conditionally rendered only when a `spawn_agent`
tool is available) is prompted purely as *when to delegate* guidance —
no schema, no named agent types, and no calling-convention detail are
captured here (that presumably lives in the `spawn_agent` tool's own
schema, not fetched into this collection).

- **Use-case list, not a mechanism description**: "Very large tasks
  with multiple well-defined scopes... Plans with independent steps
  that can be executed in parallel... Independent information-
  gathering tasks... Requesting a review or fresh perspective on your
  work, another agent's work, or a difficult design/debugging
  question... Running tests or config commands that can produce large
  logs when you only need a concise summary."
- **Confirmed stateless one-shot, final-report-only**, the same
  pattern this collection's typology calls "tool call → stateless,
  one-shot, single final report" (§2 of the sub-agent doc): "Because
  you only receive the sub-agent's final message, ask it to include
  relevant failing lines or diagnostics" — an explicit acknowledgment
  that intermediate sub-agent output is invisible to the orchestrator,
  so the delegating agent must front-load what it wants echoed back.
- **An explicit write-conflict-avoidance instruction for parallel
  sub-agents**: "If multiple agents may edit files, assign disjoint
  write scopes" — a prompted-only concurrency rule (§5 of the
  sub-agent doc's "Concurrency and write-safety" axis), not a
  code-level lock; the model is trusted to partition the work itself.
- **An explicit anti-overuse guardrail**: "Use this feature wisely.
  For simple or straightforward tasks, prefer doing the work
  directly" — delegation framed as a deliberate cost/complexity
  tradeoff, not a default.
- **No turn-limit, recursion, or tool-scope-restriction language**
  found — a capture gap (the schema isn't here), not a confirmed
  absence.

## Compaction

See [`agent-context-compaction.md`](../agent-context-compaction.md) for
the cross-source comparison this feeds into. No compaction trigger,
summarization prompt/template, or numeric token threshold was found in
any of the six templates — `system_prompt.hbs`'s only token-adjacent
content is per-command `timeout_ms` (a runtime bound, not a context
budget). This folder captures only the agent's prompt templates, not
session/thread-management code, so this reads as a capture gap rather
than a confirmed absence, consistent with this doc's treatment of
several other sources whose orchestration layer wasn't fetched.

## Permissions and approval

See [`agent-permissions-approval.md`](../agent-permissions-approval.md)
for the cross-source comparison this feeds into. The richest section
of this whole capture — a fully-specified, platform-branching terminal
sandbox with a real persistence model, conditionally rendered via
`{{#if sandboxing}}`.

- **Approval mode**: not a named discrete mode — a single sandboxed-
  by-default posture with per-command elevation requests.
- **Read/write/network split, platform-specific**: reads are
  unrestricted ("any path on the filesystem is readable, including Git
  metadata"); writes default to a scratch directory plus the current
  project's worktrees (Linux: `/tmp`, cleared between calls, plus
  project dirs; Windows: routed through WSL under Bubblewrap, `/tmp`
  inside WSL; other platforms: a per-thread temp dir via
  `$TMPDIR`/`$TMP`/`$TEMP`) — **`.git` directories remain protected in
  every branch**, a hardcoded exception that survives all three
  platform variants; network access is blocked outbound by default on
  all platforms.
- **Granular, per-command elevation requests, not a blanket
  toggle** — `allow_hosts`/`allow_all_hosts` for network (Windows can
  only grant all-or-nothing; other platforms support exact-hostname or
  `*.`-subdomain scoping via an HTTP/HTTPS proxy, with an explicit
  caveat that non-HTTP tools like SSH/FTP silently bypass host
  scoping: "use `https://` URLs instead of `git@`/`ssh://`"),
  `fs_write_paths`/`allow_fs_write_all` for the filesystem, and a full
  `unsandboxed: true` escape hatch for when nothing else suffices.
- **Git metadata is the one thing no elevation request can grant
  short of the full escape hatch**: "Git metadata paths cannot be
  requested and will never be made writable while sandboxed... Git
  metadata writes are never grantable inside the sandbox. If a command
  needs to update `.git`, linked worktree metadata, refs, the index,
  hooks, local Git config, or other Git metadata, request
  `unsandboxed: true` with a reason." A read-only workaround is
  suggested for the common case: `git --no-optional-locks status`
  instead of plain `git status`, to avoid triggering an optional
  metadata write.
- **Three explicit persistence tiers, named directly in the prompt
  text**: "The user will be prompted to approve before the command
  runs, and can grant a sandbox request for that command, for the rest
  of the thread, or always. Once a host or write path is granted for
  the thread or always, later commands in this thread reaching that
  host or writing under that path won't prompt again." — per-call,
  per-thread, and permanent, the same three-tier shape this
  collection's permissions doc documents for several other sources
  (e.g. Codex CLI's `Approved`/`ApprovedForSession`/
  `ApprovedExecpolicyAmendment`), though Zed's is stated in plain
  prose rather than a typed enum.
- **A mid-thread stability guarantee**: "These sandbox settings are
  guaranteed to remain in effect for the entire duration of this
  thread. If they ever change, you will be told" — an explicit promise
  that the sandbox posture won't silently shift under the model
  mid-task.
- **Custom-instructions injection, with an explicit precedence
  order**: a personal `AGENTS.md` ("apply to every project this user
  opens") and project-scoped rules files are both injected, with
  project rules explicitly stated to "take precedence... when they
  conflict" — the same personal-vs-project layering this collection
  documents elsewhere (e.g. Claude Code's CLAUDE.md hierarchy), here
  made explicit in the prompt text itself rather than left to file-
  loading order.

## Git and version control

See [`agent-git-vcs.md`](../agent-git-vcs.md) for the cross-source
comparison this feeds into.

- **"Don't commit unless asked," the same near-universal convention
  documented across this collection**: "Do not commit changes or
  create new git branches unless the user explicitly requests it." No
  commit-message format, no branch-naming convention, and no PR/push
  workflow are captured anywhere in these six files.
- **A related, more general safety rule**: "Keep user work safe. Do
  not overwrite, remove, or revert changes you did not make unless the
  user explicitly asks" — not git-specific, but covers the same
  "don't touch changes you didn't make" territory as other sources'
  git-specific versions of the rule (e.g. Copilot Chat's "dirty git
  worktree" section, Devin's `git add .` caution).
- **The sandbox's git-metadata protection (see Permissions above) is
  itself a git-vcs-relevant finding worth cross-referencing**: `.git`
  is hardcoded-protected across every sandbox variant, and any real
  git write operation (commit, checkout, merge, etc., all of which
  touch `.git` metadata) requires the full `unsandboxed: true` escape
  hatch — meaning ordinary git usage is structurally treated as a
  higher-trust operation than regular file edits, not simply gated by
  the same prompted "ask first" convention. No checkpoint/undo system
  or worktree-isolation feature (in the `agent-git-vcs.md` sense of
  isolated parallel checkouts) was found — the prompt's own "worktrees"
  terminology refers to the project's already-open root directories
  (`{{#each worktrees}}`), not a git-worktree creation mechanism.

## Self-verification and testing

See [`agent-self-verification.md`](../agent-self-verification.md) for
the cross-source comparison this feeds into. `diff_judge.hbs` is a
clean, minimal instance of this doc's §3 (separate-LLM-call judge/
reviewer patterns) — a dedicated prompt, not a general chat turn,
whose entire job is scoring a diff against a checklist:

&gt; "You are an expert coder, and have been tasked with looking at the
&gt; following diff: `<diff>{{diff}}</diff>` Evaluate the following
&gt; assertions: `<assertions>{{assertions}}</assertions>` You must
&gt; respond with a short analysis and a score between 0 and 100, where:
&gt; 0 means no assertions pass; 100 means all the assertions pass
&gt; perfectly."

The required output structure — a per-assertion `<analysis>` line
("one line describing why the first assertion passes or fails (even
partially)") followed by a single `<score>` — makes the judge's
reasoning auditable per-criterion rather than a single opaque verdict,
closer in spirit to a rubric-scored rather than binary pass/fail
judge. What isn't captured here: what calls this prompt, how
`{{assertions}}` gets populated, or what happens on a low score
(retry, block, just report) — this template describes the judge call
itself, not the surrounding retry/gating logic, so it can't yet be
placed on this doc's "what happens on a failed verdict" comparison
without further research.

`system_prompt.hbs`'s own "Task Execution" section has ordinary §7-style
prompted-only completion language: "Keep going until the user's task
is completely resolved before ending your turn... Only terminate your
turn when you are sure the problem is solved."

## Turn output

See [`agent-turn-output.md`](../agent-turn-output.md) for the
cross-source comparison this feeds into. No title-generation or
reasoning-display content found in any of the six templates (this
folder doesn't capture session-management/UI code where either would
plausibly live — a capture gap, not a confirmed absence). One
narration-adjacent rule: "Before a group of related tool calls, send a
brief one- to two-sentence preamble explaining what you're about to
do, so the user can follow along. Skip the preamble for trivial single
reads or when continuing a clearly described step" — ordinary prompted
narration (this doc's §3), with an explicit skip-condition for trivial
actions not every other source's version of this rule states.
