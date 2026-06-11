from atlas.platform.runtime.registry import EngineRegistry


def build_registry() -> EngineRegistry:
    """All available engines. Engine 2 (macro monitor) registers here in Phase 4."""
    from atlas.domain.engines.impairment import ImpairmentEngine

    registry = EngineRegistry()
    registry.register(ImpairmentEngine())
    return registry
