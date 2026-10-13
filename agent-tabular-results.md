# Tabular tool results

How to render rows — a SQL result, a dataframe, a CSV read — as the **text
block a model reads**. Delimiter, nulls, escaping, caps, and the point at
which a table should stop being a table.

This is the narrow question underneath two docs that already exist:
[`agent-tool-result-transport.md`](./agent-tool-result-transport.md) §4 and
§9 say *put a compact rendering in `content`, not JSON in both channels*,
and [`agent-design/data.md`](./agent-design/data.md) §2c says `:rows:`
returns "delimited text". **Neither says which delimiter, what a null looks
like, or what to do with a comma inside a cell.** This doc answers those,
with two measurements of its own and a survey of what other data-analysis
tools and MCP servers do.

**Short answer.** A header line, then one row per line, **tab-delimited**,
values sanitised so a tab or newline never appears inside a cell, **an empty
cell for null** with the convention stated in a one-line preamble, a row
count and a "next call" line on truncation, and — the finding that matters
more than any of the above — **do not rely on the model to count or aggregate
over rows it can read unless you know the model can; give it a tool that
does.** Section 6 has the whole recommendation; section 5 explains why
format turned out to be the smaller lever.

---

## 1. What this repo already says

| Where | What it settles | What it leaves open |
|---|---|---|
| `agent-tool-result-transport.md` §4, §9 | `content` for the model, `structuredContent` for programs, never the same JSON in both; SEP-1624 measured 284 vs 189 tokens for the same result as JSON vs prose | which prose |
| `agent-tool-result-transport.md` §1a | JSON-string escaping costs 1.11× on prose, 1.22× on quote-heavy text, 1.48× double-encoded | tables specifically |
| `agent-design/data.md` §2b | the *default view* of a table is column summaries (type, null count, cardinality, range), not rows | the row view |
| `agent-design/data.md` §2c | `:rows:1-20` returns "rows by position, as delimited text" | delimiter, nulls, escaping, cap |
| `agent-design/data.md` §5 | integer codes for `NULL`/`NA`/`NaN` rejected: "the model does better with `NA` than with `1`" | what the literal is |
| `data-agents/positron/` | the same ambiguity (`"NA"` the string vs missing) named as unsolved in every harness | — |

---

## 2. What other tools do

Read from source or docs; where a claim is a vendor's own it is marked.

| Tool | Row format returned to the model | Notes |
|---|---|---|
| **Axiom MCP** ([post](https://axiom.co/blog/designing-mcp-servers-for-wide-events)) | **CSV with a header** | Chosen explicitly over JSON: 166 vs 235 tokens for five rows (`o200k_base`, minified JSON), ~29% fewer. A global *cell* budget (not row budget), a "Showing 100 of 2,340 rows" note, narrow default time window, and for wide schemas it **scores columns and keeps the top N** (priority names, fill rate, variety). The author concedes "CSV drops types and nesting" |
| **Reference `postgres` MCP server** (archived) | `JSON.stringify(result.rows, null, 2)` | Pretty-printed array of objects. Measured below at 2.3–3× the cost of TSV |
| **Reference `sqlite` MCP server** (archived) | `str(results)` | A Python repr of a list of dicts. No serialisation at all |
| **`squirreling-mcp`** (Hyperparam) | Markdown table, 100-row cap | `... and N more rows (showing first 100 rows)`; string cells truncated to 1,000 chars and the *header* marked `(truncated)`; no cursor or ref. See `data-agents/hyperparam/` |
| **Vanna 2.0 `run_sql`** | first 1,000 chars of CSV **plus** the filename | Preview and handle travel together. See `data-agents/vanna/` |
| **`sqldb-mcp-server`** (community) | columnar JSON: `{columns, rows}` plus `total`/`returned` counts | Presented by its author as the token-efficient format |
| **Microsoft SQL Server MCP** (community) | `structuredContent` **and** a short text summary | The §4 pattern, done as recommended |
| **Snowflake / Databricks community servers** | mixed: arrays of objects, markdown tables, CSV *export to file* | No convention; CSV mostly appears as the "full result" side-channel |
| **Posit `btw`** | `skim` (per-column summary) by default, `json` on request | The model picks the projection. `data-agents/btw/` |
| **TOON** | tabular arrays as `key[N]{cols}:` then CSV-like rows | Self-reported 74% vs 70% for JSON on mixed structures, with versions disagreeing (76.4/75.0, 72.2/69.0). The project itself says CSV is smaller for flat tables |

What converges: **CSV-like for model-facing rows, a cap with a count, a
side-channel (file, ref, export) for the whole result.** What does not:
every server picks its own delimiter, and none documents its null literal.

Not found: any MCP specification guidance on tabular rendering. The spec
leaves the content of a `TextContent` block to the server.

---

## 3. Measurement one — token cost

`bench/tabular-formats.py`. The same synthetic rows (8 columns: ids, a
customer name with commas and quotes, categoricals, timestamps, a nullable
float, a bool, a free-text note with commas, quotes, newlines and tabs;
~8% null revenue) rendered eleven ways. Tokenizers: `o200k_base` and
`cl100k_base`. **Both are OpenAI's, not Claude's** — the two agree to
within 1% here, which suggests the direction transfers, but re-run on your
own tokenizer before deciding on a margin.

Relative to TSV (50 rows, dirty text):

| Format | o200k | × TSV |
|---|---:|---:|
| TSV (tab, sanitised, `-` for null) | 1,789 | 1.00 |
| CSV (RFC 4180 quoting, empty null) | 1,758 | **0.98** |
| columnar JSON `{"columns":[…],"rows":[[…]]}` | 1,908 | 1.07 |
| **JSONL, header array then one array per row** (`["a","b"]` newline `[1,2]` …) | 1,916 | 1.07 |
| pipe-delimited | 1,854 | 1.04 |
| Markdown table | 2,092 | 1.17 |
| fixed-width, space-padded | 1,993 | 1.11 |
| `key: value` blocks, nulls omitted | 2,936 | 1.64 |
| minified JSON, array of objects | 2,919 | 1.63 |
| JSONL | 2,967 | 1.66 |
| `## Record N` + `key: value` | 3,264 | 1.82 |
| pretty JSON, array of objects | 4,230 | **2.36** |

The ratios hold at 5 rows (pretty JSON 2.22×), 50, and 500 (2.32×).

Three things to take from this, one of which corrects what I told you
earlier in this session:

1. **Array-of-objects JSON is the expensive choice by a wide margin**, and
   that is what two of the reference MCP servers return. Keys repeat on
   every row. Pretty-printing adds another ~45% over minified.
2. **CSV quoting did not cost tokens here.** I said earlier that quoting
   and escaping make CSV more expensive than TSV. On data where 30–40% of
   rows contain a comma, quote or newline, quoted CSV came out *2% cheaper*
   than sanitised TSV (the `⏎` replacement for newlines is not free). The
   argument for TSV is therefore **not tokens**; it is that sanitising is a
   simpler contract than quoting, and that the failure mode of a missed
   escape is smaller (see §5).
3. **Tab is not automatically cheaper than pipe.** It depends on the null
   literal — next.

### The null literal costs more than the delimiter

Same data, cost by delimiter and by what a null is written as (o200k):

| Table | null written as | TSV | pipe | CSV |
|---|---|---:|---:|---:|
| 50 × 8, ~8% null | empty | 1,872 | 1,932 | 1,863 |
| | `-` | 1,885 | 1,945 | 1,870 |
| | `NULL` | 1,878 | 1,958 | 1,876 |
| 50 × 30, 60% null | **empty** | **3,576** | 3,440 | 3,391 |
| | `-` | 4,743 | 4,093 | 4,013 |
| | `NULL` | 4,040 | 4,824 | 4,041 |
| | `NA` | 4,771 | 4,824 | 4,772 |
| | `∅` | 5,502 | 5,555 | 5,503 |
| 50 × 30, 90% null | **empty** | **2,210** | 2,351 | 2,313 |
| | `-` | 4,117 | 3,177 | 3,081 |
| | `NULL` | 3,124 | 4,214 | 3,125 |

On a dense table the literal is a ~1% decision. On a sparse one it is a
**2× decision**: consecutive delimiters merge into one token when the cells
between them are empty, and a `-` or `NA` in each cell breaks that. The
cheapest literal also differs by delimiter (`NULL` for tab, `-` for pipe and
comma), which is tokenizer-specific and exactly the kind of margin that
should be re-measured on the target model.

**Cost of the preferred choice.** An empty cell is the cheapest on every
sparse table, but it is also the one a model can least easily count columns
in (`\t\t\t\t`). Whether that matters was one of the things the accuracy
experiment below was meant to show, and did not, for reasons given there.

---

## 4. What external studies say about accuracy

All of this is **one model, one data shape, or self-reported**. None is
conclusive; together they say *format affects accuracy, by a small and
unstable amount, and the best format for tokens is not the best for
accuracy.*

- **[Improving Agents](https://www.improvingagents.com/blog/best-input-data-format-for-llms)**
  — 11 formats, GPT-4.1-nano only, 1,000 synthetic employee records,
  1,000 single-field lookups. Markdown-KV 60.7% (52,104 tokens); XML 56.0%;
  INI 55.7%; YAML 54.7%; HTML 53.6%; JSON 52.3%; **Markdown table 51.9%
  (25,140)**; natural language 49.6%; JSONL 45.0%; **CSV 44.3% (19,524)**;
  pipe-delimited 41.1% (43,098). The authors list their own limits: one
  model, large table with headers not repeated (which penalises header-based
  formats), one question shape. Note the pipe-delimited row costs 2.2× CSV
  in tokens there, which does not match my measurement (1.04×) — their
  pipe variant was evidently space-padded or otherwise different.
- **TQA-Bench** (multi-table QA): CSV the most token-efficient; HTML nearly
  3× the tokens.
- **JTON** (arXiv 2604.05865): CSV wins on raw tokens in all three datasets,
  but loses the advantage once types or nesting are needed — it cannot tell
  null from empty string.
- **SQL-generation study** (9,649 trials, 11 models, as summarised in a
  search result, not read in full): format did not significantly affect
  aggregate accuracy; individual models varied. Model tier gap (21 pp)
  dwarfed any format effect.
- **TeleTables**: Markdown best for Llama; JSON within 0.2 pp of HTML at
  27% fewer tokens for Llama-3.3-70B.

The honest reading: if a format effect exists it is a few percentage points
and model-dependent, and only the one study that found a large effect used a
very small model.

---

## 5. Measurement two — accuracy, and what it could not show

`bench/tabular-accuracy.py`. One synthetic table (120 rows × 8 columns, the
same dirty-text shape as §3), rendered nine ways (`tsv` with `-` nulls,
`tsv` with empty nulls, quoted CSV, pipe, Markdown table, minified JSON,
columnar JSON, `key: value` blocks, fixed-width), and 24 questions with
answers computed in Python: numeric lookup ×6, categorical lookup ×4,
two-filter count ×5, count-of-nulls ×3, argmax-in-group ×3, filtered
bool-count ×3. **Batched** — one request per (format, model) carrying all 24
questions — because the free tiers used allow ~20 requests per model per
day, which an earlier one-question-per-request design burned through.
Temperature 0.

### What ran, and what did not

Every key supplied for this was a free tier. Most did not yield data, and
that is recorded here rather than hidden:

| Provider / model | Outcome |
|---|---|
| Gemini 3.5 / 3.6 / 3.7 / 3.8 Flash, 3.1 Flash-Lite | **Free-tier quota exhausted** — partly by my own first design (432 single-question calls per model) before the ~20/day limit was known. No usable data |
| Groq (`gpt-oss-120b`, `qwen3.8-27b`) | **HTTP 403, error 1010** from this environment's egress for every request, including a one-word prompt. Not a quota problem; not investigated further |
| Ollama cloud: `kimi-k3` | HTTP 402, model not in the free plan |
| Ollama cloud: `deepseek-v4.1-flash`, `glm-5.3-flash` | no reply recorded |
| Ollama cloud: `gpt-oss:120b` | replies, but empty `content` on the 24-question prompt (a probe with a trivial question returned an answer and a separate `reasoning` field — most likely the reasoning consumed the token budget); two attempts |
| OpenRouter free: `gemma-4-31b-it`, `nemotron-3-super` | upstream 429 / truncated at `finish_reason: length` |
| Cohere `command-r-plus-08-2024`, z.ai `glm-4.7`, `glm-5.3` | no usable reply |
| Cohere `command-a-plus-05-2026` | replied, but with a reasoning preamble instead of the requested `Q<n>: answer` lines; parser got nothing it could score |
| **Cohere `command-a-03-2025`** | **9/9 batches** |
| **Ollama cloud `gemma4:31b`** | **8/9** (one format returned no reply) |
| **OpenRouter free `poolside/laguna-s-2.1`** | **8/9** (Markdown table batch returned no reply) |
| NVIDIA build.nvidia.com (`integrate.api.nvidia.com`), added late: **`moonshotai/kimi-k3`** | **9/9 batches** |
| NVIDIA: **`z-ai/glm-5.3-flash`** | **5/9** (four batches returned nothing) |
| NVIDIA: **`google/gemma-4-31b-it`** | **9/9** — same model as the Ollama run, different host |
| NVIDIA: `mistral-large-2-instruct`, `nemotron-70b-instruct`, `nemotron-3-super-120b`, `deepseek-v4.1-flash`, `gpt-oss-20b` | no usable reply |

Result files for the usable runs are in `bench/`. Runs that returned
nothing were not kept.

### Results

Correct out of 24 per cell (one dataset, one run per cell, temperature 0).
`—` is a batch that returned no reply. The first two columns are weaker
models, the last two are strong reasoning models.

| Format | command-a-03 | gemma-4-31b (NVIDIA) | gemma4:31b (Ollama) | laguna-s-2.1 | **glm-5.3-flash** | **kimi-k3** |
|---|---:|---:|---:|---:|---:|---:|
| tsv, `-` null | 10 | 15 | 15 | 10 | 23 | 23 |
| tsv, empty null | 13 | 15 | — | 10 | 24 | 21 |
| csv | 13 | 14 | 15 | 11 | — | 24 |
| pipe | 15 | 15 | 15 | 11 | 23 | 21 |
| md_table | 12 | 15 | 15 | — | — | 24 |
| json_min | 10 | 14 | 14 | 12 | — | 24 |
| json_columnar | 11 | 16 | 15 | 10 | 23 | 24 |
| kv_blocks | 12 | 15 | 15 | 11 | 24 | 24 |
| aligned | 12 | 14 | 14 | 14 | — | 24 |
| **all answered cells** | 50% | 62% | 62% | 46% | **97.5%** | **96%** |

**Added after the table above: JSONL with a header array and one array per
row** (`jsonl_arrays`), run on the three NVIDIA-hosted models that had
answered (one batch each, same dataset and questions): `kimi-k3` 21/24,
`gemma-4-31b-it` 15/24, `glm-5.3-flash` no reply. That is level with every
other layout for gemma (14–16) and in the lower group for kimi (21, with
`tsv` empty-null and `pipe`; the other layouts 23–24). The three kimi
misses — the two-filter count 9→8, the argmax 4668→4088 and the bool count
1→0 — are **the same three items it missed in `tsv` empty-null and in
`pipe`, with the same wrong answers**. Four layouts, one set of errors: those
items are hard for that model on this table, and the layout is not what
decides it.

By question type (summed over the formats each model answered):

| Question | command-a-03 | gemma-4-31b (NV) | laguna-s-2.1 | glm-5.3-flash | kimi-k3 |
|---|---:|---:|---:|---:|---:|
| numeric lookup | 52/54 | 54/54 | 48/48 | 30/30 | 54/54 |
| categorical lookup | 36/36 | 36/36 | 31/32 | 20/20 | 36/36 |
| argmax in a group | 6/27 | 18/27 | 8/24 | 15/15 | 25/27 |
| count of nulls in a group | 5/27 | 16/27 | 1/24 | 14/15 | 27/27 |
| filtered bool count | 9/27 | 9/27 | 1/24 | 13/15 | 25/27 |
| **two-filter count** | **0/45** | **0/45** | **0/40** | 25/25 | 42/45 |

(The Ollama-hosted gemma4:31b is not repeated: 62% overall, two-filter
count 0/40 — the same as the NVIDIA-hosted copy.)

### What this does and does not show

**Shows**

1. **Reading a single cell is solved in every format and every model.**
   Lookups were right 100% of the time for the strong models and 98–100% for
   the weak ones, including empty-null TSV and minified JSON. At 120 rows ×
   8 columns the delimiter, null literal and quoting did not make a cell
   unreadable.
2. **Counting over 120 rows by reading splits models cleanly in two, and
   format does not move the line.** `command-a-03`, `gemma-4-31b` (both
   hosts) and `laguna-s-2.1` got the two-filter count wrong **170 of 170**
   times, undercounting by about half (answers of 5–6 against true counts of
   8–11). `kimi-k3` got 42 of 45 and `glm-5.3-flash` 25 of 25. The same
   table, the same question, a different model: the result is a property of
   the model, not of the rendering. **An earlier draft of this doc said
   "no model counts"; that was written before the two strong models
   returned and is withdrawn.**
3. **Where a strong model does err, the errors are off-by-one counts and
   one repeated misread, not format-shaped failures.** kimi-k3's seven
   misses: counts one too low (8→7, 9→8, 1→0) and the same wrong argmax
   (4088 for 4668) in two formats — `tsv` (empty null) and `pipe`. Both are
   the minimal-framing, unpadded delimited layouts, which is suggestive,
   but it is a 3-question gap on n = 24 and the same layouts score 24/24
   and 23/24 elsewhere in the table.

**Does not show**

- **No reliable format effect.** The spread within a model is 0–3
  questions for the strong models and driven entirely by the counting
  questions for the weak ones; there is no format that wins or loses
  consistently across models (pipe: best for command-a, level for gemma,
  lower for kimi; aligned: best for laguna, level elsewhere). The one
  hint — kimi's two 21s are both TSV-empty-null and pipe — is a hypothesis
  to test with more datasets, not a finding. In particular, **it does not
  establish that empty-null is risky**: glm-5.3-flash scored 24/24 on it.
- Nothing about Claude. None of these is an Anthropic model.
- 24 questions × 1 dataset × 1 run per cell. Strong models are near ceiling
  (96–97.5%), which leaves almost no room to see a format effect in either
  direction; a harder task (larger table, more columns, multi-step) is what
  would. The free tiers used could not supply that.

---

## 6. Recommendation

For a tool that returns rows to a model in a `content` text block:

1. **Delimited text with a header line, tab-delimited.** The tokens are a
   wash against CSV (§3), the accuracy is a wash across formats (§5), and
   what remains is that "no tab or newline inside a cell" is easier to
   guarantee than correct quoting and fails more softly. If your values
   already come through a CSV writer and you trust it, CSV is equally
   defensible; **do not use pretty or array-of-objects JSON** (2.3–3×).
2. **Sanitise, don't escape.** Replace a tab with a space; replace a newline
   inside a cell with a visible marker (`⏎`) or lift a long multi-line field
   out of the table into its own block, keyed by the row's id.
3. **State the conventions in one preamble line**, the same place you put the
   count: `120 of 5,400 rows · tab-separated · empty = null · next:
   offset=120`. A convention the model is told costs nothing; one it has to
   infer costs a wrong answer.
4. **Null is an empty cell on sparse tables** (§3: up to 2× cheaper), and on
   dense tables anything short is fine. If real empty strings can occur,
   render those distinctly (`""`) and say so. If you cannot tolerate the
   ambiguity, use a short literal and accept the cost. Prefer the literal the
   *tokenizer* likes: re-measure `NULL` vs `-` vs `NA` on your model.
5. **Cap by cells, not rows** (Axiom's rule), with the total in the preamble
   and the next call named. Wide tables: score and drop columns, or switch to
   `key: value` for a *few* records (the 1.6–1.9× premium buys nothing on
   lookup, which §5 shows is already saturated).
6. **Move counting, summing, ranking and grouping out of the model's head
   unless you know the model can do it.** The experiment's clearest result
   is that the ability to answer aggregate questions from 120 visible rows
   is a property of the model: three mid-tier models (four runs; one model on two hosts) got the two-filter
   count wrong 170 of 170 times, two strong reasoning models got it right
   67 of 70. Format did not change which side a model was on. A tool that
   returns rows invites the model to answer aggregate questions from them;
   if the harness may run on a weaker model, say in the tool description
   what to call instead, and prefer returning the aggregate. This is the
   same shape as `agent-design/data.md`: the default view is column
   summaries and `:sql:` is the reducing operation.
7. **If `content` must double as machine data, use a columnar JSON shape**:
   either one `{"columns":…,"rows":…}` object or **JSONL with a header
   array and one array per row**. They cost the same (1.06–1.08× TSV, §3),
   and neither is an array of objects. The JSONL form is the better of the
   two for a tool result: every line parses on its own, a truncation at a
   line boundary still leaves valid JSON, nulls are explicit (`null`), and a
   cell can never be mistaken for a delimiter. Its one cost over TSV is the
   ~7% above and quotes around every string.
8. **Write it as a named function**, not inline in each tool. The
   alternatives differ by 2–3× in tokens and by nothing in accuracy; that is
   a decision to make once.

### Changes this implies in the design

- `agent-design/data.md` §2c: `:rows:` output is specified as above
  (tab-delimited, header, preamble line, sanitised cells, empty = null
  stated). Done in this pass.
- `agent-design/artifacts.md` line 163 ("the sheet as delimited text"): same
  rule applies to the xlsx/csv/tsv row.
- No tool-surface change.

---

## 7. Open

- **Re-measure on Claude's tokenizer and on Claude models.** Everything
  here is OpenAI tokenizers and non-Anthropic models. Section 3's ratios are
  stable across two tokenizers; that is not proof they hold for a third.
- **A real accuracy comparison** at several table sizes (the larger the
  table, the more headers-repeated formats like `key: value` should win,
  per the Improving Agents authors' own caveat), several datasets, repeated
  runs, and a model population that does not depend on free-tier quotas.
- **Whether declaring the convention in the preamble measurably helps.**
  Not tested; the recommendation rests on it being free.
- **Wide and sparse tables with empty-null TSV.** The column-counting risk
  is real and untested.
- **Prompt-side formats** (a table the *user* pastes, a table inside a
  system prompt) may behave differently from a tool result; this doc is only
  about the latter.

---

## 8. Reproducing

```bash
pip install tiktoken
python3 bench/tabular-formats.py          # §3, no network, no keys

# §5 — pick any provider you have a key for; free tiers will run dry
GEMINI_API_KEY=…      python3 bench/tabular-accuracy.py gemini:gemini-3.8-flash
OPENROUTER_API_KEY=…  python3 bench/tabular-accuracy.py openrouter:poolside/laguna-s-2.1:free
OLLAMA_API_KEY=…      python3 bench/tabular-accuracy.py ollama:gemma4:31b
COHERE_API_KEY=…      python3 bench/tabular-accuracy.py cohere:command-a-03-2025
GROQ_API_KEY=…        python3 bench/tabular-accuracy.py groq:openai/gpt-oss-120b
ZAI_API_KEY=…         python3 bench/tabular-accuracy.py zai:glm-5.3
NVIDIA_API_KEY=…      python3 bench/tabular-accuracy.py nvidia:moonshotai/kimi-k3
```

Keys are read from the environment only. The script makes 9 requests per
model (one per format), paces itself to ~14/minute, and writes
`bench/results-<provider>-<model>-s1.json`, including the raw reply of every
batch so a scoring or parsing problem is inspectable.

Sources: [Improving Agents](https://www.improvingagents.com/blog/best-input-data-format-for-llms) ·
[Axiom](https://axiom.co/blog/designing-mcp-servers-for-wide-events) ·
[TQA-Bench](https://arxiv.org/pdf/2411.19504) ·
[JTON](https://arxiv.org/pdf/2604.05865) ·
[TeleTables](https://arxiv.org/pdf/2601.04202) ·
[Notation Matters](https://arxiv.org/pdf/2605.29676) (not read — PDF did not extract) ·
[SEP-1624](https://github.com/modelcontextprotocol/modelcontextprotocol/issues/1624) ·
the archived reference [`postgres`](https://github.com/modelcontextprotocol/servers-archived/blob/main/src/postgres/index.ts) and
[`sqlite`](https://github.com/modelcontextprotocol/servers-archived/blob/main/src/sqlite/src/mcp_server_sqlite/server.py) servers.
