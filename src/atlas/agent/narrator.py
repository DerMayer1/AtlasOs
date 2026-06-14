"""Narrator: structured results -> institutional thesis with mandatory citations.

The LLM is handed a CITABLE VALUES list (every addressable figure with its
exact ``[artifact_id:locator]`` token) plus the structured results — never raw
snapshot data. The service then validates the prose against the artifacts.

The deterministic ``template_narrative`` is the degraded path: a factual,
fully-cited summary used when no LLM is available or when LLM prose fails
citation validation after a retry (PRD: report ships numbers-only).
"""

from __future__ import annotations

import json
from dataclasses import dataclass

import pandas as pd

from atlas.agent.llm import LLMClient
from atlas.agent.prompts import NARRATOR_SYSTEM
from atlas.agent.schemas import TokenUsage
from atlas.platform.audit.artifacts import ArtifactStore
from atlas.platform.contracts.schemas import AnalysisResult

_NON_NARRATIVE_ARTIFACTS = {"regime_history.csv"}


@dataclass
class CitableValue:
    label: str
    artifact_id: str
    locator: str
    value: float

    @property
    def token(self) -> str:
        return f"[{self.artifact_id}:{self.locator}]"


def citable_values(result: AnalysisResult, store: ArtifactStore) -> list[CitableValue]:
    out: list[CitableValue] = []
    for artifact in result.artifacts:
        if artifact.name in _NON_NARRATIVE_ARTIFACTS:
            continue
        path = store.open_path(artifact.artifact_id)
        if artifact.name == "metrics.json":
            data = json.loads(path.read_text())
            for key, value in data.items():
                out.append(CitableValue(f"metric {key}", artifact.artifact_id, key, float(value)))
        elif path.suffix == ".csv":
            df = pd.read_csv(path)
            key_col = df.columns[0]
            for _, row in df.iterrows():
                row_key = str(row[key_col])
                for col in df.columns[1:]:
                    out.append(
                        CitableValue(
                            f"{col} of {row_key}",
                            artifact.artifact_id,
                            f"{col}@{row_key}",
                            float(row[col]),
                        )
                    )
    return out


def _format_citables(values: list[CitableValue]) -> str:
    return "\n".join(f"- {v.label} = {v.value:.4f}  cite as {v.token}" for v in values)


def narrate_with_llm(
    question: str,
    results: list[AnalysisResult],
    store: ArtifactStore,
    llm: LLMClient,
) -> tuple[str, TokenUsage]:
    citables: list[CitableValue] = []
    for r in results:
        citables.extend(citable_values(r, store))

    user = (
        f"Question: {question}\n\n"
        f"CITABLE VALUES (use these tokens verbatim; write no other number):\n"
        f"{_format_citables(citables)}\n\n"
        "Write the thesis now."
    )
    resp = llm.complete(NARRATOR_SYSTEM, user)
    return resp.text.strip(), resp.usage


def template_narrative(results: list[AnalysisResult], store: ArtifactStore) -> str:
    """Deterministic, fully-cited factual summary (the numbers-only path)."""
    parts: list[str] = []
    for result in results:
        values = {v.locator: v for v in citable_values(result, store)}

        regimes = [
            (loc.split("@")[1], v)
            for loc, v in values.items()
            if loc.startswith("probability@")
        ]
        if regimes:
            regime_txt = ", ".join(
                f"{name} {v.value * 100:.1f}% {v.token}" for name, v in regimes
            )
            parts.append(f"Macro regime probabilities: {regime_txt}.")

        stress = values.get("stress_index")
        breadth = values.get("stress_breadth")
        alerts = values.get("n_alerts")
        if stress is not None and breadth is not None:
            sentence = (
                "Composite macro stress is "
                f"{stress.value:.2f} {stress.token}, with "
                f"{breadth.value * 100:.1f}% {breadth.token} "
                "of monitored indicators elevated"
            )
            if alerts is not None:
                sentence += f" and {int(alerts.value)} active alerts {alerts.token}"
            parts.append(sentence + ".")

        next_regimes = [
            (loc.removeprefix("p_next_regime_"), value)
            for loc, value in values.items()
            if loc.startswith("p_next_regime_")
        ]
        if next_regimes:
            next_txt = ", ".join(
                f"{name} {value.value * 100:.1f}% {value.token}"
                for name, value in next_regimes
            )
            parts.append(f"One-month HMM transition probabilities: {next_txt}.")

        mean = values.get("portfolio_mean_p_impairment")
        n = values.get("n_companies")
        if mean is not None:
            sentence = (
                "Portfolio mean probability of impairment is "
                f"{mean.value * 100:.1f}% {mean.token}"
            )
            if n is not None:
                sentence += f" across {int(n.value)} companies {n.token}"
            parts.append(sentence + ".")

        expected_loss = values.get("portfolio_expected_impairment_loss")
        expected_ratio = values.get("portfolio_expected_loss_ratio")
        tail_loss = values.get("portfolio_loss_p95")
        if expected_loss is not None and expected_ratio is not None:
            sentence = (
                "Base one-year expected impairment loss is "
                f"{expected_loss.value:.1f} {expected_loss.token}, equal to "
                f"{expected_ratio.value * 100:.1f}% {expected_ratio.token} "
                "of carrying value"
            )
            if tail_loss is not None:
                sentence += (
                    ", while the adverse P95 loss is "
                    f"{tail_loss.value:.1f} {tail_loss.token}"
                )
            parts.append(sentence + ".")

        exposures = sorted(
            (
                (loc.split("@")[1], v)
                for loc, v in values.items()
                if loc.startswith("p_impairment@")
            ),
            key=lambda kv: kv[1].value,
            reverse=True,
        )
        if exposures:
            name, v = exposures[0]
            parts.append(
                f"The most exposed name is {name}, with an impairment probability of "
                f"{v.value * 100:.1f}% {v.token}."
            )
    return " ".join(parts)
