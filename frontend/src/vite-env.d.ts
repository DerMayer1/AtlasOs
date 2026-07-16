/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_ATLAS_API_URL?: string;
  readonly VITE_ATLAS_RUNTIME?: "proxy" | "same-origin";
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
