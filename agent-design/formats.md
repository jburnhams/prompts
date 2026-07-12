# Formats

The wire formats connecting a task to Forge and Forge's output back out:
the context envelope each run starts with, `FetchJira`'s output shape,
the `Complete` report schema for each mode, the review-finding schema,
and the `AskUser` suspend/resume protocol.

---

## 1. Task envelope (`{{TASK_ENVELOPE}}`)

Tag-delimited, appended after `{{ENV_BLOCK}}` in the system prompt —
same convention `claude-code-action`'s `<context>`/`<pr_body>`/
`<comments>` tags use, adapted per mode. Untrusted external content
(ticket text, PR descriptions, existing comments) stays inside its own
tag rather than being interleaved into instruction text, so it's
visually and structurally separated from what Forge is being told to
do — the review system prompt's "data, not instruction" rule depends on
this separation actually existing in the envelope, not just being
stated as a rule.

### 1a. Coding mode

```
<task>
  <mode>implement</mode>
  <source>jira</source>
  <issue_key>PROJ-1234</issue_key>
  <repository>owner/repo</repository>
  <base_branch>main</base_branch>
  <target_branch>proj-1234-short-slug</target_branch>
</task>

<ticket>
  {{ full FetchJira output for issue_key, pre-fetched so the model
     doesn't spend a turn fetching what it always needs — see §2 }}
</ticket>

<repo_context>
  {{ optional: contents of the root project-conventions file, if one
     exists and is short enough to inline; otherwise its path only,
     and the model reads it itself in step 1 of its workflow }}
</repo_context>
```

`source` is `jira` or `manual`; when `manual`, `<ticket>` is replaced
with a `<instruction>` tag carrying the free-text task instead of a
fetched issue. `target_branch` is omitted when the task should create
its own branch name from the issue key.

### 1b. Review mode

```
<pull_request>
  Repository: owner/repo
  PR: #123
  Title: {{ title }}
  Author: {{ author }}
  Branch: {{ head }} -> {{ base }}
  State: {{ state }}
  Additions: {{ n }}  Deletions: {{ n }}  Changed files: {{ n }}
</pull_request>

<description>
  {{ PR body, verbatim }}
</description>

<changed_files>
  - {{ path }} ({{ added | modified | removed | renamed }}) +{{a}}/-{{d}}
  ...
</changed_files>

<diff>
  {{ plain unified diff, git diff -U5 style, all changed files
     concatenated in the order listed above }}
</diff>

<existing_comments>
  [{{ author }} at {{ timestamp }}]: {{ body }}
  [Review by {{ author }} at {{ timestamp }}]: {{ state }}
    [Comment on {{ path }}:{{ line }}]: {{ body }}
  ...
</existing_comments>
```

`<diff>` is pre-fetched and baked in — the orchestrator does not run
`git diff` itself (see `README.md`'s decision log for why: line-number
accuracy matters more when comments post with no human catching a
mis-anchored one). Plain unified diff rather than a custom hunk format,
to keep the format lean; the orchestrator passes the relevant slice of
this same diff text into each specialist's `Task` prompt rather than
re-fetching per specialist.

---

## 2. `FetchJira` output

```json
{
  "issue_key": "PROJ-1234",
  "title": "string",
  "issue_type": "Bug | Story | Task | ...",
  "status": "string, the issue's current workflow state",
  "priority": "string",
  "labels": ["string", "..."],
  "description": "string, Markdown-rendered",
  "acceptance_criteria": "string, Markdown-rendered, or null if the project doesn't use this field",
  "comments": [
    { "author": "string", "created_at": "ISO 8601", "body": "string, Markdown-rendered" }
  ],
  "linked_issues": [
    { "issue_key": "string", "relationship": "string, e.g. \"blocks\", \"relates to\"", "title": "string" }
  ]
}
```

`comments` is chronological, oldest first. `linked_issues` is included
so Forge can decide whether a linked issue is in-scope context without
a second fetch — it is not itself recursively expanded (no
`linked_issues` inside `linked_issues`).

---

## 3. `Complete` report schema

`status` and `summary` are common to both modes (see `tools.md`); the
`report` object's shape depends on which orchestrator is calling.

### 3a. Coding mode

```json
{
  "ticket": "PROJ-1234",
  "files_changed": [
    { "path": "string", "change_type": "added | modified | deleted | renamed", "additions": 0, "deletions": 0 }
  ],
  "verification": [
    { "check": "string, e.g. \"unit tests\", \"lint\", \"reproduction script\"", "command": "string", "result": "pass | fail | not_run", "detail": "string, only when result != pass" }
  ],
  "commits": [
    { "sha": "string", "message": "string" }
  ],
  "pull_request_url": "string, or null if mode was investigate/review_only",
  "judgment_calls": [
    "string — any ambiguity resolved without AskUser, and why; empty array if none"
  ],
  "open_questions": [
    "string; must be empty when status is \"done\""
  ]
}
```

### 3b. Review mode

```json
{
  "pull_request": "owner/repo#123",
  "findings": [
    { "...": "one review-finding object per confirmed, posted finding — see §4" }
  ],
  "filtered": [
    { "...": "review-finding objects that were raised by a specialist but not posted, with why — see §4's validated field" }
  ],
  "comment_urls": ["string, ..."]
}
```

`findings` and `filtered` together account for every candidate a
specialist raised — nothing silently disappears between step 3 and step
7 of the review pipeline (`system-prompts.md` §2) without a recorded
reason.

---

## 4. Review-finding schema

Produced by a `reviewer` sub-agent (as a candidate, `validated: null`),
then annotated by a `validator` sub-agent, then carried through to the
orchestrator's `Complete` report:

```json
{
  "id": "string, orchestrator-assigned once a specialist returns it",
  "role": "bugs | security | conventions",
  "file": "string",
  "line": 0,
  "line_end": 0,
  "severity": "blocking | high | medium | low",
  "summary": "string, one sentence",
  "rationale": "string, why this is a real problem, citing the specific rule/behavior",
  "suggested_fix": "string, Markdown/diff snippet, or null if none proposed",
  "validated": true,
  "validator_note": "string, the validator's one-sentence reason"
}
```

`validated: null` is the specialist's own output, before the validator
pass runs; `true`/`false` is the validator's verdict. Only `true`
findings are ever passed to `AddComment`. `severity` is set by the
specialist and is not re-judged by the validator — the validator's job
is "is this real," not "how bad is it."

---

## 5. `AskUser` suspend/resume protocol

The consequence of this design's core hands-off decision
(`README.md`): there is no in-process human turn to block on, so
`AskUser` doesn't behave like an interactive prompt — it ends the run,
and a *new* run resumes it later.

**Suspending:**

1. Forge calls `AskUser` with `question`, `context`, and optionally
   `options`.
2. The harness formats this into a comment and posts it via `AddComment`
   automatically, targeting the same PR or Jira issue the task
   originated from (the envelope's `issue_key` or PR id) — Forge does
   not call `AddComment` itself for this.
3. The harness records a suspended-task record keyed to that comment's
   id/URL, containing everything needed to resume: the original task
   envelope, the full transcript so far, and the question asked.
4. The run ends. No `Complete` call happens for a suspended run — the
   task is not finished, it's paused. (This is why `tools.md` says
   `AskUser` and `Complete` never share a turn: suspension is a distinct
   terminal state from completion, not a variant of it.)

**Resuming:**

1. A reply lands on the comment thread from step 2 — the same webhook/
   poll mechanism that already watches PR and Jira activity for other
   purposes picks it up.
2. The harness matches the reply to its suspended-task record via the
   comment id, and starts a new run with the original task envelope,
   plus the transcript from the suspended run, plus a new
   `<resumed_answer>` tag carrying the reply text appended after
   `{{TASK_ENVELOPE}}`.
3. Forge continues from where it left off — the resumed run's first
   action is normally to act on the answer, not to re-derive context it
   already gathered before suspending.
4. If the reply doesn't actually resolve the ambiguity (a non-answer, a
   deflection, a reply that raises a new question), Forge may call
   `AskUser` again rather than being forced to guess.

A task can suspend and resume more than once. There is no built-in cap
in v1 — a real deployment would likely want one (e.g. "escalate instead
of asking a third time"), left as a v2 addition per `README.md`'s
"what's not in v1" list rather than specified here without a concrete
reason to pick a specific number.
