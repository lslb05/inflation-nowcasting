# Decisions

Record only decisions that change the future cost of change.

## Template

### YYYY-MM-DD — Title

- **Context:** what constraint or problem required a decision.
- **Decision:** the path chosen.
- **Alternatives:** relevant options discarded.
- **Consequences:** gains, costs and the trigger to revisit.

### 2026-08-18 — Keep `CLAUDE.md` and `AGENTS.md` in the public repository

- **Context:** both files declare that the repository is built with agent
  support. The alternative was ignoring them in git so the public
  repository wouldn't reveal the workflow.
- **Decision:** keep both versioned and public.
- **Alternatives:** ignore `AGENTS.md` in `.gitignore`; keep it local only.
  Both break delegation to Codex, which reads this file from the
  repository — the cost is functional and immediate, the gain is cosmetic.
- **Consequences:** the repository states the method instead of hiding it,
  which is also verifiable by whoever reads it. Revisit if some destination
  ever requires the opposite.

### 2026-08-19 — Each month's cutoff comes from the CPI's own `data_publicacao`

- **Context:** simulating "today" for each backtest month requires knowing
  when that month's CPI was released. The obvious alternative is assuming a
  calendar (e.g. "always the 12th of the following month"), but the BLS's
  actual release date varies month to month.
- **Decision:** each month's cutoff is the `data_publicacao` of that
  month's first CPI vintage (ALFRED), minus one day. It comes from the data
  itself.
- **Alternatives:** a hardcoded fixed calendar — simpler to write, but
  silently wrong in any month the release runs late, and undetectable
  without separately comparing against the real BLS calendar.
- **Consequences:** each month's cutoff is always correct as long as the
  CPI vintage is correct — no calendar maintenance. Cost: a month whose CPI
  hasn't been ingested yet is dropped from the backtest (not approximated),
  which is the right behavior, not a hidden limitation.

### 2026-08-19 — `numpy.linalg.lstsq` instead of `statsmodels`

- **Context:** the bridge model needs a multivariate linear regression
  (intercept + 3 regressors). `statsmodels` is the market standard for
  regression in Python, but brings statistical diagnostics (p-value, R²,
  residuals) this cut doesn't use — only the fitted coefficient, to predict.
- **Decision:** `numpy.linalg.lstsq` on the design matrix with an intercept
  column — plain least squares, without the statistical-inference layer.
- **Alternatives:** `statsmodels.OLS` — more complete, but a heavy new
  dependency for a project that neither reports p-values nor tests
  hypotheses on the coefficients in this cut.
- **Consequences:** fewer dependencies; the cost is that if a future cut
  needs significance diagnostics for the regressors (e.g. to justify
  dropping one), migrating to `statsmodels` is the right trigger — not
  worth adding now speculatively.
