import json,datetime as dt
sched=json.load(open("schedule.json")); wx=json.load(open("wx_best_match.json"))
H=[d["hourly"] for d in wx]; times=[dt.datetime.fromisoformat(t) for t in H[0]["time"]]
START=dt.datetime(2026,9,13,10,0)
for i,o in enumerate(sched): o["i"]=i; o["when"]=START+dt.timedelta(hours=o["eta"])
def hidx(w): return min(range(len(times)),key=lambda x:abs((times[x]-w).total_seconds()))
SERVICE={"R","A","R+A","BV","START","A+R"}
# assumed life-base stop for a 115 h runner; the schedule ETA is ARRIVAL, so the
# following gap otherwise includes time spent inside the base with taps available
STOP={"BV Valgrisenche":0.5,"BV Cogne":1.0,"BV Donnas":1.75,"BV Gressoney":1.75,
      "BV Valtournenche":1.25,"BV Ollomont":1.0}
svc=[o for o in sched if o["typ"] in SERVICE]
LEG=[("1",0,48.5),("2",48.5,104.0),("3",104.0,149.8),("4",149.8,203.8),
     ("5",203.8,237.5),("6",237.5,286.5),("7",286.5,336.5)]
def legof(km):
    for n,a,b in LEG:
        if a<=km<b: return n
    return "7"
gaps=[]
for a,b in zip(svc,svc[1:]):
    stop=STOP.get(a["name"],0.0)
    hrs=b["eta"]-a["eta"]-stop
    bh=(b["ts"]-a["ts"]-stop) if (a["ts"] is not None and b["ts"] is not None) else None
    inner=[o for o in sched if a["km"]<=o["km"]<=b["km"]]
    temps=[H[o["i"]]["temperature_2m"][hidx(o["when"])] for o in inner]
    tmax,tmin=max(temps),min(temps)
    dist=b["km"]-a["km"]; up=b["dp"]-a["dp"]
    tmean=sum(temps)/len(temps)
    rate=0.42+max(0,tmean-10)*0.045
    climb = up/max(dist,0.1) > 60
    if climb: rate*=1.25
    dry=[o["name"] for o in inner if o["typ"]=="W"]
    gaps.append(dict(frm=a["name"],to=b["name"],k0=a["km"],k1=b["km"],dist=dist,up=up,hrs=hrs,bhrs=bh,
                     tmax=tmax,tmin=tmin,tmean=tmean,hi=max(o["alt"] for o in inner),leg=legof(a["km"]),
                     start=a["when"]+dt.timedelta(hours=stop),need=rate*hrs,rate=rate,stop=stop,
                     dry=dry,climb=climb,ftyp=a["typ"],ttyp=b["typ"]))
gaps.sort(key=lambda g:-g["hrs"])
print("LONGEST CARRIES BETWEEN WATER POINTS — moving time, life-base stops removed (115 h plan)\n")
print(f"{'lg':>2} {'from -> to':<46}{'km':>6}{'D+':>6}{'h':>5}{'barr':>6}{'T':>5}{'~L':>5}  leave    over")
print("-"*126)
for g in gaps[:14]:
    b=f"{g['bhrs']:.1f}" if g['bhrs'] is not None else "  -"
    over=", ".join(x[:18] for x in g["dry"][:2]) or "-"
    print(f"{g['leg']:>2} {(g['frm'][:20]+' > '+g['to'][:20]):<46}{g['dist']:>6.1f}{g['up']:>6.0f}{g['hrs']:>5.1f}{b:>6}"
          f"{g['tmax']:>5.0f}{g['need']:>5.1f}  {g['start']:%a %H:%M}  {over}")
hs=sorted(x["hrs"] for x in gaps)
print(f"\n{len(gaps)} carries · median {hs[len(hs)//2]:.1f} h · mean {sum(hs)/len(hs):.1f} h · "
      f"only {sum(1 for h in hs if h>=3)} exceed 3 h, {sum(1 for h in hs if h>=4)} exceed 4 h")
print("\nWorst carry on each leg (what to fill for at the life base):")
for n,a,b in LEG:
    sub=[g for g in gaps if g["leg"]==n]
    w=max(sub,key=lambda g:g["hrs"])
    print(f"  leg {n}  {w['hrs']:.1f} h · {w['dist']:>4.1f} km · {w['up']:>4.0f} m up · T {w['tmin']:.0f}-{w['tmax']:.0f}C · "
          f"~{w['need']:.1f} L   {w['frm'][:22]} > {w['to'][:22]}")
json.dump([{k:(v.isoformat() if isinstance(v,dt.datetime) else v) for k,v in g.items()} for g in gaps],
          open("water_gaps.json","w"),indent=1)
