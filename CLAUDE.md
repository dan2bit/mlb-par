# mlb-par — project notes for Claude

## Commit discipline (hard rule)

**Always re-fetch the current file contents from `main` immediately before
any commit or push.** Never push a file from a cached/session copy — the
repo owner commits directly to `main` (and the daily Action does too), so
any cached version may be stale and pushing it will silently revert other
people's work. Workflow: fetch the live file → apply the change as a diff
against that fetched content → push. This rule exists because commit
ab54de7 (page header notes) was accidentally reverted by a push built from
a stale copy.

## Project facts

- Model: Payroll-Adjusted Record (PAR), upset-only weighting:
  g = max(1, 2·P_L^α/(P_L^α+P_W^α)), α = 0.5. Zero-sum per game.
- Payrolls: Spotrac 2026 Active payroll snapshot, hardcoded in
  scripts/generate_site.py and scripts/payroll_adjusted_record.py.
- Data: MLB Stats API (statsapi.mlb.com), free/keyless. NOT reachable from
  the Cowork sandbox (proxy 403) — fetch via host-side web fetch or the
  GitHub Actions runner (scripts/fetch_data.py).
- Site: GitHub Pages from main/docs. docs/data.js is generated — never
  hand-edit it; run scripts/generate_site.py instead.
- Daily refresh: .github/workflows/daily-refresh.yml (10:00 UTC cron).
  The PAT used by the GitHub MCP lacks the workflow scope — workflow file
  changes must be made by the repo owner in the GitHub UI.
- Slate cards link to Baseball Savant: gamefeed?gamePk=<pk> (pk carried in
  docs/data.js slate entries).
- Design doc: scripts/README.md. Full-season "baseline-excluded
  retrospective" variant is specced there but intentionally not built.
