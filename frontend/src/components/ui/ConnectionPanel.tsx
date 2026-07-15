import { useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { useApiKey } from "../../app/ApiKeyProvider";
import { bootstrapLocalDemo, getApiBaseUrl } from "../../lib/api";

export function ConnectionPanel() {
  const {
    configured,
    demoMode,
    enableDemoMode,
    useBackendMode,
    connectionMode,
    connectionState
  } = useApiKey();
  const [expanded, setExpanded] = useState(!configured);
  const [status, setStatus] = useState<string | null>(null);
  const queryClient = useQueryClient();

  async function handleBootstrap() {
    setStatus("Preparing local demo workspace...");
    try {
      const body = await bootstrapLocalDemo();
      if (body.mode === "static-demo") {
        enableDemoMode();
      } else {
        useBackendMode();
      }
      setStatus(`Local demo ready on snapshot ${body.snapshot_id ?? "latest"}.`);
      await queryClient.invalidateQueries();
    } catch (error) {
      setStatus(error instanceof Error ? error.message : "Local bootstrap failed.");
    }
  }

  return (
    <section className="connection-panel" aria-label="Connection">
      <div>
        <span className="status-dot" data-state={configured ? "ready" : "blocked"} />
        <strong>
          {demoMode
            ? "Static demo mode"
            : connectionState === "checking"
              ? "Checking backend"
              : configured
                ? "Backend connected"
                : "Backend unavailable"}
        </strong>
        <small>{demoMode ? "No backend calls" : getApiBaseUrl()}</small>
      </div>
      <button className="ghost-button" type="button" onClick={() => setExpanded((value) => !value)}>
        {expanded ? "Close" : "Details"}
      </button>
      {expanded && (
        <div className="connection-form">
          <p className="form-note">
            Secrets are backend-managed. The browser never stores or sends Atlas API keys.
          </p>
          <div className="connection-actions">
            <button
              className="primary-button"
              type="button"
              onClick={() => {
                useBackendMode();
                setStatus("Backend mode enabled.");
                void queryClient.invalidateQueries();
              }}
            >
              Backend mode
            </button>
            <button className="secondary-button" type="button" onClick={handleBootstrap}>
              Local demo
            </button>
            <button
              className="secondary-button"
              type="button"
              onClick={() => {
                enableDemoMode();
                setStatus("Static demo mode enabled explicitly.");
                void queryClient.invalidateQueries();
              }}
            >
              Static demo
            </button>
          </div>
          {status && <p className="form-note">{status}</p>}
          <p className="form-note">Connection: {connectionMode}</p>
        </div>
      )}
    </section>
  );
}
