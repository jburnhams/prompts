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
new task sources, new tools, new envelope tags, harness-side
mechanics, or (§5) a whole additional entrypoint — the existing mode
rules, completion gates, and structural tool scoping all carry
forward unchanged unless an item says otherwise explicitly.

A shared principle worth stating once rather than per item: every new
tool that returns external content (`FetchBuild`, `SearchJira`,
`WebFetch`, `SearchSource`/`ReadSource` results) routes through the
same in-code sanitizer the envelope and `FetchJira` already use
(`formats.md` §1), with the source-code exception `formats.md` §1
already carves out (don't mangle source bytes) — a CI log or a
fetched web page is exactly as untrusted as a ticket comment,
arriving through yet another door. And every new *capability* on an unsupervised path gets
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

### 2e. `SearchSource` / `ReadSource` (ref-pinned source beyond the working tree)

**What**: read-only search and file retrieval over source that is
*not* in the working tree — another repository at an exact ref, or
(phase 2) a dependency of the current build. `SearchSource` speaks
Grep's ripgrep dialect over HTTP; `ReadSource` is Read's contract
against the same scopes. Both are read-only by construction, with
deliberately no Edit counterpart — a change Forge wants made to code
it can search but doesn't own goes through §4a, never through an
edit.

**Why**: the recurring failure this addresses is an agent that wants
to read the source of something it calls — a library class, a
sibling service's API — and either can't find it at all or burns half
its budget cloning and spelunking. The collection has no precedent
for search beyond the workspace: its entire search ladder
(`agent-tool-surfaces.md` §2, plain grep → semantic → LSP-backed) is
local-only, and the closest in-collection analog for symbol-granular
retrieval is Composio's `CODE_ANALYSIS_TOOL_GET_CLASS_INFO`/
`GET_METHOD_BODY` structured-lookup toolkit. The industry precedent
(Sourcegraph-style code-search services) sits outside the collection
entirely. That absence is the opportunity — this is the single
biggest capability gap between what agents keep trying to do and
what any surveyed tool surface gives them.

**Design sketch**:

```json
{
  "name": "SearchSource",
  "input_schema": {
    "type": "object",
    "properties": {
      "scope": { "type": "string", "description": "What to search: \"repo:workspace/repo-slug@ref\" (branch, tag, or commit hash — the result always reports the hash the ref resolved to, so findings are pinned), or \"artifact:group:name\" / \"class:com.example.Foo\" for a dependency of the current working tree." },
      "pattern": { "type": "string", "description": "Ripgrep-syntax regex — the same dialect Grep uses." },
      "glob": { "type": "string" },
      "output_mode": { "type": "string", "enum": ["content", "files_with_matches"] },
      "head_limit": { "type": "integer" }
    },
    "required": ["scope", "pattern"],
    "additionalProperties": false
  }
}
```

`ReadSource` takes the same `scope` plus `path`/`offset`/`limit`.

Phased on purpose, matching how the need actually arrives:

- **Phase 1 — `repo:` scopes.** Search/read another repository at a
  branch, tag, or commit. The backing service (a code-search indexer,
  or the platform's own search API fronted by the harness) is
  infrastructure the tool schema deliberately knows nothing about —
  the same harness-owns-the-mapping pattern `AddComment` uses for
  platforms.
- **Phase 2 — `artifact:`/`class:` scopes.** The harness resolves a
  dependency coordinate to source: build manifest → exact pinned
  version → source jar or repo+tag. The resolution rule that matters:
  **the version comes from the working tree's own build manifest,
  never from the model's guess** — the lockfile/POM already knows
  exactly what's on the classpath, so "read the source of the thing
  I'm actually calling" is deterministic. This resolver (coordinate →
  version → source location → owning project) is shared machinery
  with §4a's dependency-change proposals — build it once.

**Gotchas**:

- Tool-description ordering guidance: local Grep/Read first, always —
  `SearchSource` is for code that *isn't* in the tree, not a
  second way to search code that is.
- Real source only in phase 2's first cut: if no source jar exists,
  say so rather than silently decompiling — decompiled line numbers
  and shapes lie. A clearly-labeled decompiler fallback is a possible
  later addition, not a default.
- Third-party source is untrusted content read into context; same
  accepted-residual-risk stance as repo files (`future.md`'s
  display-layer sanitization entry covers the eventual fix), worth
  restating here because dependency source is authored even further
  from the deployment's trust boundary.
- Coding mode only (both `mode` values — a plan run tracing a bug
  into a dependency is exactly what plan mode is for), plus the
  product-owner entrypoint (§5), where it's the primary code view.
  Review sub-agents stay Read/Grep/Glob-local; widening their reach
  needs finding-level evidence first, same bar as their Bash
  escalation entry (§6).

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

## 4. Cross-repo escalation and long-horizon waiting

V1 is bounded in two dimensions on purpose: one repository (the
checked-out working tree) and one sitting (a run starts, terminates,
done). The three items here extend each boundary deliberately rather
than letting it erode by accident — Forge gains a way to *ask* for
changes to code it doesn't own (never a way to make them), and a way
to park work on events that take longer than a run should live.

### 4a. Dependency-change proposals (`ProposeDependencyChange`)

**What**: when the real fix for a ticket belongs in a dependency —
a library bug, a missing API, a sibling service's contract — Forge
can propose a change to the owning team by filing a Jira in *their*
project. The tool takes a dependency coordinate and a requirement;
the harness resolves ownership and creates (or queues) the ticket.

```json
{
  "name": "ProposeDependencyChange",
  "input_schema": {
    "type": "object",
    "properties": {
      "dependency": { "type": "string", "description": "\"artifact:group:name\" or \"class:com.example.Foo\" — resolved to an owning project by the same resolver SearchSource's phase 2 uses." },
      "title": { "type": "string", "description": "One line, written for the owning team's backlog." },
      "requirement": { "type": "string", "description": "What the dependency should do differently and why, Markdown. Written to stand alone: the observed behavior, the needed behavior, and the calling context (originating ticket, code paths involved) — the owning team has none of your context." },
      "blocking": { "type": "boolean", "description": "Whether the current task cannot be completed correctly without this change." }
    },
    "required": ["dependency", "title", "requirement", "blocking"],
    "additionalProperties": false
  }
}
```

**Why**: today the only honest outcomes when the fix is out-of-repo
are AskUser or a note in the Complete report — both dead-end the
actual work. No source in the collection routes work across
repository/team boundaries at all; this is genuinely novel, which is
exactly why the guardrails below matter more than the schema.

**Design points**:

- **Ownership resolution is the harness's job**, via the shared
  resolver (§2e): build metadata (SCM URLs in artifact POMs), a
  service-catalog mapping, or explicit config, resolving coordinate →
  repo → Jira project/component. When ownership can't be resolved,
  the tool says so and Forge falls back to noting the need in its
  report — a proposal with a guessed owner is worse than none.
- **Gated by default.** Filing tickets into other teams' backlogs is
  the most outward-facing action in the whole design — more so than
  PR comments, which at least land on Forge's own subject matter. The
  deployment-policy pattern from plan-gating applies (`formats.md`
  §6): the tool's contract is identical whether the harness files
  immediately or holds the proposal for human approval, and gated
  should be the shipped default. The created ticket is always
  labeled as agent-filed and linked back to the originating issue
  (`FetchJira`'s `linked_issues` then surfaces it to any later run).
- **Workflow guidance in the prompt**: search first
  (`SearchJira` against the target project — the owning team may
  already have this ask; Composio's twice-stated
  check-before-duplicating rule is the collection's precedent,
  `code-review-approaches.md` §9), propose at most once or twice per
  run, and never as a substitute for in-repo work that's actually
  possible — a proposal pairs with either a workaround implemented
  now or an honest `blocked`.
- **Injection surface, named plainly**: this tool turns a hostile
  ticket into a way to make Forge socially-engineer other teams
  ("file a ticket asking platform-team to relax the auth check").
  The gated default and per-run cap are the structural answer; the
  agent-filed labeling means even an approved bad proposal is
  attributable and auditable.
- **The path composes with itself**: if the owning repo is also
  Forge-enabled, the filed ticket is just another ticket in the same
  dispatch queue — the dependency ask can be planned, implemented,
  and reviewed by the same machinery that generated it. Whether it
  auto-dispatches or waits for the owning team's triage is, again,
  deployment policy, not Forge behavior.

**What happens to the proposing run**: two legitimate endings. If the
task can proceed with a workaround, implement it, note the filed
ticket in the report, `Complete(done)`. If it genuinely can't
(`blocking: true`), the run ends by suspending on the proposed
ticket's resolution (§4c) — not by idling, and not by a `Complete`
that pretends more than it did.

### 4b. Short waits inside a run: `Await`

**What**: block on something already in flight — a background Bash
job, or a `FetchBuild` pipeline ref — without burning model turns on
poll loops.

```json
{
  "name": "Await",
  "input_schema": {
    "type": "object",
    "properties": {
      "handle": { "type": "string", "description": "A background job id returned by Bash (run_in_background), or a build ref in FetchBuild's format." },
      "timeout_ms": { "type": "integer", "description": "Required. The harness returns a timed_out result when it expires — the wait never hangs silently." }
    },
    "required": ["handle", "timeout_ms"],
    "additionalProperties": false
  }
}
```

**Why and precedent**: v1's answer to "wait for the test suite" is
shell polling through the persistent session — workable, but each
poll is a model turn spent on nothing. A harness-side blocking wait
is the field's converged answer, in several shapes: Codex CLI's
`wait_agent` with timeout ("returns empty status when timed out"),
Grok Build's `wait_commands_or_subagents` with `wait_any`/`wait_all`
across a shared task-id space, Copilot CLI's `read_agent` with
`wait: true` (`agent-tool-surfaces.md` §6,
`agent-subagent-architectures.md` §4). Single-handle first;
Grok's multi-handle any/all is the documented extension if fan-out
waiting shows up.

**Gotchas**:

- **Run bounding gains a third budget.** Turn and context budgets
  can't see idle time — a run blocked in `Await` consumes neither. A
  wall-clock budget joins them (`formats.md` §7's mechanism,
  triggering the same final-turn nudge), because a hung wait must
  still end in an honest `Complete`, and an idle run is not free:
  it holds its sandbox and its spent context the whole time.
- **Minutes, not hours.** `Await` is for waits where losing the run's
  context would cost more than holding it — a test suite, a lint of
  the working tree, a build already running. Anything on a human or
  cross-team timescale is §4c's job, and the tool description should
  draw that line explicitly.

### 4c. Long waits across runs: generalized task suspension

**What**: the AskUser suspend/resume protocol (`formats.md` §5),
with the wake condition generalized. V1's protocol is already "end
the run, record a suspended-task, resume when an external event
lands" — the event just happens to be a human reply. An `AwaitEvent`
terminal tool opens that to the other events worth parking on:

- `jira`: an issue (e.g. a §4a proposal) reaches a status, or its
  fix version is released
- `build`: a pipeline concludes
- `pr`: a PR merges or closes
- `timer`: a point in time — the degenerate predicate, for
  poll-based conditions with no webhook and for plain
  check-back-later (Grok Build's `scheduler_create` is the
  collection's one recurring/scheduled-prompt precedent,
  `agent-tool-surfaces.md` §10)

Suspension mechanics carry over from `formats.md` §5 unchanged: no
`Complete` (suspension is a distinct terminal state, not a variant of
completion), the harness records the envelope + transcript + wake
condition, and the resumed run gets a `<resumed_event>` tag carrying
what happened, with the same transcript-inheritance and
budget-headroom caveats that section already documents. `AskUser` stays its own
tool — the question/options shape is user-facing and worth keeping —
but internally it becomes one wake predicate among several, which is
a simplification, not new machinery.

**The design stance that keeps this small — prefer being woken over
waiting.** Most "wait for X" needs are already served *inverted* by
the trigger architecture: a failed build dispatches a `ci_failure`
run (§1a), a review comment dispatches a responder run (§1c) — no
task sits suspended at all, and a fresh run with a fresh budget picks
up the event. `AwaitEvent` is specifically for when *this* task's
accumulated context must survive to the other side of the event —
"my dependency ask shipped, now finish the integration I already
half-understand." When a fresh run could do the follow-up just as
well, the right design is a trigger, not a suspension; the prompt
guidance should say so, or every long task will end in a lazy
suspend.

`future.md`'s suspension-cycle cap applies here with more force than
it did to AskUser alone — a task that can sleep on a timer can sleep
forever, so a deployment wants a cap on total suspensions and a
maximum park duration, after which the task fails honestly back to a
human ("the dependency never shipped" is a report, not a permanent
sleep). And the standing PR-steward loop (`future.md`) is this
mechanism plus §1's triggers under one policy — these primitives are
its prerequisite, which is part of why they're medium-tier.

---

## 5. A third entrypoint: product-owner mode

The first item in this roadmap that adds an *entrypoint* rather than
extending one — a parallel track that runs through every planning
horizon rather than a single feature. Everything above extends what
the coding and review orchestrators can reach; this adds a third
orchestrator whose deliverable is **tracker artifacts, not code**:
requirements, epics broken into stories and tasks, estimates and
complexity assessments, and a groomed backlog. Same model, same core
tool discipline, a third system prompt.

The distinction from `mode: plan`, stated crisply because they will
be confused: plan mode answers *"how would I implement this ticket"*
— its output is an implementation design for one existing issue. PO
mode answers *"what tickets should exist"* — its output is the
issues themselves, written well enough that plan/implement runs (and
humans) can consume them. They compose rather than overlap: a
PO-authored story with crisp acceptance criteria is exactly what the
coding entrypoint wants as input and what the `ticket_compliance`
lens (§3a) reviews against. This track sits upstream of the entire
existing pipeline, which is what makes it a flywheel: better tickets
in, better implementation and review out.

**Precedent honesty**: the collection is nearly empty here. BMAD is
the only source with real story/sprint machinery — spec/story files
with acceptance criteria gating a review layer, sprint-status
tracking, checklist items written into story files
(`code-review-approaches.md` §§1, 4, 7) — and it's human-mediated
throughout. Nothing surveyed authors backlog structure autonomously.
That means this section leans on Forge's own established patterns
(gated outward writes, suspension, structural tool scoping) more
than on field precedent, and should be built expecting to learn.

### 5a. The entrypoint

**Input**: a PO task envelope — a goal or raw requirement
(free text or a rough epic), or a grooming brief (a board/JQL scope
plus what "groomed" means for this team). **Output**: created/updated
issues and a Complete report accounting for them.

**Workflows** (one prompt, task-shaped like coding mode's two modes):

- **Break down**: fetch the epic/requirement and everything it
  references (`FetchJira`/`SearchJira`, `SearchDocs`/`FetchDoc` —
  §5d, `SearchSource` for code reality); run a question round with
  the humans who own the ambiguity (§5c); draft the hierarchy —
  stories with acceptance criteria, tasks with scope, dependency
  links; post the draft for approval; create on approval (§5b).
- **Groom**: sweep the scoped backlog for duplicates
  (`SearchJira` + the dedup discipline the review pipeline already
  has), stale issues, missing acceptance criteria, stories too big to
  implement in one run; propose merges/splits/rewrites/closures —
  every one gated, none silent.
- **Estimate**: complexity and story points *grounded in code
  evidence* — which components and repos a story actually touches
  (`SearchSource` blast-radius reconnaissance), stated as rationale
  on the issue, not bare numbers. This is the capability nothing in
  the field has: an estimating agent that reads the code before
  sizing the story. Calibration against historical outcomes is
  future-tier (`future.md`).

**Tool surface** (structural, per the availability-table pattern in
`tools.md`): `FetchJira`, `SearchJira`, `SearchDocs`/`FetchDoc`,
`SearchSource`/`ReadSource`, `Task` (`general-purpose`, for
open-ended research), `AskUser`, `WriteJira` (§5b), `Complete`. **No
`Edit`, `Write`, or `Bash` — not wired at all.** PO mode never
touches code or a shell; it may not even have a working tree checked
out (`SearchSource` is its code view, which is why §2e lists it as a
consumer). Read/Grep/Glob are wired only when the envelope names a
primary repo worth having locally.

**Archetype stance**: still hands-off, deliberately. "More
interactive" is real — grooming means many small human decisions —
but the interaction model stays ask-suspend-resume, just cheaper and
more channel-appropriate (§5c), with batched questions (one
suspension carrying several questions beats four suspensions). A
genuinely synchronous conversational PO surface is a different
archetype with different communication rules
(`agent-archetypes.md`'s axis 1) and is tracked in `future.md`, not
smuggled in here.

### 5b. Tracker writes: `WriteJira`

The PO deliverable requires the one capability v1 deliberately
withheld everywhere else: writing to the tracker. The design holds
because the withholding was never absolute — it was "no tool without
a legitimate caller in that mode." PO mode is the legitimate caller.

- One tool, verb-scoped: create an issue (type, project, summary,
  description, acceptance criteria, estimate fields, labels), update
  those same fields on an existing issue, link issues
  (epic-child, blocks, duplicates). **No transitions and no
  deletions** — moving issues through workflow states and removing
  them stay human/harness-owned; a wrongly-created issue is flagged
  in the report, not deleted by the agent.
- **Wired in PO mode only.** Coding and review modes keep their
  v1 surfaces — same structural-gates reasoning as every other
  mode-scoped tool, and `ProposeDependencyChange` (§4a) remains the
  only tracker-write path from a coding run, with its own gating.
- **Gated by default, like §4a**: the draft hierarchy posts for
  human approval before `WriteJira` fires; a deployment can loosen
  this per workflow (grooming *proposals* might auto-post as
  comments while *closures* always gate). All created/updated issues
  are agent-labeled.
- **Integrity cross-check — the tracker is this mode's working
  tree.** The exact symmetry of the coding-mode `git status`
  cross-check (`formats.md` §3a): after a PO run, the harness
  fetches the issues the report claims were created/updated and
  attaches any mismatch — a claimed-but-missing issue, an
  unreported write — to the report it hands downstream. The
  false-completion-claim defense carries over to a new substrate
  unchanged.

### 5c. Multi-channel `AskUser` delivery

V1 routes every AskUser through a Jira comment. The PO track makes
that visibly wrong — the person who owns a requirements ambiguity
lives in chat (Symphony/Teams), email, or a review UI, not
necessarily on the ticket — but the fix is a harness-side
generalization, not a new tool, and every mode benefits.

- The suspension protocol (`formats.md` §5) is already
  channel-agnostic in structure: post question → record
  suspended-task keyed to a conversation reference → resume on
  reply. Only step 2's delivery is Jira-specific. Generalize the
  key from "comment id" to "channel + conversation reference"
  (a chat thread id, an email message id, a UI inbox item), with
  reply-matching per channel: chat webhooks, email reply-to
  threading, UI events.
- The harness owns an **addressee registry** per task — reporter,
  team channel, PO — from envelope config, the same way
  `<comment_target>` already routes manual-task communication.
  `AskUser` optionally gains one field: an `audience` hint (*who is
  best placed to answer* — "the reporter", "the team owning
  service X"), which the harness maps to a channel and address;
  Forge never sees addresses or channel mechanics.
- Whatever channel carries the question, the *audit trail* stays on
  the ticket: the harness mirrors question and answer back to the
  originating issue as a comment, so a decision made in a chat
  thread isn't invisible to the next run (or the next human) reading
  the ticket. One channel is the conversation; Jira is the record.

### 5d. Documentation sources: `SearchDocs` / `FetchDoc`

Confluence first, schema platform-agnostic — the `AddComment`
pattern applied to reading documentation. `SearchDocs(query, space?)`
returns compact hits (title, ref, excerpt); `FetchDoc(doc_ref)`
returns a page as Markdown, sanitized like every other fetched
content (`formats.md` §1 — a Confluence page is a ticket comment
with better formatting: same injection posture, data-not-instruction
rule included).

Deliberately listed under the PO section but **wired wherever
reading matters**: coding mode (the design doc a ticket links is
context plan mode should read, and today can't), review mode
*optionally* for the `conventions`/`ticket_compliance` lenses (an
ADR space is a conventions file that outgrew the repo — but wire it
to the orchestrator's context-gathering step, not the specialists,
to keep their scopes narrow), and PO mode as a primary input.
In-collection precedent is thin — PR-Agent's org-standards injection
and BMAD's frontmatter-referenced docs are the nearest shapes
(`code-review-approaches.md` §4); the abstraction cost is low
because the tools are read-only and the harness owns the source
mapping, same as everything else in this design.

---

## 6. Escalation triggers (v1 ships simple; upgrade only on evidence)

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
