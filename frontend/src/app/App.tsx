import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { useMemo, useState } from "react";
import { AnalysesPage } from "../features/analyses/AnalysesPage";
import { MacroPage } from "../features/macro/MacroPage";
import { OverviewPage } from "../features/overview/OverviewPage";
import { ReportsPage } from "../features/reports/ReportsPage";
import { SystemPage } from "../features/system/SystemPage";
import { AppShell, type RouteId } from "../components/layout/AppShell";
import { ApiKeyProvider } from "./ApiKeyProvider";

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
          {route === "overview" && <OverviewPage onNavigate={navigate} />}
          {route === "analyses" && <AnalysesPage onNavigate={navigate} />}
          {route === "reports" && <ReportsPage onNavigate={navigate} />}
          {route === "macro-monitor" && <MacroPage />}
          {route === "system" && <SystemPage />}
          {route === "impairment" && <AnalysesPage onNavigate={navigate} engineFilter="impairment" />}
          {route === "portfolios" && <OverviewPage onNavigate={navigate} focus="portfolios" />}
        </AppShell>
      </ApiKeyProvider>
    </QueryClientProvider>
  );
}

function isRoute(value: string): value is RouteId {
  return ["overview", "impairment", "portfolios", "analyses", "reports", "macro-monitor", "system"].includes(value);
}
