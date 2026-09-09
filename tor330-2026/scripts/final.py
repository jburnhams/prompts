import json,datetime as dt,math
sched=json.load(open("schedule.json")); wx=json.load(open("wx_best_match.json"))
H=[d["hourly"] for d in wx]; times=[dt.datetime.fromisoformat(t) for t in H[0]["time"]]
START=dt.datetime(2026,9,13,10,0)
for i,o in enumerate(sched): o["i"]=i; o["when"]=START+dt.timedelta(hours=o["eta"])

# global sanity
allp=[(H[i]["precipitation"][j] or 0,i,j) for i in range(len(H)) for j in range(len(times))]
mp=max(allp); print("MAX hourly precip anywhere/anytime: %.2f mm at %s on %s"%(mp[0],sched[mp[1]]["name"],times[mp[2]]))
allpp=max((H[i]["precipitation_probability"][j] or 0,i,j) for i in range(len(H)) for j in range(len(times)))
print("MAX precip probability: %d%% at %s on %s"%(allpp[0],sched[allpp[1]]["name"],times[allpp[2]]))
alls=max((H[i]["snowfall"][j] or 0,i,j) for i in range(len(H)) for j in range(len(times)))
print("MAX hourly snowfall: %.2f cm at %s on %s"%(alls[0],sched[alls[1]]["name"],times[alls[2]]))
mint=min((H[i]["temperature_2m"][j],i,j) for i in range(len(H)) for j in range(len(times)))
print("MIN temp anywhere/anytime: %.1fC at %s (%dm) on %s"%(mint[0],sched[mint[1]]["name"],sched[mint[1]]["alt"],times[mint[2]]))
fz=min((H[i]["freezing_level_height"][j],i,j) for i in range(len(H)) for j in range(len(times)))
print("MIN freezing level: %.0fm  (route high point 3295m Col Loson)"%fz[0])

def sun(d,lat=45.7,lon=7.4):
    n=d.timetuple().tm_yday
    g=2*math.pi/365*(n-1); dec=0.006918-0.399912*math.cos(g)+0.070257*math.sin(g)-0.006758*math.cos(2*g)+0.000907*math.sin(2*g)
    eqt=229.18*(0.000075+0.001868*math.cos(g)-0.032077*math.sin(g)-0.014615*math.cos(2*g)-0.040849*math.sin(2*g))
    ha=math.degrees(math.acos(math.cos(math.radians(90.833))/(math.cos(math.radians(lat))*math.cos(dec))-math.tan(math.radians(lat))*math.tan(dec)))
    noon=720-4*lon-eqt+120  # CEST
    return (dt.datetime.combine(d,dt.time())+dt.timedelta(minutes=noon-4*ha),
            dt.datetime.combine(d,dt.time())+dt.timedelta(minutes=noon+4*ha))
print("\nDaylight (CEST):")
for d in range(13,20):
    sr,ss=sun(dt.date(2026,9,d)); print(f"  Sep {d}: sunrise {sr:%H:%M}  sunset {ss:%H:%M}")

LEGS=[("1","Courmayeur","Valgrisenche",0,48.5),("2","Valgrisenche","Cogne",48.5,104.0),
      ("3","Cogne","Donnas",104.0,149.8),("4","Donnas","Gressoney",149.8,203.8),
      ("5","Gressoney","Valtournenche",203.8,237.5),("6","Valtournenche","Ollomont",237.5,286.5),
      ("7","Ollomont","Courmayeur",286.5,336.5)]
print("\n=== LEG SUMMARY FOR DROP-BAG DECISIONS ===")
for no,a,b,k0,k1 in LEGS:
    pts=[o for o in sched if k0-0.01<=o["km"]<=k1+0.01]
    t0,t1=pts[0]["when"],pts[-1]["when"]
    slack=dt.timedelta(hours=max(2.0,0.10*pts[-1]["eta"]))
    wa=max(t0-dt.timedelta(hours=1),START); wb=t1+slack
    jj=[j for j,t in enumerate(times) if wa<=t<=wb]
    ii=[o["i"] for o in pts]
    # coldest at ETA and in window
    cold_eta=min(((min(range(len(times)),key=lambda x:abs((times[x]-o['when']).total_seconds())),o) for o in pts),
                 key=lambda z:H[z[1]["i"]]["apparent_temperature"][z[0]])
    j,o=cold_eta
    cw=min(((H[i]["apparent_temperature"][j2],H[i]["temperature_2m"][j2],i,j2) for i in ii for j2 in jj))
    gust=max((H[i]["wind_gusts_10m"][j2],i,j2) for i in ii for j2 in jj)
    pmax=max((H[i]["precipitation_probability"][j2] or 0) for i in ii for j2 in jj)
    ptot=max(sum(H[i]["precipitation"][j2] or 0 for j2 in jj) for i in ii)
    hi=max(x["alt"] for x in pts); fzm=min(H[i]["freezing_level_height"][j2] for i in ii for j2 in jj)
    dur=(t1-t0).total_seconds()/3600
    # night hours in leg
    nh=0
    for x in range(int(dur)):
        t=t0+dt.timedelta(hours=x); sr,ss=sun(t.date())
        if t<sr or t>ss: nh+=1
    print(f"\nLEG {no}: {a} -> {b}   km {k0}-{k1} ({k1-k0:.0f}km)  high point {hi}m")
    print(f"  planned: {t0:%a %d %b %H:%M} -> {t1:%a %d %b %H:%M}   ({dur:.0f}h, ~{nh}h in darkness)")
    print(f"  coldest on plan : {o['name']} {o['alt']}m at {o['when']:%a %H:%M} -> {H[o['i']]['temperature_2m'][j]:.0f}C, feels {H[o['i']]['apparent_temperature'][j]:.0f}C, wind {H[o['i']]['wind_speed_10m'][j]:.0f}km/h")
    print(f"  if {slack.total_seconds()/3600:.0f}h late: {cw[1]:.0f}C air, feels {cw[0]:.0f}C (at {sched[cw[2]]['name']}, {times[cw[3]]:%a %H:%M})")
    print(f"  wind peak {gust[0]:.0f}km/h gust at {sched[gust[1]]['name']} ({times[gust[2]]:%a %H:%M})")
    print(f"  rain: max prob {pmax:.0f}%, max total {ptot:.1f}mm | snow: 0.0cm | freezing level min {fzm:.0f}m = {fzm-hi:+.0f}m above leg high point")
