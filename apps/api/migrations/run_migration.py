import httpx
import pathlib
import sys

SUPABASE_URL = "https://uoeyetxlotzwktorqnks.supabase.co"
SERVICE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InVvZXlldHhsb3R6d2t0b3JxbmtzIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc4MDY3OTY0NiwiZXhwIjoyMDk2MjU1NjQ2fQ.WzpNJ84XqWJPKXmbf04lYqveA3yyDg-mTXPcM4HWQn0"

sql = pathlib.Path(__file__).parent.joinpath("001_initial_schema.sql").read_text()

headers = {
    "apikey": SERVICE_KEY,
    "Authorization": f"Bearer {SERVICE_KEY}",
    "Content-Type": "application/json",
}

# Supabase exposes a SQL execution endpoint via the pg_dump API
resp = httpx.post(
    f"{SUPABASE_URL}/rest/v1/rpc/exec_sql",
    headers=headers,
    json={"query": sql},
    timeout=30,
)

if resp.status_code == 404:
    # exec_sql not available — use the management API approach
    print("exec_sql not found, trying query endpoint...")
    resp = httpx.post(
        f"{SUPABASE_URL}/pg/query",
        headers=headers,
        json={"query": sql},
        timeout=30,
    )

print(f"Status: {resp.status_code}")
print(resp.text[:500])
