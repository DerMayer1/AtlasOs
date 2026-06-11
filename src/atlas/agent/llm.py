"""LLM client behind an interface so the agent is testable and degradable.

- AnthropicLLMClient: production path (Anthropic tool use).
- ScriptedLLMClient: deterministic responses for tests/evals — exercises the
  real orchestrator/narrator/validator code without API cost.
- NullLLMClient: no LLM available; callers must degrade gracefully.

The agent NEVER passes raw snapshot data here — only the capability catalog and
structured AnalysisResult summaries.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any, Protocol

from atlas.agent.schemas import TokenUsage

# Anthropic list price for the small planning/narration model (USD per token).
# Used only to populate the trace cost field; not load-bearing.
_PRICE_IN = 0.80 / 1_000_000
_PRICE_OUT = 4.00 / 1_000_000


@dataclass
class LLMToolCall:
    name: str
    arguments: dict[str, Any]


@dataclass
class LLMResponse:
    text: str = ""
    tool_calls: list[LLMToolCall] = field(default_factory=list)
    usage: TokenUsage = field(default_factory=TokenUsage)


class LLMUnavailableError(Exception):
    pass


class LLMClient(Protocol):
    model: str

    def complete(
        self,
        system: str,
        user: str,
        tools: list[dict[str, Any]] | None = None,
    ) -> LLMResponse: ...


class NullLLMClient:
    """Always unavailable. The agent falls back to deterministic planning and
    numbers-only narration (PRD graceful degradation)."""

    model = "none"

    def complete(self, system: str, user: str, tools=None) -> LLMResponse:
        raise LLMUnavailableError("no LLM client configured")


class ScriptedLLMClient:
    """Deterministic client for tests/evals.

    `responder(system, user, tools) -> LLMResponse` lets a test simulate exactly
    what a real model would return (a tool call, a refusal, narrative prose),
    so the full agent code path runs without network or cost.
    """

    model = "scripted"

    def __init__(self, responder: Callable[[str, str, list | None], LLMResponse]) -> None:
        self._responder = responder

    def complete(self, system: str, user: str, tools=None) -> LLMResponse:
        return self._responder(system, user, tools)


class AnthropicLLMClient:
    """Production client. Imports `anthropic` lazily so the package is optional."""

    def __init__(self, api_key: str, model: str = "claude-haiku-4-5-20251001") -> None:
        try:
            import anthropic
        except ImportError as exc:  # pragma: no cover - depends on optional dep
            raise LLMUnavailableError("anthropic package not installed") from exc
        self._anthropic = anthropic
        self._client = anthropic.Anthropic(api_key=api_key)
        self.model = model

    def complete(self, system: str, user: str, tools=None) -> LLMResponse:
        try:
            resp = self._client.messages.create(
                model=self.model,
                max_tokens=1500,
                system=system,
                messages=[{"role": "user", "content": user}],
                tools=tools or [],
            )
        except Exception as exc:  # pragma: no cover - network path
            raise LLMUnavailableError(str(exc)) from exc

        text_parts, tool_calls = [], []
        for block in resp.content:
            if block.type == "text":
                text_parts.append(block.text)
            elif block.type == "tool_use":
                tool_calls.append(LLMToolCall(name=block.name, arguments=dict(block.input)))

        usage = TokenUsage(
            input_tokens=resp.usage.input_tokens,
            output_tokens=resp.usage.output_tokens,
            cost_usd=round(
                resp.usage.input_tokens * _PRICE_IN + resp.usage.output_tokens * _PRICE_OUT, 8
            ),
        )
        return LLMResponse(text="\n".join(text_parts), tool_calls=tool_calls, usage=usage)
