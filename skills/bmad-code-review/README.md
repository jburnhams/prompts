# BMAD-METHOD: code-review skill

- **Publisher**: BMad Code, LLC
- **License**: MIT
- **Source**: https://github.com/bmad-code-org/BMAD-METHOD
- **Retrieved from**: `main` branch,
  `src/bmm-skills/4-implementation/bmad-code-review/` +
  `src/core-skills/bmad-review-*/` (2026-07-10)

One small piece (`4-implementation/bmad-code-review`) of a much larger
"agile AI-driven development" framework (34+ workflows: planning,
architecture, story-writing, dev, retros, etc.) — only the code-review
skill and the three reviewer sub-skills it invokes are included here. Note:
the repo restructures its `src/` layout frequently (this was previously
under `src/modules/bmm/workflows/...`, now under `src/bmm-skills/...`), so
expect these paths to move again.

Structurally, this is the most elaborate scaffolding of anything in this
collection — a **4-step-file state machine** (`steps/step-01` through
`step-04`), each step read in isolation just-in-time rather than the whole
workflow being one prompt, with explicit HALT checkpoints where it must
wait for human input before continuing.

## Scaffolding (beyond the prompt text)

- **Context/diff construction is itself a 5-tier cascade**
  (`steps/step-01-gather-context.md`): explicit user argument → recent
  conversation → sprint-tracking file (a BMAD-specific "stories in review
  status" file) → current git branch vs `main` → finally, ask. Once a
  source is identified, it maps to a specific git incantation: `git diff
  --cached` (staged only), `git diff HEAD` (uncommitted, staged+unstaged),
  a verified branch/commit-range diff, or a user-pasted unified diff
  (validated as parseable). Diffs over ~3000 lines trigger an offer to
  chunk the review by file group.
- **Spec cross-referencing**: optionally loads a spec/story file and any
  docs referenced in that file's frontmatter `context` field, enabling an
  "Acceptance Auditor" layer (see below) that checks the diff against
  acceptance criteria, not just code quality in isolation.
- **Review layers are pluggable, not hardcoded**: `customize.toml` defines
  a `[[workflow.review_layers]]` array — each layer is literally an
  instruction template with `{diff_output}`/`{spec_file}` placeholders,
  overridable per-team/per-user via TOML merge files. Default layers invoke
  three separate sub-skills as isolated subagents *with no prior
  conversation context* (`core-skills/bmad-review-*.md` — adversarial
  general-purpose, edge-case hunting, and verification-gap analysis), plus
  a spec-conditional "Acceptance Auditor" layer.
- **Triage, not just severity scoring** (`steps/step-03-triage.md`):
  findings are deduplicated, severity-rated only after re-reading
  surrounding code (not from the diff hunk alone), then routed into one of
  four buckets — `decision_needed` (ambiguous, needs a human call),
  `patch` (unambiguous fix), `defer` (real but pre-existing), `dismiss`
  (noise) — a materially different model than "confidence score + binary
  filter" used elsewhere in this collection.
- **Output isn't just a chat reply**: findings get written into the spec
  file's own Tasks/Subtasks section (checked/unchecked checklist items),
  deferred items get appended to a separate `deferred-work.md`, and story
  status + a `sprint-status.yaml` file get updated to reflect review
  outcome — output is meant to update project state, not just inform the
  user.

## Files

- `SKILL.md` — activation sequence, config loading, and the step-file
  execution model rules.
- `customize.toml` — the pluggable review-layer definitions (see above) and
  override points.
- `steps/step-01-gather-context.md` — diff-source cascade + spec loading.
- `steps/step-02-review.md` — runs the configured review layers.
- `steps/step-03-triage.md` — dedup, severity, and bucket routing.
- `steps/step-04-present.md` — writes findings to project files, walks the
  user through resolving/patching, updates story/sprint status.
- `core-skills/bmad-review-adversarial-general.md` — general adversarial
  reviewer (default layer).
- `core-skills/bmad-review-edge-case-hunter.md` — edge-case-focused
  reviewer (default layer).
- `core-skills/bmad-review-verification-gap.md` — looks for gaps between
  claimed behavior and actual verification/tests (default layer).
