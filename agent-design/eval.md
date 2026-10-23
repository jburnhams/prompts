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

Four suites, in priority order (Suite 4, added 2026-10-22, covers the
analysis quick path). Each targets decisions this design currently makes on
argument alone.

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
| the FIFO and lockfile fixtures again, reached through a `general-purpose` delegate; and a delegate definition naming an MCP server outside its role's subset | delegate parity (added 2026-10-19) | `tools.md`'s "One job declares the tools": the same refusals fire inside a delegate, and the extra server is dropped, not merged |

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

**Added 2026-10-17 — attention calibration** (`risk.md` §8). Two further
sets: a *known-clean* set scored for over-tiering as well as for spurious
findings, and a *needed-a-fix* set (PRs that later needed a follow-up
fix, `risk.md` §8a), scored for whether the attention tier would have
been `medium` or above and whether `look_here` covered the lines the fix
changed. The
second is the one that decides whether `low` may ever relax a human
requirement; it is re-run on every change to the triage prompt, the
default review policy, or the model.

**Added 2026-10-19 — ReviewBench as the external calibration set**
(`../code-review-approaches.md` §15). GitHub's ReviewBench (2026-10-05):
219 public PRs from 187 repositories in 19 languages, a golden set
gathered from human reviewers, author follow-up commits, static tools and
several model families, then deduplicated and validated under a published
rubric. It is the first public review benchmark this collection has found
that is multi-language, built from real PRs, and shown to predict online
results (one Copilot experiment: offline predicted gains in precision,
recall and volume; online gave +8.0% addressed rate and +13.6% recall).
That answers part of "public benchmarks don't substitute" above, for
review only. Three uses:

1. **Run it, don't cite it.** Forge's review pipeline is run on the
   public set (the runner takes a container image and a model key) and
   the result goes in the ship/no-ship log beside Suite 3. **Grounded
   recall** is the headline, as ReviewBench uses it, because its
   denominator does not move with the agent's output. **Augmented
   precision** is a diagnostic, and it is the number that matters most
   here, since a hands-off reviewer pays more for a false positive than
   for a miss. Score both twice, on `confirmed` findings alone and on
   `confirmed` plus `plausible`: since the validator became three-state
   and `plausible` is posted only on `high`-tier reviews (`review.md`
   §5), the gap between the two runs is the recall that rule buys and the
   precision it costs, measured on PRs nobody here labelled.
2. **Copy its gold-set recipe for the internal set.** Suite 3's planted
   defects measure detection; a set built ReviewBench's way from this
   organisation's own merged PRs measures what real reviewers flagged.
   Its "issues inferred from author follow-up commits" source is the
   same signal as `risk.md` §8a's follow-up fix, so one labelling job
   feeds both the needed-a-fix set above and the review golden set.
3. **Keep the true-positive rule.** "A finding counts as a true positive
   only if it is true, relevant, and non-trivial" is a better grading
   rule than Suite 3's current planted-or-not, and is adopted for the
   internal set.

Caveats carried into the log: GitHub built it and the only
offline-to-online evidence is GitHub's own product; the judge is a single
model (Claude Sonnet 5) with 96.6% agreement against senior engineers on
true positives, which says nothing about agreement on false positives;
the blog post states no license for the dataset or code (check before
storing anything from it); and the PR-size mix is deliberately weighted
away from tiny changes.

### Suite 4 — Analysis quick path, `Expand` and `HandOff`

*Added 2026-10-22.* Decides whether the cheap-start design in
[`models.md`](./models.md) is safe and whether it earns its keep. The first
question is not whether it is accurate. It is whether the quick case got
slower or dearer, because that is the constraint the design exists to
protect.

**Fixture.** A small fixed warehouse (DuckDB or SQLite; the same data every
run) with documented joins and traps seeded on purpose, and a question set
stratified by what the right route is:

| Stratum | Right route | Examples |
|---|---|---|
| **L** — clean lookup | answer, no hatch | one aggregate over one table; a documented join |
| **T** — lookalike with a trap | answer *correctly* or escalate; a wrong quick answer is the failure | a join on a duplicated key that inflates a `SUM`; a nullable key an inner join drops; soft-deleted rows; a UTC period boundary; a metric with two plausible definitions |
| **D** — needs a hidden source | `Expand`, then answer in the same run | a question about a source not in the overview |
| **I** — needs investigation | `HandOff(too_complex)` | no obvious table, several steps, an undefined metric |
| **R** — asks for a report | `HandOff(report_requested)` as the first action | "make me a report on churn by region" |

Each item carries: the correct answer with a tolerance, the required
disclosures (SQL shown, row count shown, assumption stated), and the expected
route. T items are the ones that matter most and the ones public benchmarks
are weakest on; DAB's labelled failure modes
([`../agent-data-analysis.md`](../agent-data-analysis.md) §12a) are the
source for the trap shapes, and `data.md` §4b's `input_rows` stub is
checked against the fan-out ones.

**Arms.** The same questions, the same prompt text where the arms share it:

| Arm | What it is | Purpose |
|---|---|---|
| A0 | cheap model, quick tools, **no** hatch, no "further sources" line | baseline for quick-path cost and latency |
| A1 | A0 plus `Expand`, `HandOff` and the overview line | the design, model-called only |
| A2 | A1 plus the harness triggers (`models.md` §5) | the design as proposed |
| A3 | standard tier from the start, no hatch | the "just use a better model" alternative |
| A4 | `investigate` landing from the start | quality ceiling, and the cost of always paying for it |

**Measures** (the five in `models.md` §8, made concrete):

1. **Quick-path regression.** On stratum L: time to first token, time to final
   answer, and input and output tokens, A1 and A2 against A0. The expected
   overhead is the two descriptions and one overview line. Any gap larger
   than that is a bug in the design. Proposed gate: median latency within 5%
   and tokens within 100 of A0. These two numbers are guesses; set them from
   the first A0 baseline and write the real ones into the log.
2. **Route accuracy.** Confusion matrix of expected route against actual,
   split into model-called and harness-triggered. Many harness triggers with
   few model calls on D, I and R means the model is under-calling.
3. **Unnecessary hatch calls.** `Expand` or `HandOff` on L items that A0 answered correctly; and the `Expand` hit rate on D items (what it revealed that a later query used).
4. **Silent wrong answers (headline).** On T items: a wrong figure with no
   escalation, per arm. The goal is not zero; it is no worse than A0 and
   visibly better than nothing on the fan-out and null-key traps once the
   disclosures are in. Also scored: whether the disclosed SQL and row count
   would let a reader see the error, on a sample judged by a person.
5. **Cost per correct answer** across the whole question set, per arm. A2
   should beat A3 (otherwise the hatch has not paid for itself) and cost far
   less than A4.
6. **Handoff loss** on R items: facts present in the collector's refs that the
   report omits, and wrong facts the report states that no ref supports.
   Also, the provenance gate's pass rate.
7. **Report quality**, separately for collector tier (economy versus
   standard, same writer) and writer tier (strong versus standard, same
   collector).

**Presentation variants (text only).** How the hatch is presented
(`models.md` §4b) is cheap to vary and decides how it is used, so it is
measured, on A1 (model-called only, no harness triggers) so that triggers
cannot hide under-calling. One factor at a time against the §4b default:

| Variant | Change |
|---|---|
| V1 | situations in the prompt removed (tool description only) |
| V2 | harness notes removed |
| V3 | harness notes kept, prompt situations removed |
| V4 | the cost sentence ("the user will wait longer") removed from the description |
| V5 | tool listed first instead of last |
| V6 | one tool, named `Expand`, with the three reasons, instead of the pair |
| V7 | `HandOff` enum values `investigate` / `report` instead of the situational names |

Read each against the default on three numbers: the model-called share on D,
I and R items (under-calling), the unnecessary-call rate on L items
(over-calling), and quick-path tokens. A variant that wins on one by losing
on another is a finding, not a tie. Expect V4 to raise unnecessary calls and
V1 to lower the model-called share; if neither moves, the text matters less
than assumed and the harness triggers are doing the work.

**Online counterpart.** Once there is traffic, the same silent-wrong question
runs on sampled live requests: re-run answers that did not escalate through
the `investigate` landing and compare. This is shadow evaluation, and it is
the only source for a silent-wrong rate on questions nobody planted traps in.

**Rules.** Three reps minimum; a Haiku-class model and a materially weaker
one; record tier, model ID and price on every result; mark any run where the
prompt changed between series as non-comparable. The suite makes claims about
the harness and the routing, not about which model is better.

## Metrics

Accuracy alone hides most of what this eval is for. Every task records:

- **accuracy** — graders against planted ground truth, plus Suite 2's
  whole-tree assertion.
- **api_turns**, **tool_calls**, and per-tool call counts.
- **total_tokens**, split input/output.
- **wall_s**.
- **envelope_inflation** — the ratio between the bytes a tool *returned*
  and the tokens that reached the model for it. This is the one metric
  here that measures the harness rather than the agent, and it exists
  because `adk.md` §2c's escaping question was open-ended until it
  acquired a budget. Independent measurement
  ([`../agent-tool-result-transport.md`](../agent-tool-result-transport.md)
  §1a) puts single-level JSON escaping at **~1.11× on tag-framed prose**
  and **~1.22× on the code-shaped payloads `Read` returns**, so those are
  the expected values, not a target to beat. **Materially above ~1.25× is
  a bug report, not a cost**: it means something in the chain is
  double-encoding, and the candidates are few enough to check by hand —
  a payload serialised into a JSON string rather than carried as text, a
  result envelope being stringified whole, or a fact-shaped field
  duplicated into two channels. Record it per tool, since `Read` and
  `Bash` will differ and the difference is diagnostic. Caveat to carry in
  the log: the published ratios were derived with a GPT tokenizer as a
  proxy, so re-derive the baseline on the model actually under test
  before calling a deviation a defect.

Three more once `table://` and the ref lifetime rules are live
([`local.md`](./local.md) §2a–§2e). All three are diagnostics rather
than scores — each is a number whose *drift* names a specific
misconfiguration:

- **expired-ref-hit rate on `persist` artifacts** — how often a
  resolution returns the self-describing expiry error rather than
  bytes. A high rate means the sliding window (`artifacts.md` §5.5) is
  too short, and it is the only signal that would catch that, because
  the failure is recoverable and so does not show up as an error rate.
  Split by whether the ref was cited in a `Complete` report, since a
  miss there is a reproducibility failure and a miss on a working ref
  is merely a re-fetch.
- **local cache hit rate** (`artifacts.md` §6a), recorded only where a
  browser deployment exists. Near zero means the cache is costing
  storage for nothing; it also bounds how much the keep-alive-on-hit
  rule is actually carrying.
- **fan-out ratio on local joins** — output rows over the larger input.
  This is the metric `data.md` §2c's no-joins position exists to make
  observable: a ratio materially above 1 is a duplicated key, and the
  whole argument for fetching per table is that this number exists at
  all. Log the distribution, not the mean; the interesting case is the
  tail.
  *Added 2026-10-19:* the first labelled set to check it against is
  DAB's (`../agent-data-analysis.md` §12a). Its repository publishes
  the failure-mode judge, its prompts and an example trace; whether the
  full annotated trajectories are public was not confirmed. If they are,
  replaying the implementation-error trajectories through the
  `input_rows` stub (`data.md` §4b) and counting how many show the
  fan-out line is the test of whether the deferred halves are worth
  adopting.

Two more from [`cloudflare.md`](./cloudflare.md) §4, both of which exist
to kill a mechanism if it misbehaves rather than to score a run:

- **normalised-edit rate** — the fraction of `Edit` calls that succeeded
  only after the whitespace-normalised retry (`tools.md`), **split by
  file type**. This is that repair's kill switch, and the split is what
  makes it diagnostic: a rise concentrated in Python, YAML or Makefiles
  is the indentation risk the rule admits to, and the repair goes. A
  rise spread evenly across file types is a `Read` round-trip problem to
  fix upstream instead, and the repair is doing its job.
- **evicted bytes, and the re-read rate on evicted refs**
  (`artifacts.md` §5.6). Bytes evicted is the saving; the fraction of
  evicted refs that get read back is the cost. A high re-read rate means
  the retention window is too short and the pass is buying context space
  with tool calls.

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

00. *(Added 2026-10-22.)* Does the cheap start with `Expand` and `HandOff` keep the quick case as fast and cheap as a plain cheap agent, and is its silent-wrong rate on trap questions no worse? (Suite 4; `models.md` §8. Until it is answered yes, `HandOff` ships off.)

0. *(Added 2026-10-17.)* Is the attention tier calibrated: is the
   follow-up-fix rate (`risk.md` §8a) of `low`-tier PRs no worse than the human-reviewed baseline over a
   sustained window? (`risk.md` §8; the gate's relaxed column stays off
   until this is answered yes.)

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
6. **Does role specialization beat one broad finder at equal total spend?**
   The multi-stage and single-stage shapes (`review.md` §6) are wire-
   identical by construction, so this is directly A/B-able: same PRs,
   same envelope, N specialists versus one `all`-scope finder given a
   comparable budget. Measure recall against a seeded-defect fixture set
   and precision against the validator's reject rate, not finding count.
   The question is live because the field is split — most review tools
   in `../code-review-approaches.md` §5 fan out, DeepSeek Harness's
   review skill deliberately does not (`review.md` §6a) — and because
   the usual justification for fan-out (each agent covers different
   code) does not apply when every reviewer needs the whole diff.
7. **Is review fan-out context-bound enough to pay for Code Mode?**
   DeepSeek's typed-`.d.ts` tool advertisement costs ~25 KB of fixed
   prompt and buys back "intermediate tool results never enter the
   conversation" (`../agent-tool-call-dialects.md` §4). It only wins
   above some fan-out. The measurement that settles it is cheap and
   doesn't require building it: instrument how much of a finder's
   context is spent on reads whose content appears in no returned
   finding. If that fraction is small, the question is closed — a second
   calling convention would be cost with no return, and nothing further
   needs tracking. If it is large, the prerequisite is typed return
   schemas on every tool in `tools.md`, which the surface does not
   declare today.

8. **Does the persistence rule change outcomes, or just spend budget?**
   The coding prompt now refuses `blocked` on a first obstacle
   (`system-prompts.md` §1), which is a bet that a second approach
   usually exists. It is directly measurable and cheap to get wrong in
   both directions: run the same seeded-blocker fixtures with the rule
   on and off, and compare *completed* tasks — not turn counts — against
   the budget spent. Two failure signatures look alike in aggregate and
   should be separated: a run that grinds through variations of the same
   failed approach (the rule bought nothing and cost a budget), and a
   run that reports `budget_exhausted` where the old prompt would have
   said `blocked` (the rule deferred a human decision by one attempt).
   The second is only a loss if the retry then fails the same way, which
   the ledger's `attempts` list records directly.
9. **What fraction of `spun_off` proposals are worth having been
   filed?** Task splitting (`orchestration.md` §6) assumes a run that
   meets out-of-scope work should hand it off rather than stretch.
   Whether the proposals are any good is open, and the design already
   contains a free proxy: a gated `follows_this` spinoff waits for a
   human reply, so the **approval rate is the measurement**, arriving
   for nothing once the gate exists. A low rate means runs are inventing
   scope and §11's caps are load-bearing rather than precautionary; a
   high one means the gate is ceremony and auto-chaining `follows_this`
   deserves a second look. Not measurable on `blocks_this`, which
   auto-chains and therefore produces no signal.
