# AtlasOS

**Market intelligence & competitive cartography system.**
Part of the [Montclair Intelligence Company](https://github.com/DerMayer1) suite.

> Input a B2B company → get a structured competitive map, positioning analysis, and strategic memo in under 60 seconds.

---

## Architecture

```
atlasos/
├── apps/
│   ├── web/        # Next.js 16 (App Router) — frontend
│   └── api/        # FastAPI — pipeline + REST API
├── packages/
│   └── types/      # Shared TypeScript types
```

### Pipeline (8 stages)

```
CompanyInput
  → [1] Website Extractor      (httpx + BeautifulSoup)
  → [2] Category Classifier    (GPT-4o structured output)
  → [3] Competitor Searcher    (Tavily API)
  → [4] Competitor Classifier  (GPT-4o 5-type classification)
  → [5] Positioning Analyzer   (GPT-4o → 2x2 matrix)
  → [6] Gap Detector           (GPT-4o → market gaps)
  → [7] Recommendation Engine  (GPT-4o → strategic moves)
  → [8] Memo Composer          (GPT-4o → Market Memo)
  → MarketMap + Market Memo (Markdown / PDF)
```

### Stack

| Layer | Technology |
|-------|-----------|
| Frontend | Next.js 16, Tailwind CSS, shadcn/ui |
| Backend | FastAPI, Python 3.12 |
| LLM | OpenAI GPT-4o (structured outputs) |
| Search | Tavily API |
| Database | Supabase (PostgreSQL) |
| Auth | Supabase Auth (magic link) |
| Queue | Redis |
| Export | WeasyPrint (PDF) |
| Infra | Vercel (web) + Railway (API) |

---

## Getting started

### Prerequisites
- Node.js 22+, pnpm 11+
- Python 3.12+
- Redis running locally

### 1. Install dependencies

```bash
pnpm install
cd apps/api && python -m venv .venv && .venv/Scripts/activate && pip install -e ".[dev]"
```

### 2. Configure environment

```bash
cp .env.example .env
# Fill in: OPENAI_API_KEY, TAVILY_API_KEY, SUPABASE_URL, SUPABASE_SERVICE_KEY
```

### 3. Run

```bash
# Terminal 1 — Frontend
pnpm dev

# Terminal 2 — API
cd apps/api && uvicorn app.main:app --reload --port 8000

# Terminal 3 — Worker
cd apps/api && python -m app.queue.worker
```

Frontend: http://localhost:3000
API docs: http://localhost:8000/docs

---

## Demo

Live demo: [atlasos.io/demo](https://atlasos.io/demo)

---

*Montclair Intelligence Company — AtlasOS v1*
