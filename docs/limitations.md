# Known limitations (Phase 2)

Honesty is a feature. What this system does **not** yet do:

1. **The HMM is outperformed by naive rules on crisis precision.** The
   validation report (`validation_report.md`) shows VIX>30 and a wide-spread
   rule both beat the HMM on precision. The model over-predicts crisis during
   post-recession credit normalization (high recall, low precision). It is a
   conservative bias — defensible for monitoring, but a real weakness, published
   unmodified (PRD risk #1).
2. **Detection lag resolves only to the month.** Macro data is monthly, so a
   "1-month lag" could be anywhere from 1 to ~30 days. Daily-frequency detection
   is parking-lot work.
3. **Stress shocks are uncalibrated.** The per-regime EBITDA shock parameters
   are literature-informed placeholders, not yet fit by historical regression
   (PRD Q2, still open). The validation report's sensitivity grid shows how much
   P(impairment) moves across plausible values.
4. **No scheduler, alerts or agent.** Analyses run on demand via the API;
   POST /agent/ask is an honest stub until Phase 3; scheduling is Phase 4.
5. **Valuation is a single-multiple model.** EV = EBITDA x multiple over a
   one-year horizon; no DCF, no WACC, no multi-year paths yet.
6. **Single tenant.** API keys with read/run scopes exist; organizations and
   billing are out of scope for v1 (PRD NG4).
