# Factory (Droid)

- **Type**: Coding agent (CLI, "Droid") · **Vendor**: Factory
- **Status**: closed source (leaked)
- **Mirror source**: https://gist.github.com/AshikNesin/8c5b16f4f50734d1413bce4002223e22
  — a re-post of an extraction originally obtained/publicized by the
  jailbreak researcher "Pliny the Liberator." Retrieved 2026-07-10.
- **Not from the x1xhlol aggregator** — Factory/Droid isn't in that repo,
  this came from a separate gist.

The prompt itself contains tells of how it was extracted: it addresses the
user as "Elder Plinius" and is dated "Sunday, September 28, 2025" inside
the prompt text, suggesting this is a snapshot from that specific session
rather than an evergreen system prompt.

## Files
- `factory-droid-prompt.md` — extracted system prompt (role, behavior
  rules, tool-use guidance).

## Self-verification and testing

See [`agent-self-verification.md`](../../agent-self-verification.md) for
the cross-source comparison this feeds into. Prompted-only (§7 there —
only the system prompt was captured, so no code-level enforcement can be
confirmed either way), but the most elaborate and most gate-*shaped*
instance of that bucket found anywhere in this collection: it's written
in categorical MANDATORY/BLOCKING checklist language and — distinctively
— ties the check to an external, human-visible repo artifact rather
than to an internal "done" signal.

- **"CODE QUALITY VALIDATION (MANDATORY, BLOCKING)"**: "Required checks
  (use project-specific scripts/configs): Static analysis/linting...
  Type checking... Tests... Build verification... Run these checks.
  **Fix failures and iterate until all are green**; include concise
  evidence."
- **The check is wired to PR draft/non-draft status, not to a chat-level
  completion tool** — a mechanic not seen elsewhere in this collection:
  "Create a non-draft PR ONLY when: Dependencies successfully installed
  (frozen/locked) with evidence; All code quality checks green with
  evidence; Clean worktree except intended changes. If any item is
  missing, do NOT create a non-draft PR." Draft PRs are permitted only
  as an explicit, documented exception: "only if the user explicitly
  instructs you to open a draft despite blockers." Worth naming as its
  own pattern — a **prompt-simulated deterministic gate, externalized
  to PR state** — since it borrows the checklist shape of a §2
  deterministic gate while remaining, as far as this single captured
  file shows, purely textual.
- **A separate, narrower per-action check for a different concern**
  (content safety before every commit, not correctness): "Before ANY
  git commit or push operation: Run 'git diff --cached' to review ALL
  changes being committed... Examine the diff for secrets, credentials,
  API keys, or sensitive data... if detected, STOP and warn the user."
  Per-action in cadence like §6, but scoped to secret-leak prevention
  rather than a self-check that the code is correct — closer to this
  doc's §8 "adjacent-but-different" family.
- **A pre-work gate, not a post-work one**: a "Strict tool guard" blocks
  file-viewing tools on source files until git sync and a locked
  dependency install both succeed — validation happens before editing
  is even allowed, the mirror image of every other mechanism in this
  doc (which all gate *finishing*, not *starting*).
- **Partial overlap with, but not a match for, §1's SWE-bench-lineage
  template**: shares the "run tests/lint/build as a blocking check"
  spirit but has no reproduce-script mechanic and no explicit
  "consider edge cases" step — closer to just the verification tail of
  that workflow than the full reproduce → fix → verify → submit shape.

## Compaction and turn output

See [`agent-context-compaction.md`](../../agent-context-compaction.md)
and [`agent-turn-output.md`](../../agent-turn-output.md) for the
cross-source comparisons these feed into. Nothing found for either
topic across the full 334-line prompt — no context-window/token-budget
language, no handoff/resume concept, no title/session-name field or
generation logic. This prompt is entirely oriented around a single
bounded implementation-or-diagnostic task ending in a PR (Phase 0 →
Phase 1 → Phase 2A/2B), so it's plausible compaction is structurally
less relevant to this product's per-task design than to a long-lived
interactive session — but that's an inference from the prompt's shape,
not a confirmed finding; this is a single system-prompt extraction with
no orchestration code, so a genuine absence can't be confirmed either
way.

- **Two prompted-narration rules touch turn-output territory without
  being reasoning-display mechanisms**: "if there is no real need to
  use tools, then the LLM response should only contain the non-empty
  text part and should not include any tool calls," and "Output text
  to communicate with the user; all text outside of tool use is
  displayed to the user. Only use tools to complete tasks, not to
  communicate with the user." Both are ordinary output-shape/
  communication-style instructions (already this collection's
  `coding-agent-approaches.md` territory), not a native
  thinking/reasoning content-block mechanism.
- No thinking/reasoning-visibility language of any kind was found.
