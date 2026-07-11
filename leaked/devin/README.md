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

## Compaction and turn output

See [`agent-context-compaction.md`](../../agent-context-compaction.md)
and [`agent-turn-output.md`](../../agent-turn-output.md) for the
cross-source comparisons these feed into.

- **Compaction — confirmed absent**, via a full read plus targeted
  grep across the whole 402-line prompt (`summar`/`compact`/`context
  window`/`token limit`/`truncat`/`conversation history`/`handoff`/
  `memory`/`session`). The only hits are unrelated shell/search-output
  truncation ("Long shell outputs will be truncated and written to a
  file"). `DeepWiki Prompt.txt`'s `<budget:token_budget>200000` is a
  token budget for that separate read-only Q&A feature's own answer
  generation, not agent-context management. The prompt reads as a
  complete, coherent document with no missing-section markers, so this
  looks like a genuine absence in what leaked, not a partial extraction.
- **Title generation — not captured.** No session/conversation-naming
  instruction anywhere; the only naming convention present is for git
  branches (`devin/{timestamp}-{feature-name}`). Devin's product UI
  visibly shows session names, so this plausibly happens server-side,
  outside what a client-facing system prompt would carry.
- **Reasoning display — a genuinely novel mechanism, worth reading in
  full.** The `<think>` tool (see the self-verification section above
  for its role as a completion-gate) is structurally distinct from
  everything else surveyed in `agent-turn-output.md`: "Freely describe
  and reflect on what you know so far... **The user will not see any of
  your thoughts here**, so you can think freely." Three properties make
  it a third category, not a fit for the doc's existing native-block-
  vs-prompted-narration split:
  - **Categorically hidden, not a visibility default the user can
    flip** — every other "hidden by default" source in the turn-output
    doc's comparison is a toggle on native reasoning content; Devin's
    prompt frames invisibility as structural to the tool itself, with
    no visibility setting described.
  - **Mandatory at named checkpoints, not just available** — a numbered
    "you must use the think tool" list with three required triggers
    (one of which is the pre-completion verification checkpoint already
    documented in Self-verification above), plus ten more "should use"
    situations.
  - **A prompted tool call, not a native reasoning API block** — no
    evidence of `reasoning_effort`/`thinking`-style API parameters
    anywhere in the prompt, and it's visibly distinct from ordinary
    narration (which goes through a separate `<message_user>` command).
  This is the same "private scratchpad, visible output" shape this
  collection's compaction doc documents for *summarization-specific*
  internal tags elsewhere (Gemini CLI, Claude Code) — Devin is the one
  source found so far generalizing that shape to ordinary turn-by-turn
  reasoning across an entire task, not just at compaction time, and
  coupling it directly to self-verification (the same tool call serves
  both purposes).

## Permissions and approval

See [`agent-permissions-approval.md`](../../agent-permissions-approval.md)
for the cross-source comparison this feeds into. **The cleanest
confirmation in this collection that a background-autonomous agent can
have zero command-approval infrastructure at all.** No named modes, no
risk flag, no allow/deny list, no config file anywhere in the 402-line
prompt — the `<shell>` tool's description covers only output formatting
(multi-line `&&`, bracketed paste mode, truncation to a file), never a
safety qualifier. "Permission" appears exactly twice, and neither is
about command execution: once about *requesting credentials* from the
user, once about getting consent before *external communications with
third parties* — not about running shell commands.

- **What replaces per-command approval is a reflection checkpoint, not
  a gate**: the `<think>` tool is a mandatory pause-and-reason step
  before consequential decisions (see the Turn-output section above for
  its full detail) — an internal self-check, not an external approval
  request. There's no human in the loop for the action itself.
- **Safety is enforced by absolute prohibitions instead of conditional
  risk judgment**: "Never force push, instead ask the user for help if
  your push fails," "Never use `git add .`; instead be careful to only
  add the files that you actually want to commit." Hard rules baked
  into the prompt, not a per-instance safe/unsafe classification.
- **A notify-and-continue pattern substitutes for a blocking pause**:
  `<report_environment_issue>` — "Use this to report issues with your
  dev environment as a reminder to the user... It is critical that you
  use this command whenever you encounter an environment issue so the
  user understands what is happening" — Devin is told to keep working
  around the issue rather than stop and wait for a response.
- No sandbox/isolation is invoked as a safety rationale — Devin
  operates on "a real computer operating system" (presumably an
  isolated cloud VM per task, by product design) but the prompt never
  points to that isolation as a reason approval can be skipped; it
  simply isn't discussed as a safety layer.
