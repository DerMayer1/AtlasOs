import { useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { useApiKey } from "../../app/ApiKeyProvider";
import { bootstrapLocalDemo, getApiBaseUrl, login, logout } from "../../lib/api";

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
  const [apiKeyInput, setApiKeyInput] = useState("");
  const [signingIn, setSigningIn] = useState(false);
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

  async function handleSignIn() {
    const key = apiKeyInput.trim();
    if (!key) {
      setStatus("Enter an API key to sign in.");
      return;
    }
    setSigningIn(true);
    setStatus("Signing in...");
    try {
      await login(key);
      setApiKeyInput("");
      useBackendMode();
      setStatus("Signed in. Backend connected.");
      await queryClient.invalidateQueries();
    } catch (error) {
      setStatus(error instanceof Error ? error.message : "Sign in failed.");
    } finally {
      setSigningIn(false);
    }
  }

  async function handleSignOut() {
    await logout();
    setStatus("Signed out.");
    await queryClient.invalidateQueries();
    window.location.reload();
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
            Sign in with an Atlas API key. It is exchanged once for an HttpOnly
            session cookie and is never kept in browser storage.
          </p>
          <div className="connection-signin">
            <label className="form-note" htmlFor="atlas-api-key">
              API key
            </label>
            <input
              id="atlas-api-key"
              type="password"
              autoComplete="off"
              placeholder="atlas_..."
              value={apiKeyInput}
              onChange={(event) => setApiKeyInput(event.target.value)}
              onKeyDown={(event) => {
                if (event.key === "Enter") {
                  void handleSignIn();
                }
              }}
            />
            <div className="connection-actions">
              <button
                className="primary-button"
                type="button"
                disabled={signingIn}
                onClick={() => void handleSignIn()}
              >
                {signingIn ? "Signing in..." : "Sign in"}
              </button>
              {configured && !demoMode && (
                <button className="secondary-button" type="button" onClick={handleSignOut}>
                  Sign out
                </button>
              )}
            </div>
          </div>
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
