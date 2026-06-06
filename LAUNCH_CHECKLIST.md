# AtlasOS — V1 Launch Checklist

## P0 — Must pass before launch

- [ ] Full pipeline runs in < 60s (standard depth) — test on 5 real companies
- [ ] Pipeline completes for 9/10 test companies without fatal errors
- [ ] Memo is coherent and exportable as PDF — manual review (5 memos)
- [ ] Auth works end-to-end: sign up → magic link → session → dashboard
- [ ] Rate limit blocks excess requests (automated API test)
- [ ] No API keys exposed in frontend bundle (inspect Network tab)
- [ ] Demo page loads at /demo without authentication
- [ ] GitHub README has live demo link

## P1 — Launch week

- [ ] Deploy web to Vercel — production domain configured
- [ ] Deploy API to Railway — health check passing
- [ ] Redis running in production
- [ ] Supabase schema migrated on production project
- [ ] Environment variables set in Vercel + Railway dashboards
- [ ] Record demo walkthrough video (2–3 min)
- [ ] Post on LinkedIn + Wellfound

## Environment variables required

### Vercel (web)
- `NEXT_PUBLIC_SUPABASE_URL`
- `NEXT_PUBLIC_SUPABASE_ANON_KEY`
- `NEXT_PUBLIC_API_URL` — Railway API URL
- `API_URL` — same (server-side)

### Railway (api + worker)
- `OPENAI_API_KEY`
- `TAVILY_API_KEY`
- `SUPABASE_URL`
- `SUPABASE_SERVICE_KEY`
- `REDIS_URL`
- `LOG_LEVEL=info`
- `PIPELINE_TIMEOUT_S=90`

## Demo companies (pre-test these)

- [ ] Linear (https://linear.app) — reference case
- [ ] Notion (https://notion.so) — category ambiguity test
- [ ] Figma (https://figma.com) — crowded market test
