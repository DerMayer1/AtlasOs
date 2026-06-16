import { createContext, useContext, useMemo, useState, type ReactNode } from "react";
import { getConnectionMode, isDemoMode, setDemoMode } from "../lib/api";

type ApiKeyContextValue = {
  useBackendMode: () => void;
  enableDemoMode: () => void;
  configured: boolean;
  demoMode: boolean;
  connectionMode: string;
};

const ApiKeyContext = createContext<ApiKeyContextValue | null>(null);

export function ApiKeyProvider({ children }: { children: ReactNode }) {
  const [demoMode, setDemoModeState] = useState(isDemoMode);

  const value = useMemo<ApiKeyContextValue>(
    () => ({
      configured: true,
      demoMode,
      connectionMode: getConnectionMode(),
      useBackendMode: () => {
        setDemoMode(false);
        setDemoModeState(false);
      },
      enableDemoMode: () => {
        setDemoMode(true);
        setDemoModeState(true);
      }
    }),
    [demoMode]
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
