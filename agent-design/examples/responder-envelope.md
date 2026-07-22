# Example: comment-responder run envelope

A **coding-entrypoint** envelope, not a review one — the
`source: pr_comments` responder run from `medium.md` §1c, shown here
because it consumes the review side's thread model verbatim
(`review.md` §8: one thread format everywhere, nothing translates).

Scenario: PR #91 on the same repo was authored by Forge itself (a
`mode: implement` run on ticket PROJ-990, committed/pushed and opened
as a PR by the external process, as always). A human reviewer, Carol,
left two inline comments. The harness — having checked Carol is on the
configured reviewer allowlist (§1c's gate) — dispatches this run on
the PR's branch, which is already checked out.

```
<task>
  <mode>implement</mode>
  <source>pr_comments</source>
  <issue_key>PROJ-990</issue_key>
  <repository>acme/billing-service</repository>
  <base_branch>main</base_branch>
  <target_branch>PROJ-990-reconciliation-export</target_branch>
</task>

<pull_request>
  Platform: bitbucket
  Repository: acme/billing-service
  PR: #91
  Title: PROJ-990: Nightly reconciliation export
  Author: forge-bot
  Branch: PROJ-990-reconciliation-export -> main
  Head SHA: c41a77d09be2
  Base SHA: 5d02e93aa118
  State: OPEN
  Snapshot: 2026-07-21T14:37:00Z
  Additions: 210  Deletions: 4  Changed files: 5
</pull_request>

<description>
{{ … example truncation: the PR body, verbatim … }}
</description>

<existing_comments>
  <thread id="t-512" anchor="billing/export.py:57" status="open">
    [c-6301 | carol at 2026-07-21T14:02:00Z]: This loads the whole
    ledger into memory before writing. Month-end that's ~2M rows —
    please stream it (the ledger client has iter_rows()).
  </thread>
  <thread id="t-513" anchor="billing/export.py:24" status="open">
    [c-6304 | carol at 2026-07-21T14:05:00Z]: Naming nit: `do_export`
    → `export_ledger`, to match the other public entry points in this
    module.
  </thread>
</existing_comments>
```

Notes:

- The thread block is `review.md` §3's format, filtered to **open
  threads only** — a responder run acts on live requests; settled
  history would just be noise. Resolved/outdated threads aren't
  carried at all here (unlike review envelopes, which need them for
  dedup context).
- No `<diff>` tag: this is an implement-mode run with `Bash` — it
  inspects its own branch with read-only git as needed, per the normal
  coding workflow. The pre-baked-diff guarantee exists for review
  mode's unsupervised *anchoring* problem, which a responder run
  doesn't have (it replies to existing threads by `in_reply_to`, never
  by fresh anchor).
- `AddComment` is wired in this run source (the §1c exception), scoped
  by prompt to threaded replies on the envelope's thread ids. The run
  makes both changes in the working tree, runs the tests, and replies
  on `t-512` and `t-513` with what it changed (one reply each, no
  progress narration — `review.md` §8's etiquette rule). If it judged
  a request wrong or out of scope, it would reply once saying why and
  leave the thread open; contradictory reviewer asks route to
  `AskUser` as usual.
- Its Complete report maps each thread to an outcome, mirroring the
  fix-run contract in `medium.md` §1b — nothing silently disappears.
- The loop then closes without ceremony: the external process commits
  and pushes the tree, the head moves, and the *next review session*
  of PR #91 sees Carol's threads answered and the changes in its
  interdiff (`review.md` §8).
