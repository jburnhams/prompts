# Eval

Every number in [`tools.md`](./tools.md)'s configuration section is a
defensible guess. Every format decision in [`formats.md`](./formats.md) is
an argument from other people's source code. [`adk.md`](./adk.md) contains
two open questions phrased as "this is the eval that decides whether §2c is
a note or a problem" — and, until this document, no eval to decide them in.

This is the harness for answering those questions on this agent, with the
models it actually runs on, against repositories it actually touches.

## Why this is not optional, and why public benchmarks don't substitute

The research pass behind this design ended on an uncomfortable finding
([`agent-tool-implementations.md`](../agent-tool-implementations.md) §4a2):
**there is no public evidence base good enough to settle harness
decisions.** An April 2026 audit of the only two benchmarks that evaluate
instructed code editing with human-authored instructions and test-based
evaluation found both are over 90% Python with zero TypeScript, Java, C#,
Go or Rust; that they invert the real domain mix; that neither contains
documentation, testing or maintenance edits — 31.4% of real pull requests;
and that 59% of EDIT-Bench's low-coverage suites cannot detect
modifications *outside* the edit region. That last one is disqualifying
here: collateral damage is the specific failure mode of an unsupervised
agent, and the public oracles are blind to it.

Meanwhile the vendor benchmarks measure the right construct on the wrong
terms — run by interested parties, on rosters that go stale in months
(Diff-XYZ's entire roster was superseded within ten months).

What every credible actor in that survey actually did was build their own:
OMP for edit formats, Hermes for read-tool hardening, both published with
method and caveats. Hermes's `evals/readtool/` is the template this
document copies, because it is the most rigorous artifact the research
pass found (§6e).

**The point is not to produce a score.** It is to make the tunables and
format rules *decidable*, and to catch the class of defect where nothing
fails and everything costs more — the FIFO guard Hermes measured was worth
−79% tokens and −81% wall clock with task accuracy unchanged at 1.00. No
functional test would ever have found it.

## What it measures

Three suites, in priority order. Each targets decisions this design
currently makes on argument alone.

### Suite 1 — Tool hardening (the hostile workspace)

One deterministic workspace of adversarial files, run through the real
agent with the real tool surface. Nine fixtures come straight from
Hermes's eval because the failure shapes are universal; the rest are
specific to decisions this design made.

| Fixture | Shape | Decision under test |
|---|---|---|
| 80K-line, 2.7 MB lockfile | token tarpit | `read.default_lines` |
| one 600 KB line | wide, not many | `read.max_line_chars` |
| 2,000 lines × 900 chars | wide *and* many | `read.max_entry_bytes`, and whether whole-line enforcement resumes cleanly |
| 150K-line log, one ERROR near the tail | needle past the window | whether the model pages or reaches for `Grep` |
| 412-line file, `start_line: 900` | past EOF | the `past_eof` note (`formats.md` §8b) |
| empty file | non-silence | the `empty` status |
| `Meeting…PM.txt` (NFD + U+202F + U+2019) | invisible filename difference | tolerance layer 4, and whether the repaired path is echoed back |
| `AGENT.md` beside a real `AGENTS.md` | near-miss name | did-you-mean |
| FIFO at `logs/live.pipe` | a read that never returns | the `stat` type guard — *not* the name blocklist |
| PNG bytes behind `data.txt` | lying extension | `binary` detection by content |
| file with tabs, quotes and backslashes | envelope round-trip | **`adk.md` §2c's open question**: does `Edit` still land first-try after MCP JSON encoding? |
| CRLF file | line-ending restore | `formats.md` §8a's normalise-on-read/restore-on-write rule |
| file where `old_string` appears twice | ambiguous match | the error text, and whether the model recovers in one turn |
| 20-file batch of large files | call budget | `read.max_entries`, `read.call_budget_chars`, and whether truncated entries are re-read individually |

### Suite 2 — Edit correctness under collateral-damage checking

The audit's **D4** as a hard rule: *every* task asserts on the whole
working tree, not on the edited region. A task passes only if the intended
change landed **and** nothing else moved. This is the oracle the public
benchmarks lack and the one that matters for a hands-off agent whose
output is a working tree somebody else commits.

Fixtures are invertible mutations planted in real repositories — the
Stencil method — but in **the languages this deployment actually ships**,
which is the specific thing no public benchmark provides.

### Suite 3 — Review mode

Planted defects with known locations and severities, plus deliberately
clean diffs. Measures precision as much as recall: for a bot that posts
without a human in the loop, a false positive costs more than a miss, so
the headline metric is findings-on-clean-diffs (should be zero) alongside
detection rate.

## Metrics

Accuracy alone hides most of what this eval is for. Every task records:

- **accuracy** — graders against planted ground truth, plus Suite 2's
  whole-tree assertion.
- **api_turns**, **tool_calls**, and per-tool call counts.
- **total_tokens**, split input/output.
- **wall_s**.

Efficiency aggregates are **per-task means, never sums**. Errored runs
score 0 and stay in the accuracy denominator but are **excluded from
efficiency means**, so a crash cannot flatter the token numbers.

## Rules of engagement

Copied from Hermes's discipline, which is stricter than anything else the
research pass found, and adopted wholesale rather than reinvented:

- **Three reps minimum.** Single-run deltas within ±3% are noise, not
  wins.
- **Two models on purpose**: the strongest model this agent targets, and a
  materially weaker one. A feature that only helps the weaker model still
  ships — that is the population hardening serves, and it is the leading
  indicator for the stronger model on harder tasks.
- **Never change tool code while a run is in flight.** The runner imports
  the live tree.
- **Same prompt in both arms**, or the comparison is void. Record it when
  a prompt changed between series and mark those numbers non-comparable
  rather than quietly reporting them.
- **Record the caveat that invalidates your own result.** Hermes's log
  notes that with a full toolset models dodge the FIFO hang by reaching
  for `stat` first, so the measured saving is an upper bound. A results
  log without caveats is marketing.

## Output: a ship/no-ship log

Results are per-feature, not a leaderboard. Each entry records the change,
the A/B table, a verdict, and the caveats — the same shape as
`results/SUMMARY.md` in Hermes's eval. A tunable that cannot be shown to
matter goes back to being a default, and is documented as such.

This is what turns `tools.md`'s configuration section from seventeen
opinions into seventeen decisions, and it is the only mechanism in this
design that can retire one.

## What this is not

- **Not a model benchmark.** The model is a parameter; the harness is the
  variable. If a run produces a claim about which model is better, the
  eval has been misused.
- **Not SWE-bench.** Task-completion benchmarks measure the whole system
  and cannot attribute a regression to a tunable. Both are useful; only
  one of them is this.
- **Not a substitute for the normalisation telemetry** (`tools.md`'s
  tolerance section). That telemetry is production evidence about what
  models actually emit; this eval is controlled evidence about what the
  harness does in response. The flat-`Read` question in
  [`future.md`](./future.md) is gated on the former, not the latter.

## Open questions this is built to close

1. Does `Edit` land first-try on tab/quote/backslash-heavy files after the
   MCP envelope? (`adk.md` §2c — currently "a note or a problem," unknown
   which.)
2. Is `read.max_entry_bytes` at 64 KB, or is the call budget doing all the
   work?
3. Does structural summarization (`tools.md`'s `Read`) reduce turns, or
   just add a re-read round trip?
4. Does the batch `Read` shape produce malformed-argument rates high
   enough to justify the flat spelling in `future.md`?
5. Does read-before-edit's full-view requirement on `Write` ever block a
   legitimate rewrite?
