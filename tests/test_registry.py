import pytest

from atlas.domain.engines.impairment import ImpairmentEngine
from atlas.platform.runtime.registry import EngineRegistry


def test_register_and_get():
    registry = EngineRegistry()
    engine = ImpairmentEngine()
    registry.register(engine)
    assert registry.get("impairment") is engine
    assert "impairment" in registry.capabilities()


def test_duplicate_rejected():
    registry = EngineRegistry()
    registry.register(ImpairmentEngine())
    with pytest.raises(ValueError, match="already registered"):
        registry.register(ImpairmentEngine())


def test_unknown_engine_lists_available():
    registry = EngineRegistry()
    registry.register(ImpairmentEngine())
    with pytest.raises(KeyError, match="impairment"):
        registry.get("macro_monitor")


def test_non_worker_rejected():
    registry = EngineRegistry()
    with pytest.raises(TypeError):
        registry.register(object())  # type: ignore[arg-type]
