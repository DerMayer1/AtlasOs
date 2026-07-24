"""End-to-end API tests (PRD R3) over SQLite + in-process queue.

The API contract is identical in production (ARQ/Redis) mode: POST returns a
job_id, GET /analyses/{id} is polled for the outcome.
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import event

from atlas.domain.data.synthetic import make_macro_frame
from atlas.interfaces.api import app as app_module
from atlas.interfaces.api.app import create_app
from atlas.interfaces.api.auth import create_api_key
from atlas.platform.db.models import SnapshotRow
from atlas.platform.runtime.settings import Settings


@pytest.fixture
def client_and_keys(tmp_path):
    settings = Settings(
        database_url=f"sqlite:///{tmp_path / 'atlas.db'}",
        redis_url="",
        data_dir=tmp_path / "data",
        auto_create_schema=True,
    )
    app = create_app(settings)
    container = app.state.container

    manifest = container.snapshots.create({"macro": make_macro_frame()}, sources=["test"])
    with container.session_factory() as session:
        session.add(
            SnapshotRow(snapshot_id=manifest.snapshot_id, manifest=manifest.model_dump(mode="json"))
        )
        session.commit()
        _, run_token = create_api_key(session, "test-run", ["read", "run"])
        _, read_token = create_api_key(session, "test-read", ["read"])

    return TestClient(app), run_token, read_token, manifest.snapshot_id


PORTFOLIO = {
    "name": "Test PF",
    "companies": [
        {"name": "Alpha", "ebitda": 100.0, "multiple": 8.0, "carrying_value": 750.0},
    ],
}


def test_full_flow_portfolio_to_result(client_and_keys):
    client, run_token, _, snapshot_id = client_and_keys
    headers = {"X-API-Key": run_token}

    pf = client.post("/portfolios", json=PORTFOLIO, headers=headers)
    assert pf.status_code == 201

    job = client.post(
        "/analyses",
        json={"engine": "impairment", "portfolio_id": pf.json()["portfolio_id"]},
        headers=headers,
    )
    assert job.status_code == 202
    job_id = job.json()["job_id"]

    status = client.get(f"/analyses/{job_id}", headers=headers).json()
    assert status["status"] == "succeeded"
    assert status["snapshot_id"] == snapshot_id
    assert status["portfolio_id"] == pf.json()["portfolio_id"]
    assert status["portfolio_version_id"] == pf.json()["current_version_id"]
    assert 0.0 <= status["result"]["metrics"]["portfolio_mean_p_impairment"] <= 1.0

    # every artifact is downloadable
    for artifact in status["result"]["artifacts"]:
        resp = client.get(f"/artifacts/{job_id}/{artifact['name']}", headers=headers)
        assert resp.status_code == 200
        assert len(resp.content) == artifact["size_bytes"]


def test_organization_keys_isolate_portfolios_analyses_and_artifacts(client_and_keys):
    client, default_token, _, _ = client_and_keys
    with client.app.state.container.session_factory() as session:
        _, second_token = create_api_key(
            session,
            "second-tenant",
            ["read", "run"],
            org_id="org_second",
        )
    default_headers = {"X-API-Key": default_token}
    second_headers = {"X-API-Key": second_token}

    first = client.post("/portfolios", json=PORTFOLIO, headers=default_headers).json()
    second_body = {**PORTFOLIO, "name": "Second tenant PF"}
    second = client.post("/portfolios", json=second_body, headers=second_headers).json()

    assert [
        row["portfolio_id"]
        for row in client.get("/portfolios", headers=default_headers).json()["portfolios"]
    ] == [first["portfolio_id"]]
    assert [
        row["portfolio_id"]
        for row in client.get("/portfolios", headers=second_headers).json()["portfolios"]
    ] == [second["portfolio_id"]]
    assert (
        client.get(f"/portfolios/{first['portfolio_id']}", headers=second_headers).status_code
        == 404
    )

    job = client.post(
        "/analyses",
        json={"engine": "impairment", "portfolio_id": first["portfolio_id"]},
        headers=default_headers,
    ).json()["job_id"]
    result = client.get(f"/analyses/{job}", headers=default_headers).json()["result"]
    artifact_name = result["artifacts"][0]["name"]
    assert client.get(f"/analyses/{job}", headers=second_headers).status_code == 404
    assert (
        client.get(f"/artifacts/{job}/{artifact_name}", headers=second_headers).status_code == 404
    )


def test_company_history_is_versioned_with_the_portfolio(client_and_keys):
    client, run_token, _, _ = client_and_keys
    body = {
        "name": "Calibrated PF",
        "companies": [
            {
                "name": "History Co",
                "ebitda": 120.0,
                "multiple": 8.0,
                "carrying_value": 800.0,
                "ebitda_history": [
                    {"year": 2021, "value": 85.0},
                    {"year": 2022, "value": 93.0},
                    {"year": 2023, "value": 104.0},
                    {"year": 2024, "value": 120.0},
                ],
            }
        ],
    }
    response = client.post("/portfolios", json=body, headers={"X-API-Key": run_token})

    assert response.status_code == 201
    assert (
        response.json()["companies"][0]["ebitda_history"] == body["companies"][0]["ebitda_history"]
    )


def test_portfolio_version_is_inserted_before_company_inputs(client_and_keys):
    client, run_token, _, _ = client_and_keys
    statements: list[str] = []
    engine = client.app.state.container.engine

    def record_statement(_conn, _cursor, statement, _parameters, _context, _executemany):
        statements.append(statement)

    event.listen(engine, "before_cursor_execute", record_statement)
    try:
        response = client.post(
            "/portfolios",
            json=PORTFOLIO,
            headers={"X-API-Key": run_token},
        )
    finally:
        event.remove(engine, "before_cursor_execute", record_statement)

    assert response.status_code == 201
    version_insert = next(
        index
        for index, statement in enumerate(statements)
        if "INSERT INTO portfolio_versions" in statement
    )
    company_insert = next(
        index
        for index, statement in enumerate(statements)
        if "INSERT INTO portfolio_company_inputs" in statement
    )
    assert version_insert < company_insert


def test_portfolio_versions_are_immutable_and_deduplicated(client_and_keys):
    client, run_token, _, _ = client_and_keys
    headers = {"X-API-Key": run_token}

    created = client.post("/portfolios", json=PORTFOLIO, headers=headers)
    assert created.status_code == 201
    portfolio = created.json()
    assert portfolio["version_number"] == 1
    assert portfolio["changed"] is True

    unchanged = client.put(
        f"/portfolios/{portfolio['portfolio_id']}",
        json=PORTFOLIO,
        headers=headers,
    )
    assert unchanged.status_code == 200
    assert unchanged.json()["changed"] is False
    assert unchanged.json()["current_version_id"] == portfolio["current_version_id"]

    updated_payload = {
        **PORTFOLIO,
        "companies": [{**PORTFOLIO["companies"][0], "ebitda": 85.0}],
    }
    updated = client.put(
        f"/portfolios/{portfolio['portfolio_id']}",
        json=updated_payload,
        headers=headers,
    )
    assert updated.status_code == 200
    assert updated.json()["changed"] is True
    assert updated.json()["version_number"] == 2
    assert updated.json()["current_version_id"] != portfolio["current_version_id"]

    versions = client.get(
        f"/portfolios/{portfolio['portfolio_id']}/versions",
        headers=headers,
    )
    assert versions.status_code == 200
    version_rows = versions.json()["versions"]
    assert [row["version_number"] for row in version_rows] == [2, 1]
    assert version_rows[0]["is_current"] is True
    assert version_rows[1]["is_current"] is False

    job = client.post(
        "/analyses",
        json={
            "engine": "impairment",
            "portfolio_id": portfolio["portfolio_id"],
            "params": {
                "n_sims": 100,
                "seed": 11,
                "companies": PORTFOLIO["companies"] * 2,
            },
        },
        headers=headers,
    )
    analysis = client.get(
        f"/analyses/{job.json()['job_id']}",
        headers=headers,
    ).json()
    assert analysis["portfolio_version_id"] == updated.json()["current_version_id"]
    assert analysis["result"]["metrics"]["n_companies"] == 1


def test_portfolios_can_be_listed_with_current_version(client_and_keys):
    client, run_token, read_token, _ = client_and_keys
    created = client.post(
        "/portfolios",
        json=PORTFOLIO,
        headers={"X-API-Key": run_token},
    ).json()

    response = client.get(
        "/portfolios",
        headers={"X-API-Key": read_token},
    )
    assert response.status_code == 200
    portfolios = response.json()["portfolios"]
    assert portfolios[0]["portfolio_id"] == created["portfolio_id"]
    assert portfolios[0]["version_number"] == 1
    assert portfolios[0]["company_count"] == 1


def test_auth_required_and_scoped(client_and_keys):
    client, run_token, read_token, _ = client_and_keys

    assert client.post("/portfolios", json=PORTFOLIO).status_code == 401
    assert (
        client.post("/portfolios", json=PORTFOLIO, headers={"X-API-Key": "bogus"}).status_code
        == 401
    )
    # read-scoped key cannot run
    assert (
        client.post("/portfolios", json=PORTFOLIO, headers={"X-API-Key": read_token}).status_code
        == 403
    )
    # but can read
    pf = client.post("/portfolios", json=PORTFOLIO, headers={"X-API-Key": run_token}).json()
    got = client.get(f"/portfolios/{pf['portfolio_id']}", headers={"X-API-Key": read_token})
    assert got.status_code == 200


def test_unknown_engine_rejected_with_capabilities(client_and_keys):
    client, run_token, _, _ = client_and_keys
    resp = client.post(
        "/analyses",
        json={"engine": "does_not_exist", "params": {"companies": PORTFOLIO["companies"]}},
        headers={"X-API-Key": run_token},
    )
    assert resp.status_code == 422
    assert "impairment" in resp.json()["detail"]
    assert "macro_monitor" in resp.json()["detail"]


def test_macro_monitor_runs_without_portfolio(client_and_keys):
    client, run_token, _, snapshot_id = client_and_keys
    job = client.post(
        "/analyses",
        json={"engine": "macro_monitor", "snapshot_id": snapshot_id},
        headers={"X-API-Key": run_token},
    )
    assert job.status_code == 202
    status = client.get(
        f"/analyses/{job.json()['job_id']}",
        headers={"X-API-Key": run_token},
    ).json()
    assert status["status"] == "succeeded"
    assert status["result"]["engine"] == "macro_monitor"
    assert 0.0 <= status["result"]["metrics"]["stress_breadth"] <= 1.0

    history = client.get(
        "/analyses",
        headers={"X-API-Key": run_token},
    ).json()["analyses"]
    macro_run = next(item for item in history if item["job_id"] == job.json()["job_id"])
    assert macro_run["macro_regime"] in {"expansion", "tightening", "crisis"}
    assert macro_run["stress_index"] is not None


def test_unknown_snapshot_rejected(client_and_keys):
    client, run_token, _, _ = client_and_keys
    resp = client.post(
        "/analyses",
        json={
            "engine": "impairment",
            "snapshot_id": "snap_nope",
            "params": {"companies": PORTFOLIO["companies"]},
        },
        headers={"X-API-Key": run_token},
    )
    assert resp.status_code == 404


def test_failed_analysis_persists_error(client_and_keys):
    client, run_token, _, _ = client_and_keys
    # params without companies and no portfolio -> engine validation fails
    job = client.post("/analyses", json={"engine": "impairment"}, headers={"X-API-Key": run_token})
    assert job.status_code == 202
    status = client.get(f"/analyses/{job.json()['job_id']}", headers={"X-API-Key": run_token})
    body = status.json()
    assert body["status"] == "failed"
    assert body["error"]
    assert body["attempts"] == 1


def test_agent_ask_refuses_out_of_scope(client_and_keys):
    # No OpenAI key in tests -> deterministic planner; FX is out of scope.
    client, run_token, _, _ = client_and_keys
    resp = client.post(
        "/agent/ask",
        json={"question": "what is your EUR/USD forecast?"},
        headers={"X-API-Key": run_token},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["plan"]["refusal_reason"] is not None
    assert body["executed"] == []
    assert "impairment" in body["capabilities"]


def test_agent_ask_runs_engine_and_persists_trace(client_and_keys):
    client, run_token, _, _ = client_and_keys
    pf = client.post("/portfolios", json=PORTFOLIO, headers={"X-API-Key": run_token}).json()
    resp = client.post(
        "/agent/ask",
        json={"question": "what is the impairment risk?", "portfolio_id": pf["portfolio_id"]},
        headers={"X-API-Key": run_token},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["executed"][0]["status"] == "succeeded"
    # no LLM in tests -> degraded numbers-only, but still a valid cited narrative
    assert body["degraded"] is True
    assert body["citations"]["orphan_claims"] == []
    assert body["narrative"]

    trace = client.get(f"/agent/traces/{body['trace_id']}", headers={"X-API-Key": run_token})
    assert trace.status_code == 200
    assert trace.json()["citations_valid"] is True


def test_health_unauthenticated(client_and_keys):
    client, *_ = client_and_keys
    resp = client.get("/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert body["checks"]["database"] == "ok"
    assert body["checks"]["queue"] == "in-process"


def test_rate_limit_returns_429(tmp_path):
    settings = Settings(
        database_url=f"sqlite:///{tmp_path / 'rate-limit.db'}",
        redis_url="",
        data_dir=tmp_path / "data",
        auto_create_schema=True,
        # Keep refill negligible during the test so slow Windows CI hosts do
        # not replenish a token between the second and third request.
        rate_limit_requests_per_minute=1,
        rate_limit_burst=2,
    )
    client = TestClient(create_app(settings))

    assert client.get("/health").status_code == 200
    assert client.get("/health").status_code == 200
    limited = client.get("/health")

    assert limited.status_code == 429
    assert limited.json()["detail"] == "rate limit exceeded"
    assert limited.headers["retry-after"]


def test_request_body_limit_returns_413(tmp_path):
    settings = Settings(
        database_url=f"sqlite:///{tmp_path / 'body-limit.db'}",
        redis_url="",
        data_dir=tmp_path / "data",
        auto_create_schema=True,
        rate_limit_enabled=False,
        max_request_body_bytes=10,
    )
    client = TestClient(create_app(settings))

    response = client.post(
        "/agent/ask",
        content=b'{"question":"this body is intentionally too large"}',
        headers={"Content-Type": "application/json", "X-API-Key": "atlas_test"},
    )

    assert response.status_code == 413
    assert response.json()["detail"] == "request body too large"


def test_spoofed_forwarded_for_cannot_bypass_rate_limit(tmp_path):
    # Direct exposure (trusted_proxy_count=0): a client that rotates
    # X-Forwarded-For must not mint a fresh bucket per request.
    settings = Settings(
        database_url=f"sqlite:///{tmp_path / 'xff.db'}",
        redis_url="",
        data_dir=tmp_path / "data",
        auto_create_schema=True,
        rate_limit_requests_per_minute=1,
        rate_limit_burst=2,
    )
    client = TestClient(create_app(settings))

    codes = [
        client.get("/health", headers={"X-Forwarded-For": f"203.0.113.{i}"}).status_code
        for i in range(4)
    ]
    assert 429 in codes  # the spoofed header did not grant unlimited identities


def test_trusted_proxy_reads_client_ip_from_right_of_forwarded_for(tmp_path):
    # Behind one trusted proxy, distinct real clients get distinct buckets, and
    # a spoofed left-hand entry does not change the trusted right-hand IP.
    settings = Settings(
        database_url=f"sqlite:///{tmp_path / 'proxy.db'}",
        redis_url="",
        data_dir=tmp_path / "data",
        auto_create_schema=True,
        rate_limit_requests_per_minute=1,
        rate_limit_burst=2,
        trusted_proxy_count=1,
    )
    client = TestClient(create_app(settings))

    # Two requests from real client A (rightmost entry), then a third: limited.
    a = [
        client.get("/health", headers={"X-Forwarded-For": f"{spoof}, 198.51.100.7"}).status_code
        for spoof in ("evil-1", "evil-2", "evil-3")
    ]
    # A different real client B is unaffected by A's exhaustion.
    b = client.get("/health", headers={"X-Forwarded-For": "198.51.100.8"}).status_code

    assert a[0] == 200 and a[1] == 200 and a[2] == 429  # spoofed left entry ignored
    assert b == 200


def test_rate_limit_identity_table_is_bounded(tmp_path):
    from atlas.interfaces.api.security import RateLimitMiddleware, _Bucket

    middleware = RateLimitMiddleware(
        app=lambda *args: None,
        requests_per_minute=600,
        burst=5,
        trusted_proxy_count=1,
        max_tracked_identities=50,
    )
    import time

    now = time.monotonic()
    with middleware._lock:
        for i in range(500):
            if len(middleware._buckets) >= middleware.max_tracked_identities:
                middleware._evict_locked(now)
            middleware._buckets[f"ip:10.0.{i}"] = _Bucket(tokens=5.0, updated_at=now)

    assert len(middleware._buckets) <= 50  # a unique-identity flood cannot grow it without bound


def test_chunked_body_over_limit_is_rejected(tmp_path):
    # No Content-Length: httpx streams a generator as chunked transfer-encoding,
    # which the old Content-Length-only guard let straight through.
    settings = Settings(
        database_url=f"sqlite:///{tmp_path / 'chunked.db'}",
        redis_url="",
        data_dir=tmp_path / "data",
        auto_create_schema=True,
        rate_limit_enabled=False,
        max_request_body_bytes=32,
    )
    client = TestClient(create_app(settings))

    def oversized_stream():
        yield b'{"question":"' + b"x" * 200 + b'"}'

    response = client.post(
        "/agent/ask",
        content=oversized_stream(),
        headers={"Content-Type": "application/json", "X-API-Key": "atlas_test"},
    )
    assert response.status_code == 413
    assert response.json()["detail"] == "request body too large"


def test_legacy_frontend_and_static_assets_are_served(client_and_keys):
    client, *_ = client_and_keys
    page = client.get("/legacy")
    assert page.status_code == 200
    assert "Impairment analysis" in page.text
    assert "Macro Monitor" in page.text
    assert "Portfolio library" in page.text

    stylesheet = client.get("/static/styles.css")
    script = client.get("/static/app.js")
    assert stylesheet.status_code == 200
    assert script.status_code == 200
    assert "runAnalysis" in script.text
    assert "runMacroMonitor" in script.text
    assert "renderMacroRegimeChart" in script.text
    assert "persistPortfolio" in script.text
    assert 'sessionStorage.setItem("atlas_api_key"' not in script.text
    assert 'sessionStorage.removeItem("atlas_api_key")' in script.text
    assert "bootstrap.api_key" not in script.text
    assert 'credentials: "same-origin"' in script.text


def test_react_frontend_is_the_official_root(tmp_path, monkeypatch):
    spa_dir = tmp_path / "spa"
    assets_dir = spa_dir / "assets"
    assets_dir.mkdir(parents=True)
    (spa_dir / "index.html").write_text(
        "<!doctype html><title>Atlas React</title>"
        '<script type="module" src="/assets/app.js"></script>',
        encoding="utf-8",
    )
    (assets_dir / "app.js").write_text(
        "window.__atlasReact = true;",
        encoding="utf-8",
    )
    monkeypatch.setattr(app_module, "SPA_DIR", spa_dir)

    settings = Settings(
        database_url=f"sqlite:///{tmp_path / 'react-ui.db'}",
        redis_url="",
        data_dir=tmp_path / "data",
        auto_create_schema=True,
        rate_limit_enabled=False,
    )
    client = TestClient(app_module.create_app(settings))

    root = client.get("/")
    assert root.status_code == 200
    assert root.headers["x-atlas-frontend"] == "react"
    assert "Atlas React" in root.text

    asset = client.get("/assets/app.js")
    assert asset.status_code == 200
    assert "__atlasReact" in asset.text

    legacy = client.get("/legacy")
    assert legacy.status_code == 200
    assert "Impairment analysis" in legacy.text

    previous_path = client.get("/app/overview", follow_redirects=False)
    assert previous_path.status_code == 308
    assert previous_path.headers["location"] == "/"


def test_demo_bootstrap_is_disabled_by_default(client_and_keys):
    client, *_ = client_and_keys
    response = client.post("/demo/bootstrap")
    assert response.status_code == 404


def test_local_demo_bootstraps_and_lists_persisted_analysis(tmp_path):
    settings = Settings(
        database_url=f"sqlite:///{tmp_path / 'demo.db'}",
        redis_url="",
        data_dir=tmp_path / "data",
        auto_create_schema=True,
        demo_mode=True,
    )
    client = TestClient(create_app(settings))

    bootstrap = client.post("/demo/bootstrap")
    assert bootstrap.status_code == 200
    body = bootstrap.json()
    assert body["mode"] == "local-demo"
    assert body["authentication"] == "http-only-cookie"
    assert "api_key" not in body
    assert body["snapshot_id"].startswith("snap_")
    assert "impairment" in body["capabilities"]
    assert "atlas_api_key=" in bootstrap.headers["set-cookie"]
    assert "HttpOnly" in bootstrap.headers["set-cookie"]
    assert "SameSite=strict" in bootstrap.headers["set-cookie"]

    # TestClient retains the HttpOnly cookie just like a same-origin browser.
    portfolio = client.post("/portfolios", json=PORTFOLIO)
    assert portfolio.status_code == 201

    job = client.post(
        "/analyses",
        json={
            "engine": "impairment",
            "portfolio_id": portfolio.json()["portfolio_id"],
            "params": {"n_sims": 100, "seed": 7},
        },
    )
    assert job.status_code == 202

    history = client.get("/analyses")
    assert history.status_code == 200
    recent = history.json()["analyses"]
    assert recent[0]["job_id"] == job.json()["job_id"]
    assert recent[0]["portfolio_name"] == PORTFOLIO["name"]
    assert recent[0]["status"] == "succeeded"
    assert 0.0 <= recent[0]["portfolio_mean_p_impairment"] <= 1.0
