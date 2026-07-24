import { useQuery } from "@tanstack/react-query";
import {
  Area,
  CartesianGrid,
  ComposedChart,
  ReferenceArea,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis
} from "recharts";
import type { RouteId } from "../../components/layout/AppShell";
import { StateBlock } from "../../components/ui/StateBlock";
import { fetchAnalyses, fetchPortfolios, fetchReports } from "../../lib/api";
import {
  latestImpairment,
  latestMacro,
  riskSeries,
  totalActions,
  worstReport
} from "../../lib/analytics";
import { compactDate, number, percent, titleCase } from "../../lib/format";
import type { Analysis, ReportSummary, Severity } from "../../lib/schemas";

// Policy thresholds (mirror src/atlas/domain/reports/builder.py). These are the
// reference lines a risk chart in this domain must show.
const IMPAIRMENT_REVIEW = 15;
const IMPAIRMENT_ELEVATED = 30;

function riskTone(risk: number | null | undefined): string {
  const value = (risk ?? 0) * 100;
  if (value >= IMPAIRMENT_ELEVATED) return "neg";
  if (value >= IMPAIRMENT_REVIEW) return "warn";
  return "pos";
}

function stressTone(stress: number | null | undefined): string {
  const value = stress ?? 0;
  if (value >= 0.66) return "neg";
  if (value >= 0.5) return "warn";
  return "pos";
}

function regimeTone(regime: string | null | undefined): string {
  if (regime === "crisis") return "neg";
  if (regime === "tightening") return "warn";
  return "pos";
}

function severityTone(severity: Severity): string {
  return { info: "muted", watch: "warn", elevated: "warn", critical: "neg" }[severity] ?? "muted";
}

export function OverviewPage({
  onNavigate
}: {
  onNavigate: (route: RouteId) => void;
  focus?: "portfolios";
}) {
  const analysesQuery = useQuery({ queryKey: ["analyses"], queryFn: () => fetchAnalyses(100) });
  const reportsQuery = useQuery({ queryKey: ["reports"], queryFn: () => fetchReports(100) });
  const portfoliosQuery = useQuery({ queryKey: ["portfolios"], queryFn: () => fetchPortfolios(100) });

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
        detail={error instanceof Error ? error.message : "Check backend status."}
        action={<button className="primary-button" onClick={() => onNavigate("system")}>Open system</button>}
      />
    );
  }

  const snapshot = impairment?.snapshot_id ?? macro?.snapshot_id ?? "-";
  const asOf = impairment?.created_at ?? macro?.created_at;

  // Per-portfolio exposure, ranked by risk — the "who is most exposed" table.
  const exposures = analyses
    .filter((a) => a.engine === "impairment" && a.portfolio_mean_p_impairment != null)
    .map((a) => ({
      name: a.portfolio_name ?? a.portfolio_id ?? a.job_id,
      risk: a.portfolio_mean_p_impairment ?? 0,
      when: a.created_at
    }))
    .sort((x, y) => y.risk - x.risk);
  const maxRisk = Math.max(0.3, ...exposures.map((e) => e.risk));

  const ctx: Array<[string, string, string?]> = [
    ["SNAP", snapshot],
    ["AS OF", compactDate(asOf)],
    ["REGIME", macro?.macro_regime ? titleCase(macro.macro_regime) : "-", regimeTone(macro?.macro_regime)],
    ["STRESS", number(macro?.stress_index), stressTone(macro?.stress_index)],
    ["PF", String(portfolios.length)],
    ["RUNS", String(analyses.length)],
    ["RPT", String(reports.length)]
  ];

  const metrics: Array<[string, string, string?]> = [
    ["MEAN P(IMP)", percent(impairment?.portfolio_mean_p_impairment), riskTone(impairment?.portfolio_mean_p_impairment)],
    ["MACRO REGIME", macro?.macro_regime ? titleCase(macro.macro_regime) : "-", regimeTone(macro?.macro_regime)],
    ["STRESS IDX", number(macro?.stress_index), stressTone(macro?.stress_index)],
    ["OPEN ACTIONS", String(totalActions(reports)), totalActions(reports) > 0 ? "warn" : "pos"],
    ["PORTFOLIOS", String(portfolios.length)],
    ["REPORTS", String(reports.length)]
  ];

  return (
    <div className="term">
      <div className="term-context">
        {ctx.map(([k, v, tone]) => (
          <span className="ctx-item" key={k}>
            <span className="ctx-k">{k}</span>
            <span className={`ctx-v mono${tone ? ` is-${tone}` : ""}`}>{v}</span>
          </span>
        ))}
        <span className="ctx-item ctx-right">
          <span className={`status-dot${loading ? "" : " is-live"}`} />
          <span className="ctx-v mono">{loading ? "LOADING" : "LIVE"}</span>
        </span>
      </div>

      <div className="term-metrics">
        {metrics.map(([k, v, tone]) => (
          <div className="term-metric" key={k}>
            <span className="tm-k">{k}</span>
            <span className={`tm-v mono${tone ? ` is-${tone}` : ""}`}>{v}</span>
          </div>
        ))}
      </div>

      <div className="term-grid">
        <section className="pane pane-chart">
          <div className="pane-head">
            <span className="pane-title">Portfolio risk path</span>
            <span className="pane-meta mono">P(impairment) % · review {IMPAIRMENT_REVIEW} · elevated {IMPAIRMENT_ELEVATED}</span>
          </div>
          {loading ? (
            <div className="skeleton-chart" />
          ) : chartData.length ? (
            <ResponsiveContainer width="100%" height={214}>
              <ComposedChart data={chartData} margin={{ left: 2, right: 10, top: 10, bottom: 2 }}>
                <defs>
                  <linearGradient id="riskFill" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor="#f0a830" stopOpacity={0.22} />
                    <stop offset="100%" stopColor="#f0a830" stopOpacity={0} />
                  </linearGradient>
                </defs>
                <CartesianGrid stroke="#1d2127" vertical={false} />
                <ReferenceArea y1={IMPAIRMENT_ELEVATED} y2={100} fill="#ff4d44" fillOpacity={0.05} />
                <ReferenceLine y={IMPAIRMENT_REVIEW} stroke="#f0a830" strokeDasharray="3 3" strokeOpacity={0.5} />
                <ReferenceLine y={IMPAIRMENT_ELEVATED} stroke="#ff4d44" strokeDasharray="3 3" strokeOpacity={0.5} />
                <XAxis dataKey="name" tickLine={false} axisLine={{ stroke: "#2c323a" }} tick={{ fontSize: 10, fill: "#69707a", fontFamily: "var(--mono)" }} />
                <YAxis tickLine={false} axisLine={false} width={30} domain={[0, "dataMax + 6"]} tick={{ fontSize: 10, fill: "#69707a", fontFamily: "var(--mono)" }} />
                <Tooltip
                  cursor={{ stroke: "#69707a", strokeDasharray: "3 3" }}
                  contentStyle={{ background: "#15181c", border: "1px solid #2c323a", borderRadius: 0, fontSize: 11, fontFamily: "var(--mono)" }}
                  labelStyle={{ color: "#9098a1" }}
                  itemStyle={{ color: "#f0a830" }}
                  formatter={(v: number) => [`${v}%`, "risk"]}
                />
                <Area type="monotone" dataKey="risk" stroke="#f0a830" strokeWidth={1.75} fill="url(#riskFill)" dot={{ r: 2, fill: "#f0a830" }} activeDot={{ r: 3 }} />
              </ComposedChart>
            </ResponsiveContainer>
          ) : (
            <StateBlock title="No impairment history" detail="Run the impairment engine." />
          )}
        </section>

        <section className="pane pane-exposure">
          <div className="pane-head">
            <span className="pane-title">Exposure by portfolio</span>
            <span className="pane-meta mono">ranked · P(imp)</span>
          </div>
          <table className="term-table">
            <tbody>
              {exposures.length ? exposures.map((e) => (
                <tr key={e.name}>
                  <td className="tt-name">{e.name}</td>
                  <td className="tt-bar">
                    <span className="sparkbar">
                      <span className={`sparkbar-fill is-${riskTone(e.risk)}`} style={{ width: `${(e.risk / maxRisk) * 100}%` }} />
                    </span>
                  </td>
                  <td className={`num is-${riskTone(e.risk)}`}>{percent(e.risk)}</td>
                </tr>
              )) : (
                <tr><td className="tt-empty">No exposures.</td></tr>
              )}
            </tbody>
          </table>
        </section>
      </div>

      <div className="term-grid term-grid-2">
        <section className="pane pane-ledger">
          <div className="pane-head">
            <span className="pane-title">Analyses</span>
            <button className="pane-link mono" onClick={() => onNavigate("analyses")}>LEDGER →</button>
          </div>
          <table className="term-table term-table-head">
            <thead>
              <tr>
                <th>RUN</th><th>ENGINE</th><th>STATUS</th><th className="num">OUTCOME</th><th className="num">CREATED</th>
              </tr>
            </thead>
            <tbody>
              {analyses.map((a: Analysis) => (
                <tr key={a.job_id}>
                  <td className="mono tt-id">{a.job_id}</td>
                  <td>{titleCase(a.engine)}</td>
                  <td><span className={`tag is-${a.status}`}>{a.status.toUpperCase()}</span></td>
                  <td className={`num mono is-${a.engine === "macro_monitor" ? stressTone(a.stress_index) : riskTone(a.portfolio_mean_p_impairment)}`}>
                    {a.engine === "macro_monitor" ? number(a.stress_index) : percent(a.portfolio_mean_p_impairment)}
                  </td>
                  <td className="num mono tt-time">{compactDate(a.created_at)}</td>
                </tr>
              ))}
              {!analyses.length && <tr><td colSpan={5} className="tt-empty">No analyses.</td></tr>}
            </tbody>
          </table>
        </section>

        <section className="pane pane-reports">
          <div className="pane-head">
            <span className="pane-title">Decision reports</span>
            <button className="pane-link mono" onClick={() => onNavigate("reports")}>ALL →</button>
          </div>
          <div className="report-list">
            {reports.length ? reports.map((r: ReportSummary) => (
              <button key={r.report_id} className="report-row" onClick={() => onNavigate("reports")}>
                <span className={`sev-tick is-${severityTone(r.max_severity)}`} />
                <span className="rr-body">
                  <span className="rr-head mono">
                    <span className={`rr-sev is-${severityTone(r.max_severity)}`}>{r.max_severity.toUpperCase()}</span>
                    <span className="rr-meta">{r.action_count} act · {compactDate(r.created_at)}</span>
                  </span>
                  <span className="rr-line">{r.headline}</span>
                </span>
              </button>
            )) : (
              <StateBlock title="No memo built" detail="Build a report from a completed analysis." />
            )}
            {topReport && (
              <div className="report-foot mono">TOP: {titleCase(topReport.max_severity)} · {topReport.portfolio_name ?? titleCase(topReport.engine)}</div>
            )}
          </div>
        </section>
      </div>
    </div>
  );
}
