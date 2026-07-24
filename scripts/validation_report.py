"""Generate the causal walk-forward model validation report.

Run: python scripts/validation_report.py

The primary score is always out-of-sample. Each fold fits model parameters and
thresholds using only months before its test period. Full-sample smoothed HMM
results are deliberately not used as headline evidence.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from atlas.domain.data.fred import AlfredClient, FredClient, build_macro_frame  # noqa: E402
from atlas.domain.engines.impairment.engine import _SHOCKS  # noqa: E402
from atlas.domain.validation.labels import (  # noqa: E402
    STRICT_CRISIS_WINDOWS,
    binary_crisis_labels,
)
from atlas.domain.validation.metrics import calibration_table  # noqa: E402
from atlas.domain.validation.walk_forward import (  # noqa: E402
    VIX_OVERRIDE_LEVEL,
    VIX_SCORE_CEILING,
    VIX_SCORE_FLOOR,
    run_walk_forward,
)
from atlas.platform.audit.snapshots import SnapshotStore  # noqa: E402

DOCS = ROOT / "docs"
FIGS = DOCS / "figures"


def md_table(df: pd.DataFrame, index_name: str = "") -> str:
    out = [
        f"| {index_name} | " + " | ".join(map(str, df.columns)) + " |",
        "|" + "---|" * (len(df.columns) + 1),
    ]
    for idx, row in df.iterrows():
        cells = " | ".join(
            f"{value:.3f}" if isinstance(value, (float, np.floating)) else str(value)
            for value in row
        )
        out.append(f"| {idx} | {cells} |")
    return "\n".join(out)


def _event_lags(predictions: pd.DataFrame) -> dict[str, int | None]:
    lags: dict[str, int | None] = {}
    for start, _ in STRICT_CRISIS_WINDOWS:
        if start < "2000-01":
            continue
        start_ts = pd.Period(start, freq="M").to_timestamp(how="end").normalize()
        window = predictions.loc[predictions.index >= start_ts].iloc[:12]
        hits = window[window["hybrid_prediction"] == 1]
        if hits.empty:
            lags[start] = None
        else:
            first = hits.index[0]
            lags[start] = (first.year - start_ts.year) * 12 + first.month - start_ts.month
    return lags


def _sensitivity_table() -> pd.DataFrame:
    regime_mix = np.array([0.25, 0.25, 0.5])
    rows = []
    for mean in (-0.25, -0.15, -0.05):
        row = {}
        for std in (0.10, 0.20, 0.30):
            rng = np.random.default_rng(0)
            draws = rng.choice(3, size=50_000, p=regime_mix)
            means = np.array([_SHOCKS["expansion"][0], _SHOCKS["tightening"][0], mean])[draws]
            stds = np.array([_SHOCKS["expansion"][1], _SHOCKS["tightening"][1], std])[draws]
            growth = rng.standard_normal(50_000) * stds + means
            enterprise_value = 100.0 * (1.0 + growth) * 8.0
            row[f"sigma={std}"] = float((enterprise_value < 780.0).mean())
        rows.append(pd.Series(row, name=f"mu={mean}"))
    return pd.DataFrame(rows)


def main() -> None:
    FIGS.mkdir(parents=True, exist_ok=True)

    offline = os.getenv("ATLAS_VALIDATION_OFFLINE", "").lower() in {"1", "true", "yes"}
    data_source = os.getenv("ATLAS_VALIDATION_DATA_SOURCE", "alfred").lower()
    if data_source == "alfred":
        client = AlfredClient(
            ROOT / "var" / "data" / "cache" / "alfred",
            api_key=os.getenv("ATLAS_FRED_API_KEY", ""),
            offline=offline,
        )
        source_label = "ALFRED initial releases (point-in-time)"
        source_id = "alfred:initial-release:macro+vix"
        temporal_note = (
            "Every macro observation is its ALFRED initial release (`output_type=4`), "
            "so later revisions cannot leak into historical folds."
        )
    elif data_source == "fred":
        client = FredClient(ROOT / "var" / "data" / "cache" / "fred", offline=offline)
        source_label = "Revised FRED history (provisional development run)"
        source_id = "fredgraph:revised:macro+vix"
        temporal_note = (
            "This provisional run uses revised FRED history. Set "
            "`ATLAS_VALIDATION_DATA_SOURCE=alfred` with `ATLAS_FRED_API_KEY` before "
            "treating the metrics as release evidence."
        )
    else:
        raise ValueError("ATLAS_VALIDATION_DATA_SOURCE must be 'alfred' or 'fred'")
    macro = build_macro_frame(client, start="1990-01-01")
    snapshots = SnapshotStore(ROOT / "var" / "data" / "snapshots")
    manifest = snapshots.create(
        {"macro": macro},
        sources=[source_id],
        period_start=str(macro.index.min().date()),
        period_end=str(macro.index.max().date()),
    )
    macro = snapshots.load(manifest.snapshot_id)["macro"]

    strict_labels = binary_crisis_labels(macro.index, definition="strict")
    stress_labels = binary_crisis_labels(macro.index, definition="stress")
    strict = run_walk_forward(macro, strict_labels)
    stress = run_walk_forward(macro, stress_labels)

    comparison_columns = [
        "precision",
        "recall",
        "f1",
        "pr_auc",
        "brier",
        "false_alerts_per_year",
    ]
    comparison = strict.aggregate_metrics[comparison_columns].round(3)

    # Per-fold results carry an explicit `model` column. An earlier version
    # pivoted these and dropped the model level from the column names, which
    # published logistic fold numbers directly beneath a hybrid headline.
    fold_frame = strict.fold_metrics.reset_index()
    fold_frame["crisis_months"] = (fold_frame["tp"] + fold_frame["fn"]).astype(int)
    fold_table = (
        fold_frame[fold_frame["model"].isin(("hybrid", "logistic"))]
        .sort_values(["fold", "model"])
        .set_index("fold")[
            ["model", "precision", "recall", "f1", "crisis_months", "false_alerts_per_year"]
        ]
        .round(3)
    )

    # Under the strict NBER target some folds contain no crisis months at all.
    # Their precision/recall are undefined rather than zero, and only their
    # false-alert burden is informative. Saying so is the difference between a
    # fold that failed and a fold that had nothing to find.
    hybrid_folds = fold_frame[fold_frame["model"] == "hybrid"].set_index("fold")
    scored = hybrid_folds[hybrid_folds["crisis_months"] > 0]
    empty_folds = sorted(hybrid_folds.index[hybrid_folds["crisis_months"] == 0])
    missed_folds = sorted(scored.index[scored["recall"] == 0.0])
    detected_folds = sorted(scored.index[scored["recall"] > 0.0])
    total_crisis_months = int(scored["crisis_months"].sum())
    largest_fold = scored["crisis_months"].idxmax()
    largest_share = int(scored["crisis_months"].max())

    target_sensitivity = pd.DataFrame(
        {
            "strict_nber": strict.aggregate_metrics.loc["hybrid", comparison_columns],
            "broader_stress": stress.aggregate_metrics.loc["hybrid", comparison_columns],
        }
    ).T.round(3)

    calibration = calibration_table(
        strict.predictions["target"], strict.predictions["hybrid_probability"]
    ).round(3)
    top_features = (
        strict.coefficients.abs()
        .mean()
        .sort_values(ascending=False)
        .head(10)
        .rename("mean_abs_coef")
    )
    event_lags = _event_lags(strict.predictions)
    sensitivity = _sensitivity_table().round(3)

    fig, ax = plt.subplots(figsize=(11, 4))
    probability_series = strict.predictions["hybrid_probability"].reindex(
        pd.date_range(
            strict.predictions.index.min(),
            strict.predictions.index.max(),
            freq="ME",
        )
    )
    ax.plot(
        probability_series.index,
        probability_series,
        label="walk-forward hybrid P(crisis)",
        color="darkred",
        linewidth=1.2,
    )
    for start, end in STRICT_CRISIS_WINDOWS:
        if pd.Timestamp(end) < probability_series.index.min():
            continue
        ax.axvspan(
            pd.Timestamp(start),
            pd.Timestamp(end) + pd.offsets.MonthEnd(),
            alpha=0.15,
            color="red",
        )
    ax.set_ylim(0, 1)
    ax.legend(loc="upper left")
    ax.set_title("Causal out-of-sample crisis probabilities")
    fig.tight_layout()
    fig.savefig(FIGS / "walk_forward_crisis_probabilities.png", dpi=120)
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(5, 5))
    plotted = calibration.dropna()
    ax.plot([0, 1], [0, 1], linestyle="--", color="gray", label="perfect calibration")
    ax.scatter(
        plotted["mean_probability"],
        plotted["crisis_rate"],
        s=30 + plotted["observations"] * 2,
        color="darkred",
        label="logistic",
    )
    for _, row in plotted.iterrows():
        offset = (4, -14) if row["crisis_rate"] > 0.9 else (4, 4)
        ax.annotate(
            f"n={int(row['observations'])}",
            (row["mean_probability"], row["crisis_rate"]),
            xytext=offset,
            textcoords="offset points",
            fontsize=8,
        )
    ax.set(
        xlim=(0, 1),
        ylim=(-0.02, 1.05),
        xlabel="Mean predicted probability",
        ylabel="Crisis rate",
    )
    ax.legend(loc="upper left")
    ax.set_title("Out-of-sample calibration")
    fig.tight_layout()
    fig.savefig(FIGS / "crisis_calibration.png", dpi=120)
    plt.close(fig)

    def _join(names: list[str]) -> str:
        return ", ".join(f"`{name}`" for name in names) if names else "none"

    fold_note = (
        f"Only {len(scored)} of {len(hybrid_folds)} folds contain labeled crisis "
        f"months under the strict NBER target. {_join(empty_folds)} contain none, "
        "so their precision and recall are undefined rather than zero — only "
        "their false-alert burden is meaningful.\n\n"
        f"Of the {len(scored)} scorable folds, the hybrid model detects at least "
        f"one crisis month in {_join(detected_folds)} and misses "
        f"{_join(missed_folds)} entirely. `{largest_fold}` supplies "
        f"{largest_share} of the {total_crisis_months} pooled crisis months, so "
        "the aggregate in section 1 is largely a statement about that single "
        "episode. With this few independent events, treat all three-decimal "
        "figures in this report as indicative, not precise."
    )

    lag_lines = "\n".join(
        f"- Crisis starting {start}: "
        + (
            f"detected after **{lag} month(s)**"
            if lag is not None
            else "**not detected** within 12 months"
        )
        for start, lag in event_lags.items()
    )

    report = f"""# Model Validation Report - Causal Crisis Classifier

*Generated by `scripts/validation_report.py`. The headline results are expanding
walk-forward tests; no model parameter or threshold is fitted on a test period.
Section 1 pools all folds — section 2 reports each episode separately and is the
table to read for detection skill.*

| | |
|---|---|
| Snapshot | `{manifest.snapshot_id}` |
| Data period | {macro.index.min().date()} to {macro.index.max().date()} (monthly) |
| Data source | {source_label} |
| Primary target | Strict NBER recession months, contemporaneous detection |
| Primary model | Causal logistic score with fixed VIX stress override |
| Operating rule | Maximize training precision subject to at least 60% training recall |

## 1. Primary out-of-sample comparison

All models below are scored on the same walk-forward test months. HMM and
logistic thresholds are selected only from each fold's training history.

{md_table(comparison, "model")}

`false_alerts_per_year` is the operational false-positive burden. `pr_auc` is
preferred over overall accuracy because crisis months are rare. The Brier score
measures probability quality; lower is better.

**These figures pool every fold's test months into one sample.** Pooling hides
which episodes the model actually caught, and the episodes are not
interchangeable. Read section 2 before quoting anything here.

## 2. Walk-forward folds

Per-fold results for the headline model and the logistic baseline. The `model`
column is explicit: these rows are not a decomposition of a single row above.

{md_table(fold_table, "fold")}

Folds cover dot-com, GFC, 2011 stress, COVID and the recent post-COVID period.

{fold_note}

## 3. Detection lag

{lag_lines}

Detection is monthly. A zero-month result means the model crossed its
training-selected threshold during the first labeled crisis month.

## 4. Probability calibration

{md_table(calibration, "probability bin")}

![Out-of-sample calibration](figures/crisis_calibration.png)

## 5. Target-definition sensitivity

{md_table(target_sensitivity, "target")}

`strict_nber` is the primary benchmark. `broader_stress` includes extended
credit-stress periods and 2011. Publishing both prevents label choices from
being mistaken for model improvement.

## 6. Most influential standardized features

{md_table(top_features.to_frame(), "feature")}

These are mean absolute coefficients across folds. They describe model use, not
causal economic importance.

## 7. Temporal controls

- CPI and unemployment are delayed by one month in the backtest.
- Every feature is backward-looking.
- Standardization, HMM fitting, logistic fitting and threshold selection happen
  inside each training fold.
- No model parameter or threshold is *fitted* on a test period.
- The VIX override levels ({VIX_SCORE_FLOOR:.0f}/{VIX_OVERRIDE_LEVEL:.0f}/{VIX_SCORE_CEILING:.0f})
  and the credit-spread rule are fixed constants, not fold-fitted values. They
  were nonetheless chosen by an author who has seen the full history, so the
  hybrid and the two rule baselines carry hindsight that the logistic model does
  not. The logistic row is the cleaner out-of-sample claim.
- {temporal_note}

## 8. Crisis probabilities

![Walk-forward crisis probabilities](figures/walk_forward_crisis_probabilities.png)

## 9. Impairment shock sensitivity

P(impairment) for a reference company under a stressed regime mix, varying the
crisis EBITDA shock:

{md_table(sensitivity)}

Production crisis values remain calibrated from corporate-profit history:
mu={_SHOCKS["crisis"][0]:.3f}, sigma={_SHOCKS["crisis"][1]:.3f}. This calibration
is separate from crisis-classifier validation.

## 10. Interpretation

- The hybrid classifier combines the calibrated logistic score with a fixed,
  causal VIX stress override. HMM remains a feature and benchmark.
- Episode-level detection (section 2) is the honest read of skill. The pooled
  aggregate in section 1 is reported for baseline comparison, not as a summary
  of how the model behaves on a new crisis.
- This report does not claim deployable forecasting skill. It establishes a
  leakage-controlled baseline that future feature and model changes must beat.
"""
    report_path = DOCS / "validation_report.md"
    report_path.write_text(report, encoding="utf-8")
    print(f"snapshot: {manifest.snapshot_id}")
    print(comparison.to_string())
    print(f"wrote {report_path}")


if __name__ == "__main__":
    main()
