# -*- coding: utf-8 -*-
import json
p=json.load(open("rendered.parts.json"))
CSS = """
:root{
  --bg:#EDF0F3; --surface:#FFFFFF; --surface-2:#F5F8FA; --sunk:#E4EAEF;
  --ink:#0E1C27; --ink-2:#42566A; --ink-3:#6F869B; --rule:#D2DBE3; --rule-2:#E3EAF0;
  --accent:#15679F; --accent-2:#0B4570; --accent-soft:#DCEBF6;
  --hot:#B4652A; --mild:#5E8348; --cool:#2A79A6; --cold:#2A5488; --freeze:#57489B;
  --hot-bg:#F7EBE0; --mild-bg:#E9F0E3; --cool-bg:#E0EEF6; --cold-bg:#DCE5F1; --freeze-bg:#E5E1F4;
  --night:#DCE3EA; --shadow:0 1px 2px rgba(14,28,39,.05),0 6px 18px -10px rgba(14,28,39,.16);
}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]){
  --bg:#0B141D; --surface:#12222F; --surface-2:#172B3A; --sunk:#0E1B25;
  --ink:#E7EFF5; --ink-2:#A6BAC9; --ink-3:#7B92A4; --rule:#22394B; --rule-2:#1B2E3D;
  --accent:#54AEE0; --accent-2:#8FD3F5; --accent-soft:#14324A;
  --hot:#E5A165; --mild:#96C078; --cool:#63BCE6; --cold:#7FA6DA; --freeze:#A79BE8;
  --hot-bg:#33231A; --mild-bg:#1F3020; --cool-bg:#12303F; --cold-bg:#182640; --freeze-bg:#241F42;
  --night:#0A1620; --shadow:0 1px 2px rgba(0,0,0,.4),0 8px 22px -12px rgba(0,0,0,.7);
}}
:root[data-theme="dark"]{
  --bg:#0B141D; --surface:#12222F; --surface-2:#172B3A; --sunk:#0E1B25;
  --ink:#E7EFF5; --ink-2:#A6BAC9; --ink-3:#7B92A4; --rule:#22394B; --rule-2:#1B2E3D;
  --accent:#54AEE0; --accent-2:#8FD3F5; --accent-soft:#14324A;
  --hot:#E5A165; --mild:#96C078; --cool:#63BCE6; --cold:#7FA6DA; --freeze:#A79BE8;
  --hot-bg:#33231A; --mild-bg:#1F3020; --cool-bg:#12303F; --cold-bg:#182640; --freeze-bg:#241F42;
  --night:#0A1620; --shadow:0 1px 2px rgba(0,0,0,.4),0 8px 22px -12px rgba(0,0,0,.7);
}
*{box-sizing:border-box}
body{background:var(--bg);color:var(--ink);
  font-family:"IBM Plex Sans","Helvetica Neue",Arial,sans-serif;font-size:16px;line-height:1.55;
  -webkit-text-size-adjust:100%}
.wrap{max-width:1120px;margin:0 auto;padding-inline:20px;padding-block:32px 72px;
  display:flex;flex-direction:column;gap:40px}
h1,h2,h3,h4{font-family:"Barlow Condensed","Arial Narrow",Arial,sans-serif;font-weight:600;
  text-wrap:balance;margin:0;letter-spacing:.01em}
.eyebrow{font-family:"IBM Plex Mono",ui-monospace,monospace;font-size:11px;letter-spacing:.16em;
  text-transform:uppercase;color:var(--ink-3);margin:0}
/* masthead */
.mast{display:flex;flex-direction:column;gap:14px;border-bottom:2px solid var(--ink);padding-bottom:20px}
.mast h1{font-size:clamp(38px,8vw,66px);line-height:.94;letter-spacing:-.005em}
.mast h1 em{font-style:normal;color:var(--accent);display:block;font-size:.62em;letter-spacing:.005em}
.mast-sub{color:var(--ink-2);max-width:62ch;margin:0;font-size:16.5px}
.runline{display:flex;flex-wrap:wrap;gap:8px 22px;font-family:"IBM Plex Mono",ui-monospace,monospace;
  font-size:12.5px;color:var(--ink-2)}
.runline b{color:var(--ink);font-weight:600}
/* verdict */
.verdict{background:var(--surface);border:1px solid var(--rule);border-left:4px solid var(--accent);
  border-radius:3px;padding:22px 24px;display:flex;flex-direction:column;gap:12px;box-shadow:var(--shadow)}
.verdict h2{font-size:27px;line-height:1.15}
.verdict p{margin:0;color:var(--ink-2);max-width:70ch}
.verdict p b{color:var(--ink)}
.vgrid{display:grid;grid-template-columns:repeat(auto-fit,minmax(168px,1fr));gap:1px;background:var(--rule-2);
  border:1px solid var(--rule-2);margin-top:4px}
.vcell{background:var(--surface);padding:13px 15px;display:flex;flex-direction:column;gap:2px}
.vcell .k{font-family:"IBM Plex Mono",ui-monospace,monospace;font-size:10.5px;letter-spacing:.12em;
  text-transform:uppercase;color:var(--ink-3)}
.vcell .v{font-family:"Barlow Condensed","Arial Narrow",Arial,sans-serif;font-size:29px;line-height:1.05;
  font-weight:600;font-variant-numeric:tabular-nums}
.vcell .s{font-size:12.5px;color:var(--ink-3)}
/* profile */
.panel{display:flex;flex-direction:column;gap:14px}
.panel-hd{display:flex;flex-wrap:wrap;align-items:baseline;gap:6px 16px;justify-content:space-between}
.panel-hd h2{font-size:24px}
.chartbox{background:var(--surface);border:1px solid var(--rule);border-radius:3px;padding:14px 10px 8px;
  overflow-x:auto;box-shadow:var(--shadow)}
.profile{display:block;width:100%;min-width:660px;height:auto}
.nightband{fill:var(--night)}
.grid{stroke:var(--rule-2);stroke-width:1}
.gridlab,.kmlab{font-family:"IBM Plex Mono",ui-monospace,monospace;font-size:9.5px;fill:var(--ink-3)}
.prof-area{fill:var(--accent-soft)}
.prof-line{fill:none;stroke:var(--accent-2);stroke-width:1.5;stroke-linejoin:round}
.bvline{stroke:var(--ink-3);stroke-width:1;stroke-dasharray:2 3}
.bvlab{font-family:"Barlow Condensed","Arial Narrow",Arial,sans-serif;font-size:13px;fill:var(--ink-2);
  letter-spacing:.02em}
.coldpt{fill:var(--freeze);stroke:var(--surface);stroke-width:1.4}
.coldlab{font-family:"IBM Plex Mono",ui-monospace,monospace;font-size:10px;fill:var(--freeze);font-weight:600}
.tb-hot{fill:var(--hot)}.tb-mild{fill:var(--mild)}.tb-cool{fill:var(--cool)}
.tb-cold{fill:var(--cold)}.tb-freeze{fill:var(--freeze)}
.legend{display:flex;flex-wrap:wrap;gap:6px 16px;font-size:12px;color:var(--ink-2);
  font-family:"IBM Plex Mono",ui-monospace,monospace}
.legend span{display:inline-flex;align-items:center;gap:6px}
.sw{width:13px;height:9px;border-radius:1px;display:inline-block}
/* legs */
.legs{display:flex;flex-direction:column;gap:18px}
.leg{background:var(--surface);border:1px solid var(--rule);border-radius:3px;padding:20px 22px 22px;
  display:flex;flex-direction:column;gap:15px;box-shadow:var(--shadow)}
#leg6{border-color:var(--freeze);border-width:1.5px}
.leg-hd{display:flex;flex-wrap:wrap;gap:12px 18px;align-items:flex-start}
.leg-id{display:flex;align-items:baseline;gap:5px;min-width:56px}
.leg-no{font-family:"Barlow Condensed","Arial Narrow",Arial,sans-serif;font-size:46px;line-height:.8;
  font-weight:700;color:var(--accent);font-variant-numeric:tabular-nums}
.leg-of{font-family:"IBM Plex Mono",ui-monospace,monospace;font-size:10px;color:var(--ink-3);
  letter-spacing:.1em;text-transform:uppercase}
.leg-name{flex:1 1 240px}
.leg-name h3{font-size:29px;line-height:1.05}
.arw{color:var(--ink-3)}
.leg-meta{margin:2px 0 0;font-size:13px;color:var(--ink-3);font-family:"IBM Plex Mono",ui-monospace,monospace}
.leg-meta b{color:var(--ink-2);font-weight:600}
.leg-eta{display:flex;flex-direction:column;text-align:right;margin-left:auto;
  font-family:"IBM Plex Mono",ui-monospace,monospace;font-variant-numeric:tabular-nums}
.eta-k{font-size:10px;letter-spacing:.12em;text-transform:uppercase;color:var(--ink-3)}
.eta-v{font-size:19px;font-weight:600}
.eta-d{font-size:12.5px;color:var(--ink-2)}
.leg-head{margin:0;font-size:17px;color:var(--ink);max-width:70ch}
#leg6 .leg-head{color:var(--freeze);font-weight:600}
.tiles{display:grid;grid-template-columns:repeat(auto-fit,minmax(146px,1fr));gap:1px;
  background:var(--rule-2);border:1px solid var(--rule-2)}
.tile{background:var(--surface-2);padding:11px 13px;display:flex;flex-direction:column;gap:1px}
.tile-k{font-family:"IBM Plex Mono",ui-monospace,monospace;font-size:10px;letter-spacing:.11em;
  text-transform:uppercase;color:var(--ink-3)}
.tile-v{font-family:"Barlow Condensed","Arial Narrow",Arial,sans-serif;font-size:31px;line-height:1;
  font-weight:600;font-variant-numeric:tabular-nums}
.tile-s{font-size:12px;color:var(--ink-3)}
.tile--hot{background:var(--hot-bg)} .tile--hot .tile-v{color:var(--hot)}
.tile--mild{background:var(--mild-bg)} .tile--mild .tile-v{color:var(--mild)}
.tile--cool{background:var(--cool-bg)} .tile--cool .tile-v{color:var(--cool)}
.tile--cold{background:var(--cold-bg)} .tile--cold .tile-v{color:var(--cold)}
.tile--freeze{background:var(--freeze-bg)} .tile--freeze .tile-v{color:var(--freeze)}
.crux{margin:0;font-size:14.5px;color:var(--ink-2);background:var(--sunk);padding:12px 14px;
  border-radius:2px;max-width:none}
.crux-k{font-family:"IBM Plex Mono",ui-monospace,monospace;font-size:10px;letter-spacing:.13em;
  text-transform:uppercase;color:var(--ink-3);display:block;margin-bottom:3px}
.bag{display:grid;grid-template-columns:1.4fr 1fr;gap:18px}
.bag h4{font-family:"IBM Plex Mono",ui-monospace,monospace;font-size:10.5px;letter-spacing:.13em;
  text-transform:uppercase;font-weight:600;margin-bottom:7px}
.bag-take h4{color:var(--accent)}
.bag-leave h4{color:var(--ink-3)}
.bag ul{margin:0;padding-left:17px;display:flex;flex-direction:column;gap:5px;font-size:14.5px}
.bag-take li::marker{color:var(--accent)}
.bag-leave{color:var(--ink-3)}
.bag-leave li{text-decoration:line-through;text-decoration-color:var(--rule)}
/* table */
details.splits{background:var(--surface);border:1px solid var(--rule);border-radius:3px;box-shadow:var(--shadow)}
details.splits>summary{cursor:pointer;padding:16px 20px;font-family:"Barlow Condensed","Arial Narrow",Arial,sans-serif;
  font-size:23px;font-weight:600;list-style:none;display:flex;justify-content:space-between;align-items:center;gap:10px}
details.splits>summary::-webkit-details-marker{display:none}
details.splits>summary::after{content:"+";font-family:"IBM Plex Mono",monospace;font-size:19px;color:var(--accent)}
details.splits[open]>summary::after{content:"–"}
details.splits>summary:focus-visible{outline:2px solid var(--accent);outline-offset:-2px}
.tablebox{overflow-x:auto;border-top:1px solid var(--rule-2)}
table{border-collapse:collapse;width:100%;min-width:720px;font-size:13.5px}
th,td{padding:6px 12px;text-align:left;border-bottom:1px solid var(--rule-2);white-space:nowrap}
th{font-family:"IBM Plex Mono",ui-monospace,monospace;font-size:10px;letter-spacing:.1em;
  text-transform:uppercase;color:var(--ink-3);position:sticky;top:0;background:var(--surface-2)}
td.n{font-family:"IBM Plex Mono",ui-monospace,monospace;font-variant-numeric:tabular-nums;text-align:right}
tr.bvrow td{background:var(--accent-soft);font-weight:600}
td.t-hot{color:var(--hot)}td.t-mild{color:var(--mild)}td.t-cool{color:var(--cool)}
td.t-cold{color:var(--cold)}td.t-freeze{color:var(--freeze);font-weight:600}
/* footer notes */
.notes{display:grid;grid-template-columns:repeat(auto-fit,minmax(268px,1fr));gap:18px}
.note{background:var(--surface);border:1px solid var(--rule);border-radius:3px;padding:17px 19px}
.note h4{font-size:19px;margin-bottom:6px}
.note p,.note li{font-size:14px;color:var(--ink-2);margin:0}
.note ul{margin:0;padding-left:17px;display:flex;flex-direction:column;gap:5px}
.conf{display:flex;flex-direction:column;gap:7px;margin-top:4px}
.confrow{display:flex;align-items:center;gap:10px;font-size:13.5px}
.bar{height:7px;border-radius:4px;flex:0 0 76px}
.bar.hi{background:var(--mild)}.bar.md{background:var(--hot)}.bar.lo{background:var(--freeze)}
.confrow .lb{font-family:"IBM Plex Mono",ui-monospace,monospace;font-size:11.5px;color:var(--ink-3)}
a{color:var(--accent)}
footer{border-top:1px solid var(--rule);padding-top:18px;font-size:13px;color:var(--ink-3)}
footer p{margin:0 0 6px}
@media (max-width:640px){
  .bag{grid-template-columns:1fr}
  .leg-eta{margin-left:0;text-align:left}
  .leg{padding:17px 16px 19px}
}
@media (prefers-reduced-motion:reduce){*{animation:none!important;transition:none!important}}
"""
HEAD = """<title>TOR330 Cold Map</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Barlow+Condensed:wght@500;600;700&family=IBM+Plex+Mono:wght@400;500;600&family=IBM+Plex+Sans:wght@400;500;600&display=swap">
<style>%s</style>""" % CSS

BODY = """
<div class="wrap">

<header class="mast">
  <p class="eyebrow">Tor des Géants 2026 · Wave 1 · 115-hour plan</p>
  <h1>Seven legs,<em>one cold night that matters.</em></h1>
  <p class="mast-sub">A drop-bag brief for the 336.5&#8201;km course: where you will be, when, how high, and what the
  air will be doing when you get there. Built from the official TORX 2026 timetable, the certified GPX, and
  altitude-corrected forecasts for all 79 checkpoints.</p>
  <div class="runline">
    <span>Start <b>Sun 13 Sep 10:00</b></span>
    <span>Finish on plan <b>Fri 18 Sep 05:00</b></span>
    <span>Barrier <b>Sat 19 Sep 16:00</b></span>
    <span>Climb <b>26 182 m</b></span>
    <span>Forecast issued <b>9 Sep</b></span>
  </div>
</header>

<section class="verdict">
  <h2>It is a cold-kit week, not a wet one.</h2>
  <p>A ridge sits over the western Alps for the whole race. Across all 79 checkpoints and all seven days the
  models produce <b>no meaningful rain at all</b> — the wettest single hour anywhere on the course is
  <b>0.6&#8201;mm</b>, and peak rain probability never passes 19% while you are on the mountain.
  <b>Snowfall is zero</b>: the freezing level bottoms out near <b>3030&#8201;m</b>, which is still above
  Col Loson, the highest point you touch.</p>
  <p>So the decision at every life base is about <b>cold and wind</b>. Two things drive it. First, the
  ridge cools from <b>Wednesday night</b> onward — the freezing level falls from 4300&#8201;m to
  3200&#8201;m and the high cols go sub-zero. Second, those nights are <b>clear and almost windless</b>,
  which is what makes them bite: nothing traps the heat, so exposed cols radiate hard and you feel several
  degrees below the air temperature the moment you stop moving.</p>
  <div class="vgrid">
    <div class="vcell"><span class="k">Coldest on course</span><span class="v" style="color:var(--freeze)">&minus;4&#8201;°C</span><span class="s">Col Malatrà 2921&#8201;m, Fri 00:43 · feels &minus;3&#8201;°C</span></div>
    <div class="vcell"><span class="k">Warmest on course</span><span class="v" style="color:var(--hot)">26&#8201;°C</span><span class="s">Donnas 323&#8201;m, Tue&ndash;Wed afternoons</span></div>
    <div class="vcell"><span class="k">Total rain, worst point</span><span class="v">0.6&#8201;mm</span><span class="s">in any single hour, anywhere</span></div>
    <div class="vcell"><span class="k">Snow</span><span class="v">0&#8201;cm</span><span class="s">0&#8201;°C level never below 3030&#8201;m</span></div>
    <div class="vcell"><span class="k">Windiest</span><span class="v">72&#8201;km/h</span><span class="s">gusts, Col Pinter ridge, Wed dawn</span></div>
  </div>
</section>

<section class="panel">
  <div class="panel-hd">
    <h2>Where the cold finds you</h2>
    <p class="eyebrow">Profile · night shading · feels-like at your ETA</p>
  </div>
  <div class="chartbox">
    __SVG__
  </div>
  <div class="legend">
    <span><i class="sw" style="background:var(--night)"></i>in darkness on plan</span>
    <span><i class="sw" style="background:var(--hot)"></i>above 16&#8201;°C</span>
    <span><i class="sw" style="background:var(--mild)"></i>9&ndash;16&#8201;°C</span>
    <span><i class="sw" style="background:var(--cool)"></i>3&ndash;9&#8201;°C</span>
    <span><i class="sw" style="background:var(--cold)"></i>&minus;2&ndash;3&#8201;°C</span>
    <span><i class="sw" style="background:var(--freeze)"></i>below &minus;2&#8201;°C</span>
  </div>
  <p class="mast-sub">The strip under the profile is <b>felt</b> temperature — air temperature corrected for wind —
  at the hour you are forecast to be standing there. Marked dots are each leg&rsquo;s coldest point. Note that the
  two coldest sections of the whole race, Vessonaz and Malatrà, are also the two that fall deepest into the night.</p>
</section>

<section class="panel legs">
  <div class="panel-hd">
    <h2>Leg by leg, life base to life base</h2>
    <p class="eyebrow">what to pull out of the bag</p>
  </div>
__CARDS__
</section>

<details class="splits">
  <summary>All 79 checkpoints — ETA, altitude and conditions</summary>
  <div class="tablebox">
    <table>
      <thead><tr><th>km</th><th>Checkpoint</th><th>Alt m</th><th>ETA</th><th>Elapsed h</th>
      <th>Air °C</th><th>Feels °C</th><th>Gust km/h</th><th>Rain</th></tr></thead>
      <tbody>
__ROWS__
      </tbody>
    </table>
  </div>
</details>

<section class="notes">
  <div class="note">
    <h4>How much to trust this</h4>
    <p>Forecast skill decays fast past four days, and this is a single model blend — cross-checks against a
    second source were only possible for the first two race days, where they agree closely.</p>
    <div class="conf">
      <div class="confrow"><i class="bar hi"></i><span class="lb">Legs 1&ndash;3 · Sun&ndash;Mon</span></div>
      <div class="confrow"><i class="bar md"></i><span class="lb">Legs 4&ndash;5 · Tue&ndash;Wed</span></div>
      <div class="confrow"><i class="bar lo"></i><span class="lb">Legs 6&ndash;7 · Thu&ndash;Fri</span></div>
    </div>
    <p style="margin-top:9px">The dry, ridge-dominated pattern is the robust part and is unlikely to break.
    The exact timing of Wednesday&rsquo;s cool-down is the soft part — it could arrive twelve hours either side.
    Re-check at each life base.</p>
  </div>
  <div class="note">
    <h4>If your race drifts</h4>
    <ul>
      <li>Every leg card&rsquo;s second tile shows the felt temperature if you are running behind plan by the
      slack shown — up to twelve hours by the last leg.</li>
      <li>Running late makes legs 6 and 7 <em>colder</em>, not warmer: you push deeper into the pre-dawn hours
      at altitude.</li>
      <li>Wave 2 starters: add two hours to every time on this page.</li>
      <li>A 100-hour race pulls Malatrà into Thursday evening and out of the coldest window entirely; a
      130-hour race puts Vessonaz into Friday night instead.</li>
    </ul>
  </div>
  <div class="note">
    <h4>The two cold decisions</h4>
    <ul>
      <li><b>At Valtournenche (km 237.5)</b> take everything warm you own. Cuney to Vessonaz is two hours
      above 2650&#8201;m in the coldest part of Thursday morning, at or below freezing, in still air.</li>
      <li><b>At Ollomont (km 286.5)</b> keep it all. Col Malatrà at 2921&#8201;m around midnight is the
      coldest point on the entire course, and it has chains to hold in the dark.</li>
      <li>Everything before Gressoney is a sun-and-water problem. Carry the mandatory shell, expect not to
      use it.</li>
    </ul>
  </div>
</section>

<footer>
  <p><b>Sources.</b> Route, distances, altitudes and cut-offs from the official
  <a href="https://torxtrail.com/tor330-tor-des-geants/">TORX TOR330 2026 timetable</a>; positions from the
  certified TOR330 2026 GPX. Forecasts from
  <a href="https://open-meteo.com/">Open-Meteo</a>, requested per checkpoint with each checkpoint&rsquo;s true
  altitude so temperatures are elevation-corrected rather than valley values. Cross-checked for 13&ndash;14 Sep
  against <a href="https://www.mountain-forecast.com/">mountain-forecast.com</a> at 2000&#8201;m and 3000&#8201;m
  for Mont Blanc, Punta Tersiva, Monte Emilius, Corno Bianco, Becca di Luseney and Mont Vélan.</p>
  <p>Schedule interpolated between the organiser&rsquo;s own fastest and slowest passage columns, scaled to a
  115-hour finish. It is a plan, not a promise.</p>
</footer>

</div>
"""
out=HEAD+BODY.replace("__SVG__",p["svg"]).replace("__CARDS__",p["cards"]).replace("__ROWS__",p["rows"])
open("tor330-cold-map.html","w",encoding="utf-8").write(out)
print("bytes",len(out))
