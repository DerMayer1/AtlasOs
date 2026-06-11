# Known limitations (Phase 3)

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

1. **The HMM is outperformed by naive rules on crisis precision, and this is
   structural.** VIX>30 and a wide-spread rule both beat the HMM on precision.
   We investigated (ADR-015): switching the spread feature from level to change
   improved real-time COVID detection but did *not* lift precision, and a causal
   threshold sweep is flat because the probabilities are saturated — the model
   *confidently* over-calls crisis. The cause is unsupervised states (comparably
   sized) vs. a rare label (~16% of months). The real fix is supervised/
   semi-supervised calibration of the crisis state; published unmodified meanwhile
   (PRD risk #1). High recall makes it a defensible *monitoring* bias.
2. **Detection lag resolves only to the month.** Macro data is monthly, so a
   "1-month lag" could be anywhere from 1 to ~30 days. Daily-frequency detection
   is parking-lot work.
3. **Stress shocks are calibrated, but the std is an aggregate lower bound.**
   The per-regime shocks are now fit by regime-dummy regression of corporate
   profits over NBER+ windows (PRD Q2 closed; ADR-016). But `CP` is aggregate,
   so its volatility understates single-company EBITDA dispersion — the
   regime-conditional *mean* is well identified, the *std* is a floor.
   Cross-sectional dispersion calibration is future work.
4. **No scheduler or alerts.** Analyses and agent runs are on demand via the
   API; recurring analysis and threshold alerts are Phase 4.
5. **Valuation is a single-multiple model.** EV = EBITDA x multiple over a
   one-year horizon; no DCF, no WACC, no multi-year paths yet.
6. **Single tenant.** API keys with read/run scopes exist; organizations and
   billing are out of scope for v1 (PRD NG4).
