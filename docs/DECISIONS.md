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

## Parking lot

- Citation locator granularity (PRD Q1) — decide in Phase 3.
- LLM model choice for prod vs evals (PRD Q3) — decide in Phase 3.
- Demo data for public deploy (PRD Q4) — decide in Phase 4.
- Snapshot retention policy (PRD Q5) — post-v1.
