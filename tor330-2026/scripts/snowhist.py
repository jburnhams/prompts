import json,subprocess,urllib.parse,time
sched=json.load(open("schedule.json"))
HI=[o for o in sched if o["alt"]>=2300]
print("high points:",len(HI))
HOURLY="snowfall,snow_depth,freezing_level_height,precipitation,temperature_2m"
out=[]
for i in range(0,len(HI),7):
    ch=HI[i:i+7]
    q={"latitude":",".join(str(p["lat"]) for p in ch),
       "longitude":",".join(str(p["lon"]) for p in ch),
       "elevation":",".join(str(p["alt"]) for p in ch),
       "hourly":HOURLY,"timezone":"Europe/Rome","past_days":"92","forecast_days":"10"}
    url="https://api.open-meteo.com/v1/forecast?"+urllib.parse.urlencode(q)
    r=subprocess.run(["curl","-sS","-m","90",url],capture_output=True,text=True)
    d=json.loads(r.stdout)
    if isinstance(d,dict) and d.get("error"): print("ERR",d); break
    out+= d if isinstance(d,list) else [d]
    print("  fetched",len(out)); time.sleep(1)
json.dump({"points":[{k:v for k,v in p.items()} for p in HI],"wx":out},open("snowhist.json","w"))
h=out[0]["hourly"]; print("hours",len(h["time"]),h["time"][0],"->",h["time"][-1])
print("snow_depth sample:",[x for x in h["snow_depth"][:5]], "units:",out[0]["hourly_units"].get("snow_depth"))
