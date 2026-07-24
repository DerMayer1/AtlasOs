# Deploying AtlasOS to Render

AtlasOS ships as a single container that serves the API **and** the built React
UI, with the Arq worker running alongside it. On Render that maps to one web
service plus managed Postgres and Key Value (Redis), described by
[`render.yaml`](../render.yaml).

## Why one service

A Render persistent disk attaches to exactly one service, and both halves of the
app need the same `/data` volume — the worker **writes** snapshots and artifacts,
the API **reads** them to serve downloads, reports and citation validation. So
the API (uvicorn) and the worker (arq) run as two processes inside one web
service, supervised by [`scripts/render_start.py`](../scripts/render_start.py).
Jobs still flow through Redis and execute in the worker process, so a heavy
analysis never blocks request handling.

Splitting the worker into its own service later means moving artifact/snapshot
storage off the local disk to object storage — see [Scaling](#scaling).

## Prerequisites

- A Render account with this repository connected.
- A **FRED API key** (free): https://fred.stlouisfed.org/docs/api/api_key.html —
  required to ingest real macro data.
- Optionally an **OpenAI API key**. Without one the agent still works, degraded
  to deterministic planning and fully-cited numbers-only narration.

## Deploy

1. **Create the Blueprint.** In Render: **New → Blueprint**, pick this repo, and
   apply. It provisions `atlas-postgres`, `atlas-redis`, and the `atlas` web
   service. Adjust plan slugs in `render.yaml` if your account/region rejects
   them.
2. **Set secrets** on the `atlas` service (marked `sync: false`, never committed):
   - `ATLAS_FRED_API_KEY` — required.
   - `ATLAS_OPENAI_API_KEY` — optional.
3. **First deploy runs migrations automatically** (`alembic upgrade head` inside
   the start script), then boots the worker and API.
4. **Seed a snapshot.** Analyses never run on live data — they run on a frozen,
   hash-identified snapshot. Open the service **Shell** and ingest one:
   ```
   python -m atlas.interfaces.cli ingest
   ```
   It prints the `snapshot_id` and period. Until this runs, analyses return
   `409 no snapshot available`.
5. **Create an org and an API key:**
   ```
   python -m atlas.interfaces.cli create-org --name "Investment Team" --slug investment-team
   python -m atlas.interfaces.cli create-key --org-id org_... --name production --scopes read,run
   ```
   The plaintext key is shown once — copy it now.
6. **Sign in.** Open the service URL, expand the **Connection** panel, paste the
   API key, and **Sign in**. The key is exchanged once for an HttpOnly,
   Secure, `SameSite=Strict` session cookie; it is never stored in the browser.
   Programmatic clients use the same key as an `X-API-Key` header.

## Verify

```
curl https://<service>.onrender.com/health           # {"status":"ok"} — cheap, DB + queue only
curl 'https://<service>.onrender.com/health?deep=true'  # also probes FRED

# authenticated smoke test
curl -H "X-API-Key: atlas_..." https://<service>.onrender.com/portfolios
```

Then in the UI: sign in, confirm the overview loads, and run one analysis.

## Configuration

All settings are `ATLAS_*` env vars (see [`.env.example`](../.env.example)). The
blueprint sets the production-relevant ones:

| Variable | Value | Why |
| --- | --- | --- |
| `ATLAS_DATABASE_URL` | from Postgres | Bare `postgresql://` DSNs are auto-normalized to the psycopg3 driver. |
| `ATLAS_REDIS_URL` | from Key Value | Arq queue + worker. |
| `ATLAS_DATA_DIR` | `/data` | The persistent disk. Source of truth for snapshots + artifacts. |
| `ATLAS_TRUSTED_PROXY_COUNT` | `1` | Render terminates TLS at one proxy; the real client IP is the rightmost `X-Forwarded-For` entry. |
| `ATLAS_SESSION_COOKIE_SECURE` | `true` (default) | Session cookie is HTTPS-only. |
| `ATLAS_AUTO_CREATE_SCHEMA` | `false` | Schema is Alembic-managed, not `create_all`. |

## Operational notes

- **Single instance.** A disk-backed Render service runs one instance without
  zero-downtime deploys — expected for this filesystem-backed design.
- **Backups.** Enable Render's Postgres backups. The `/data` disk holds every
  snapshot and artifact; enable disk backups too, since losing it breaks
  reproducibility and citation resolution for past runs.
- **Key Value eviction** is set to `noeviction` so the queue never silently
  drops jobs under memory pressure.

## Scaling

The single-instance, shared-disk design is the deliberate first step. To scale
horizontally or split the worker into its own Render service, move the two
filesystem stores to S3-compatible object storage — `SnapshotStore` and
`ArtifactStore` (`src/atlas/platform/audit/`) are the seams to reimplement. That
removes the shared-disk constraint and lets the API and worker scale
independently.
