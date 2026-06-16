import { useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { useApiKey } from "../../app/ApiKeyProvider";
import { bootstrapLocalDemo } from "../../lib/api";

export function ConnectionPanel() {
  const { apiKey, setApiKey, clearApiKey, configured } = useApiKey();
  const [draft, setDraft] = useState(apiKey);
  const [expanded, setExpanded] = useState(!configured);
  const [status, setStatus] = useState<string | null>(null);
  const queryClient = useQueryClient();

  async function handleBootstrap() {
    setStatus("Preparing local demo workspace...");
    try {
      const body = await bootstrapLocalDemo();
      if (typeof body.api_key === "string") {
        setApiKey(body.api_key);
      }
      setDraft(body.api_key ?? "");
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
        <strong>{configured ? "API key configured" : "API key required"}</strong>
        <small>{configured ? "Same-origin API" : "Read/run scope needed"}</small>
      </div>
      <button className="ghost-button" type="button" onClick={() => setExpanded((value) => !value)}>
        {expanded ? "Close" : "Configure"}
      </button>
      {expanded && (
        <form
          className="connection-form"
          onSubmit={(event) => {
            event.preventDefault();
            setApiKey(draft);
            setStatus("API key stored for this browser session.");
            void queryClient.invalidateQueries();
          }}
        >
          <label>
            <span>API key</span>
            <input
              value={draft}
              onChange={(event) => setDraft(event.target.value)}
              placeholder="atlas_..."
              type="password"
            />
          </label>
          <div className="connection-actions">
            <button className="primary-button" type="submit">
              Save key
            </button>
            <button className="secondary-button" type="button" onClick={handleBootstrap}>
              Local demo
            </button>
            <button
              className="ghost-button"
              type="button"
              onClick={() => {
                clearApiKey();
                setDraft("");
                setStatus("API key cleared.");
                void queryClient.invalidateQueries();
              }}
            >
              Clear
            </button>
          </div>
          {status && <p className="form-note">{status}</p>}
        </form>
      )}
    </section>
  );
}
