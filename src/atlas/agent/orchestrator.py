"""Orchestrator: question -> typed Plan (PRD R7).

Production path uses the LLM with the engine catalog exposed as tools. When no
LLM is available it falls back to a deterministic keyword planner, which also
serves as the graceful-degradation path. Either way the output is a typed Plan
and the engines that run are the real deterministic ones.
"""

from __future__ import annotations

from atlas.agent.llm import LLMClient, LLMUnavailableError
from atlas.agent.prompts import ORCHESTRATOR_SYSTEM
from atlas.agent.schemas import Plan, PlannedCall
from atlas.platform.runtime.registry import EngineRegistry

# Words that signal a question Atlas cannot answer (no engine covers them).
_OUT_OF_SCOPE = (
    "fx", "currency", "foreign exchange", "equity price", "stock price",
    "interest rate forecast", "options", "crypto", "bitcoin", "commodity",
)
# Evaluated before impairment because impairment also consumes macro regimes.
_MACRO_MONITOR_HINTS = (
    "macro", "regime", "cycle", "inflation", "credit spread", "yield curve",
    "unemployment", "fed funds", "vix", "market stress", "macro alert",
    "macro scenario", "tightening",
)
# Words that map to the impairment engine.
_IMPAIRMENT_HINTS = (
    "impair", "impairment", "risk", "portfolio", "write-down", "writedown",
    "valuation", "ebitda", "carrying", "scenario", "stress",
)


def _engine_tools(registry: EngineRegistry) -> list[dict]:
    tools = []
    for name, desc in registry.capabilities().items():
        tools.append(
            {
                "name": f"run_{name}",
                "description": desc,
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "reason": {"type": "string", "description": "why this engine answers"}
                    },
                },
            }
        )
    return tools


def plan_with_llm(question: str, registry: EngineRegistry, llm: LLMClient,
                  portfolio_context: str = "") -> Plan:
    tools = _engine_tools(registry)
    user = f"Question: {question}"
    if portfolio_context:
        user += f"\nPortfolio context: {portfolio_context}"

    resp = llm.complete(ORCHESTRATOR_SYSTEM, user, tools=tools)

    calls: list[PlannedCall] = []
    for tc in resp.tool_calls:
        engine = tc.name[len("run_") :] if tc.name.startswith("run_") else tc.name
        if engine in registry.capabilities():
            calls.append(PlannedCall(engine=engine, reason=str(tc.arguments.get("reason", ""))))

    if calls:
        return Plan(question=question, calls=calls)

    # No tool call -> the model declined. Honour its stated reason.
    reason = resp.text.strip()
    if reason.upper().startswith("CANNOT:"):
        reason = reason[len("CANNOT:") :].strip()
    return Plan(
        question=question,
        refusal_reason=reason or "No available engine can answer this question.",
    )


def plan_deterministic(question: str, registry: EngineRegistry) -> Plan:
    """LLM-free planner: keyword match against the registry. Used when no LLM is
    configured or when the LLM is down (graceful degradation)."""
    caps = registry.capabilities()
    q = question.lower()

    if any(term in q for term in _OUT_OF_SCOPE):
        return Plan(
            question=question,
            refusal_reason=(
                "Atlas does not cover that. Available capabilities: "
                + "; ".join(f"{n} ({d})" for n, d in caps.items())
            ),
        )

    if "macro_monitor" in caps and any(term in q for term in _MACRO_MONITOR_HINTS):
        return Plan(
            question=question,
            calls=[
                PlannedCall(
                    engine="macro_monitor",
                    reason="macro-monitor keyword match (deterministic)",
                )
            ],
        )

    if "impairment" in caps and any(term in q for term in _IMPAIRMENT_HINTS):
        return Plan(
            question=question,
            calls=[PlannedCall(engine="impairment", reason="keyword match (deterministic)")],
        )

    return Plan(
        question=question,
        refusal_reason=(
            "No engine matched this question. Available capabilities: "
            + "; ".join(f"{n} ({d})" for n, d in caps.items())
        ),
    )


def make_plan(question: str, registry: EngineRegistry, llm: LLMClient,
              portfolio_context: str = "") -> tuple[Plan, bool]:
    """Returns (plan, used_llm). Falls back to deterministic planning if the LLM
    is unavailable."""
    try:
        return plan_with_llm(question, registry, llm, portfolio_context), True
    except LLMUnavailableError:
        return plan_deterministic(question, registry), False
