"""Agent orchestrator / narrator / service tests (PRD R7)."""

import pytest

from atlas.agent.evals.cases import _good_narrative, _orphan_narrative, make_responder
from atlas.agent.llm import LLMResponse, LLMToolCall, NullLLMClient, ScriptedLLMClient
from atlas.agent.orchestrator import make_plan, plan_deterministic
from atlas.agent.service import AgentService
from atlas.agent.trace_store import TraceStore
from atlas.domain.data.synthetic import make_macro_frame
from atlas.domain.engines import build_registry
from atlas.platform.audit.artifacts import ArtifactStore
from atlas.platform.audit.snapshots import SnapshotStore
from atlas.platform.db.models import Base
from atlas.platform.db.session import make_engine, make_session_factory

PARAMS = {
    "companies": [
        {"name": "Alpha", "ebitda": 120.0, "multiple": 8.0, "carrying_value": 900.0},
        {"name": "Beta", "ebitda": 60.0, "multiple": 6.5, "carrying_value": 450.0},
    ],
    "n_sims": 2000,
    "seed": 7,
}


@pytest.fixture
def wiring(tmp_path):
    engine = make_engine(f"sqlite:///{tmp_path / 'a.db'}")
    Base.metadata.create_all(engine)
    sf = make_session_factory(engine)
    snapshots = SnapshotStore(tmp_path / "snap")
    artifacts = ArtifactStore(tmp_path / "art")
    manifest = snapshots.create({"macro": make_macro_frame()}, sources=["t"])
    registry = build_registry()
    return sf, snapshots, artifacts, registry, manifest.snapshot_id


def _service(wiring, llm):
    sf, snapshots, artifacts, registry, snap = wiring
    svc = AgentService(
        registry=registry, snapshots=snapshots, artifacts=artifacts,
        session_factory=sf, trace_store=TraceStore(sf), llm=llm,
    )
    return svc, snap


# --- orchestrator -----------------------------------------------------------


def test_deterministic_planner_routes_impairment():
    plan = plan_deterministic("what is the impairment risk?", build_registry())
    assert not plan.is_refusal
    assert plan.calls[0].engine == "impairment"


def test_deterministic_planner_routes_macro_monitor():
    plan = plan_deterministic(
        "show the current macro regime and credit spread alerts",
        build_registry(),
    )
    assert not plan.is_refusal
    assert plan.calls[0].engine == "macro_monitor"


def test_deterministic_planner_refuses_out_of_scope():
    plan = plan_deterministic("what's your fx forecast?", build_registry())
    assert plan.is_refusal
    assert "impairment" in plan.refusal_reason


def test_make_plan_falls_back_when_llm_unavailable():
    plan, used_llm = make_plan("impairment risk?", build_registry(), NullLLMClient())
    assert used_llm is False
    assert not plan.is_refusal


def test_llm_tool_call_becomes_plan():
    def responder(system, user, tools):
        return LLMResponse(tool_calls=[LLMToolCall("run_impairment", {"reason": "x"})])

    plan, used_llm = make_plan("anything", build_registry(), ScriptedLLMClient(responder))
    assert used_llm and plan.calls[0].engine == "impairment"


def test_llm_refusal_text_becomes_refusal():
    def responder(system, user, tools):
        return LLMResponse(text="CANNOT: no fx engine, only impairment")

    plan, _ = make_plan("fx?", build_registry(), ScriptedLLMClient(responder))
    assert plan.is_refusal and "impairment" in plan.refusal_reason


# --- service flow -----------------------------------------------------------


def test_full_flow_valid_narrative(wiring):
    svc, snap = _service(wiring, ScriptedLLMClient(
        make_responder(plan_engine="impairment", narrator=_good_narrative)))
    answer = svc.ask("impairment risk?", snap, PARAMS, portfolio_id="pf_1")
    assert answer.executed[0].status == "succeeded"
    assert answer.citations.valid
    assert not answer.degraded
    assert answer.narrative


def test_orphan_narrative_degrades_to_numbers_only(wiring):
    svc, snap = _service(wiring, ScriptedLLMClient(
        make_responder(plan_engine="impairment", narrator=_orphan_narrative)))
    answer = svc.ask("impairment risk?", snap, PARAMS, portfolio_id="pf_1")
    assert answer.degraded
    assert "numbers-only" in answer.degraded_reason
    # the degraded narrative is itself fully cited
    assert answer.citations.valid


def test_no_llm_degrades_gracefully(wiring):
    svc, snap = _service(wiring, NullLLMClient())
    answer = svc.ask("what is the impairment risk?", snap, PARAMS, portfolio_id="pf_1")
    # deterministic planner still routes + engine runs + template narrative
    assert answer.executed[0].status == "succeeded"
    assert answer.degraded
    assert answer.citations.valid
    assert answer.narrative


def test_macro_monitor_flow_needs_no_portfolio(wiring):
    svc, snap = _service(wiring, NullLLMClient())
    answer = svc.ask("show the current macro regime", snap, {})
    assert answer.executed[0].engine == "macro_monitor"
    assert answer.executed[0].status == "succeeded"
    assert answer.citations.valid
    assert "Macro regime probabilities" in answer.narrative


def test_refusal_is_not_degradation(wiring):
    svc, snap = _service(wiring, NullLLMClient())
    answer = svc.ask("what's your eur/usd forecast?", snap, PARAMS)
    assert answer.plan.is_refusal
    assert not answer.executed
    assert "impairment" in answer.capabilities


def test_trace_persisted_and_queryable(wiring):
    sf = wiring[0]
    svc, snap = _service(wiring, ScriptedLLMClient(
        make_responder(plan_engine="impairment")))
    answer = svc.ask("impairment risk?", snap, PARAMS, portfolio_id="pf_42")
    store = TraceStore(sf)
    assert store.get(answer.trace_id) is not None
    assert len(store.by_portfolio("pf_42")) == 1
    run_id = answer.executed[0].run_id
    assert store.by_run(run_id)[0].id == answer.trace_id
