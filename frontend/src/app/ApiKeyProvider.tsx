import { createContext, useContext, useMemo, useState, type ReactNode } from "react";
import { getStoredApiKey, isDemoMode, setStoredApiKey } from "../lib/api";

type ApiKeyContextValue = {
  apiKey: string;
  setApiKey: (value: string) => void;
  clearApiKey: () => void;
  configured: boolean;
};

const ApiKeyContext = createContext<ApiKeyContextValue | null>(null);

export function ApiKeyProvider({ children }: { children: ReactNode }) {
  const [apiKey, setApiKeyState] = useState(getStoredApiKey);

  const value = useMemo<ApiKeyContextValue>(
    () => ({
      apiKey,
      configured: Boolean(apiKey) || isDemoMode(),
      setApiKey: (next: string) => {
        setStoredApiKey(next);
        setApiKeyState(next.trim());
      },
      clearApiKey: () => {
        setStoredApiKey("");
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
