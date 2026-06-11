"""Citation validator tests (PRD R7) — the core of the auditability guarantee."""

import json

import pytest

from atlas.agent.citations import resolve_value, validate
from atlas.platform.audit.artifacts import ArtifactStore


@pytest.fixture
def store_with_artifacts(tmp_path):
    store = ArtifactStore(tmp_path / "artifacts")
    store.publish(
        "run_1",
        "impairment_scores.csv",
        b"company,p_impairment,ev_mean\nAlpha,0.3240,950.19\nBeta Logistics,0.9239,386.01\n",
    )
    store.publish(
        "run_1",
        "metrics.json",
        json.dumps({"portfolio_mean_p_impairment": 0.6240, "n_companies": 2.0}).encode(),
    )
    return store


def test_resolve_csv_value(store_with_artifacts):
    v = resolve_value(
        store_with_artifacts, "run_1/impairment_scores.csv", "p_impairment@Beta Logistics"
    )
    assert v == pytest.approx(0.9239)


def test_resolve_json_value(store_with_artifacts):
    v = resolve_value(store_with_artifacts, "run_1/metrics.json", "portfolio_mean_p_impairment")
    assert v == pytest.approx(0.6240)


def test_valid_narrative_passes(store_with_artifacts):
    text = (
        "Portfolio mean impairment probability is 0.6240 "
        "[run_1/metrics.json:portfolio_mean_p_impairment]. The most exposed name is "
        "Beta Logistics at 92.4% [run_1/impairment_scores.csv:p_impairment@Beta Logistics]."
    )
    report = validate(text, store_with_artifacts)
    assert report.valid
    assert report.orphan_claims == []
    assert all(c.ok for c in report.citations)


def test_percentage_matches_fraction(store_with_artifacts):
    # 32.4% must match the stored fraction 0.3240
    text = "Alpha sits at 32.4% [run_1/impairment_scores.csv:p_impairment@Alpha]."
    report = validate(text, store_with_artifacts)
    assert report.valid


def test_orphan_claim_detected(store_with_artifacts):
    text = "Impairment risk is around 87.5% this year."  # no citation
    report = validate(text, store_with_artifacts)
    assert not report.valid
    assert "87.5%" in report.orphan_claims


def test_broken_citation_detected(store_with_artifacts):
    text = "Risk is 0.5000 [run_1/does_not_exist.csv:p_impairment@Nobody]."
    report = validate(text, store_with_artifacts)
    assert not report.valid
    assert any(not c.ok for c in report.citations)


def test_value_mismatch_detected(store_with_artifacts):
    # cites the right artifact/locator but states the wrong number
    text = "Beta Logistics is at 0.1000 [run_1/impairment_scores.csv:p_impairment@Beta Logistics]."
    report = validate(text, store_with_artifacts)
    assert not report.valid
    assert any("!=" in c.detail for c in report.citations)


def test_years_are_not_flagged_as_orphans(store_with_artifacts):
    text = (
        "Echoing 2008 and 2020, mean risk is 0.6240 "
        "[run_1/metrics.json:portfolio_mean_p_impairment]."
    )
    report = validate(text, store_with_artifacts)
    assert report.valid  # 2008 / 2020 are integers, not risk figures
