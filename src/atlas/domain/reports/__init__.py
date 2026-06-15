"""Deterministic report builder: turns engine numbers into decisions.

Lives in the domain layer because it knows engine-specific metric keys and the
action rules. It never calculates a new number and never calls an LLM — it
selects, formats and cites figures the engines already produced (PRD §7.1).
"""

from atlas.domain.reports.builder import build_report
from atlas.domain.reports.models import Action, Citation, Figure, Report

__all__ = ["Action", "Citation", "Figure", "Report", "build_report"]
