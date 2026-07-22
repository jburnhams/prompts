# Review context and query structure

The single authority for **what reaches the model in review mode, at
every stage** — the review envelope's construction (especially the
diff), the exact payload each specialist and validator sub-agent
receives, the comment-thread model (including threads anchored to
earlier versions of the PR), the two run shapes (single-stage and
multi-stage), and how repeat reviews of the same PR are structured:
state, incremental diffs, replies on existing threads, and code
changes made in response to comments.

`formats.md` §1b defines the envelope's tag skeleton and defers to this
document for the interior of `<diff>` and `<existing_comments>` and for
everything session-related. `system-prompts.md` §2 defines the
pipelines that consume all of this. Worked, end-to-end examples of
every payload in this document live in `examples/` — read them
alongside this file; each section below names its example.

A note on phasing, because it shapes the whole document: the run-shape
here is split into **v1** (single-session review: §1–§5, either §6 run
shape, §8's race policy, and the `at_sha` staleness marker on threads)
and **phase 2** (stateful re-review sessions §7, §3a's stale-thread
context blocks with §3b's conditional format notes, and §9's responder
seam — tracked as `medium.md` §3f and §1b/§1c). The split is in
*machinery*, not in wire format — every phase-2 addition is an
additive tag or field on the v1 shapes, so the v1 formats are stable
from day one and nothing breaks when the session machinery arrives.
That's deliberate: the payload structure is the hardest thing to
change after launch (every stored transcript, every prompt tuned
against it), so it gets nailed first even where the consuming behavior
ships later.

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
| Existing comments and threads (§3) | Inline, envelope; transcluded into specialist/validator briefs (§4–5), including, for stale threads, the then/now code blocks (§3a) | The dedup step (pipeline step 4) and re-review reconciliation (§7) need the complete set, and finders/validators need it as intent context — the record of what humans asked for, without which a specialist can end up proposing the revert of a requested change (§3); "fetch if you think you need it" is exactly how a run silently duplicates a comment |
| Project-conventions files | Path known to orchestrator; contents read in step 2 and transcluded into the `conventions` specialist's brief (or held in hand by a single-stage finder) | Only the conventions lens needs the text; repo-controlled, so lower injection risk than PR content |
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

The rule that connects them, carried in the shared reviewer core
(`system-prompts.md` §4) and load-bearing enough to restate as the
principle: **a finding may not rest on assumed code outside the hunk.**
Either the finder read the surrounding code and the finding cites
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
   both burns the size budget and invites finders to re-review
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
   `<changed_files>` line, so a finder knows the change exists
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

Every other diff this document defines — the interdiff (§7a) and a
stale thread's `<changed_since>` block (§3a) — is built by this same
procedure over a different SHA pair, so there is exactly one diff
dialect anywhere in the system.

Line-number convention, restated once here because every downstream
schema inherits it: findings, anchors, and thread positions all use
**new-file (post-change) line numbers at Head SHA** — except inside a
stale thread, whose numbers belong to its own `at_sha` (§3a states
this precisely). The diff is plain unified format in v1 — no injected
line numbers; finders confirm numbers by Reading the file, per §1's
rule, and PR-Agent's per-hunk line-number injection stays the
documented upgrade if mis-anchoring shows up in practice (`medium.md`
escalation entry).

Worked example: `examples/review-envelope-initial.md`.

---

## 3. The comment-thread model

The interior of `<existing_comments>` (the tag name and envelope
position are unchanged from `formats.md` §1b). The earlier draft's flat
comment list made replies invisible — a reply was just another line, so
"what was the last word on this thread, and from whom" (which both
dedup and everything in §7/§9 turns on) had to be re-derived from
timestamps and guesswork. Threads are explicit, and a thread whose
anchored code has moved since it was written carries its own history
(§3a):

```
<existing_comments>
  <general>
    [{{comment_id}} | {{author}} at {{timestamp}}]: {{body}}
    [{{comment_id}} | Review by {{author}} at {{timestamp}} | {{state}}]: {{body}}
  </general>

  <thread id="{{thread_id}}" anchor="{{path}}:{{line}}" status="open|resolved">
    [{{comment_id}} | {{author}} at {{timestamp}}]: {{body}}
    [{{comment_id}} | reply | {{author}} at {{timestamp}}]: {{body}}
  </thread>

  <thread id="{{thread_id}}" anchor="{{path}}:{{line}}" at_sha="{{sha}}" status="open|resolved">
    [{{comment_id}} | {{author}} at {{timestamp}} @ {{sha}}]: {{body}}
    [{{comment_id}} | reply | {{author}} at {{timestamp}} @ {{sha}}]: {{body}}
    <code_then sha="{{sha}}">
    {{ the PR-diff hunk the root comment was anchored on, as of sha }}
    </code_then>
    <changed_since from="{{sha}}" to="{{head_sha}}">
    {{ diff hunks overlapping the anchored region, sha → head — §2's
       construction, restricted }}
    </changed_since>
  </thread>
</existing_comments>
```

- `<general>` holds top-level PR comments and formal review bodies
  (approvals, change requests), chronological. The `[id | author at
  timestamp]` line convention is `claude-code-action`'s formatter
  shape, kept as-is; a formal review's verdict rides in the same line
  (`| APPROVED`, `| CHANGES_REQUESTED`) rather than a separate block.
- One `<thread>` per inline discussion: root comment first, replies in
  order, each marked `reply`.
- **`status` is the conversation's state only**: `open` or `resolved`,
  mapped by the harness from the platform's native resolution
  (Bitbucket threads are natively resolvable; GitHub review threads
  via thread resolution). Whether the *anchored code* has changed
  since the thread was written is a separate, orthogonal fact —
  staleness — carried structurally by `at_sha` and the §3a blocks,
  never by `status`. GitHub's "outdated" flag maps to staleness, not
  to closure: a thread can be stale and still very much open (the
  author pushed a fix and is waiting for the reviewer), and stale-open
  threads participate fully in dedup and reconciliation. An earlier
  draft had `outdated` as a third status value and told dedup to skip
  it — wrong on exactly this case, and removed.
- **Trimming**: `open` threads are carried verbatim — stale or not,
  and a stale open thread additionally carries its §3a blocks, since
  it's the one most likely to need careful reading. `resolved` threads
  carry the root comment (truncated at ~500 characters with a visible
  `[truncated]` marker) and `[{{n}} replies elided]` in place of their
  replies — enough to know what was raised and settled there, without
  spending tokens on the settlement conversation. Dedup (pipeline step
  4) considers open threads only; an issue raised and *resolved* at a
  location does not immunize that location, because resolution usually
  means the code changed and a new candidate there is describing new
  code.
- Everything inside this tag is untrusted external content: the
  harness's code-level sanitizer (`formats.md` §1) has already run on
  every body, and the review prompts' data-not-instruction rule
  applies to all of it.

Who consumes this block: **every review context, as data.** The
orchestrating context uses it for dedup (pipeline step 4) and
reconciliation (§7); finders and the validator receive it transcluded
verbatim in their briefs (§4, §5) as intent context — the record of
why the code is the way it is. An earlier draft kept finders and the
validator blind to it on an injection-surface argument; that was
reversed for a concrete failure the blindness causes: a reviewer asks
for X→Y, the author complies, and a blind finder — seeing only Y, with
no trace of the request — flags Y and proposes the revert, producing a
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

### 3a. Stale threads: comments across pushes *(blocks are phase 2; `at_sha` is v1)*

A thread is written against the PR as it stood at some head; the PR
moves on. Once finders read threads as intent context, a stale thread
without its history is actively misleading: "don't log the payload
here" read against code that no longer logs the payload looks like a
comment about nothing — unless the reader can see the code it *did*
apply to, and what changed at that spot since (often the very change
made in response). The comment's anchor line numbers are equally
treacherous: they belong to a version of the file that may no longer
exist.

**Definitions.** Each inline thread has an anchor commit `A` — the PR
head its root comment was made against (platforms record this; GitHub
calls it `original_commit_id`) — and an anchored region `R` (path +
line range, in `A`'s new-file numbering).

**Currency test.** A thread is **current** if `A` equals the
envelope's Head SHA, or if `git diff A..head -- path` contains no hunk
overlapping `R` (with a small margin, ±3 lines). Current threads
render in the plain form — no `at_sha`, no blocks, anchor mapped to
head numbering (the platform's own forward-mapped position) — so the
common case stays exactly as noisy as it needs to be: not at all.

**Stale rendering.** Otherwise the thread is **stale** and gains:

1. `at_sha="A"` on the `<thread>` tag. The thread's `anchor` line
   numbers are **`A`'s numbering, not the current head's** — the one
   deliberate exception to the head-SHA numbering convention, flagged
   by the attribute's presence and explained by the §3b format note.
2. An `@ {{sha}}` marker on every comment line — the PR head current
   when that comment was posted (from platform/webhook records, or the
   harness's own session records; omitted if genuinely unknown). This
   is what makes reply ordering relative to pushes readable: a reply
   marked with a later SHA than `<changed_since>`'s `from` was written
   *after* the code moved — "fixed in 6b1d94e" followed by that very
   SHA is self-verifying.
3. `<code_then sha="A">` — the PR-diff hunk the root comment was
   anchored on, as of `A`: the hunk overlapping `R` from the diff
   `merge-base(base, A)..A`. This is the artifact the commenter was
   actually looking at (a diff view, not a raw file) — GitHub stores
   it verbatim as `diff_hunk` and the harness may use that directly;
   on Bitbucket it reconstructs the hunk from git, which it can always
   do because it has `A`.
4. `<changed_since from="A" to="{{head_sha}}">` — the hunks of
   `git diff A..head -- path` (built with §2's flags) that overlap
   `R`'s forward image, again with the ±3-line margin. This is "what
   happened at that spot since the comment" — frequently the response
   to the thread itself.

**Force-push caveat** (mirrors §7a's session rule): if `A` is no
longer an ancestor of the head, `<changed_since>` cannot be computed
as a clean delta — the harness omits it, keeps `<code_then>` (still
valid: it's what the commenter saw), and marks the thread
`rebased="true"`. Never fabricate a delta across a history rewrite.

**Deliberately bounded archaeology.** One `<code_then>`/
`<changed_since>` pair per thread, anchored to the *root* comment —
not a reconstruction of every intermediate push state between every
reply. The question a reader must answer about a stale thread is
"does this comment still apply, and was it acted on?", which needs
*then* versus *now*; the `@ sha` markers recover reply-vs-push
ordering where it matters, and full per-push archaeology would
multiply envelope size for histories nobody needs re-litigated.

**Accepted redundancy.** On a re-review session, a stale thread's
`<changed_since>` often overlaps hunks also present in
`<incremental_diff>` (§7a) — `examples/review-envelope-rereview.md`
shows exactly this. The duplication is kept: the thread-local copy
makes each thread self-contained for a finder reading it in
isolation, and stale threads also occur *outside* sessions entirely —
a first Forge review of a PR that humans reviewed and the author
revised has stale threads and no interdiff at all. That first-review
case is why this machinery lives here in §3 and not inside §7.

**Phasing.** `at_sha` (and the `@ sha` comment markers) are v1 —
cheap, additive, and already enough for a careful reader to know the
numbering caveat applies. The `<code_then>`/`<changed_since>` blocks
and the §3b note arrive in phase 2 with the same git plumbing the
interdiff needs (`medium.md` §3f); until then the v1 fallback is
what it always was — the finder treats a thread whose `at_sha` isn't
the envelope head with proportionate caution.

### 3b. Conditional format notes (`<format_notes>`)

Explanatory prompt text that's only ever needed when a matching
envelope feature is present, injected by the harness only then —
so the common case pays nothing and the rare case gets told exactly
what it's looking at. Rules:

- `<format_notes>` sits immediately before `<existing_comments>`.
  It contains only **canonical, harness-fixed snippets** specified in
  this document — the harness selects which to include, it never
  writes or edits them, and the model never authors them. That's what
  makes an instruction-shaped tag near untrusted data safe: its text
  is exactly as trusted as the system prompt, because it's authored in
  the same place.
- Whenever a brief transcludes a block that has an active format note,
  the note transcludes with it (§4's transclusion rule applies to the
  pair).

One note is defined so far — the **stale-thread note**, injected iff
at least one thread rendered stale:

```
<format_notes>
Some threads below carry an at_sha attribute: they were anchored
against an earlier version of this PR, and the code they discuss has
changed since. For each such thread, <code_then> shows the diff hunk
the root comment was actually written against, and <changed_since>
shows how that region has changed between then and this envelope's
Head SHA — often in response to the thread itself. A stale thread's
anchor and line numbers belong to its at_sha, not to the current
diff; each comment's trailing @ sha says which version of the PR it
was written against. Read the conversation against <code_then>; judge
the current code against <changed_since> and the working tree.
</format_notes>
```

Worked example: `examples/review-envelope-rereview.md`.

---

## 4. The finder brief — exact payload

`system-prompts.md` §2 step 3 says what each specialist gets; this is
the wire shape of the `Task` call's `prompt`, assembled by the
orchestrator by **verbatim transclusion** of envelope blocks. (In the
single-stage shape (§6) there is no assembly step at all — the finder
*is* the top-level context and these blocks are already its envelope;
that identity is the point.)

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

<format_notes>
{{ present iff active for a transcluded block — §3b }}
</format_notes>

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
{{ phase 2, re-review sessions only — see §7: names the
   incremental-diff base SHA and restricts findings to code changed
   since it }}
</scope>
```

The finder's *instructions* (what to flag, what not to flag, the
discussion rules, output schema) live in the shared reviewer core
(`system-prompts.md` §4) and are not repeated per brief.

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
   Three sub-rules, carried in the reviewer core
   (`system-prompts.md` §4):
   - A thread never suppresses a candidate. Raise it even where the
     discussion already covers that code — dedup is a later pipeline
     step (step 4), and the report's nothing-silently-disappears
     accounting only works if candidates are raised and then visibly
     dropped, not silently unraised.
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
   sanitizer has already run on them, and the reviewer core's
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
(pipeline step 5), `prompt` assembled the same way — identically in
both run shapes (§6):

```
<candidate_finding>
{{ the finding, as JSON per formats.md §4, exactly as the finder
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

<format_notes>
{{ present iff active — §3b }}
</format_notes>

<existing_comments>
{{ envelope block, verbatim, when the PR has any — the discussion can
   already explain or authorize the behavior a finding targets
   (a reviewer requested it, a tradeoff was settled), which bears
   directly on the validator's "would a senior engineer flag this"
   question. The social counterpart of the in-code lint suppression
   its prompt already covers }}
</existing_comments>
```

What the validator deliberately does *not* get: the finder's
reasoning beyond what the finding schema itself carries
(`rationale` is part of the finding; any additional chain-of-thought
is not) and the other candidates. Independence is the
mechanism — the validator re-derives the claim against the code
(Read/Grep/Glob at Head SHA) rather than auditing the finder's
argument for persuasiveness. The discussion doesn't weaken that:
threads inform the *worth-flagging* judgment, while the *is-it-true*
judgment stays code-only — a comment asserting the code is fine is
weighed like a comment asserting it's broken, which is to say not at
all until the tree agrees.

**Phase 2 adds one variant**: the *resolution check*, dispatched by
re-review reconciliation (§7) — same payload shape plus the
`<incremental_diff>`, with the question inverted: not "is this
finding real" but "did the changes since {{sha}} actually fix this
previously-confirmed issue." Same binary-verdict discipline, same
reject-when-unsure default — except here "reject" means *don't
declare it fixed*, which fails safe in the same direction (no comment
posted claiming a fix that didn't happen).

Worked example: `examples/validator-brief.md`.

---

## 6. One review, two run shapes: single-stage and multi-stage

Everything above — envelope, diff, threads, briefs, validator — is
shape-neutral. The harness dispatches a review run in one of two
shapes, chosen per run by config (typically a changed-lines
threshold); nothing in the wire formats differs between them:

- **Multi-stage** (`system-prompts.md` §2a — the reference shape): a
  pure orchestrator fans out to parallel role specialists, then
  dedups, validates, delivers, reports. The pipeline as originally
  designed.
- **Single-stage** (`system-prompts.md` §2b): one context does the
  finding itself — the same reviewer core the specialists run, with
  the broad `all` lens covering every role at once — then runs the
  identical tail in the same context: dedup, validate (the same
  validator sub-agents, §5), deliver, report.

The unification is deliberate and total on the data side:

- A single-stage finder's "brief" is simply the envelope itself — the
  same blocks a specialist receives by verbatim transclusion (§4),
  with zero transformation in either direction. Same diff dialect,
  same thread model, same format notes.
- The finding schema, the validator payload (§5), the delivery rules
  (severity order, suggestion-block criteria), and the Complete
  report (`formats.md` §3b) are byte-identical across shapes.
  Switching a deployment between shapes is a harness flag, not a
  migration.
- On the prompt side, both finders run the same **reviewer core**
  (`system-prompts.md` §4) — the flag/don't-flag rules, the
  discussion rules, the line-number ground-truth discipline —
  parameterized only by lens: one role's scope for a specialist, the
  `all` scope for single-stage. Broad versus focused is the *entire*
  difference between a single-stage finder and a specialist, which is
  what keeps the two shapes from drifting into two products.

**Where dedup lives, and why it isn't part of verify.** Dedup is two
different jobs that happen to share a name:

- *External dedup* — candidate versus the PR's open threads — runs in
  **both** shapes, before validation (pipeline step 4). It sits with
  whichever context holds the threads (the orchestrator in multi, the
  single-stage agent itself) because that's where it's free, and
  running it pre-verify is what makes an already-reported finding
  cost nothing instead of a validator sub-agent run. Folding it into
  the validator would spend a fresh context per already-reported
  candidate and hand the validator a second question — and the
  validator's value comes precisely from having exactly one ("is this
  real"), answered from the code.
- *Internal dedup* — two finders raising the same issue at the same
  location — only exists where there are two finders, so it's
  multi-stage-only (pipeline step 5's same-location drop). It's
  inherently cross-candidate, which is also why it structurally
  *couldn't* live inside a per-candidate validator.

**What each shape buys.** Multi-stage buys lens focus and recall on
large diffs (a bugs specialist doesn't spend attention on convention
citations), parallel wall-clock time, and per-role model choice later
(`medium.md` §3d) — at the cost of extra finder contexts and the diff
copied into each (`formats.md` §1b's fan-out multiplier).
Single-stage buys cost and latency on the PRs that dominate real
queues — small diffs where three specialist contexts would each
re-read the same forty lines — at the cost of one context's attention
covering three lenses. In-collection precedent for shape-by-situation:
TuringMind's quick (4-agent) vs. deep (9-agent) tiers, and
pr-review-toolkit's user-chosen execution mode; PR-Agent and
Codex-review are production single-pass finders. What no source does —
and this design keeps in **both** shapes, non-negotiably — is the
independent validation pass: the hands-off false-positive argument
(`code-review-approaches.md` §5–6, README decision log) doesn't get
weaker because the finder got cheaper. A single-stage run is still a
two-opinion pipeline; it just spends the second opinion only on
candidates that survive dedup.

Multi-stage remains the v1 reference and default; single-stage is
v1-eligible behind the harness flag, and because every format is
shared, promoting it to default-for-small-PRs later is a config
change with no migration.

---

## 7. Re-review sessions: state, the interdiff, and thread reconciliation *(phase 2 — `medium.md` §3f)*

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
agent-side machinery. Sessions apply to either run shape (§6): the
session steps below belong to the orchestrating context, which in
single-stage is the same context that found the candidates.

### 7a. Envelope additions

Two additive tags, appended after `<existing_comments>`; a first
review simply omits both, which is exactly the v1 envelope:

```
<review_state rebased="false">
  <previous_session at="{{timestamp}}" head_sha="{{sha}}">
    <posted_finding id="{{finding_id}}" thread="{{thread_id}}"
        file="{{path}}" line="{{n}}" severity="{{severity}}"
        status="open|resolved">
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
  `<thread>` in `<existing_comments>`, where any replies live — and
  where, if the anchored code has since changed, the §3a staleness
  blocks already show then-versus-now: the state tag says *what Forge
  said and where*, the thread says *what happened next*.
- `<incremental_diff>` (the interdiff) is what changed since the last
  session. **Force-push/rebase caveat**: if `last_reviewed_head_sha`
  is no longer an ancestor of the new head, the interdiff would be
  garbage (it would diff across the rewrite, blaming the rebase for
  everything). The harness detects this, omits `<incremental_diff>`
  entirely, and sets `rebased="true"` — the session then runs
  full-scope like a first review, with dedup and reconciliation still
  doing their work. Never fabricate an interdiff across a rewrite.

### 7b. Pipeline deltas

Against the numbered pipeline in `system-prompts.md` §2 — same steps,
three changes:

- **Step 1 (warranted?)** gains a session-aware skip: an empty
  interdiff *and* no new replies on any Forge thread means nothing
  happened since last session → `Complete(skipped)`.
- **Step 3 (finders)** — each brief carries the **full diff plus a
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
  finders run full-scope.
- **Step 3½ (reconciliation)** — new, run by the orchestrating
  context, dispatched in the same turn as the finders since neither
  depends on the other. For each **open, Forge-authored** thread in
  `<review_state>` (`status="open"`, joined to its thread), exactly
  one of:

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
  (already in the review prompts): matter-of-fact, no filler, no
  "thanks for the fix!" boilerplate.
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

### 7c. Tool addition

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

## 8. Mid-run races: the snapshot contract

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
  and the platform handles the stale-anchor bookkeeping (the §3a
  machinery will render it faithfully to the *next* run) — but the
  tool result carries `head_moved: true`. The orchestrating context
  finishes the session normally (its findings are true *of the commit
  it reviewed*) and records the supersession in its Complete summary;
  it never chases the new head mid-run. Dispatching the follow-up
  session against the new head is the harness's trigger policy, not
  the agent's decision.
- **Serialization.** At most one review session per PR runs at a time;
  pushes and comments arriving during a session coalesce (debounce)
  into at most one queued follow-up session. Harness-side, but stated
  here because §7's state model assumes it: "the previous session"
  is only well-defined if sessions don't interleave.

---

## 9. Code changes in response to comments — the boundary

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
reconciliation (§7b step 3½) sees Forge-authored replies on its own
threads plus the fix in the interdiff — confirming, resolving, and
reporting `thread_updates` exactly as if a human had made the fix. The
two entrypoints never share a run; they meet only through the platform
state (threads, commits) and the envelope formats defined here.

One rule worth stating because both sides touch it: **thread etiquette
is owned by whichever run replies.** A responder run's reply says what
it changed (or why it disagrees, once — the same one-round cap as
§7b's standing-firm rule, for the same reason); a review session's
reply says what it verified. Neither posts progress narration,
"working on it" placeholders, or a second reply where one already
covers it.

---

## 10. Phasing summary

| Capability | v1 | Phase 2 (`medium.md` §3f) | Later (tracked) |
|---|---|---|---|
| Diff | §2 algorithm: merge-base, `-U5 -M`, visible elisions | unchanged | Per-hunk line-number injection; diff-as-file (`medium.md` §3b) |
| Comment context | §3 threaded model, full set inline; transcluded into every brief as intent context under §4's discussion rules | unchanged | — |
| Stale threads | `at_sha` attribute + `@ sha` comment markers (§3a) | + `<code_then>`/`<changed_since>` blocks and the `<format_notes>` stale note (§3a–3b, same plumbing as the interdiff) | — |
| Run shapes | Both specified (§6); multi-stage is the reference default, single-stage selectable by harness config — identical formats either way | unchanged | Per-role model selection (`medium.md` §3d) |
| Finder/validator briefs | §4/§5 verbatim-transclusion payloads | + `<scope>`/`<incremental_diff>`; resolution-check variant | Ticket-compliance lens brief (`medium.md` §3a) |
| Repeat review | Full re-review + dedup against open threads | Sessions: `<review_state>`, interdiff scoping, reconciliation, `thread_updates` | Finding-outcome telemetry (`medium.md` §3e) feeding thresholds |
| Replies | None (review posts new findings only) | Reconciliation replies + `resolve_thread`; one-round standing-firm cap | — |
| Comment-driven code changes | None | Responder/fix runs (`medium.md` §1b/§1c) consuming §3's thread shape | — |
| Races | §8 snapshot contract, `head_moved`, serialization | unchanged | — |

Everything phase 2 adds is an additive tag (`<review_state>`,
`<incremental_diff>`, `<scope>`, `<code_then>`, `<changed_since>`,
`<format_notes>`), an additive field (`resolve_thread`,
`thread_updates`), or a new run source — no v1 shape changes meaning.
That is the property the whole document is built to protect: the query
structure holds still while the behavior around it grows.
