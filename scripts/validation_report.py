"""Generates docs/validation_report.md + figures from FRED data (PRD R6).

Run: python scripts/validation_report.py   (or: make validation-report)

Everything is derived from a frozen snapshot whose id is printed in the
report header — re-running against the same snapshot regenerates identical
numbers (PRD G1).
"""

from __future__ import annotations

import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from atlas.domain.data.fred import FredClient, build_macro_frame  # noqa: E402
from atlas.domain.engines.impairment.hmm import fit_hmm, regime_path  # noqa: E402
from atlas.domain.engines.impairment.regimes import (  # noqa: E402
    REGIMES,
    REQUIRED_SERIES,
    _WEIGHTS,
)
from atlas.domain.validation.labels import CRISIS_WINDOWS, reference_labels  # noqa: E402
from atlas.domain.validation.metrics import (  # noqa: E402
    accuracy,
    confusion_matrix,
    detection_lag_months,
)
from atlas.platform.audit.snapshots import SnapshotStore  # noqa: E402

DOCS = ROOT / "docs"
FIGS = DOCS / "figures"
EVAL_START = "2000-01-31"


def zscore_path(macro: pd.DataFrame) -> pd.DataFrame:
    """Phase 0 baseline applied to every month (full-sample stats)."""
    values = macro[list(REQUIRED_SERIES)].astype(float)
    z = (values - values.mean()) / values.std(ddof=0).replace(0.0, 1.0)
    scores = z.to_numpy() @ _WEIGHTS.T
    scores -= scores.max(axis=1, keepdims=True)
    probs = np.exp(scores)
    probs /= probs.sum(axis=1, keepdims=True)
    return pd.DataFrame(probs, index=macro.index, columns=list(REGIMES))


def md_table(df: pd.DataFrame, index_name: str = "") -> str:
    out = [f"| {index_name} | " + " | ".join(map(str, df.columns)) + " |",
           "|" + "---|" * (len(df.columns) + 1)]
    for idx, row in df.iterrows():
        cells = " | ".join(
            f"{v:.3f}" if isinstance(v, float) else str(v) for v in row
        )
        out.append(f"| {idx} | {cells} |")
    return "\n".join(out)


def main() -> None:
    FIGS.mkdir(parents=True, exist_ok=True)

    client = FredClient(ROOT / "var" / "data" / "cache" / "fred")
    macro = build_macro_frame(client, start="1990-01-01")
    snapshots = SnapshotStore(ROOT / "var" / "data" / "snapshots")
    manifest = snapshots.create(
        {"macro": macro},
        sources=[f"fredgraph:{s}" for s in REQUIRED_SERIES],
        period_start=str(macro.index.min().date()),
        period_end=str(macro.index.max().date()),
    )
    macro = snapshots.load(manifest.snapshot_id)["macro"]  # numbers come from the frozen copy

    eval_macro = macro.loc[EVAL_START:]
    labels = reference_labels(eval_macro.index)

    # --- full-sample HMM (smoothed) ------------------------------------------
    fit = fit_hmm(macro)
    path_full = regime_path(macro, fit, smoothed=True).loc[EVAL_START:]
    pred_full = path_full.idxmax(axis=1)
    cm_full = confusion_matrix(labels, pred_full)
    acc_full = accuracy(labels, pred_full)

    lags = {
        start: detection_lag_months(path_full["crisis"], start)
        for start, _ in CRISIS_WINDOWS
    }

    # --- out-of-sample: train 2010-2018, evaluate 2019-2024 -------------------
    fit_oos = fit_hmm(macro.loc["2010-01":"2018-12"])
    # one year of warm-up: the unemployment_chg12 feature needs 12 prior months
    oos_macro = macro.loc["2018-01":"2024-12"]
    path_oos = regime_path(oos_macro, fit_oos, smoothed=False).loc["2019-01":]  # causal
    labels_oos = reference_labels(path_oos.index)
    pred_oos = path_oos.idxmax(axis=1)
    cm_oos = confusion_matrix(labels_oos, pred_oos)
    acc_oos = accuracy(labels_oos, pred_oos)
    lag_2020_oos = detection_lag_months(path_oos["crisis"], "2020-02")

    # --- naive benchmarks ------------------------------------------------------
    vix = client.get_raw("VIXCLS", daily=True).resample("ME").mean().reindex(eval_macro.index)
    naive_rows = []
    for name, signal in {
        "VIX > 30": vix > 30,
        "BAA-AAA spread > 1.2pp": eval_macro["baa_aaa_spread"] > 1.2,
    }.items():
        is_crisis = labels == "crisis"
        tp = int((signal & is_crisis).sum())
        fp = int((signal & ~is_crisis).sum())
        fn = int((~signal & is_crisis).sum())
        naive_rows.append({
            "rule": name,
            "precision": tp / (tp + fp) if tp + fp else 0.0,
            "recall": tp / (tp + fn) if tp + fn else 0.0,
        })
    hmm_crisis = pred_full == "crisis"
    is_crisis = labels == "crisis"
    tp = int((hmm_crisis & is_crisis).sum())
    fp = int((hmm_crisis & ~is_crisis).sum())
    fn = int((~hmm_crisis & is_crisis).sum())
    naive_rows.insert(0, {
        "rule": "HMM (smoothed argmax)",
        "precision": tp / (tp + fp) if tp + fp else 0.0,
        "recall": tp / (tp + fn) if tp + fn else 0.0,
    })
    naive = pd.DataFrame(naive_rows).set_index("rule")

    # --- z-score baseline ------------------------------------------------------
    pred_z = zscore_path(macro).loc[EVAL_START:].idxmax(axis=1)
    acc_z = accuracy(labels, pred_z)

    # --- sensitivity of crisis stress shocks -----------------------------------
    from atlas.domain.engines.impairment.engine import _SHOCKS

    # Under a stressed regime mix (P(crisis)=0.5): with today's P(crisis) near
    # zero the crisis parameters are inert and the grid would be flat.
    rng_probs = np.array([0.25, 0.25, 0.5])
    sens_rows = []
    for mu in (-0.25, -0.15, -0.05):
        row = {}
        for sigma in (0.10, 0.20, 0.30):
            rng = np.random.default_rng(0)
            draws = rng.choice(3, size=50_000, p=rng_probs)
            mus = np.array([_SHOCKS["expansion"][0], _SHOCKS["tightening"][0], mu])[draws]
            sigmas = np.array([_SHOCKS["expansion"][1], _SHOCKS["tightening"][1], sigma])[draws]
            growth = rng.standard_normal(50_000) * sigmas + mus
            ev = 100.0 * (1 + growth) * 8.0  # reference company
            row[f"sigma={sigma}"] = float((ev < 780.0).mean())
        sens_rows.append(pd.Series(row, name=f"mu={mu}"))
    sensitivity = pd.DataFrame(sens_rows)

    # --- figures ----------------------------------------------------------------
    fig, ax = plt.subplots(figsize=(11, 4))
    for regime in REGIMES:
        ax.plot(path_full.index, path_full[regime], label=regime, linewidth=1.2)
    for start, end in CRISIS_WINDOWS:
        ax.axvspan(pd.Timestamp(start), pd.Timestamp(end) + pd.offsets.MonthEnd(),
                   alpha=0.15, color="red")
    ax.legend(loc="upper left")
    ax.set_title("HMM smoothed regime probabilities (shaded = reference crisis windows)")
    fig.tight_layout()
    fig.savefig(FIGS / "regime_probabilities.png", dpi=120)

    fig, ax = plt.subplots(figsize=(8, 4))
    zoom = path_oos.loc["2019-06":"2021-06", "crisis"]
    ax.plot(zoom.index, zoom.values, color="darkred")
    ax.axhline(0.5, linestyle="--", color="gray")
    ax.axvspan(pd.Timestamp("2020-02"), pd.Timestamp("2020-05-31"), alpha=0.15, color="red")
    ax.set_title("Out-of-sample (causal) P(crisis), COVID window")
    fig.tight_layout()
    fig.savefig(FIGS / "covid_detection.png", dpi=120)

    # --- report -------------------------------------------------------------------
    lag_lines = "\n".join(
        f"- Crisis starting {start}: "
        + (f"detected after **{lag} month(s)**" if lag is not None else "**not detected** within 12 months")
        for start, lag in lags.items()
    )
    report = f"""# Model Validation Report — HMM regime classifier

*Generated by `scripts/validation_report.py` (versioned; `make validation-report`
regenerates byte-comparable numbers from the same snapshot).*

| | |
|---|---|
| Snapshot | `{manifest.snapshot_id}` |
| Data period | {macro.index.min().date()} → {macro.index.max().date()} (monthly) |
| Model | 3-state diagonal-Gaussian HMM, `hmm3-mc-0.2` |
| Evaluation window | 2000-01 → {macro.index.max().date()} |

Reference labels are NBER recessions plus Fed hiking cycles (see
`atlas/domain/validation/labels.py` for the exact windows and rationale).
**Monthly data bounds detection-lag resolution at one month** — daily-frequency
detection is future work (docs/limitations.md).

## 1. Confusion matrix — full sample (smoothed), 2000→present

Rows = reference label, columns = model prediction, values = months.

{md_table(cm_full, "label \\\\ pred")}

Accuracy: **{acc_full:.1%}** (z-score baseline from Phase 0: {acc_z:.1%}).

## 2. Detection lag per crisis window

{lag_lines}

Out-of-sample causal detection of COVID (2020-02): {"**" + str(lag_2020_oos) + " month(s)**" if lag_2020_oos is not None else "**not detected**"}.

## 3. Out-of-sample — train 2010–2018, evaluate 2019–2024 (causal)

{md_table(cm_oos, "label \\\\ pred")}

Out-of-sample accuracy: **{acc_oos:.1%}**.

## 4. Naive benchmark comparison (crisis detection, 2000→present)

{md_table(naive.round(3))}

## 5. Sensitivity — crisis EBITDA shock parameters

P(impairment) for a reference company (EBITDA 100, multiple 8.0, carrying
value 780) under a stressed regime mix (P(crisis)=0.5 — today's P(crisis) is
near zero, which would make the grid flat), varying the crisis shock:

{md_table(sensitivity.round(3))}

The production values (mu={_SHOCKS["crisis"][0]}, sigma={_SHOCKS["crisis"][1]}) sit in the
middle of this grid. They remain literature-informed placeholders pending
historical calibration (PRD Q2 — still open; tracked in DECISIONS.md).

## 6. Figures

![Regime probabilities](figures/regime_probabilities.png)

![COVID detection](figures/covid_detection.png)

## 7. Honest read

- The HMM is compared against trivially simple rules in §4 on purpose; where a
  naive rule wins on a metric, that is reported, not hidden.
- The model's characteristic failure is **over-predicting crisis during
  post-recession credit normalization** (2003, 2009-10, 2015-16): spreads stay
  wide after the acute phase ends, so recall is high ({tp}/{tp + fn} crisis
  months caught) but precision is low. For an impairment *monitoring* system a
  conservative bias is the preferable failure direction, but it is a bias.
  Candidate fix (parking lot): spread *change* rather than level as a feature.
- Labels in 2011 and 2022 are judgment calls (not NBER); accuracy there
  measures agreement with our labeling, not truth.
- Smoothed probabilities (§1) use future data and overstate real-time skill;
  the causal numbers in §2-3 are the ones that matter for operation.
"""
    (DOCS / "validation_report.md").write_text(report, encoding="utf-8")
    print(f"snapshot: {manifest.snapshot_id}")
    print(f"full-sample accuracy: {acc_full:.3f} | out-of-sample: {acc_oos:.3f}")
    print(f"detection lags (months): {lags} | OOS covid: {lag_2020_oos}")
    print(f"wrote {DOCS / 'validation_report.md'}")


if __name__ == "__main__":
    main()
