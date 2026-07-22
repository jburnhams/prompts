# Example: initial review envelope

The complete `{{TASK_ENVELOPE}}` for the first review session of PR
#87 — every tag from `formats.md` §1b, with `<diff>` built by the
algorithm in `review.md` §2 and `<existing_comments>` in the thread
model of `review.md` §3. This is a first review, so no
`<review_state>`/`<incremental_diff>` tags appear.

```
<pull_request>
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
</pull_request>

<description>
Gateway 5xx blips currently fail invoice dispatch outright (see
PROJ-982). This adds a small retry helper with exponential backoff and
uses it in `InvoiceDispatcher.dispatch`. Only transport-level errors
are retried; client errors still fail immediately.
</description>

<changed_files>
- billing/dispatch.py (modified) +18/-7
- billing/retry.py (added) +29/-0
- tests/test_retry.py (added) +18/-0
</changed_files>

<diff>
diff --git a/billing/dispatch.py b/billing/dispatch.py
index 8d21f3a..b7a90c4 100644
--- a/billing/dispatch.py
+++ b/billing/dispatch.py
@@ -2,10 +2,12 @@
 
 import logging
 
 import requests
 
+from billing.retry import TransportError, send_with_retry
+
 logger = logging.getLogger(__name__)
 
 
 class InvoiceDispatcher:
     """Sends invoices to the configured gateway endpoint."""
@@ -18,12 +20,21 @@ class InvoiceDispatcher:
     def _headers(self):
         return {"Authorization": f"Bearer {self._token}"}
 
     def dispatch(self, invoice):
         payload = invoice.to_wire()
-        response = self._session.post(
-            self._endpoint, json=payload, headers=self._headers(), timeout=10
-        )
-        if response.status_code >= 500:
-            raise RuntimeError(f"gateway 5xx: {response.status_code}")
-        response.raise_for_status()
-        return response.json()["dispatch_id"]
+        logger.info("dispatching invoice %s payload=%r", invoice.id, payload)
+        response = send_with_retry(
+            self._post_once,
+            payload,
+            max_attempts=3,
+        )
+        return response.json()["dispatch_id"]
+
+    def _post_once(self, payload):
+        response = self._session.post(
+            self._endpoint, json=payload, headers=self._headers(), timeout=10
+        )
+        if response.status_code >= 500:
+            raise TransportError(f"gateway 5xx: {response.status_code}")
+        response.raise_for_status()
+        return response
diff --git a/billing/retry.py b/billing/retry.py
new file mode 100644
index 0000000..3e1c9d2
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
+    for attempt in range(1, max_attempts):
+        try:
+            return send(*args, **kwargs)
+        except TransportError as exc:
+            last_exc = exc
+            logger.warning(
+                "dispatch attempt %d/%d failed: %s", attempt, max_attempts, exc
+            )
+            time.sleep(base_delay * 2 ** (attempt - 1))
+    raise last_exc
diff --git a/tests/test_retry.py b/tests/test_retry.py
new file mode 100644
index 0000000..a41f8e7
--- /dev/null
+++ b/tests/test_retry.py
@@ -0,0 +1,18 @@
+from unittest import mock
+
+import pytest
+
+from billing.retry import TransportError, send_with_retry
+
+
+def test_retries_then_succeeds():
+    send = mock.Mock(side_effect=[TransportError("boom"), "ok"])
+    with mock.patch("billing.retry.time.sleep"):
+        assert send_with_retry(send, max_attempts=3) == "ok"
+
+
+def test_raises_after_exhaustion():
+    send = mock.Mock(side_effect=TransportError("boom"))
+    with mock.patch("billing.retry.time.sleep"):
+        with pytest.raises(TransportError):
+            send_with_retry(send, max_attempts=2)
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
```

Things to notice, each specified in `review.md`:

- `Base SHA` is the **merge-base** of `main` and the branch head, not
  `main`'s tip (§2 step 1) — the diff charges the PR only with what it
  introduces.
- The diff is `-U5 -M` plain unified output, files in
  `<changed_files>` order (§2 steps 2–3). No file here triggers the
  elision rules; a lockfile in this PR would have appeared header-only
  with a visible `[hunks elided: …]` marker and an `[elided]` tag on
  its `<changed_files>` line.
- Bob's inline comment arrives as an explicit `<thread>` with a stable
  id, a new-file anchor, and an `open` status (§3) — this is what lets
  pipeline step 4 dedup the security specialist's payload-logging
  candidate against it by structure rather than by scraping a flat
  comment list.
- `Snapshot:` records when this state was captured; the mid-run race
  rules in §8 are defined against it.
- Both threads here are **current** — anchored at the same head this
  envelope snapshots — so they carry no `at_sha`, no `@ sha` comment
  markers, and no then/now blocks, and no `<format_notes>` tag
  appears: the staleness machinery (§3a–3b) costs nothing until a
  thread actually goes stale. Contrast the re-review example, where
  both threads have.
