from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class CompanyInput:
    company_name: str
    website_url: str
    description: str
    target_market: str | None = None
    known_competitors: list[str] = field(default_factory=list)
    analysis_depth: str = "standard"  # quick | standard | deep


@dataclass
class Category:
    label: str
    definition: str


@dataclass
class Competitor:
    name: str
    website: str | None
    type: str  # direct | indirect | substitute | adjacent | future
    threat_level: str  # low | medium | high
    summary: str
    positioning: str


@dataclass
class PositioningEntity:
    name: str
    x: float
    y: float
    is_subject: bool = False


@dataclass
class PositioningMap:
    x_axis: dict[str, str]  # {label, low, high}
    y_axis: dict[str, str]  # {label, low, high}
    entities: list[PositioningEntity]


@dataclass
class Gap:
    description: str
    addressability: str
    risk: str


@dataclass
class Recommendation:
    type: str
    description: str
    impact: str
    risk: str


@dataclass
class PipelineContext:
    """
    Shared state passed sequentially through all 8 pipeline stages.
    Each stage reads from and writes to this object.
    No stage mutates another stage's output.
    """
    input: CompanyInput

    # Stage outputs — populated as pipeline progresses
    raw_text: str = ""                          # Stage 1
    category: Category | None = None            # Stage 2
    search_results: list[dict[str, Any]] = field(default_factory=list)   # Stage 3
    competitors: list[Competitor] = field(default_factory=list)          # Stage 4
    positioning_map: PositioningMap | None = None                        # Stage 5
    gaps: list[Gap] = field(default_factory=list)                        # Stage 6
    recommendations: list[Recommendation] = field(default_factory=list)  # Stage 7
    memo_markdown: str = ""                     # Stage 8

    # Execution metadata
    current_stage: int = 0
    errors: list[dict[str, Any]] = field(default_factory=list)

    def record_error(self, stage: int, name: str, error: str) -> None:
        self.errors.append({"stage": stage, "name": name, "error": error})
