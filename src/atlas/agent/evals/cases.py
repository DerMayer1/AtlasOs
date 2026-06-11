"""Agent eval cases (PRD R8).

Each case scripts the LLM (so the suite is deterministic and free to run in CI)
and asserts on the *structured* outcome — which engine the plan used, whether
the agent correctly refused, whether citations validated, whether it degraded —
never on exact prose. A regression in the orchestrator, narrator, citation
validator, or prompts flips one of these assertions and fails CI.

The scripted responder simulates a competent model. The same code path runs
against the real Anthropic model when ATLAS_ANTHROPIC_API_KEY is set (see
runner.run_evals(live=True))."""

from __future__ import annotations

import re
from collections.abc import Callable
from dataclasses import dataclass

from atlas.agent.llm import LLMResponse, LLMToolCall
from atlas.agent.schemas import AgentAnswer

# --- scripted LLM responders ------------------------------------------------

_CITABLE_LINE = re.compile(r"=\s*(-?\d+\.\d+)\s+cite as (\[[^\]]+\])")


def _good_narrative(user: str) -> str:
    """Build a citation-valid narrative from the CITABLE VALUES block we were
    given — exactly what a compliant model would do."""
    pairs = _CITABLE_LINE.findall(user)[:3]
    if not pairs:
        return "No citable values were provided."
    sentences = [f"The figure stands at {value} {token}." for value, token in pairs]
    return " ".join(sentences)


def _orphan_narrative(user: str) -> str:
    """A non-compliant model: states a number with no citation."""
    return "Overall portfolio impairment risk is approximately 87.5% this cycle."


def _wrong_citation_narrative(user: str) -> str:
    """A model that cites a non-existent artifact/locator."""
    return "Risk is 0.5000 [run_fake/does_not_exist.csv:p_impairment@Nobody]."


def make_responder(
    *,
    plan_engine: str | None = None,
    refuse_text: str | None = None,
    narrator: Callable[[str], str] = _good_narrative,
) -> Callable[[str, str, list | None], LLMResponse]:
    def responder(system: str, user: str, tools: list | None) -> LLMResponse:
        if tools is not None:  # planning phase
            if refuse_text is not None:
                return LLMResponse(text=f"CANNOT: {refuse_text}")
            return LLMResponse(
                tool_calls=[LLMToolCall(name=f"run_{plan_engine}", arguments={"reason": "fits"})]
            )
        return LLMResponse(text=narrator(user))  # narration phase

    return responder


# --- case definition --------------------------------------------------------


@dataclass
class EvalCase:
    name: str
    question: str
    responder: Callable[[str, str, list | None], LLMResponse]
    check: Callable[[AgentAnswer], bool]
    rationale: str


def _plans_engine(answer: AgentAnswer, engine: str) -> bool:
    return not answer.plan.is_refusal and any(c.engine == engine for c in answer.plan.calls)


def _refused_with_capabilities(answer: AgentAnswer) -> bool:
    return answer.plan.is_refusal and "impairment" in (answer.plan.refusal_reason or "").lower()


CASES: list[EvalCase] = [
    # -- planning: questions that should route to the impairment engine -------
    EvalCase("impairment_direct", "What is the impairment risk of this portfolio?",
             make_responder(plan_engine="impairment"),
             lambda a: _plans_engine(a, "impairment"), "direct impairment ask routes to engine"),
    EvalCase("impairment_scenario", "How exposed is the portfolio to a 2022-style scenario?",
             make_responder(plan_engine="impairment"),
             lambda a: _plans_engine(a, "impairment"), "scenario phrasing routes to engine"),
    EvalCase("impairment_regime", "Show the current macro regime probabilities.",
             make_responder(plan_engine="impairment"),
             lambda a: _plans_engine(a, "impairment"), "regime ask routes to engine"),
    EvalCase("impairment_stress", "Stress test these holdings for a downturn.",
             make_responder(plan_engine="impairment"),
             lambda a: _plans_engine(a, "impairment"), "stress phrasing routes to engine"),
    EvalCase("impairment_valuation", "What is the valuation risk across the book?",
             make_responder(plan_engine="impairment"),
             lambda a: _plans_engine(a, "impairment"), "valuation phrasing routes to engine"),
    # -- refusals: out-of-scope questions must be declined honestly -----------
    EvalCase("refuse_fx", "What's your EUR/USD forecast for next month?",
             make_responder(refuse_text="Atlas has no FX engine. It covers impairment risk."),
             _refused_with_capabilities, "FX is out of scope -> honest refusal"),
    EvalCase("refuse_crypto", "Should I buy Bitcoin right now?",
             make_responder(refuse_text="Atlas has no crypto engine. It covers impairment risk."),
             _refused_with_capabilities, "crypto is out of scope -> honest refusal"),
    EvalCase("refuse_equity", "Predict next quarter's equity prices.",
             make_responder(refuse_text="Atlas has no equity engine. It covers impairment risk."),
             _refused_with_capabilities, "equity prediction out of scope -> refusal"),
    EvalCase("refuse_options", "Price these options for me.",
             make_responder(refuse_text="Atlas has no options engine. It covers impairment risk."),
             _refused_with_capabilities, "options out of scope -> refusal"),
    EvalCase("refuse_unrelated", "What's the weather in Lisbon?",
             make_responder(refuse_text="That is unrelated. Atlas covers impairment risk."),
             _refused_with_capabilities, "unrelated question -> refusal with capabilities"),
    # -- narration + citation enforcement -------------------------------------
    EvalCase("cited_narrative_valid", "Summarise the portfolio impairment risk.",
             make_responder(plan_engine="impairment", narrator=_good_narrative),
             lambda a: a.narrative is not None and a.citations.valid and not a.degraded,
             "compliant narrative validates and does not degrade"),
    EvalCase("orphan_claim_degrades", "Summarise the portfolio impairment risk.",
             make_responder(plan_engine="impairment", narrator=_orphan_narrative),
             lambda a: a.degraded and a.citations.valid,
             "uncited number -> rejected, retried, degraded to valid numbers-only"),
    EvalCase("broken_citation_degrades", "Summarise the portfolio impairment risk.",
             make_responder(plan_engine="impairment", narrator=_wrong_citation_narrative),
             lambda a: a.degraded,
             "citation to a non-existent artifact -> degraded"),
    EvalCase("degraded_still_cited", "Summarise the portfolio impairment risk.",
             make_responder(plan_engine="impairment", narrator=_orphan_narrative),
             lambda a: a.narrative is not None and a.citations.valid,
             "even the degraded numbers-only narrative carries valid citations"),
    EvalCase("execution_happened", "What is the impairment risk of this portfolio?",
             make_responder(plan_engine="impairment", narrator=_good_narrative),
             lambda a: len(a.executed) == 1 and a.executed[0].status == "succeeded",
             "planned engine actually ran and produced artifacts"),
    EvalCase("trace_has_capabilities_on_refusal", "Forecast gold prices.",
             make_responder(refuse_text="No commodity engine. Atlas covers impairment risk."),
             lambda a: "impairment" in a.capabilities,
             "refusal answer still advertises real capabilities"),
]
