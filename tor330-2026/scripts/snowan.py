import json,datetime as dt
D=json.load(open("snowhist.json")); P=D["points"]; W=D["wx"]
t=[dt.datetime.fromisoformat(x) for x in W[0]["hourly"]["time"]]
NOW=dt.datetime(2026,9,10,6,0)
nn=[i for i,v in enumerate(W[0]["hourly"]["snow_depth"]) if v is not None]
print("snow_depth non-null from",t[nn[0]] if nn else "never","to",t[nn[-1]] if nn else "-")
print(f"\n{'point':<28}{'alt':>6} | {'snowfall cm':>11} {'last30d':>8} | {'snowdepth cm':>12} | {'snow-hrs':>8} {'last event':>12}")
print("-"*104)
rows=[]
for p,w in zip(P,W):
    h=w["hourly"]; sf=h["snowfall"]; sd=h["snow_depth"]; fz=h["freezing_level_height"]; pr=h["precipitation"]
    idx_now=max(i for i,x in enumerate(t) if x<=NOW)
    tot=sum(sf[i] or 0 for i in range(idx_now))
    l30=sum(sf[i] or 0 for i in range(idx_now) if t[i]>=NOW-dt.timedelta(days=30))
    cur=None
    for i in range(idx_now,-1,-1):
        if sd[i] is not None: cur=sd[i]*100; break
    # physically-grounded: hours with precip while freezing level below this altitude
    snowhrs=[i for i in range(idx_now) if (pr[i] or 0)>0.05 and (fz[i] or 9999)<p["alt"]]
    last=t[snowhrs[-1]].strftime("%d %b") if snowhrs else "-"
    rows.append((p,tot,l30,cur,len(snowhrs),last,
                 sum(pr[i] or 0 for i in snowhrs),
                 sum(pr[i] or 0 for i in snowhrs if t[i]>=NOW-dt.timedelta(days=30))))
for p,tot,l30,cur,nh,last,mm,mm30 in sorted(rows,key=lambda r:-r[0]["alt"]):
    print(f"{p['name'][:27]:<28}{p['alt']:>6} | {tot:>11.1f} {l30:>8.1f} | {('%.1f'%cur) if cur is not None else '   n/a':>12} | {nh:>8} {last:>12}   ({mm:.0f}mm as snow, {mm30:.0f}mm last 30d)")
json.dump([[r[0]["name"],r[0]["alt"],r[1],r[2],r[3],r[4],r[5],r[6],r[7]] for r in rows],open("snow_summary.json","w"))
