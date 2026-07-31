#!/usr/bin/env python3
"""
Fetch 2026 season results + the upcoming week from the MLB Stats API
into schedule/. Intended to run in GitHub Actions (open network); the
Cowork sandbox cannot reach statsapi.mlb.com directly.

Writes:
  schedule/sched_1.json   full season to date (replaces any sched_*.json)
  schedule/upcoming.json  today through today+6
"""
import glob
import json
import os
import urllib.request
from datetime import date, timedelta

SEASON = 2026
FIELDS = ("dates,date,games,gamePk,gameDate,status,codedGameState,"
          "teams,away,home,team,id,isWinner")
BASE = ("https://statsapi.mlb.com/api/v1/schedule?sportId=1&season={s}"
        "&gameType=R&startDate={a}&endDate={b}&fields=" + FIELDS)


def fetch(start, end):
    url = BASE.format(s=SEASON, a=start, b=end)
    req = urllib.request.Request(url, headers={"User-Agent": "mlb-par/1.0"})
    with urllib.request.urlopen(req, timeout=120) as r:
        return json.load(r)


def main():
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    sched = os.path.join(root, "schedule")
    os.makedirs(sched, exist_ok=True)
    today = date.today()

    season = fetch(f"{SEASON}-03-01", today.isoformat())
    upcoming = fetch(today.isoformat(),
                     (today + timedelta(days=6)).isoformat())

    # Replace all windowed season files with one canonical file so the
    # generator's glob never double-counts.
    for p in glob.glob(os.path.join(sched, "sched_*.json")):
        os.remove(p)
    with open(os.path.join(sched, "sched_1.json"), "w") as f:
        json.dump(season, f, separators=(",", ":"))
    with open(os.path.join(sched, "upcoming.json"), "w") as f:
        json.dump(upcoming, f, separators=(",", ":"))

    n = sum(len(d.get("games", [])) for d in season.get("dates", []))
    print(f"season games fetched: {n}; "
          f"upcoming days: {len(upcoming.get('dates', []))}")


if __name__ == "__main__":
    main()
