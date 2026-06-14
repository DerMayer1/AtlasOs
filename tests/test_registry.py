import pytest

from atlas.domain.engines import build_registry
from atlas.domain.engines.impairment import ImpairmentEngine
from atlas.domain.engines.macro_monitor import MacroMonitorEngine
from atlas.platform.runtime.registry import EngineRegistry


def test_register_and_get():
    registry = EngineRegistry()
    engine = ImpairmentEngine()
    registry.register(engine)
    assert registry.get("impairment") is engine
    assert "impairment" in registry.capabilities()


def test_default_registry_contains_two_real_engines():
    registry = build_registry()
    assert set(registry.capabilities()) == {"impairment", "macro_monitor"}
    assert isinstance(registry.get("macro_monitor"), MacroMonitorEngine)


def test_duplicate_rejected():
    registry = EngineRegistry()
    registry.register(ImpairmentEngine())
    with pytest.raises(ValueError, match="already registered"):
        registry.register(ImpairmentEngine())


def test_unknown_engine_lists_available():
    registry = EngineRegistry()
    registry.register(ImpairmentEngine())
    with pytest.raises(KeyError, match="impairment"):
        registry.get("does_not_exist")


def test_non_worker_rejected():
    registry = EngineRegistry()
    with pytest.raises(TypeError):
        registry.register(object())  # type: ignore[arg-type]
