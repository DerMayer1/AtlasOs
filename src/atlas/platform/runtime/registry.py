"""Engine registry: engines are discoverable, never hard-coded (PRD P2 / R9).

The agent (Phase 3) will read capabilities from here to build plans and to
answer honestly when no engine can handle a question.
"""

from __future__ import annotations

from atlas.platform.contracts.worker import AnalysisWorker


class EngineRegistry:
    def __init__(self) -> None:
        self._engines: dict[str, AnalysisWorker] = {}

    def register(self, worker: AnalysisWorker) -> None:
        if not isinstance(worker, AnalysisWorker):
            raise TypeError(f"{type(worker).__name__} does not implement AnalysisWorker")
        if worker.name in self._engines:
            raise ValueError(f"engine {worker.name!r} is already registered")
        self._engines[worker.name] = worker

    def get(self, name: str) -> AnalysisWorker:
        try:
            return self._engines[name]
        except KeyError:
            raise KeyError(
                f"no engine named {name!r}; available: {sorted(self._engines)}"
            ) from None

    def capabilities(self) -> dict[str, str]:
        return {name: worker.describe() for name, worker in sorted(self._engines.items())}
