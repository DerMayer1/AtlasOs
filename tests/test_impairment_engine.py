import numpy as np
import pandas as pd
import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from atlas.domain.engines.impairment import ImpairmentEngine
from atlas.domain.engines.impairment.regimes import REGIMES, regime_probabilities
from atlas.platform.contracts.schemas import AnalysisRequest, AnalysisStatus
from atlas.platform.contracts.worker import AnalysisWorker, RunContext
from tests.conftest import make_macro_frame


def _request(snapshot_id: str, seed: int = 7) -> AnalysisRequest:
    return AnalysisRequest(
        request_id="req_test",
        engine="impairment",
        snapshot_id=snapshot_id,
        params={
            "companies": [
                {
                    "name": "Alpha",
                    "sector": "industrials",
                    "ebitda": 100.0,
                    "multiple": 8.0,
                    "carrying_value": 750.0,
                    "debt": 300.0,
                    "cash": 50.0,
                    "debt_due_1y": 75.0,
                },
                {
                    "name": "Beta",
                    "sector": "logistics",
                    "ebitda": 50.0,
                    "multiple": 6.0,
                    "carrying_value": 400.0,
                    "ebitda_volatility": 0.4,
                    "debt": 220.0,
                    "cash": 20.0,
                    "debt_due_1y": 80.0,
                },
            ],
            "n_sims": 5000,
            "seed": seed,
        },
    )


def test_engine_satisfies_worker_protocol():
    assert isinstance(ImpairmentEngine(), AnalysisWorker)


def test_legacy_four_field_company_contract_remains_valid(
    macro_snapshot, snapshot_store, artifact_store
):
    request = AnalysisRequest(
        request_id="req_legacy",
        engine="impairment",
        snapshot_id=macro_snapshot.snapshot_id,
        params={
            "companies": [
                {
                    "name": "Legacy",
                    "ebitda": 100.0,
                    "multiple": 8.0,
                    "carrying_value": 750.0,
                }
            ],
            "n_sims": 100,
            "seed": 7,
        },
    )
    result = ImpairmentEngine().run(
        request,
        RunContext("run_legacy", snapshot_store, artifact_store),
    )
    assert 0 <= result.metrics["portfolio_mean_p_impairment"] <= 1


def test_run_produces_provenance_and_artifacts(macro_snapshot, snapshot_store, artifact_store):
    ctx = RunContext(run_id="run_1", snapshots=snapshot_store, artifacts=artifact_store)
    result = ImpairmentEngine().run(_request(macro_snapshot.snapshot_id), ctx)

    assert result.status is AnalysisStatus.SUCCEEDED
    assert result.snapshot_id == macro_snapshot.snapshot_id
    assert result.engine_version and result.model_version
    assert {a.name for a in result.artifacts} == {
        "financial_resilience.csv",
        "impairment_scores.csv",
        "portfolio_scenarios.csv",
        "regime_probabilities.csv",
        "scenario_analysis.csv",
        "sensitivities.csv",
        "value_correlation.csv",
        "metrics.json",
    }
    scores = pd.read_csv(artifact_store.open_path("run_1/impairment_scores.csv"))
    assert list(scores["company"]) == ["Alpha", "Beta"]
    assert scores["p_impairment"].between(0, 1).all()
    assert (scores["expected_impairment_loss"] >= 0).all()
    assert (scores["recoverable_p05"] <= scores["recoverable_mean"]).all()
    assert (scores["recoverable_mean"] <= scores["recoverable_p95"]).all()


def test_scenarios_publish_decision_relevant_loss_distribution(
    macro_snapshot, snapshot_store, artifact_store
):
    result = ImpairmentEngine().run(
        _request(macro_snapshot.snapshot_id),
        RunContext("run_scenarios", snapshot_store, artifact_store),
    )
    scenarios = pd.read_csv(
        artifact_store.open_path("run_scenarios/portfolio_scenarios.csv")
    ).set_index("case")

    assert {"base|1y", "base|3y", "tightening|1y", "crisis|1y"} <= set(
        scenarios.index
    )
    assert scenarios.loc["crisis|1y", "expected_loss_ratio"] > scenarios.loc[
        "tightening|1y", "expected_loss_ratio"
    ]
    assert result.metrics["portfolio_expected_impairment_loss"] >= 0
    assert result.metrics["portfolio_loss_p95"] >= result.metrics[
        "portfolio_expected_impairment_loss"
    ]


def test_joint_model_has_explicit_nonperfect_dependence(
    macro_snapshot, snapshot_store, artifact_store
):
    ImpairmentEngine().run(
        _request(macro_snapshot.snapshot_id),
        RunContext("run_corr", snapshot_store, artifact_store),
    )
    correlation = pd.read_csv(
        artifact_store.open_path("run_corr/value_correlation.csv"),
        index_col="company",
    )

    assert np.allclose(np.diag(correlation), 1.0)
    assert np.allclose(correlation, correlation.T)
    assert -1.0 < correlation.loc["Alpha", "Beta"] < 1.0


def test_debt_changes_resilience_not_accounting_impairment(
    macro_snapshot, snapshot_store, artifact_store
):
    low_debt = _request(macro_snapshot.snapshot_id)
    high_debt = _request(macro_snapshot.snapshot_id)
    high_debt.params["companies"][0]["debt"] = 1_500.0
    high_debt.params["companies"][0]["debt_due_1y"] = 500.0

    low = ImpairmentEngine().run(
        low_debt,
        RunContext("run_low_debt", snapshot_store, artifact_store),
    )
    high = ImpairmentEngine().run(
        high_debt,
        RunContext("run_high_debt", snapshot_store, artifact_store),
    )
    low_scores = next(
        a.sha256 for a in low.artifacts if a.name == "impairment_scores.csv"
    )
    high_scores = next(
        a.sha256 for a in high.artifacts if a.name == "impairment_scores.csv"
    )
    low_resilience = next(
        a.sha256 for a in low.artifacts if a.name == "financial_resilience.csv"
    )
    high_resilience = next(
        a.sha256 for a in high.artifacts if a.name == "financial_resilience.csv"
    )

    assert low_scores == high_scores
    assert low_resilience != high_resilience


def test_higher_carrying_value_increases_impairment_risk(
    macro_snapshot, snapshot_store, artifact_store
):
    low_carrying = _request(macro_snapshot.snapshot_id)
    high_carrying = _request(macro_snapshot.snapshot_id)
    low_carrying.params["companies"] = [low_carrying.params["companies"][0]]
    high_carrying.params["companies"] = [high_carrying.params["companies"][0]]
    low_carrying.params["companies"][0]["carrying_value"] = 500.0
    high_carrying.params["companies"][0]["carrying_value"] = 950.0

    low = ImpairmentEngine().run(
        low_carrying,
        RunContext("run_low_carrying", snapshot_store, artifact_store),
    )
    high = ImpairmentEngine().run(
        high_carrying,
        RunContext("run_high_carrying", snapshot_store, artifact_store),
    )

    assert high.metrics["portfolio_mean_p_impairment"] > low.metrics[
        "portfolio_mean_p_impairment"
    ]
    assert high.metrics["portfolio_expected_impairment_loss"] > low.metrics[
        "portfolio_expected_impairment_loss"
    ]


def test_same_seed_bit_identical_artifacts(macro_snapshot, snapshot_store, artifact_store):
    engine = ImpairmentEngine()
    r1 = engine.run(
        _request(macro_snapshot.snapshot_id),
        RunContext("run_a", snapshot_store, artifact_store),
    )
    r2 = engine.run(
        _request(macro_snapshot.snapshot_id),
        RunContext("run_b", snapshot_store, artifact_store),
    )
    assert [a.sha256 for a in r1.artifacts] == [a.sha256 for a in r2.artifacts]


def test_different_seed_different_numbers(macro_snapshot, snapshot_store, artifact_store):
    engine = ImpairmentEngine()
    r1 = engine.run(
        _request(macro_snapshot.snapshot_id, seed=1),
        RunContext("run_a", snapshot_store, artifact_store),
    )
    r2 = engine.run(
        _request(macro_snapshot.snapshot_id, seed=2),
        RunContext("run_b", snapshot_store, artifact_store),
    )
    h1 = next(a.sha256 for a in r1.artifacts if a.name == "impairment_scores.csv")
    h2 = next(a.sha256 for a in r2.artifacts if a.name == "impairment_scores.csv")
    assert h1 != h2


def test_missing_macro_table_fails(snapshot_store, artifact_store):
    manifest = snapshot_store.create(
        {"prices": pd.DataFrame({"x": [1.0, 2.0]})}, sources=["synthetic://test"]
    )
    ctx = RunContext("run_x", snapshot_store, artifact_store)
    with pytest.raises(ValueError, match="no 'macro' table"):
        ImpairmentEngine().run(_request(manifest.snapshot_id), ctx)


# --- property-based invariants (PRD R5) -------------------------------------


@given(seed=st.integers(min_value=0, max_value=10_000))
@settings(max_examples=25, deadline=None)
def test_regime_probabilities_form_distribution(seed):
    probs = regime_probabilities(make_macro_frame(seed=seed))
    assert list(probs.index) == list(REGIMES)
    assert (probs >= 0).all()
    assert np.isclose(probs.sum(), 1.0)


@given(
    ebitda=st.floats(min_value=1.0, max_value=1e4),
    multiple=st.floats(min_value=1.0, max_value=20.0),
    carrying=st.floats(min_value=1.0, max_value=1e6),
    seed=st.integers(min_value=0, max_value=1_000),
)
@settings(max_examples=20, deadline=None)
def test_p_impairment_always_in_unit_interval(
    tmp_path_factory, ebitda, multiple, carrying, seed
):
    from atlas.platform.audit.artifacts import ArtifactStore
    from atlas.platform.audit.snapshots import SnapshotStore

    base = tmp_path_factory.mktemp("prop")
    snaps = SnapshotStore(base / "s")
    arts = ArtifactStore(base / "a")
    manifest = snaps.create({"macro": make_macro_frame()}, sources=["synthetic://test"])

    request = AnalysisRequest(
        request_id="req_prop",
        engine="impairment",
        snapshot_id=manifest.snapshot_id,
        params={
            "companies": [
                {
                    "name": "X",
                    "ebitda": ebitda,
                    "multiple": multiple,
                    "carrying_value": carrying,
                }
            ],
            "n_sims": 500,
            "seed": seed,
        },
    )
    result = ImpairmentEngine().run(
        request, RunContext(f"run_{seed}_{id(request)}", snaps, arts)
    )
    p = result.metrics["portfolio_mean_p_impairment"]
    assert 0.0 <= p <= 1.0
