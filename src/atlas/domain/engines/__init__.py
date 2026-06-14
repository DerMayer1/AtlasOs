from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from atlas.platform.runtime.registry import EngineRegistry


def build_registry() -> EngineRegistry:
    """Build the registry of available deterministic engines."""
    from atlas.domain.engines.impairment.engine import ImpairmentEngine
    from atlas.domain.engines.macro_monitor.engine import MacroMonitorEngine
    from atlas.platform.runtime.registry import EngineRegistry

    registry = EngineRegistry()
    registry.register(ImpairmentEngine())
    registry.register(MacroMonitorEngine())
    return registry
