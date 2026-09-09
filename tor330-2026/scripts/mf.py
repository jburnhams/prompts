import re,html,sys,json,subprocess,os
UA="Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36"
PEAKS={"Mont-Blanc":"leg 1 & 7 (Courmayeur/Rutor/Malatra)","Punta-Tersiva":"leg 2 (Entrelor/Loson)",
 "Monte-Emilius":"leg 3 (Champorcher) & leg 6 (Cuney)","Corno-Bianco":"leg 4/5 (Coda/Pinter/Tournalin)",
 "Becca-di-Luseney":"leg 6 (Tsan/Vessonaz)","Mont-Velan":"leg 7 (Champillon/Malatra)"}
def get(slug,lvl):
    fn=f"mfx_{slug}_{lvl}.html"
    if not os.path.exists(fn):
        subprocess.run(["curl","-sS","-L","-m","40","-A",UA,"-o",fn,
                        f"https://www.mountain-forecast.com/peaks/{slug}/forecasts/{lvl}"],check=False)
    return open(fn,encoding="utf-8",errors="replace").read()
def cells(h,row):
    m=re.search(r'data-row="%s".*?</tr>'%row,h,re.S)
    if not m: return []
    return re.findall(r'<td[^>]*>(.*?)</td>',m.group(0),re.S)
def clean(s):
    s=re.sub(r'<[^>]+>',' ',s); return html.unescape(s).strip()
def parse(slug,lvl):
    h=get(slug,lvl)
    dates=[(d,c) for c,d in re.findall(r'colspan="(\d+)"[^>]*?data-date="(\d{4}-\d{2}-\d{2})"',h)]
    days=[]
    for d,c in dates: days+= [d]*int(c)
    tm=[clean(x) for x in cells(h,"time")]
    ph=[clean(x) for x in cells(h,"phrases")]
    tx=[clean(x) for x in cells(h,"temperature-max")]
    tn=[clean(x) for x in cells(h,"temperature-min")]
    ch=[clean(x) for x in cells(h,"temperature-chill")]
    rn=[clean(x) for x in cells(h,"rain")]
    sn=[clean(x) for x in cells(h,"snow")]
    fz=[clean(x) for x in cells(h,"freezing-level")]
    wd=[clean(x) for x in cells(h,"wind")]
    n=min(len(days),len(tm),len(ph),len(tx))
    return [dict(date=days[i],per=tm[i],phrase=ph[i],tmax=tx[i],tmin=tn[i] if i<len(tn) else "",
                 chill=ch[i] if i<len(ch) else "",rain=rn[i] if i<len(rn) else "",
                 snow=sn[i] if i<len(sn) else "",fz=fz[i] if i<len(fz) else "",
                 wind=wd[i] if i<len(wd) else "") for i in range(n)]
for slug,note in PEAKS.items():
    for lvl in ("3000","2000"):
        rows=parse(slug,lvl)
        rows=[r for r in rows if r["date"]>="2026-09-13"]
        print(f"\n### {slug} @ {lvl}m  — {note}")
        if not rows: print("   (free forecast does not reach 13 Sep at this level)"); continue
        for r in rows:
            print(f"   {r['date']} {r['per']:<7} {r['phrase'][:26]:<27} max{r['tmax']:>4} min{r['tmin']:>4} chill{r['chill']:>4}  rain:{r['rain'] or '-':<5} snow:{r['snow'] or '-':<5} 0C:{r['fz']:<8} wind:{r['wind']}")
