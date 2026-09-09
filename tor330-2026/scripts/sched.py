import json,math,datetime as dt,xml.etree.ElementTree as ET
from waypoints import WPTS
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
GTOT=cum[-1]/1000.0
OFFTOT=336.5
SCALE=GTOT/OFFTOT
def at_km(km):
    t=km*SCALE*1000.0
    lo,hi=0,len(cum)-1
    while lo<hi:
        m=(lo+hi)//2
        if cum[m]<t: lo=m+1
        else: hi=m
    i=max(1,lo); w=(t-cum[i-1])/max(1e-6,cum[i]-cum[i-1])
    return (pts[i-1][0]+w*(pts[i][0]-pts[i-1][0]), pts[i-1][1]+w*(pts[i][1]-pts[i-1][1]), pts[i-1][2]+w*(pts[i][2]-pts[i-1][2]))

D0=dt.datetime(2026,9,11); START=dt.datetime(2026,9,13,10,0)
def parse(s):
    if not s: return None
    d,t=s.split(); hh,mm=t.split(".")
    return D0+dt.timedelta(days=int(d[1:])-1,hours=int(hh),minutes=int(mm))
off=[]
for name,alt,typ,km,dp,f,s,_la,_lo in WPTS:
    tf=parse(f); ts=parse(s)
    la,lo,gel=at_km(km)
    off.append(dict(name=name,alt=alt,typ=typ,km=km,dp=dp,lat=round(la,5),lon=round(lo,5),gele=round(gel),
                    tf=(tf-START).total_seconds()/3600 if tf else None,
                    ts=(ts-START).total_seconds()/3600 if ts else None))
# sanity: official altitude vs GPX track elevation at that km
worst=sorted(off,key=lambda o:-abs(o["gele"]-o["alt"]))[:6]
print("largest official-vs-GPX elevation gaps:", [(o["name"],o["alt"],o["gele"]) for o in worst])
for key in ("tf","ts"):
    prev=-1e9
    for o in off:
        if o[key] is None: continue
        if o[key]<prev: o[key]=prev
        prev=o[key]
print("elite finish %.2fh   barrier finish %.2fh"%(off[-1]["tf"],off[-1]["ts"]))

TOT_EFF=off[-1]["km"]+off[-1]["dp"]/100.0
TARGET=115.0
f_end=(TARGET-off[-1]["tf"])/(off[-1]["ts"]-off[-1]["tf"]); F0=0.50
print("f0=%.3f f_end=%.3f"%(F0,f_end))
for o in off:
    o["p"]=(o["km"]+o["dp"]/100.0)/TOT_EFF
    fr=F0+(f_end-F0)*o["p"]
    o["eta"]=o["tf"]+fr*(o["ts"]-o["tf"]) if o["tf"] is not None and o["ts"] is not None else None
off[0]["eta"]=0.0
idx=[i for i,o in enumerate(off) if o["eta"] is not None]
for i,o in enumerate(off):
    if o["eta"] is not None: continue
    a,b=off[max(j for j in idx if j<i)],off[min(j for j in idx if j>i)]
    w=(o["p"]-a["p"])/(b["p"]-a["p"]); o["eta"]=a["eta"]+w*(b["eta"]-a["eta"])
prev=-1
for o in off:
    o["eta"]=max(o["eta"],prev+0.01); prev=o["eta"]
    o["dtime"]=(START+dt.timedelta(hours=o["eta"])).strftime("%a %d %H:%M")
json.dump(off,open("schedule.json","w"),indent=1)
BV=[o for o in off if o["typ"] in ("BV","START","A+R")]
print("\nLIFE-BASE SPLITS (115h plan)")
for o in BV: print(f"  {o['km']:6.1f}km  {o['name']:<22} {o['dtime']}   {o['eta']:6.1f}h")
