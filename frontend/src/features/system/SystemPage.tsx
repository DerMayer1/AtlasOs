import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { useApiKey } from "../../app/ApiKeyProvider";
import { Metric } from "../../components/ui/Metric";
import { Panel } from "../../components/ui/Panel";
import { bootstrapLocalDemo, fetchHealth, getApiBaseUrl } from "../../lib/api";

export function SystemPage() {
  const {
    configured,
    demoMode,
    enableDemoMode,
    useBackendMode,
    connectionMode,
    connectionState
  } = useApiKey();
  const [message, setMessage] = useState<string | null>(null);
  const queryClient = useQueryClient();
  const health = useQuery({
    queryKey: ["health", configured],
    queryFn: fetchHealth,
    enabled: configured
  });

  async function localDemo() {
    setMessage("Preparing local demo workspace...");
    try {
      const body = await bootstrapLocalDemo();
      if (body.mode === "static-demo") {
        enableDemoMode();
      } else {
        useBackendMode();
      }
      setMessage(`Local demo ready on snapshot ${body.snapshot_id ?? "latest"}.`);
      await queryClient.invalidateQueries();
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Local bootstrap failed.");
    }
  }

  return (
    <div className="system-grid">
      <section className="executive-strip">
        <Metric
          label="Connection"
          value={
            demoMode
              ? "Demo"
              : connectionState === "checking"
                ? "Checking"
                : configured
                  ? "Configured"
                  : "Missing"
          }
          detail={demoMode ? "Static demo mode" : getApiBaseUrl()}
          tone={configured ? "good" : "watch"}
        />
        <Metric label="Health" value={health.data?.status ?? (health.isError ? "Unavailable" : "-")} detail={health.isFetching ? "Checking..." : "Runtime endpoint"} />
        <Metric label="Frontend" value="React + Vite" detail="TypeScript client" />
      </section>

      <Panel title="Backend security" subtitle="Secrets stay in server-side environment variables. The browser only talks to the Atlas API or proxy.">
        <div className="settings-form">
          <div className="stack-list">
            <div>
              <strong>Browser</strong>
              <span>No Atlas API key in sessionStorage, localStorage or bundled JavaScript.</span>
            </div>
            <div>
              <strong>Runtime</strong>
              <span>Backend and proxy credentials are loaded from .env or deployment environment variables.</span>
            </div>
          </div>
          <div className="connection-actions">
            <button
              className="primary-button"
              type="button"
              onClick={() => {
                useBackendMode();
                setMessage("Backend mode enabled.");
                void queryClient.invalidateQueries();
              }}
            >
              Backend mode
            </button>
            <button className="secondary-button" type="button" onClick={localDemo}>Local demo</button>
            <button
              className="secondary-button"
              type="button"
              onClick={() => {
                enableDemoMode();
                setMessage("Static demo mode enabled explicitly.");
                void queryClient.invalidateQueries();
              }}
            >
              Static demo
            </button>
          </div>
          {message && <p className="form-note">{message}</p>}
          <p className="form-note">Connection mode: {connectionMode}</p>
          {health.error && <p className="inline-error">{health.error instanceof Error ? health.error.message : "Health check failed."}</p>}
        </div>
      </Panel>

      <Panel title="Stack contract" subtitle="The frontend is intentionally decoupled from the legacy static UI until we are ready to switch serving.">
        <div className="stack-list">
          <div><strong>React 19 + Vite</strong><span>Fast local development and isolated app shell.</span></div>
          <div><strong>TypeScript + Zod</strong><span>Typed UI contracts with runtime response validation.</span></div>
          <div><strong>TanStack Query/Table</strong><span>Data fetching, cache discipline and financial ledger tables.</span></div>
          <div><strong>Recharts</strong><span>Restrained charts for risk and stress trends.</span></div>
        </div>
      </Panel>
    </div>
  );
}
