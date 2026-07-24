# Known limitations (Phase 4a)

Honesty is a feature. What this system does **not** yet do:

0. **The orphan-claim detector treats only decimals and percentages as claims.**
   A bare integer asserted by the narrator (e.g. "12 companies") would not be
   flagged as an orphan. Engine outputs are probabilities/percentages/decimals,
   so this is safe in practice, but it is a real edge of the validator. Years
   (2008, 2020) are excluded on purpose for the same reason.
0b. **Eval suite scripts the LLM.** CI runs the agent logic against a scripted
   model, not the live API, so it catches regressions in orchestration,
   narration, citation validation and prompt wiring — but not changes in the
   real model's behaviour. A live eval run needs a key and is manual.

1. **The hybrid crisis classifier remains a validation candidate.** A fixed VIX
   stress override raises provisional walk-forward recall from 0.355 to 0.645,
   PR-AUC from 0.515 to 0.686 and improves Brier from 0.115 to 0.095. It also
   raises false alerts from 0.18 to 0.94 per year. These are materially better
   operating characteristics, but promotion into the impairment engine remains
   gated on the point-in-time rerun below.
1b. **ALFRED ingestion is implemented; release evidence needs a FRED API key.**
   Validation defaults to initial releases (`output_type=4`) and stores them in
   a separate immutable cache. The checked-in report is explicitly marked as a
   provisional revised-FRED run because no API key is committed. Regenerate it
   with `ATLAS_FRED_API_KEY` before treating the metrics as release evidence.
2. **Detection lag resolves only to the month.** Macro data is monthly, so a
   "1-month lag" could be anywhere from 1 to ~30 days. Daily-frequency detection
   is parking-lot work.
3. **Stress-shock std falls back to an aggregate lower bound when a company has
   no history.**
   The per-regime shocks are now fit by regime-dummy regression of corporate
   profits over NBER+ windows (PRD Q2 closed; ADR-016). But `CP` is aggregate,
   so its volatility understates single-company EBITDA dispersion — the
   regime-conditional *mean* is well identified, the *std* is a floor.
   When at least four annual company EBITDA observations are supplied, the
   engine estimates that company's log-growth volatility and records the source
   in `risk_calibration.json`.
4. **Alerts are on demand, not delivered automatically.** The Macro Monitor
   identifies level and momentum alerts inside each run, but there is no
   scheduler, notification channel or recurring execution.
4b. **Macro scenarios are references, not forecasts.** Tightening and crisis
   levels are historical medians for periods assigned to those HMM states.
   They provide transparent comparison anchors, not dated point forecasts.
5. **Valuation is still market-multiple based.** The engine now models joint
   EBITDA and multiple distributions, macro/sector/company factors, explicit
   cross-company dependence and 1/3-year scenarios. It still does not implement
   a DCF, WACC term structure, tax effects or cash-flow conversion.
5b. **Correlation has a transparent fallback hierarchy.** A user-supplied PSD
   matrix wins; otherwise five aligned annual EBITDA observations per company
   produce a shrunk empirical matrix. Shared market/sector assumptions remain
   only when histories are insufficient. The selected source and matrix are
   published in `risk_calibration.json`.
5c. **Debt diagnostics are deliberately separate from accounting impairment.**
   Net leverage, interest coverage and near-term liquidity are reported as
   financial resilience indicators. They do not mechanically alter recoverable
   amount, which remains EBITDA x stochastic multiple versus carrying value.
5d. **Regime multiple compression is an assumption, and it dominates crisis
   severity.** Recoverable amount is `EBITDA x multiple`. The per-regime EBITDA
   shock is calibrated from corporate-profit history (item 3), but the
   per-regime multiple re-rating (`expansion +4%`, `tightening -12%`,
   `crisis -30%`) is a hand-set analyst assumption — no point-in-time
   market-multiple series is ingested, so there is nothing to fit it against.
   Because the calibrated crisis EBITDA shock is only about -2%, roughly **95%**
   of the mean crisis decline in recoverable value comes from this uncalibrated
   -30% term. The values and their `assumption` provenance are emitted in
   `shock_calibration.json` and in every run's `risk_calibration.json`. Treat
   the crisis scenario as a transparent stress assumption, not a calibrated
   forecast; calibrating compression against a market-multiple series (e.g. a
   sector EV/EBITDA history) is the natural next step.
6. **Organization isolation is implemented; billing is not.** Every API key is
   bound to an organization and portfolio, analysis, report, trace and artifact
   access is organization-scoped. Subscription plans, metering and invoicing
   remain outside the product.
