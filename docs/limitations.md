# Known limitations (Phase 0)

Honesty is a feature. What this system does **not** yet do:

1. **Regime model is a heuristic baseline.** Regime probabilities come from a
   fixed-weight z-score classifier, not the HMM. No historical validation has
   been performed yet; do not trust the probabilities for real decisions until
   the Phase 2 validation report exists.
2. **Stress shocks are uncalibrated.** The per-regime EBITDA shock parameters
   are placeholders pending historical regression / literature review (PRD Q2).
3. **No live data.** There is no FRED ingestion yet; snapshots are created from
   caller-provided frames. Phase 2 adds `atlas.domain.data`.
4. **No API, queue, scheduler or agent.** Engines run in-process only (Phase 1
   adds the API/queue; Phase 3 adds the orchestrator/narrator).
5. **Valuation is a single-multiple model.** EV = EBITDA x multiple over a
   one-year horizon; no DCF, no WACC, no multi-year paths yet.
6. **Single tenant, no auth.** API keys arrive with the API in Phase 1.
