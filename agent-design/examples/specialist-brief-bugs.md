# Example: specialist brief (`bugs` role)

The exact `Task` call the review orchestrator makes in pipeline step 3
for the `bugs` lens, against the PR in
`review-envelope-initial.md`. The specialist's instructions and output
schema live in its system prompt (`system-prompts.md` §4); the brief
carries only data, assembled by verbatim transclusion (`review.md` §4).

```json
{
  "subagent_type": "reviewer",
  "role": "bugs",
  "description": "Bugs review of PR #87",
  "prompt": "<pr>\n…\n</pr>\n\n<description>\n…\n</description>\n\n<diff>\n…\n</diff>\n\n<existing_comments>\n…\n</existing_comments>\n\n<focus>\n…\n</focus>"
}
```

With the `prompt` string unpacked (this is the full text; the fenced
block below is what the specialist model actually receives after its
system prompt):

```
<pr>
  Platform: bitbucket
  Repository: acme/billing-service
  PR: #87
  Title: PROJ-982: Retry invoice dispatch on gateway errors
  Author: dana
  Branch: PROJ-982-dispatch-retry -> main
  Head SHA: 9f3c2abe41d7
  Base SHA: 2c86e11baf04
  State: OPEN
  Snapshot: 2026-07-20T09:14:00Z
  Additions: 65  Deletions: 7  Changed files: 3
</pr>

<description>
Gateway 5xx blips currently fail invoice dispatch outright (see
PROJ-982). This adds a small retry helper with exponential backoff and
uses it in `InvoiceDispatcher.dispatch`. Only transport-level errors
are retried; client errors still fail immediately.
</description>

<diff>
{{ … example truncation: the envelope's <diff> contents, byte-for-byte
   identical to review-envelope-initial.md's <diff> block — on the
   wire this is always the verbatim text, never a summary … }}
</diff>

<existing_comments>
  <general>
    [c-5109 | dana at 2026-07-19T16:41:00Z]: Follow-up to last week's
    dispatch timeout incident — context in PROJ-982.
  </general>
  <thread id="t-301" anchor="billing/dispatch.py:25" status="open">
    [c-5117 | bob at 2026-07-19T17:03:00Z]: We got burned logging whole
    invoice payloads at INFO before — this includes cardholder name and
    address. Can we log just the invoice id here?
  </thread>
</existing_comments>

<focus>
The description says only transport-level errors are retried and that
behavior is otherwise unchanged. Pay attention to whether the retry
helper actually delivers the configured number of attempts and whether
the rewiring of dispatch() preserves the old success and failure
behavior.
</focus>
```

Things to notice:

- The orchestrator wrote only `<focus>` — two sentences of direction
  derived from the description, no restatement of any diff content
  (`review.md` §4 rule 1).
- The `<existing_comments>` block is transcluded verbatim as intent
  context, governed by the discussion rules (§4 rule 2): Bob's thread
  is the record of what a human already asked for, not a verdict and
  not a skip list. The `security` specialist's brief is identical, and
  it still raises its payload-logging candidate *despite* Bob's thread
  covering it — raising is its job; the orchestrator's dedup then
  drops the candidate with a recorded reason. Had the diff instead
  contained something a thread explicitly requested, flagging it would
  demand a concrete defect and a rationale that names the thread.
- **Absent on purpose** (§4 rule 3): any `<conventions>` tag (this
  repo has none; the conventions specialist wasn't even launched), and
  the other specialists' output.
- The specialist works from this brief plus Read/Grep/Glob against the
  working tree at `9f3c2abe41d7`. For candidate f-1 it Reads
  `billing/retry.py` to confirm line 20 carries
  `for attempt in range(1, max_attempts):` — the numbered Read output
  is the ground truth its finding's `line` field must match, not hunk
  arithmetic (§1).
- Its return value is a JSON list of candidate findings per
  `formats.md` §4, `validated: null` — e.g. f-1:

```json
{
  "role": "bugs",
  "file": "billing/retry.py",
  "line": 20,
  "line_end": 20,
  "severity": "high",
  "summary": "send_with_retry makes one fewer attempt than max_attempts, and raises None when max_attempts=1",
  "rationale": "range(1, max_attempts) iterates max_attempts-1 times, so the configured attempt budget is never delivered (max_attempts=3 yields 2 calls). With max_attempts=1 the loop body never runs, last_exc stays None, and `raise last_exc` at line 29 raises TypeError instead of a TransportError. tests/test_retry.py never asserts call counts, so both cases pass CI.",
  "suggested_fix": "for attempt in range(1, max_attempts + 1):",
  "validated": null,
  "validator_note": null
}
```
