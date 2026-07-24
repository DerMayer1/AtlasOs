"""Calibrate the per-regime EBITDA stress shocks from history (closes PRD Q2).

Method (a regime-dummy regression on earnings growth):
  1. Ingest US corporate profits (FRED `CP`, quarterly) as the earnings proxy
     and compute year-over-year growth.
  2. Label each quarter by the REFERENCE regime windows (NBER recessions + Fed
     hiking cycles, from atlas.domain.validation.labels) — NOT the model's own
     HMM classification. This is deliberate: calibrating the model's shock off
     the model's own (over-broad) crisis state is circular and, when tried,
     produced a positive crisis mean because the over-broad crisis state absorbs
     high-rebound recovery quarters. Real NBER crisis windows give the true
     earnings collapse.
  3. Estimate per regime the mean and std of earnings growth (a regime-dummy
     regression: the group mean is OLS on dummies, the within-group residual std
     is the dispersion).
  4. Write src/atlas/domain/engines/impairment/shock_calibration.json with the
     coefficients and full provenance (source series, n per regime).

Honest caveat recorded in the output and in docs/limitations.md: `CP` is an
AGGREGATE series, so its volatility understates single-company EBITDA
dispersion. The regime-conditional MEAN is well identified; the std is an
aggregate lower bound. Cross-sectional dispersion is future work.

Run: python scripts/calibrate_shocks.py   (or: make calibrate-shocks)
"""

from __future__ import annotations

import json
import sys
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import pandas as pd  # noqa: E402

from atlas.domain.data.fred import FredClient, build_macro_frame  # noqa: E402
from atlas.domain.engines.impairment.regimes import REGIMES  # noqa: E402
from atlas.domain.validation.labels import reference_labels  # noqa: E402
from atlas.platform.audit.snapshots import SnapshotStore  # noqa: E402

OUT_FILE = ROOT / "src" / "atlas" / "domain" / "engines" / "impairment" / "shock_calibration.json"
PROFITS_SERIES = "CP"  # Corporate Profits with IVA & CCAdj, quarterly, $bn (SAAR)
MIN_QUARTERS = 4  # below this a regime estimate is too thin to trust

# Documented priors, used only if a regime has too few historical quarters.
_PRIOR = {
    "expansion": (0.05, 0.08),
    "tightening": (-0.02, 0.12),
    "crisis": (-0.15, 0.20),
}

# Regime-conditional multiple re-rating. This is an explicit ASSUMPTION, not a
# calibration — there is no point-in-time market-multiple series to fit against,
# so this script cannot derive it. It is emitted here (rather than hardcoded in
# the engine) so the whole regime-parameter set lives in one provenance file and
# survives regeneration, with its non-calibrated status stated in the payload.
_MULTIPLE_COMPRESSION_ASSUMPTION = {
    "expansion": 0.04,
    "tightening": -0.12,
    "crisis": -0.30,
}


def main() -> None:
    cache = ROOT / "var" / "data" / "cache" / "fred"
    client = FredClient(cache)

    macro = build_macro_frame(client)
    snapshots = SnapshotStore(ROOT / "var" / "data" / "snapshots")
    manifest = snapshots.create({"macro": macro}, sources=["fredgraph:macro"])
    macro = snapshots.load(manifest.snapshot_id)["macro"]

    # reference (NBER+) regime per month, then dominant regime per quarter
    monthly_regime = reference_labels(macro.loc["2000-01-01":].index)
    quarterly_regime = monthly_regime.groupby(pd.Grouper(freq="QE")).agg(
        lambda s: s.value_counts().index[0] if len(s) else None
    )

    profits = client.get_raw(PROFITS_SERIES)
    growth = (profits.pct_change(4) * 100.0).rename("profit_yoy_pct")  # percent
    growth.index = growth.index.to_period("Q").to_timestamp("Q") + pd.offsets.QuarterEnd(0)

    df = pd.DataFrame({"regime": quarterly_regime}).join(growth, how="inner").dropna()

    shocks: dict[str, dict] = {}
    for regime in REGIMES:
        sub = df[df["regime"] == regime]["profit_yoy_pct"] / 100.0  # back to fraction
        n = int(len(sub))
        if n >= MIN_QUARTERS:
            mean, std, source = float(sub.mean()), float(sub.std(ddof=1)), "calibrated"
        else:
            mean, std, source = (*_PRIOR[regime], "prior (too few quarters)")
        shocks[regime] = {"mean": round(mean, 4), "std": round(std, 4),
                          "n_quarters": n, "source": source}

    payload = {
        "method": (
            "regime-dummy regression of CP YoY growth on REFERENCE (NBER+) regime "
            "windows; mean+std per regime"
        ),
        "snapshot_id": manifest.snapshot_id,
        "profits_series": PROFITS_SERIES,
        "data_period": [str(df.index.min().date()), str(df.index.max().date())],
        "generated_at": datetime.now(UTC).isoformat(),
        "caveat": (
            "CP is aggregate; its std understates single-company EBITDA dispersion. "
            "The regime-conditional mean is well identified; std is a lower bound."
        ),
        "shocks": shocks,
        "multiple_compression": {
            "method": (
                "Analyst assumption: regime-conditional EV/EBITDA multiple re-rating "
                "applied on top of the calibrated EBITDA shock. NOT calibrated from "
                "data — no point-in-time market-multiple series is ingested. This term "
                "is the dominant driver of modeled crisis severity (~95% of the mean "
                "crisis decline in recoverable value); see docs/limitations.md before "
                "treating crisis output as calibrated."
            ),
            **{
                regime: {"value": value, "source": "assumption"}
                for regime, value in _MULTIPLE_COMPRESSION_ASSUMPTION.items()
            },
        },
    }
    OUT_FILE.write_text(json.dumps(payload, indent=2) + "\n")

    print(f"snapshot: {manifest.snapshot_id}")
    for regime in REGIMES:
        s = shocks[regime]
        print(f"  {regime:11s} mean={s['mean']:+.3f} std={s['std']:.3f} "
              f"n={s['n_quarters']:3d} ({s['source']})")
    print(f"wrote {OUT_FILE.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
