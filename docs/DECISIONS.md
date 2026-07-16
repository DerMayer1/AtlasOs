# Architecture Decision Records

## ADR-001 — Source layout: `src/atlas/*` instead of top-level `platform/`, `domain/`

The PRD sketches top-level directories (`platform/`, `domain/`, ...). A top-level
Python package named `platform` would shadow the stdlib `platform` module and break
third-party libraries. All code therefore lives under the `atlas` namespace
(`atlas.platform`, `atlas.domain`, ...) with a `src/` layout. The PRD's dependency
rule is preserved and enforced by `tests/test_import_direction.py`.

## ADR-002 — Phase 0 regime model is a z-score classifier, not the HMM

There is no legacy Atlas script in this repository to migrate, so Phase 0 ships a
deterministic baseline: z-scores of the latest macro observation against history,
mapped to regime probabilities via a fixed weight matrix + softmax
(`atlas/domain/engines/impairment/regimes.py`). It implements the exact function
signature the Phase 2 HMM will replace, and the validation report (R6) will
benchmark both. The PRD's R5 regression test ("new output == legacy") becomes
"new output == frozen baseline output" once the HMM lands.

## ADR-003 — Snapshot identity = content hash of logical data

`snapshot_id` is derived from `pd.util.hash_pandas_object` over each table (logical
content), while integrity verification uses sha256 of the parquet bytes on disk.
Rationale: the same dataset frozen twice gets the same id (idempotent ingestion),
but any post-freeze byte tampering is detected on load. Snapshots are published via
atomic directory rename, so a half-written snapshot can never be read.

## ADR-004 — Stress shock coefficients are placeholders

`_SHOCKS` in the impairment engine (per-regime EBITDA growth mean/std) are
uncalibrated placeholders. PRD Q2 (calibrate by historical regression or
literature) is blocking for R6 and is scheduled for Phase 2. Tracked in
`docs/limitations.md`.

## ADR-005 — Sync SQLAlchemy + dual queue mode for Phase 1

Persistence uses synchronous SQLAlchemy (psycopg) — FastAPI runs sync endpoints
in its threadpool, and the ARQ worker offloads the sync runner to an executor.
Async DB would add asyncpg/aiosqlite complexity with no benefit at v1 load.

The queue is an interface with two implementations: ARQ + Redis in production
(`ATLAS_REDIS_URL` set) and an in-process queue for dev/tests (empty URL). The
API contract is identical in both modes: POST /analyses returns a job_id and
clients poll GET /analyses/{id}. Tests therefore exercise the real API surface
without service containers; docker compose exercises the real queue.

## ADR-006 — /agent/ask ships as an honest stub until Phase 3

The PRD lists POST /agent/ask as a P0 endpoint, but the orchestrator is a
Phase 3 deliverable. Until then the endpoint answers exactly as the PRD edge
case demands of the future agent: it states it has no agent capability and
lists the engines that exist. Never inventing > pretending.

## ADR-007 — FRED ingestion via the keyless fredgraph endpoint

Phase 2 ingests from `fred.stlouisfed.org/graph/fredgraph.csv`, which needs no
API key, rather than the JSON API (which does). Rationale: zero-config
reproducibility for an external evaluator (PRD persona 4) and no secret to
manage in CI. The `DataSource` abstraction (PRD P2) still applies — fredgraph
is one implementation. Daily series (T10Y2Y, VIXCLS) are fetched in 5-year
chunks because the endpoint returns 504 on full-history daily requests;
monthly series come in one request. Caching is incremental: refreshes refetch
only from 60 days before the last cached point to absorb FRED's retroactive
revisions, exactly the scenario snapshots exist to neutralize (PRD risk table,
last row).

## ADR-008 — HMM feature set: unemployment *change*, not level

The Phase 2 production model is a 3-state diagonal-Gaussian HMM fit by
Baum-Welch in plain numpy (≈150 lines we control, for bit-reproducibility —
seeded k-means init + fixed iteration budget). Features are fed-funds, BAA-AAA
spread, 10y-2y curve, CPI YoY, and the **12-month change** in unemployment.
The level was tried first and made the crisis state absorb the entire jobless
recovery (124 expansion months mislabeled crisis in the first run), because the
unemployment level stays elevated for years after a recession ends. The change
is a coincident signal instead of a lagging one. The Phase 0 z-score classifier
is retained as `regime_model="zscore"` and is the comparison baseline in the
validation report (ADR-002 fulfilled).

## ADR-009 — Validation results are published as-is

The validation report (`docs/validation_report.md`) shows the HMM beaten on
crisis-detection *precision* by both naive benchmarks (VIX>30, wide spread),
with a documented over-prediction bias during post-recession credit
normalization. Per PRD risk #1 ("honestidade é feature") these numbers are
published unmodified rather than tuned until they flatter the model. Improving
calibration (spread *change* as a feature, daily-frequency detection) is
legitimate future work in the parking lot, not a blocker for shipping the
phase.

## ADR-010 — Citation syntax (resolves PRD Q1)

A citation is ``[<artifact_id>:<locator>]`` where ``artifact_id`` is
``<run_id>/<filename>`` (globally addressable, matches the ArtifactStore) and
the locator addresses one value: ``<column>@<row_key>`` for CSV (e.g.
``p_impairment@Beta Logistics``) and a dot-path key for JSON (e.g.
``portfolio_mean_p_impairment``). Cell-level granularity, not just line — this
is what lets the Phase 4 frontend open the exact figure behind a claim. Q1 is
hereby closed: cell/key locators, not whole lines.

## ADR-011 — LLM behind an interface; graceful degradation is the default path

The agent talks to an ``LLMClient`` protocol with three implementations:
``OpenAILLMClient`` (production), ``ScriptedLLMClient`` (deterministic,
drives tests + evals with zero cost), and ``NullLLMClient`` (no key). With no
key the orchestrator falls back to a deterministic keyword planner and the
narrator to a fully-cited template — so the system is completely functional and
honest offline, and this *is* the PRD's graceful-degradation requirement (LLM
down → numbers-only, pipeline never blocks). Set ``ATLAS_OPENAI_API_KEY``
for LLM planning + prose. The LLM only ever sees the capability catalog and a
CITABLE VALUES list — never raw snapshot data (PRD §7.1 principle 2).

## ADR-012 — Citation validation: number-must-cite, with one retry then degrade

The validator flags any decimal/percentage figure not immediately backed by a
resolving citation (orphan), any citation that doesn't resolve (broken), and
any cited figure whose value doesn't match the artifact (mismatch). Integers
(years like 2008) are deliberately not treated as claims to keep false
positives near zero; this limitation is documented. On failure the narrative is
regenerated once; if it still fails, the report ships the deterministic
numbers-only template (PRD R7 acceptance, verbatim).

## ADR-013 — Eval suite uses a scripted LLM and gates CI

The ≥15-case eval suite (``agent/evals``) scripts the LLM so it is
deterministic, free, and network-free — it tests the real orchestrator,
narrator, validator and prompts end-to-end (a regression flips a structured
assertion). ``PROMPT_VERSION`` is asserted and recorded in every trace, so
editing a prompt is a versioned, eval-gated change. CI runs the suite as a
hard gate (``python -m atlas.agent.evals.runner`` exits non-zero on
regression). A ``live=True`` path against the real model is available for
manual runs but kept out of CI to avoid cost/flakiness (PRD R8 + risk table).

## ADR-014 — /agent/ask is synchronous in v1

Unlike /analyses (queued), /agent/ask runs the full orchestration inline and
returns the answer. The heavy work (engine Monte Carlo) is already fast and the
LLM calls are short; an async orchestration job is a clean future enhancement
but would double the surface for no v1 benefit.

## ADR-015 — HMM spread-change feature; the precision ceiling is structural

We hypothesised that the low crisis *precision* (many expansion months called
crisis) came from the credit-spread *level* persisting after the acute phase,
and switched the feature to its 6-month *change* (model `hmm3sc`). Measured
result: out-of-sample COVID detection improved to a 0-month causal lag, but
argmax precision did **not** improve, and a causal P(crisis) threshold sweep is
flat (saturated probabilities) — see validation_report.md §4/§4b. Conclusion:
the precision ceiling is structural — an unsupervised 3-state HMM splits history
into comparably-sized states while true crisis is rare (~16% of months), so it
*confidently* over-calls. We kept the change feature (better real-time COVID
detection, principled consistency with the unemployment-change feature) but the
real fix is supervised/semi-supervised calibration of the crisis state, which is
in the parking lot. Documented, not dressed up (PRD risk #1).

## ADR-016 — Stress shocks calibrated from reference NBER windows (closes Q2)

`scripts/calibrate_shocks.py` estimates the per-regime EBITDA shock as a
regime-dummy regression of FRED corporate-profit (`CP`) YoY growth, writing
`shock_calibration.json` (loaded by the engine; a hardcoded fallback remains).
Regimes for calibration are the **reference NBER+ windows, not the model's own
HMM output** — calibrating the model's shock off its own over-broad crisis state
is circular and, when first tried, produced a *positive* crisis mean (the broad
crisis state absorbs high-rebound recovery quarters). PRD Q2 is closed: the
coefficients now have a historical origin, not a chosen one. Caveats recorded in
the report and limitations: `CP` is aggregate (its std understates single-name
dispersion — mean well identified, std a lower bound) and the mild crisis mean
is pulled up by the 2011 stress-without-recession window and nominal growth.

## ADR-017 — Crisis validation is supervised and walk-forward

The HMM no longer serves as the final crisis classifier in validation. Its
probabilities are retained as candidate features and as a benchmark, while a
small L2-regularized logistic model is trained against a versioned binary
target. The primary target uses strict NBER recession months; a broader stress
definition is reported separately as sensitivity analysis.

Every headline score is produced by expanding walk-forward folds. Feature
normalization, HMM fitting, logistic fitting and threshold selection occur
inside the training period only. CPI and unemployment are shifted one month to
approximate publication delay. Thresholds maximize training precision subject
to a 60% recall floor, and the report prioritizes PR-AUC, Brier score and false
alerts per year over class-imbalanced accuracy.

The logistic implementation is kept in NumPy rather than adding a second
modelling dependency. Current revised FRED history still creates possible
revision look-ahead; vintage ALFRED data is the next credibility upgrade.

## ADR-018 — Impairment uses a joint factor model; debt remains a separate lens

The first impairment model applied one common normal EBITDA shock and a fixed
multiple to every company. Engine 1.0 replaces that bridge with positive
multiplicative EBITDA paths, stochastic bounded multiples and shared market and
sector factors plus company-specific residuals. This creates explicit,
non-perfect cross-company dependence and controlled base/tightening/crisis
comparisons over one- and three-year horizons.

The model publishes expected impairment loss, tail loss, scenario distributions,
value correlations, sensitivities and break-even points. Debt, cash, interest
coverage and near-term liquidity are published separately as resilience
diagnostics. They do not enter the accounting impairment test mechanically:
recoverable amount remains enterprise value versus carrying value. Correlation
and company-volatility defaults are transparent structural assumptions until
company-level calibration data is available.

## ADR-019 — Macro Monitor is a state monitor, not a market forecaster

Engine 2 reuses the same causal filtered HMM as impairment and publishes a
separate, versioned `macro_state.json`. It adds indicator level and momentum
standardization, adverse percentiles, stress breadth, one-month probabilities
from the fitted transition matrix, optional snapshot comparison and explicit
alert evidence.

Its base/tightening/crisis scenarios are state-conditioned historical medians.
They are reference conditions for downstream analyses, not point forecasts.
Alerts are calculated only when a run is explicitly requested; scheduling and
notification delivery remain separate concerns. This keeps the engine
deterministic, snapshot-bound and honest about what the model can infer.

## ADR-020 — Validation uses ALFRED initial releases by default

`scripts/validation_report.py` now defaults to the official FRED API with
`output_type=4`, which returns each observation's initial release. ALFRED data
has its own cache and requires `ATLAS_FRED_API_KEY`. Revised FRED history remains
available only through the explicit `ATLAS_VALIDATION_DATA_SOURCE=fred`
development mode, and reports generated that way label themselves provisional.

## ADR-021 — Crisis operation is a causal hybrid, not a threshold-only logistic

The primary candidate keeps the fold-trained logistic probability but takes the
maximum with a fixed VIX stress score and flags VIX above 30 as an override. The
rule is fixed before every fold and uses contemporaneously observable market
data. On the provisional revised-FRED run it raises recall from 0.355 to 0.645,
PR-AUC from 0.515 to 0.686 and reduces Brier from 0.115 to 0.095, at the cost of
0.94 false alerts per year versus 0.18.

## ADR-022 — Company histories calibrate risk; organizations are the data boundary

Company inputs may carry annual EBITDA histories. Four observations calibrate
single-name volatility; five aligned observations per company calibrate a
shrunk PSD correlation matrix. Explicit user assumptions still take priority,
and aggregate/structural values remain a named fallback. Every run publishes
`risk_calibration.json` with the selected sources.

API keys now belong to organizations. All portfolio, analysis, report, trace and
artifact reads and writes are scoped to the authenticated organization. The
default organization exists only for backward-compatible local/demo operation;
billing is a separate concern.

## Parking lot

- Citation locator granularity (PRD Q1) — decide in Phase 3.
- LLM model choice for prod vs evals (PRD Q3) — decide in Phase 3.
- Demo data for public deploy (PRD Q4) — decide in Phase 4.
- Snapshot retention policy (PRD Q5) — post-v1.
- Regenerate and publish the validation report from ALFRED after configuring the
  server-side FRED API key.
- Evaluate daily-frequency market features for sub-month detection lag.
- Add billing and metering only after organization-level usage contracts exist.
