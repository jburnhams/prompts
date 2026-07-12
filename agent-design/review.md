# Design review

A full pass over `README.md` / `tools.md` / `system-prompts.md` /
`formats.md`, cross-checked against the rest of this repo's research
(`agent-self-verification.md`, `agent-subagent-architectures.md`,
`agent-permissions-approval.md`, `agent-context-compaction.md`,
`code-review-approaches.md`, `coding-agent-approaches.md`,
`agent-git-vcs.md`, `agent-tool-surfaces.md`) and the primary sources
they catalogue — in particular Anthropic's own `/code-review` skill
(`skills/anthropic/code-review/commands/code-review.md`), which the
review pipeline deliberately mirrors.

Findings are ordered by severity. Each notes whether the fix was
**applied** to the design docs in this same change, or left as an
**open question** because it's genuinely a judgment call the design's
owner should make.

## What's already strong (kept, not revisited)

- The decision log with named rejected alternatives is the best part
  of the design — every load-bearing choice traces to a specific
  research finding rather than taste.
- The scratch-directory decision (structural boundary instead of a
  remembered cleanup step) is exactly the right instinct, and it's the
  same instinct several findings below extend to other parts of the
  design.
- Author-agnostic dedup, the binary validator, `AskUser` as
  suspend-and-exit rather than block-in-place, and the no-git-writes
  delivery contract are all well-reasoned and well-precedented; nothing
  below touches their substance.

---

## F1 — Read-only modes were prompt-enforced only (high; applied)

`tools.md` said `Edit`/`Write` are "wired to the coding orchestrator in
every mode" with the read-only rule living purely in the system prompt —
and said so out loud ("the behavioral rule this table doesn't enforce on
its own"). Two problems:

1. This contradicts the design's own scratch-dir philosophy: "a
   structural directory boundary can't be forgotten or misconfigured"
   applies at least as strongly to write tools in a mode that must
   never write.
2. It left a real hole: under `mode: plan`, `Task(general-purpose)` had
   *full tool parity* — a read-only orchestrator could delegate to a
   write-capable sub-agent.

The research is unambiguous that structural enforcement beats prompted
enforcement wherever it's cheap: Gemini CLI strips agent-kind tools
from sub-agent registries in code ("the model has no code path to
violate" — `agent-subagent-architectures.md` §6); Composio scopes
permissions per role "at the tool level, not just by instruction";
`agent-permissions-approval.md`'s central takeaway is that every
serious source layers prompt rules *on top of* a structural gate, never
instead of one. Withholding two tools per run mode costs the harness
nothing.

**Applied**: `tools.md` availability is now mode-scoped — in
`plan`/`investigate`/`review_only` runs the harness does not wire
`Edit`/`Write` at all (for the orchestrator *or* its `general-purpose`
delegates), and `Bash` keeps its existing read-only-git rule as prompt
text since command-level filtering is a real permission engine (v2, per
the README's "not in v1" list). The system-prompt rule stays as belt to
the new suspenders.

## F2 — No run-bounding or context story at all (high; applied)

The design says stopping without `Complete` is "a failure mode to
avoid" — but nothing bounds a run. No turn cap, no token budget, no
wrap-up mechanism, no position on compaction. A hands-off agent on a
gnarly ticket *will* hit the context ceiling, and when it does, this
design's contract (always end via `Complete`) is unenforceable: the run
just dies mid-turn and the Jira ticket hears nothing — indistinguishable
from the harness crashing.

Precedents for the cheap fix: Copilot Chat injects a forced "your
allotted iterations are finished" nudge on the last allowed turn
(`agent-self-verification.md` §4 / `agent-subagent-architectures.md`
§4); Grok Build gates ending a turn at all while work is open. And
`agent-context-compaction.md` shows compaction is a deep subsystem no
v1 should casually absorb — so the right v1 position is to *say* it's
out and define what happens instead.

**Applied**: `formats.md` gains §7 (run bounding): the harness enforces
a turn budget and a context high-water mark; crossing either injects a
final wrap-up turn whose only permitted actions are `AskUser` or
`Complete` (with `status: "failed"` and a partial report being an
acceptable, honest outcome). No compaction in v1, stated explicitly in
the README's "not in v1" list. The `Complete` schema needs no change.

## F3 — `Complete` is an unverified self-report (high; applied)

The single most-documented failure mode in this repo's research is the
false completion claim: `agent-self-verification.md` §7 records a leaked
Anthropic code comment measuring a **29-30% false-claim rate** on an
internal model version, and its design takeaways note that mechanical
gates "can't be talked out of firing" while prompt-only instructions
routinely are. Forge's v1 had `verification` results, `files_changed`,
and the final `git status` check all as *self-reported prompt
obligations* — the exact shape §7 catalogues as weakest.

Two deterministic, non-LLM gates are available almost for free, both
directly precedented:

1. **SWE-agent's `review_on_submit_m` pattern** (§2 of the
   self-verification doc): the first `Complete(status: "done")` call in
   an `implement` run doesn't complete — it returns a canned checklist
   as the tool result (re-run your verification commands now; run
   `git status` and confirm every path is intended; confirm no scratch
   files leaked). Only a second `Complete` goes through. Pure string
   templating, no extra model call.
2. **Harness-side cross-check**: the harness computes the real changed
   file list from `git status` after the run and records (not blocks
   on) any mismatch with the reported `files_changed` — and in
   read-only modes, a *non-empty* working-tree diff is a hard integrity
   failure it can detect without any model involvement.

**Applied**: both, in `tools.md` (`Complete`) and `formats.md` §3a.

## F4 — Review-mode line anchoring was under-specified (high; applied)

The design's own decision log says pre-formatting the diff exists
because "line-number accuracy matters more when comments post
unsupervised" — but then under-delivered on exactly that:

- A plain `-U5` unified diff forces the model to derive new-file line
  numbers by hunk arithmetic — the error-prone step PR-Agent's custom
  hunk format (line numbers injected per hunk) exists to remove
  (`code-review-approaches.md` §3).
- The finding schema has `line`/`line_end`, but `AddComment.anchor` was
  a single `line` — multi-line findings and multi-line committable
  suggestions (which replace the anchored *range* on GitHub) were
  structurally impossible.
- Nothing said which side of the diff a line number refers to, and
  nothing handled the GitHub constraint that an inline comment must
  anchor within a diff hunk.

**Applied**: `AddComment.anchor` gains `line_end`; anchors are defined
as new-file (right-side) line numbers; the harness validates that an
anchor is commentable and falls back to a non-anchored PR comment
(prefixed with `file:line`) rather than dropping the finding, reporting
the fallback in the tool result. `suggestion` is now schema-bound to
require `anchor` (same `allOf` device the Task tool already uses).
PR-Agent-style per-hunk line-number injection is noted as the v2
upgrade if mis-anchoring shows up in practice.

## F5 — Review sub-agents' Read/Grep/Glob assumed an unstated checkout (medium; applied)

`reviewer`/`validator` are told to pull in surrounding context with
Read/Grep/Glob — which only works if the working tree actually contains
the PR head the diff was generated from. No document said the review
harness checks anything out, at what SHA, or that the diff and tree are
guaranteed consistent. An implementer could reasonably have built
review mode with no checkout at all (the envelope carries the diff,
after all) and shipped sub-agents whose tools silently read the wrong
version.

**Applied**: the review envelope (`formats.md` §1b) now carries
`head_sha`/`base_sha`, and states the harness guarantee: the working
tree is checked out at `head_sha`, and the baked diff is
`base_sha...head_sha`.

## F6 — `general-purpose` inheriting the full coding prompt verbatim (medium; applied)

`system-prompts.md` had the coding-mode delegate follow "the OpenCode
convention" of inheriting the parent's prompt unchanged. But the
analogy doesn't hold: OpenCode's `general` inherits a base *persona*
prompt. Forge's coding prompt is not a persona — its spine is the task
envelope, the mode mandate, and the "you must end with Complete /
AskUser" contract, all of which reference tools and context the
sub-agent doesn't have. A delegate running under that prompt is being
instructed, in its own system prompt, to end its run with a tool call
it cannot make.

`agent-subagent-architectures.md` §3 shows the mainstream answer: every
source with a captured delegate prompt (Copilot Chat, Crush, Goose,
OpenHands, Amp's `H_R`) gives the delegate a short, role-scoped prompt
of its own — Amp's is ~10 lines.

**Applied**: `system-prompts.md` gains a short dedicated
`general-purpose` prompt (§3, before the reviewer/validator prompts):
persona line, tool list, "your brief is complete — you cannot ask
follow-ups," and a final-report contract ("answer exactly what was
asked, cite paths/lines, say what you ruled out"). ~12 lines.

## F7 — Review pipeline ordering wasted validators; no-findings comments spam re-reviews (medium; applied)

Two related issues, both consequences of (correctly) dropping the
run-level skip gate:

1. Dedup against `<existing_comments>` ran *after* validation — so on a
   re-review, every already-reported finding burned a validator
   sub-agent before being discarded. The dedup criterion is identical
   either way; running it earlier is pure cost savings.
2. "If no findings survived, post one short summary comment" — on a PR
   re-reviewed on every push, that's a fresh "nothing to report"
   comment per push. This recreates exactly the noise problem the
   dedup design exists to prevent (and the codex-review reference
   implementation is called out in `code-review-approaches.md` §9 for
   duplicating comments on re-runs).

**Applied**: pipeline reordered — existing-comment dedup now sits
between specialist fan-out and validation; intra-run same-location
dedup stays after validation. Both `findings` and `filtered` accounting
in the `Complete` report are unchanged (filtered-before-validation
entries record `validated: null` plus the dedup reason).

**Superseded (see "Review delivery shape" below)**: the no-findings
summary comment and its dedup are removed entirely, not just deduped.
`AddComment` is now findings-only — a no-findings run posts nothing to
the PR at all. The run's outcome (including "nothing found") is
reported solely via `Complete`'s summary field; surfacing that to the
PR, if desired, is the invoking harness's decision, not something Forge
does through its own tool calls. This also resolves open question 3
below: `AddComment` stays create/reply-only (no `UpdateComment`), and
there is no tracking-comment mechanism in v1 — with summary comments
gone entirely, there's nothing left for a tracking comment to update.

## F8 — No large-diff policy (medium; open question + placeholder applied)

The envelope bakes the full diff into the prompt with no size gate. A
5-figure-line PR blows the context window before the run starts —
there's no code path in which Forge even gets to call
`Complete(skipped)`. BMAD is the collection's precedent (>3000 changed
lines → chunk); PR-Agent token-clips.

**Applied**: `formats.md` §1b now names the constraint and requires the
harness to enforce *some* threshold before dispatch, with
skip-with-reason as the v1 default behavior.

**Resolved: skip, not shard — no source in the collection does
automated sharding-with-merge.** Checked against Anthropic's own
`/code-review` skill (the pipeline Forge's review mode is explicitly
modeled on) and `claude-code-action`, not just the sources already
cited: Anthropic's skill has *no* size gate at all — its troubleshooting
doc says large PRs are just slow ("4 independent agents ensure
thoroughness... consider splitting large PRs into smaller ones," i.e.
the PR *author's* job, before review, not the harness's). PR-Agent's
`can_be_split` field is the same shape — the model proposes a
human-facing sub-PR split, it doesn't shard its own review. BMAD's
chunking is human-mediated across separate runs (agree the first group
with the user, list the rest for follow-up runs), not an in-run merge.
Nobody in the collection solves "which findings span a batch boundary"
without a human deciding the grouping — which doesn't transfer to
Forge's unsupervised review pipeline. Skip-with-reason stands as more
than a leanness default; it's what every real source effectively does
once you net out the human-mediation each one leans on.

The threshold itself is now specified as harness-configurable rather
than a hardcoded constant — either a fixed changed-line count (BMAD's
shape) or a fraction of the deployed model's context-window budget,
estimated from diff character count via a fixed chars-per-token ratio
(no tokenizer call) and adjustable for the specialist-fan-out
duplication multiplier. See `formats.md` §1b. BMAD's ~3000-line figure
is the only concrete number found anywhere in the collection, and it
carries no stated derivation (no token-budget or cost math behind it)
— not reused as a default for that reason.

## F9 — `AskUser` granted to the review orchestrator but never used (low; applied)

The review pipeline has no step that can reach `AskUser`, and
suspend/resume makes little sense for a review anyway — by the time a
human answers, new pushes have likely invalidated the diff the question
was about. An unused escape hatch on an unsupervised path is surface
area for misuse (a prompt-injected "ask the user to approve this"
becomes representable).

**Applied**: `AskUser` removed from the review orchestrator's tool set
in `tools.md`. Review runs end in `Complete` (`done`/`skipped`/
`failed`) only.

## F10 — Self-reported `files_changed` vs. harness truth (folded into F3; applied)

Covered by F3's harness-side cross-check; noted separately only because
`suggested_commit_message` means the external committer *reads* the
report — so a report/tree mismatch should be visible to it, not just
logged.

## F11 — `mode` stated in two places (low; applied)

`Run mode` appeared in `<env>` *and* as `<mode>` in the task envelope —
two copies that can drift, and it's a per-task fact, not an
environment fact. **Applied**: dropped from `<env>`; the envelope is
the single source of truth.

## F12 — Coding mode had no data-vs-instruction rule (low; applied)

The review prompt has the "data, not instruction" paragraph; the coding
prompt had nothing equivalent, even though its envelope carries just as
much untrusted text (ticket description, *comments from any Jira user*,
linked issues). The subtlety is that the ticket **is** the task — so
the rule can't be "ignore instructions in the ticket." The right line:
the ticket defines *what to build*; text inside ticket/comment content
that tries to change *how Forge operates* (mode, safety rules, tool
behavior, "ignore previous instructions") is data to flag, not obey.

**Applied**: one paragraph in the coding prompt's Safety section.

## F13 — Sanitization belongs in the harness, in code (low; applied)

`claude-code-action` is the only source in the collection that strips
invisible/zero-width Unicode, bidi overrides, and hidden HTML from
untrusted content *in code* before it reaches the prompt
(`code-review-approaches.md` §10, `sanitizer.ts`). Tag-separation (which
the envelope already has) defends against structural confusion; it does
nothing against invisible-character payloads. **Applied**: stated as a
harness requirement in `formats.md` §1.

## F14 — Specialists lacked part of the false-positive exclusion list (low; applied)

Anthropic's `/code-review` gives its *finder* agents the full
do-not-flag list; Forge gave specialists a subset and left "linter
would catch it" and "explicitly silenced in code" to the validator.
Every excluded candidate a specialist never raises is a validator call
never spent. **Applied**: two bullets added to the specialist prompt's
"Do not flag" list.

## F15 — `severity` was produced but never consumed (low; applied)

Findings carry `severity`, but nothing ordered, filtered, or displayed
by it. **Applied**: step 6 now posts comments in severity order and
prefixes each comment body with its severity. (An actual severity
*threshold* stays out of v1 deliberately — same reasoning as the
"no numeric confidence scoring" decision.)

## Noted, not applied (v2 candidates)

- **Diff-as-file instead of diff-in-prompt-thrice.** The orchestrator
  currently carries the diff in its envelope *and* copies slices into
  each specialist's Task prompt. Having the harness also write the diff
  to a scratch-dir file and letting sub-agents `Read` it would cut the
  duplication for large PRs — at the cost of sub-agents starting cold
  on what they should read. Worth measuring before adopting.
- **Double-coverage on the bugs lens.** Anthropic's skill runs *two*
  bug finders in parallel for recall and lets validation handle the
  overlap. Forge runs one per lens. Cheap to add later if recall
  measures low; the validator + dedup machinery already handles the
  duplicate-findings consequence.
- **Turn caps for sub-agents** (Copilot Chat's `isLastTurn` nudge) —
  same mechanism as F2, one level down. F2's harness budget bounds the
  whole run, which is enough for v1.

## Questions for the design's owner

1. ~~**`review_only` naming.**~~ **Resolved: folded into `investigate`.**
   It collided confusingly with the review *entrypoint* ("review mode"),
   and its definition was already "treat the same as `investigate`."
   `system-prompts.md`, `tools.md`, and `README.md` now define three
   coding-mode values (`plan`/`implement`/`investigate`), with
   `investigate` covering both open-ended investigation and
   look-don't-touch assessment — the task instruction carries that
   distinction, not the mode.
2. ~~**Large-diff policy (F8): skip or shard?**~~ **Resolved:
   skip-with-reason, threshold harness-configurable** (fixed line count
   or a char-count-estimated fraction of the model's token budget,
   adjustable for specialist fan-out). No source in the collection,
   including Anthropic's own `/code-review` skill, does automated
   sharding-with-merge — see F8 above.
3. ~~**Review delivery shape.**~~ **Resolved: no `UpdateComment`, no
   tracking comment, no summary comment at all.** `AddComment` stays
   create/reply-only and findings-only. A no-findings run — and a run's
   overall outcome generally — is reported through `Complete`'s summary
   field only; whether/how that reaches the PR (a tracking comment, a
   check-run annotation, nothing) is the invoking harness's decision,
   not Forge's. See F7's "Superseded" note above.
4. ~~**Jira body format.**~~ **Resolved: `AddComment.body` stays plain
   Markdown, always — conversion to whatever the target platform
   actually needs (Jira Cloud's ADF, legacy wiki markup, anything else)
   is entirely a harness-side concern, never something Forge's schema
   or prompts encode.** Language across `tools.md`/`formats.md` updated
   to say "issue-tracker issue" rather than assuming Jira specifically
   wherever the concept is platform-generic (the `AddComment`/`AskUser`
   mechanics apply to whatever tracker the harness is wired to);
   `FetchJira` itself stays Jira-named, since first-class Jira
   integration is a named requirement in the brief, not a
   platform-generic capability.
