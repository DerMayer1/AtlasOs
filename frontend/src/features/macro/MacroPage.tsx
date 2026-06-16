import { useQuery } from "@tanstack/react-query";
import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { Metric } from "../../components/ui/Metric";
import { Panel } from "../../components/ui/Panel";
import { StateBlock } from "../../components/ui/StateBlock";
import { fetchAnalyses } from "../../lib/api";
import { latestMacro } from "../../lib/analytics";
import { compactDate, number, titleCase } from "../../lib/format";

export function MacroPage() {
  const { data = [], isLoading, error } = useQuery({
    queryKey: ["analyses"],
    queryFn: () => fetchAnalyses(100)
  });
  const macro = latestMacro(data);
  const macroRuns = data.filter((analysis) => analysis.engine === "macro_monitor").slice(0, 8).reverse();
  const chart = macroRuns.map((analysis, index) => ({
    name: `M${index + 1}`,
    stress: Number((analysis.stress_index ?? 0).toFixed(2))
  }));

  if (error) {
    return <StateBlock title="Unable to load macro monitor" detail={error instanceof Error ? error.message : "Check connection."} />;
  }

  return (
    <div className="macro-grid">
      <section className="executive-strip">
        <Metric label="Current regime" value={macro?.macro_regime ? titleCase(macro.macro_regime) : "-"} detail={macro ? compactDate(macro.created_at) : "No macro run"} />
        <Metric label="Stress index" value={number(macro?.stress_index)} detail={macro?.snapshot_id ?? "No snapshot"} tone={(macro?.stress_index ?? 0) > 1 ? "watch" : "neutral"} />
        <Metric label="Runs" value={macroRuns.length} detail="Recent macro monitor executions" />
      </section>
      <Panel title="Stress series" subtitle="Recent Macro Monitor stress index readings." className="wide-panel">
        {isLoading && <div className="skeleton-chart" />}
        {!isLoading && chart.length > 0 && (
          <ResponsiveContainer width="100%" height={280}>
            <BarChart data={chart} margin={{ left: 6, right: 14, top: 12, bottom: 8 }}>
              <CartesianGrid vertical={false} stroke="#eee9df" />
              <XAxis dataKey="name" tickLine={false} axisLine={false} tick={{ fontSize: 10 }} />
              <YAxis tickLine={false} axisLine={false} tick={{ fontSize: 10 }} width={36} />
              <Tooltip contentStyle={{ borderRadius: 0, border: "1px solid #d8d3c8", fontSize: 12 }} />
              <Bar dataKey="stress" fill="#315c45" radius={[2, 2, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        )}
        {!isLoading && chart.length === 0 && <StateBlock title="No macro run yet" detail="Run the Macro Monitor engine to populate this page." />}
      </Panel>
    </div>
  );
}
