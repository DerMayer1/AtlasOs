import { createContext, useContext, useMemo, useState, type ReactNode } from "react";
import { getConnectionMode, getStoredApiKey, isDemoMode, setDemoMode, setStoredApiKey } from "../lib/api";

type ApiKeyContextValue = {
  apiKey: string;
  setApiKey: (value: string) => void;
  clearApiKey: () => void;
  enableDemoMode: () => void;
  configured: boolean;
  demoMode: boolean;
  connectionMode: string;
};

const ApiKeyContext = createContext<ApiKeyContextValue | null>(null);

export function ApiKeyProvider({ children }: { children: ReactNode }) {
  const [apiKey, setApiKeyState] = useState(getStoredApiKey);

  const value = useMemo<ApiKeyContextValue>(
    () => ({
      apiKey,
      configured: Boolean(apiKey) || isDemoMode(),
      demoMode: isDemoMode(),
      connectionMode: getConnectionMode(),
      setApiKey: (next: string) => {
        setStoredApiKey(next);
        setApiKeyState(next.trim());
      },
      enableDemoMode: () => {
        setStoredApiKey("");
        setDemoMode(true);
        setApiKeyState("");
      },
      clearApiKey: () => {
        setStoredApiKey("");
        setDemoMode(false);
        setApiKeyState("");
      }
    }),
    [apiKey]
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
