# Example: validator brief

The exact `Task` call the review orchestrator makes in pipeline step 5
to validate candidate **f-2** — the one the validator ends up
*rejecting*, which is the more instructive case. (f-1's brief is
identical in shape, with its own finding JSON.)

The candidate, as the `bugs` specialist returned it and the
orchestrator assigned it an id:

```json
{
  "id": "f-2",
  "role": "bugs",
  "file": "billing/dispatch.py",
  "line": 38,
  "line_end": 38,
  "severity": "medium",
  "summary": "dispatch() failure exception type changed from RuntimeError to TransportError, breaking existing callers' handlers",
  "rationale": "The old code raised RuntimeError on gateway 5xx; the new _post_once raises TransportError. Any caller with `except RuntimeError` around dispatch() no longer catches gateway failures.",
  "suggested_fix": null,
  "validated": null,
  "validator_note": null
}
```

The `Task` call:

```json
{
  "subagent_type": "validator",
  "description": "Validate finding f-2",
  "finding": { "…": "the JSON above, verbatim" },
  "prompt": "<candidate_finding>\n…\n</candidate_finding>\n\n<pr>\n…\n</pr>\n\n<description>\n…\n</description>\n\n<diff>\n…\n</diff>"
}
```

With the `prompt` unpacked:

```
<candidate_finding>
{{ … example truncation: the f-2 JSON above, verbatim … }}
</candidate_finding>

<pr>
{{ … example truncation: the envelope's <pull_request> block, verbatim
   — see review-envelope-initial.md … }}
</pr>

<description>
{{ … example truncation: the envelope's <description>, verbatim … }}
</description>

<diff>
{{ … example truncation: the envelope's full <diff>, verbatim — the
   whole diff, not just billing/dispatch.py: pre-existing-ness is
   judged from the diff's own old-side lines (review.md §5) … }}
</diff>
```

How this validation actually runs (per the validator system prompt,
`system-prompts.md` §5):

1. *Is the described problem real?* Partially — the diff's old-side
   lines do show `raise RuntimeError(...)` replaced by
   `TransportError` inside `_post_once`. The type change is a fact.
2. *Does it matter?* The claim's teeth are "breaking existing
   callers' handlers." The validator Greps the tree at head:
   `Grep("except RuntimeError", output_mode: "content")` → no matches
   anywhere; `Grep("dispatch\\(", glob: "*.py")` → three call sites,
   none wrapping the call in a handler for either type (failures
   propagate to the job runner's generic error handling).
3. Verdict: **rejected** — "No caller catches RuntimeError anywhere in
   the tree; the exception-type change has no observable effect in
   this codebase."

f-2 therefore lands in the Complete report's `filtered` list with
`validated: false` and that sentence as `validator_note` — recorded,
never posted. Had the validator been genuinely unable to tell (say,
`dispatch()` were a public API of a published package), the standing
rule is the same outcome for a different reason: reject rather than
post an unverified claim.

Contrast f-1: the same brief shape, and the validator confirms by
Reading `billing/retry.py:19-29` (the loop really does run
`max_attempts - 1` times; `last_exc` really can be `None`) and
`tests/test_retry.py` (no call-count assertion — the specialist's
claim that CI misses it holds). Verdict **confirmed**, one sentence,
and f-1 proceeds to delivery.
