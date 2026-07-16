import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { lazy, Suspense, useMemo, useState } from "react";
import { AppShell, type RouteId } from "../components/layout/AppShell";
import { ApiKeyProvider } from "./ApiKeyProvider";

const AnalysesPage = lazy(() =>
  import("../features/analyses/AnalysesPage").then((module) => ({ default: module.AnalysesPage }))
);
const MacroPage = lazy(() =>
  import("../features/macro/MacroPage").then((module) => ({ default: module.MacroPage }))
);
const OverviewPage = lazy(() =>
  import("../features/overview/OverviewPage").then((module) => ({ default: module.OverviewPage }))
);
const ReportsPage = lazy(() =>
  import("../features/reports/ReportsPage").then((module) => ({ default: module.ReportsPage }))
);
const SystemPage = lazy(() =>
  import("../features/system/SystemPage").then((module) => ({ default: module.SystemPage }))
);

export function App() {
  const [route, setRoute] = useState<RouteId>(() => {
    const hash = window.location.hash.replace("#", "");
    return isRoute(hash) ? hash : "overview";
  });
  const queryClient = useMemo(
    () =>
      new QueryClient({
        defaultOptions: {
          queries: {
            staleTime: 20_000,
            retry: 1,
            refetchOnWindowFocus: false
          }
        }
      }),
    []
  );

  function navigate(next: RouteId) {
    setRoute(next);
    window.history.pushState(null, "", `#${next}`);
  }

  return (
    <QueryClientProvider client={queryClient}>
      <ApiKeyProvider>
        <AppShell route={route} onNavigate={navigate}>
          <Suspense fallback={<div className="list-skeleton" role="status" aria-label="Loading view" />}>
            {route === "overview" && <OverviewPage onNavigate={navigate} />}
            {route === "analyses" && <AnalysesPage onNavigate={navigate} />}
            {route === "reports" && <ReportsPage />}
            {route === "macro-monitor" && <MacroPage />}
            {route === "system" && <SystemPage />}
            {route === "impairment" && <AnalysesPage onNavigate={navigate} engineFilter="impairment" />}
            {route === "portfolios" && <OverviewPage onNavigate={navigate} focus="portfolios" />}
          </Suspense>
        </AppShell>
      </ApiKeyProvider>
    </QueryClientProvider>
  );
}

function isRoute(value: string): value is RouteId {
  return ["overview", "impairment", "portfolios", "analyses", "reports", "macro-monitor", "system"].includes(value);
}
