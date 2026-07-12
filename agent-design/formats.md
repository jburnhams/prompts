# Formats

The wire formats connecting a task to Forge and Forge's output back out:
the context envelope each run starts with, `FetchJira`'s output shape,
the `Complete` report schema for each mode (including the plan
schema), the review-finding schema, the `AskUser` suspend/resume
protocol, the plan → implement handoff between runs, and the run-
bounding contract the harness enforces around every run.

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

Tag separation defends against structural confusion; it does nothing
against invisible-character payloads. Before any untrusted content
(ticket text, PR bodies, comments, diffs) is placed into an envelope,
the harness sanitizes it **in code**: strip zero-width and other
invisible Unicode, bidi-override characters, and hidden HTML
attributes/comments. `claude-code-action`'s `sanitizer.ts` is the
precedent — the only source in this collection doing this in code
rather than by instruction (`code-review-approaches.md` §10), and the
right layer for it, since a model can't be instructed to ignore
characters it can't see.

The same sanitizer applies to `FetchJira` results returned mid-run —
a linked issue fetched in turn 12 is the same untrusted content as the
ticket baked into the envelope at turn 0, arriving through a different
door, and skipping it there would leave the envelope pass trivially
bypassable by anything that can get Forge to fetch an issue. (Repo
*file* contents read via Read/Grep are deliberately not sanitized in
v1 — mangling source bytes would break Edit's exact-match contract;
the residual invisible-Unicode risk from a malicious file in a
reviewed PR is accepted and noted in `future.md`.)

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

<plan>
  {{ optional — present only on an `implement` run dispatched as the
     follow-up to an accepted `mode: plan` run against this same
     issue_key. Carries that earlier run's Complete report.report
     verbatim (the plan schema, §3c) — see §6, the plan/implement
     handoff }}
</plan>

<repo_context>
  {{ optional: contents of the root project-conventions file, if one
     exists and is short enough to inline; otherwise its path only,
     and the model reads it itself in step 1 of its workflow }}
</repo_context>
```

`source` is `jira` or `manual`; when `manual`, `<ticket>` is replaced
with a `<instruction>` tag carrying the free-text task instead of a
fetched issue, and the envelope additionally carries a
`<comment_target>` tag naming a valid `AddComment` target (platform +
id) for anything the run needs to post — the plan-mode workflow's
step 5 posting and the AskUser suspend protocol (§5) both route there
when there's no originating issue to default to. `target_branch` names the branch the harness has
**already checked out** before this run starts — Forge works directly
in that working tree and never creates, names, or switches branches
itself (see `system-prompts.md`'s coding-mode workflow, step 5). It's
included here purely so Forge can reference the branch name in its
`Complete` summary if useful, not as something to act on.

### 1b. Review mode

```
<pull_request>
  Repository: owner/repo
  PR: #123
  Title: {{ title }}
  Author: {{ author }}
  Branch: {{ head }} -> {{ base }}
  Head SHA: {{ head_sha }}
  Base SHA: {{ base_sha }}
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
  [{{ comment_id }} | {{ author }} at {{ timestamp }}]: {{ body }}
  [Review by {{ author }} at {{ timestamp }}]: {{ state }}
    [{{ comment_id }} | Comment on {{ path }}:{{ line }}{{ , resolved | , outdated }}]: {{ body }}
  ...
</existing_comments>
```

Each entry carries the platform's comment id — that's what makes
`AddComment`'s `in_reply_to` usable against a comment Forge didn't post
itself (the brief's threaded-reply requirement), not just against ids
returned by Forge's own earlier `AddComment` calls. Inline review
comments that GitHub reports as resolved or outdated are annotated as
such, in the envelope itself — the review pipeline's dedup step
(`system-prompts.md` §2, step 4) is told to ignore resolved/outdated
comments, and it can only do that if the envelope actually distinguishes
them.

`<diff>` is pre-fetched and baked in — the orchestrator does not run
`git diff` itself (see `README.md`'s decision log for why: line-number
accuracy matters more when comments post with no human catching a
mis-anchored one). Plain unified diff rather than a custom hunk format,
to keep the format lean; the orchestrator passes the relevant slice of
this same diff text into each specialist's `Task` prompt rather than
re-fetching per specialist. (If mis-anchored comments show up in
practice, PR-Agent's per-hunk new-file line-number injection is the
documented upgrade path — see `future.md`'s "PR-Agent-style per-hunk
line-number injection" entry — since deriving new-file line numbers by
hunk arithmetic is the error-prone step; `AddComment`'s harness-side
anchor validation in `tools.md` is the v1 backstop.)

**Harness guarantees for review mode**: the working tree is checked out
at `Head SHA`, and `<diff>` is exactly `base_sha...head_sha`. This is
load-bearing, not incidental — `reviewer` and `validator` sub-agents
are told to pull in surrounding context with Read/Grep/Glob, which is
only sound if the tree they're reading is the code the diff describes.
All line numbers in findings and comment anchors are new-file
(post-change) line numbers at `Head SHA`.

**Diff size**: the envelope inlines the full diff, so the harness must
gate on size *before* dispatching a run — past the threshold there is
no code path in which Forge even gets to call `Complete(skipped)`,
because the run dies on context before its first turn. V1 behavior
above the threshold is skip-with-reason, reported the same way a
`skipped` run reports.

Skip, not shard: no source in this collection does automated
sharding-with-merge (splitting specialists per file group and
reconciling cross-file findings across batches), including Anthropic's
own `/code-review` skill that this review pipeline is modeled on — its
own troubleshooting guidance for large PRs is "consider splitting large
PRs into smaller ones," a step taken by the PR author before review,
not something the review harness does. BMAD's >3000-changed-lines
chunking cascade, the field's other precedent, is human-mediated across
separate runs (a person agrees the first file group, then the rest are
noted for follow-up runs) — nobody has solved "which findings span a
batch boundary" without a human arbitrating the split, which doesn't
transfer to an unsupervised pipeline. Skip-with-reason is what every
real source effectively falls back to once the human-mediation each one
leans on is netted out.

The threshold itself is a harness config value, not a constant in this
design, and the harness may express it either way:

- a fixed changed-line count (BMAD's shape — simple, diff-tool-native,
  no model/tokenizer dependency; BMAD's own ~3000-line figure carries no
  stated derivation, so it's a sanity-check anchor here, not a default
  to inherit), or
- a fraction of the deployed model's context-window token budget,
  estimated from diff character count via a fixed chars-per-token
  ratio (no real tokenizer call — this is a cheap guesstimate gate,
  not an exact accounting) — this shape follows the deployed model's
  actual window rather than a number picked for one model and left
  stale after a model swap, and it can additionally divide by
  `(1 + number of specialist lenses)` to account for the diff being
  copied into every specialist's `Task` prompt in v1 (see `future.md`'s
  "Diff-as-file instead of diff-in-prompt-thrice" entry for the fix
  that would remove that multiplier).

Which shape a deployment uses is a harness config choice, not a Forge
behavior difference — either way Forge only ever sees a run that either
dispatches normally or never starts.

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
    { "id": "string, the platform's comment id — usable as AddComment's in_reply_to", "author": "string", "created_at": "ISO 8601", "body": "string, Markdown-rendered" }
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
  "target_branch": "string, the branch the working tree was left on",
  "files_changed": [
    { "path": "string", "change_type": "added | modified | deleted | renamed", "additions": 0, "deletions": 0 }
  ],
  "verification": [
    { "check": "string, e.g. \"unit tests\", \"lint\", \"reproduction script\"", "command": "string", "result": "pass | fail | not_run", "detail": "string, only when result != pass" }
  ],
  "suggested_commit_message": "string — a proposed commit message (summary + body) for whatever picks up this branch to use or adapt; not applied by Forge itself",
  "judgment_calls": [
    "string — any ambiguity resolved without AskUser, and why; empty array if none"
  ],
  "open_questions": [
    "string; must be empty when status is \"done\""
  ]
}
```

No `commits`/`pull_request_url` fields — Forge never commits, pushes, or
opens a pull request in v1 (see `README.md`'s decision log). The
working tree left behind, plus this report, is the complete handoff;
`suggested_commit_message` exists so the external process that does
commit doesn't have to re-derive intent from a diff alone.

`files_changed` and `verification` are the model's self-report, and the
harness does not take them on faith: after the run it computes the real
changed-path list from `git status` and attaches any mismatch to the
report it hands downstream (so the external committer sees the
discrepancy, not just a log line). In read-only modes, a non-empty
working-tree diff of tracked files (e.g., via `git diff --exit-code`)
after the run is a hard integrity failure the harness flags regardless.
In `plan` mode the harness additionally checks that at least one
successful `AddComment` call happened before `Complete` — the plan-mode
workflow's step 5 posting is unconditional, so its absence means the
run claimed an outcome it never delivered to the ticket. Together with
the first-call checklist gate (`tools.md`), these are the design's
answer to the false-completion-claim failure mode
`agent-self-verification.md` documents as real and measured —
deterministic checks that can't be talked out of firing, not a second
LLM judge (which stays out of v1, per the README's leanness rule).

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
reason. A candidate dropped by the pre-validation dedup (pipeline step
4) appears in `filtered` with `validated: null` and the dedup reason —
it was never judged wrong, just already reported.

### 3c. Plan mode

```json
{
  "ticket": "PROJ-1234",
  "approach": "string — a few sentences: what will change and why (or, if steps is empty, what was investigated and why no change is needed), in plain terms",
  "steps": [
    { "order": 1, "description": "string, concrete and specific", "files": ["string, ..."] }
  ],
  "context_gathered": [
    { "file": "string", "note": "string — why this file/area is relevant, what an implement run needs to know about it" }
  ],
  "risks_and_assumptions": [
    "string — anything this plan assumes that could turn out false"
  ],
  "out_of_scope": [
    "string — explicitly not covered by this plan, and why, so an implement run doesn't silently expand scope"
  ],
  "acceptance_criteria": "string — restated/clarified from the ticket, resolving any ambiguity AskUser didn't need to be raised for"
}
```

`steps` is written for a fresh `implement` run with no memory of this
one to consume — concrete enough to act on (`files`, not just prose)
without forcing it to skip its own verification. `context_gathered` is
what makes handing this to a *different* run viable at all: without it,
an implement run has to redo the investigation from scratch, which
defeats the point of planning first. See §6 for how this schema actually
reaches that later run.

`steps: []` is a valid, deliberate outcome, not an incomplete plan — it
represents a `plan`-mode run that investigated and concluded no code
change is needed (the ticket was a question, the behavior was already
correct, the report wasn't reproducible). This is how `mode: plan`
covers what an earlier draft of this design called a separate
`investigate` mode: both are the same read-only investigation, and only
the *outcome* differs, not the mode. `status` on the `Complete` call is
`"done"` rather than `"planned"` in this case (`tools.md`); `approach`,
`context_gathered`, and `risks_and_assumptions` are still populated to
explain the finding, and step 5 of the plan-mode workflow
(`system-prompts.md`) still posts it — a ticket that asked a question
gets an answer on the ticket either way.

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
is "is this real," not "how bad is it." `line`/`line_end` are new-file
(post-change) line numbers at the envelope's `Head SHA` — the same
convention `AddComment`'s anchor uses, so a finding's location passes
through to a posted comment without translation.

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
   automatically, targeting the Jira issue the task originated
   from (the envelope's `issue_key`; for a `source: manual` task,
   wherever the harness routes that task's communication) — Forge does
   not call `AddComment` itself for this. AskUser is coding-mode-only
   (`tools.md`): review runs end in `Complete`, never a suspension.
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
of asking a third time"), left as a v2 addition per `future.md` rather
than specified here without a concrete reason to pick a specific
number.

One interaction worth stating explicitly: a resumed run inherits the
suspended run's full transcript, so it starts with most of that run's
context already spent. The run-bounding budgets (§7) apply to the
resumed run as normal — which means a run that suspended near its
context high-water mark can resume, act on the answer briefly, and hit
the final-turn nudge almost immediately. That's the intended behavior,
not a bug (the nudge guarantees an honest `Complete(failed)` with a
partial report rather than a silent death), but a harness that wants
resumed runs to have real headroom should suspend-and-resume with a
raised budget or accept that late-run questions buy very little
additional work.

---

## 6. Plan → implement handoff

How a `mode: plan` run's output becomes a `mode: implement` run's
input. Deliberately underspecified in one place, on purpose — see the
callout at the end.

1. A `mode: plan` run ends one of three ways: `AskUser` (per §5, same
   suspend/resume mechanics — the run pauses on a question, and when it
   resumes, it's still `mode: plan`, concluding only once unblocked),
   `Complete` with `status: "planned"` and a §3c plan with a non-empty
   `steps` list in `report`, or `Complete` with `status: "done"` and an
   empty `steps` list — a no-action finding, per §3c's note. Either way
   the text was also already posted to the originating Jira issue via
   `AddComment` (plan mode workflow step 5, `system-prompts.md`) — that
   posting is unconditional and happens regardless of what occurs next.
   Only the `status: "planned"` case has anything left to hand off; the
   rest of this section doesn't apply to a no-action finding.
2. Whatever invoked the plan run decides whether, and when, to dispatch
   a follow-up `mode: implement` run. This document does not specify
   that policy — it's a deployment-time choice, not something Forge's
   own prompt encodes (see `README.md`'s decision log for why this was
   left open deliberately rather than picked). Two patterns are equally
   valid implementations of everything above:
   - **Gated**: treat the posted plan like an `AskUser` question in
     reverse — wait for an explicit approving reply on the same thread
     before dispatching `implement`.
   - **Auto-chained**: dispatch `implement` immediately once
     `Complete(status: "planned")` returns; the posted comment is
     audit trail, not a gate.
3. When the `implement` run is dispatched, its task envelope (§1a)
   carries the same `issue_key` as the plan run, `mode: implement`, and
   a `<plan>` tag containing the plan run's `report` object verbatim —
   this is the entire mechanism by which context transfers between the
   two runs; there is no other channel, since each run starts with a
   fresh context window.

The one thing worth being explicit about even though the gating policy
itself is left open: **whatever makes that decision is responsible for
also handling a rejected or amended plan** (a human reply asking for
changes rather than approving) — that's a new `mode: plan` run, with the
rejection/amendment appended to its envelope the same way
`<resumed_answer>` works in §5, not a special case this schema needs its
own field for.

---

## 7. Run bounding

"The only way a run finishes is `Complete`" is only enforceable if
something guarantees the run gets a last chance to call it. A hands-off
run has no human to notice it drifting or to type `/compact` — so the
harness bounds every run with two budgets, and the design takes an
explicit position on what happens at each:

1. **A turn budget and a context high-water mark**, both set by the
   harness per run. Crossing either doesn't kill the run — it triggers
   a **final-turn nudge**: an injected message stating that this is the
   last turn and the only acceptable actions are `AskUser` or
   `Complete`, with whatever status honestly describes the state —
   `Complete(status: "failed")` carrying a partial report (what was
   done, what was verified, what remains) is a *successful* use of the
   mechanism, not a failure of it. The harness structurally blocks and
   rejects any other tool calls on this turn to guarantee termination.
   The precedent is Copilot Chat's forced last-turn cutoff message
   ("OK, your allotted iterations are finished...") — deterministic
   string injection, no extra model call (`agent-self-verification.md` §7).
   In review mode, where `AskUser` isn't wired at all (`tools.md`), the
   nudge names `Complete` as the only acceptable action — the injected
   text is mode-aware, not one fixed string.
   Grok Build's harder variant — refusing to end a turn at all while
   work is still open — is not adopted here, since it fights the same
   budget this mechanism exists to enforce.
2. **No compaction in v1.** Summarize-and-continue is a genuine
   subsystem (triggers, templates, incremental anchoring — see
   `agent-context-compaction.md`) that this design deliberately does
   not absorb at launch. A run that can't finish inside its budgets
   ends via the nudge above, and the report says so; the ticket hears
   "this didn't fit," which is actionable (split the ticket, raise the
   budget), instead of silence, which isn't. Compaction is the natural
   v2 lever if budget-exhausted runs turn out to be common on
   legitimately-sized tasks.

A run killed by infrastructure failure (crash, timeout at a layer below
the harness) is the one case with no `Complete` — the harness itself
posts the failure note to the originating ticket/PR, so silence still
never reaches the person waiting.
