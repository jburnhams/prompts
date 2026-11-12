# Hex evals, and the prompt Hex publishes for building them

*Read 2026-11-12. Tags as in [`README.md`](./README.md). Everything in
§1–§3 is [docs] unless marked; §4 is the verbatim bootstrap prompt from
the docs; §5 is [source].*

Shipped 2026-08-04 ("so you're not just going on vibes"), publishing and
scheduling 2026-09-15. [changelog] Team and Enterprise; Editors run,
Managers and Admins publish and schedule. Defined and run **only from
the CLI**; results readable in the CLI or Context Studio.

## 1. The format

A suite is one YAML file with up to 100 cases; a case has a prompt,
1–5 `attempts`, up to 15 rubrics, optional `attachments` (a connection,
table, semantic dataset or view, or project IDs, "the same way
@-mentioning a resource does") and `threadOptions` (`endorsedMode`). A
workspace runs at most 3 suites at once. "Each case runs a real agent
thread, and the result is graded by an LLM judge."

```yaml
name: "March MAU checks"
id: march-mau-checks
modelSelection: { model: <model_name>, effortLevel: medium }
cases:
  - id: mau-detailed
    prompt: "How many monthly active users did we have in March 2024?"
    attempts: 1
    rubrics:
      - id: counted_distinct_users
        type: judge_thread           # judge sees messages, tool activity, final answer
        criterion: "Did the agent count distinct users rather than sessions?"
        measure: correct-method
      - id: states_the_number
        type: judge_final_answer     # judge sees the final answer only
        criterion: "Does the final answer give a single MAU number?"
        expected: "18432"
      - id: cites_a_source
        type: judge_final_answer
        criterion: "Does the final answer name the table it queried?"
        warnOnly: true
      - id: mau_matches_sql
        type: numeric_value
        target:
          sql: "SELECT count(distinct user_id) FROM events WHERE date_trunc('month', ts) = '2024-03-01'"
          dataConnectionId: "dc_..."
          timeoutSeconds: 30
        tolerancePercentage: 1
```

(Condensed from the docs' example; field names unchanged.)

### Rubric types

| Type | Judge sees | Use for | Extras |
|---|---|---|---|
| `judge_thread` | "the full thread, including messages, tool activity, and the final answer" | method: "whether it used the expected table or business definition" | `expected`, `expectedSql` (run at grade time, result shown to the judge) |
| `judge_final_answer` | "only the agent's final answer" | the delivered result | same |
| `numeric_value` | — (extraction plus compare) | one number | `target` as a literal or `{sql, dataConnectionId, timeoutSeconds ≤ 120}`; `tolerancePercentage` (default 1) **or** `absoluteTolerance` ("a value passes if it's within either"); `strictHeadline` (default true: grade "the number identified as the answer's primary result, and fails the rubric if no primary result can be identified"); `extractionGuidance` ("the enterprise ARR, not total ARR") |

### Grading rules

- **Attempts**: "With one attempt, that attempt must pass. With multiple
  attempts, the case can tolerate one failed attempt and still pass. If
  any attempt errors, the case is marked **Error**." Hex's skill states
  it as "1 → must pass; 2 → ≥1 passes; 3 → ≥2 pass". [source] The skill
  says 1–3 attempts; the docs now say 1–5.
- **Outcomes**: Pass, Fail, **Error** ("could not run or be graded …
  out of credits"), Cancelled, Skipped. Cancelling keeps completed
  grades as a partial summary.
- **`warnOnly`**: graded and reported, never fails or errors the case,
  including when the judge call itself fails. "Every case needs at least
  one rubric that is not warn-only."
- **Measures**: a `measure` tag rolls rubrics up across cases into one
  pass rate. "Every tagged rubric counts equally within its case, and
  every case counts equally across the suite, however many attempts it
  ran. Tagging more rubrics … or running more attempts, adds confidence
  rather than weight. Checks that errored or were not graded are
  excluded rather than counted as failures." Suggested names:
  `objective-met`, `correct-method`, `answer-grounded`, named "so that a
  passing check represents a positive outcome". Renaming a measure, or a
  suite without an explicit `id`, starts its history over.
- **Model pinning**: `--model` and `--effort` together on the CLI, or
  `modelSelection` in the suite; CLI wins; otherwise the workspace
  default.
- **Billing**: credits for the agent thread *and* the judge, charged to
  whoever started the run.

## 2. Baseline and hill-climbing

"**Baseline evals** are questions you expect to pass consistently — the
canonical facts and definitions your business depends on." They "catch
changes caused by dependencies that evolve separately from your
published context, such as referenced projects or MCP servers".
"**Hill-climbing evals** are harder, aspirational questions … especially
useful in a test-driven workflow: write the eval first, then iterate on
your guides and semantic models until the agent can pass it
consistently."

## 3. Context previews: fork, change, test, publish

"Evals are especially useful when you run them against a **Context
Preview** — a sandboxed fork of your context — before a change reaches
production. This mirrors a normal software workflow: fork, change, test,
then publish."

1. Edit guides or semantic models locally.
2. `hex context preview` from a repo with `hex_context.config.json`
   "uploads the current working tree to an ephemeral context branch and
   prints a Preview ID and link".
3. `hex eval run <file> --preview-id <id>`.
4. Compare with a baseline run without `--preview-id`.
5. `hex context publish <preview_id>`.

The GitHub Action (`hex-inc/action-context-toolkit`, MIT, read at
`6246f48`) does steps 2 and 5 in CI: on a pull request it previews and
comments "a summary of changed resources, along with a link to test them
in a thread preview"; on the default branch it publishes. [source] Evals
themselves sync the same way and can be **scheduled** (daily, weekly,
monthly, in a two-hour window Hex picks to spread load). [docs]

The blog adds what the judge is for: it "reads the entire conversation,
and sees the specific tools and resources the agent uses", and a
criterion can ask whether the agent "appropriately refuse[d] to answer a
question where there is insufficient context". No model or cost results
are published. [blog]

## 4. The bootstrap prompt, verbatim

Hex's docs give this prompt "to your coding agent" to build a first
suite from real usage. It is the only complete agent prompt Hex
publishes in its docs. Reproduced exactly as served on 2026-11-12.

```text
You're going to help me bootstrap an eval suite for our Hex agent, grounded in how our workspace is actually used, so we can test and improve our agent's context. Build the suite from our real usage where it exists, and fall back to our key tables where usage is thin. Follow these steps in order.

1. Check prerequisites. The Hex CLI supports macOS and Linux only; on Windows, run it under WSL. Run `hex --version`. If it's missing, install it:
   - macOS: `brew tap hex-inc/hex-cli && brew install hex-inc/hex-cli/hex`
   - Linux (or WSL): `curl -fsSL https://hex.tech/install.sh | bash`
   Then run `hex auth status`. If I'm not authenticated, stop and tell me to run `hex auth login`; don't authenticate on my behalf. If I have multiple profiles, ask which to use (`hex auth switch <profile>`). This flow needs a Manager or higher role; if a command is rejected as unauthorized, tell me.

2. Install the Hex agent skill and read it. Run `hex install agent-skill` with the flag for your agent environment (`--claude`, `--codex`, or `--path <dir>`), then read the installed SKILL.md, especially the evals section — it documents the `hex eval` commands and how async runs work. For the full `evals.yaml` schema (every case and rubric field), read https://learn.hex.tech/docs/agent-management/evals; the example in step 5 covers the essentials. `hex eval run` validates the file and reports schema errors before starting a run.

3. Find how the workspace is actually used. Hex already classifies threads into workspace topics, so use those instead of inventing categories. Run `hex context topic list --json`, then `hex thread list --topic-ids <id> --num-days 30 -n 100 --json` for each. The list isn't ranked, so rank it yourself by distinct question intent, not raw count: duplicates and our own test/eval runs inflate it, and widen `--num-days` if 30 days looks thin. Pick the 3 to 6 most-used topics and gather about 25 representative threads, reading each with `hex thread get <thread_id> --json` for its `resources` array (the exact tables and semantic models it touched) and `hex thread messages <thread_id> --json` for the conversation, where the agent's replies usually include the SQL it ran. Those two are what make the suite specific to us rather than generically plausible, so don't skip them. Keep notes in a scratch file outside any repo, delete it when you're done, and never copy thread content into evals.yaml. If there are no topics, or usage looks thin, duplicated or synthetic, stop and confirm with me that we should build from expected usage of our key tables instead.

4. Ground the schema and characterize each topic. For each topic or table theme, note how the question gets phrased and what a correct answer depends on: which tables, metrics, and filters the agent should reach for, and any known traps (dedup rules, excluding test/internal rows, valid-order filters, unit mismatches like cents vs dollars). Ground table and column names, in order of preference, in: (1) our workspace guides or context docs, if we maintain them (read these first); (2) the `resources` and message SQL from the threads you read in step 3; (3) the connection's prose description from `hex connection get` as a last resort. Mark any identifier you couldn't confirm against real usage with a `# TODO-verify` comment.

5. Generate `evals.yaml` as a judge-only starter suite. If an `evals.yaml` already exists, show it to me and ask before replacing it. Aim for 5 to 10 cases total. The file has a top-level `name` and a `cases:` list. Each case needs:
   - an `id` prefixed by its topic (for example `revenue-mrr-trend`)
   - a realistic `prompt`: paraphrased, never copied verbatim, with no customer names or sensitive values
   - `attempts` from 1 to 5 (higher surfaces run-to-run variance)
   - 1 to 2 `rubrics`, defaulting to `judge_thread`. Give each a yes/no `criterion` naming the expected sources and the trap to avoid, drawing on steps 3 and 4. `judge_thread` grades against the whole conversation, so it can check method: which tables the agent reached for, whether it deduplicated, whether it excluded test rows. Use `judge_final_answer` only when the criterion is about the delivered answer itself, such as whether it states a single number.
   For a case with a deterministic answer, you can also give the judge ground truth: add an `expectedSql` block to the rubric with `sql` and `dataConnectionId` keys, taking the `dataConnectionId` from `hex connection list --json` (ask me if it's ambiguous). The query runs at grade time and the judge sees its result alongside the conversation. Only do this with identifiers I've confirmed. For a strict numeric check with an explicit tolerance instead of a judge's call, see `numeric_value` in the docs from step 2.
   If my instructions conflict with your recommendation (for example, building from synthetic threads you'd have skipped), say so, proceed as I ask, and note the suite's trust level in a top-of-file comment. Here's the minimal shape:

   name: Starter suite
   cases:
     - id: revenue-mrr-trend
       prompt: "How has MRR trended over the last 6 months?"
       attempts: 1
       rubrics:
         - id: uses-revenue-model
           type: judge_thread
           criterion: Uses the canonical revenue tables and reports a month-over-month MRR trend.
     - id: customers-active-total
       prompt: "How many active customers do we have?"
       attempts: 1
       rubrics:
         - id: dedupes-and-excludes-test
           type: judge_thread
           criterion: Counts distinct customers, deduplicating fragmented ids and excluding test/internal accounts.

6. Don't run the evals yourself. When you're done, tell me to review evals.yaml and then start a run with `hex eval run evals.yaml`. Runs are async; results show up in Hex under Context Studio, then Evals (or via `hex eval get <run_id>`). As a next step, to test whether a context change (guides, warehouse descriptions) improves the agent, compare a baseline run against a run using `--preview-id` before publishing the change.
```

What the prompt does that is worth copying [inference]:

- **It grounds cases in usage, then ranks by intent, not count**:
  "duplicates and our own test/eval runs inflate it".
- **It names the evidence that makes a case specific**: the thread's
  `resources` array and the SQL in the agent's replies, "Those two are
  what make the suite specific to us rather than generically
  plausible, so don't skip them."
- **Privacy is a rule in the prompt**: scratch notes "outside any repo,
  delete it when you're done, and never copy thread content into
  evals.yaml"; prompts "paraphrased, never copied verbatim, with no
  customer names or sensitive values".
- **Unverified identifiers are marked, not guessed**: `# TODO-verify`.
- **Judge on method by default**: `judge_thread` "can check method:
  which tables the agent reached for, whether it deduplicated, whether
  it excluded test rows".
- **It ends before running**: "Don't run the evals yourself", because a
  run costs credits and the user reviews the suite first.
- **It stops rather than authenticating**: "If I'm not authenticated,
  stop and tell me to run `hex auth login`; don't authenticate on my
  behalf."

## 5. The rubric rules in Hex's eval-engineer subagent

From `hex-skills/skills/context-consultant/agents/eval-engineer.md` at
`17f928f`. [source] Selected because they go further than the docs.

**The lifecycle rule.** "A hill-climb that scores 100% isn't a
hill-climb anymore — you've climbed it. Either replace it with a harder
case, or move it into baseline as a regression guard." And: "if a
hill-climb *stays* at 0% after you've added the context meant to fix it,
the problem usually isn't the agent — the fix went to the wrong asset,
or the question isn't answerable from the data."

**Two tiers of hill-climb, "prefer the second"**:

> - **Definition/context gap** — the agent improvises because something
>   isn't pinned (a metric, a population, a table). Real, but it
>   graduates the instant you write the guide line.
> - **Analytical-reasoning trap** — the agent has every definition and
>   number it needs, computes them correctly, and still reasons wrong.
>   These don't graduate on a one-line fix and they find the model's
>   ceiling.

Failure modes to hunt: **causal overreach**, **selection bias /
confounding**, **aggregation flips** ("per-order vs per-parcel, pooled vs
cohort; Simpson's paradox"), and **intervention from a non-causal
finding**.

> **Write these rubrics as failure conditions, not checklists.**
> Enumerate the specific overclaims that *fail* the case … This catches
> what the agent wrongly *asserted*, which a "did it do X?" rubric
> misses.
>
> **Author the prompt so the data is easy and the inference is the
> trap.** The strongest of these are answers that come out ~90% right —
> correct numbers, honest denominator, even a verified mechanism — and
> fail on one reasoning step. Make that step the whole grade.

**Rubric rules**, quoted:

- "**One assertion per rubric.**"
- "**A rubric may only fail for a reason you can fix by adding
  context.** If the only remedy is 'the agent should've said that out
  loud,' that's a transparency nicety → `warnOnly` or drop it."
- "**Never contradict a pinned rule.** If a guide says cancelled values
  are sign-flipped, a rubric can't demand a positive number."
- "**Refusal-correct cases get no numeric rubric** — any number,
  including 0, is a wrong answer."
- "**`numeric_value` grabs the headline number only** — unreliable on
  multi-row/breakdown answers. Grade those with a judge."
- "**Target = SQL that reproduces the endorsed definition**, not a
  raw-table shortcut — so it recomputes each run and never goes stale."
- "**Pin `modelSelection`.** Unpinned, attempts can run on different
  models — not reproducible."
- "**`warnOnly` rubrics don't decide pass/fail.** Confirmed after a
  platform update (2026-08)."

**Reading results** (`references/evals-and-preview-loop.md`): "The
scoreboard lies in both directions; **read the underlying thread before
you trust a grade.**" An `ERRORED` case can be "Never started —
`agentChatThreadId: null`", "Started then crashed", or a genuine
failure; and a *failing* case "can mean the agent is right and your
target/definition is unpinned (fix the context, not the agent)".

**Who can see the data.** The eval-engineer runs in a coding agent that
cannot see the warehouse, so: "Numeric ground truth and 'does this gap
actually exist' must be verified by the Hex agent … `hex thread create
"<profiling question>"`, poll `hex thread get`, then bring the numbers
back. Never write a target from a number you can't verify." The outer
agent delegates data access to the inner one through the same thread
tools the MCP server exposes. [source]
