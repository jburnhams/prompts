# Worked examples of the review payloads

Concrete, end-to-end instances of every payload `review.md` specifies,
all drawn from **one fictional scenario** so the same code can be
followed from first review through re-review to a comment-driven fix
run. Everything here — repository, people, code, SHAs, ids — is
invented for illustration.

## The scenario

Repository `acme/billing-service` (Bitbucket, Python). Dana opens PR
#87, "PROJ-982: Retry invoice dispatch on gateway errors": a new
`billing/retry.py` helper, `billing/dispatch.py` rewired to use it,
and a small test file. Before Forge's first review, a human reviewer
(Bob) has already opened one inline thread about payload logging.

The seeded defect: `send_with_retry` iterates
`for attempt in range(1, max_attempts)` — one fewer attempt than
configured, and with `max_attempts=1` the loop never runs and
`raise last_exc` raises `None` (a `TypeError`). The author's own
exhaustion test doesn't assert the attempt count, so CI passes.

## The files

| File | Payload | `review.md` § |
|---|---|---|
| `review-envelope-initial.md` | The complete task envelope for the first review session | §2, §3 |
| `specialist-brief-bugs.md` | The exact `Task` prompt the orchestrator sends the `bugs` specialist | §4 |
| `validator-brief.md` | The exact `Task` prompt validating one candidate finding | §5 |
| `review-envelope-rereview.md` | The envelope for the second session, after a new push and a reply (phase 2) | §6 |
| `responder-envelope.md` | A comment-responder coding run's envelope on a different, Forge-authored PR | review.md §8, `medium.md` §1c |

## How the first session plays out (for orientation)

- The `bugs` specialist returns two candidates: **f-1**, the
  `range(1, max_attempts)` off-by-one/`raise None` defect (validator
  **confirms** — it re-reads `billing/retry.py` at head and the test
  file, and notes the test gap), and **f-2**, "the exception type
  seen by `dispatch()` callers changed from `RuntimeError` to
  `TransportError`, breaking existing handlers" (validator **rejects**
  after a Grep across the tree finds no caller catching
  `RuntimeError` — the type change has no observable effect in this
  codebase).
- The `security` specialist flags the new
  `logger.info(... payload=%r ...)` line as logging cardholder data —
  **deduplicated** at pipeline step 4 against Bob's open thread
  `t-301`, which already says exactly this; it is never validated and
  appears in the report's `filtered` list with the dedup reason.
- The `conventions` specialist is skipped: the repo has no
  project-conventions file.
- One comment posts: f-1, anchored to `billing/retry.py:20`, with a
  single-line committable suggestion
  (`for attempt in range(1, max_attempts + 1):`) — committable because
  applying it verbatim fully resolves the issue.

Between sessions, Dana pushes `6b1d94efc2a3`: applies the suggestion,
trims Bob's logged payload, moves JSON parsing inside the retried
call, and broadens the retry to also catch `ValueError`. The second
session's envelope (`review-envelope-rereview.md`) shows the state
tag, the interdiff, and the reply on Forge's thread; its
reconciliation confirms f-1 fixed (reply + resolve), leaves Bob's
thread to Bob, and its scoped specialists raise the new **f-3**:
retrying on `ValueError` after a successful POST re-sends a
non-idempotent invoice dispatch.

## Reading notes

- Wire content sits inside fenced blocks. A line of the form
  `{{ … example truncation … }}` is **this document set eliding for
  readability** — it is never part of the wire format. The format's
  own, real elision markers look like
  `[hunks elided: … matched generated-file pattern …]` and are
  specified in `review.md` §2.
- Line numbers in the diffs are internally consistent — the findings'
  anchors can be checked against the hunks by hand, which is the point
  of the exercise.
