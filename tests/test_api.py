"""End-to-end API tests (PRD R3) over SQLite + in-process queue.

The API contract is identical in production (ARQ/Redis) mode: POST returns a
job_id, GET /analyses/{id} is polled for the outcome.
"""

import pytest
from fastapi.testclient import TestClient

from atlas.domain.data.synthetic import make_macro_frame
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
    assert 0.0 <= status["result"]["metrics"]["portfolio_mean_p_impairment"] <= 1.0

    # every artifact is downloadable
    for artifact in status["result"]["artifacts"]:
        resp = client.get(f"/artifacts/{job_id}/{artifact['name']}", headers=headers)
        assert resp.status_code == 200
        assert len(resp.content) == artifact["size_bytes"]


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
    job = client.post(
        "/analyses", json={"engine": "impairment"}, headers={"X-API-Key": run_token}
    )
    assert job.status_code == 202
    status = client.get(f"/analyses/{job.json()['job_id']}", headers={"X-API-Key": run_token})
    body = status.json()
    assert body["status"] == "failed"
    assert body["error"]
    assert body["attempts"] == 1


def test_agent_ask_is_honest_about_capabilities(client_and_keys):
    client, run_token, _, _ = client_and_keys
    resp = client.post(
        "/agent/ask", json={"question": "what is the FX risk?"}, headers={"X-API-Key": run_token}
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["answer"] is None
    assert "impairment" in body["capabilities"]


def test_health_unauthenticated(client_and_keys):
    client, *_ = client_and_keys
    resp = client.get("/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert body["checks"]["database"] == "ok"
    assert body["checks"]["queue"] == "in-process"
