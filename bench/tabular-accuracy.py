"""Does the text format of a table change how well a model reads it?
Same rows, nine renderings, deterministic questions with computed answers.
Run: GEMINI_API_KEY=... python3 bench/tabular-accuracy.py MODEL [SEEDS] [ROWS]
Key is read from the environment only. Results go to bench/results-<model>.json.
"""
import sys, os, re, json, io, csv, random, time, urllib.request, concurrent.futures as cf

MODEL = sys.argv[1]; SEEDS = int(sys.argv[2]) if len(sys.argv) > 2 else 2
NROWS = int(sys.argv[3]) if len(sys.argv) > 3 else 120
KEY = os.environ["GEMINI_API_KEY"]
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
    if f == "kv_blocks": return "\n\n".join("\n".join(f"{c}: {san(r[c], 'null')}" for c in cols) for r in rows)
    if f == "aligned":
        w_ = [max(len(c), *(len(san(r[c])) for r in rows)) for c in cols]
        return "  ".join(c.ljust(x) for c, x in zip(cols, w_)) + "\n" + "\n".join("  ".join(san(r[c]).ljust(x) for c, x in zip(cols, w_)) for r in rows)
FORMATS = ["tsv_dash", "tsv_empty", "csv", "pipe", "md_table", "json_min", "json_columnar", "kv_blocks", "aligned"]

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

def ask(prompt):
    body = json.dumps({"contents": [{"parts": [{"text": prompt}]}], "generationConfig": {"temperature": 0, "maxOutputTokens": 4096}}).encode()
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL}:generateContent?key={KEY}"
    for attempt in range(6):
        try:
            req = urllib.request.Request(url, body, {"Content-Type": "application/json"})
            d = json.load(urllib.request.urlopen(req, timeout=120))
            p = d["candidates"][0]["content"]["parts"]
            return "".join(x.get("text", "") for x in p), d.get("usageMetadata", {}).get("promptTokenCount")
        except Exception as e:
            time.sleep(2 ** attempt + random.random())
    return None, None

def correct(kind, ans, gold):
    if ans is None: return False
    a = ans.strip().splitlines()[-1] if ans.strip() else ""
    m = re.findall(r"-?\d[\d,]*\.?\d*", a.replace(",", "") if kind != "lookup_cat" else a)
    if kind == "lookup_cat": return gold.lower() in a.lower().split() or a.strip(" .*`").upper() == gold
    if not m: return False
    try: return abs(float(m[-1] if kind != "argmax" else m[0]) - float(gold)) < 0.006
    except ValueError: return False

jobs = []
for seed in range(1, SEEDS + 1):
    rows = make(seed); qs = questions(rows, seed)
    for f in FORMATS:
        table = render(rows, f)
        for kind, q, gold in qs:
            jobs.append((f, seed, kind, gold, f"Below is the result of a database query tool call.\n\n{table}\n\nQuestion: {q}\nReply with just the answer on the last line."))

def run(j):
    f, seed, kind, gold, prompt = j
    ans, ptok = ask(prompt)
    return {"format": f, "seed": seed, "kind": kind, "gold": gold, "ans": ans, "ok": correct(kind, ans, gold), "ptok": ptok}

out = []
with cf.ThreadPoolExecutor(8) as ex:
    for i, r in enumerate(ex.map(run, jobs)):
        out.append(r)
        if i % 50 == 0: print(i, "/", len(jobs), flush=True)
json.dump(out, open(f"bench/results-{MODEL}.json", "w"), ensure_ascii=False)
print(f"\n{MODEL}  {SEEDS} seeds x {NROWS} rows; n per cell = {len(out)//len(FORMATS)}")
kinds = sorted({r['kind'] for r in out})
print(f"{'format':14}{'acc':>6}{'ptok':>8}  " + " ".join(f"{k:>10}" for k in kinds) + "   errors")
for f in FORMATS:
    rs = [r for r in out if r["format"] == f]; pt = [r["ptok"] for r in rs if r["ptok"]]
    print(f"{f:14}{100*sum(r['ok'] for r in rs)/len(rs):>5.1f}%{(sum(pt)//len(pt) if pt else 0):>8}  " +
          " ".join(f"{100*sum(r['ok'] for r in rs if r['kind']==k)/max(1,sum(1 for r in rs if r['kind']==k)):>9.0f}%" for k in kinds) +
          f"   {sum(1 for r in rs if r['ans'] is None)}")
