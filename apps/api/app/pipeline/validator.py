"""
LLM Output Validator
Validates and clamps structured outputs from LLM stages before they
are stored or passed downstream. Prevents malformed data from
propagating through the pipeline.
"""
from __future__ import annotations

import logging

from app.pipeline.context import (
    Competitor,
    Gap,
    PositioningEntity,
    PositioningMap,
    Recommendation,
)

logger = logging.getLogger(__name__)

VALID_COMPETITOR_TYPES = {"direct", "indirect", "substitute", "adjacent", "future"}
VALID_THREAT_LEVELS = {"low", "medium", "high"}
VALID_REC_TYPES = {"Reposition", "Vertically Focus", "Category Create", "Competitive Response"}


def clamp(value: float, lo: float = -1.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, value))


def validate_competitors(competitors: list[Competitor]) -> list[Competitor]:
    valid = []
    for c in competitors:
        if not c.name or not c.name.strip():
            logger.warning("[Validator] Skipping competitor with empty name")
            continue
        if c.type not in VALID_COMPETITOR_TYPES:
            logger.warning(f"[Validator] Invalid competitor type '{c.type}' for {c.name} — defaulting to 'indirect'")
            c.type = "indirect"
        if c.threat_level not in VALID_THREAT_LEVELS:
            logger.warning(f"[Validator] Invalid threat_level '{c.threat_level}' for {c.name} — defaulting to 'medium'")
            c.threat_level = "medium"
        valid.append(c)

    # Deduplicate by lowercased name
    seen: set[str] = set()
    deduped = []
    for c in valid:
        key = c.name.lower().strip()
        if key not in seen:
            seen.add(key)
            deduped.append(c)
        else:
            logger.debug(f"[Validator] Duplicate competitor removed: {c.name}")

    return deduped


def validate_positioning_map(pm: PositioningMap) -> PositioningMap:
    for entity in pm.entities:
        original_x, original_y = entity.x, entity.y
        entity.x = clamp(entity.x)
        entity.y = clamp(entity.y)
        if entity.x != original_x or entity.y != original_y:
            logger.warning(
                f"[Validator] Clamped coordinates for '{entity.name}': "
                f"({original_x:.2f}, {original_y:.2f}) -> ({entity.x:.2f}, {entity.y:.2f})"
            )
    return pm


def validate_gaps(gaps: list[Gap]) -> list[Gap]:
    return [g for g in gaps if g.description and g.description.strip()]


def validate_recommendations(recs: list[Recommendation]) -> list[Recommendation]:
    valid = []
    for r in recs:
        if r.type not in VALID_REC_TYPES:
            logger.warning(f"[Validator] Unknown recommendation type '{r.type}' — keeping as-is")
        if r.description and r.description.strip():
            valid.append(r)
    return valid[:3]  # Hard cap at 3 per spec
