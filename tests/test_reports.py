"""Report builder (deterministic) + report/idempotency endpoints."""

import pytest
from fastapi.testclient import TestClient

from atlas.domain.data.synthetic import make_macro_frame
from atlas.domain.reports.builder import build_report
from atlas.interfaces.api.app import create_app
from atlas.interfaces.api.auth import create_api_key
from atlas.platform.db.models import SnapshotRow
from atlas.platform.runtime.settings import Settings

# --- builder unit tests (no IO) ----------------------------------------------


def test_impairment_report_flags_actions_and_cites_them():
    metrics = {
        "portfolio_mean_p_impairment": 0.22,
        "portfolio_expected_impairment_loss": 120.0,
        "portfolio_loss_p95": 400.0,
        "n_companies": 2.0,
        "crisis_1y_expected_loss_ratio": 0.31,
    }
    resilience = [
        {
            "company": "Alpha",
            "liquidity_gap_to_ebitda": 0.9,
            "interest_coverage": 1.2,
        },
        {
            "company": "Beta",
            "liquidity_gap_to_ebitda": 0.1,
            "interest_coverage": 8.0,
        },
    ]

    report = build_report(
        run_id="run_x",
        engine="impairment",
        snapshot_id="snap_1",
        engine_version="1.0.0",
        model_version="m1",
        metrics=metrics,
        resilience_rows=resilience,
    )

    codes = {a.code for a in report.actions}
    assert "valuation_review" in codes  # mean p 0.22 >= 0.15
    assert "stress_capital_review" in codes  # crisis ratio 0.31 >= 0.25
    assert "refinancing_review" in codes  # Alpha gap + coverage

    # exactly one refinancing action, for Alpha, citing its resilience rows
    refi = [a for a in report.actions if a.code == "refinancing_review"]
    assert len(refi) == 1 and "Alpha" in refi[0].title
    assert {cite.artifact for cite in refi[0].citations} == {"financial_resilience.csv"}

    # every action cites at least one artifact value
    assert all(a.citations for a in report.actions)


def test_impairment_report_quiet_when_healthy():
    metrics = {"portfolio_mean_p_impairment": 0.02, "n_companies": 1.0}
    report = build_report(
        run_id="r",
        engine="impairment",
        snapshot_id="s",
        engine_version="1.0.0",
        model_version="m",
        metrics=metrics,
        resilience_rows=[
            {"company": "A", "liquidity_gap_to_ebitda": 0.0, "interest_coverage": 10.0}
        ],
    )
    assert report.actions == []


def test_impairment_report_escalates_material_increase():
    metrics = {"portfolio_mean_p_impairment": 0.12, "n_companies": 1.0}
    previous = {"portfolio_mean_p_impairment": 0.05}
    report = build_report(
        run_id="r",
        engine="impairment",
        snapshot_id="s",
        engine_version="1.0.0",
        model_version="m",
        metrics=metrics,
        previous_metrics=previous,
        previous_run_id="run_prev",
    )
    assert any(a.code == "escalate_increase" for a in report.actions)
    assert report.previous_run_id == "run_prev"


def test_macro_report_actions_scale_with_stress():
    crisis = build_report(
        run_id="r",
        engine="macro_monitor",
        snapshot_id="s",
        engine_version="1.0.0",
        model_version="m",
        metrics={
            "p_regime_expansion": 0.1,
            "p_regime_tightening": 0.2,
            "p_regime_crisis": 0.7,
            "stress_index": 0.8,
            "p_next_regime_crisis": 0.5,
        },
    )
    codes = {a.code for a in crisis.actions}
    assert "macro_heightened_monitoring" in codes
    assert "macro_transition_watch" in codes
    assert any(a.severity == "critical" for a in crisis.actions)


# --- endpoint tests ----------------------------------------------------------


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
    return TestClient(app), run_token, manifest.snapshot_id


PORTFOLIO = {
    "name": "Report PF",
    "companies": [
        {
            "name": "Alpha",
            "ebitda": 100.0,
            "multiple": 8.0,
            "carrying_value": 750.0,
            "debt": 600.0,
            "cash": 10.0,
            "debt_due_1y": 200.0,
        }
    ],
}


def test_report_endpoint_round_trip(client_and_keys):
    client, run_token, _ = client_and_keys
    headers = {"X-API-Key": run_token}

    pf = client.post("/portfolios", json=PORTFOLIO, headers=headers)
    job = client.post(
        "/analyses",
        json={"engine": "impairment", "portfolio_id": pf.json()["portfolio_id"]},
        headers=headers,
    )
    analysis_id = job.json()["job_id"]
    assert client.get(f"/analyses/{analysis_id}", headers=headers).json()["status"] == "succeeded"

    # no report yet
    assert client.get(f"/analyses/{analysis_id}/report", headers=headers).status_code == 404

    created = client.post(f"/analyses/{analysis_id}/report", headers=headers)
    assert created.status_code == 201
    body = created.json()
    assert body["engine"] == "impairment"
    assert body["headline"]
    assert "report_id" in body

    fetched = client.get(f"/analyses/{analysis_id}/report", headers=headers)
    assert fetched.status_code == 200
    assert fetched.json()["report_id"] == body["report_id"]


def test_report_requires_succeeded_analysis(client_and_keys):
    client, run_token, snapshot_id = client_and_keys
    headers = {"X-API-Key": run_token}
    # macro_monitor needs no portfolio and succeeds; fabricate a missing one
    missing = client.post("/analyses/run_does_not_exist/report", headers=headers)
    assert missing.status_code == 404


def test_analyses_are_idempotent(client_and_keys):
    client, run_token, _ = client_and_keys
    headers = {"X-API-Key": run_token}

    first = client.post("/analyses", json={"engine": "macro_monitor"}, headers=headers)
    assert first.json()["deduplicated"] is False
    job_id = first.json()["job_id"]

    second = client.post("/analyses", json={"engine": "macro_monitor"}, headers=headers)
    assert second.json()["deduplicated"] is True
    assert second.json()["job_id"] == job_id

    forced = client.post(
        "/analyses", json={"engine": "macro_monitor", "force": True}, headers=headers
    )
    assert forced.json()["deduplicated"] is False
    assert forced.json()["job_id"] != job_id
