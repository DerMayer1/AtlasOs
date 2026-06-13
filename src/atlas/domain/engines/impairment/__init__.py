from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from atlas.domain.engines.impairment.engine import ImpairmentEngine

__all__ = ["ImpairmentEngine"]


def __getattr__(name: str):
    if name == "ImpairmentEngine":
        from atlas.domain.engines.impairment.engine import ImpairmentEngine

        return ImpairmentEngine
    raise AttributeError(name)
