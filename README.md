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
│   └── runtime/         # engine registry (queue/scheduler arrive in Phase 1)
├── domain/
│   └── engines/
│       └── impairment/  # Engine 1: regime-conditional Monte Carlo
docs/                    # DECISIONS.md (ADRs), limitations.md
tests/                   # unit, property-based, import-direction lint
```

Non-negotiable principles (PRD §7.1):

1. Dependency direction: `domain → platform`, never the reverse.
2. The LLM never calculates — all math lives in deterministic engines.
3. Nothing runs on live data — only on identified, hash-verified snapshots.
4. Every decision leaves a trace.
5. Graceful degradation — narration failure never blocks numbers.

## Quickstart

```powershell
py -3.12 -m venv .venv
.venv\Scripts\pip install -e .[dev]
.venv\Scripts\pytest
.venv\Scripts\ruff check .
```

## Roadmap (PRD §9)

| Phase | Content | Done when |
|---|---|---|
| **0 — Foundation** ✅ | Contracts, schemas, snapshot/artifact stores, registry, Engine 1 behind `AnalysisWorker`, tests, CI | Tests green; import-direction enforced |
| 1 — Living system | FastAPI, Postgres + Alembic, ARQ/Redis queue, docker compose, API keys | `POST /analyses` → result via `GET` |
| 2 — Credibility | FRED ingestion, real snapshots, HMM, validation report (2008/2020/2022) | "Detection lag in 2020?" answerable with a number |
| 3 — Differentiator | Orchestrator, narrator with mandatory citations, trace store, eval suite in CI | Prompt change → CI catches regression |
| 4 — Public proof | React frontend (clickable citations), Engine 2 (macro monitor), scheduler + alerts, deploy | A stranger uses it unaided via the link |
