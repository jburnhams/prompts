# OpenClaw — tool descriptions, verbatim

Model-facing `description` text for the tools that matter to a coding
agent, from commit `5f714ef` (`main`, 2026-08-31). **License: MIT.**

Three properties of this surface are worth stating before the text:

1. **Every tool carries three strings, not one.** `description` is what the
   model sees, `label` and `displaySummary` are what the human UI shows,
   and `promptSnippet` / `promptGuidelines` are what the *system prompt*
   shows when the tool appears in the `## Tooling` catalogue. The one-line
   summaries in the prompt's tool list are a separate, shorter register
   from the schema descriptions here.
2. **Descriptions are functions of runtime.** `describeExecTool`,
   `describeSessionsSpawnTool`, `describeAgentsWaitTool`,
   `describeAgentsListTool` and the memory contracts are all builders that
   take availability flags and produce different text. `AGENTS.md` makes
   this a rule: *"Tool/prompt descriptions never statically name tools from
   other toolsets/plugins; gating turns the reference into hallucination
   bait. Needed cross-references are injected at definition-build time from
   what is actually available."*
3. **Caps are in the description.** Read/grep/find/bash all state their own
   truncation ceilings in the text the model reads.

---

## File tools (`src/agents/sessions/tools/`)

### `read`

```text
Read text/image file (jpg/png/gif/webp/bmp); images attach to model context. Text caps 2000 lines or 50KB. Continue with offset/limit, or cursor within a long line.
```

```text
promptSnippet:     Read file contents
promptGuidelines:  Use read to examine files and its offset, limit, or cursor to continue.
```

Parameters: `path`, `offset` (≥1), `limit`, `cursor` (≥0), `optional`.
`cursor` is a **byte position inside a single long line** — a third
continuation axis alongside `offset`/`limit`, so a minified file is
resumable rather than merely truncated. Renderer messages on truncation:

```text
[First line exceeds ${size} limit]
[Truncated: showing ${n} of ${total} lines (2000 line limit)]
[Truncated: ${n} lines shown (50KB limit)]
```

### `edit`

```text
Exact single-file replacements. oldText unique/non-overlapping against original. Merge nearby changes; omit large unchanged spans.
```

```text
promptSnippet:     Exact file edits; multiple disjoint edits per call
promptGuidelines:
  - oldText must match exactly
  - Multiple disjoint locations: one call, multiple edits[]
  - Match original file; no overlap/nesting; merge nearby
  - oldText minimal but unique; no padding
```

Parameter descriptions:

```text
path:          File path; relative/absolute.
edits:         Targeted replacements against original file; no overlap/nesting. Merge nearby changes.
edits[].oldText: Exact original text; unique and non-overlapping in this call.
edits[].newText: Replacement text.
```

### `write`

```text
Write/overwrite file; creates parent directories.
```

```text
promptSnippet:     Create/overwrite files
promptGuidelines:  Use only new files/complete rewrites.
```

### `grep`

```text
Search contents; returns path:line matches. Respects .gitignore. Caps 100 matches/50KB; lines cap 500 chars.
```

```text
promptSnippet:  Search file contents for patterns (respects .gitignore)
```

```text
pattern:     Regex/literal pattern.
path:        File/dir; default cwd.
glob:        File glob, e.g. *.ts.
ignoreCase:  Ignore case; default false.
literal:     Literal, not regex; default false.
context:     Context lines each side; default 0.
limit:       Max matches; default 100.
```

### `find`

```text
Find by glob; paths relative to search dir. Respects .gitignore. Caps 1000 results/50KB.
```

### `bash`

```text
Run bash in cwd; stdout+stderr. Returns last 2000 lines or 50KB; full truncated output saved temp. Optional timeout seconds.
```

```text
promptSnippet:  Execute bash commands (ls, grep, find, etc.)
```

Shared ceilings (`packages/agent-core/src/harness/utils/truncate.ts`):
`DEFAULT_MAX_LINES = 2000`, `DEFAULT_MAX_BYTES = 50 KiB`,
`GREP_MAX_LINE_LENGTH = 500`.

---

## `exec` (`describeExecTool`)

Composed at build time from three flags. With a process tool and an
automations tool present, on POSIX:

```text
Run shell now; background continuation supported. Use yieldMs/background, then process for logs/status/input/intervention. Long run: automatic completion wake when enabled and output/failure occurs; otherwise process confirms completion. No sleep loops for reminders/follow-ups; use automations. TTY CLI/UI/coding agent: pty=true. Quote arguments containing shell metacharacters, including URL query strings with `?` or `&`.
```

Without a process tool the first sentence collapses to `Run shell and wait
for completion.`

On Windows the trailing quoting sentence is replaced by a platform block —
and, uniquely in this codebase, by a **rendering of the host's own approval
allowlist into the tool description**:

```text
IMPORTANT (Windows): Run executables directly; do NOT wrap commands in `cmd /c`, `powershell -Command`, `& ` prefix, or WSL. Use backslash paths (C:\path), not forward slashes. Use short executable names (e.g. `node`, `python3`) instead of full paths.
Pre-approved executables (exact arguments are enforced at runtime; no approval prompt needed when args match):
  ${shortName} (any arguments)
  ${shortName} (restricted args)
```

Ten entries maximum, and only allowlist patterns containing a path
separator or `~`. Loading is best-effort inside a `try/catch` so a broken
approvals file cannot block tool construction.

---

## Delegation and orchestration

### `sessions_spawn` (`describeSessionsSpawnTool`)

`displaySummary`: `Spawn hidden subagent (ephemeral) or visible work session (durable).`
(or `Spawn subagent session.` when ACP is unavailable).

Full description, ACP + threads + swarm all available:

```text
Spawn child session; default `runtime="subagent"`; ACP needs explicit `runtime="acp"`. `mode="run"` one-shot; `mode="session"` persistent/thread-bound only on supporting requester channel. `agentId` targets a configured agent; `model` overrides its model; `cleanup` delete|keep hidden child session; `sandbox` inherit|require. `visible=true`: durable visible session. Default for coding, multi-step work, or results user may revisit/steer/keep — not only when a thread is requested. Shows in web UI sidebar; works without UI: completion announces back, progress checkable. `group` places it in a custom sidebar group (a new name creates the group); omission or an empty string leaves it ungrouped. Subagent only; omit `mode` (`mode="run"` is also accepted), `thread`, `thinking`, and `lightContext`; `attachments=[]` and omitted/blank `attachAs.mountPath` are accepted, but nonempty attachment staging is unsupported; inherits the caller tool-policy ceiling; may check out a git worktree via `worktree`/`worktreeName`/`worktreeBaseRef`. When its accepted result includes `sessionUrl`, channel acknowledgements put the session URL on the first line and `Owner: <label>` on the second line. Session listing/addressing obeys `tools.sessions.visibility` (${scope}: ${meaning}). `collect=true` (swarm): parallel fan-out collector children; structured result per `outputSchema`; `groupId` groups a batch. Inherits parent workspace. Native task arrives in the child's initial `[Subagent Task]` message. `runtime="acp"` ids: codex, claude, gemini, opencode, or configured ACP. Native: explicit context="isolated" starts clean; context="fork" copies requester transcript and requires the same agent. Omitted context follows configured threadBindings.defaultSpawnContext policy (fork by default) with thread=true; without a thread it is isolated. Hidden child: research, parallel/batch reads, throwaway side tasks. Coding, PRs, long builds, anything worth keeping: `visible=true`. No spawn for quick lookup/single read. After spawn, do non-overlap work. Run result returns; session output stays thread unless ACP `streamTo="parent"`.
```

Selected parameter descriptions:

```text
taskName:           Stable later-target alias; starts lowercase letter; then lowercase/digit/_/-.
label:              Short task title shown in UI lists; name the work, not the agent.
runtime:            Runtime; visible=true requires "subagent".
runTimeoutSeconds:  Per-run timeout in seconds; overrides the configured subagent default. Zero disables the timeout.
thinking:           Thinking override; unavailable with visible=true.
cwd:                Child working directory. Visible paths outside configured agent workspaces require operator.admin. Omitted with worktree=true: inherit the same-agent parent managed repository; otherwise use the target agent workspace.
thread:             Bind new chat thread when supported; true defaults mode="session"; unavailable with visible=true.
mode:               "run" one-shot; "session" persistent/thread-bound. Visible sessions accept only omitted/default "run" and remain persistent.
cleanup:            Hidden session cleanup; visible=true always keeps the session.
sandbox:            "inherit" parent sandbox policy; "require" fails unless child is sandboxed.
lightContext:       Light bootstrap; subagent only; unavailable with visible=true.
collect:            Swarm collector child for parallel fan-out.
outputSchema:       JSON Schema for the child's structured result; requires collect=true.
groupId:            Groups parallel collector children; requires collect=true.
attachments:        Inline snapshots; visible=true accepts only an empty array.
resumeSessionId:    ACP resume id already recorded for requester; ignored by subagent.
```

Rejection messages are themselves instructions:

```text
sessions_spawn from a collector requires collect=true so approvals stay non-interactive.
sessions_spawn parameter "${key}" requires tools.swarm.enabled=true.
sessions_spawn "outputSchema" requires collect=true.
sessions_spawn collect=true does not support thread, visible, or session mode.
sessions_spawn does not support "${key}"; remove channel-delivery parameters.
sessions_spawn does not support "${key}". Use "runTimeoutSeconds" for a per-run timeout.
```

### `agents_wait` (`describeAgentsWaitTool`)

```text
Wait for collector subagents started by sessions_spawn collect=true. Accepts many run ids; returns once any completes (completed results incl. structured output, plus pending ids), or on timeoutSeconds.
```

### `agents_list` (`describeAgentsListTool`)

```text
List configured agent ids with name/model/runtime metadata, allowed as `sessions_spawn(runtime:"subagent")` targets.
```

### `session_status` (`describeSessionStatusTool`)

```text
Show visible-session model/usage/time/cost/tasks. `sessionKey="current"` for current; UI labels are not keys. `model` overrides; `model=default` resets. Use for active model/session questions.
```

---

## `ask_user` (`describeAskUserTool`)

```text
Ask the human user 1-3 structured questions and wait for their answer; `multiSelect` allows picking several options and `timeoutSeconds` bounds the wait. Use only when blocked on a decision genuinely theirs that cannot be resolved from the request, code, or sensible defaults; never ask whether to proceed or confirm a plan. Ask exactly one question per call unless several answers must be submitted together; one single-select question uses native controls on supported messaging channels. Put every selectable choice in `options`, never only in the question text. Put the recommended option first and suffix its label with ` (Recommended)`. Use `multiSelect` only when the user may choose several options at once; otherwise omit it. Do not include an Other option; free text is added automatically. If the result is no_answer, continue with best judgment.
```

```text
key:            Unique snake_case answer key.
header:         Short chip label; longer input is truncated to 12 characters.
question:       Single-sentence question only. Put all selectable choices in options.
options:        Every selectable choice. Put the recommended choice first; do not repeat choices only in the question text.  (2–4 items)
multiSelect:    True only when the user may choose several options at once.
timeoutSeconds: Maximum human wait in seconds; default 900, clamped 30-3600. Earlier run cancellation or overall run timeout still applies.
```

---

## `progress_card`

The longest single tool description in the codebase, and the only one that
argues for its own use rather than describing a capability:

```text
Maintain this session's progress card: the single durable status surface shown next to the session in OpenClaw's UIs, for someone who is not reading the transcript. Keep it current on any task that takes more than a moment — it is how the user watches you work without scrolling. Each call replaces the whole card. Pick the representation that fits the work, using either or both parts: `markdown` — a compact note; tables for comparisons or metrics, <progress value="3" max="7"></progress> bars for one long operation, a bold one-liner for simple state; other raw HTML is stripped. Known URL? Link it. Don't leave PRs or issues as bare IDs. And `plan` — an ordered step checklist (pending | in_progress | completed, at most one in_progress) for genuinely sequential work. The checklist is optional: omit it whenever a table, bar, or sentence says it better, and never repeat the same facts in both parts. Call with both parts empty to clear. Update on meaningful change — a step done, a blocker, results in — not every message. Max 8 KB markdown, 50 steps.
```

A second, one-line reminder is appended to `extraSystemPrompt` — but only
for non-main sessions, only when a paired card renderer exists, and only
when the session's utility model differs from its primary model:

```text
During multi-step work, keep your progress card current with the progress_card tool; the user follows it instead of reading the transcript.
```

---

## `secrets` (`describeSecretsTool`)

```text
Protected credentials: `list` metadata first; `request` missing task-needed name + reason via human masked entry; `delete` removes an entry. Request waits for human; value goes straight to shared store, never model/chat. Use the returned store SecretRef for supported config fields. Gateway egress only: enabled proxy + exact allowedHosts required; no hosts blocks egress, not config refs. No plaintext fallback. Gateway-host commands: use auto-injected opaque env sentinel under stored name. No secret templates; never override/print that variable. Native shell/sandbox/node: no protected injection. First command snapshots store for run; late saves need next turn. Operator-set env entries are readable; never request them here. no_answer: report blocker or use best judgment, never ask for credentials in chat.
```

---

## Memory tools (`extensions/memory-core/src/memory-tool-contract.ts`)

Both descriptions are builders over the configured corpus set.

### `memory_search`

```text
Mandatory recall step: semantically search ${search} before answering questions about prior work, decisions, dates, people, preferences, or todos. Optional `corpus=wiki` or `corpus=all` also searches registered compiled-wiki supplements. `corpus=memory` restricts hits to indexed memory files (excludes session transcript chunks from ranking). `corpus=sessions` restricts hits to the session corpus under the same visibility rules as session history tools. Corpus outcomes cover each requested corpus; a corpus warning means results are partial and must be surfaced to the user. If response has disabled=true or stale=true, tell the user and include the warning/action guidance.
```

### `memory_get`

```text
Safe exact excerpt read from ${files}. Defaults to a bounded excerpt when lines are omitted and includes truncation/continuation info when more content exists. `corpus=wiki` reads registered compiled-wiki supplements. status=ok means the requested excerpt was read; status=not_found means every requested available corpus missed. Corpus outcomes cover each requested corpus; a corpus warning means results are partial and must be surfaced to the user.
```

---

## `view_image`

A three-way builder on the runtime's vision situation
([`src/agents/tools/image-tool.ts`](https://github.com/openclaw/openclaw/blob/v2026.8.1/src/agents/tools/image-tool.ts)).
The tool returns `null` — refusing to register — when the session model has
no vision and no image model is configured or resolvable.

Session model has vision:

```text
Load image(s) into private model context for inspection: path accepts one local image path or permitted URL; paths accepts up to maxImages entries (20 by default). Does not display, attach, or send files to the user. Prompt images are already visible.
```

Explicit image model configured:

```text
Inspect image(s) in private model context with the configured model: path accepts one local image path or permitted URL; paths accepts up to maxImages entries (20 by default). Does not display, attach, or send files to the user.
```

Auto-resolved image model:

```text
Inspect image(s) in private model context with available vision: path accepts one local image path or permitted URL; paths accepts up to maxImages entries (20 by default). Does not display, attach, or send files to the user.
```

With a sighted session model the tool is additionally marked
`catalogMode: "direct-only"`, which keeps it a real model tool under Code
Mode instead of moving it behind the JSON-only guest bridge that cannot
carry an image result.

**A dead key.** The prompt renderer's `coreToolSummaries` has an entry
`image: "Analyze images"`, but `toolOrder` and the tool itself use
`view_image`. The lookup is by tool name, so `view_image` renders in the
`## Tooling` catalogue as a bare `- view_image` with no summary, and the
`image` entry is unreachable.

---

## Display summaries (`src/agents/tool-description-presets.ts`)

Not model-facing; these are the human-UI strings, listed here because the
split between them and `description` is the point.

```text
Spawn hidden subagent (ephemeral) or visible work session (durable).
Spawn subagent session.
Wait for collector subagents.
Show session status/model/usage.
Ask the user and wait for an answer.
Suggest follow-up work for operator approval.
Withdraw a pending task suggestion.
Manage reusable-skill proposals; inspect can select one stored artifact and returns complete content only when it fits the model budget.
```
