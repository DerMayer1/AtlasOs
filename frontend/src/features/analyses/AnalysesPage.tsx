import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  createColumnHelper,
  flexRender,
  getCoreRowModel,
  getFilteredRowModel,
  useReactTable
} from "@tanstack/react-table";
import { useMemo, useState } from "react";
import type { RouteId } from "../../components/layout/AppShell";
import { Panel } from "../../components/ui/Panel";
import { StateBlock } from "../../components/ui/StateBlock";
import { buildReport, fetchAnalyses } from "../../lib/api";
import { compactDate, number, percent, titleCase } from "../../lib/format";
import type { Analysis } from "../../lib/schemas";

const columnHelper = createColumnHelper<Analysis>();

export function AnalysesPage({
  onNavigate,
  engineFilter
}: {
  onNavigate: (route: RouteId) => void;
  engineFilter?: string;
}) {
  const queryClient = useQueryClient();
  const { data = [], isLoading, error } = useQuery({
    queryKey: ["analyses"],
    queryFn: () => fetchAnalyses(100)
  });
  const [engine, setEngine] = useState(engineFilter ?? "");
  const [status, setStatus] = useState("");

  const filtered = useMemo(
    () =>
      data.filter(
        (analysis) =>
          (!engine || analysis.engine === engine) &&
          (!status || analysis.status === status)
      ),
    [data, engine, status]
  );

  const reportMutation = useMutation({
    mutationFn: buildReport,
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["reports"] });
      onNavigate("reports");
    }
  });

  const columns = useMemo(
    () => [
      columnHelper.accessor("job_id", {
        header: "Run",
        cell: (info) => <span className="mono strong">{info.getValue()}</span>
      }),
      columnHelper.accessor("engine", {
        header: "Engine",
        cell: (info) => titleCase(info.getValue())
      }),
      columnHelper.accessor("portfolio_name", {
        header: "Portfolio",
        cell: (info) => info.getValue() ?? "-"
      }),
      columnHelper.accessor("status", {
        header: "Status",
        cell: (info) => <span className={`status-chip is-${info.getValue()}`}>{titleCase(info.getValue())}</span>
      }),
      columnHelper.display({
        id: "outcome",
        header: "Outcome",
        cell: ({ row }) =>
          row.original.engine === "macro_monitor"
            ? `Stress ${number(row.original.stress_index)}`
            : percent(row.original.portfolio_mean_p_impairment)
      }),
      columnHelper.accessor("created_at", {
        header: "Created",
        cell: (info) => compactDate(info.getValue())
      }),
      columnHelper.display({
        id: "actions",
        header: "Actions",
        cell: ({ row }) => (
          <div className="row-actions">
            {row.original.status === "succeeded" && (
              <button
                className="secondary-button"
                type="button"
                onClick={() => reportMutation.mutate(row.original.job_id)}
              >
                Report
              </button>
            )}
          </div>
        )
      })
    ],
    [reportMutation]
  );

  const table = useReactTable({
    data: filtered,
    columns,
    getCoreRowModel: getCoreRowModel(),
    getFilteredRowModel: getFilteredRowModel()
  });

  if (error) {
    return <StateBlock title="Unable to load analyses" detail={error instanceof Error ? error.message : "Check connection."} />;
  }

  return (
    <Panel
      title="Execution ledger"
      subtitle="A single operational table for every engine run. Reports are built from completed rows only."
      action={<button className="ghost-button" onClick={() => void queryClient.invalidateQueries({ queryKey: ["analyses"] })}>Refresh</button>}
    >
      <div className="toolbar">
        <label>
          <span>Engine</span>
          <select value={engine} onChange={(event) => setEngine(event.target.value)}>
            <option value="">All engines</option>
            <option value="impairment">Impairment</option>
            <option value="macro_monitor">Macro Monitor</option>
          </select>
        </label>
        <label>
          <span>Status</span>
          <select value={status} onChange={(event) => setStatus(event.target.value)}>
            <option value="">All statuses</option>
            <option value="succeeded">Succeeded</option>
            <option value="queued">Queued</option>
            <option value="running">Running</option>
            <option value="failed">Failed</option>
          </select>
        </label>
      </div>
      <div className="data-table">
        <table>
          <thead>
            {table.getHeaderGroups().map((headerGroup) => (
              <tr key={headerGroup.id}>
                {headerGroup.headers.map((header) => (
                  <th key={header.id}>{flexRender(header.column.columnDef.header, header.getContext())}</th>
                ))}
              </tr>
            ))}
          </thead>
          <tbody>
            {isLoading && (
              <tr>
                <td colSpan={7}>Loading analyses...</td>
              </tr>
            )}
            {!isLoading &&
              table.getRowModel().rows.map((row) => (
                <tr key={row.id}>
                  {row.getVisibleCells().map((cell) => (
                    <td key={cell.id}>{flexRender(cell.column.columnDef.cell, cell.getContext())}</td>
                  ))}
                </tr>
              ))}
            {!isLoading && !table.getRowModel().rows.length && (
              <tr>
                <td colSpan={7}>No analyses match the current filters.</td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
      {reportMutation.error && (
        <p className="inline-error">{reportMutation.error instanceof Error ? reportMutation.error.message : "Unable to build report."}</p>
      )}
    </Panel>
  );
}
