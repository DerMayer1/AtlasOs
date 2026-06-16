"""LLM client behind an interface so the agent is testable and degradable.

- OpenAILLMClient: production path (OpenAI tool use).
- ScriptedLLMClient: deterministic responses for tests/evals — exercises the
  real orchestrator/narrator/validator code without API cost.
- NullLLMClient: no LLM available; callers must degrade gracefully.

The agent NEVER passes raw snapshot data here — only the capability catalog and
structured AnalysisResult summaries.
"""

from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any, Protocol

from atlas.agent.schemas import TokenUsage

# Approximate OpenAI list price for the default small planning/narration model
# (USD per token). Used only to populate the trace cost field; not load-bearing.
_PRICE_IN = 0.40 / 1_000_000
_PRICE_OUT = 1.60 / 1_000_000


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


def _openai_tools(tools: list[dict[str, Any]] | None) -> list[dict[str, Any]]:
    converted = []
    for tool in tools or []:
        converted.append(
            {
                "type": "function",
                "function": {
                    "name": tool["name"],
                    "description": tool.get("description", ""),
                    "parameters": tool.get("input_schema", {"type": "object"}),
                },
            }
        )
    return converted


class OpenAILLMClient:
    """Production client. Imports `openai` lazily so the package is optional."""

    def __init__(self, api_key: str, model: str = "gpt-4.1-mini") -> None:
        try:
            from openai import OpenAI
        except ImportError as exc:  # pragma: no cover - depends on optional dep
            raise LLMUnavailableError("openai package not installed") from exc
        self._client = OpenAI(api_key=api_key)
        self.model = model

    def complete(self, system: str, user: str, tools=None) -> LLMResponse:
        openai_tools = _openai_tools(tools)
        try:
            resp = self._client.chat.completions.create(
                model=self.model,
                max_completion_tokens=1500,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
                tools=openai_tools or None,
            )
        except Exception as exc:  # pragma: no cover - network path
            raise LLMUnavailableError(str(exc)) from exc

        choice = resp.choices[0]
        message = choice.message
        tool_calls = []
        for tool_call in message.tool_calls or []:
            function = tool_call.function
            arguments = function.arguments or "{}"
            try:
                parsed_arguments = json.loads(arguments)
            except Exception:
                parsed_arguments = {}
            tool_calls.append(LLMToolCall(name=function.name, arguments=parsed_arguments))

        usage_data = resp.usage
        input_tokens = usage_data.prompt_tokens if usage_data else 0
        output_tokens = usage_data.completion_tokens if usage_data else 0

        usage = TokenUsage(
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cost_usd=round(
                input_tokens * _PRICE_IN + output_tokens * _PRICE_OUT,
                8,
            ),
        )
        return LLMResponse(text=message.content or "", tool_calls=tool_calls, usage=usage)
