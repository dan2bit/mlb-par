#!/usr/bin/env python3
"""
Payroll-Adjusted Record (PAR) — proof of concept.

Weights each 2026 regular-season win/loss by the payroll gap between the
two teams. Equal payrolls -> win/loss counts 1.0. Underdog win over a
richer team counts >1 (and the favorite's loss counts the same amount);
favorite win over a poorer team counts <1.

Game weight (recommended, "payroll-logistic"):
    g = 2 * P_loser^a / (P_loser^a + P_winner^a)      a = ALPHA
Bounded in (0, 2), zero-sum per game (winner's credit == loser's debit),
equal payrolls give exactly 1.

Payrolls: Spotrac 2026 "Active" payroll, snapshot 2026-07-28.
Schedule/results: MLB Stats API (statsapi.mlb.com), free, no key.
"""
import glob
import json
import os

ALPHA = 0.5  # sensitivity; 1.0 = full ratio, 0.5 = square-root dampening

# "symmetric":  every game weighted by payroll gap (favorite's win < 1)
# "upset_only": expected outcome (richer team wins) = plain 1 win / 1 loss;
#               weight applied only when the poorer team wins (g > 1)
MODE = "upset_only"

# Spotrac 2026 Active payroll ($), snapshot 2026-07-28
# https://www.spotrac.com/mlb/payroll/_/year/2026
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

# MLB Stats API team id -> Spotrac abbreviation
TEAM_ID = {
    108: "LAA", 109: "ARI", 110: "BAL", 111: "BOS", 112: "CHC",
    113: "CIN", 114: "CLE", 115: "COL", 116: "DET", 117: "HOU",
    118: "KC", 119: "LAD", 120: "WSH", 121: "NYM", 133: "ATH",
    134: "PIT", 135: "SD", 136: "SEA", 137: "SF", 138: "STL",
    139: "TB", 140: "TEX", 141: "TOR", 142: "MIN", 143: "PHI",
    144: "ATL", 145: "CHW", 146: "MIA", 147: "NYY", 158: "MIL",
}


def game_weight(p_winner: float, p_loser: float, alpha: float = ALPHA,
                mode: str = None) -> float:
    """Zero-sum per game. Equal payrolls -> 1.0.

    symmetric:  g = 2*P_L^a/(P_L^a+P_W^a), bounded (0,2)
    upset_only: g = max(1, same) -> favorite win is exactly 1/1,
                upsets credited/debited on a (1,2) scale
    """
    w, l = p_winner ** alpha, p_loser ** alpha
    g = 2 * l / (w + l)
    return max(1.0, g) if (mode or MODE) == "upset_only" else g


def fetch_season(season=2026):
    """Load pre-fetched schedule windows (sched_*.json) from this script's dir."""
    here = os.path.dirname(os.path.abspath(__file__))
    dates = []
    for path in sorted(glob.glob(os.path.join(here, "sched_*.json"))):
        with open(path) as f:
            dates.extend(json.load(f).get("dates", []))
    return {"dates": dates}


def main():
    data = fetch_season()
    rec = {ab: {"W": 0, "L": 0, "adjW": 0.0, "adjL": 0.0} for ab in PAYROLL}
    n_games = 0
    for date in data["dates"]:
        for g in date["games"]:
            if g["status"].get("codedGameState") != "F":
                continue
            home, away = g["teams"]["home"], g["teams"]["away"]
            if "isWinner" not in home:  # tie/suspended edge case
                continue
            winner, loser = (home, away) if home["isWinner"] else (away, home)
            w_ab = TEAM_ID.get(winner["team"]["id"])
            l_ab = TEAM_ID.get(loser["team"]["id"])
            if not w_ab or not l_ab:
                continue
            gw = game_weight(PAYROLL[w_ab], PAYROLL[l_ab])
            rec[w_ab]["W"] += 1
            rec[w_ab]["adjW"] += gw
            rec[l_ab]["L"] += 1
            rec[l_ab]["adjL"] += gw
            n_games += 1

    print(f"2026 regular-season final games processed: {n_games}\n")
    print(f"{'Team':<5}{'W':>4}{'L':>4}{'Pct':>7}"
          f"{'adjW':>8}{'adjL':>8}{'adjPct':>8}{'Δpct':>7}")
    rows = []
    for ab, r in rec.items():
        gp = r["W"] + r["L"]
        if gp == 0:
            continue
        pct = r["W"] / gp
        apct = r["adjW"] / (r["adjW"] + r["adjL"])
        rows.append((ab, r["W"], r["L"], pct, r["adjW"], r["adjL"], apct))
    for ab, w, l, pct, aw, al, apct in sorted(rows, key=lambda x: -x[6]):
        print(f"{ab:<5}{w:>4}{l:>4}{pct:>7.3f}"
              f"{aw:>8.1f}{al:>8.1f}{apct:>8.3f}{apct-pct:>+7.3f}")

    # zero-sum sanity check
    tot_w = sum(r["adjW"] for r in rec.values())
    tot_l = sum(r["adjL"] for r in rec.values())
    print(f"\nSanity: sum(adjW)={tot_w:.2f} sum(adjL)={tot_l:.2f} "
          f"(must be equal)")


if __name__ == "__main__":
    main()
