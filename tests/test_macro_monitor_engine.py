import json

import numpy as np
import pandas as pd
import pytest

from atlas.agent.narrator import citable_values
from atlas.domain.engines.macro_monitor import MacroMonitorEngine
from atlas.platform.contracts.schemas import AnalysisRequest, AnalysisStatus
from atlas.platform.contracts.worker import AnalysisWorker, RunContext


def _request(snapshot_id: str, **params) -> AnalysisRequest:
    return AnalysisRequest(
        request_id="req_macro",
        engine="macro_monitor",
        snapshot_id=snapshot_id,
        params=params,
    )


def test_engine_satisfies_worker_protocol():
    assert isinstance(MacroMonitorEngine(), AnalysisWorker)


def test_run_publishes_macro_state_and_decision_artifacts(
    macro_snapshot, snapshot_store, artifact_store
):
    result = MacroMonitorEngine().run(
        _request(macro_snapshot.snapshot_id),
        RunContext("run_macro", snapshot_store, artifact_store),
    )

    assert result.status is AnalysisStatus.SUCCEEDED
    assert {artifact.name for artifact in result.artifacts} == {
        "macro_state.json",
        "indicator_snapshot.csv",
        "regime_history.csv",
        "scenario_assumptions.csv",
        "regime_probabilities.csv",
        "metrics.json",
    }
    assert np.isclose(
        sum(
            result.metrics[f"p_regime_{regime}"]
            for regime in ("expansion", "tightening", "crisis")
        ),
        1.0,
    )
    assert np.isclose(
        sum(
            result.metrics[f"p_next_regime_{regime}"]
            for regime in ("expansion", "tightening", "crisis")
        ),
        1.0,
    )
    assert 0.0 <= result.metrics["stress_breadth"] <= 1.0

    state = json.loads(
        artifact_store.open_path("run_macro/macro_state.json").read_text()
    )
    assert state["regime"]["current"] in {"expansion", "tightening", "crisis"}
    assert set(state["indicators"]) == {
        "fed_funds",
        "baa_aaa_spread",
        "t10y2y",
        "cpi_yoy",
        "unemployment",
    }
    assert state["scenario_method"] == "state_conditioned_historical_median"


def test_scenarios_are_numeric_state_conditioned_references(
    macro_snapshot, snapshot_store, artifact_store
):
    MacroMonitorEngine().run(
        _request(macro_snapshot.snapshot_id),
        RunContext("run_scenarios_macro", snapshot_store, artifact_store),
    )
    scenarios = pd.read_csv(
        artifact_store.open_path("run_scenarios_macro/scenario_assumptions.csv")
    )
    assert list(scenarios["scenario"]) == ["base", "tightening", "crisis"]
    assert scenarios.drop(columns="scenario").notna().all().all()
    assert (scenarios["sample_size"] >= 0).all()


def test_optional_vix_and_snapshot_comparison_are_reported(
    snapshot_store, artifact_store
):
    from atlas.domain.data.synthetic import make_macro_frame

    previous = make_macro_frame()
    previous["vix"] = np.linspace(14.0, 18.0, len(previous))
    current = previous.copy()
    current.iloc[-1, current.columns.get_loc("baa_aaa_spread")] += 1.0
    current.iloc[-1, current.columns.get_loc("vix")] += 10.0
    old_manifest = snapshot_store.create({"macro": previous}, sources=["old"])
    new_manifest = snapshot_store.create({"macro": current}, sources=["new"])

    result = MacroMonitorEngine().run(
        _request(
            new_manifest.snapshot_id,
            comparison_snapshot_id=old_manifest.snapshot_id,
        ),
        RunContext("run_compare", snapshot_store, artifact_store),
    )
    indicators = pd.read_csv(
        artifact_store.open_path("run_compare/indicator_snapshot.csv")
    ).set_index("indicator")

    assert result.metrics["has_vix"] == 1.0
    assert result.metrics["has_comparison_snapshot"] == 1.0
    assert indicators.loc["vix", "snapshot_delta"] == pytest.approx(10.0)
    assert indicators.loc["baa_aaa_spread", "snapshot_delta"] == pytest.approx(1.0)


def test_same_snapshot_produces_identical_artifacts(
    macro_snapshot, snapshot_store, artifact_store
):
    engine = MacroMonitorEngine()
    first = engine.run(
        _request(macro_snapshot.snapshot_id),
        RunContext("run_macro_a", snapshot_store, artifact_store),
    )
    second = engine.run(
        _request(macro_snapshot.snapshot_id),
        RunContext("run_macro_b", snapshot_store, artifact_store),
    )
    assert [artifact.sha256 for artifact in first.artifacts] == [
        artifact.sha256 for artifact in second.artifacts
    ]


def test_narrator_excludes_full_regime_history(
    macro_snapshot, snapshot_store, artifact_store
):
    result = MacroMonitorEngine().run(
        _request(macro_snapshot.snapshot_id),
        RunContext("run_macro_citations", snapshot_store, artifact_store),
    )
    values = citable_values(result, artifact_store)
    assert values
    assert all(
        value.artifact_id != "run_macro_citations/regime_history.csv"
        for value in values
    )


def test_missing_macro_table_fails(snapshot_store, artifact_store):
    manifest = snapshot_store.create(
        {"prices": pd.DataFrame({"value": [1.0, 2.0]})},
        sources=["test"],
    )
    with pytest.raises(ValueError, match="no 'macro' table"):
        MacroMonitorEngine().run(
            _request(manifest.snapshot_id),
            RunContext("run_missing_macro", snapshot_store, artifact_store),
        )


def test_invalid_monitoring_windows_fail(
    macro_snapshot, snapshot_store, artifact_store
):
    with pytest.raises(ValueError, match="long_window_months"):
        MacroMonitorEngine().run(
            _request(
                macro_snapshot.snapshot_id,
                short_window_months=12,
                long_window_months=6,
            ),
            RunContext("run_invalid_windows", snapshot_store, artifact_store),
        )
