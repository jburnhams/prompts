import json,datetime as dt,statistics as st
sched=json.load(open("schedule.json")); wx=json.load(open("wx_best_match.json"))
START=dt.datetime(2026,9,13,10,0)
H=[d["hourly"] for d in wx]
times=[dt.datetime.fromisoformat(t) for t in H[0]["time"]]
def series(i,k): return H[i][k]
def val(i,k,when):
    j=min(range(len(times)),key=lambda x:abs((times[x]-when).total_seconds()))
    v=H[i][k]
    return v[j] if j<len(v) else None
for o,i in zip(sched,range(len(sched))): o["i"]=i; o["when"]=START+dt.timedelta(hours=o["eta"])

WCODE={0:"clear",1:"mostly clear",2:"part cloud",3:"overcast",45:"fog",48:"rime fog",51:"lt drizzle",53:"drizzle",
55:"hvy drizzle",56:"frz drizzle",57:"frz drizzle",61:"lt rain",63:"rain",65:"heavy rain",66:"frz rain",67:"frz rain",
71:"lt snow",73:"snow",75:"heavy snow",77:"snow grains",80:"lt showers",81:"showers",82:"violent showers",
85:"snow showers",86:"hvy snow showers",95:"thunderstorm",96:"tstorm+hail",99:"tstorm+hail"}

print("=== REGIONAL DAILY PICTURE (mean over all 79 route points) ===")
for d in range(13,20):
    idxs=[j for j,t in enumerate(times) if t.day==d]
    pr=st.mean(sum(H[i]["precipitation"][j] or 0 for j in idxs) for i in range(len(H)))
    fz=st.mean(st.mean([H[i]["freezing_level_height"][j] or 0 for j in idxs]) for i in range(len(H)))
    fzmin=min(min([H[i]["freezing_level_height"][j] or 9999 for j in idxs]) for i in range(len(H)))
    cc=st.mean(st.mean([H[i]["cloud_cover"][j] or 0 for j in idxs]) for i in range(len(H)))
    gm=max(max([H[i]["wind_gusts_10m"][j] or 0 for j in idxs]) for i in range(len(H)))
    sn=st.mean(sum(H[i]["snowfall"][j] or 0 for j in idxs) for i in range(len(H)))
    print(f"  Sep {d}: precip {pr:5.1f}mm/24h  snow {sn:4.1f}cm  freezing lvl mean {fz:4.0f}m (min {fzmin:4.0f}m)  cloud {cc:3.0f}%  max gust {gm:3.0f}km/h")

LEGS=[("1  Courmayeur->Valgrisenche",0,48.5),("2  Valgrisenche->Cogne",48.5,104.0),("3  Cogne->Donnas",104.0,149.8),
      ("4  Donnas->Gressoney",149.8,203.8),("5  Gressoney->Valtournenche",203.8,237.5),
      ("6  Valtournenche->Ollomont",237.5,286.5),("7  Ollomont->Courmayeur",286.5,336.5)]
print("\n=== PER-LEG (at planned ETA, plus +/- slack window) ===")
for nm,a,b in LEGS:
    pts=[o for o in sched if a-0.01<=o["km"]<=b+0.01]
    t0,t1=pts[0]["when"],pts[-1]["when"]
    slack=dt.timedelta(hours=max(2.0,0.10*pts[-1]["eta"]))
    print(f"\n--- LEG {nm}  km {a}-{b}  ETA {t0:%a %d %H:%M} -> {t1:%a %d %H:%M}  (slack +/-{slack.total_seconds()/3600:.0f}h)")
    print(f"    {'km':>6} {'alt':>5}  {'point':<26} {'ETA':<12} {'T':>6} {'feels':>6} {'wind/gust':>11} {'prec':>6} {'snow':>5} {'0C lvl':>7}  sky")
    rows=[]
    for o in pts:
        i=o["i"]; w=o["when"]
        t=val(i,"temperature_2m",w); ap=val(i,"apparent_temperature",w)
        ws=val(i,"wind_speed_10m",w); wg=val(i,"wind_gusts_10m",w)
        pr=val(i,"precipitation",w); sn=val(i,"snowfall",w); fz=val(i,"freezing_level_height",w)
        pp=val(i,"precipitation_probability",w); wc=val(i,"weather_code",w)
        rows.append((o,t,ap,ws,wg,pr,sn,fz,pp,wc))
        mark="*" if o["typ"] in("BV","START","A+R") else " "
        print(f"    {o['km']:6.1f} {o['alt']:5d}{mark}{o['name'][:25]:<26} {w:%a %H:%M}    {t:5.1f} {ap:6.1f} {ws:5.0f}/{wg:<5.0f} {pr:5.1f} {sn:4.1f} {fz:7.0f}  {WCODE.get(wc,wc)} {pp or 0:.0f}%")
    # window aggregate
    ws0=t0-slack; ws1=t1+slack
    jj=[j for j,t in enumerate(times) if ws0<=t<=ws1]
    ii=[o["i"] for o in pts]
    tmin=min(H[i]["temperature_2m"][j] for i in ii for j in jj)
    apmin=min(H[i]["apparent_temperature"][j] for i in ii for j in jj)
    gmax=max(H[i]["wind_gusts_10m"][j] for i in ii for j in jj)
    prmax=max(sum(H[i]["precipitation"][j] or 0 for j in jj) for i in ii)
    snmax=max(sum(H[i]["snowfall"][j] or 0 for j in jj) for i in ii)
    ppmax=max((H[i]["precipitation_probability"][j] or 0) for i in ii for j in jj)
    fzmin=min(H[i]["freezing_level_height"][j] for i in ii for j in jj)
    hi=max(o["alt"] for o in pts)
    print(f"    WINDOW WORST-CASE: Tmin {tmin:.1f}C  feels {apmin:.1f}C  gust {gmax:.0f}km/h  precip up to {prmax:.1f}mm  snow {snmax:.1f}cm  Pmax {ppmax:.0f}%  min 0C-level {fzmin:.0f}m  vs leg high point {hi}m")
