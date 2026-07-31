# mlb-par

Payroll-Adjusted Record (PAR): an MLB metric where expected outcomes (the
richer team winning) count as a plain 1 win / 1 loss, and upsets credit the
underdog 1–2 wins while debiting the favorite the same in losses:

    g = max(1, 2 · P_loser^α / (P_loser^α + P_winner^α)),  α = 0.5

Zero-sum per game. Payrolls: Spotrac 2026 active payroll (snapshot).
Results: MLB Stats API (statsapi.mlb.com, free/keyless).

## Layout

- `docs/` — GitHub Pages site: division/league PAR standings + "The Slate"
  (upcoming games with payroll-implied lines and upset stakes)
- `scripts/payroll_adjusted_record.py` — CLI standings calculator
- `scripts/generate_site.py` — builds `docs/data.js` from `schedule/*.json`
- `scripts/README.md` — full design doc (algorithm, variants, tooling)
- `schedule/sched_*.json` — 2026 season results (statsapi schedule shape)
- `schedule/upcoming.json` — upcoming-games snapshot

## Enabling the site

Repo Settings → Pages → Source: **Deploy from a branch** → `main` / `docs/`.
Site will serve at https://dan2bit.github.io/mlb-par/

## Refreshing data

1. Re-fetch season windows and the upcoming week from
   `https://statsapi.mlb.com/api/v1/schedule?sportId=1&season=2026&gameType=R&startDate=...&endDate=...&fields=dates,date,games,gamePk,gameDate,status,codedGameState,teams,away,home,team,id,isWinner`
   into `schedule/`.
2. `python3 scripts/generate_site.py`
3. Commit `schedule/` + `docs/data.js`.

Stretch goal: a scheduled GitHub Action that does the above daily (statsapi
is reachable from Actions runners; payroll snapshot updated manually).
