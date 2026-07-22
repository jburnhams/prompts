# Example: re-review envelope (phase 2 session)

The envelope for the **second** review session of PR #87, after Dana's
follow-up push. Everything from the initial envelope is still present
(refreshed to the new snapshot); the session machinery appears as the
two additive tags `<review_state>` and `<incremental_diff>`
(`review.md` §6a). Between sessions:

- Dana pushed `6b1d94efc2a3`: applied Forge's committable suggestion
  on `billing/retry.py:20`, trimmed the payload out of the dispatch
  log line (Bob's thread), moved JSON parsing inside the retried call,
  and broadened the retry clause to `except (TransportError,
  ValueError)`.
- Dana replied on Forge's thread.

```
<pull_request>
  Platform: bitbucket
  Repository: acme/billing-service
  PR: #87
  Title: PROJ-982: Retry invoice dispatch on gateway errors
  Author: dana
  Branch: PROJ-982-dispatch-retry -> main
  Head SHA: 6b1d94efc2a3
  Base SHA: 2c86e11baf04
  State: OPEN
  Snapshot: 2026-07-21T08:02:00Z
  Additions: 64  Deletions: 7  Changed files: 3
</pull_request>

<description>
{{ … example truncation: unchanged from the initial envelope … }}
</description>

<changed_files>
- billing/dispatch.py (modified) +17/-7
- billing/retry.py (added) +29/-0
- tests/test_retry.py (added) +18/-0
</changed_files>

<diff>
{{ … example truncation: the full merge-base diff 2c86e11baf04 →
   6b1d94efc2a3, same §2 construction as the initial example with the
   round-2 changes folded in. Shown here for the one file both
   sessions' findings anchor to: … }}
diff --git a/billing/retry.py b/billing/retry.py
new file mode 100644
index 0000000..77b2a10
--- /dev/null
+++ b/billing/retry.py
@@ -0,0 +1,29 @@
+"""Retry helpers for outbound gateway calls."""
+
+import logging
+import time
+
+logger = logging.getLogger(__name__)
+
+
+class TransportError(Exception):
+    """Raised when the invoice gateway rejects or drops a request."""
+
+
+def send_with_retry(send, *args, max_attempts=3, base_delay=0.5, **kwargs):
+    """Call ``send`` until it succeeds or ``max_attempts`` is exhausted.
+
+    Retries only on TransportError; any other exception propagates
+    immediately. The delay doubles after each failed attempt.
+    """
+    last_exc = None
+    for attempt in range(1, max_attempts + 1):
+        try:
+            return send(*args, **kwargs)
+        except (TransportError, ValueError) as exc:
+            last_exc = exc
+            logger.warning(
+                "dispatch attempt %d/%d failed: %s", attempt, max_attempts, exc
+            )
+            time.sleep(base_delay * 2 ** (attempt - 1))
+    raise last_exc
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
    [c-5218 | reply | dana at 2026-07-21T07:48:00Z]: Trimmed to the
    invoice id only in 6b1d94e.
  </thread>
  <thread id="t-388" anchor="billing/retry.py:20" status="open">
    [c-5201 | forge-bot at 2026-07-20T09:31:00Z]: **High**:
    `send_with_retry` makes one fewer attempt than `max_attempts`
    (`range(1, max_attempts)` iterates `max_attempts - 1` times), and
    with `max_attempts=1` the loop never runs, so `raise last_exc`
    raises `None` (TypeError). The exhaustion test doesn't assert call
    counts, so CI passes both cases.
    ```suggestion
    for attempt in range(1, max_attempts + 1):
    ```
    [c-5214 | reply | dana at 2026-07-21T07:51:00Z]: Applied the
    suggestion — good catch, the exhaustion test didn't assert call
    counts so it slipped through.
  </thread>
</existing_comments>

<review_state rebased="false">
  <previous_session at="2026-07-20T09:31:00Z" head_sha="9f3c2abe41d7">
    <posted_finding id="f-1" thread="t-388" file="billing/retry.py"
        line="20" severity="high" status="open">
      send_with_retry makes one fewer attempt than max_attempts, and
      raises None when max_attempts=1
    </posted_finding>
  </previous_session>
</review_state>

<incremental_diff base="9f3c2abe41d7">
diff --git a/billing/dispatch.py b/billing/dispatch.py
index b7a90c4..e02c551 100644
--- a/billing/dispatch.py
+++ b/billing/dispatch.py
@@ -20,21 +20,20 @@ class InvoiceDispatcher:
     def _headers(self):
         return {"Authorization": f"Bearer {self._token}"}
 
     def dispatch(self, invoice):
         payload = invoice.to_wire()
-        logger.info("dispatching invoice %s payload=%r", invoice.id, payload)
-        response = send_with_retry(
+        logger.info("dispatching invoice %s", invoice.id)
+        return send_with_retry(
             self._post_once,
             payload,
             max_attempts=3,
         )
-        return response.json()["dispatch_id"]
 
     def _post_once(self, payload):
         response = self._session.post(
             self._endpoint, json=payload, headers=self._headers(), timeout=10
         )
         if response.status_code >= 500:
             raise TransportError(f"gateway 5xx: {response.status_code}")
         response.raise_for_status()
-        return response
+        return response.json()["dispatch_id"]
diff --git a/billing/retry.py b/billing/retry.py
index 3e1c9d2..77b2a10 100644
--- a/billing/retry.py
+++ b/billing/retry.py
@@ -15,14 +15,14 @@ def send_with_retry(send, *args, max_attempts=3, base_delay=0.5, **kwargs):
 
     Retries only on TransportError; any other exception propagates
     immediately. The delay doubles after each failed attempt.
     """
     last_exc = None
-    for attempt in range(1, max_attempts):
+    for attempt in range(1, max_attempts + 1):
         try:
             return send(*args, **kwargs)
-        except TransportError as exc:
+        except (TransportError, ValueError) as exc:
             last_exc = exc
             logger.warning(
                 "dispatch attempt %d/%d failed: %s", attempt, max_attempts, exc
             )
</incremental_diff>
```

## How the session consumes this

**Reconciliation (pipeline step 3½)** — one open Forge thread,
`t-388`, and its anchored code appears in the interdiff, so a
resolution check dispatches (`review.md` §5's variant: the f-1
finding, the thread, and the interdiff, asking "did the changes since
`9f3c2abe41d7` fix this?"). It confirms — line 20 now reads
`range(1, max_attempts + 1)`, delivering `max_attempts` calls and
guaranteeing `last_exc` is set on exhaustion. Forge replies on `t-388`
("Verified: the loop now delivers all `max_attempts` attempts and
`last_exc` is always set on exhaustion.") with `resolve_thread: true`,
and the Complete report's `thread_updates` records
`{"thread": "t-388", "action": "replied_fixed", "comment": "c-5231"}`.
Bob's thread `t-301` is **not** Forge's — Dana's reply and fix sit
there, but confirming and resolving it is Bob's call, so
reconciliation never touches it.

**Specialists (step 3)** run with the full diff for context plus the
`<scope>` tag naming `9f3c2abe41d7` as the incremental base
(`review.md` §6b) — new findings must lie inside the interdiff's
ranges. Their briefs also carry the updated `<existing_comments>`
block above, which is what keeps them from second-guessing the round
of changes they're looking at: the `range(1, max_attempts + 1)` line
in the interdiff is visibly the fix requested on thread `t-388`, and
the trimmed log line is visibly what Bob asked for on `t-301` —
without the threads, either could read as an unexplained change worth
questioning (`review.md` §3's reversal note). The `bugs` specialist raises **f-3** there: the retry clause
now catches `ValueError`, and JSON parsing moved *inside* the retried
`_post_once` — so a malformed success response (gateway accepted the
invoice, body didn't parse) triggers a re-POST of a non-idempotent
dispatch: duplicate invoices. Anchored at `billing/retry.py:23`,
severity high, prose fix (retry only transport-level failures that
precede delivery, or add an idempotency key to the POST). The
validator confirms after reading both files; the finding posts as a
new thread.

Had Dana **force-pushed** instead, the envelope would have carried
`rebased="true"`, no `<incremental_diff>`, and no `<scope>` in the
briefs — a full-scope session in which dedup against `t-388` and
`t-301` does all the noise control, exactly the v1 behavior.
