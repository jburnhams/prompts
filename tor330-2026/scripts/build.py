import xml.etree.ElementTree as ET, math, json, re, unicodedata
G="../data/TOR330CERT2026.gpx"
NS="{http://www.topografix.com/GPX/1/1}"
r=ET.parse(G).getroot()
pts=[]
for p in r.iter(NS+"trkpt"):
    e=p.find(NS+"ele")
    pts.append((float(p.get("lat")),float(p.get("lon")),float(e.text) if e is not None else 0.0))
def hav(a,b,c,d):
    R=6371000.0;q=math.radians
    x=math.sin(q(c-a)/2)**2+math.cos(q(a))*math.cos(q(c))*math.sin(q(d-b)/2)**2
    return 2*R*math.asin(math.sqrt(x))
cum=[0.0]
for i in range(1,len(pts)): cum.append(cum[-1]+hav(*pts[i-1][:2],*pts[i][:2]))
TOT=cum[-1]/1000.0

gw=[]
for w in r.iter(NS+"wpt"):
    n=w.find(NS+"name"); e=w.find(NS+"ele")
    gw.append({"name":n.text,"lat":float(w.get("lat")),"lon":float(w.get("lon")),
               "gele":float(e.text) if e is not None else None})
# snap to track
for w in gw:
    best=(1e18,-1)
    for i,p in enumerate(pts):
        d=(p[0]-w["lat"])**2+(p[1]-w["lon"])**2
        if d<best[0]: best=(d,i)
    w["idx"]=best[1]; w["km"]=cum[best[1]]/1000.0
    w["snap_m"]=hav(w["lat"],w["lon"],pts[best[1]][0],pts[best[1]][1])
gw.sort(key=lambda x:x["km"])
json.dump({"total_km":TOT,"wpts":gw},open("gpx_wpts.json","w"),indent=1)
for w in gw: print(f"{w['km']:7.1f}  {w['name']:<30} {w['lat']:.5f},{w['lon']:.5f}  gpxele={w['gele']}  snap={w['snap_m']:.0f}m")
print("TOTAL",round(TOT,1))
