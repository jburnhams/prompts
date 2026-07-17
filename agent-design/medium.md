# Medium-term roadmap

The concrete next tier after v1: upgrades with a named need or an
already-visible evidence trigger, sketched in enough detail to
implement against without re-deriving the design conversation. The
line between this file and `future.md` is horizon and certainty —
everything here is either demanded by the deployment context (CI,
deeper Jira, the loop-closing run sources) or is a documented
escalation path v1 deliberately shipped the simple version of.
`future.md` holds the long-horizon and measurement-gated ideas.

Nothing in this file changes v1's contracts. Every item is additive:
new task sources, new tools, new envelope tags, or harness-side
mechanics — the existing mode rules, completion gates, and structural
tool scoping all carry forward unchanged unless an item says otherwise
explicitly.

A shared principle worth stating once rather than per item: every new
tool that returns external content (`FetchBuild`, `SearchJira`,
`WebFetch`) routes through the same in-code sanitizer the envelope and
`FetchJira` already use (`formats.md` §1) — a CI log or a fetched web
page is exactly as untrusted as a ticket comment, arriving through yet
another door. And every new *capability* on an unsupervised path gets
the same structural-gates treatment as v1: wired only in the run
sources/modes that have a workflow step using it, never "available but
unused."

---

## 1. New task sources: closing the loop

V1 has two entrypoints and two coding-mode sources (`jira`, `manual`).
These three additions are all new values of the existing
`<source>` mechanism plus new envelope tags — the same pattern
`<plan>` already uses for the plan → implement handoff
(`formats.md` §6). None of them is a new mode or a new system prompt.

### 1a. CI-failure fix runs (`source: ci_failure`)

**What**: a failed pipeline on a branch Forge owns (or is asked to
babysit) dispatches a `mode: implement` run whose envelope carries a
`<build_failure>` tag: pipeline/build id, the failed step's name, an
excerpt of its log (truncated and sanitized), and the commit the run
failed at. The working tree is checked out at that commit's branch,
same as any other implement run.

**Why**: this is the second half of "hands-off" — v1 delivers a
working tree and stops, but the first contact with real CI is where
unattended changes actually break. The trigger mechanism is
harness-side (webhook or poll on pipeline events), the same machinery
the AskUser resume protocol already requires (`formats.md` §5).

**Design sketch**:

```
<task>
  <mode>implement</mode>
  <source>ci_failure</source>
  <issue_key>PROJ-1234</issue_key>       <!-- when known: the ticket the branch belongs to -->
  <repository>workspace/repo-slug</repository>
  <target_branch>proj-1234-short-slug</target_branch>
</task>

<build_failure>
  Pipeline: {{ id / URL }}
  Commit: {{ sha }}
  Failed step: {{ name }}
  <log_excerpt>
    {{ tail of the failed step's log, harness-truncated, sanitized }}
  </log_excerpt>
</build_failure>
```

Workflow fit: the coding prompt's step 2 ("reproduce, if there's a
bug") maps directly — the reproduction is re-running the failing
step's command locally, and the fix isn't done until it passes. The
`FetchBuild` tool (§2a) lets the run pull more of the log than the
excerpt if it needs to.

**Gotchas to build in from day one**:

- **A retry cap, harness-side.** A flaky test or an infrastructure
  failure must not produce an infinite fix-run loop. Cap fix attempts
  per branch per failure (two or three; Copilot Chat's Grok-family
  prompt's "iterate up to three targeted fixes" is the field's stated
  number — `agent-self-verification.md` §1), then stop dispatching and
  surface the failure to a human. The cap lives in the dispatcher, not
  the prompt — a prompt can't see across runs.
- **"The fix is not mine to make" is a valid outcome.** The prompt
  guidance for this source should say explicitly: if the failure is
  not caused by the branch's own changes (broken main, infra flake,
  an expired credential), report that via `Complete(status:
  "blocked")` with the diagnosis rather than contorting the branch to
  paper over it. This mirrors the existing "don't fix pre-existing
  issues" review rule, applied to CI.

### 1b. Review → implement handoff (`<findings>` envelope tag)

**What**: a review run's confirmed findings can dispatch a follow-up
`mode: implement` run on the PR's branch, whose envelope carries a
`<findings>` tag holding the review run's posted findings verbatim
(the review-finding schema, `formats.md` §4). The implement run
treats findings the way it treats a `<plan>`: the primary guide to
what to do and where, verified rather than blindly trusted.

**Why**: v1's two entrypoints never feed each other; this is the
highest-leverage connection between them, and it reuses the
plan → implement handoff mechanism wholesale — same envelope-tag
pattern, same "gated or auto-chained is a deployment policy, not a
Forge behavior" stance (`formats.md` §6, README's gating-policy
decision row).

**Design sketch**: the dispatch policy question is identical in shape
to plan-gating and should be answered the same way — the harness
decides whether a fix run fires automatically, only for findings above
a severity threshold, or only after a human reacts to the comment.
Two Forge-side contracts are new:

- The fix run's Complete report maps each finding `id` to an outcome
  (`fixed` / `skipped`, with a reason) — the same
  nothing-silently-disappears accounting the review report already
  does for candidates (`formats.md` §3b).
- The fix run replies on each addressed finding's comment thread —
  this is the one place the responder machinery (§1c) and this item
  share plumbing: `AddComment` wired for threaded replies, scoped to
  the threads named in the envelope.

**Gotcha**: a fix run must not expand scope — it addresses the listed
findings on the existing branch and nothing else. That's a prompt rule
for this source, and the existing post-run `git status` cross-check
already makes violations visible.

### 1c. PR-comment-responder runs (`source: pr_comments`)

**What**: unresolved review comments (human or bot) on a PR branch
Forge owns dispatch a `mode: implement` run whose envelope carries the
PR context block and the unresolved comment threads (with comment ids,
same shape as review mode's `<existing_comments>`). The run makes the
requested changes in the working tree and replies on each thread —
what it did, or why it disagrees. `AddComment` is wired in this
source's implement runs, scoped by prompt to threaded replies on the
envelope's threads: replying is the deliverable here, which is exactly
the "legitimate caller" test v1's AddComment-in-implement decision row
says a re-wiring needs.

**Why**: without this, every human review comment on a Forge PR needs
a human to act on it, which un-does most of the hands-off value.
Precedent: `claude-code-cookbook`'s `pr-fix` exists entirely to
consume review comments (`code-review-approaches.md` §9);
`claude-code-action`'s tag mode is the same loop triggered by
@-mention.

**Gotchas — this source deliberately relaxes a v1 boundary, so name
it**: v1's injection posture is "the ticket defines what to build;
comments don't get to redefine how you operate." A responder run makes
PR comments the task *by design*, which is why the harness must gate
*which* comments can dispatch a run — restrict to comments from
repository members / a configured reviewer list, never drive-by
comments from arbitrary accounts. The prompt keeps the second layer:
comments define what to change in the code, and anything in them
aimed at Forge's rules rather than the code (mode changes, safety
waivers, "ignore previous instructions") is still data to flag, not
obey. Ambiguous or contradictory reviewer asks route to `AskUser`,
which this source inherits unchanged.

---

## 2. New tools

### 2a. `FetchBuild` (read-only CI)

**What**: fetch a pipeline run's status and logs. Read-only by
construction — no trigger/re-run/cancel verbs at all (active CI
control is a `future.md` item with a genuinely different permission
surface).

```json
{
  "name": "FetchBuild",
  "input_schema": {
    "type": "object",
    "properties": {
      "build_ref": { "type": "string", "description": "A pipeline/build id or URL, or \"latest\" for the newest run on this task's target branch." },
      "step": { "type": "string", "description": "Optional: a specific step name to fetch the log for. Omit for the run's step list and statuses only." },
      "log_lines": { "type": "integer", "description": "Optional: how many lines from the end of the step's log to return. Defaults to a harness-set cap." }
    },
    "required": ["build_ref"],
    "additionalProperties": false
  }
}
```

Output: run status, per-step name/status/duration, and (when `step` is
set) the log tail — truncated, sanitized. Wired in coding mode (both
`mode` values — a plan run diagnosing a build failure is legitimate);
not wired in review mode in this tier (a reviewer judging the diff by
CI outcome is a different, deliberate feature — note it as an option,
don't drift into it).

CI-system-agnostic on purpose: Bitbucket Pipelines is the primary
target, but the schema names nothing Pipelines-specific — `build_ref`
and step names are universal, and the harness owns the mapping, the
same way `AddComment` owns platform mapping.

### 2b. `SearchJira` (read-only JQL)

**What**: search issues by JQL, returning a capped list of compact
results (key, title, type, status — `FetchJira`'s summary fields, not
full issues). Read-only; no issue creation, transition, or edit —
ticket state changes stay harness-owned, same reasoning as git writes.

**Why**: `FetchJira` can only fetch what something else already named.
Real tickets constantly reference work by description rather than key
("the login bug from last sprint", "duplicate of the timeout issue"),
and a plan run checking for prior art or related tickets is exactly
the investigation that mode exists for. Precedent: PR-Agent is the
one review source that pulls linked-tracker context and treats it as
a first-class review input (`code-review-approaches.md` §4).

```json
{
  "name": "SearchJira",
  "input_schema": {
    "type": "object",
    "properties": {
      "jql": { "type": "string", "description": "The JQL query." },
      "max_results": { "type": "integer", "description": "Cap on results returned. Defaults to a small harness-set number." }
    },
    "required": ["jql"],
    "additionalProperties": false
  }
}
```

Results are sanitized like every other Jira-sourced content. Wired
where `FetchJira` is wired (coding mode only), for the same reason.

### 2c. `MultiEdit`

**What**: several `Edit`-shaped replacements against one file in one
atomic call — all apply or none do. Precedent: Claude Code's
`Edit`+`MultiEdit` and Copilot Chat's
`ReplaceString`+`MultiReplaceString` are the two primary+batch pairs
in the collection (`agent-tool-surfaces.md` §8).

**Why now rather than v1**: pure ergonomics/token savings on
many-small-changes files; nothing about correctness depends on it.
It's the cheapest tool addition in this file — the schema is `Edit`'s
schema wrapped in an array, and the uniqueness contract is unchanged
per element (each `old_string` must be unique against the file state
its edit sees, in order).

### 2d. `WebFetch` and `WebSearch`

**What**: plain URL fetch (returning readable text, not raw HTML) and
general web search, as two tools — the split Claude Code, Windsurf,
and the richer Cursor capture all converge on
(`agent-tool-surfaces.md` §4).

**Why**: "implement a Jira ticket" regularly needs a library's
current documentation — an API renamed since training, a migration
guide, an error message worth searching. V1 called these
non-load-bearing; that's true for the benchmark shape but not for
day-to-day tickets against moving dependencies.

**Constraints**:

- Availability is a deployment/network-policy decision — many CI-side
  sandboxes are network-isolated, and the tools simply aren't wired
  there (dynamic tool-surface rendering, `agent-tool-surfaces.md`
  §10: the prompt must not describe a tool that isn't wired).
- Fetched content is the most arbitrary untrusted input in the whole
  surface: sanitized like everything else, and covered by the same
  "data, not instruction" rule the envelope states for tickets and
  comments.
- Coding mode only. Review mode's job is judging a diff against the
  repo and its conventions; giving its sub-agents a reason to leave
  the repo mid-review is scope drift and injection surface with no
  workflow step behind it.

---

## 3. Review pipeline upgrades

### 3a. Ticket context in review mode, and a `ticket_compliance` lens

**What**: the review envelope optionally carries the PR's linked Jira
issue (`<ticket>`, same pre-fetched shape as coding mode's), located
by the harness from the branch name/PR title convention. When present,
a fourth specialist lens becomes available: `ticket_compliance` —
does the diff actually do what the ticket asked, are the acceptance
criteria met, is anything in the AC silently unaddressed. Skipped
entirely when no ticket is linked, exactly like the `conventions`
lens with no conventions file.

**Why**: this is the review-side payoff of being an Atlassian-stack
agent — the ticket is *right there*. Precedent: PR-Agent's `/review`
takes a ticket (title, requirements, DoD) as first-class compliance
input, and BMAD gates a whole "Acceptance Auditor" layer on the
spec/story file (`code-review-approaches.md` §4). No Claude-Code-skill
source does this — it's a genuine differentiator.

**Gotcha**: the validator's "is it caused by this diff" question
doesn't fit compliance findings ("AC #3 not addressed" has no line to
anchor). Compliance findings need their own validation framing —
"does the envelope's ticket actually require this, and does the diff
actually not do it" — and post as general PR comments, not inline
anchors. Small prompt fork, worth doing properly rather than forcing
the bugs-shaped schema onto it.

### 3b. Diff-as-file (promoted from deferred)

**What**: the harness writes the diff to a scratch-dir file as well as
(or eventually instead of) inlining it per specialist; specialists get
the changed-file list, their role, and the diff path, and `Read` the
slices they need. Removes the `(1 + lenses)` duplication multiplier
from the large-diff threshold math (`formats.md` §1b) — which the
fan-out of this file's new lenses (§3a, §3c) makes strictly worse,
hence the promotion from `future.md`.

**Measure, don't assume**: the stated cost is specialists starting
cold on what to read. Run it both ways on a sample of real PRs and
compare finding recall before switching the default. The orchestrator
keeps the inlined diff either way — its skip/dispatch decisions and
specialist-brief construction need it.

### 3c. Double coverage on the bugs lens

**What**: run two `bugs` specialists in parallel and let the existing
dedup + validator machinery absorb the overlap — Anthropic's own
`/code-review` skill does exactly this for recall
(`code-review-approaches.md` §5). Cheap because the consequence of
duplication (two candidates, one location) is already handled by
pipeline steps 4-5. Turn on when finding-outcome telemetry (§3e)
shows recall is the binding problem; the knob costs one line in the
orchestrator's step 3.

### 3d. Per-role model selection

**What**: run different roles on different models — the natural first
split is a cheaper model for specialists and the strongest available
for the validator (the asymmetry the pipeline's own design implies:
a missed specialist finding is silent, a wrong validator confirmation
becomes a posted comment). Precedent is strong and specific:
Anthropic's `/code-review` assigns Haiku/Sonnet/Opus by role, Amp
pins `oracle` to a different vendor entirely, GitHub Copilot CLI pins
per-sub-agent models in YAML with one deliberately inheriting the
user's live choice (`agent-subagent-architectures.md` §3).

Mechanically this is harness config (model per `subagent_type`/role),
zero prompt changes — which is what makes it medium-tier: the work is
choosing and measuring, not building.

### 3e. Finding-outcome telemetry

**What**: the harness records what happens to every posted finding —
resolved, replied-to, fixed by a follow-up commit touching the
anchored lines, or left to rot — and every filtered candidate. No
agent-side changes at all.

**Why this is the load-bearing item of this section**: several
deferred decisions are explicitly gated on measurement that doesn't
exist yet — numeric confidence scoring "once false-positive rate is
actually measured" (`future.md`), double bugs coverage "if recall
measures low" (§3c), per-role models "once cost per review run is
measured" (§3d), diff-as-file "worth measuring before adopting"
(§3b). Without this item, every one of those stays permanently
blocked on data nobody is collecting. TuringMind's "Filtered Issues"
transparency section is the only in-collection precedent for even
surfacing the filtered set (`code-review-approaches.md` §6); v1's
`filtered` report field already captures the agent side — this closes
the loop with the platform side.

---

## 4. Escalation triggers (v1 ships simple; upgrade only on evidence)

Moved from the original single-file roadmap, unchanged in substance:
each of these is a case where v1 deliberately shipped the simple
mechanism, with a named, more expensive upgrade to reach for only if
the simple version measurably falls short.

- **PR-Agent-style per-hunk line-number injection**, if mis-anchored
  review comments show up in practice. V1 bakes a plain unified diff
  and validates anchors after the fact, degrading a bad anchor to a
  visible `file:line`-prefixed general comment rather than silently
  mis-posting (`formats.md` §1b). PR-Agent's custom
  `__new hunk__`/`__old hunk__` format with injected line numbers
  (`code-review-approaches.md` §3) removes the hunk-arithmetic step
  that causes mis-anchoring, at the cost of a less lean diff format.
- **General command-level `Bash` permission filtering**, beyond the
  narrow git-write blocklist v1 ships (`tools.md`). Filtering
  arbitrary commands correctly (compound commands, subshells,
  `xargs`, script files) is a real permission engine — OpenCode's
  tree-sitter AST parsing and Gemini CLI's per-sub-command redirection
  detection are the field's benchmarks
  (`agent-permissions-approval.md` §2-3), and both are whole
  subsystems. The natural first slice of `future.md`'s tiered
  permission subsystem, scoped to one tool.
- **Read-only-git `Bash` for `reviewer`/`validator` sub-agents**, if
  pre-existing-vs-introduced misjudgments show up in posted findings.
  V1 gives review sub-agents no `Bash` at all, so a validator's only
  view of pre-change code is the diff's `-` lines and context; the
  validator prompt trades recall for safety by rejecting when that's
  insufficient. The upgrade (agent37/TuringMind's read-only-git
  allowlist shape, `code-review-approaches.md` §10) depends on the
  command-level filtering entry above existing first — without it,
  "read-only git only" would be prompt-enforced, exactly what the
  structural-gates principle rejects.
- **Batched review delivery**, if per-finding notification noise draws
  complaints. On GitHub the mechanism is the native pending-review
  flow (create → add comments → submit once, event type locked to
  `COMMENT` — `gemini-code-review`'s shape,
  `code-review-approaches.md` §9), which also gives an API-layer place
  to hard-lock "never APPROVE/REQUEST_CHANGES." Bitbucket has no
  pending-review equivalent — comments post as they're created — so
  the Bitbucket version of this upgrade is different: batch
  harness-side and post rapidly in sequence, and/or lead with a single
  summary comment linking the inline findings. Either way it's a
  change to how the harness flushes `AddComment` calls, not to the
  tool surface Forge sees — but the two platforms genuinely diverge
  here, the one place the peer-platform abstraction leaks.
- **Structural write protection for the project-conventions file**, if
  the post-run flag on conventions-file diffs (`formats.md` §3a) ever
  actually fires on a non-conventions ticket. The upgrade is Roo
  Code's `RooProtectedController` shape
  (`agent-permissions-approval.md` §3): the harness rejects
  `Edit`/`Write` calls targeting the conventions path unless the run
  was dispatched with an explicit this-ticket-may-edit-conventions
  flag. Deferred because the flag already makes the failure visible
  rather than silent.
