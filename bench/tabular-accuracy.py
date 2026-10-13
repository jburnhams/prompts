"""Does the text format of a table change how well a model reads it?
Same rows, nine renderings, deterministic questions with computed answers.
Run: python3 bench/tabular-accuracy.py PROVIDER:MODEL [SEEDS] [ROWS] [FIRST_SEED]
  gemini:gemini-3.8-flash   (GEMINI_API_KEY)     openrouter:google/gemma-4-31b-it:free (OPENROUTER_API_KEY)
  groq:openai/gpt-oss-120b  (GROQ_API_KEY)       ollama:gpt-oss:120b (OLLAMA_API_KEY, ollama.com cloud)
  cohere:command-a-03-2025  (COHERE_API_KEY)     zai:glm-5.3 (ZAI_API_KEY)
  nvidia:mistralai/mistral-large-2-instruct (NVIDIA_API_KEY, build.nvidia.com)
BATCHED: one request per (format, dataset) carrying all 24 questions, because the free tier
allows only ~20 requests per model per day. 10 formats x 1 dataset = 10 requests per model (FORMATS=a,b limits it).
Key is read from the environment only. Results go to bench/results-<provider>-<model>-s<first seed>.json.
"""
import sys, os, re, json, io, csv, random, time, urllib.request, urllib.error, concurrent.futures as cf

PROVIDER, MODEL = sys.argv[1].split(":", 1)
SLUG = re.sub(r"[^A-Za-z0-9.-]+", "_", PROVIDER + "-" + MODEL)
SEEDS = int(sys.argv[2]) if len(sys.argv) > 2 else 2
NROWS = int(sys.argv[3]) if len(sys.argv) > 3 else 120
FIRST = int(sys.argv[4]) if len(sys.argv) > 4 else 1
BASES = {"openrouter": "https://openrouter.ai/api/v1", "groq": "https://api.groq.com/openai/v1", "ollama": "https://ollama.com/v1", "cohere": "https://api.cohere.ai/compatibility/v1", "zai": "https://api.z.ai/api/paas/v4", "nvidia": "https://integrate.api.nvidia.com/v1"}
KEY = os.environ[PROVIDER.upper() + "_API_KEY"]
import threading
_lock = threading.Lock(); _next = [0.0]
def pace(gap=4.4):
    with _lock:
        now = time.time(); wait = max(0.0, _next[0] - now); _next[0] = max(now, _next[0]) + gap
    time.sleep(wait)
REG = ["EMEA", "NA", "APAC", "LATAM"]; CUR = ["USD", "EUR", "GBP"]
NAMES = ["Acme, Inc.", "Smith & Sons", "O'Brien Ltd", 'Zoë "Z" Café', "Müller GmbH", "Tokyo Trading Co.", "Nguyen Bros", "Plain Co"]
NOTES = [None, "", "rush order", "call back: ask for J. Lee, re: invoice #4412", "line1\nline2", "tab\there", 'said "no", twice']

def make(seed):
    rnd = random.Random(seed); rows = []
    for i in range(NROWS):
        rows.append({"order_id": 4000 + i * 7 + rnd.randint(0, 6), "customer": rnd.choice(NAMES), "region": rnd.choice(REG),
                     "ordered_at": f"2026-{1+i%9:02d}-{10+i%18:02d}", "revenue": None if rnd.random() < .12 else round(rnd.uniform(1, 5000), 2),
                     "currency": rnd.choice(CUR), "is_refunded": rnd.random() < .15, "note": rnd.choice(NOTES)})
    return rows

def s(v, null=""):
    if v is None: return null
    if isinstance(v, bool): return "true" if v else "false"
    return str(v)
def san(v, null="-"): return s(v, null).replace("\t", " ").replace("\r", " ").replace("\n", " ⏎ ")

def render(rows, f):
    cols = list(rows[0])
    if f == "tsv_dash":  return "\t".join(cols) + "\n" + "\n".join("\t".join(san(r[c], "-") for c in cols) for r in rows)
    if f == "tsv_empty": return "\t".join(cols) + "\n" + "\n".join("\t".join(san(r[c], "") for c in cols) for r in rows)
    if f == "csv":
        b = io.StringIO(); w = csv.writer(b, lineterminator="\n"); w.writerow(cols)
        for r in rows: w.writerow([s(r[c]) for c in cols])
        return b.getvalue()
    if f == "pipe": return "|".join(cols) + "\n" + "\n".join("|".join(san(r[c]).replace("|", "/") for c in cols) for r in rows)
    if f == "md_table": return "| " + " | ".join(cols) + " |\n|" + "|".join("---" for _ in cols) + "|\n" + "\n".join("| " + " | ".join(san(r[c]) for c in cols) + " |" for r in rows)
    if f == "json_min": return json.dumps(rows, separators=(",", ":"), ensure_ascii=False)
    if f == "json_columnar": return json.dumps({"columns": cols, "rows": [[r[c] for c in cols] for r in rows]}, separators=(",", ":"), ensure_ascii=False)
    if f == "jsonl_arrays": return "\n".join(json.dumps(x, separators=(",", ":"), ensure_ascii=False) for x in [cols] + [[r[c] for c in cols] for r in rows])
    if f == "kv_blocks": return "\n\n".join("\n".join(f"{c}: {san(r[c], 'null')}" for c in cols) for r in rows)
    if f == "aligned":
        w_ = [max(len(c), *(len(san(r[c])) for r in rows)) for c in cols]
        return "  ".join(c.ljust(x) for c, x in zip(cols, w_)) + "\n" + "\n".join("  ".join(san(r[c]).ljust(x) for c, x in zip(cols, w_)) for r in rows)
FORMATS = ["tsv_dash", "tsv_empty", "csv", "pipe", "md_table", "json_min", "json_columnar", "jsonl_arrays", "kv_blocks", "aligned"]
if os.environ.get("FORMATS"):   # e.g. FORMATS=jsonl_arrays to run one format; results get a suffix
    FORMATS = os.environ["FORMATS"].split(","); SLUG += "-" + "+".join(FORMATS)

def questions(rows, seed):
    rnd = random.Random(seed * 99); qs = []
    nn = [r for r in rows if r["revenue"] is not None]
    for r in rnd.sample(nn, 6): qs.append(("lookup_num", f"What is the revenue of order_id {r['order_id']}? Answer with the number only.", r["revenue"]))
    for r in rnd.sample(rows, 4): qs.append(("lookup_cat", f"What is the region of order_id {r['order_id']}? Answer with the region code only.", r["region"]))
    for _ in range(5):
        g, c = rnd.choice(REG), rnd.choice(CUR)
        qs.append(("count_and", f"How many rows have region {g} and currency {c}? Answer with an integer.", sum(1 for r in rows if r["region"] == g and r["currency"] == c)))
    for g in rnd.sample(REG, 3): qs.append(("count_null", f"How many rows with region {g} have no revenue value (missing)? Answer with an integer.", sum(1 for r in rows if r["region"] == g and r["revenue"] is None)))
    for g in rnd.sample(REG, 3):
        m = max((r for r in rows if r["region"] == g and r["revenue"] is not None), key=lambda r: r["revenue"])
        qs.append(("argmax", f"Among rows with region {g}, which order_id has the highest revenue? Answer with the order_id only.", m["order_id"]))
    for g in rnd.sample(REG, 3): qs.append(("count_bool", f"How many rows with region {g} are refunded (is_refunded true)? Answer with an integer.", sum(1 for r in rows if r["region"] == g and r["is_refunded"])))
    return qs

PACE_GAP = 4.4
def ask_openai_compat(prompt):
    body = json.dumps({"model": MODEL, "messages": [{"role": "user", "content": prompt}], "temperature": 0, "max_tokens": 8192}).encode()
    for attempt in range(3):
        pace(PACE_GAP)
        try:
            req = urllib.request.Request(BASES[PROVIDER] + "/chat/completions", body, {"Content-Type": "application/json", "Authorization": f"Bearer {KEY}"})
            d = json.load(urllib.request.urlopen(req, timeout=300))
            if "error" in d: raise RuntimeError(str(d["error"])[:200])
            u = d.get("usage", {})
            return d["choices"][0]["message"].get("content") or "", {"promptTokenCount": u.get("prompt_tokens")}
        except urllib.error.HTTPError as e:
            msg = e.read().decode("utf8", "replace")
            if "per-day" in msg.lower() or "per day" in msg.lower(): return "DAILY_QUOTA: " + msg[:200], {}
            time.sleep(15)
        except Exception:
            time.sleep(10)
    return None, {}

def ask(prompt):
    if PROVIDER != "gemini": return ask_openai_compat(prompt)
    body = json.dumps({"contents": [{"parts": [{"text": prompt}]}], "generationConfig": {"temperature": 0, "maxOutputTokens": 8192}}).encode()
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL}:generateContent?key={KEY}"
    for attempt in range(3):
        pace(PACE_GAP)
        try:
            req = urllib.request.Request(url, body, {"Content-Type": "application/json"})
            d = json.load(urllib.request.urlopen(req, timeout=300))
            p = d["candidates"][0]["content"]["parts"]
            return "".join(x.get("text", "") for x in p if not x.get("thought")), d.get("usageMetadata", {})
        except urllib.error.HTTPError as e:
            msg = e.read().decode("utf8", "replace")
            if "PerDay" in msg or "per day" in msg.lower(): return "DAILY_QUOTA: " + msg[:200], {}
            m = re.search(r"retry in ([\d.]+)s", msg)
            time.sleep(float(m.group(1)) + 1 if m else 5)
        except Exception:
            time.sleep(5)
    return None, {}

def correct(kind, ans, gold):
    if ans is None: return False
    a = ans.strip()
    if kind == "lookup_cat": return a.strip(" .*`\"").upper() == gold
    m = re.findall(r"-?\d[\d,]*\.?\d*", a.replace(",", ""))
    if not m: return False
    try: return abs(float(m[0]) - float(gold)) < 0.006
    except ValueError: return False

def parse(text, n):
    got = {}
    for line in (text or "").splitlines():
        m = re.match(r"\W*Q?(\d+)\s*[:.)-]\s*(.+)$", line.strip())
        if m and 1 <= int(m.group(1)) <= n: got[int(m.group(1))] = m.group(2)
    return got

jobs = []
for seed in range(FIRST, FIRST + SEEDS):
    rows = make(seed); qs = questions(rows, seed)
    for f in FORMATS:
        qtext = "\n".join(f"Q{i+1}. {q}" for i, (_, q, _) in enumerate(qs))
        prompt = (f"Below is the result of a database query tool call.\n\n{render(rows, f)}\n\n"
                  f"Answer every question below using only that table.\n{qtext}\n\n"
                  f"Reply with exactly one line per question, in the form `Q<number>: <answer>`, and nothing else.")
        jobs.append((f, seed, qs, prompt))

def run(j):
    f, seed, qs, prompt = j
    text, usage = ask(prompt); got = parse(text, len(qs))
    return [{"format": f, "seed": seed, "kind": k, "gold": g, "ans": got.get(i + 1), "ok": correct(k, got.get(i + 1), g),
             "ptok": usage.get("promptTokenCount"), "raw_ok": text is not None and not str(text).startswith("DAILY_QUOTA")}
            for i, (k, _, g) in enumerate(qs)] + [{"format": f, "seed": seed, "kind": "_raw", "raw": text}]

res = []
with cf.ThreadPoolExecutor(2) as ex:
    for i, r in enumerate(ex.map(run, jobs)):
        res.extend(r); print(i + 1, "/", len(jobs), flush=True)
        json.dump(res, open(f"bench/results-{SLUG}-s{FIRST}.json", "w"), ensure_ascii=False)
out = [r for r in res if r["kind"] != "_raw"]
print(f"\n{PROVIDER}:{MODEL}  {SEEDS} dataset(s) x {NROWS} rows; questions per format = {len(out)//len(FORMATS)}")
kinds = sorted({r['kind'] for r in out})
print(f"{'format':14}{'acc':>6}{'ptok':>8}  " + " ".join(f"{k:>10}" for k in kinds) + "   unanswered")
for f in FORMATS:
    rs = [r for r in out if r["format"] == f]; pt = [r["ptok"] for r in rs if r["ptok"]]
    print(f"{f:14}{100*sum(r['ok'] for r in rs)/len(rs):>5.1f}%{(sum(pt)//len(pt) if pt else 0):>8}  " +
          " ".join(f"{100*sum(r['ok'] for r in rs if r['kind']==k)/max(1,sum(1 for r in rs if r['kind']==k)):>9.0f}%" for k in kinds) +
          f"   {sum(1 for r in rs if r['ans'] is None)}")
