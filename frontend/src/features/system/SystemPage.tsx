import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { useApiKey } from "../../app/ApiKeyProvider";
import { Metric } from "../../components/ui/Metric";
import { Panel } from "../../components/ui/Panel";
import { bootstrapLocalDemo, fetchHealth } from "../../lib/api";

export function SystemPage() {
  const { apiKey, setApiKey, clearApiKey, configured } = useApiKey();
  const [draft, setDraft] = useState(apiKey);
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
      if (typeof body.api_key === "string") {
        setApiKey(body.api_key);
      }
      setDraft(body.api_key ?? "");
      setMessage(`Local demo ready on snapshot ${body.snapshot_id ?? "latest"}.`);
      await queryClient.invalidateQueries();
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Local bootstrap failed.");
    }
  }

  return (
    <div className="system-grid">
      <section className="executive-strip">
        <Metric label="Connection" value={configured ? "Configured" : "Missing"} detail="Browser session storage" tone={configured ? "good" : "watch"} />
        <Metric label="Health" value={health.data?.status ?? (health.isError ? "Unavailable" : "-")} detail={health.isFetching ? "Checking..." : "Runtime endpoint"} />
        <Metric label="Frontend" value="React + Vite" detail="TypeScript client" />
      </section>

      <Panel title="API key" subtitle="Stored only in sessionStorage for local operation. No key is committed or persisted to source.">
        <form
          className="settings-form"
          onSubmit={(event) => {
            event.preventDefault();
            setApiKey(draft);
            setMessage("API key saved.");
            void queryClient.invalidateQueries();
          }}
        >
          <label>
            <span>Key</span>
            <input value={draft} onChange={(event) => setDraft(event.target.value)} type="password" placeholder="atlas_..." />
          </label>
          <div className="connection-actions">
            <button className="primary-button" type="submit">Save</button>
            <button className="secondary-button" type="button" onClick={localDemo}>Local demo</button>
            <button
              className="ghost-button"
              type="button"
              onClick={() => {
                clearApiKey();
                setDraft("");
                setMessage("API key cleared.");
                void queryClient.invalidateQueries();
              }}
            >
              Clear
            </button>
          </div>
          {message && <p className="form-note">{message}</p>}
          {health.error && <p className="inline-error">{health.error instanceof Error ? health.error.message : "Health check failed."}</p>}
        </form>
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
