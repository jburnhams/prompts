# TOR330 2026 — route, pacing plan and altitude-corrected weather

Working data behind a drop-bag weather brief for the Tor des Géants (TOR330), 13–19 September 2026.
The question it answers: **for each leg between life bases, what will the weather be doing when I get
there, and what do I need to take out of the drop bag?**

Forecasts were issued **9 September 2026**, four to ten days ahead of the race. Anything past
16 September is trend, not detail.

## Plan assumptions

| | |
|---|---|
| Wave | 1 — start Sunday 13 Sep 10:00 CEST |
| Target | 115 h → finish Friday 18 Sep ~05:00 |
| Course | 336.5 km, 26 182 m D+, 79 checkpoints, 6 life bases |
| Barrier | Saturday 19 Sep 16:00 (wave 1) |

Wave 2 starts at 12:00; add two hours to every time here.

## Layout

```
data/
  TOR330-Timetable-2026.pdf     official TORX timetable (source of km, altitude, cut-offs)
  TOR330-Timetable-2026.txt     layout-preserving text extraction of the above
  TOR330CERT2026.gpx            official certified 2026 route, 37 382 track points
  tor330-2026-plan.tsv          MAIN OUTPUT: 79 checkpoints x plan ETA x forecast
  schedule.json                 same, plus the organiser's fastest/slowest columns
  profile.json                  route sampled every 500 m: altitude, ETA, felt temp, day/night
  forecast-open-meteo-raw.json  unmodified API response, 79 points x 168 hours
  mountain-forecast-crosscheck.tsv  independent second source, 6 peaks x 2 levels
scripts/                        everything used to build the above, in dependency order
tor330-cold-map.html            the rendered brief
```

`tor330-2026-plan.tsv` is the file to read first. One row per checkpoint:
km, name, altitude, lat/lon, the organiser's elite and barrier splits, the planned ETA, and
air/felt temperature, wind, gust, precipitation, snowfall, cloud and freezing level at that ETA.

## Method

1. **Route.** Checkpoint names, cumulative km, altitudes and cut-offs come from the official
   timetable PDF. Coordinates come from the certified GPX by interpolating along the track to each
   checkpoint's cumulative distance, scaled by 337.0/336.5 to reconcile GPX and official totals.
   This avoids name-matching entirely and lands each point within a few hundred metres.
2. **Pacing.** The timetable publishes a fastest (66.1 h) and slowest (149.8 h) passage time for
   every timed checkpoint. The plan interpolates between them at fraction `f(p) = 0.50 + 0.084p`,
   where `p` is effort progress `(km + D+/100) / total` — so it starts nearer the fast column and
   drifts toward the slow one, matching how a field actually spreads. `f(1) = 0.584` makes the
   finish land on 115 h exactly. Untimed waypoints (cols) are interpolated by effort progress
   between their neighbours.
3. **Weather.** Open-Meteo, one request per checkpoint with that checkpoint's **true altitude**
   passed as `elevation`, so temperatures are lapse-rate corrected rather than valley readings.
   Verified: the API echoed the requested elevation for every point.
4. **Cross-check.** mountain-forecast.com at 2000 m and 3000 m for Mont Blanc, Punta Tersiva,
   Monte Emilius, Corno Bianco, Becca di Luseney and Mont Vélan. Its free tier only reaches
   14 September, so the check covers race days 1–2 only. It agrees closely there.

## Corrections applied to the source PDF

The published timetable has two day-field typos that make the slowest column non-monotonic:

- **Rif. Vittorio Sella**, slowest passage printed `D5 22.34`. Sella (km 95.2) precedes Cogne, whose
  slowest is `D5 01.13`, so it must be `D4 22.34`. Corrected.
- **Perloz**, slowest passage printed `D5 02.15`. Perloz (km 155.6) follows Donnas, whose exit
  cut-off is `D6 02.00`, so it must be `D6 02.15`. Corrected.

Both are recorded in `scripts/waypoints.py`.

## Findings

The week is anticyclonic and dry end to end. Across all 79 points and all 168 hours the wettest
single hour anywhere is 0.6 mm; snowfall is zero and the freezing level bottoms out at 3030 m,
above Col Loson (3295 m), the highest point on the course. So the drop bag is a cold-and-wind
decision, not a wet one.

The airmass cools from Wednesday 16th: freezing level 4300 m → 3200 m. That puts the two coldest
sections of the race in the last two legs, both deep in the night and both in clear, near-calm air
that radiates hard:

| Leg | Section | Time on plan | Air | Felt |
|---|---|---|---|---|
| 6 | Rif. Cuney → Col de Vessonaz, 2655–2788 m | Thu 02:17–03:36 | 0.3 → 0.2 °C | −4 °C |
| 7 | Col Malatrà, 2921 m | Fri 00:43 | 0.0 °C | −3 °C |

Legs 1–4 are the opposite problem: 22 °C at Cogne, 26 °C at Donnas, and the Lillaz → Finestra di
Champorcher climb in full afternoon sun. Water and sun protection, not insulation.

## Caveats

- Single-model blend (Open-Meteo `best_match`). Requests for ECMWF IFS, GFS and ICON to compare
  spread hit the API's daily rate limit and are not in this dataset.
- Skill decays sharply past four days. Legs 1–3 are reasonably firm; legs 6–7 are a trend.
  The dry ridge is the robust signal; the timing of Wednesday's cool-down is the soft one and
  could move twelve hours either way.
- The ETA column is a plan, not a prediction. Every leg in the brief also carries a
  "if you run late" figure for the felt temperature if you are behind by the slack shown.
