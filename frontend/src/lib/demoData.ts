import type { Analysis, Portfolio, ReportDetail, ReportSummary } from "./schemas";

const now = "2026-06-16T02:00:00.000Z";

export const demoAnalyses: Analysis[] = [
  {
    job_id: "run_ic_92f4a1c8",
    portfolio_id: "pf_centurion_credit",
    portfolio_version_id: "ver_20260616",
    portfolio_name: "Atlas Strategic Credit",
    engine: "impairment",
    snapshot_id: "snap_20260616_macro",
    status: "succeeded",
    portfolio_mean_p_impairment: 0.184,
    created_at: now,
    finished_at: now
  },
  {
    job_id: "run_macro_77b91d0e",
    portfolio_id: null,
    portfolio_version_id: null,
    portfolio_name: null,
    engine: "macro_monitor",
    snapshot_id: "snap_20260616_macro",
    status: "succeeded",
    macro_regime: "tightening",
    stress_index: 0.82,
    created_at: "2026-06-16T01:44:00.000Z",
    finished_at: "2026-06-16T01:44:02.000Z"
  },
  {
    job_id: "run_ic_58c7d20a",
    portfolio_id: "pf_global_special",
    portfolio_version_id: "ver_20260615",
    portfolio_name: "Global Special Situations",
    engine: "impairment",
    snapshot_id: "snap_20260615_macro",
    status: "succeeded",
    portfolio_mean_p_impairment: 0.116,
    created_at: "2026-06-15T20:18:00.000Z",
    finished_at: "2026-06-15T20:18:04.000Z"
  },
  {
    job_id: "run_ic_31a6e90b",
    portfolio_id: "pf_long_duration",
    portfolio_version_id: "ver_20260614",
    portfolio_name: "Long Duration Industrials",
    engine: "impairment",
    snapshot_id: "snap_20260614_macro",
    status: "succeeded",
    portfolio_mean_p_impairment: 0.092,
    created_at: "2026-06-14T18:32:00.000Z",
    finished_at: "2026-06-14T18:32:03.000Z"
  }
];

export const demoReports: ReportSummary[] = [
  {
    report_id: "rep_ic_92f4a1c8",
    analysis_id: "run_ic_92f4a1c8",
    engine: "impairment",
    headline: "Strategic Credit requires committee review as impairment risk rises to 18.4%.",
    action_count: 2,
    max_severity: "elevated",
    portfolio_id: "pf_centurion_credit",
    portfolio_name: "Atlas Strategic Credit",
    created_at: now
  },
  {
    report_id: "rep_ic_58c7d20a",
    analysis_id: "run_ic_58c7d20a",
    engine: "impairment",
    headline: "Special Situations remains inside mandate, with liquidity sensitivity watchlisted.",
    action_count: 1,
    max_severity: "watch",
    portfolio_id: "pf_global_special",
    portfolio_name: "Global Special Situations",
    created_at: "2026-06-15T20:20:00.000Z"
  }
];

export const demoReportDetails: Record<string, ReportDetail> = {
  run_ic_92f4a1c8: {
    report_id: "rep_ic_92f4a1c8",
    run_id: "run_ic_92f4a1c8",
    engine: "impairment",
    snapshot_id: "snap_20260616_macro",
    engine_version: "impairment.v1",
    model_version: "joint-portfolio.2026-06",
    headline: "Strategic Credit requires committee review as impairment risk rises to 18.4%.",
    previous_run_id: "run_ic_58c7d20a",
    key_figures: [
      {
        label: "Mean P(impairment)",
        value: "18.4%",
        severity: "elevated",
        citation: { artifact: "metrics.json", locator: "portfolio_mean_p_impairment" }
      },
      {
        label: "Companies",
        value: 6,
        severity: "info",
        citation: { artifact: "metrics.json", locator: "n_companies" }
      }
    ],
    risk_drivers: [
      {
        label: "Macro regime",
        value: "Tightening",
        severity: "watch",
        citation: { artifact: "macro_state.json", locator: "current_regime" }
      },
      {
        label: "Stress index",
        value: "0.82",
        severity: "watch",
        citation: { artifact: "macro_state.json", locator: "stress_index" }
      }
    ],
    actions: [
      {
        title: "Review valuation marks before next committee",
        severity: "elevated",
        rationale:
          "Portfolio impairment probability is above the internal review threshold and has moved materially versus the prior run.",
        citations: [{ artifact: "metrics.json", locator: "portfolio_mean_p_impairment" }]
      },
      {
        title: "Prepare liquidity sensitivity appendix",
        severity: "watch",
        rationale:
          "The macro monitor shows tightening conditions, so the report should include downside liquidity sensitivity before approval.",
        citations: [{ artifact: "macro_state.json", locator: "stress_index" }]
      }
    ]
  },
  run_ic_58c7d20a: {
    report_id: "rep_ic_58c7d20a",
    run_id: "run_ic_58c7d20a",
    engine: "impairment",
    snapshot_id: "snap_20260615_macro",
    engine_version: "impairment.v1",
    model_version: "joint-portfolio.2026-06",
    headline: "Special Situations remains inside mandate, with liquidity sensitivity watchlisted.",
    previous_run_id: null,
    key_figures: [
      {
        label: "Mean P(impairment)",
        value: "11.6%",
        severity: "watch",
        citation: { artifact: "metrics.json", locator: "portfolio_mean_p_impairment" }
      }
    ],
    risk_drivers: [
      {
        label: "Macro regime",
        value: "Expansion",
        severity: "info",
        citation: { artifact: "macro_state.json", locator: "current_regime" }
      }
    ],
    actions: [
      {
        title: "Keep liquidity sensitivity on watchlist",
        severity: "watch",
        rationale: "Risk remains below escalation threshold, but liquidity diagnostics justify monitoring.",
        citations: [{ artifact: "metrics.json", locator: "liquidity_gap_to_ebitda" }]
      }
    ]
  }
};

export const demoPortfolios: Portfolio[] = [
  {
    portfolio_id: "pf_centurion_credit",
    name: "Atlas Strategic Credit",
    companies: [
      { company: "Northbridge Infrastructure", ebitda: 180, multiple: 8.4, carrying_value: 1380 },
      { company: "Helios Data Services", ebitda: 96, multiple: 11.2, carrying_value: 1040 },
      { company: "Meridian Logistics", ebitda: 72, multiple: 7.1, carrying_value: 520 }
    ],
    created_at: now,
    updated_at: now
  },
  {
    portfolio_id: "pf_global_special",
    name: "Global Special Situations",
    companies: [
      { company: "Aurelian Health", ebitda: 210, multiple: 10.8, carrying_value: 2160 },
      { company: "Crownwell Materials", ebitda: 130, multiple: 6.9, carrying_value: 830 }
    ],
    created_at: "2026-06-15T20:00:00.000Z",
    updated_at: "2026-06-15T20:00:00.000Z"
  }
];
