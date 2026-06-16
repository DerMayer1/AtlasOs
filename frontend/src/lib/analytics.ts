import type { Analysis, ReportSummary } from "./schemas";
import { severityRank } from "./format";

export function latestImpairment(analyses: Analysis[]) {
  return analyses.find((analysis) => analysis.engine === "impairment");
}

export function latestMacro(analyses: Analysis[]) {
  return analyses.find((analysis) => analysis.engine === "macro_monitor");
}

export function worstReport(reports: ReportSummary[]) {
  return [...reports].sort((a, b) => severityRank(b.max_severity) - severityRank(a.max_severity))[0];
}

export function totalActions(reports: ReportSummary[]) {
  return reports.reduce((sum, report) => sum + report.action_count, 0);
}

export function riskSeries(analyses: Analysis[]) {
  return analyses
    .filter((analysis) => analysis.portfolio_mean_p_impairment !== null && analysis.portfolio_mean_p_impairment !== undefined)
    .slice()
    .reverse()
    .slice(-12)
    .map((analysis, index) => ({
      name: `Run ${index + 1}`,
      risk: Number(((analysis.portfolio_mean_p_impairment ?? 0) * 100).toFixed(1))
    }));
}
