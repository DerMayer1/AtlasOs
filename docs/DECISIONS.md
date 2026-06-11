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

## Parking lot

- Citation locator granularity (PRD Q1) — decide in Phase 3.
- LLM model choice for prod vs evals (PRD Q3) — decide in Phase 3.
- Demo data for public deploy (PRD Q4) — decide in Phase 4.
- Snapshot retention policy (PRD Q5) — post-v1.
- HMM calibration (PRD Q2, still open): spread *change* feature to cut the
  post-recession false-positive bias; daily-frequency detection for sub-month
  lag resolution; historical regression for the stress-shock coefficients.
