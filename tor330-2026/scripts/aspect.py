import json,subprocess,urllib.parse,math,time
sched=json.load(open("schedule.json"))
HI=[o for o in sched if o["alt"]>=2600]
def grid(lat,lon,d=0.0045):
    la=[];lo=[]
    for j in (-1,0,1):
        for i in (-1,0,1):
            la.append(round(lat+j*d,6)); lo.append(round(lon+i*d/math.cos(math.radians(lat)),6))
    q={"latitude":",".join(map(str,la)),"longitude":",".join(map(str,lo))}
    for attempt in range(4):
        r=subprocess.run(["curl","-sS","-m","60","https://api.open-meteo.com/v1/elevation?"+urllib.parse.urlencode(q)],
                         capture_output=True,text=True)
        try:
            d=json.loads(r.stdout)
            if "elevation" in d: return d["elevation"]
            print("   api said:",str(d)[:120])
        except Exception:
            print("   raw:",(r.stdout or r.stderr)[:120])
        time.sleep(2*(attempt+1))
    raise SystemExit("elevation API unavailable")
COMP=["N","NNE","NE","ENE","E","ESE","SE","SSE","S","SSW","SW","WSW","W","WNW","NW","NNW"]
print(f"{'point':<26}{'alt':>6}{'slope':>7}{'aspect':>8}   shading / snow-holding read")
print("-"*88)
res=[]
for p in HI:
    e=grid(p["lat"],p["lon"]); time.sleep(0.4)
    # 3x3 grid, rows south->north (j=-1,0,1), cols west->east
    z=[e[0:3],e[3:6],e[6:9]]
    cell=500.0  # approx metres between samples
    dzdx=((z[0][2]+2*z[1][2]+z[2][2])-(z[0][0]+2*z[1][0]+z[2][0]))/(8*cell)
    dzdy=((z[2][0]+2*z[2][1]+z[2][2])-(z[0][0]+2*z[0][1]+z[0][2]))/(8*cell)
    slope=math.degrees(math.atan(math.hypot(dzdx,dzdy)))
    asp=(math.degrees(math.atan2(dzdy,-dzdx))+360)%360   # downslope direction
    asp=(90-math.degrees(math.atan2(dzdy,dzdx)))%360
    c=COMP[int((asp+11.25)//22.5)%16]
    northness=math.cos(math.radians(asp))   # +1 = due north facing
    res.append((p["name"],p["alt"],slope,asp,c,northness))
for n,a,s,asp,c,nn in sorted(res,key=lambda r:-(r[5]*1000+r[1]/10)):
    tag=""
    if nn>0.35 and a>=2700: tag="north-facing AND high — the only kind of spot old snow survives"
    elif nn>0.35: tag="north-facing but low"
    elif nn<-0.35: tag="sun-facing — melts out first"
    else: tag="cross-slope"
    print(f"{n[:25]:<26}{a:>6}{s:>6.0f}°{c:>8}   {tag}")
json.dump(res,open("aspect.json","w"))
