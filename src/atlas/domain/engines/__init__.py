from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from atlas.platform.runtime.registry import EngineRegistry


def build_registry() -> EngineRegistry:
    """All available engines. Engine 2 (macro monitor) registers here in Phase 4."""
    from atlas.domain.engines.impairment.engine import ImpairmentEngine
    from atlas.platform.runtime.registry import EngineRegistry

    registry = EngineRegistry()
    registry.register(ImpairmentEngine())
    return registry
