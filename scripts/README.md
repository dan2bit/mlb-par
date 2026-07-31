# Payroll-Adjusted Record (PAR) — Design Sketch

A metric that re-weights MLB wins and losses by the payroll gap between the two teams. Expected outcomes are the baseline: when payrolls are roughly equal, or when the richer team wins, the game counts as a plain 1 win / 1 loss. When the poorer team wins, the upset credits the underdog with extra win value and debits the favorite with the same extra loss value, in proportion to the payroll gap.

## The algorithm — upset-only payroll-logistic

For a game where the winner has payroll `P_W` and the loser has payroll `P_L`:

    g = max(1, 2 · P_L^α / (P_L^α + P_W^α))

The winner is credited `g` adjusted wins; the loser is debited `g` adjusted losses.

How it behaves:

- **Expected outcome → g = 1.** If the winner's payroll ≥ the loser's, the inner expression is ≤ 1 and the max() clamps it: plain 1 win / 1 loss. Equal payrolls also give exactly 1, so the function is continuous — the upset branch starts at 1 and rises smoothly from there.
- **Upsets are bounded in (1, 2).** A win can never count more than double, no matter how extreme the ratio (Dodgers active payroll is ~11× Washington's).
- **Zero-sum per game.** The underdog's extra credit always equals the favorite's extra debit — no wins created that aren't matched by losses. Verified in the season run: Σ adjW = Σ adjL = 1737.34. (One side effect: Σ(adjW+adjL) exceeds games played, since upsets add weight with no offsetting discount. adjPct is the comparable stat.)
- **Performance still dominates.** A team involved in no upsets, either direction, keeps its exact real record. The metric adjusts at the margin instead of re-deriving the standings from payroll.
- **Elo-flavored kernel.** `E = P_A^α/(P_A^α + P_B^α)` is a payroll-implied win expectancy and the unclamped weight is `2·(1 − E_winner)`: payment in proportion to how unexpected the win was.

**α (alpha) is the sensitivity dial**, default **0.5** (square-root dampening of payroll ratios):

| Matchup (active payroll) | α = 0.25 | α = 0.5 | α = 1.0 |
|---|---|---|---|
| LAD ($369M) beats WSH ($34M) | 1.00 | 1.00 | 1.00 |
| WSH beats LAD | 1.28 | 1.51 | 1.83 |
| TB ($77M) beats NYY ($286M) | 1.16 | 1.32 | 1.57 |
| NYY beats TB | 1.00 | 1.00 | 1.00 |
| CHC ($210M) beats DET ($209M) | 1.00 | 1.00 | 1.00 |

α = 1 nearly doubles extreme upsets; α = 0.5 keeps them in a ~1.3–1.5 band, sensible for a sport where the worst team still beats the best ~1 time in 3.

**Adjusted record:** adjW = Σ g over wins, adjL = Σ g over losses, adjPct = adjW/(adjW+adjL). For a display "record," rescale to games played: `(adjPct·G, (1−adjPct)·G)`.

### Rejected variant: symmetric weighting

The first draft applied the unclamped `g = 2·P_L^α/(P_L^α+P_W^α)` to every game, so a favorite's win counted <1. That punished rich teams merely for winning: LAD's 67 wins shrank to 51 adjusted and cheap .500 teams (WSH, STL, MIA) auto-led the table, drowning out actual performance. Kept in the script as `MODE = "symmetric"` for comparison. Also considered and rejected: a raw power ratio `g = (P_L/P_W)^α`, which is unbounded (a Marlins-over-Dodgers win at α=1 would count ~9 wins).

## Results — 2026 season through July 27 (1,597 games, α = 0.5)

| # | Team | W–L | Pct | adjPct | Δ |
|---|------|-----|-----|--------|---|
| 1 | MIL | 66–40 | .623 | .631 | +.008 |
| 2 | TB | 62–43 | .590 | .619 | +.029 |
| 3 | LAD | 67–39 | .632 | .580 | −.052 |
| 4 | WSH | 54–53 | .505 | .575 | +.070 |
| 5 | STL | 53–53 | .500 | .564 | +.064 |
| 6 | CHW | 55–50 | .524 | .564 | +.040 |
| 7 | ATL | 62–45 | .579 | .553 | −.026 |
| 8 | CLE | 54–53 | .505 | .552 | +.048 |
| 9 | MIA | 53–54 | .495 | .551 | +.056 |
| 10 | MIN | 53–54 | .495 | .537 | +.042 |
| 11 | CHC | 60–46 | .566 | .534 | −.032 |
| 12 | PIT | 55–52 | .514 | .528 | +.014 |
| 13 | NYY | 60–46 | .566 | .525 | −.041 |
| 14 | ARI | 55–52 | .514 | .501 | −.013 |
| 15 | PHI | 57–50 | .533 | .499 | −.034 |
| 16 | TEX | 54–52 | .509 | .498 | −.011 |
| 17 | BOS | 55–50 | .524 | .498 | −.026 |
| 18 | CIN | 49–55 | .471 | .483 | +.011 |
| 19 | SEA | 52–55 | .486 | .476 | −.010 |
| 20 | SD | 53–53 | .500 | .475 | −.025 |
| 21 | BAL | 52–55 | .486 | .472 | −.014 |
| 22 | HOU | 53–55 | .491 | .459 | −.031 |
| 23 | DET | 50–57 | .467 | .444 | −.023 |
| 24 | ATH | 44–62 | .415 | .435 | +.020 |
| 25 | COL | 42–65 | .393 | .434 | +.042 |
| 26 | TOR | 49–58 | .458 | .419 | −.039 |
| 27 | SF | 46–61 | .430 | .413 | −.017 |
| 28 | KC | 45–62 | .421 | .405 | −.016 |
| 29 | LAA | 42–65 | .393 | .388 | −.005 |
| 30 | NYM | 45–62 | .421 | .375 | −.046 |

Face validity is good: MIL leads on merit with a small value bonus, LAD holds 3rd (excellent record, but many wins came as a massive favorite and their upset losses cost 1.2–1.5 each), cheap near-.500 teams get real credit without auto-leading, and NYM — losing record on the #2 payroll — is last.

## Payroll basis

Spotrac 2026 **Active** payroll, snapshotted into the script (per spec: no retroactive per-game payroll). Note the Active column excludes retained/deferred salary, which makes STL ($39.7M active vs $126M tax payroll), WSH, and MIA look far poorer than their real spend; alternatives (Active+Retained, or total tax payroll) are a one-line change to the `PAYROLL` dict if ever wanted.

## Tooling evaluation

**Data sources — both verified working:**

- **MLB Stats API** (`statsapi.mlb.com`) — free, keyless, official. One `/api/v1/schedule?sportId=1&season=2026&gameType=R` call returns every game with scores and winners; a `fields=` filter trims it to ~10% size. (The Cowork sandbox proxy blocks it, so fetching goes through the host-side web fetch; a chunked fetch of the full season took ~7 calls.)
- **Spotrac payroll page** — fetches cleanly as a table including the Active column. Treated as a periodic snapshot baked into the script, refreshed occasionally.

**Wrapper options:**

1. **Plain script (what the PoC is)** — `payroll_adjusted_record.py`, stdlib only. Right tool for batch computation: one bulk fetch + local math over 1,600 games. **Recommended core regardless of wrapper.**
2. **Cowork plugin/skill wrapping the script** — a skill ("update PAR standings") that re-fetches the schedule, reruns, and reports movers; optionally on a weekly schedule. Cheap to build with the existing `create-cowork-plugin` skill. **Recommended next step.**
3. **Existing MLB MCP servers** — [guillochon/mlb-api-mcp](https://github.com/guillochon/mlb-api-mcp) (FastMCP, comprehensive), [mpizza/mcp_mlb_statsapi](https://github.com/mpizza/mcp_mlb_statsapi) (schedules/results/lookup), [etweisberg/mlb-mcp](https://github.com/etweisberg/mlb-mcp) (adds Statcast/FanGraphs), [pipeworx-io/mcp-mlb-stats](https://github.com/pipeworx-io/mcp-mlb-stats), plus the [toddrob99/MLB-StatsAPI](https://github.com/toddrob99/MLB-StatsAPI) Python library they wrap. Good for conversational queries, wrong shape for this project's core loop (~1,600 per-game tool calls vs one bulk fetch). Connect later only for ad-hoc Q&A.
4. **Custom MCP server for PAR itself** — overkill unless you want the metric queryable from any Claude surface.

## Pipeline sketch (steady state)

1. Refresh payroll snapshot from Spotrac (manual or monthly) → `PAYROLL` dict.
2. Fetch season schedule (bulk, `fields`-filtered) → local JSON.
3. Filter to Final regular-season games with a winner (codedGameState = "F"); skip postponements/suspensions.
4. Apply `g = max(1, 2·P_L^α/(P_L^α+P_W^α))`, accumulate per team.
5. Emit standings (+ zero-sum sanity check); optionally track week-over-week movers.

## Future extension — baseline-excluded retrospective (not yet run)

Only applicable to a **complete** season, not a partial one. The premise: there is a floor and ceiling every team hits regardless of payroll — no team in MLB history has won fewer than ~55 games or lost fewer than ~52 in a full season. Those games are noise common to all 30 teams. So for a full-season retrospective: exclude 55 **non-upset** wins and 52 **non-upset** losses (the weight-1.0 games) from each team's ledger, then apply the formula only to the residual ~55 "discretionary" games. The question it answers: how did the team do relative to payroll, excluding the baseline outcomes every team experiences?

Design choice to settle before implementing: a team may have fewer than 55 weight-1 wins (a cheap team's wins are mostly upsets) or fewer than 52 weight-1 losses (an expensive team's losses are mostly upsets). Likely rule: remove weight-1 games first, then the lowest-weight remaining games until the quota is met — so the strongest payroll signals are the last to be excluded.

## Files

- `payroll_adjusted_record.py` — working PoC (`MODE` = "upset_only" default, "symmetric" available)
- `sched_1.json` … `sched_7.json` — 2026 schedule through 7/27
