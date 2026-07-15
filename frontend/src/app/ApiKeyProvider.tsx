import { createContext, useContext, useEffect, useMemo, useState, type ReactNode } from "react";
import {
  getConnectionMode,
  isDemoMode,
  probeAuthenticatedConnection,
  setDemoMode
} from "../lib/api";

type ConnectionState = "checking" | "ready" | "unavailable";

type ApiKeyContextValue = {
  useBackendMode: () => void;
  enableDemoMode: () => void;
  configured: boolean;
  demoMode: boolean;
  connectionMode: string;
  connectionState: ConnectionState;
};

const ApiKeyContext = createContext<ApiKeyContextValue | null>(null);

export function ApiKeyProvider({ children }: { children: ReactNode }) {
  const [demoMode, setDemoModeState] = useState(isDemoMode);
  const [connectionState, setConnectionState] = useState<ConnectionState>(
    demoMode ? "ready" : "checking"
  );
  const [probeVersion, setProbeVersion] = useState(0);

  useEffect(() => {
    if (demoMode) {
      setConnectionState("ready");
      return;
    }

    let active = true;
    setConnectionState("checking");
    void probeAuthenticatedConnection().then((available) => {
      if (active) {
        setConnectionState(available ? "ready" : "unavailable");
      }
    });
    return () => {
      active = false;
    };
  }, [demoMode, probeVersion]);

  const value = useMemo<ApiKeyContextValue>(
    () => ({
      configured: demoMode || connectionState === "ready",
      demoMode,
      connectionMode: getConnectionMode(),
      connectionState,
      useBackendMode: () => {
        setDemoMode(false);
        setDemoModeState(false);
        setProbeVersion((version) => version + 1);
      },
      enableDemoMode: () => {
        setDemoMode(true);
        setDemoModeState(true);
      }
    }),
    [connectionState, demoMode]
  );

  return <ApiKeyContext.Provider value={value}>{children}</ApiKeyContext.Provider>;
}

export function useApiKey() {
  const context = useContext(ApiKeyContext);
  if (!context) {
    throw new Error("useApiKey must be used inside ApiKeyProvider");
  }
  return context;
}
