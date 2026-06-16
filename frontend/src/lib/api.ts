import {
  analysesResponseSchema,
  healthSchema,
  portfoliosResponseSchema,
  reportDetailSchema,
  reportsResponseSchema,
  type Analysis,
  type Portfolio,
  type ReportDetail,
  type ReportSummary
} from "./schemas";

const API_KEY_STORAGE = "atlas_api_key";

export function getStoredApiKey() {
  return sessionStorage.getItem(API_KEY_STORAGE) ?? "";
}

export function setStoredApiKey(value: string) {
  if (value.trim()) {
    sessionStorage.setItem(API_KEY_STORAGE, value.trim());
  } else {
    sessionStorage.removeItem(API_KEY_STORAGE);
  }
}

export class ApiError extends Error {
  constructor(
    message: string,
    readonly status: number
  ) {
    super(message);
  }
}

async function atlasFetch(path: string, init: RequestInit = {}) {
  const apiKey = getStoredApiKey();
  const headers = new Headers(init.headers);
  headers.set("Accept", "application/json");
  if (apiKey) {
    headers.set("X-API-Key", apiKey);
  }
  if (init.body && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }

  const response = await fetch(path, { ...init, headers });
  if (!response.ok) {
    let message = `${response.status} ${response.statusText}`;
    try {
      const body = await response.json();
      message = body.detail ?? message;
    } catch {
      // Keep the HTTP status text when the backend returns no JSON body.
    }
    throw new ApiError(message, response.status);
  }
  return response.json();
}

export async function bootstrapLocalDemo() {
  const body = await atlasFetch("/demo/bootstrap", { method: "POST" });
  if (typeof body.api_key === "string") {
    setStoredApiKey(body.api_key);
  }
  return body;
}

export async function fetchAnalyses(limit = 100): Promise<Analysis[]> {
  const body = await atlasFetch(`/analyses?limit=${limit}`);
  return analysesResponseSchema.parse(body).analyses;
}

export async function fetchReports(limit = 100): Promise<ReportSummary[]> {
  const body = await atlasFetch(`/reports?limit=${limit}`);
  return reportsResponseSchema.parse(body).reports;
}

export async function fetchReport(analysisId: string): Promise<ReportDetail> {
  const body = await atlasFetch(`/analyses/${analysisId}/report`);
  return reportDetailSchema.parse(body);
}

export async function buildReport(analysisId: string): Promise<ReportDetail> {
  const body = await atlasFetch(`/analyses/${analysisId}/report`, {
    method: "POST"
  });
  return reportDetailSchema.parse(body);
}

export async function fetchPortfolios(limit = 200): Promise<Portfolio[]> {
  const body = await atlasFetch(`/portfolios?limit=${limit}`);
  return portfoliosResponseSchema.parse(body).portfolios;
}

export async function fetchHealth() {
  const body = await atlasFetch("/health");
  return healthSchema.parse(body);
}
