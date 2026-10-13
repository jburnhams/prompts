"""Token cost of the same rows in eleven text formats, and of the null literal.
Run: pip install tiktoken && python3 bench/tabular-formats.py
Tokenizers are OpenAI o200k_base / cl100k_base, NOT Claude's: trust direction, not margins.
Synthetic data (seeded): commas, quotes, newlines, tabs in text cells; ~8% nulls.
"""
import json, csv, io, random, tiktoken
random.seed(7)
encs = {n: tiktoken.get_encoding(n) for n in ("o200k_base","cl100k_base")}
REG=["EMEA","NA","APAC","LATAM"]; CUR=["USD","EUR","GBP"]
NAMES=["Acme, Inc.","Smith & Sons","O'Brien Ltd","Zoë \"Z\" Café","Müller GmbH","Tokyo Trading Co.","Nguyen Bros","Plain Co"]
NOTES=[None,"","rush order","call back: ask for J. Lee, re: invoice #4412","line1\nline2","tab\there","said \"no\", twice"]
def flat(n, wide=0, dirty=True):
    rows=[]
    for i in range(n):
        r={"order_id":1000+i,"customer":random.choice(NAMES) if dirty else f"cust{i%9}",
           "region":random.choice(REG),"ordered_at":f"2026-0{1+i%9}-{10+i%18}T0{i%10}:15:00Z",
           "revenue":None if random.random()<.08 else round(random.uniform(1,5000),2),
           "currency":random.choice(CUR),"is_refunded":random.random()<.04,
           "note":random.choice(NOTES) if dirty else None}
        for k in range(wide): r[f"metric_{k}"]=None if random.random()<.6 else round(random.uniform(0,100),1)
        rows.append(r)
    return rows
def s(v,null=""): 
    if v is None: return null
    if isinstance(v,bool): return "true" if v else "false"
    return str(v)
def san(v,null="-"):  # sanitize for tsv/pipe: tabs/newlines -> space
    return s(v,null).replace("\t"," ").replace("\r"," ").replace("\n"," ⏎ ")
def fmts(rows):
    cols=list(rows[0]); out={}
    out["json_pretty"]=json.dumps(rows,indent=2,ensure_ascii=False)
    out["json_min"]=json.dumps(rows,separators=(",",":"),ensure_ascii=False)
    out["jsonl"]="\n".join(json.dumps(r,separators=(",",":"),ensure_ascii=False) for r in rows)
    out["jsonl_arrays"]="\n".join(json.dumps(x,separators=(",",":"),ensure_ascii=False) for x in [cols]+[[r[c] for c in cols] for r in rows])
    out["json_columnar"]=json.dumps({"columns":cols,"rows":[[r[c] for c in cols] for r in rows]},separators=(",",":"),ensure_ascii=False)
    b=io.StringIO(); w=csv.writer(b,lineterminator="\n"); w.writerow(cols)
    for r in rows: w.writerow([s(r[c]) for c in cols])
    out["csv_quoted"]=b.getvalue()
    out["tsv"]="\t".join(cols)+"\n"+"\n".join("\t".join(san(r[c]) for c in cols) for r in rows)
    out["pipe"]="|".join(cols)+"\n"+"\n".join("|".join(san(r[c]).replace("|","/") for c in cols) for r in rows)
    out["md_table"]="| "+" | ".join(cols)+" |\n|"+"|".join("---" for _ in cols)+"|\n"+"\n".join("| "+" | ".join(san(r[c]).replace("|","\\|") for c in cols)+" |" for r in rows)
    w_=[max(len(c),*(len(san(r[c])) for r in rows)) for c in cols]
    out["aligned"]="  ".join(c.ljust(x) for c,x in zip(cols,w_))+"\n"+"\n".join("  ".join(san(r[c]).ljust(x) for c,x in zip(cols,w_)) for r in rows)
    out["kv_blocks"]="\n\n".join("\n".join(f"{c}: {san(r[c])}" for c in cols if r[c] is not None) for r in rows)
    out["md_kv"]="\n\n".join(f"## Record {i+1}\n"+"\n".join(f"{c}: {san(r[c])}" for c in cols) for i,r in enumerate(rows))
    return out
def run(title, rows):
    f=fmts(rows); print(f"\n### {title}  ({len(rows)} rows x {len(rows[0])} cols)")
    base={k:len(e.encode(f['tsv'])) for k,e in encs.items()}
    print(f"{'format':14}{'o200k':>8}{'x tsv':>7}{'cl100k':>8}{'x tsv':>7}{'bytes':>8}")
    for k,v in f.items():
        a=len(encs['o200k_base'].encode(v)); b=len(encs['cl100k_base'].encode(v))
        print(f"{k:14}{a:>8}{a/base['o200k_base']:>7.2f}{b:>8}{b/base['cl100k_base']:>7.2f}{len(v):>8}")
run("narrow, clean", flat(50,dirty=False))
run("narrow, dirty text (commas/quotes/newlines)", flat(50))
run("narrow, dirty, 500 rows", flat(500))
run("wide (30 metric cols, 60% null)", flat(50,wide=22,dirty=False))
run("5 rows only", flat(5))
# escaping cost on the dirty set: quoted-csv vs tsv

# ---- null-literal sweep ----
enc = encs["o200k_base"]
def tab(rows, sep, null, pad=False):
    cols=list(rows[0])
    def c(v):
        x=san(v,null) if True else v
        return x
    return sep.join(cols)+"\n"+"\n".join(sep.join(c(r[k]) for k in cols) for r in rows)
for title,rows in [("narrow dirty 50 (8% null revenue, 40% null note)",flat(50)),("wide 60% null",flat(50,wide=22,dirty=False)),("sparse 90% null",None)]:
    if rows is None:
        random.seed(3); rows=flat(50,wide=22,dirty=False)
        for r in rows:
            for k in list(r)[8:]:
                if random.random()<.75: r[k]=None
    print("\n",title)
    for sep,name in [("\t","tsv"),("|","pipe"),(",","csv-ish")]:
        print(f"  {name:8}",end="")
        for null in ["","-","NULL","null","NA","∅"]:
            print(f"  {null!r:7}:{len(enc.encode(tab(rows,sep,null))):>6}",end="")
        print()
