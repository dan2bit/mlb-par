#!/usr/bin/env python3
"""
Build docs/data.js for the MLB PAR Pages site.

Reads:  schedule/sched_*.json  (season results, statsapi schedule shape)
        schedule/upcoming.json (next ~week, same shape)
Writes: docs/data.js           (window.PAR = {...})

Run from anywhere; paths resolve relative to the repo root (parent of the
directory containing this script, or the script's own directory if it
holds schedule/ itself).

Payroll basis: Spotrac 2026 Active payroll snapshot (see PAYROLL).
Model: upset-only payroll-logistic, g = max(1, 2*P_L^a/(P_L^a+P_W^a)),
with per-game implied expectancy clamped to [1-MODEL_CAP, MODEL_CAP].
"""
import glob
import json
import os
from datetime import datetime, timezone

ALPHA = 0.5
# No club is ever priced outside this band for a single game. Payroll alone
# implies .767 for the richest club over the poorest, which no rational
# market would post; the guard reflects that even the best team loses and
# the worst team wins. Capping the favourite floors the underdog at 1-CAP.
MODEL_CAP = 0.72
PAYROLL_ASOF = "2026-07-28"

PAYROLL = {
    "LAD": 368_740_747, "NYM": 315_942_898, "NYY": 285_992_534,
    "TOR": 272_263_793, "PHI": 265_488_771, "SD": 239_767_012,
    "BOS": 222_180_833, "ATL": 210_091_667, "CHC": 209_835_714,
    "DET": 209_388_939, "HOU": 201_738_328, "SF": 187_522_686,
    "BAL": 173_637_000, "TEX": 168_925_000, "ARI": 159_047_500,
    "LAA": 158_106_023, "KC": 155_439_192, "SEA": 152_271_167,
    "CIN": 103_583_333, "ATH": 99_711_190, "MIL": 96_890_000,
    "PIT": 86_873_750, "TB": 77_090_000, "COL": 73_946_429,
    "CHW": 68_900_000, "MIN": 61_010_714, "CLE": 55_906_000,
    "STL": 39_725_000, "MIA": 39_620_000, "WSH": 33_920_000,
}

TEAM_ID = {
    108: "LAA", 109: "ARI", 110: "BAL", 111: "BOS", 112: "CHC",
    113: "CIN", 114: "CLE", 115: "COL", 116: "DET", 117: "HOU",
    118: "KC", 119: "LAD", 120: "WSH", 121: "NYM", 133: "ATH",
    134: "PIT", 135: "SD", 136: "SEA", 137: "SF", 138: "STL",
    139: "TB", 140: "TEX", 141: "TOR", 142: "MIN", 143: "PHI",
    144: "ATL", 145: "CHW", 146: "MIA", 147: "NYY", 158: "MIL",
}

TEAMS = {  # abbrev: (display name, division)
    "BAL": ("Orioles", "AL East"), "BOS": ("Red Sox", "AL East"),
    "NYY": ("Yankees", "AL East"), "TB": ("Rays", "AL East"),
    "TOR": ("Blue Jays", "AL East"),
    "CHW": ("White Sox", "AL Central"), "CLE": ("Guardians", "AL Central"),
    "DET": ("Tigers", "AL Central"), "KC": ("Royals", "AL Central"),
    "MIN": ("Twins", "AL Central"),
    "ATH": ("Athletics", "AL West"), "HOU": ("Astros", "AL West"),
    "LAA": ("Angels", "AL West"), "SEA": ("Mariners", "AL West"),
    "TEX": ("Rangers", "AL West"),
    "ATL": ("Braves", "NL East"), "MIA": ("Marlins", "NL East"),
    "NYM": ("Mets", "NL East"), "PHI": ("Phillies", "NL East"),
    "WSH": ("Nationals", "NL East"),
    "CHC": ("Cubs", "NL Central"), "CIN": ("Reds", "NL Central"),
    "MIL": ("Brewers", "NL Central"), "PIT": ("Pirates", "NL Central"),
    "STL": ("Cardinals", "NL Central"),
    "ARI": ("D-backs", "NL West"), "COL": ("Rockies", "NL West"),
    "LAD": ("Dodgers", "NL West"), "SD": ("Padres", "NL West"),
    "SF": ("Giants", "NL West"),
}

# Spotrac team pages, as linked from the 2026 payroll tracker
# (https://www.spotrac.com/mlb/payroll/_/year/2026), scraped 2026-07-31.
SPOTRAC = {
    "ARI": "arizona-diamondbacks", "ATH": "athletics",
    "ATL": "atlanta-braves", "BAL": "baltimore-orioles",
    "BOS": "boston-red-sox", "CHC": "chicago-cubs",
    "CHW": "chicago-white-sox", "CIN": "cincinnati-reds",
    "CLE": "cleveland-guardians", "COL": "colorado-rockies",
    "DET": "detroit-tigers", "HOU": "houston-astros",
    "KC": "kansas-city-royals", "LAA": "los-angeles-angels",
    "LAD": "los-angeles-dodgers", "MIA": "miami-marlins",
    "MIL": "milwaukee-brewers", "MIN": "minnesota-twins",
    "NYM": "new-york-mets", "NYY": "new-york-yankees",
    "PHI": "philadelphia-phillies", "PIT": "pittsburgh-pirates",
    "SD": "san-diego-padres", "SEA": "seattle-mariners",
    "SF": "san-francisco-giants", "STL": "st-louis-cardinals",
    "TB": "tampa-bay-rays", "TEX": "texas-rangers",
    "TOR": "toronto-blue-jays", "WSH": "washington-nationals",
}


def spotrac_url(ab):
    return f"https://www.spotrac.com/mlb/{SPOTRAC[ab]}"


def repo_root():
    here = os.path.dirname(os.path.abspath(__file__))
    for cand in (os.path.dirname(here), here):
        if os.path.isdir(os.path.join(cand, "schedule")):
            return cand
    return here


def implied_expectancy(p_a, p_b, alpha=ALPHA, cap=MODEL_CAP):
    """Payroll-implied win expectancy for A over B, clamped to [1-cap, cap]."""
    a, b = p_a ** alpha, p_b ** alpha
    e = a / (a + b)
    return min(max(e, 1 - cap), cap)


def game_weight(p_winner, p_loser, alpha=ALPHA, cap=MODEL_CAP):
    """Upset-only payroll-logistic. Favoured outcome -> 1.0; upset in (1, 2*cap].

    The weight is twice the LOSER's implied expectancy, so beating a club the
    market priced higher pays more. Clamped, the ceiling is 2*0.72 = 1.44.
    """
    return max(1.0, 2 * implied_expectancy(p_loser, p_winner, alpha, cap))


def to_moneyline(e):
    """American-odds style rendering of an expectancy (payroll-implied)."""
    if e >= 0.5:
        return -round(100 * e / (1 - e))
    return round(100 * (1 - e) / e)


def load_dates(path_glob):
    dates = []
    for path in sorted(glob.glob(path_glob)):
        with open(path) as f:
            dates.extend(json.load(f).get("dates", []))
    return dates


def standings(sched_dir):
    rec = {ab: {"w": 0, "l": 0, "aw": 0.0, "al": 0.0,
                "favw": 0, "favl": 0, "upsw": 0, "upsl": 0}
           for ab in PAYROLL}
    n = 0
    fav_wins = 0        # games won by the higher-payroll club
    for date in load_dates(os.path.join(sched_dir, "sched_*.json")):
        for g in date["games"]:
            if g["status"].get("codedGameState") != "F":
                continue
            home, away = g["teams"]["home"], g["teams"]["away"]
            if "isWinner" not in home:
                continue
            winner, loser = (home, away) if home["isWinner"] else (away, home)
            w_ab = TEAM_ID.get(winner["team"]["id"])
            l_ab = TEAM_ID.get(loser["team"]["id"])
            if not w_ab or not l_ab:
                continue
            gw = game_weight(PAYROLL[w_ab], PAYROLL[l_ab])
            # Upset = the lower-payroll club won. Equal payroll counts as
            # favoured (weight is exactly 1.0 either way). Note this is a
            # statement about relative spend, not a prediction: payroll
            # barely tracks single-game outcomes.
            upset = PAYROLL[w_ab] < PAYROLL[l_ab]
            rec[w_ab]["w"] += 1
            rec[w_ab]["aw"] += gw
            rec[w_ab]["upsw" if upset else "favw"] += 1
            rec[l_ab]["l"] += 1
            rec[l_ab]["al"] += gw
            rec[l_ab]["upsl" if upset else "favl"] += 1
            if not upset:
                fav_wins += 1
            n += 1
    rows = []
    for ab, r in rec.items():
        gp = r["w"] + r["l"]
        pct = r["w"] / gp if gp else 0.0
        apct = r["aw"] / (r["aw"] + r["al"]) if gp else 0.0
        name, div = TEAMS[ab]
        rows.append({
            "ab": ab, "name": name, "div": div,
            "payroll": PAYROLL[ab],
            "url": spotrac_url(ab),
            "w": r["w"], "l": r["l"], "pct": round(pct, 3),
            "favw": r["favw"], "favl": r["favl"],
            "upsw": r["upsw"], "upsl": r["upsl"],
            "aw": round(r["aw"], 1), "al": round(r["al"], 1),
            "apct": round(apct, 3), "delta": round(apct - pct, 3),
        })
    rows.sort(key=lambda x: -x["apct"])
    return rows, n, (fav_wins / n if n else 0.0)


def slate(sched_dir):
    games = []
    for date in load_dates(os.path.join(sched_dir, "upcoming.json")):
        for g in date["games"]:
            state = g["status"].get("codedGameState")
            if state in ("F", "D"):  # finished/postponed: off the board
                continue
            away = TEAM_ID.get(g["teams"]["away"]["team"]["id"])
            home = TEAM_ID.get(g["teams"]["home"]["team"]["id"])
            if not away or not home:
                continue
            p_away, p_home = PAYROLL[away], PAYROLL[home]
            fav, dog = (away, home) if p_away >= p_home else (home, away)
            e_fav = implied_expectancy(PAYROLL[fav], PAYROLL[dog])
            # upset weight: dog wins (winner=dog, loser=fav)
            stake = game_weight(PAYROLL[dog], PAYROLL[fav])
            games.append({
                "pk": g["gamePk"], "date": date["date"], "iso": g["gameDate"],
                "live": state == "I",
                "away": away, "home": home,
                "fav": fav, "dog": dog,
                "edge": PAYROLL[fav] - PAYROLL[dog],
                "eFav": round(e_fav, 3),
                "mlFav": to_moneyline(e_fav),
                "mlDog": to_moneyline(1 - e_fav),
                "stake": round(stake, 2),
            })
    games.sort(key=lambda x: x["iso"])
    return games


def main():
    root = repo_root()
    sched_dir = os.path.join(root, "schedule")
    st, n_games, fav_win_pct = standings(sched_dir)
    sl = slate(sched_dir)
    payload = {
        "generated": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%MZ"),
        "season": 2026,
        "alpha": ALPHA,
        "modelCap": MODEL_CAP,
        "payrollAsOf": PAYROLL_ASOF,
        "gamesProcessed": n_games,
        "favWinPct": round(fav_win_pct, 4),
        "standings": st,
        "slate": sl,
    }
    out = os.path.join(root, "docs", "data.js")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, "w") as f:
        f.write("window.PAR = " + json.dumps(payload, separators=(",", ":"))
                + ";\n")
    print(f"Wrote {out}: {n_games} games -> {len(st)} teams, "
          f"{len(sl)} upcoming games")


if __name__ == "__main__":
    main()
