# Atlas — Macro-Financial Monitoring Platform

> Every number is reproducible; every claim cites its number; every decision
> leaves a trace.

Pluggable quantitative engines produce numbers; a governed orchestrating agent
produces theses citing those numbers; every decision is traceable to the datum
that originated it. Full product spec: see the PRD (v1.0, June 2026).

## Architecture at a glance

```
src/atlas/
├── platform/            # domain-agnostic: never imports domain (CI-enforced)
│   ├── contracts/       # AnalysisWorker + pydantic schemas (the central contract)
│   ├── audit/           # immutable snapshots (parquet + sha256 manifest), artifacts
│   ├── db/              # SQLAlchemy models (Postgres = source of truth)
│   └── runtime/         # registry, queue (ARQ/in-process), runner, settings
├── domain/
│   ├── data/            # FRED ingestion (cached, incremental) + synthetic demo
│   ├── engines/
│   │   └── impairment/  # Engine 1: Monte Carlo + HMM regime model
│   └── validation/      # reference labels + metrics for the validation report
├── agent/               # orchestrator (question→plan), narrator (results→thesis),
│   │                    # citation validator, trace store, evals/
│   └── evals/           # ≥15 scripted-LLM cases; CI gate
└── interfaces/
    ├── api/             # FastAPI app, API-key auth (read/run scopes)
    ├── worker.py        # ARQ worker (3 retries, exponential backoff)
    └── cli.py           # init-db, seed, ingest
scripts/                 # validation_report.py (make validation-report)
docs/                    # DECISIONS.md (ADRs), limitations.md, validation_report.md, agent_evals.md
migrations/              # Alembic
tests/                   # unit, property-based, API e2e, agent, citations, evals
```

Non-negotiable principles (PRD §7.1):

1. Dependency direction: `domain → platform`, never the reverse.
2. The LLM never calculates — all math lives in deterministic engines.
3. Nothing runs on live data — only on identified, hash-verified snapshots.
4. Every decision leaves a trace.
5. Graceful degradation — narration failure never blocks numbers.

## Quickstart (local, no Docker)

```powershell
py -3.12 -m venv .venv
.venv\Scripts\pip install -e .[dev]
.venv\Scripts\pytest                            # full suite
.venv\Scripts\python -m atlas.interfaces.cli seed   # demo snapshot + portfolio + API key
.venv\Scripts\uvicorn atlas.interfaces.api.app:create_app --factory
```

Then (replace the key/ids printed by `seed`):

```powershell
$h = @{ "X-API-Key" = "<api_key>" }
Invoke-RestMethod -Method Post http://127.0.0.1:8000/analyses -Headers $h `
  -ContentType application/json -Body '{"engine":"impairment","portfolio_id":"<pf_id>"}'
Invoke-RestMethod http://127.0.0.1:8000/analyses/<job_id> -Headers $h
```

## Full system (Postgres + Redis + worker)

```bash
docker compose up --build
docker compose run --rm api python -m atlas.interfaces.cli seed
```

API at http://localhost:8000 (OpenAPI docs at `/docs`). Endpoints: `POST /portfolios`,
`POST /analyses` (returns `job_id`), `GET /analyses/{id}`, `POST /agent/ask`,
`GET /agent/traces/{id}`, `GET /artifacts/{run_id}/{name}`, `GET /health`. Auth
via `X-API-Key` with `read`/`run` scopes.

## Real macro data + validation (Phase 2)

```powershell
.venv\Scripts\python -m atlas.interfaces.cli ingest   # FRED → frozen snapshot
make calibrate-shocks                                 # fit per-regime EBITDA shocks from corporate profits
make validation-report                                # regenerate docs/validation_report.md + figures
```

Ingestion pulls five macro series from FRED's keyless `fredgraph` endpoint
(cached, incremental), freezes them as a hash-verified snapshot, and indexes it
in Postgres. The regime model is a 3-state Gaussian HMM (`regime_model="hmm"`,
the default, with a credit-spread *change* feature); the Phase 0 z-score
classifier remains available as `regime_model="zscore"` and is the baseline in
the validation report. The per-regime stress shocks are calibrated from
corporate-profit history (`make calibrate-shocks` → `shock_calibration.json`).
The report itself ([docs/validation_report.md](docs/validation_report.md)) is
regenerated from a frozen snapshot — same snapshot, same numbers — and publishes
the model's results honestly, including where naive benchmarks beat it and the
finding that the crisis-precision ceiling is structural (§4b).

## The agent: every claim cites its number (Phase 3)

`POST /agent/ask` turns an institutional question into a typed plan of engine
calls (orchestrator), runs the real deterministic engines, and narrates the
structured results into a thesis where **every figure is followed by a
`[artifact_id:locator]` citation** — validated against the artifacts before the
answer is returned. An uncited or wrong number gets the narrative regenerated
once, then degraded to a numbers-only summary. Out-of-scope questions are
refused honestly with the real capability list. The whole decision (plan, tool
calls, tokens, cost, latency, prompt version) is persisted as a queryable trace
(`GET /agent/traces/{id}`).

```powershell
$h = @{ "X-API-Key" = "<api_key>" }
Invoke-RestMethod -Method Post http://127.0.0.1:8000/agent/ask -Headers $h `
  -ContentType application/json `
  -Body '{"question":"What is the impairment risk in a 2022-style scenario?","portfolio_id":"<pf_id>"}'
```

The LLM is optional: with no `ATLAS_ANTHROPIC_API_KEY` the orchestrator uses a
deterministic planner and the narrator a fully-cited template (the PRD's
graceful-degradation path). The LLM never sees raw data — only the capability
catalog and a list of citable values. The eval suite
([docs/agent_evals.md](docs/agent_evals.md)) gates CI: 16 scripted-LLM cases,
regression fails the build.

## Roadmap (PRD §9)

| Phase | Content | Done when |
|---|---|---|
| **0 — Foundation** ✅ | Contracts, schemas, snapshot/artifact stores, registry, Engine 1 behind `AnalysisWorker`, tests, CI | Tests green; import-direction enforced |
| **1 — Living system** ✅ | FastAPI, Postgres + Alembic, ARQ/Redis queue, docker compose, API keys | `POST /analyses` → result via `GET` |
| **2 — Credibility** ✅ | FRED ingestion, real snapshots, HMM, validation report (2008/2020/2022) | "Detection lag in 2020?" answerable with a number |
| **3 — Differentiator** ✅ | Orchestrator, narrator with mandatory citations, trace store, eval suite in CI | Prompt change → CI catches regression |
| 4 — Public proof | React frontend (clickable citations), Engine 2 (macro monitor), scheduler + alerts, deploy | A stranger uses it unaided via the link |
