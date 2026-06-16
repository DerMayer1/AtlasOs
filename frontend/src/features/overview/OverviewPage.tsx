import { useQuery } from "@tanstack/react-query";
import { Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import type { RouteId } from "../../components/layout/AppShell";
import { Metric } from "../../components/ui/Metric";
import { Panel } from "../../components/ui/Panel";
import { SeverityBadge } from "../../components/ui/SeverityBadge";
import { StateBlock } from "../../components/ui/StateBlock";
import { fetchAnalyses, fetchPortfolios, fetchReports } from "../../lib/api";
import { latestImpairment, latestMacro, riskSeries, totalActions, worstReport } from "../../lib/analytics";
import { compactDate, number, percent, relativeTime, titleCase } from "../../lib/format";

export function OverviewPage({
  onNavigate,
  focus
}: {
  onNavigate: (route: RouteId) => void;
  focus?: "portfolios";
}) {
  const analysesQuery = useQuery({
    queryKey: ["analyses"],
    queryFn: () => fetchAnalyses(100)
  });
  const reportsQuery = useQuery({
    queryKey: ["reports"],
    queryFn: () => fetchReports(100)
  });
  const portfoliosQuery = useQuery({
    queryKey: ["portfolios"],
    queryFn: () => fetchPortfolios(100)
  });

  const analyses = analysesQuery.data ?? [];
  const reports = reportsQuery.data ?? [];
  const portfolios = portfoliosQuery.data ?? [];
  const impairment = latestImpairment(analyses);
  const macro = latestMacro(analyses);
  const topReport = worstReport(reports);
  const chartData = riskSeries(analyses);
  const loading = analysesQuery.isLoading || reportsQuery.isLoading || portfoliosQuery.isLoading;
  const error = analysesQuery.error ?? reportsQuery.error ?? portfoliosQuery.error;

  if (error) {
    return (
      <StateBlock
        title="Unable to load Atlas data"
        detail={error instanceof Error ? error.message : "Check API key and backend status."}
        action={<button className="primary-button" onClick={() => onNavigate("system")}>Open system</button>}
      />
    );
  }

  return (
    <div className="overview-grid">
      <section className="executive-strip">
        <Metric
          label="Mean impairment risk"
          value={percent(impairment?.portfolio_mean_p_impairment)}
          detail={impairment ? `${impairment.portfolio_name ?? "Portfolio"} / ${relativeTime(impairment.created_at)}` : "No impairment run"}
          tone={(impairment?.portfolio_mean_p_impairment ?? 0) > 0.25 ? "critical" : "neutral"}
        />
        <Metric
          label="Macro regime"
          value={macro?.macro_regime ? titleCase(macro.macro_regime) : "-"}
          detail={macro ? `Stress ${number(macro.stress_index)} / ${relativeTime(macro.created_at)}` : "No macro monitor run"}
          tone={macro?.macro_regime === "crisis" ? "critical" : macro?.macro_regime === "tightening" ? "watch" : "good"}
        />
        <Metric
          label="Open decision actions"
          value={totalActions(reports)}
          detail={reports.length ? `${reports.length} report(s) persisted` : "No decision reports"}
          tone={totalActions(reports) > 0 ? "watch" : "good"}
        />
        <Metric
          label="Portfolios"
          value={portfolios.length}
          detail={focus === "portfolios" ? "Portfolio view selected" : "Versioned input library"}
        />
      </section>

      <Panel title="Portfolio risk path" subtitle="Recent impairment outputs, ordered by execution time." className="risk-chart-panel">
        {loading ? (
          <div className="skeleton-chart" />
        ) : chartData.length ? (
          <ResponsiveContainer width="100%" height={260}>
            <LineChart data={chartData} margin={{ left: 6, right: 14, top: 12, bottom: 8 }}>
              <XAxis dataKey="name" tickLine={false} axisLine={false} tick={{ fontSize: 10 }} />
              <YAxis tickLine={false} axisLine={false} tick={{ fontSize: 10 }} width={36} />
              <Tooltip contentStyle={{ borderRadius: 0, border: "1px solid #d8d3c8", fontSize: 12 }} />
              <Line type="monotone" dataKey="risk" stroke="#315c45" strokeWidth={2} dot={{ r: 3 }} />
            </LineChart>
          </ResponsiveContainer>
        ) : (
          <StateBlock title="No impairment history" detail="Run the impairment engine to populate the risk path." />
        )}
      </Panel>

      <Panel
        title="Current decision memo"
        subtitle="Highest-severity report in the current persisted set."
        action={<button className="ghost-button" onClick={() => onNavigate("reports")}>Reports</button>}
        className="memo-panel"
      >
        {topReport ? (
          <article className="decision-memo">
            <SeverityBadge severity={topReport.max_severity} />
            <h3>{topReport.headline}</h3>
            <dl>
              <div>
                <dt>Scope</dt>
                <dd>{topReport.portfolio_name ?? titleCase(topReport.engine)}</dd>
              </div>
              <div>
                <dt>Actions</dt>
                <dd>{topReport.action_count}</dd>
              </div>
              <div>
                <dt>Created</dt>
                <dd>{compactDate(topReport.created_at)}</dd>
              </div>
            </dl>
          </article>
        ) : (
          <StateBlock title="No memo built" detail="Build a report from a completed analysis to create the decision layer." />
        )}
      </Panel>

      <Panel
        title="Recent analyses"
        subtitle="Operational runs across impairment and macro engines."
        action={<button className="ghost-button" onClick={() => onNavigate("analyses")}>Full ledger</button>}
        className="wide-panel"
      >
        <div className="compact-table">
          <table>
            <thead>
              <tr>
                <th>Run</th>
                <th>Engine</th>
                <th>Status</th>
                <th>Outcome</th>
                <th>Created</th>
              </tr>
            </thead>
            <tbody>
              {analyses.slice(0, 7).map((analysis) => (
                <tr key={analysis.job_id}>
                  <td className="mono">{analysis.job_id}</td>
                  <td>{titleCase(analysis.engine)}</td>
                  <td>{titleCase(analysis.status)}</td>
                  <td>
                    {analysis.engine === "macro_monitor"
                      ? `Stress ${number(analysis.stress_index)}`
                      : percent(analysis.portfolio_mean_p_impairment)}
                  </td>
                  <td>{compactDate(analysis.created_at)}</td>
                </tr>
              ))}
              {!analyses.length && (
                <tr>
                  <td colSpan={5}>No analyses available.</td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </Panel>
    </div>
  );
}
