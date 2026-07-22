# Review context and query structure

The single authority for **what reaches the model in review mode, at
every stage** — the review envelope's construction (especially the
diff), the exact payload each specialist and validator sub-agent
receives, the comment-thread model, and how repeat reviews of the same
PR are structured: state, incremental diffs, replies on existing
threads, and code changes made in response to comments.

`formats.md` §1b defines the envelope's tag skeleton and defers to this
document for the interior of `<diff>` and `<existing_comments>` and for
everything session-related. `system-prompts.md` §2 defines the pipeline
that consumes all of this. Worked, end-to-end examples of every payload
in this document live in `examples/` — read them alongside this file;
each section below names its example.

A note on phasing, because it shapes the whole document: the run-shape
here is split into **v1** (single-session review: everything through §5,
plus §7's race policy) and **phase 2** (stateful re-review sessions: §6
and §8, tracked as `medium.md` §3f). The split is in *machinery*, not in
wire format — every phase-2 addition is an additive tag or field on the
v1 shapes, so the v1 formats are stable from day one and nothing
breaks when the session machinery arrives. That's deliberate: the
payload structure is the hardest thing to change after launch (every
stored transcript, every prompt tuned against it), so it gets nailed
first even where the consuming behavior ships later.

---

## 1. The context ladder: what's inline, what's fetched

Two camps exist in this repo's research (`code-review-approaches.md`
§3): pre-format the diff and hand it over (PR-Agent, Codex-review,
Gemini's extension), or let the model run `git diff`/`gh` itself (every
Claude-Code-skill-style source). This design is already committed to the
first camp for the diff (README decision log: line-number accuracy
matters when comments post unsupervised). This section states the full
ladder — for each kind of context, *why* it sits where it sits:

| Context | Delivery | Why there |
|---|---|---|
| PR metadata, description, changed-file list | Inline, envelope | Needed by every run, tiny, and the harness has it anyway from the webhook/API call that triggered the run |
| The diff | Inline, envelope, pre-built by the harness (§2) | Line-number fidelity is the whole game: a posted comment's anchor derives from these hunks, and no human filters a mis-anchored comment before it lands. Also removes a whole class of failure where the model runs the *wrong* diff command (wrong base, no rename detection) and reviews the wrong delta |
| Existing comments and threads (§3) | Inline, envelope; transcluded into specialist/validator briefs (§4–5) | The dedup step (pipeline step 4) and re-review reconciliation (§6) need the complete set, and finders/validators need it as intent context — the record of what humans asked for, without which a specialist can end up proposing the revert of a requested change (§3); "fetch if you think you need it" is exactly how a run silently duplicates a comment |
| Project-conventions files | Path known to orchestrator; contents read in step 2 and transcluded into the `conventions` specialist's brief | Only one specialist needs the text; repo-controlled, so lower injection risk than PR content |
| Surrounding code beyond hunks | **Not inline** — Read/Grep/Glob against the working tree at Head SHA | See below |
| Linked ticket | Phase 2+, inline when present (`medium.md` §3a) | Compliance lens only |

The "surrounding lines vs. lookup tools" question is answered **both,
with different jobs**:

- The diff's five context lines per hunk side (§2) are for **finding** —
  enough locality to spot a suspicious change and understand the shape
  of the edit without a tool call. Five lines is where the field
  independently converged (Codex-review's `--unified=5`, Gemini's
  `-U5`), and going wider inline pays the token cost on every hunk of
  every file for context most hunks never need.
- The working tree at Head SHA is for **verifying** — the harness
  guarantees the checkout matches the diff (`formats.md` §1b), so
  Read/Grep/Glob are ground truth for anything beyond the hunk:
  enclosing function, callers, the definition of a symbol the hunk
  uses, whether a claimed-missing guard exists three lines past the
  context window.

The rule that connects them, already present in the specialist prompt
(`system-prompts.md` §4) and load-bearing enough to restate as the
principle: **a finding may not rest on assumed code outside the hunk.**
Either the specialist read the surrounding code and the finding cites
what it read, or the finding isn't raised. BMAD is the precedent for
making this mandatory rather than optional (`code-review-approaches.md`
§6 — the only source *requiring* surrounding-code reading before
severity is assigned); PR-Agent's system prompt shows the failure mode
its absence causes, having to warn the model against "questioning code
elements that may be defined elsewhere in the codebase" precisely
because its model has no tools to go look.

---

## 2. Diff construction algorithm

The harness builds `<diff>` — Forge never runs `git diff` in review
mode (review roles have no Bash at all, `tools.md`). The exact
procedure:

1. **Base is the merge-base, not the base branch tip.** Record
   `base_sha = merge-base(base_branch_tip, head_sha)` and diff
   `base_sha..head_sha` (equivalently: three-dot `base...head`). If the
   base branch has moved since the PR branched, a two-dot diff against
   its tip charges the PR with reverting every unrelated commit that
   landed on main since — the review would flag code the author never
   touched. Every source in the collection that states its base is on
   the merge-base side: Gemini's `git diff -U5 --merge-base`, Devin's
   PR-viewing instruction (`git diff --merge-base`), and the leaked
   Claude Code bundled review skill's explicit "three-dot, so the
   comparison is against the merge-base". The `<pull_request>` block's
   `Base SHA` field carries this merge-base, so the recorded pair
   always reproduces the exact diff reviewed.
2. **Flags**: `git diff -U5 -M --no-color --no-ext-diff
   <base_sha> <head_sha>`. `-U5` per the convergence above. `-M`
   (rename detection) so a moved-and-tweaked file renders as a rename
   header plus small hunks instead of a full delete-file/add-file pair —
   without it, a rename reads as hundreds of lines of "new" code, which
   both burns the size budget and invites specialists to re-review
   unchanged code. `--no-ext-diff` so a repo's local diff driver can't
   alter what the model sees.
3. **File order** matches `<changed_files>` (git's own path order), all
   of one file's hunks contiguous. The two blocks are views of the same
   set — a file in one is always in the other.
4. **Elisions — visible, never silent.** Three cases where hunk bodies
   are withheld, all rendered the same way (the file's `diff --git` /
   `---` / `+++` header retained, hunks replaced by one bracketed line):
   - *Generated/vendored/lock files*, matched by a harness-configured
     glob list (sane defaults: lockfiles, `*.min.*`, `dist/`,
     vendored dirs, generated protobuf/openapi output):
     `[hunks elided: 4,812 changed lines, matched generated-file
     pattern "package-lock.json"]`
   - *Binary files*: git's own `Binary files ... differ` line stands
     as-is.
   - *Per-file cap*: a single file whose hunks exceed a configured line
     count gets `[hunks elided: exceeds per-file limit of N lines]` —
     so one enormous mechanical refactor can't starve every other file
     in the PR out of the run-level size gate. The run-level gate
     (`formats.md` §1b) then applies to the post-elision total.
   Every elided file is also marked `[elided]` at the end of its
   `<changed_files>` line, so a specialist knows the change exists
   without seeing it and doesn't misread absence as "file untouched".
   Elided files are reviewable only in the weak sense that their names
   and stats are visible; if one looks load-bearing (a hand-edited file
   matching a generated-file glob), that's a finding about the PR
   ("generated file edited by hand?"), not something to reconstruct
   via Read.
5. **Whitespace changes are kept** (no `-w`): whitespace is semantic in
   enough of the target languages (Python, YAML, Makefiles) that
   hiding it hides real bugs.
6. **Submodule bumps** render as git's standard one-line subproject
   change and are never expanded.

Line-number convention, restated once here because every downstream
schema inherits it: findings, anchors, and thread positions all use
**new-file (post-change) line numbers at Head SHA**. The diff is plain
unified format in v1 — no injected line numbers; specialists confirm
numbers by Reading the file, per §1's rule, and PR-Agent's per-hunk
line-number injection stays the documented upgrade if mis-anchoring
shows up in practice (`medium.md` escalation entry).

Worked example: `examples/review-envelope-initial.md`.

---

## 3. The comment-thread model

The interior of `<existing_comments>` (the tag name and envelope
position are unchanged from `formats.md` §1b). The earlier draft's flat
comment list made replies invisible — a reply was just another line, so
"what was the last word on this thread, and from whom" (which both
dedup and everything in §6/§8 turns on) had to be re-derived from
timestamps and guesswork. Threads are now explicit:

```
<existing_comments>
  <general>
    [{{comment_id}} | {{author}} at {{timestamp}}]: {{body}}
    [{{comment_id}} | Review by {{author}} at {{timestamp}} | {{state}}]: {{body}}
  </general>
  <thread id="{{thread_id}}" anchor="{{path}}:{{line}}" status="open|resolved|outdated">
    [{{comment_id}} | {{author}} at {{timestamp}}]: {{body}}
    [{{comment_id}} | reply | {{author}} at {{timestamp}}]: {{body}}
  </thread>
</existing_comments>
```

- `<general>` holds top-level PR comments and formal review bodies
  (approvals, change requests), chronological. The `[id | author at
  timestamp]` line convention is `claude-code-action`'s formatter
  shape, kept as-is; a formal review's verdict rides in the same line
  (`| APPROVED`, `| CHANGES_REQUESTED`) rather than a separate block.
- One `<thread>` per inline discussion: root comment first, replies in
  order, each marked `reply`. `anchor` is the thread's file/line in
  new-file terms. `status` is the platform's own state, mapped by the
  harness: Bitbucket threads are natively resolvable; on GitHub,
  `resolved` maps from review-thread resolution and `outdated` from
  the platform marking the anchored code as changed since. Forge's
  logic never branches per platform — the harness normalizes into this
  one shape, the same contract the envelope already applies to formal
  reviews.
- **Trimming**: `open` threads are carried verbatim. `resolved` and
  `outdated` threads carry the root comment (truncated at ~500
  characters with a visible `[truncated]` marker) and `[{{n}} replies
  elided]` in place of their replies — enough to know what was raised
  and settled there, without spending tokens on the settlement
  conversation. Dedup (pipeline step 4) considers open threads only;
  an issue raised and *resolved* at a location does not immunize that
  location, because resolution usually means the code changed and a
  new candidate there is describing new code.
- Everything inside this tag is untrusted external content: the
  harness's code-level sanitizer (`formats.md` §1) has already run on
  every body, and the review prompt's data-not-instruction rule applies
  to all of it.

Who consumes this block: **every review context, as data.** The
orchestrator uses it for dedup (pipeline step 4) and reconciliation
(§6); specialists and the validator receive it transcluded verbatim in
their briefs (§4, §5) as intent context — the record of why the code
is the way it is. An earlier draft kept specialists and the validator
blind to it on an injection-surface argument; that was reversed for a
concrete failure the blindness causes: a reviewer asks for X→Y, the
author complies, and a blind specialist — seeing only Y, with no trace
of the request — flags Y and proposes the revert, producing a
validator-confirmed comment that argues with a human's explicit
decision directly under the thread where they made it. Nothing else in
the pipeline can catch that: dedup drops candidates that *duplicate* a
thread, and this candidate *contradicts* one. The injection exposure
this trades away is real but bounded — bodies are code-sanitized
(`formats.md` §1), every prompt carries the data-not-instruction rule,
a finding must still be verified against the code, and on the primary
deployment (an internal Atlassian stack) comment authors are
authenticated colleagues, not drive-by accounts. §4's discussion rules
are the behavioral layer that keeps context from becoming instruction.

---

## 4. The specialist brief — exact payload

`system-prompts.md` §2 step 3 says what each specialist gets; this is
the wire shape of the `Task` call's `prompt`, assembled by the
orchestrator by **verbatim transclusion** of envelope blocks:

```
<pr>
{{ the envelope's <pull_request> block, verbatim }}
</pr>

<description>
{{ the envelope's <description> contents, verbatim }}
</description>

<diff>
{{ the envelope's <diff> contents, verbatim — the whole diff, not a
   slice; "diff-as-file" (medium.md §3b) is the tracked change to this }}
</diff>

<conventions file="{{path}}">
{{ contents of one project-conventions file scoped to the changed
   paths — conventions role only; one tag per file }}
</conventions>

<existing_comments>
{{ the envelope's <existing_comments> block, verbatim — §3's trimming
   already applied by the harness. Omitted entirely when the PR has no
   comments, which makes a comment-free first review identical either
   way }}
</existing_comments>

<focus>
{{ optional, orchestrator-authored: at most a few sentences directing
   attention — e.g. "the description claims a pure refactor; flag any
   behavior change" — never a summary or restatement of the diff }}
</focus>

<scope>
{{ phase 2, re-review sessions only — see §6: names the
   incremental-diff base SHA and restricts findings to code changed
   since it }}
</scope>
```

The specialist's *instructions* (what to flag, what not to flag,
output schema) live in its system prompt (`system-prompts.md` §4) and
are not repeated per brief.

Four rules with teeth:

1. **Transclusion is verbatim, always.** The orchestrator never
   paraphrases, summarizes, or trims the diff for a specialist. A
   rewritten diff re-introduces exactly the line-number laundering the
   pre-baked diff exists to prevent — one model's paraphrase becoming
   another model's ground truth is how an anchor ends up on the wrong
   line with nobody able to say where the number came from. The only
   permitted orchestrator-authored content is `<focus>`, and its job
   is direction, not data.
2. **Discussion is context — never verdicts, never a skip list.**
   Three sub-rules, carried in the specialist prompt
   (`system-prompts.md` §4):
   - A thread never suppresses a candidate. Raise it even where the
     discussion already covers that code — dedup is the orchestrator's
     job (pipeline step 4), and the report's
     nothing-silently-disappears accounting only works if candidates
     are raised and then visibly dropped, not silently unraised.
   - A thread's claim is a lead, not evidence. "This looks buggy" in a
     comment justifies a look; only the code showing the defect
     justifies a finding.
   - Contradicting an explicit human decision raises the bar. When a
     thread shows a reviewer asked for the very behavior in question,
     the request *explains* the code — re-proposing what it replaced
     on taste is a misstep. Flag it only for a concrete defect the
     discussion doesn't already address, and the finding's rationale
     must name the thread and engage the request ("requested in
     t-301; as implemented it also …") so the eventual comment reads
     as joining the conversation, not ignoring it. A human-requested
     change that genuinely introduces a bug is still flagged — the
     request changes the framing, never the verdict.
3. **What's deliberately absent.** Other specialists' output — lens
   independence is the point of having lenses — and anything not in
   the envelope: a brief is transcluded envelope blocks plus
   `<focus>`, nothing else.
4. **The description and the discussion are inside the brief but
   still untrusted.** Both are needed for intent — the author's
   stated intent in `<description>`, the reviewers' decisions in the
   threads — and both are arbitrary people's text: the harness
   sanitizer has already run on them, and the specialist prompt's
   data-not-instruction rule covers them. This is a knowing expansion
   of untrusted-text exposure at the finding stage, accepted because
   these reviews are collaborative: a finder that can't see what
   humans asked for will eventually argue with them (§3's reversal
   note), which costs more trust than the injection risk it avoided —
   and on comment-free PRs the two designs are identical anyway.

Worked example: `examples/specialist-brief-bugs.md`.

---

## 5. The validator brief — exact payload

One `Task(subagent_type: "validator")` call per surviving candidate
(pipeline step 5), `prompt` assembled the same way:

```
<candidate_finding>
{{ the finding, as JSON per formats.md §4, exactly as the specialist
   returned it (id assigned, validated: null) }}
</candidate_finding>

<pr>
{{ envelope <pull_request> block, verbatim }}
</pr>

<description>
{{ envelope <description>, verbatim }}
</description>

<diff>
{{ envelope <diff>, verbatim — the full diff, not just the finding's
   file: the validator's "is this pre-existing" question is answered
   by the diff's own old-side lines, and its "is this handled
   elsewhere" question routinely crosses file boundaries }}
</diff>

<existing_comments>
{{ envelope block, verbatim, when the PR has any — the discussion can
   already explain or authorize the behavior a finding targets
   (a reviewer requested it, a tradeoff was settled), which bears
   directly on the validator's "would a senior engineer flag this"
   question. The social counterpart of the in-code lint suppression
   its prompt already covers }}
</existing_comments>
```

What the validator deliberately does *not* get: the specialist's
reasoning beyond what the finding schema itself carries
(`rationale` is part of the finding; any additional chain-of-thought
is not) and the other candidates. Independence is the
mechanism — the validator re-derives the claim against the code
(Read/Grep/Glob at Head SHA) rather than auditing the specialist's
argument for persuasiveness. The discussion doesn't weaken that:
threads inform the *worth-flagging* judgment, while the *is-it-true*
judgment stays code-only — a comment asserting the code is fine is
weighed like a comment asserting it's broken, which is to say not at
all until the tree agrees. This mirrors the structure Anthropic's
`/code-review` uses (a fresh sub-agent per candidate, given the issue
description and the PR context, not the finder's transcript) and is
why the validator prompt (`system-prompts.md` §5) tells it "you did
not raise this finding."

**Phase 2 adds one variant**: the *resolution check*, dispatched by
re-review reconciliation (§6) — same payload shape plus the finding's
`<thread>` (from `<existing_comments>`) and the `<incremental_diff>`,
with the question inverted: not "is this finding real" but "did the
changes since {{sha}} actually fix this previously-confirmed issue."
Same binary-verdict discipline, same reject-when-unsure default —
except here "reject" means *don't declare it fixed*, which fails safe
in the same direction (no comment posted claiming a fix that didn't
happen).

Worked example: `examples/validator-brief.md`.

---

## 6. Re-review sessions: state, the interdiff, and thread reconciliation *(phase 2 — `medium.md` §3f)*

V1 already handles a re-run on a previously-reviewed PR correctly but
statelessly: review everything, dedup against open threads (README
decision log, "Review dedup identity"). That's the right floor — it
never spams — but it leaves the three things a *returning* reviewer
actually does undone: focus on what changed since last time, notice
that a previous finding got fixed and say so, and answer people who
replied. Sessions add those. A **session** is one review run; the
harness persists per-PR state between sessions — which it can build
entirely from artifacts it already holds (each session's Complete
report plus the comment ids/URLs AddComment returned), no new
agent-side machinery.

### 6a. Envelope additions

Two additive tags, appended after `<existing_comments>`; a first
review simply omits both, which is exactly the v1 envelope:

```
<review_state rebased="false">
  <previous_session at="{{timestamp}}" head_sha="{{sha}}">
    <posted_finding id="{{finding_id}}" thread="{{thread_id}}"
        file="{{path}}" line="{{n}}" severity="{{severity}}"
        status="open|resolved|outdated">
      {{ the finding's summary sentence }}
    </posted_finding>
  </previous_session>
</review_state>

<incremental_diff base="{{last_reviewed_head_sha}}">
{{ unified diff, last_reviewed_head_sha..head_sha, built by the exact
   §2 algorithm — same flags, same elision rules }}
</incremental_diff>
```

- `<review_state>` lists every prior session (most recent last), each
  with the findings it posted and their *current* thread status —
  `status` is live platform state at snapshot time, not what it was
  when posted. The `thread` attribute joins a finding to its
  `<thread>` in `<existing_comments>`, where any replies live: the
  state tag says *what Forge said and where*, the thread says *what
  happened next*.
- `<incremental_diff>` (the interdiff) is what changed since the last
  session. **Force-push/rebase caveat**: if `last_reviewed_head_sha`
  is no longer an ancestor of the new head, the interdiff would be
  garbage (it would diff across the rewrite, blaming the rebase for
  everything). The harness detects this, omits `<incremental_diff>`
  entirely, and sets `rebased="true"` — the session then runs
  full-scope like a first review, with dedup and reconciliation still
  doing their work. Never fabricate an interdiff across a rewrite.

### 6b. Pipeline deltas

Against the numbered pipeline in `system-prompts.md` §2 — same steps,
three changes:

- **Step 1 (warranted?)** gains a session-aware skip: an empty
  interdiff *and* no new replies on any Forge thread means nothing
  happened since last session → `Complete(skipped)`.
- **Step 3 (specialists)** — each brief carries the **full diff plus a
  `<scope>` tag**, not the interdiff alone:

  ```
  <scope>
  This PR was previously reviewed at {{last_reviewed_head_sha}}. Only
  the changes since then are in scope for new findings: the file/line
  ranges appearing in <incremental_diff> below. The full PR diff above
  is context — use it to understand the change, but do not raise a
  finding whose lines lie entirely outside the incremental ranges.
  </scope>
  <incremental_diff base="{{sha}}">…</incremental_diff>
  ```

  Why both diffs: the interdiff alone loses the surrounding change
  (a three-line fix commit is unreviewable without the feature it
  patches), while the full diff alone re-reviews everything and
  re-generates round-one findings for the dedup step to re-kill —
  wasteful and, worse, noisy whenever dedup's similarity judgment
  wobbles. Scoped-full-context is what the two stateful precedents
  converge on: security-guidance tracks prior-review state and
  instructs "only flag something in the delta", and PR-Agent's
  incremental `/review -i` reviews only the commits since its last
  review. On a `rebased="true"` session, `<scope>` is omitted and
  specialists run full-scope.
- **Step 3½ (reconciliation)** — new, orchestrator-driven, dispatched
  in the same turn as the specialists since neither depends on the
  other. For each **open, Forge-authored** thread in `<review_state>`
  (`status="open"`, joined to its thread), exactly one of:

  1. **Anchored code changed in the interdiff** → dispatch a
     resolution check (§5's variant). Confirmed fixed → reply on the
     thread (brief: what the new code does that resolves it, 1–2
     sentences) and resolve it. Not confirmed fixed → if the author
     also replied, fall through to (2); otherwise leave the thread
     open and silent — the next session will look again. Do not post
     "still not fixed" on an unanswered thread; that's a nag, not a
     review.
  2. **Author replied, code unchanged (or changed but not fixed)** →
     judge the reply on its content. If it's right — the finding
     misread the code, the behavior is intentional and now
     explained, a suppression or test covers it — concede: reply
     acknowledging (one sentence), resolve the thread, and record the
     finding as withdrawn in the report. If the finding still stands,
     reply **once** restating the concrete failure scenario the
     validator confirmed — specific inputs, specific wrong outcome —
     and stop. **At most one standing-firm reply per thread, ever,
     across all sessions.** If the author replies again without the
     code changing, the thread is left for humans; the disagreement is
     now above a bot's pay grade, and a bot that argues in rounds
     torches exactly the trust the validator pass exists to protect.
     A factual dispute ("that guard does exist, line 88") gets a
     resolution-check dispatch before conceding or standing firm — the
     answer should come from the tree, not from who sounds confident.
  3. **Nothing happened on the thread** → do nothing. Open threads are
     allowed to just sit; silence is not a state that needs a comment.

  Reconciliation replies inherit PR-Agent's comment-voice rules
  (already in the specialist/orchestrator prompts): matter-of-fact, no
  filler, no "thanks for the fix!" boilerplate.
- **Step 4 (dedup)** — unchanged criterion, one more input: candidates
  are also checked against `<review_state>`'s open findings (belt and
  braces — those findings' threads are already in
  `<existing_comments>`, but the state tag's structured form makes the
  match cheap and exact).
- **Step 7 (report)** — the Complete report (`formats.md` §3b) gains a
  `thread_updates` array: every open Forge thread from the state tag,
  with what happened to it this session (`replied_fixed` /
  `replied_conceded` / `replied_standing_firm` / `left_open`, plus the
  reply comment id where one was posted). Same
  nothing-silently-disappears accounting the findings list already
  has, extended to threads.

### 6c. Tool addition

Reconciliation needs "reply and resolve" as one action. `AddComment`
gains one phase-2 field:

```json
"resolve_thread": { "type": "boolean", "description": "After posting, resolve the thread this reply lands on. Requires in_reply_to. Where the platform has no thread resolution, the harness notes that in the tool result and the reply still posts — degrade visibly, never silently." }
```

Schema-enforced to require `in_reply_to` (an `allOf`/`if`/`then` pair,
the same device the tool already uses for `suggestion`), wired in
review sessions only. V1's schema is unchanged until then.

Worked example: `examples/review-envelope-rereview.md`.

---

## 7. Mid-run races: the snapshot contract

The envelope is a **snapshot**: comments and diff as of dispatch time,
with the snapshot instant recorded as a `Snapshot:` line in
`<pull_request>`. Two things can move under a running session, and the
design's answers are deliberately asymmetric:

- **A comment lands mid-run.** Accepted race, no machinery. Worst case
  is a benign near-duplicate (a human flags something in the minutes a
  session takes, and the session posts the same finding), which the
  next session's dedup/reconciliation absorbs. The alternative —
  re-snapshotting the comment set at deliver time and re-running a
  fuzzy dedup inside the harness — puts an LLM-shaped similarity
  judgment into harness code, the one place it can't be reviewed or
  validated. Not worth it for a rare, self-healing case.
- **The head moves mid-run (new push).** Detected structurally: every
  `AddComment` call against a PR compares the PR's current head with
  the envelope's `Head SHA`. On mismatch the comment **still posts** —
  it's anchored to the reviewed commit, which is exactly what a human
  reviewer's in-flight comments do when an author pushes mid-review,
  and the platform marks it outdated if the anchored code changed —
  but the tool result carries `head_moved: true`. The orchestrator
  finishes the session normally (its findings are true *of the commit
  it reviewed*) and records the supersession in its Complete summary;
  it never chases the new head mid-run. Dispatching the follow-up
  session against the new head is the harness's trigger policy, not
  the agent's decision.
- **Serialization.** At most one review session per PR runs at a time;
  pushes and comments arriving during a session coalesce (debounce)
  into at most one queued follow-up session. Harness-side, but stated
  here because §6's state model assumes it: "the previous session"
  is only well-defined if sessions don't interleave.

---

## 8. Code changes in response to comments — the boundary

Review mode replies to threads; it never edits code
(`system-prompts.md` §2's constraints). Making the change a reviewer
asked for is the **coding entrypoint's** job, via the two roadmap run
sources that already exist for it, and this section exists to pin the
seam between them:

- A human (or Forge-review) comment asking for a change on a
  Forge-owned PR dispatches a **responder run** (`medium.md` §1c):
  `mode: implement` on the PR branch, envelope carrying the PR block
  and the open threads **in §3's exact thread shape** — one format for
  threads everywhere, so nothing translates. The run edits the working
  tree and replies on each thread via `AddComment` (`in_reply_to`),
  which is wired in that run source precisely because replying is the
  deliverable there. Worked example:
  `examples/responder-envelope.md`.
- A review session's own confirmed findings can dispatch a **fix run**
  (`medium.md` §1b) the same way, with `<findings>` instead of
  comment threads as the drive.

The loop then closes without any new machinery: the responder/fix run
pushes nothing itself (its tree is committed/pushed by the external
process, as everywhere in this design), the new commits move the PR's
head, the harness queues a review session, and that session's
reconciliation (§6b step 3½) sees Forge-authored replies on its own
threads plus the fix in the interdiff — confirming, resolving, and
reporting `thread_updates` exactly as if a human had made the fix. The
two entrypoints never share a run; they meet only through the platform
state (threads, commits) and the envelope formats defined here.

One rule worth stating because both sides touch it: **thread etiquette
is owned by whichever run replies.** A responder run's reply says what
it changed (or why it disagrees, once — the same one-round cap as
§6b's standing-firm rule, for the same reason); a review session's
reply says what it verified. Neither posts progress narration,
"working on it" placeholders, or a second reply where one already
covers it.

---

## 9. Phasing summary

| Capability | v1 | Phase 2 (`medium.md` §3f) | Later (tracked) |
|---|---|---|---|
| Diff | §2 algorithm: merge-base, `-U5 -M`, visible elisions | unchanged | Per-hunk line-number injection; diff-as-file (`medium.md` §3b) |
| Comment context | §3 threaded model, full set inline; transcluded into every brief as intent context under §4's discussion rules | unchanged | — |
| Specialist/validator briefs | §4/§5 verbatim-transclusion payloads | + `<scope>`/`<incremental_diff>`; resolution-check variant | Ticket-compliance lens brief (`medium.md` §3a) |
| Repeat review | Full re-review + dedup against open threads | Sessions: `<review_state>`, interdiff scoping, reconciliation, `thread_updates` | Finding-outcome telemetry (`medium.md` §3e) feeding thresholds |
| Replies | None (review posts new findings only) | Reconciliation replies + `resolve_thread`; one-round standing-firm cap | — |
| Comment-driven code changes | None | Responder/fix runs (`medium.md` §1b/§1c) consuming §3's thread shape | — |
| Races | §7 snapshot contract, `head_moved`, serialization | unchanged | — |

Everything phase 2 adds is an additive tag (`<review_state>`,
`<incremental_diff>`, `<scope>`), an additive field (`resolve_thread`,
`thread_updates`), or a new run source — no v1 shape changes meaning.
That is the property the whole document is built to protect: the query
structure holds still while the behavior around it grows.
