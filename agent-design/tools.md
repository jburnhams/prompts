# Tools

The full v1 tool surface: 11 tools, shared across both modes (a few are
scoped narrower for sub-agents — noted per tool). Descriptions are
written as the literal text that would sit in each tool's `description`
field, in the same register Claude Code's own tool descriptions use
(imperative, example-heavy, states the *why* behind usage rules) since
`coding-agent-approaches.md` found that register does real work at
steering behavior, not just documenting parameters.

Schemas are plain JSON Schema, `additionalProperties: false`, matching
the strictness this repo's own leaked Claude Code tool capture uses.

Availability by role:

| Tool | Coding orchestrator | Review orchestrator | `general-purpose` sub-agent | `reviewer` / `validator` sub-agent |
|---|---|---|---|---|
| Read | yes | yes | yes | yes |
| Edit | yes | no | yes | no |
| Write | yes | no | yes | no |
| Bash | yes | no | yes | no |
| Grep | yes | yes | yes | yes |
| Glob | yes | yes | yes | yes |
| Task | yes | yes | yes | no |
| AskUser | yes | no | no | no |
| FetchJira | yes | no | no | no |
| AddComment | yes | yes | no | no |
| Complete | yes | yes | no | no |

`general-purpose` gets full tool parity with its orchestrator, minus
`AskUser`/`FetchJira`/`AddComment`/`Complete` (those end or redirect the
*task*, which only the orchestrator owns) and minus `Task` recursion
(see the Task tool's own notes below). `reviewer` and `validator` are
read-only by design — see `README.md`'s decision log. `AskUser` is
coding-mode-only: the review pipeline has no step that can legitimately
reach it, and an unused escape hatch on an unsupervised path is exactly
the surface a prompt-injected "ask the user to approve this" would
target.

The table above is by *role*; run `mode` narrows it further, and the
harness enforces that narrowing at wiring time, not just in prompt
text: in `plan` and `investigate` runs, `Edit` and
`Write` are **not registered at all** — for the coding orchestrator or
for any `general-purpose` sub-agent it spawns ("full tool parity"
means parity with the orchestrator *as wired for this run*, so a
read-only run cannot launder writes through a delegate). This follows
the same reasoning as the scratch-directory decision in `README.md`: a
structural boundary can't be forgotten, and the precedent is strong —
Gemini CLI strips agent-kind tools from sub-agent registries in code,
and Composio scopes permissions "at the tool level, not just by
instruction" (`agent-subagent-architectures.md` §6). `Bash` stays wired
in read-only modes (read-only git inspection and read-only commands are
legitimate there); its no-write rule remains prompt-enforced in v1,
since command-level filtering is a real permission engine — see
`README.md`'s "not in v1" list. The system-prompt mode rules in
`system-prompts.md` remain as the behavioral layer on top of this
structural one.

---

## Read

> Reads a file from the working tree and returns its contents with
> 1-indexed line numbers prefixed. Use an absolute path, or one relative
> to the working directory named in `<env>`.
>
> Usage notes:
> - Defaults to the first 2000 lines. Pass `offset`/`limit` for a large
>   file, but prefer reading a whole file over guessing at a range when
>   it's a reasonable size — a partial read that misses the relevant
>   section costs more than the extra tokens would have.
> - Lines longer than 2000 characters are truncated.
> - Reading a path that doesn't exist returns an error rather than empty
>   content — check with Glob first if you're not sure a path is right.
> - Reading a file that exists but is empty returns an explicit marker,
>   not blank content, so it isn't mistaken for a failed read.

```json
{
  "name": "Read",
  "input_schema": {
    "type": "object",
    "properties": {
      "path": { "type": "string", "description": "Absolute or working-directory-relative path to the file." },
      "offset": { "type": "integer", "description": "1-indexed line number to start from. Omit to read from the start." },
      "limit": { "type": "integer", "description": "Maximum number of lines to return. Omit to use the default cap." }
    },
    "required": ["path"],
    "additionalProperties": false
  }
}
```

---

## Edit

> Makes a targeted change to an existing file by replacing one exact,
> contiguous span of text with another.
>
> `old_string` must match the file's actual current content byte for
> byte — same whitespace, same line endings — and must be **unique**
> within the file. If it matches more than once, the call fails rather
> than guessing which occurrence you meant; include enough surrounding
> context (a few lines before/after the change, not just the changed
> line) to make it unambiguous. Read the file (or the relevant section
> of it) before editing it, so `old_string` is guaranteed to match what's
> actually there rather than what you assume is there.
>
> Set `replace_all: true` to replace every occurrence instead of
> requiring uniqueness — use this for a deliberate rename across a file,
> never as a workaround for an `old_string` you couldn't make unique.
>
> To insert new content, include a line of existing surrounding context
> in `old_string` and repeat it (extended) in `new_string`. To delete,
> set `new_string` to the content that should remain, omitting the
> deleted span. This tool cannot create a new file — use Write for that.

```json
{
  "name": "Edit",
  "input_schema": {
    "type": "object",
    "properties": {
      "path": { "type": "string", "description": "Absolute or working-directory-relative path to an existing file." },
      "old_string": { "type": "string", "description": "The exact text to replace. Must uniquely match within the file unless replace_all is set." },
      "new_string": { "type": "string", "description": "The text to replace it with. Must differ from old_string." },
      "replace_all": { "type": "boolean", "description": "Replace every occurrence of old_string instead of requiring a unique match. Default false." }
    },
    "required": ["path", "old_string", "new_string"],
    "additionalProperties": false
  }
}
```

---

## Write

> Creates a new file, or fully overwrites an existing one.
>
> Prefer Edit for any change to a file that already has content worth
> preserving — Write replaces the entire file, so using it on an
> existing file discards everything not repeated in `content`. Use Write
> for genuinely new files, or when a rewrite is so extensive that
> reconstructing it via Edit calls would be less reliable than writing
> it fresh.
>
> Only write into the repository working tree for files meant to be
> part of the actual change. Anything throwaway — a reproduction
> script, a scratch note, exploratory output — goes in the scratch
> directory named in `<env>` instead, never in the repository, even
> temporarily (see the coding system prompt's workflow, step 2).

```json
{
  "name": "Write",
  "input_schema": {
    "type": "object",
    "properties": {
      "path": { "type": "string", "description": "Absolute or working-directory-relative path." },
      "content": { "type": "string", "description": "The full file contents to write." }
    },
    "required": ["path", "content"],
    "additionalProperties": false
  }
}
```

---

## Bash

> Executes a command in a persistent shell session (state — cwd,
> environment variables, background jobs — carries over between calls
> within one task).
>
> Usage notes:
> - Use this for git, running tests/linters, package-manager commands,
>   and anything else with no dedicated tool. Do not use it for search
>   or plain file reads — use Grep/Glob/Read instead; they're faster and
>   don't spend context on output you don't need.
> - Quote paths containing spaces.
> - Default timeout is 120000ms; pass `timeout_ms` up to 600000 for a
>   command that legitimately needs longer.
> - Set `run_in_background: true` for a long-running process (a dev
>   server, a watch task) you need to keep running while you do other
>   work; poll it with the same tool call shape and its process id.
> - Output over 30000 characters is truncated. If you need to inspect
>   something larger, redirect it to a file in the scratch directory
>   (named in `<env>`) and Read the relevant slice — never redirect into
>   the repository working tree.
> - Before a command that creates a new directory or file, confirm the
>   parent exists (Glob or a quick `ls`) rather than assuming.
>
> Git in v1: read-only inspection only (`status`, `diff`, `log`,
> `blame`, `show`) to understand what's already changed and orient
> yourself in the repository's history. Never run a git command that
> writes repository or branch state — `commit`, `add`, `push`,
> `branch`, `checkout`, `reset`, `merge`, `rebase`, or anything
> equivalent. The task's target branch is already checked out before
> your run starts; leaving a finished, uncommitted working tree is the
> entire delivery mechanism (see the coding system prompt's workflow) —
> whatever invoked you owns turning it into a commit.

```json
{
  "name": "Bash",
  "input_schema": {
    "type": "object",
    "properties": {
      "command": { "type": "string", "description": "The shell command to execute." },
      "description": { "type": "string", "description": "A 5-10 word description of what this command does." },
      "timeout_ms": { "type": "integer", "description": "Maximum time to allow, up to 600000. Defaults to 120000." },
      "run_in_background": { "type": "boolean", "description": "Run without blocking; poll for output separately. Default false." }
    },
    "required": ["command"],
    "additionalProperties": false
  }
}
```

---

## Grep

> Searches file contents using ripgrep's regex syntax. Prefer this over
> Bash for any content search — it's faster and its output is
> pre-shaped for you.
>
> - `output_mode: "files_with_matches"` (default) returns matching file
>   paths only; `"content"` returns matching lines (supports `-A`/`-B`/
>   `-C` context and `-n` line numbers); `"count"` returns per-file match
>   counts.
> - Filter with `glob` (e.g. `"*.ts"`) or `type` (e.g. `"python"`).
> - Patterns are ripgrep regex, not shell-glob — escape literal braces
>   (`interface\{\}`) etc.
> - `multiline: true` lets `.` match newlines, for a pattern that spans
>   lines.

```json
{
  "name": "Grep",
  "input_schema": {
    "type": "object",
    "properties": {
      "pattern": { "type": "string", "description": "Regex pattern to search for." },
      "path": { "type": "string", "description": "File or directory to search. Defaults to the working directory." },
      "glob": { "type": "string", "description": "Glob to filter which files are searched, e.g. \"*.ts\"." },
      "type": { "type": "string", "description": "File type filter, e.g. \"python\", \"go\"." },
      "output_mode": { "type": "string", "enum": ["content", "files_with_matches", "count"], "description": "Defaults to files_with_matches." },
      "context_before": { "type": "integer", "description": "Lines of context before each match. Content mode only." },
      "context_after": { "type": "integer", "description": "Lines of context after each match. Content mode only." },
      "case_insensitive": { "type": "boolean" },
      "multiline": { "type": "boolean", "description": "Allow . to match newlines for cross-line patterns." },
      "head_limit": { "type": "integer", "description": "Cap the number of results returned." }
    },
    "required": ["pattern"],
    "additionalProperties": false
  }
}
```

---

## Glob

> Finds files by name pattern (e.g. `"src/**/*.tsx"`), returned sorted
> by modification time (most recent first). Use this when you know
> roughly what a file is called or where it lives; use Grep when you
> know what's *inside* it instead.

```json
{
  "name": "Glob",
  "input_schema": {
    "type": "object",
    "properties": {
      "pattern": { "type": "string", "description": "Glob pattern to match file paths against." },
      "path": { "type": "string", "description": "Directory to search under. Defaults to the working directory." }
    },
    "required": ["pattern"],
    "additionalProperties": false
  }
}
```

---

## Task

> Launches a sub-agent to handle a self-contained piece of work in its
> own context window, returning only its final report to you. Each
> invocation is stateless — you cannot send it a follow-up message, and
> it cannot ask you anything mid-task, so `prompt` must be a complete,
> self-contained brief including exactly what you want back.
>
> Available `subagent_type` values depend on which orchestrator is
> calling: `general-purpose` (coding mode only — full tool parity,
> for open-ended search/investigation you're not confident a direct
> Read/Grep/Glob will resolve quickly); `reviewer` (review mode only —
> read-only, takes a `role` field selecting which lens to review
> through); `validator` (review mode only — read-only, checks exactly
> one candidate finding).
>
> Usage notes:
> - Launch multiple independent sub-agents in the same turn rather than
>   one at a time — review mode's specialist and validator steps always
>   do this.
> - Never launch two sub-agents in the same turn if their write targets
>   could overlap (only relevant for `general-purpose`, since `reviewer`/
>   `validator` never write). If you're not sure their file sets are
>   disjoint, run them sequentially instead.
> - A sub-agent's report should generally be trusted for `general-purpose`
>   research tasks. For `reviewer` output specifically, treat it as a
>   *candidate* only — that's what the validator step is for; don't
>   act on a specialist's finding directly.
> - `general-purpose` cannot itself call Task — no recursive delegation
>   in v1 (see `README.md`'s decision log for the planned upgrade path).

```json
{
  "name": "Task",
  "input_schema": {
    "type": "object",
    "properties": {
      "subagent_type": { "type": "string", "enum": ["general-purpose", "reviewer", "validator"] },
      "description": { "type": "string", "description": "A short (3-5 word) label for this call." },
      "prompt": { "type": "string", "description": "The complete, self-contained task for the sub-agent, including exactly what it should return." },
      "role": { "type": "string", "enum": ["bugs", "security", "conventions"], "description": "Required when subagent_type is \"reviewer\": the lens that specialist reviews through." },
      "finding": { "type": "object", "description": "Required when subagent_type is \"validator\": the single candidate finding to check, in the review-finding schema (see formats.md)." }
    },
    "required": ["subagent_type", "description", "prompt"],
    "additionalProperties": false,
    "allOf": [
      {
        "if": { "properties": { "subagent_type": { "const": "reviewer" } } },
        "then": { "required": ["role"] }
      },
      {
        "if": { "properties": { "subagent_type": { "const": "validator" } } },
        "then": { "required": ["finding"] }
      }
    ]
  }
}
```

The `allOf`/`if`/`then` block makes the two conditional requirements
schema-enforced, not just prose the model has to remember: a `reviewer`
call missing `role`, or a `validator` call missing `finding`, fails
validation before it ever reaches Forge — rather than being accepted and
only failing at runtime when the sub-agent doesn't get the parameter it
needs. (Both keywords are plain JSON Schema draft-07+, so this doesn't
change the schema dialect used elsewhere in this document.)

---

## AskUser

> Raises a blocking question back to a human and **ends the current
> run** — see `formats.md`'s AskUser protocol for the full suspend/resume
> mechanics. Use this only when the task genuinely cannot proceed
> correctly without a human decision: contradictory requirements, a
> destructive/irreversible choice with no clear right answer in the
> task, or a precondition the task assumed that turns out to be false in
> a way that changes what "done" means.
>
> Do not use this for anything you could reasonably decide yourself —
> routine implementation choices, style preferences, or ambiguity you
> can resolve by reading more code. Note any judgment call you made
> instead of asking in your final Complete report, so it's visible and
> reviewable even though it didn't block you.
>
> Calling this tool is the last action in a run — do not call any other
> tool afterward, and do not call Complete in the same turn. It posts
> your question through AddComment automatically; you do not need to
> call AddComment yourself first.

```json
{
  "name": "AskUser",
  "input_schema": {
    "type": "object",
    "properties": {
      "question": { "type": "string", "description": "The specific question that needs a human answer." },
      "context": { "type": "string", "description": "Why this is blocking, and what you've already tried or ruled out." },
      "options": {
        "type": "array",
        "items": { "type": "string" },
        "description": "Optional: 2-4 concrete choices, if the question reduces to one. Omit for an open-ended question."
      }
    },
    "required": ["question", "context"],
    "additionalProperties": false
  }
}
```

---

## FetchJira

> Fetches a Jira issue by key and returns its full content: title,
> description, status, issue type, priority, labels, acceptance
> criteria (if the project uses that field), comments in chronological
> order, and any linked issues. Coding-mode-only — review mode doesn't
> take a Jira issue as input, only a PR.
>
> Pass `fields` to limit the response to specific top-level fields (e.g.
> `["description", "comments"]`) when you only need part of the issue
> and want to keep the response small; omit it to get everything.

```json
{
  "name": "FetchJira",
  "input_schema": {
    "type": "object",
    "properties": {
      "issue_key": { "type": "string", "description": "The Jira issue key, e.g. \"PROJ-1234\"." },
      "fields": {
        "type": "array",
        "items": { "type": "string" },
        "description": "Optional subset of fields to return. Omit for the full issue."
      }
    },
    "required": ["issue_key"],
    "additionalProperties": false
  }
}
```

Output shape is documented in `formats.md`.

---

## AddComment

> Posts a comment — a new top-level comment, an inline comment anchored
> to a specific file/line on a PR, or a threaded reply to an existing
> comment — on either a Jira issue or a PR. One tool for both platforms,
> per the brief; platform differences are handled by which optional
> fields you set, not by separate tools. `body` is always plain
> Markdown regardless of target — converting it to whatever the target
> platform actually needs (e.g. Jira Cloud's ADF, or legacy wiki markup)
> is a harness-side concern, not something this schema or Forge itself
> handles; see `review.md`'s decision log.
>
> - `target.platform: "jira"` + `target.id` (an issue key): posts a
>   Jira comment. `in_reply_to` is honored as a best-effort @-mention
>   reference — Jira's own comment model isn't fully threaded, so a true
>   nested reply isn't always possible; the tool falls back to a
>   plain comment prefixed with a reference to the original if the
>   target platform can't thread it.
> - `target.platform: "github_pr"` + `target.id` (`"owner/repo#123"`):
>   posts a GitHub PR comment. Set `anchor` (file + line, optionally a
>   `line_end` for a range) for an inline review comment; omit it for a
>   general PR comment. Anchor line numbers are **new-file (post-change)
>   line numbers** — the same side the review-finding schema uses. Set
>   `in_reply_to` (a comment id) to reply within an existing review
>   thread rather than starting a new one.
> - An inline comment can only attach to lines that appear in the PR's
>   diff. The harness validates the anchor before posting; if it isn't
>   commentable, the comment is posted as a general PR comment prefixed
>   with `file:line` instead of being dropped, and the tool result says
>   which happened — so a mis-derived line number degrades visibly, not
>   silently.
> - `suggestion` wraps `body` in a GitHub-native committable suggestion
>   block, replacing the full anchored line range. Only set this when
>   applying it verbatim fully resolves the issue — never for a fix that
>   needs a follow-up step. Requires `anchor` (schema-enforced below).
>
> Returns the posted comment's id and URL, which a caller can use as a
> later `in_reply_to` value.

```json
{
  "name": "AddComment",
  "input_schema": {
    "type": "object",
    "properties": {
      "target": {
        "type": "object",
        "properties": {
          "platform": { "type": "string", "enum": ["jira", "github_pr"] },
          "id": { "type": "string", "description": "Jira issue key, or \"owner/repo#pr_number\" for a PR." }
        },
        "required": ["platform", "id"],
        "additionalProperties": false
      },
      "body": { "type": "string", "description": "Comment text, Markdown. The harness converts to the target platform's native format if needed (e.g. Jira ADF) — this schema always carries Markdown." },
      "in_reply_to": { "type": "string", "description": "Optional: id of an existing comment to reply to." },
      "anchor": {
        "type": "object",
        "description": "Optional, github_pr only: anchors the comment to a specific new-file line or line range.",
        "properties": {
          "file": { "type": "string" },
          "line": { "type": "integer", "description": "New-file (post-change) line number. The start of the range when line_end is set." },
          "line_end": { "type": "integer", "description": "Optional: new-file line number ending the range, inclusive. Omit for a single-line anchor." }
        },
        "required": ["file", "line"],
        "additionalProperties": false
      },
      "suggestion": { "type": "boolean", "description": "Wrap body as a committable suggestion block replacing the anchored line range. github_pr, anchored comments only." }
    },
    "required": ["target", "body"],
    "additionalProperties": false,
    "allOf": [
      {
        "if": { "properties": { "suggestion": { "const": true } } },
        "then": { "required": ["anchor"] }
      }
    ]
  }
}
```

The `allOf` block makes `suggestion` without an `anchor` a schema
error rather than a runtime surprise — same device the Task tool uses
for its conditional requirements.

---

## Complete

> Ends the task. This is the only way a run finishes successfully —
> stopping without calling it (running out of turns, trailing off) is a
> failure mode to avoid, not an alternate ending. Carries the structured
> report described in `formats.md`'s completion schema: status, a short
> human-readable summary (Forge does not post this anywhere itself —
> whether and how it reaches a PR, a Jira comment, a CI summary, or
> nowhere at all is entirely the invoking harness's call),
> and mode-specific detail (files changed and verification run, for
> `implement`; the full finding list, for review mode; the plan itself,
> for `mode: plan`).
>
> Calling this is always the last action in a run. `status: "planned"`
> is `plan`-mode-only — it means a plan was produced and posted, not
> that any code changed; it says nothing about whether an `implement`
> run will follow, since that's decided outside this run. `status:
> "blocked"` is for a run resuming after AskUser that still didn't fully
> resolve things; within a single run, use AskUser directly instead of
> reaching Complete with status `blocked`.
>
> In `implement` mode, the **first** `Complete(status: "done")` call
> does not complete the run. It returns a fixed checklist as the tool
> result instead — re-run your verification commands now and confirm
> they still pass; run `git status` and confirm every changed or
> untracked path is intended; confirm nothing throwaway leaked out of
> the scratch directory — and only a second `Complete` call actually
> ends the run. This is deliberate and deterministic (no extra model
> call), directly following SWE-agent's `review_on_submit_m` gate
> (`agent-self-verification.md` %2): a mechanical gate can't be talked
> out of firing, and false completion claims are the best-measured
> failure mode in this design's source research. Other statuses and
> other modes complete on the first call. The harness resets this
> gate (requiring the checklist again) if any state-modifying tools
> (like Edit or Write) are called after the first Complete call.

```json
{
  "name": "Complete",
  "input_schema": {
    "type": "object",
    "properties": {
      "status": { "type": "string", "enum": ["done", "planned", "skipped", "failed", "blocked"] },
      "summary": { "type": "string", "description": "Short, human-readable. This is what a person reads first." },
      "report": { "type": "object", "description": "Full structured report. Shape depends on mode — see formats.md." }
    },
    "required": ["status", "summary", "report"],
    "additionalProperties": false
  }
}
```
