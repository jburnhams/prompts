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
| AddComment | `plan` runs only | yes | no | no |
| Complete | yes | yes | no | no |

The "Review orchestrator" column covers both review run shapes
(`review.md` §6): the single-stage reviewer (`system-prompts.md` §2b)
uses this wiring unchanged — same tools, same absences — and its
`Task` calls are validator-only by prompt (the `reviewer`
subagent_type simply has no caller in that shape; the schema's enums
don't change).

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
text: in `plan` runs, `Edit` and `Write` are **not registered at
all** — for the coding orchestrator or
for any `general-purpose` sub-agent it spawns ("full tool parity"
means parity with the orchestrator *as wired for this run*, so a
read-only run cannot launder writes through a delegate). This follows
the same reasoning as the scratch-directory decision in `README.md`: a
structural boundary can't be forgotten, and the precedent is strong —
Gemini CLI strips agent-kind tools from sub-agent registries in code,
and Composio scopes permissions "at the tool level, not just by
instruction" (`agent-subagent-architectures.md` §6). `Bash` stays wired
in `plan` mode (read-only git inspection and read-only commands are
legitimate there); its general no-write rule remains prompt-enforced in
v1, with one narrow structural exception — the git-write blocklist
described in the Bash tool's own section below, which the harness
applies in every mode. Filtering arbitrary commands beyond that one
family is a real permission engine — see `medium.md`'s "General
command-level `Bash` permission filtering" escalation entry.

The narrowing runs the other way too: in `implement` runs, `AddComment`
is **not registered**. Plan mode needs it (workflow step 5 posts the
plan or finding to the ticket), but implement mode has no workflow step
that posts anything — the Complete report is its only outward channel,
and the harness owns what reaches the ticket or PR from it. Leaving the
tool wired anyway would be exactly the unused-escape-hatch surface this
design strips `AskUser` from review mode for: a tool with no legitimate
caller in that mode is only reachable by a prompt-injected instruction.
(`AskUser`'s suspend protocol is unaffected — the harness posts the
question itself; Forge never calls `AddComment` for it. Tracked
upgrades: `medium.md`'s PR-comment-responder runs wire `AddComment`
for threaded replies in that one task source, where replying *is* the
deliverable; `future.md`'s "Re-wiring `AddComment` in implement mode"
entry covers a general mid-run decision-notes channel.) The
system-prompt mode rules in
`system-prompts.md` remain as the behavioral layer on top of this
structural one.

---

## Implementation contract

The schemas below say what a call looks like. This section says what every
tool must do *around* the call — the rules
[`agent-tool-implementations.md`](../agent-tool-implementations.md) found
running through every mature harness's source, adopted here as a single
contract rather than restated per tool. Its §12 checklist is the source for
each rule; only the deviations are argued again below.

**Three channels per tool.** Every tool produces three things, and they are
built separately: the **model result** (text, per the format policy below),
the **harness record** (a typed object: what changed, what was truncated,
what path was touched — this is what the post-run `git status` cross-check
and the `Complete` report reconcile against), and, where a human is
watching, a **rendering**. Forge's prompts only ever see the first. This is
the split Claude Code makes with `outputSchema` +
`mapToolResultToToolResultBlockParam`, Gemini CLI with
`llmContent`/`returnDisplay`, and MCP with `content`/`structuredContent`.

**Output format policy.** Prose-shaped payloads — file contents, diffs,
search matches, command output — are returned as **raw text**, never
JSON-encoded. Fact-shaped payloads — exit codes, counts, truncation state,
ids, comment URLs — are returned as **named fields** (either a small JSON
object, or `key: value` lines when they accompany prose). No tool returns a
file body inside a JSON string: escaping inflates tokens and breaks the
byte-exact match `Edit` depends on. Untrusted or heterogeneous content
inside a result is delimited with XML-style tags, the same device
`formats.md` §1 uses for the task envelope, for the same reason.

**Every cap is self-describing.** Any truncation, page, or elision appends
a footer stating three things: what was shown, how much exists, and the
exact next call. Not "output truncated" but "Showing lines 1-2000 of 8123 —
pass `offset: 2001` to continue." Three independent implementations
(Gemini CLI's `Action:` block, OpenCode's `Use offset=N to continue`,
Claude Code's pagination note) converge on this, and a cap without a
continuation instruction is the one failure mode that reliably turns into a
retry loop. Notices go at the head or tail of a result, never in an elided
middle, so they survive any later re-truncation.

**Caps by default, errors on impossible explicit requests.** A call that
omits limits and gets a large result is capped and told so. A call that
*explicitly* asks for more than a cap allows fails with a short error
instead of returning a capped success. The reasoning is measured, not
aesthetic: Claude Code tested truncating instead of throwing on exactly
this case (`FileReadTool/limits.ts`, experiment #21841) and reverted —
tool-error rate fell but mean tokens rose, because an error result costs
~100 bytes and a capped success costs a full page of content the model
didn't want.

**Spill, don't dump.** A result past the harness's size ceiling is written
to a file in the scratch directory (`{{SCRATCH_DIR}}`, `formats.md` §1a) and
the model receives a preview plus that path. `Read` is the deliberate
exception — spilling a read to a file the model then reads back is circular
— so `Read` self-bounds via its own limits instead.

**Errors are instructions.** Every tool error states what happened, what to
do about it, and — where the harness can compute one — a concrete
suggestion. "File does not exist. Did you mean `src/parser/index.ts`?" beats
"ENOENT". "Found 3 matches for `old_string`; add surrounding lines or set
`replace_all`" beats "ambiguous match". Nothing ever returns silent
emptiness: an empty file, an offset past EOF, and a search with no hits each
say so in words.

**Advertise strict, accept tolerant.** The schemas below are the advertised
contract and stay strict (`additionalProperties: false`). The harness's
parser is deliberately looser: it coerces stringified numbers, accepts the
obvious aliases for a path field, clamps out-of-range line numbers rather
than rejecting them, and normalises a bare string where an object was
expected. A rejected call costs a full turn and teaches nothing; a
normalised one costs nothing. (Precedent: Cline's SDK parses `read_files`
against a 13-branch union while advertising one shape; Zed clamps
`start_line: 0` to 1 in code with a comment noting models do this despite
instructions.)

**Line numbering is one contract shared by Read and Edit.** `Read` returns
`cat -n`-style output: the 1-indexed line number, a tab, then the line's
exact bytes. `Edit`'s `old_string` matches against the bytes *after* the
tab. These two facts are a single decision — changing the prefix format
means changing both tools' descriptions in the same edit — and both
descriptions below state it explicitly, because echoing the prefix back
into `old_string` is the most common way an exact-match edit fails.

**Tool results are an injection point.** Two things ride along with results
rather than living in the system prompt: when `Read` returns a file that has
a project-conventions file governing its directory, that file's content is
appended inside a `<system-reminder>` block (OpenCode, Gemini CLI and Claude
Code each do a version of this); and any content originating outside the
repository is sanitized before it lands, per `formats.md` §1.

**Two pieces of harness-side state make the file tools safe.**
*Read-before-edit*: `Edit` and `Write` fail on a path this run has not
`Read` (for `Write`, only when the file already exists), enforced by a
per-run read-state cache rather than by prompt text — the same
structural-gate principle as the git-write blocklist.
*Unchanged-file dedup*: re-reading a file whose mtime and size are unchanged
since the last `Read` in this run returns a one-line stub pointing at the
earlier result instead of the content again. On a long implement run that
re-reads the same handful of files, this is the single largest token saving
available, and no other saving in this design competes with it for
cost-to-build.

**Per-tool harness metadata.** Every tool declares, in code, whether it is
read-only, whether it is safe to run concurrently with another call, and
whether it is destructive. These are what `plan`-mode wiring, parallel
dispatch, and the completion gate key off — not prompt text. For v1:

| Tool | Read-only | Concurrency-safe | Destructive |
|---|---|---|---|
| Read, Grep, Glob, FetchJira | yes | yes | no |
| Edit, Write | no | only for disjoint paths | no |
| Bash | unknown (assume no) | no | assume yes |
| Task | inherits the child's wiring | yes | no |
| AddComment | no (external) | no | yes (a post is not retractable) |
| AskUser, Complete | terminal | n/a | n/a |

"Assume no / assume yes" is the fail-closed default every source surveyed
uses for an unclassifiable shell.

**The tool set is configuration, not a constant.** Nothing in this document
should be read as "these eleven tools, this text, for every model." Gemini
CLI ships per-model-family schemas and descriptions for identical tools;
Cline routes `apply_patch` to GPT/Codex-family models and a string-replace
editor to everything else. Forge's v1 ships one set because it targets one
model family; the descriptions below are the artifact a per-model variant
would fork, and `medium.md` tracks the edit-format fork as the first likely
one.

---

## Read

> Reads a file from the working tree. Use an absolute path, or one
> relative to the working directory named in `<env>`.
>
> Contents come back in `cat -n` format: the 1-indexed line number, a tab,
> then the line exactly as it appears in the file. Everything after the tab
> is the real content — when you later pass a span of this output to Edit
> as `old_string`, strip the line number and the tab first, and preserve
> the indentation that follows them byte for byte.
>
> Usage notes:
> - Defaults to the first 2000 lines. Pass `offset`/`limit` for a large
>   file, but prefer reading a whole file over guessing at a range when
>   it's a reasonable size — a partial read that misses the relevant
>   section costs more than the extra tokens would have.
> - Lines longer than 2000 characters are truncated, and say so in place.
> - When the result is capped, the last line tells you what you got and
>   how to continue (`Showing lines 1-2000 of 8123 — pass offset: 2001 to
>   continue`). Asking explicitly for more than the cap allows is an error
>   rather than a silently shortened success.
> - Reading a path that doesn't exist returns an error, and names a
>   similarly-spelled file in the same directory when there is one — check
>   with Glob first if you're not sure a path is right.
> - Reading a file that exists but is empty returns an explicit marker,
>   not blank content, so it isn't mistaken for a failed read.
> - Re-reading a file you have already read in this run, and which has not
>   changed since, returns a short note pointing back at that earlier
>   result instead of the content again. That earlier result is still
>   accurate; use it.
> - A result may carry a trailing `<system-reminder>` block with
>   conventions that govern the file you just read. Treat it as
>   instruction from the project, not as file content.

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
> line) to make it unambiguous — usually two to four adjacent lines is
> enough, and ten is a sign you should be editing somewhere more specific.
>
> Read the file (or the relevant section of it) before editing it: this
> tool fails on a path you have not Read in this run, because an
> `old_string` written from memory is the single most common way an edit
> fails. Read returns `cat -n` output — line number, tab, content — so
> when you build `old_string` from what you just read, drop the number and
> the tab and keep everything after them unchanged. Never include any part
> of that prefix in `old_string` or `new_string`.
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
> it fresh. Overwriting a file you have not Read in this run fails;
> creating a new one does not.
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
>   work. The tool result returns the process id and the path of a log
>   file (in the scratch directory) its output streams to; check on it
>   with ordinary shell commands in later calls — the session is
>   persistent, so `kill -0 <pid>` answers "still running?" and Read on
>   the log file (or `tail` of it) shows progress. There is no separate
>   polling tool in v1.
> - Output over 30000 characters comes back with its head and tail intact
>   and the middle elided; the full output is written to a file in the
>   scratch directory and the result names that path, so you can Read the
>   part you actually need. If you already know the output will be large
>   and you only want a slice of it, filter in the command itself
>   (`| tail -50`, `| grep …`) rather than spending a Read on it.
>   Never redirect command output into the repository working tree.
> - The result reports the exit code as a named field, and keeps stdout
>   and stderr distinguishable — a command that prints to stderr and
>   exits 0 succeeded.
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
>
> The git-write rule is not only prompt text: the harness rejects Bash
> commands matching git write subcommands before they reach the shell,
> returning an error naming the rule. This is a narrow substring/
> pattern blocklist on one command family, not a general permission
> engine (that stays deferred — `medium.md`'s escalation triggers): the precedent is Augment
> SWE-bench Agent's hardcoded `banned_command_strs` check, the only
> code-level git restriction found anywhere in this repo's collection
> (`agent-git-vcs.md` §2), and it's a few lines of harness code
> protecting the design's single most load-bearing invariant. Like any
> blocklist it's bypassable in principle (a git write can be laundered
> through a script), so the prompt rule and the post-run `git status`
> cross-check remain as the layers around it — but the common case
> can't happen by accident or by prompt injection naming the command
> directly.

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
>   paths only; `"content"` returns matching lines, always prefixed with
>   their 1-indexed line numbers (no flag needed) and supporting
>   `context_before`/`context_after`; `"count"` returns per-file match
>   counts.
> - Filter with `glob` (e.g. `"*.ts"`) or `type` (e.g. `"python"`).
> - Patterns are ripgrep regex, not shell-glob — escape literal braces
>   (`interface\{\}`) etc.
> - `multiline: true` lets `.` match newlines, for a pattern that spans
>   lines.
> - Results are capped at 250 entries unless you set `head_limit`
>   (equivalent to `| head -N`); `offset` skips that many entries first
>   (equivalent to `| tail -n +N | head -N`), so a search with more hits
>   than fit can be paged rather than re-run with a narrower pattern you
>   had to guess at. When the cap applies, the result says so and gives
>   the `offset` to continue from.
> - A search with no matches says so; it never returns an empty result.

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
      "head_limit": { "type": "integer", "description": "Cap the number of results returned, equivalent to \"| head -N\". Defaults to 250." },
      "offset": { "type": "integer", "description": "Skip this many results before applying head_limit, equivalent to \"| tail -n +N | head -N\". Defaults to 0." }
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
>   do this. The harness caps how many run concurrently (a small fixed
>   number; Codex CLI's default of 16 and OpenHands's 5-8 are the
>   field's code-enforced precedents — `agent-subagent-architectures.md`
>   §5) and queues the rest, so a validator fan-out larger than the cap
>   is safe to dispatch in one turn — it just won't all run at once.
> - Never launch two sub-agents in the same turn if their write targets
>   could overlap (only relevant for `general-purpose`, since `reviewer`/
>   `validator` never write). If you're not sure their file sets are
>   disjoint, run them sequentially instead.
> - A sub-agent's report should generally be trusted for `general-purpose`
>   research tasks. For `reviewer` output specifically, treat it as a
>   *candidate* only — that's what the validator step is for; don't
>   act on a specialist's finding directly.
> - `general-purpose` cannot itself call Task — no recursive delegation
>   in v1 (see `future.md`'s "Addressable/resumable sub-agents" entry).

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
> comment — on a Jira issue or a pull request (Bitbucket or GitHub).
> One tool for every platform, per the brief; platform differences are
> handled by which optional fields you set and by harness-side
> capability handling, not by separate tools. Wired in review runs and
> `plan`-mode coding runs only — an `implement` run's sole outward
> channel is its Complete report (see the availability notes at the top
> of this document). `body` is always plain
> Markdown regardless of target — converting it to whatever the target
> platform actually needs (e.g. Jira Cloud's ADF, or legacy wiki markup)
> is a harness-side concern, not something this schema or Forge itself
> handles; see `README.md`'s decision log ("Comment body format").
>
> - `target.platform: "jira"` + `target.id` (an issue key): posts a
>   Jira comment. `in_reply_to` is honored as a best-effort @-mention
>   reference — Jira's own comment model isn't fully threaded, so a true
>   nested reply isn't always possible; the tool falls back to a
>   plain comment prefixed with a reference to the original if the
>   target platform can't thread it.
> - `target.platform: "bitbucket_pr"` + `target.id`
>   (`"workspace/repo-slug#123"`): posts a Bitbucket PR comment.
>   Bitbucket PR comments are natively threaded, so `in_reply_to`
>   (a comment id) produces a true nested reply.
> - `target.platform: "github_pr"` + `target.id` (`"owner/repo#123"`):
>   posts a GitHub PR comment. Set `in_reply_to` (a comment id) to
>   reply within an existing review thread rather than starting a new
>   one.
> - On either PR platform, set `anchor` (file + line, optionally a
>   `line_end` for a range) for an inline review comment; omit it for a
>   general PR comment. Anchor line numbers are **new-file (post-change)
>   line numbers** — the same side the review-finding schema uses.
> - An inline comment can only attach to lines that appear in the PR's
>   diff. The harness validates the anchor before posting; if it isn't
>   commentable, the comment is posted as a general PR comment prefixed
>   with `file:line` instead of being dropped, and the tool result says
>   which happened — so a mis-derived line number degrades visibly, not
>   silently.
> - `suggestion` wraps `body` in the platform's committable suggestion
>   block, replacing the full anchored line range. Only set this when
>   applying it verbatim fully resolves the issue — never for a fix that
>   needs a follow-up step. Requires `anchor` (schema-enforced below).
>   When set, `body` must contain **only the exact replacement source
>   lines** — no prose, no Markdown fences, no explanation. The platform
>   commits the block's contents verbatim over the anchored range, so
>   any explanatory text inside it becomes a syntax error in someone's
>   codebase when they click "apply." Put the explanation in a separate
>   unanchored or prose comment if one is needed, or skip the
>   suggestion and describe the fix in prose instead. Suggestion-block
>   support varies by platform deployment; where the target can't apply
>   one, the harness posts the same content as a plain fenced code block
>   labeled as a suggested replacement, and the tool result says so —
>   the same degrade-visibly pattern anchor validation uses.
>
> Returns the posted comment's id and URL, which a caller can use as a
> later `in_reply_to` value. On PR targets the result also reports
> `head_moved: true` when the PR's head has advanced past the
> envelope's `Head SHA` since the run started — the comment still
> posts, anchored to the reviewed commit; see `review.md` §8 for the
> race policy this serves.

(Phase 2 reserves one additional field on this schema:
`resolve_thread`, a boolean valid only with `in_reply_to`, used by
re-review reconciliation to reply-and-resolve in one call — see
`review.md` §7c and `medium.md` §3f. Not part of the v1 schema below.)

```json
{
  "name": "AddComment",
  "input_schema": {
    "type": "object",
    "properties": {
      "target": {
        "type": "object",
        "properties": {
          "platform": { "type": "string", "enum": ["jira", "bitbucket_pr", "github_pr"] },
          "id": { "type": "string", "description": "Jira issue key, \"workspace/repo-slug#pr_number\" for a Bitbucket PR, or \"owner/repo#pr_number\" for a GitHub PR." }
        },
        "required": ["platform", "id"],
        "additionalProperties": false
      },
      "body": { "type": "string", "description": "Comment text, Markdown. The harness converts to the target platform's native format if needed (e.g. Jira ADF) — this schema always carries Markdown." },
      "in_reply_to": { "type": "string", "description": "Optional: id of an existing comment to reply to." },
      "anchor": {
        "type": "object",
        "description": "Optional, PR targets only: anchors the comment to a specific new-file line or line range.",
        "properties": {
          "file": { "type": "string" },
          "line": { "type": "integer", "description": "New-file (post-change) line number. The start of the range when line_end is set." },
          "line_end": { "type": "integer", "description": "Optional: new-file line number ending the range, inclusive. Omit for a single-line anchor." }
        },
        "required": ["file", "line"],
        "additionalProperties": false
      },
      "suggestion": { "type": "boolean", "description": "Wrap body as a committable suggestion block replacing the anchored line range. PR targets, anchored comments only." }
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
> is `plan`-mode-only, for the case where the investigation found an
> actual change to make — it means a plan was produced and posted, not
> that any code changed; it says nothing about whether an `implement`
> run will follow, since that's decided outside this run. A `plan`-mode
> run that instead concludes no code change is needed uses
> `status: "done"` with an empty `steps` list in `report` — the finding
> was still posted per the same workflow, there's just nothing to hand
> off. `status: "blocked"` is for a run resuming after AskUser that
> still didn't fully resolve things; within a single run, use AskUser
> directly instead of reaching Complete with status `blocked`.
>
> In `implement` mode, the **first** `Complete(status: "done")` call
> does not complete the run. It returns a fixed checklist as the tool
> result instead — re-run your verification commands now and confirm
> they still pass; run `git status` and confirm every changed or
> untracked path is intended; confirm nothing throwaway leaked out of
> the scratch directory — and only a second `Complete` call actually
> ends the run. This is deliberate and deterministic (no extra model
> call), directly following SWE-agent's `review_on_submit_m` gate
> (`agent-self-verification.md` §2): a mechanical gate can't be talked
> out of firing, and false completion claims are the best-measured
> failure mode in this design's source research. Other statuses and
> other modes complete on the first call. The harness resets this
> gate (requiring the checklist again) if Edit, Write, or Bash is
> called after the first Complete call — Bash included because it can
> modify the working tree just as freely as Edit (a package-manager
> run, a formatter, a code-generation script), and v1 has no
> command-level filter to tell a read-only invocation from a mutating
> one, so the reset has to be conservative.

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
