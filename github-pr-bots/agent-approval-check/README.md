# Agent approval check and the PR stamp sweep (Anthropic)

- **Type**: Two merge-side pieces, not a reviewer: a deterministic
  required-status gate for agent-authored PRs, and a two-pass agent workflow
  that decides which PRs a maintainer can approve with little discussion
- **License**: MIT (both live in `anthropics/claude-code-action`)
- **Source**: https://github.com/anthropics/claude-code-action —
  `agent-approval-check/` (added 2026-06-30, #1429) and
  `.claude/workflows/pr-stamp-sweep.js` (added 2026-06-11, #1409)
- **Retrieved from**: `main` at `f27be6b` (2026-10-16), read 2026-10-17

Not found in the 2026-07-10 pass of this folder. That pass read only
`src/create-prompt/`, `src/github/data/formatter.ts` and
`src/github/utils/sanitizer.ts`, so both pieces were missed rather than
absent. They matter here because they are the open-source half of what
Anthropic's [code-review post][post] describes: **who has to approve, and
how many**, as distinct from what the reviewer found.

## Files

- `README-orig.md` — the action's own README, verbatim: inputs, the
  `/approve <sha>` flow, and the threat model.
- `pr-stamp-sweep.js` — the workflow script, verbatim. Both prompts and
  both JSON schemas are inline.
- The Python implementation (`agent_approval_check.py`, 1,828 lines) is not
  copied. Its behaviour is fully described by the README, and the points
  below were checked against the commit history.

## `agent-approval-check`: the gate

The commit message calls it "a sanitized port of the check Anthropic runs
internally on every agent-authored PR — same detection rules, /approve
<sha> comment flow, sibling-PR-same-SHA guard, and fail-closed semantics,
with the Anthropic-specific path exemptions and kill-switch removed".

- **What triggers it is authorship, not content.** A PR needs
  `required_approvals` (default **2**) distinct human approvals if any
  commit has an agent committer email, the PR author is an agent login, or
  an agent submitted an `APPROVED` review. A PR with no agent activity
  passes immediately. This is the opposite axis from the risk tiers in the
  post, which are set "based on the change, not the author". The two
  compose: authorship decides whether the gate applies, and content (the
  stripped-out path exemptions, here only `exempt_path_prefixes`) lowers
  it.
- **Approvals are bound to a SHA.** A human counts either with a native
  Approve review or by commenting `/approve <head-sha>`. A push moves the
  head, so older `/approve` comments are flagged stale. This lets the PR
  author vouch for commits an agent pushed for them, which GitHub's UI
  can't, but the author counts once and only with verified write access.
- **Agents never count.** Agent logins and `excluded_approvers` are
  dropped from the count. This is the post's "an agent's approval never
  counts as a human's", enforced in code.
- **Fail-closed, with two non-obvious guards.** Any unhandled error leaves
  the status non-success. A PR with more than 100 commits is treated as
  agent-authored because its full commit list can't be verified. And
  because commit statuses attach to a SHA rather than a PR, `success` is
  withheld while another open PR to a protected base shares the same head
  (the *sibling-PR guard*). Otherwise a green status earned on one PR would
  unblock another.
- **Tamper resistance comes from the trigger choice.** It runs on
  `pull_request_target` and `issue_comment`, which execute the workflow
  from the base branch. It deliberately omits `pull_request_review`,
  because that event runs from the merge ref. `config_file` must be read
  from a base checkout. `exempt_head_branches` carries a warning that
  branch names are attacker-controlled. Same reasoning as Forge's
  base-SHA rule for conventions files ([`context-files.md`] §5).

## `pr-stamp-sweep`: the attention triage, as two agents

A Claude Code workflow script (`meta` + `pipeline(prs, review, verify)`)
for a maintainer clearing a queue of mostly external PRs.

1. **Review, one agent per PR.** It reads a pre-fetched dossier (metadata,
   body, existing reviews and comments, full diff). The script notes that
   sandboxed agents "can't reliably call gh themselves". The agent also
   reads the touched source in a local checkout to verify the diff's
   claims. It returns `verdict: stamp | needs-discussion | skip`, plus
   `category`, `behaviorChange` (or `"none"`), `concerns`,
   `securitySensitive` and `duplicateOf`. "Stamp" requires all five of:
   small and does exactly what it says; no major behaviour change;
   verified correct against current source; no security concern (with an
   explicit checklist); and doesn't break the public action API.
   `securitySensitive` is defined by **what the change touches** ("auth,
   sanitization, parsers of untrusted input, actor checks, file restore,
   or shell construction"), not by what was found.
2. **Verify, only for stamp candidates.** An "adversarial security
   skeptic" is told the first reviewer recommended approval and that its
   job is "to REFUTE that recommendation". It is told to lean towards
   reporting when uncertain. It returns `safeToStamp`, `findings` and
   `confidence`. A stamp the verifier rejects is **demoted**, not dropped:
   the output has four buckets, `stamped / demoted / discuss / skipped`.

Two things to take from it:

- **The verifier is asymmetric.** It runs only on the "less attention"
  recommendation, the one whose error is expensive. Nothing re-checks a
  `skip` or a `needs-discussion`, because sending a PR to a human is
  already the safe direction. This is the escalate-only principle applied
  to agent effort rather than to a tier.
- **The prompt names the repo's own risk surface.** "Treat any change
  touching content sanitization, actor/bot allowlists, config restoration,
  prompt construction, or shell command construction as high-risk." This
  is a per-repo sensitive-path list written as prose, the same idea as the
  medium-tier examples in the post (caching, the auto-updater, system
  prompts).

[post]: https://claude.dev/blog/solving-code-review-at-anthropic/
[`context-files.md`]: ../../agent-design/context-files.md
