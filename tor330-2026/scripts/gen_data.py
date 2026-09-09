import json,math,datetime as dt,xml.etree.ElementTree as ET
NS="{http://www.topografix.com/GPX/1/1}"
G="../data/TOR330CERT2026.gpx"
r=ET.parse(G).getroot()
pts=[]
for p in r.iter(NS+"trkpt"):
    e=p.find(NS+"ele"); pts.append((float(p.get("lat")),float(p.get("lon")),float(e.text) if e is not None else 0.0))
def hav(a,b,c,d):
    R=6371000.0;q=math.radians
    x=math.sin(q(c-a)/2)**2+math.cos(q(a))*math.cos(q(c))*math.sin(q(d-b)/2)**2
    return 2*R*math.asin(math.sqrt(x))
cum=[0.0]
for i in range(1,len(pts)): cum.append(cum[-1]+hav(*pts[i-1][:2],*pts[i][:2]))
SCALE=(cum[-1]/1000.0)/336.5
sched=json.load(open("schedule.json")); wx=json.load(open("wx_best_match.json"))
H=[d["hourly"] for d in wx]; times=[dt.datetime.fromisoformat(t) for t in H[0]["time"]]
START=dt.datetime(2026,9,13,10,0)
for i,o in enumerate(sched): o["i"]=i
def sun(d,lat=45.7,lon=7.4):
    n=d.timetuple().tm_yday; g=2*math.pi/365*(n-1)
    dec=0.006918-0.399912*math.cos(g)+0.070257*math.sin(g)-0.006758*math.cos(2*g)+0.000907*math.sin(2*g)
    eqt=229.18*(0.000075+0.001868*math.cos(g)-0.032077*math.sin(g)-0.014615*math.cos(2*g)-0.040849*math.sin(2*g))
    ha=math.degrees(math.acos(math.cos(math.radians(90.833))/(math.cos(math.radians(lat))*math.cos(dec))-math.tan(math.radians(lat))*math.tan(dec)))
    noon=720-4*lon-eqt+120
    base=dt.datetime.combine(d,dt.time())
    return base+dt.timedelta(minutes=noon-4*ha), base+dt.timedelta(minutes=noon+4*ha)
def eta_at(km):
    for a,b in zip(sched,sched[1:]):
        if a["km"]<=km<=b["km"]:
            w=(km-a["km"])/max(1e-9,b["km"]-a["km"]); return a["eta"]+w*(b["eta"]-a["eta"])
    return sched[-1]["eta"]
def ele_at(km):
    t=km*SCALE*1000.0; lo,hi=0,len(cum)-1
    while lo<hi:
        m=(lo+hi)//2
        if cum[m]<t: lo=m+1
        else: hi=m
    i=max(1,lo); w=(t-cum[i-1])/max(1e-6,cum[i]-cum[i-1])
    return pts[i-1][2]+w*(pts[i][2]-pts[i-1][2])
def near_wp(km): return min(sched,key=lambda o:abs(o["km"]-km))
def hidx(when): return min(range(len(times)),key=lambda x:abs((times[x]-when).total_seconds()))
S=[]
km=0.0
while km<=336.5:
    e=eta_at(km); when=START+dt.timedelta(hours=e)
    o=near_wp(km); j=hidx(when)
    sr,ss=sun(when.date())
    S.append(dict(km=round(km,1),ele=round(ele_at(km)),eta=round(e,2),
                  t=round(H[o["i"]]["temperature_2m"][j],1),
                  ap=round(H[o["i"]]["apparent_temperature"][j],1),
                  night=1 if (when<sr or when>ss) else 0))
    km+=0.5
json.dump(dict(samples=S,sched=[{k:v for k,v in o.items() if k!="i"} for o in sched]),open("profile.json","w"))
print("samples",len(S),"maxele",max(s["ele"] for s in S),"minap",min(s["ap"] for s in S))
