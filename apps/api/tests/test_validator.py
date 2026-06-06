"""
Unit tests for LLM output validator.
"""
import pytest
from app.pipeline.context import Competitor, Gap, PositioningEntity, PositioningMap, Recommendation
from app.pipeline.validator import (
    clamp,
    validate_competitors,
    validate_gaps,
    validate_positioning_map,
    validate_recommendations,
)


class TestClamp:
    def test_clamps_above_max(self):
        assert clamp(1.5) == 1.0

    def test_clamps_below_min(self):
        assert clamp(-2.0) == -1.0

    def test_passes_valid_value(self):
        assert clamp(0.5) == 0.5


class TestValidateCompetitors:
    def _make(self, name="Jira", type_="direct", threat="high"):
        return Competitor(name=name, website=None, type=type_, threat_level=threat, summary="s", positioning="p")

    def test_removes_invalid_type(self):
        c = self._make(type_="unknown")
        result = validate_competitors([c])
        assert result[0].type == "indirect"

    def test_removes_invalid_threat(self):
        c = self._make(threat="critical")
        result = validate_competitors([c])
        assert result[0].threat_level == "medium"

    def test_deduplicates_by_name(self):
        c1 = self._make(name="Jira")
        c2 = self._make(name="jira")  # same, different case
        result = validate_competitors([c1, c2])
        assert len(result) == 1

    def test_removes_empty_name(self):
        c = self._make(name="")
        result = validate_competitors([c])
        assert len(result) == 0


class TestValidatePositioningMap:
    def _make_map(self, x, y):
        return PositioningMap(
            x_axis={"label": "X", "low": "low", "high": "high"},
            y_axis={"label": "Y", "low": "low", "high": "high"},
            entities=[PositioningEntity(name="TestCo", x=x, y=y, is_subject=True)],
        )

    def test_clamps_x_above_1(self):
        pm = validate_positioning_map(self._make_map(1.8, 0.5))
        assert pm.entities[0].x == 1.0

    def test_clamps_y_below_minus_1(self):
        pm = validate_positioning_map(self._make_map(0.5, -3.0))
        assert pm.entities[0].y == -1.0

    def test_valid_coordinates_unchanged(self):
        pm = validate_positioning_map(self._make_map(0.5, -0.3))
        assert pm.entities[0].x == 0.5
        assert pm.entities[0].y == -0.3


class TestValidateRecommendations:
    def _make(self, type_="Reposition", desc="Do this"):
        return Recommendation(type=type_, description=desc, impact="high", risk="low")

    def test_caps_at_three(self):
        recs = [self._make() for _ in range(5)]
        result = validate_recommendations(recs)
        assert len(result) == 3

    def test_removes_empty_description(self):
        recs = [self._make(desc=""), self._make(desc="Valid")]
        result = validate_recommendations(recs)
        assert len(result) == 1
        assert result[0].description == "Valid"
