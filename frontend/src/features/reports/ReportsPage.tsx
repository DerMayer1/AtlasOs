import { useQuery } from "@tanstack/react-query";
import { useMemo, useState } from "react";
import { Panel } from "../../components/ui/Panel";
import { SeverityBadge } from "../../components/ui/SeverityBadge";
import { StateBlock } from "../../components/ui/StateBlock";
import { fetchReport, fetchReports } from "../../lib/api";
import { compactDate, titleCase } from "../../lib/format";

export function ReportsPage() {
  const reportsQuery = useQuery({
    queryKey: ["reports"],
    queryFn: () => fetchReports(100)
  });
  const reports = reportsQuery.data ?? [];
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const activeId = selectedId ?? reports[0]?.analysis_id ?? null;
  const activeSummary = useMemo(
    () => reports.find((report) => report.analysis_id === activeId) ?? reports[0],
    [reports, activeId]
  );
  const detailQuery = useQuery({
    queryKey: ["report", activeId],
    queryFn: () => fetchReport(activeId ?? ""),
    enabled: Boolean(activeId)
  });

  if (reportsQuery.error) {
    return <StateBlock title="Unable to load reports" detail={reportsQuery.error instanceof Error ? reportsQuery.error.message : "Check connection."} />;
  }

  return (
    <div className="reports-grid">
      <Panel title="Decision reports" subtitle="Persisted memo layer. Select one report to inspect figures, actions and citations.">
        <div className="report-list">
          {reports.map((report) => (
            <button
              className="report-row"
              data-selected={report.analysis_id === activeId}
              key={report.report_id}
              type="button"
              onClick={() => setSelectedId(report.analysis_id)}
            >
              <span>
                <strong>{report.headline}</strong>
                <small>{report.portfolio_name ?? titleCase(report.engine)} / {compactDate(report.created_at)}</small>
              </span>
              <SeverityBadge severity={report.max_severity} />
            </button>
          ))}
          {!reports.length && !reportsQuery.isLoading && (
            <StateBlock title="No reports yet" detail="Create a report from a completed analysis in the ledger." />
          )}
          {reportsQuery.isLoading && <div className="list-skeleton" />}
        </div>
      </Panel>

      <Panel
        title="Committee memo"
        subtitle={activeSummary ? `${activeSummary.analysis_id} / ${activeSummary.portfolio_name ?? titleCase(activeSummary.engine)}` : "No report selected"}
        className="report-detail"
      >
        {detailQuery.isLoading && <div className="memo-skeleton" />}
        {detailQuery.error && (
          <StateBlock title="Unable to open report" detail={detailQuery.error instanceof Error ? detailQuery.error.message : "Report detail unavailable."} />
        )}
        {detailQuery.data && (
          <article className="memo-body">
            <div className="memo-heading">
              <SeverityBadge severity={activeSummary?.max_severity ?? "info"} />
              <h3>{detailQuery.data.headline}</h3>
              <p>
                Snapshot {detailQuery.data.snapshot_id}. Engine {detailQuery.data.engine_version || "-"},
                model {detailQuery.data.model_version || "-"}.
              </p>
            </div>

            <section className="memo-section">
              <h4>Key figures</h4>
              <div className="figure-grid">
                {detailQuery.data.key_figures.map((figure) => (
                  <div className="figure" key={`${figure.label}-${figure.citation.locator}`}>
                    <span>{figure.label}</span>
                    <strong>{figure.value}</strong>
                    <small>{figure.citation.artifact}:{figure.citation.locator}</small>
                  </div>
                ))}
              </div>
            </section>

            <section className="memo-section">
              <h4>Drivers</h4>
              <div className="figure-grid">
                {detailQuery.data.risk_drivers.map((figure) => (
                  <div className="figure" key={`${figure.label}-${figure.citation.locator}`}>
                    <span>{figure.label}</span>
                    <strong>{figure.value}</strong>
                    <small>{figure.citation.artifact}:{figure.citation.locator}</small>
                  </div>
                ))}
              </div>
            </section>

            <section className="memo-section">
              <h4>Actions</h4>
              <div className="action-stack">
                {detailQuery.data.actions.map((action) => (
                  <div className="action-item" data-severity={action.severity} key={action.title}>
                    <SeverityBadge severity={action.severity} />
                    <strong>{action.title}</strong>
                    <p>{action.rationale}</p>
                    <small>
                      {action.citations.map((citation) => `${citation.artifact}:${citation.locator}`).join(" / ")}
                    </small>
                  </div>
                ))}
              </div>
            </section>
          </article>
        )}
      </Panel>
    </div>
  );
}
