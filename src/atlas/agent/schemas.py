"""Typed contracts for the agent layer (PRD R7)."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field

from atlas.platform.contracts.schemas import utcnow


class PlannedCall(BaseModel):
    """One typed engine invocation the orchestrator decided to make."""

    engine: str
    params: dict = Field(default_factory=dict)
    reason: str = ""


class Plan(BaseModel):
    """Output of the orchestrator. An empty `calls` list means a refusal."""

    question: str
    calls: list[PlannedCall] = Field(default_factory=list)
    refusal_reason: str | None = None

    @property
    def is_refusal(self) -> bool:
        return not self.calls


class ExecutedCall(BaseModel):
    engine: str
    run_id: str
    status: str
    latency_ms: int
    result_id: str | None = None
    error: str | None = None


class Citation(BaseModel):
    """A resolved (or unresolved) `[artifact_id:locator]` reference."""

    raw: str
    artifact_id: str
    locator: str
    claimed_value: float | None = None
    resolved_value: float | None = None
    ok: bool = False
    detail: str = ""


class CitationReport(BaseModel):
    citations: list[Citation] = Field(default_factory=list)
    orphan_claims: list[str] = Field(default_factory=list)

    @property
    def valid(self) -> bool:
        return not self.orphan_claims and all(c.ok for c in self.citations)


class TokenUsage(BaseModel):
    input_tokens: int = 0
    output_tokens: int = 0
    cost_usd: float = 0.0

    def __add__(self, other: TokenUsage) -> TokenUsage:
        return TokenUsage(
            input_tokens=self.input_tokens + other.input_tokens,
            output_tokens=self.output_tokens + other.output_tokens,
            cost_usd=round(self.cost_usd + other.cost_usd, 8),
        )


class AgentAnswer(BaseModel):
    """What POST /agent/ask returns and what the trace records."""

    trace_id: str
    question: str
    plan: Plan
    executed: list[ExecutedCall] = Field(default_factory=list)
    narrative: str | None = None
    citations: CitationReport = Field(default_factory=CitationReport)
    degraded: bool = False
    degraded_reason: str | None = None
    capabilities: dict[str, str] = Field(default_factory=dict)
    llm_model: str | None = None
    usage: TokenUsage = Field(default_factory=TokenUsage)
    latency_ms: int = 0
    created_at: datetime = Field(default_factory=utcnow)
