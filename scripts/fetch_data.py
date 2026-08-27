#!/usr/bin/env python3
"""
Fetch 2026 season results + the upcoming week from the MLB Stats API
into schedule/. Intended to run in GitHub Actions (open network); the
Cowork sandbox cannot reach statsapi.mlb.com directly.

Writes:
  schedule/sched_1.json   full season to date (replaces any sched_*.json)
  schedule/upcoming.json  today through today+6
  schedule/season.json    season window, so generate_site.py (no network)
                          knows when to stand down

Outside the regular-season window this exits 0 without touching any file,
so the daily workflow becomes a no-op rather than committing churn. The
window is read from the API, not hardcoded, so it carries to future
seasons without an edit.
"""
import glob
import json
import os
import urllib.request
from datetime import date, timedelta

SEASON = 2026
# The last regular-season games finish late on the final night ET, which is
# already the next day UTC. The 10:00 UTC job therefore needs to run once
# MORE after the closing date to capture them - hence the grace day.
GRACE_DAYS = 1
SEASONS_URL = ("https://statsapi.mlb.com/api/v1/seasons"
               "?sportId=1&season={s}")
FIELDS = ("dates,date,games,gamePk,gameDate,status,codedGameState,"
          "teams,away,home,team,id,isWinner")
BASE = ("https://statsapi.mlb.com/api/v1/schedule?sportId=1&season={s}"
        "&gameType=R&startDate={a}&endDate={b}&fields=" + FIELDS)


def get(url):
    req = urllib.request.Request(url, headers={"User-Agent": "mlb-par/1.0"})
    with urllib.request.urlopen(req, timeout=120) as r:
        return json.load(r)


def season_window():
    """(start, end) of the regular season, straight from the API."""
    d = get(SEASONS_URL.format(s=SEASON))["seasons"][0]
    return (date.fromisoformat(d["regularSeasonStartDate"]),
            date.fromisoformat(d["regularSeasonEndDate"]))


def fetch(start, end):
    url = BASE.format(s=SEASON, a=start, b=end)
    return get(url)


def main():
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    sched = os.path.join(root, "schedule")
    os.makedirs(sched, exist_ok=True)
    today = date.today()

    start, end = season_window()
    last_run = end + timedelta(days=GRACE_DAYS)
    if not (start <= today <= last_run):
        why = "not started" if today < start else "over"
        print(f"{SEASON} regular season {why} "
              f"({start} to {end}, final run {last_run}); "
              f"today is {today}. Nothing to do.")
        return

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
    # let the offline generator see the same window
    with open(os.path.join(sched, "season.json"), "w") as f:
        json.dump({"season": SEASON, "regularSeasonStartDate": start.isoformat(),
                   "regularSeasonEndDate": end.isoformat(),
                   "graceDays": GRACE_DAYS}, f, indent=1)

    n = sum(len(d.get("games", [])) for d in season.get("dates", []))
    print(f"season games fetched: {n}; "
          f"upcoming days: {len(upcoming.get('dates', []))}")


if __name__ == "__main__":
    main()
