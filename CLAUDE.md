# Project contract — Inflation Nowcasting

Read the global `CLAUDE.md` and use this file for what's specific to this
repository.

## Product outcome

- **Problem:** CPI nowcasting is a classic bridge/mixed-frequency problem,
  but easy to get wrong via information leakage — using a future revision
  or an indicator published after the simulated "today." Proving that
  discipline is what separates this from a toy notebook.
- **User:** me, and whoever reviews the portfolio evaluating for
  quantitative research.
- **Verifiable output:** for each month of the test period, the m/m CPI
  nowcast using only data with `data_publicacao <=` that month's simulated
  cutoff, compared to the first published value (not the revision), with
  MAE against a naive baseline (repeating the prior month's change).
- **Allowed data source:** FRED via Postgres from `public-market-data`
  (`series_vintage`) — `CPIAUCSL` (target), `T10YIE` (10y breakeven, daily),
  `DCOILWTICO` (WTI, daily), `MICH` (Michigan expectations, monthly). Each
  month's cutoff date is the CPI's own `data_publicacao` in that vintage,
  not a hardcoded calendar.
- **Smallest end-to-end cut:** a CLI that runs the point-in-time backtest
  for a month range and prints a table (month, nowcast, released, baseline,
  nowcast error, baseline error).
- **Out of scope:** a multivariate state-space/Kalman model, forecasting
  more than 1 month ahead, a dashboard, more than 3 auxiliary indicators.

Do not implement while a `FILL_IN` that changes the design is still open.

## Commands

```bash
uv sync
uv run python scripts/format.py
uv run python scripts/check.py
```

## Local rules

- The package is `inflation_nowcasting` and lives in `src/inflation_nowcasting`.
- Notebooks import from `src/`; production code never imports a notebook.
- Configuration comes from the environment via `Settings`.
- Preserve raw data and time-vintage metadata whenever there's ingestion.
- Update this file when a structural decision changes.

## Style

Public code, read by people. The rule is restraint — the full list is in
`AGENTS.md`, "Style" section, and applies equally to me and to Codex.

- A comment explains *why*, never *what*. If it paraphrases the line below,
  delete it; if the line needs paraphrasing, rename the variable instead.
- Docstrings only where the signature isn't enough (unit, timezone, side
  effect, what it raises). A three-line private helper doesn't need one.
- Tests assert behavior that can break, not a constant. Coverage is a
  consequence of testing what matters, never a target to inflate.
- Don't catch an exception you don't know how to handle; don't abstract for
  a single caller.

## Commit authorship

Author and committer are one and the same: the repository owner. No
`Co-Authored-By:`, no session trailer, no mention of Claude, Codex or any
tool. Don't change `user.name` or `user.email`.

## Session state

- **Decided:** first cut delivered — a point-in-time walk-forward backtest
  of m/m CPI (OLS via `numpy.linalg.lstsq`, 3 regressors) against a naive
  baseline, reading `series_vintage` from `public-market-data`. Each
  month's cutoff comes from the CPI's real `data_publicacao`, not an
  assumed calendar.
- **Pending:** never run against real FRED data — an API key is needed to
  ingest `CPIAUCSL`/`T10YIE`/`DCOILWTICO`/`MICH` in the neighboring
  project. All point-in-time discipline is validated with synthetic data.
- **Next step:** with a FRED key, ingest the four series and run the real
  backtest to see whether the nowcast's MAE beats the baseline over a real
  period — today that's an open question, not a claim.
