"""Citation parsing and validation (PRD R7, the killer feature).

Citation syntax (resolves PRD Q1): ``[<artifact_id>:<locator>]`` where
``artifact_id`` is ``<run_id>/<filename>`` and the locator addresses a value:
  - CSV : ``<column>@<row_key>``  e.g. ``p_impairment@Beta Logistics``
  - JSON: ``<dot.path.key>``      e.g. ``portfolio_mean_p_impairment``

A narrative is valid iff:
  1. every citation resolves to a real artifact + locator, and
  2. every figure attached to a citation equals the resolved value, and
  3. no orphan figures remain — a number not backed by a citation.

The narrator is instructed to write each quantitative claim as
``<number> [<artifact_id>:<locator>]``.
"""

from __future__ import annotations

import json
import math
import re
from pathlib import Path

import pandas as pd

from atlas.agent.schemas import Citation, CitationReport
from atlas.platform.audit.artifacts import ArtifactStore

# number (optional %) immediately followed by a citation -> a backed claim
_CLAIM_RE = re.compile(r"(-?\d+(?:\.\d+)?)\s*(%?)\s*\[([^\[\]:]+):([^\[\]]+)\]")
# any citation token (to catch unattached / broken ones)
_CITATION_RE = re.compile(r"\[([^\[\]:]+):([^\[\]]+)\]")
# a "risk figure": a decimal or a percentage. Integers (e.g. years) are ignored
# on purpose to avoid flagging "2008" as a claim.
_FIGURE_RE = re.compile(r"\d+\.\d+\s*%?|\d+\s*%")

_TOL = 5e-3  # narratives round to ~1 decimal place


def _values_match(claimed: float, is_pct: bool, resolved: float) -> bool:
    candidates = [claimed, claimed / 100.0, claimed * 100.0]
    if is_pct:
        candidates = [claimed / 100.0]
    return any(math.isclose(c, resolved, rel_tol=1e-2, abs_tol=_TOL) for c in candidates)


def resolve_value(store: ArtifactStore, artifact_id: str, locator: str) -> float:
    """Look up the numeric value a citation points at. Raises on any failure."""
    path: Path = store.open_path(artifact_id)
    if path.suffix == ".json":
        data = json.loads(path.read_text())
        for key in locator.split("."):
            data = data[key]
        return float(data)
    if path.suffix == ".csv":
        if "@" not in locator:
            raise ValueError(f"CSV locator must be 'column@row_key', got {locator!r}")
        column, row_key = locator.split("@", 1)
        df = pd.read_csv(path)
        key_col = df.columns[0]
        match = df[df[key_col].astype(str) == row_key]
        if match.empty:
            raise KeyError(f"row {row_key!r} not found in {artifact_id}")
        return float(match.iloc[0][column])
    raise ValueError(f"unsupported artifact type for citation: {path.suffix}")


def validate(narrative: str, store: ArtifactStore) -> CitationReport:
    citations: list[Citation] = []
    consumed_spans: list[tuple[int, int]] = []

    # 1. figure + citation pairs (backed claims)
    for m in _CLAIM_RE.finditer(narrative):
        claimed = float(m.group(1))
        is_pct = m.group(2) == "%"
        artifact_id, locator = m.group(3).strip(), m.group(4).strip()
        cit = Citation(raw=m.group(0), artifact_id=artifact_id, locator=locator,
                       claimed_value=claimed)
        try:
            resolved = resolve_value(store, artifact_id, locator)
            cit.resolved_value = resolved
            if _values_match(claimed, is_pct, resolved):
                cit.ok = True
            else:
                cit.detail = f"claimed {claimed}{'%' if is_pct else ''} != artifact {resolved}"
        except Exception as exc:
            cit.detail = f"unresolved: {type(exc).__name__}: {exc}"
        citations.append(cit)
        consumed_spans.append(m.span())

    # 2. citations not attached to a figure: still must resolve, but back nothing
    for m in _CITATION_RE.finditer(narrative):
        if any(s <= m.start() < e for s, e in consumed_spans):
            continue
        artifact_id, locator = m.group(1).strip(), m.group(2).strip()
        cit = Citation(raw=m.group(0), artifact_id=artifact_id, locator=locator)
        try:
            cit.resolved_value = resolve_value(store, artifact_id, locator)
            cit.ok = True
        except Exception as exc:
            cit.detail = f"unresolved: {type(exc).__name__}: {exc}"
        citations.append(cit)
        consumed_spans.append(m.span())

    # 3. orphan figures: blank out everything already consumed, scan the rest
    masked = list(narrative)
    for start, end in consumed_spans:
        for i in range(start, end):
            masked[i] = " "
    residual = "".join(masked)
    orphans = [m.group(0).strip() for m in _FIGURE_RE.finditer(residual)]

    return CitationReport(citations=citations, orphan_claims=orphans)
