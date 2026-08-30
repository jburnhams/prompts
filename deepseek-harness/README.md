# DeepSeek Harness (`dsh`)

DeepSeek AI's open-source agent harness, released as a *developer preview*
in August 2026. Everything below was retrieved from
[`github.com/deepseek-ai/deepseek-harness`](https://github.com/deepseek-ai/deepseek-harness)
at commit `47f9438` (`master`, 2026-08-13), read **2026-08-14**.

**License:** MIT. Prompt text and skill files are reproduced here under it.

## What this source is

A TypeScript monorepo — 51 package groups, ~7,400 files — built on a
vendored copy of [Cordis](https://github.com/cordiverse/cordis), a
dependency-injection/plugin framework. The organising claim is
"**everything is a plugin**": the tool registry, the system-prompt
assembler, the sandbox, compaction, subagents, plan mode and the agent
loop itself are all Cordis plugins registered through `ctx.effect()`, and
a deployment is a `cordis.yml` file naming which ones to load.

Two things make it unusual as a *source of prompts*, and both are why it
earns a folder here rather than a line in `sources.md`:

1. **The prompt is assembled, not authored.** No file in the repo contains
   the system prompt. Each plugin contributes an ordered
   `PromptSection`, and `dsh-system-prompt` concatenates them per request.
   What's stored here is therefore a *snapshot* — the assembled result,
   checked into the repo as a test expectation.
2. **The repo's own agent-facing process documents are themselves a
   corpus.** `AGENTS.md`, the `.agents/skills/` set, and the Agent Note
   tree are the instructions DeepSeek gives agents working *on* dsh. The
   code-review skill and its self-maintenance loop are the most developed
   artifacts of their kind in this collection.

## Files

| File | What it is |
|---|---|
| [`system-prompt-native.md`](./system-prompt-native.md) | The assembled system prompt for an ordinary (non-Code-Mode) turn, from `examples/acp-agent/tests/snapshots/text-turn/system-prompt.expected.md`. ~3.4 KB: harness identity, deployment persona, then one short guidance paragraph per tool package. |
| [`system-prompt-code-mode.md`](./system-prompt-code-mode.md) | The same assembly with **Code Mode** on, from `.../snapshots/code-mode-turn/`. ~28 KB, almost all of it a generated TypeScript `.d.ts` declaring every tool as `tools.<name>(args)` with a full `ToolArgsMap`/`ToolOutputMap`. |
| [`AGENTS.md`](./AGENTS.md) | The repo's project-memory file — the standing orders every agent session loads. Word-budgeted to ≤1,600 words by a gate. |
| [`skills/dsh-code-review.md`](./skills/dsh-code-review.md) | The PR-review skill. See below. |
| [`skills/dsh-prose-standard.md`](./skills/dsh-prose-standard.md) | Required prose coverage + editorial judgment, per prose location (JSDoc, comments, tests, READMEs, Agent Notes, prompts, diagnostics). |
| [`skills/dsh-trim-cot-leakage.md`](./skills/dsh-trim-cot-leakage.md) | An eight-class taxonomy of **chain-of-thought leakage** in committed prose, with keep-rules for what only *looks* like leakage. |
| [`skills/dsh-trim-cot-leakage-examples.md`](./skills/dsh-trim-cot-leakage-examples.md) | Its calibration file, including the four **overcorrection traps** that shipped in the original purge and were caught in review. |
| [`skills/dsh-find-simplifications.md`](./skills/dsh-find-simplifications.md) | Turning "find things to simplify" into evidence-backed proposals; the production/non-production/ambiguous consumer classification. |
| [`skills/dsh-pre-push-checks.md`](./skills/dsh-pre-push-checks.md) | Selecting the *smallest* evidence that covers a diff, instead of running the full suite. |

Not copied here, but the paths worth re-reading — see
[`../sources.md`](../sources.md) for the full list:
`docs/cookbook/maintaining-dsh-code-review.md` (the review-skill
maintenance workflow), `.agents/notes/proposed/process/2026-07-13-human-review-skill-maintenance.md`
(its specification, with measured results),
`docs/cookbook/adding-a-package.md` §4 (the Model Experience README
contract), `docs/AGENTS.md` (the doc tier taxonomy and slop checklist),
and `.agents/notes/README.md` (the Agent Note format).

## The five things worth reading this source for

### 1. A code-review skill that maintains itself from human review feedback

[`dsh-code-review`](./skills/dsh-code-review.md) is 49 lines and reads
like the distilled output of many reviews — because that's what it is. A
private periodic tool mines *merged* PRs for pre-merge **human** review
comments, decides which ones the final code actually adopted, and drafts
a revised `SKILL.md` from the adopted set.

The parts that make it more than "feed comments to a model":

- **Adoption is proven by diff, not by social signal.** Merge, thread
  resolution, an author's "fixed" reply, and a same-file edit are all
  explicitly *context rather than adoption proof*. The tool compares two
  PR-specific patch snapshots — baseline→feedback-time and target-parent→merge
  — precisely so a change that arrived on the target branch can't be
  miscredited to the review comment.
- **Two independently configured reviewer adapters** classify authorship
  and adoption; only matching `human-authored` + `adopted` verdicts
  proceed. The tool refuses to run if the two adapter commands resolve to
  byte-identical executables.
- **Bot findings are excluded by contract.** The source is human review
  feedback; humans forwarding automated findings are filtered out too.
- **Untrusted-input handling is explicit**: feedback is wrapped in a
  `<untrusted-feedback nonce="…">` block with a 128-bit nonce so a comment
  body can't forge the closing tag.
- **A human promotes, and is told not to defer to the reviewers.** The
  cookbook's first instruction on receiving a candidate diff is "Do not
  defer to 'the reviewers approved'" — look for checklist bloat,
  unsupported extrapolation from a single incident, duplicated coverage.
- **The measured result is mostly silence.** The Agent Note records the
  2026-07-15 acceptance run: 62 merged PRs scanned, 426 human feedback
  items considered, **0 candidates surfaced**. "Days without a skill
  update are the workflow behaving correctly, not a stall."

**Re-read 2026-08-30 at `cd5ef81`** (the stored copies remain the
`47f9438` snapshot). Two weeks on, `dsh-code-review/SKILL.md` has gained
exactly one rule — item 7, "Client UI copy is locale-owned" — and
`git log` says where it came from: `3c10f5d2d fix(client): route UI copy
through locale`, **the implementation PR that established the
convention**, which in one commit routes ~40 files' strings through the
locale dictionaries, adds the `verify-client-ui-i18n` gate, writes a new
Agent Note, and appends the review rule that will catch the next
violation. The maintenance loop did not produce it. The same shape holds
for the file's other recent history: `61703d224` adds the `change-scope`
tool *and* rewrites the skill's opening paragraph to tell reviewers to run
it; `a4be4b5e5` replaces item 5 wholesale rather than appending a sixth.
So over the window observed here, mining produced zero rules and ordinary
convention-setting PRs produced all of them — not an argument against the
loop (its authors call silence correct), but a sharp one about order of
investment. Recorded in full in
[`../agent-memory-learning.md`](../agent-memory-learning.md) §8, alongside
the protocol detail from the Agent Note that the first pass summarised:
merge-commit ancestry as the sole eligibility check, why PR conversation
comments are excluded outright (a force-push makes "which commit preceded
this comment" unprovable), batch-level fail-closed on a hallucinated id,
and the rule that most sharply separates this loop from the
self-mining ones — **"a singleton may qualify; recurrence is not
required."**

### 2. The review skill's own content: manual checks, not a checklist

It opens by disclaiming itself — "**This skill is guidance, not a
complete checklist**" — and closes with "a short review with one
substantiated blocker is better than a list of nits." In between, the
checks are unusually specific about *what code alone can't show*:

- **Model perspective** as a review dimension: "inspect the exact
  prompts, tool schemas, results, and diagnostics the model receives
  across affected modes. Flag concepts outside the model's task."
- **The inverse API-bloat check**: not just "is this abstraction used?"
  but "a new public method on a generic service whose only caller is one
  internal consumer is an unnecessary API expansion — require a private
  capability closure handed to that consumer at construction instead."
- **Enforcement tracing**: "follow every denial path to the operation
  that executes it; exercise direct and alternate callers that can bypass
  schemas, prompts, facades, wrappers, or listener ordering."
- **Test strength over coverage**: "assertions fail on the intended
  regression and verify external state, logs, events, or disposal rather
  than restating the implementation **or trusting an agent's report**.
  Coverage is necessary but not evidence that the scenario is correct."
- **Omit what a gate already proves**: "omit issues already enforced by a
  green gate" — the skill's scope is explicitly the residue that
  automation cannot reach.
- Reviewing *received* review: "verify each claim and fix or rebut it on
  technical grounds **without performative agreement**."

The companion cookbook
(`docs/cookbook/responding-to-pr-review-on-a-stack.md`) adds the two
sharpest lines in the repo on verification:

> for a regression guard, prove it FAILS on the unfixed code (introduce
> the regression, watch red, revert) — a guard that passes both ways
> guards nothing

> A sub-agent that reframes a problem as already handled is a signal to
> dig in personally.

### 3. Code Mode: tools as a typed TypeScript API

[`system-prompt-code-mode.md`](./system-prompt-code-mode.md) shows the
model a generated `.d.ts` — `ToolArgsMap`, `ToolOutputMap`,
`ToolCallError`, `declare const tools` — and asks for the body of an
async function instead of a tool call. Every registered tool is reachable
as `await tools.name(args)` "for free," re-entering the normal execution
pipeline including policy.

The load-bearing sentence is about context, not ergonomics:

> ONLY what you print or return comes back to you — intermediate tool
> results never enter the conversation, so extract just what you need.

Two contract details that don't appear in other harnesses here: a tool's
`output.schema` is explicitly designed as *a programmatic API* ("return
handles and fields directly … keep human explanation in
`output.render`"), and the cookbook states the resulting rule outright —
a background job's Native renderer may say `started background job
bash-1`, but **"Code Mode must never parse that prose to recover the
id."** The same tool therefore has two truths: a canonical JSON value for
programs and rendered prose for the transcript.

### 4. The "Model Experience" README contract — machine-enforced

Every package README must end with a canonical section, checked by
`scripts/verify-package-readme-model-experience.ts`:

```
## Model Experience
### <each context entry>
#### What the model sees      ← verbatim prompt text, quoted from source
#### Token effect             ← fixed / conditional / retained / capped / zero
#### KV Cache effect          ← append-only / prefix-stable / replacing / independent
## Known Limitations and Deferred Work
```

A package with nothing to declare must use one of the audited sentences
(`None, as …` / `Indirectly, through …`) — it cannot simply omit the
section. This is the only instance in this collection of a repository
treating "what does this component cost the model, in tokens and in cache
invalidation" as a **required, gated, per-component disclosure**.

### 5. Agent Notes: decision memory with a lifecycle and a format gate

`.agents/notes/{proposed,implemented,rejected,archived}/{class}/yyyy-mm-dd-topic.md`,
where both axes are encoded in the path and a note *moves between folders*
as its status changes. Non-trivial changes MUST add or update one in the
same PR. `verify-agent-note-format` enforces the header block and the
per-lifecycle body skeleton — and rejects `## Proposal`, `## Plan`,
`## Migration plan`, `## Acceptance criteria` inside an `implemented/`
note, because an implemented note describes what *is*.

`## Alternatives considered` is **mandatory**: "A decision recorded
without what it beat invites re-litigation — the failure Agent Notes
exist to prevent." Notes predating the format carry an exact machine-read
comment admitting their alternatives are not reconstructible, rather than
having plausible ones invented for them.

Archived notes are **frozen**: sealed triplets (English, Chinese,
sidecar) that gates skip and prose may not modernize, with an append-only
content manifest. The skills that touch prose all carry the same
exclusion — `.agents/notes/archived/` is never edited, only cited.

## What travels, and what doesn't

This repo's process apparatus is unusually heavy, and most of it is a
consequence of *its* constraints rather than a transferable idea. Sorting
it, since the temptation on reading a source this disciplined is to copy
the discipline rather than the reasoning:

**Travels.** Adoption proven from the tree rather than the thread; the
"omit what a green gate already enforces" scope rule; rewriting a
criteria document wholesale instead of appending to it; the
negative-control rule for regression guards; treating review comments as
untrusted input; the inverse API-bloat check; and "alternatives are
recorded, never invented." Each is a rule you can apply on day one with
no infrastructure behind it. Where these landed in this collection's own
design work is recorded in [`../agent-design/`](../agent-design) —
`future.md` for the maintenance loop, `formats.md`/`review.md`/
`system-prompts.md` for the rest.

**Doesn't travel.**

- **Per-file 100% coverage as a merge gate.** DeepSeek runs it *and*
  writes down that it proves nothing ("coverage is necessary but not
  evidence that the scenario is correct"). The second half is the
  transferable part; the first is a policy choice for a repo with a
  full-time gate budget.
- **The bilingual apparatus.** Paired `.zh.md` files, pairing hashes, a
  translation-pairing gate, and the rule that "a green pairing hash does
  not prove translation quality." Real engineering, entirely downstream
  of shipping bilingual docs.
- **Everything-is-a-plugin.** The composability is genuine; the cost is
  a vendored DI framework and 44 subsystem reference pages.
- **The eleven-tier doc taxonomy and word budgets.** The idea underneath
  — one home per fact, link everywhere else — is worth having as a
  habit. The gate enforcing it is for a repo with 2,300 markdown files.
- **The Agent Note lifecycle in full.** Lifecycle folders, a format gate
  per folder, frozen archive triplets with a content manifest. Two rules
  from it survive extraction on their own (see
  `../agent-memory-learning.md` §9): a record is superseded rather than
  edited into a different decision, and alternatives are recorded rather
  than invented.
- **The maintenance tool's single-operator, out-of-repo home.** Its own
  Risks section names the cost — "single-maintainer bus factor… its
  interruption stops skill maintenance entirely." The reasoning behind
  it (repo overhead exceeds the value for one skill, one maintainer) is
  narrow and does not generalize.

## Reading the snapshots as prompt text

Both prompt files are **test expectations**, re-recorded by
`pnpm run test:snapshot:record`. That is itself the finding: the repo's
testing policy states that every non-trivial model-visible behavior
change "adds or updates a keyless snapshot through a real runnable
example in the same PR," and `AGENTS.md` carries the rule as
**"Model-visible ⟺ logged"** — anything reaching a model request must be
reconstructable from the session log. Prompt wording is treated as
behavior under test, not as configuration.

Note the literal `{{cwd}}` in both files: the persona is a template
interpolated strictly against registered variables at render time, and
the snapshot is recorded before interpolation of that one field. The
harness identity (`You are an AI agent powered by DeepSeek Harness.`) is
a fixed order-−100 opener; the persona is order 0; tool guidance occupies
orders 100–199.
