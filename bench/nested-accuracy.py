"""Accuracy on NESTED and ESCAPED values: does the cell rule in agent-design/data.md §2h
(TSV, bare scalars, compact JSON in a cell, JSON-quoted when unsafe) read as well as the
usual alternatives? Same orders rendered three ways, 14 questions with computed answers.
Run: NVIDIA_API_KEY=... python3 bench/nested-accuracy.py MODEL   (e.g. moonshotai/kimi-k3)
"""
import sys, os, re, json, random, time, urllib.request, urllib.error
sys.path.insert(0, os.path.dirname(__file__)); import render
MODEL = sys.argv[1]; KEY = os.environ["NVIDIA_API_KEY"]
rnd = random.Random(11)
SKU = ["A1", "B7", "C3", "D9", "E2"]; CITY = ["Leeds", "Oslo", "Lima", "Kyiv", "Pune"]; TAG = ["gift", "rush", "b2b", "fragile"]
NOTES = [None, "", "call back\nafter 5pm", 'said "no", twice', "tab\there", "plain note"]
orders = []
for i in range(60):
    orders.append({"id": 9000 + i, "customer": rnd.choice(["Acme, Inc.", 'Zoë "Z" Café', "Plain Co", "O'Brien"]),
                   "lines": [{"sku": rnd.choice(SKU), "qty": rnd.randint(1, 9)} for _ in range(rnd.randint(1, 4))],
                   "tags": rnd.sample(TAG, rnd.randint(0, 3)), "ship": {"city": rnd.choice(CITY), "geo": [round(rnd.uniform(-60, 60), 2), round(rnd.uniform(-90, 90), 2)]},
                   "note": rnd.choice(NOTES)})
def fmt(f):
    if f == "tsv_json_cells": return render.table(orders)
    if f == "json_min": return json.dumps(orders, separators=(",", ":"), ensure_ascii=False)
    if f == "json_pretty": return json.dumps(orders, indent=2, ensure_ascii=False)
qs = []
for o in rnd.sample(orders, 3): qs.append((f"How many line items does order {o['id']} have? Integer only.", len(o["lines"])))
for o in rnd.sample(orders, 3): qs.append((f"What is the total quantity across all line items of order {o['id']}? Integer only.", sum(l["qty"] for l in o["lines"])))
for c in rnd.sample(CITY, 2): qs.append((f"How many orders ship to {c}? Integer only.", sum(o["ship"]["city"] == c for o in orders)))
for t in rnd.sample(TAG, 2): qs.append((f"How many orders have the tag '{t}'? Integer only.", sum(t in o["tags"] for o in orders)))
qs.append(("How many orders have a null note (missing, not empty text)? Integer only.", sum(o["note"] is None for o in orders)))
qs.append(("How many orders have an empty-string note (present but empty)? Integer only.", sum(o["note"] == "" for o in orders)))
o = next(o for o in orders if o["note"] and "\n" in o["note"])
qs.append((f"Does the note of order {o['id']} contain a line break? Answer yes or no.", "yes"))
o = next(o for o in orders if o["note"] and "\t" in o["note"])
qs.append((f"Does the note of order {o['id']} contain a tab character? Answer yes or no.", "yes"))
def ask(prompt):
    body = json.dumps({"model": MODEL, "messages": [{"role": "user", "content": prompt}], "temperature": 0, "max_tokens": 8192}).encode()
    for _ in range(3):
        try:
            r = urllib.request.Request("https://integrate.api.nvidia.com/v1/chat/completions", body, {"Content-Type": "application/json", "Authorization": "Bearer " + KEY})
            d = json.load(urllib.request.urlopen(r, timeout=300)); return d["choices"][0]["message"].get("content") or "", d["usage"]["prompt_tokens"]
        except Exception: time.sleep(10)
    return None, None
res = {}
for f in ["tsv_json_cells", "json_min", "json_pretty"]:
    qtext = "\n".join(f"Q{i+1}. {q}" for i, (q, _) in enumerate(qs))
    text, ptok = ask(f"Below is the result of a tool call.\n\n{fmt(f)}\n\nAnswer every question using only that data.\n{qtext}\n\nReply with exactly one line per question, `Q<number>: <answer>`, and nothing else.")
    got = {int(m.group(1)): m.group(2).strip() for l in (text or "").splitlines() if (m := re.match(r"\W*Q(\d+)\s*[:.)-]\s*(.+)$", l.strip()))}
    ok = [str(got.get(i + 1, "")).strip(" .*`").lower() == str(g).lower() for i, (_, g) in enumerate(qs)]
    res[f] = {"ptok": ptok, "answered": len(got), "ok": ok, "raw": text}
    print(f"{MODEL}  {f:15} prompt_tokens={ptok}  correct={sum(ok)}/{len(qs)}  answered={len(got)}", flush=True)
json.dump(res, open(f"bench/results-nested-{re.sub('[^A-Za-z0-9.-]+','_',MODEL)}.json", "w"), ensure_ascii=False)
