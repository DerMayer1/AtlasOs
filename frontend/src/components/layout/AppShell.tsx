import type { ReactNode } from "react";
import { clsx } from "clsx";
import { useApiKey } from "../../app/ApiKeyProvider";
import { ConnectionPanel } from "../ui/ConnectionPanel";

export type RouteId =
  | "overview"
  | "impairment"
  | "portfolios"
  | "analyses"
  | "reports"
  | "macro-monitor"
  | "system";

const routes: Array<{ id: RouteId; label: string }> = [
  { id: "overview", label: "Overview" },
  { id: "impairment", label: "Impairment" },
  { id: "portfolios", label: "Portfolios" },
  { id: "analyses", label: "Analyses" },
  { id: "reports", label: "Reports" },
  { id: "macro-monitor", label: "Macro Monitor" },
  { id: "system", label: "System" }
];

const pageCopy: Record<RouteId, { title: string; subtitle: string }> = {
  overview: {
    title: "Overview",
    subtitle: "Portfolio impairment, macro regime and open decisions at a glance."
  },
  impairment: {
    title: "Impairment",
    subtitle: "Completed impairment runs, outputs and report creation."
  },
  portfolios: {
    title: "Portfolios",
    subtitle: "Versioned portfolio inputs and latest exposure context."
  },
  analyses: {
    title: "Analyses",
    subtitle: "Execution ledger across engines, snapshots and portfolios."
  },
  reports: {
    title: "Reports",
    subtitle: "Decision memos, actions, severities and cited figures."
  },
  "macro-monitor": {
    title: "Macro Monitor",
    subtitle: "Regime signal, stress index and recent macro engine output."
  },
  system: {
    title: "System",
    subtitle: "Local connection, API key and runtime status."
  }
};

export function AppShell({
  route,
  onNavigate,
  children
}: {
  route: RouteId;
  onNavigate: (route: RouteId) => void;
  children: ReactNode;
}) {
  const { configured } = useApiKey();
  const copy = pageCopy[route];

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <a className="brand" href="#overview" onClick={() => onNavigate("overview")}>
          <span className="brand-mark">A</span>
          <span>ATLAS</span>
        </a>
        <nav className="nav" aria-label="Primary">
          {routes.map((item) => (
            <button
              className={clsx("nav-item", route === item.id && "is-active")}
              key={item.id}
              type="button"
              onClick={() => onNavigate(item.id)}
            >
              <span className="nav-rule" />
              {item.label}
            </button>
          ))}
        </nav>
        <div className="sidebar-footer">
          <span>AtlasOS v0.5</span>
          <strong>{configured ? "Connected" : "Key required"}</strong>
        </div>
      </aside>
      <main className="main">
        <header className="topbar">
          <div>
            <h1>{copy.title}</h1>
            <p>{copy.subtitle}</p>
          </div>
          <ConnectionPanel />
        </header>
        {children}
      </main>
    </div>
  );
}
