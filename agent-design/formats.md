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
  Platform: {{ bitbucket | github }}
  Repository: {{ workspace/repo-slug | owner/repo }}
  PR: #123
  Title: {{ title }}
  Author: {{ author }}
  Branch: {{ head }} -> {{ base }}
  Head SHA: {{ head_sha }}
  Base SHA: {{ base_sha }}
  State: {{ state }}
  Snapshot: {{ ISO 8601 — when this envelope's state was captured }}
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
  <general>
    [{{ comment_id }} | {{ author }} at {{ timestamp }}]: {{ body }}
    [{{ comment_id }} | Review by {{ author }} at {{ timestamp }} | {{ state }}]: {{ body }}
  </general>
  <thread id="{{ thread_id }}" anchor="{{ path }}:{{ line }}" status="open|resolved">
    [{{ comment_id }} | {{ author }} at {{ timestamp }}]: {{ body }}
    [{{ comment_id }} | reply | {{ author }} at {{ timestamp }}]: {{ body }}
  </thread>
</existing_comments>
```

The interior of `<existing_comments>` — the thread model, its
trimming rules, and who consumes it — is specified in `review.md` §3;
the skeleton above is the shape at a glance. Each entry carries the
platform's comment id — that's what makes `AddComment`'s
`in_reply_to` usable against a comment Forge didn't post itself (the
brief's threaded-reply requirement), not just against ids returned by
Forge's own earlier `AddComment` calls. `status` is the
conversation's state only (`open`/`resolved`, mapped from the
platform's native resolution); whether a thread's *anchored code* has
changed since it was written is the orthogonal staleness fact,
carried by an `at_sha` attribute plus, in phase 2, then/now context
blocks and a conditional `<format_notes>` explainer — all specified
in `review.md` §3a–3b. The review pipeline's dedup step
(`system-prompts.md` §2, step 4) considers open threads only, stale
or not. Formal-review entries (`[... | Review by ...]`) appear only
where the platform has that concept — Bitbucket approvals and change
requests are rendered into the same shape by the harness, so Forge's
dedup logic doesn't branch per platform.

Two further tags are reserved for re-review sessions —
`<review_state>` (the findings prior sessions posted, with live
thread status) and `<incremental_diff>` (the delta since the last
reviewed head, same construction rules as `<diff>`). Both are additive
and phase 2: a first review simply omits them, and their full shape
and consuming pipeline live in `review.md` §7 (roadmap entry:
`medium.md` §3f).

`<diff>` is pre-fetched and baked in — the orchestrator does not run
`git diff` itself (see `README.md`'s decision log for why: line-number
accuracy matters more when comments post with no human catching a
mis-anchored one). The exact construction algorithm — merge-base
three-dot semantics, `-U5 -M`, file ordering, and the visible-elision
rules for generated/binary/oversized files — is specified in
`review.md` §2. Plain unified diff rather than a custom hunk format,
to keep the format lean; the orchestrator transcludes this same diff
text verbatim into each specialist's `Task` prompt (the brief format
in `review.md` §4) rather than re-fetching or paraphrasing per
specialist. (If mis-anchored comments show up in
practice, PR-Agent's per-hunk new-file line-number injection is the
documented upgrade path — see `medium.md`'s "PR-Agent-style per-hunk
line-number injection" escalation entry — since deriving new-file line numbers by
hunk arithmetic is the error-prone step; `AddComment`'s harness-side
anchor validation in `tools.md` is the v1 backstop.)

**Harness guarantees for review mode**: the working tree is checked out
at `Head SHA`, and `<diff>` is exactly `base_sha...head_sha`. This is
load-bearing, not incidental — `reviewer` and `validator` sub-agents
are told to pull in surrounding context with Read/Grep/List, which is
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
  copied into every specialist's `Task` prompt in v1 (see `medium.md`'s
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
run claimed an outcome it never delivered to the ticket. The same
post-run cross-check specifically flags any diff touching a
project-conventions file (`AGENTS.md`/`CLAUDE.md`/equivalent): that
file is instruction to every future run, so a change to it is
prompt-injection surface, not an ordinary edit — the coding prompt
forbids touching it except when the ticket is explicitly about it, and
the flag makes a violation (or a legitimate, ticket-driven change)
visible to whoever reviews the handoff either way. Together with
the first-call checklist gate (`tools.md`), these are the design's
answer to the false-completion-claim failure mode
`agent-self-verification.md` documents as real and measured —
deterministic checks that can't be talked out of firing, not a second
LLM judge (which stays out of v1, per the README's leanness rule).

### 3b. Review mode

```json
{
  "pull_request": "string — the PR reference, in AddComment's target.id format (workspace/repo-slug#123 for Bitbucket, owner/repo#123 for GitHub)",
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
reason. In phase 2's re-review sessions the report additionally
carries a `thread_updates` array — every open Forge thread from the
envelope's `<review_state>`, with what this session did to it
(`replied_fixed` / `replied_conceded` / `replied_standing_firm` /
`left_open`, plus the reply's comment id where one was posted) — the
same accounting discipline extended to threads; see `review.md` §7b. A candidate dropped by the pre-validation dedup (pipeline step
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
   harness per run. For the high-water mark's headroom there's a real
   field convergence to anchor on: of the sources with code-confirmed
   reserved-buffer numbers, Claude Code reserves 13,000 tokens and
   OpenCode 20,000 (twice, in two parallel implementations), with
   Codex's 90%-of-window threshold landing in the same absolute range
   on a large window (`agent-context-compaction.md` §6) — three
   unrelated codebases independently settling on a five-figure token
   buffer. Forge's mark should leave at least that much room, plus
   whatever a worst-case final `Complete` report costs, since the nudge
   turn still has to fit. Crossing either budget doesn't kill the run —
   it triggers
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

---

## 8. Tool result formats

`tools.md` specifies what a tool call looks like going in, and states the
policies every result obeys (text for prose, named fields for facts;
self-describing caps; errors as instructions). This section is the exact
byte-level shape coming back, because "one block per file" is not a
specification — a multi-file, multi-range result has to answer where each
block starts and ends, what happens when file content looks like a block
delimiter, and how a partial failure is reported without discarding the
successes.

These are harness-side formats. They are not in any tool's `description`
field beyond the summaries already in `tools.md`; the model learns them by
seeing them, which is only safe because they are unambiguous by
construction.

Structure here is fixed; the numbers in the examples are not. Every limit
shown (2000 lines, depth 3, 250 matches) is the default from `tools.md`'s
configuration section, rendered from the effective config at runtime — a
deployment tunes the values, never the shapes.

### 8a. Rules common to every tool result

**Payload lines must be distinguishable from structural lines, and the
mechanism differs by payload — deliberately.** Content is never escaped
where escaping would break something; each block type instead carries an
invariant that makes its payload lines unmistakable:

| Block payload | Invariant | Why this one |
|---|---|---|
| File content (`<file>`) | every payload line starts with `<decimal><TAB>` | `Edit` matches file bytes exactly, so the bytes cannot be altered; the prefix is already there for citation and paging, and doubles as the frame |
| Path listings (`<tree>`, `<paths>`) | every payload line starts with at least one space | paths are re-used as tool inputs, so they must survive verbatim; indentation is free and a leading space is not part of any path the harness emits |
| Match lines (`<matches>`) | payload is ripgrep's own `path:line:text`; notes appear only at the end of the block, immediately before the close | inherited format the model already knows, and match text is never byte-matched by another tool, so position is a sufficient separator |
| Command output (`<bash>`) | payload is verbatim **except** that a line equal to the closing delimiter is prefixed with a space | nothing byte-matches command output, so minimally escaping one exact token costs nothing — this is the only place any escaping happens at all |

So, for file content specifically: **every content line is prefixed with
its 1-indexed line number followed by a single tab**, including blank
lines, which appear as a number, a tab, and nothing else. A file
containing `</file>` renders as `73\t</file>` and cannot be confused with
the block close. **No file content is ever escaped, re-encoded, or
quoted** — that is what preserves `Edit`'s byte-exact match contract, and
it is why the delimiter question is settled by the prefix rather than by
inventing a delimiter no file would contain (there is no such delimiter).

Formally, inside a `<file>` block each line matches exactly one of:

```
<digits> TAB <the file's line, verbatim>     a content line
"!" SP <text>                                a harness note
"</file>"                                    the block close
```

**The prefix format is `<decimal><TAB>`, unpadded.** Not right-aligned,
not `N | ` (Cline), not `N: ` (OpenCode). Only the *first* tab on a line
is structural; the file's own tabs follow it untouched. This is the format
`Read`'s and `Edit`'s descriptions both describe, and the two must change
together.

A harness note (`!` at column 0) can only be confused with payload in the
`<bash>` case, where output may legitimately contain such a line. That is
tolerable there and nowhere else: `<bash>` notes appear only after the
final output line and immediately before `</bash>`, and no tool consumes
command output as an exact-match input.

**Attributes carry facts.** Block headers are XML-style tags whose
attributes hold the fact-shaped payload (paths, ranges, totals, statuses,
exit codes). Attribute values are XML-escaped (`&` → `&amp;`, `"` →
`&quot;`, `<` → `&lt;`), which matters only for the rare path containing a
quote. Attribute escaping never touches block *content*.

**Paths are repository-relative** wherever the file is inside the working
tree, and absolute otherwise. The path echoed back is the *resolved* one,
not the string the model passed, so a call that was normalised (a
`file_path` alias, a relative path, a trailing space) shows the model what
was actually read.

**Text is UTF-8, with line endings normalised to `\n`.** A file stored
with CRLF is displayed without the `\r`, and `Edit`/`Write` restore the
file's original ending on the way back out — so the model never has to
emit or match a `\r`. (Gemini CLI does exactly this: it detects the
original file's line ending on write and converts the model's `\n`
content back before saving.) A file that is not valid UTF-8 is reported
with status `not_utf8` and no content, because a lossy rendering would
break `Edit`'s match contract silently.

**Every truncation states what was cut and the exact next call**, per
`tools.md`. Those notes are `!` lines, so they are visible to the model
and unambiguous to a parser.

### 8b. `Read`

```
<files count="4" ok="2" truncated="1" failed="1">
<file path="src/parser/index.ts" lines="1-42" total="42" status="ok">
1	import { Token } from "./lexer"
2	
3	export function parse(tokens: Token[]) {
...
42	}
</file>
<file path="src/parser/lexer.ts" lines="120-180" total="1841" status="ok">
120	  while (pos < src.length) {
...
180	  }
</file>
<file path="src/big-generated.ts" lines="1-2000" total="18422" status="truncated">
1	// AUTO-GENERATED
...
2000	  "z": 1,
! Showed lines 1-2000 of 18422. Pass start_line: 2001 to continue, or narrow with Grep.
</file>
<file path="src/parsr/index.ts" status="not_found">
! No such file. Did you mean src/parser/index.ts?
</file>
</files>
```

Rules:

- **The `<files>` wrapper is always present**, including for a
  single-entry read, so the shape never varies with the call. Its
  attributes are counts only: `count` (entries requested), and however
  many of `ok`/`truncated`/`failed` are non-zero.
- **One `<file>` block per requested entry, in request order**, whatever
  each entry's outcome. The model can always match its Nth request to the
  Nth block. Two entries naming the same path (e.g. two different ranges)
  produce two blocks; an exact duplicate `(path, start_line, end_line)`
  produces one block plus a `!` note saying it was requested twice.
- `lines` is the inclusive range actually returned; `total` is the file's
  full line count. `lines` is omitted when no content is returned.
  Line numbers are the file's own, so a ranged read starts at
  `start_line`, not at 1 — which is what makes a range citable and
  `Edit`-safe without re-reading from the top.
- **`status` vocabulary**: `ok`, `truncated` (a cap applied — the note
  gives the continuation), `empty` (zero-byte or whitespace-only file),
  `past_eof` (`start_line` beyond the file's length; the note gives
  `total`), `not_found` (with a did-you-mean when one is computable),
  `is_directory` (the note says to use `List`), `binary` (with the byte
  size; no content), `not_utf8`, `too_large` (the file exceeds the
  hard byte ceiling even for a ranged read), and `unreadable`
  (permissions or I/O error, with the reason).
- **A failed entry never fails the call.** The tool returns an error only
  when *every* entry failed, and then the error text is the same set of
  `!` notes so nothing is lost.
- Blocks with a non-`ok` status carry `!` notes and no content lines.
- **Batch budget.** Per-entry caps apply first (2000 lines by default,
  or the requested range). If the assembled result would still exceed the
  call's overall size budget, the harness truncates whole entries from the
  end — never the middle of a file — sets their status to `truncated`,
  and adds a `!` note *inside each affected block* plus a summary note
  before `</files>`: `! 2 of 6 files were shortened to fit this call's
  size budget — re-read them individually or with ranges.` Entries are
  never silently dropped: a block exists for every request.
- **Nearby project conventions** discovered for any file in the batch are
  appended once, after `</files>`, inside a single `<system-reminder>`
  block naming which paths they came from — not repeated per file.

### 8c. `List`

Tree mode (the default). The number after each file is its line count;
`-` means binary or unreadable:

```
<tree path="src" depth="2" entries="41" shown="38">
  src/
    parser/
      index.ts        42
      lexer.ts      1841
    util/
      fs.ts          210
      logo.png         -
    legacy/
! 3 entries below depth 2 not shown under src/legacy — pass depth: 3, or path: "src/legacy".
</tree>
```

Paths mode:

```
<paths count="3" sort="mtime" pattern="src/**/*.ts">
  src/parser/lexer.ts
  src/parser/index.ts
  src/util/fs.ts
</paths>
```

Rules:

- **Every entry line begins with at least one space** — two per tree
  level, and two flat in paths mode. That is the invariant from §8a: a
  line starting at column 0 inside these blocks is structure (`!` note or
  closing tag), never a path. It matters because filenames beginning with
  `!` or `<` are legal, and paths from these blocks get fed straight back
  into `Read` and `Grep`.
- Directories carry a trailing `/`. Tree mode sorts directories first,
  then alphabetically; paths mode sorts most-recently-modified first
  (`sort` says which).
- The number after a file in tree mode is its line count; `-` means
  binary, unreadable, or over the size at which counting isn't worth the
  IO. Nothing is counted that wouldn't be readable.
- `entries` is how many exist under the constraints given, `shown` how
  many are printed; when they differ a `!` note says why and what to pass
  (a deeper `depth`, a narrower `path`, an `offset`).
- An empty result is a block with `entries="0"` and a `!` note saying
  nothing matched and what to widen — never an empty block, and never a
  bare "no results".

### 8d. `Grep`

Ripgrep's own output conventions, so the format is already familiar:

```
<matches mode="content" files="2" matches="3" shown="3">
src/parser/index.ts:17:  const tokens = lex(src)
src/parser/index.ts:41:  return parse(tokens)
src/parser/lexer.ts:220:export function lex(src: string) {
</matches>
```

`mode="files_with_matches"` prints one path per line; `mode="count"`
prints `path:count`. In content mode, context lines requested with
`context_before`/`context_after` use `path-line-text` — a hyphen instead
of the second colon, ripgrep's own convention for distinguishing context
from matches — and `--` on its own line separates non-adjacent context
groups, also as ripgrep does. Matched content is printed verbatim on one
line: a match inside a very long line is cut at 2000 characters with a
trailing `[line truncated]` marker rather than wrapped, so the
`path:line:` prefix always starts a line. `shown` versus `matches` drives
the `head_limit`/`offset` continuation note.

The `path:line:text` form is ripgrep's, inherited rather than invented,
and it inherits ripgrep's one ambiguity too: a path containing a colon
makes the split positional rather than exact. This is accepted — the same
tradeoff every `grep`-shaped tool in the field makes — because match lines
are read, not parsed, and because the alternative (quoting paths) would
diverge from the format the model already knows. For the same reason,
harness notes in this block are placed only at the end, immediately
before `</matches>`, rather than relying on `!` being distinguishable
from a path that starts with `!`.

### 8e. `Bash`

```
<bash exit="1" duration_ms="4210" truncated="false">
$ npm test -- parser

FAIL src/parser/index.test.ts
  ● parse() handles empty input
    Expected: []
    Received: undefined
</bash>
```

Rules:

- **stdout and stderr are interleaved in the order the process wrote
  them**, as a terminal would show, because causality between the two is
  what makes test and build output readable. A command that needs them
  separated redirects explicitly. `exit` is always present and is the
  only thing that decides success — output on stderr with `exit="0"` is a
  success.
- The command is echoed as the first line, prefixed `$ `, so the block is
  self-describing when re-read later out of context.
- Output is verbatim, with exactly one exception, and it is the only
  escaping anywhere in these formats: **a line whose entire content is
  `</bash>` is emitted with a leading space.** Command output can contain
  anything, including this design's own delimiters, and unlike file
  content it is never byte-matched by another tool — so a one-token,
  one-space escape is free here where it would be unacceptable in a
  `<file>` block. Harness notes (`! …`) appear only after the last output
  line, immediately before the close; a line of output that happens to
  start with `!` is therefore ambiguous only in position, not in
  consequence.
- When output exceeds the cap, the head and tail are kept and the middle
  is elided with a `! … N lines elided …` note (never the head or tail,
  per `tools.md`'s edge rule), `truncated="true"` is set, and a `log`
  attribute carries the scratch-directory path holding the full output.
- Background commands return immediately with `exit` absent, a
  `pid` attribute, and the `log` path — the mechanism `tools.md`'s Bash
  description already describes.

### 8f. Errors

A tool that fails entirely returns an error result whose text is a `!`
note in the same voice: what happened, what to do, and a suggestion when
one is computable. It carries no partial content. The exception is
`Read`, whose per-entry failures are reported in-band (§8b) precisely so
that one bad path doesn't discard three good files.
