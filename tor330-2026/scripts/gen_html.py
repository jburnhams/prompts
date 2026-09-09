# -*- coding: utf-8 -*-
import json,datetime as dt,html,math
from kit import LEGS
P=json.load(open("profile.json")); S=P["samples"]; sched=P["sched"]
wx=json.load(open("wx_best_match.json")); H=[d["hourly"] for d in wx]
times=[dt.datetime.fromisoformat(t) for t in H[0]["time"]]
START=dt.datetime(2026,9,13,10,0)
for i,o in enumerate(sched): o["i"]=i; o["when"]=START+dt.timedelta(hours=o["eta"])
def hidx(w): return min(range(len(times)),key=lambda x:abs((times[x]-w).total_seconds()))
def th(n,dec=0):
    return f"{n:,.{dec}f}".replace(",","\u2009")
def band(ap):
    if ap<=-2: return "freeze"
    if ap<=3:  return "cold"
    if ap<=9:  return "cool"
    if ap<=16: return "mild"
    return "hot"
# ---------- profile svg ----------
W,Hh=1160.0,290.0; PADL,PADR,PADT,PADB=8.0,8.0,26.0,46.0
KM=336.5; EMIN,EMAX=250.0,3400.0
def X(k): return PADL+(k/KM)*(W-PADL-PADR)
def Y(e): return PADT+(1-(e-EMIN)/(EMAX-EMIN))*(Hh-PADT-PADB)
line=" ".join(f"{X(s['km']):.1f},{Y(s['ele']):.1f}" for s in S)
area=f"M {X(0):.1f},{Y(EMIN):.1f} L "+line.replace(" "," L ")+f" L {X(KM):.1f},{Y(EMIN):.1f} Z"
# night bands
nb=[];run=None
for s in S:
    if s["night"] and run is None: run=s["km"]
    if not s["night"] and run is not None: nb.append((run,s["km"])); run=None
if run is not None: nb.append((run,KM))
night_rects="".join(f'<rect x="{X(a):.1f}" y="{PADT:.1f}" width="{max(1.0,X(b)-X(a)):.1f}" height="{Hh-PADT-PADB:.1f}" class="nightband"/>' for a,b in nb)
# feels-like strip
sy=Hh-PADB+8; sh=11.0
strip="".join(f'<rect x="{X(s["km"]):.1f}" y="{sy:.1f}" width="{(W-PADL-PADR)/len(S)+0.7:.2f}" height="{sh:.1f}" class="tb-{band(s["ap"])}"/>' for s in S)
# life bases
BV=[o for o in sched if o["typ"] in("BV","START","A+R")]
bvm="".join(f'<line x1="{X(o["km"]):.1f}" y1="{PADT:.1f}" x2="{X(o["km"]):.1f}" y2="{Hh-PADB:.1f}" class="bvline"/>' for o in BV)
def shortname(n): return n.replace("BV ","").replace("Courmayeur START","Courmayeur").replace("Courmayeur FINISH","Finish")
lab=[]
for o in BV:
    x=X(o["km"]); anc="middle"
    if o["km"]<10: anc="start"; x=X(o["km"])+1
    if o["km"]>330: anc="end"; x=X(o["km"])-1
    lab.append(f'<text x="{x:.1f}" y="{PADT-9:.1f}" text-anchor="{anc}" class="bvlab">{html.escape(shortname(o["name"]))}</text>')
bvlab="".join(lab)
# cold markers: coldest apparent point of each leg
cold=[]
for L in LEGS:
    seg=[s for s in S if L["k0"]<=s["km"]<=L["k1"]]
    c=min(seg,key=lambda s:s["ap"]); cold.append((L["no"],c))
cm=""
for no,c in cold:
    if c["ap"]>6: continue
    cm+=(f'<circle cx="{X(c["km"]):.1f}" cy="{Y(c["ele"]):.1f}" r="3.4" class="coldpt"/>'
         f'<text x="{X(c["km"]):.1f}" y="{Y(c["ele"])-9:.1f}" text-anchor="middle" class="coldlab">{c["ap"]:.0f}°</text>')
grid="".join(f'<line x1="{PADL}" y1="{Y(e):.1f}" x2="{W-PADR}" y2="{Y(e):.1f}" class="grid"/>'            f'<text x="{W-PADR-3:.1f}" y="{Y(e)-4:.1f}" text-anchor="end" class="gridlab">{e//1000} 000 m</text>'            for e in (1000,2000,3000))
kmt="".join(f'<text x="{X(k):.1f}" y="{Hh-PADB+34:.1f}" text-anchor="middle" class="kmlab">{k}</text>' for k in (0,50,100,150,200,250,300,336))
SVG=(f'<svg viewBox="0 0 {W:.0f} {Hh:.0f}" class="profile" role="img" '
 f'aria-label="TOR330 route profile with night sections and feels-like temperature">'
 f'{night_rects}{grid}<path d="{area}" class="prof-area"/><polyline points="{line}" class="prof-line"/>'
 f'{bvm}{cm}{bvlab}{strip}{kmt}</svg>')
# ---------- leg cards ----------
def sun_(d,lat=45.7,lon=7.4):
    n=d.timetuple().tm_yday; g=2*math.pi/365*(n-1)
    dec=0.006918-0.399912*math.cos(g)+0.070257*math.sin(g)-0.006758*math.cos(2*g)+0.000907*math.sin(2*g)
    eqt=229.18*(0.000075+0.001868*math.cos(g)-0.032077*math.sin(g)-0.014615*math.cos(2*g)-0.040849*math.sin(2*g))
    ha=math.degrees(math.acos(math.cos(math.radians(90.833))/(math.cos(math.radians(lat))*math.cos(dec))-math.tan(math.radians(lat))*math.tan(dec)))
    noon=720-4*lon-eqt+120; b=dt.datetime.combine(d,dt.time())
    return b+dt.timedelta(minutes=noon-4*ha), b+dt.timedelta(minutes=noon+4*ha)
cards=[]
for L in LEGS:
    pts=[o for o in sched if L["k0"]-0.01<=o["km"]<=L["k1"]+0.01]
    t0,t1=pts[0]["when"],pts[-1]["when"]
    slack=max(2.0,0.10*pts[-1]["eta"])
    wa=max(t0-dt.timedelta(hours=1),START); wb=t1+dt.timedelta(hours=slack)
    jj=[j for j,t in enumerate(times) if wa<=t<=wb]; ii=[o["i"] for o in pts]
    coldest=min(((H[o["i"]]["apparent_temperature"][hidx(o["when"])],
                  H[o["i"]]["temperature_2m"][hidx(o["when"])],o) for o in pts),key=lambda z:z[0])
    late=min(H[i]["apparent_temperature"][j] for i in ii for j in jj)
    gust=max((H[i]["wind_gusts_10m"][j],i,j) for i in ii for j in jj)
    pmax=max((H[i]["precipitation_probability"][j] or 0) for i in ii for j in jj)
    ptot=max(sum(H[i]["precipitation"][j] or 0 for j in jj) for i in ii)
    snow=max(sum(H[i]["snowfall"][j] or 0 for j in jj) for i in ii)
    fz=min(H[i]["freezing_level_height"][j] for i in ii for j in jj)
    hi=max(o["alt"] for o in pts); dur=(t1-t0).total_seconds()/3600
    nh=sum(1 for x in range(int(dur)) for t in [t0+dt.timedelta(hours=x)] if t<sun_(t.date())[0] or t>sun_(t.date())[1])
    b=band(coldest[0])
    dplus=pts[-1]["dp"]-pts[0]["dp"]
    M=lambda v:f"{v:.0f}".replace("-","\u2212")
    tiles=[("Coldest point",M(coldest[1])+"\u2009°C",f"feels {M(coldest[0])}\u2009°C",b),
           ("If you run late",M(late)+"\u2009°C",f"felt, +{slack:.0f} h behind plan","x"),
           ("Peak gust",f"{gust[0]:.0f}","km/h  ·  "+html.escape(shortname(sched[gust[1]]["name"])),"x"),
           ("Rain",f"{pmax:.0f}%","max chance  ·  {:.1f}\u2009mm".format(ptot),"x"),
           ("Snow / ice",f"{snow:.0f} cm","0 °C at {:,.0f} m — {:+,.0f} m over the top".format(fz,fz-hi).replace(","," "),"x")]
    tl="".join(f'<div class="tile{" tile--"+t[3] if t[3]!="x" else ""}"><span class="tile-k">{t[0]}</span>'
               f'<span class="tile-v">{t[1]}</span><span class="tile-s">{t[2]}</span></div>' for t in tiles)
    take="".join(f"<li>{html.escape(x)}</li>" for x in L["take"])
    leave="".join(f"<li>{html.escape(x)}</li>" for x in L["leave"])
    cards.append(f"""<article class="leg" id="leg{L['no']}">
<header class="leg-hd">
 <div class="leg-id"><span class="leg-no">{L['no']}</span><span class="leg-of">of 7</span></div>
 <div class="leg-name"><h3>{html.escape(L['frm'])} <span class="arw">&rarr;</span> {html.escape(L['to'])}</h3>
  <p class="leg-meta"><b>{L['k1']-L['k0']:.0f}&#8201;km</b> &middot; <b>{th(dplus)}&#8201;m</b> climb &middot; high point <b>{th(hi)}&#8201;m</b> &middot; {dur:.0f}&#8201;h, {nh}&#8201;h in the dark</p></div>
 <div class="leg-eta"><span class="eta-k">On plan</span><span class="eta-v">{t0:%a %H:%M}</span><span class="eta-d">&rarr; {t1:%a %H:%M}</span></div>
</header>
<p class="leg-head">{html.escape(L['head'])}</p>
<div class="tiles">{tl}</div>
<p class="crux"><span class="crux-k">Crux</span>{html.escape(L['crux'])}</p>
<div class="bag">
 <div class="bag-col bag-take"><h4>Take from the bag</h4><ul>{take}</ul></div>
 <div class="bag-col bag-leave"><h4>Leave it</h4><ul>{leave}</ul></div>
</div></article>""")
CARDS="\n".join(cards)
# ---------- full table ----------
rows=[]
for o in sched:
    j=hidx(o["when"]); t=H[o["i"]]["temperature_2m"][j]; ap=H[o["i"]]["apparent_temperature"][j]
    g=H[o["i"]]["wind_gusts_10m"][j]; pp=H[o["i"]]["precipitation_probability"][j] or 0
    cls=" class=\"bvrow\"" if o["typ"] in("BV","START","A+R") else ""
    rows.append(f'<tr{cls}><td class="n">{o["km"]:.1f}</td><td>{html.escape(o["name"])}</td>'
                f'<td class="n">{th(o["alt"])}</td><td class="n">{o["when"]:%a %H:%M}</td><td class="n">{o["eta"]:.0f}</td>'
                f'<td class="n t-{band(ap)}">{t:.0f}</td><td class="n t-{band(ap)}">{ap:.0f}</td>'
                f'<td class="n">{g:.0f}</td><td class="n">{pp:.0f}%</td></tr>')
ROWS="\n".join(rows).replace(">-",">\u2212")
open("rendered.parts.json","w").write(json.dumps(dict(svg=SVG,cards=CARDS,rows=ROWS)))
print("svg",len(SVG),"cards",len(CARDS),"rows",len(ROWS))
