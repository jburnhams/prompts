# Devin AI

- **Type**: Autonomous coding agent · **Vendor**: Cognition
- **Status**: closed source (leaked)
- **Mirror source**: https://github.com/x1xhlol/system-prompts-and-models-of-ai-tools/tree/main/Devin%20AI (2026-07-10)

## Files
- `Prompt.txt` — main agent system prompt.
- `DeepWiki Prompt.txt` — prompt for Devin's DeepWiki (repo documentation
  generation) feature.

## Self-verification and testing

See [`agent-self-verification.md`](../../agent-self-verification.md) for
the cross-source comparison this feeds into. Prompted-only (§7 there) —
no code-level enforcement is visible in this captured text — but denser
and more deliberately structured than most §7 examples, because
verification is wired into a *mandatory reflection tool call* rather
than scattered as free-floating prose.

- **Shared SWE-bench-lineage echo**: "When struggling to pass tests,
  never modify the tests themselves, unless your task explicitly asks
  you to modify the tests. Always first consider that the root cause
  might be in the code you are testing rather than the test itself" —
  the same "don't touch the tests" instruction the §1 workflow-template
  comparison documents for SWE-agent/mini-swe-agent/Augment, here
  appearing independently in a fully-autonomous product rather than a
  benchmark harness.
- **A mandatory pre-completion checkpoint, not just an instruction**:
  the `<think>` scratchpad tool has a list of required (not merely
  suggested) triggers, one of which gates completion directly: "Before
  reporting completion to the user. You must critically ex[a]mine your
  work so far and ensure that you completely fulfilled the user's
  request and intent. Make sure you completed all verification steps
  that were expected of you, such as linting and/or testing... verify
  that you successfully edited all relevant locations before telling
  the user that you're done." This sits between §6 (per-action) and §7
  (prompted-only): it's per-*critical-decision* rather than per-write,
  and what's enforced is that the tool gets called, not that its
  content is actually a correct self-check — the checkpoint is formal,
  the verification inside it is not code-checked.
  A second mandatory trigger covers what to do after a failed check:
  "if tests, lint, or CI failed and you need to decide what to do about
  it... it's better to first take a step back and think big picture...
  rather than diving directly into modifying code."
- **A bounded-retry rule on CI failure**, the same shape as a linter-fix
  cap elsewhere in this collection: "When iterating on getting CI to
  pass, ask the user for help if CI does not pass after the third
  attempt" — a numeric cap, but counting/enforcement is left entirely to
  the model's own turn-tracking.
- **`gh_pr_checklist`, worth distinguishing from self-verification**: a
  tool for tracking whether *human reviewer* comments on an already-open
  PR have been addressed — the inverse of this doc's §4 conflation trap
  (Devin isn't reviewing someone else's code; it's tracking whether
  someone else's review of *its* code got addressed). Not self-check of
  the agent's own initial work, so it doesn't count toward §1-§6 despite
  the "checklist" framing.
- **`DeepWiki Prompt.txt`** doesn't apply here at all — it's a read-only
  documentation/citation-generation feature (mandatory per-sentence
  `<cite>` tags) with no edit tools, so "checking its own code" isn't a
  meaningful question for that prompt.
