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
import { demoAnalyses, demoPortfolios, demoReportDetails, demoReports } from "./demoData";

const API_KEY_STORAGE = "atlas_api_key";
const DEMO_MODE_STORAGE = "atlas_demo_mode";
const API_BASE_URL = import.meta.env.VITE_ATLAS_API_URL?.replace(/\/$/, "") ?? "";

export function getStoredApiKey() {
  return sessionStorage.getItem(API_KEY_STORAGE) ?? "";
}

export function setStoredApiKey(value: string) {
  if (value.trim()) {
    sessionStorage.setItem(API_KEY_STORAGE, value.trim());
    setDemoMode(false);
  } else {
    sessionStorage.removeItem(API_KEY_STORAGE);
  }
}

export function isDemoMode() {
  return sessionStorage.getItem(DEMO_MODE_STORAGE) === "1";
}

export function setDemoMode(value: boolean) {
  if (value) {
    sessionStorage.setItem(DEMO_MODE_STORAGE, "1");
  } else {
    sessionStorage.removeItem(DEMO_MODE_STORAGE);
  }
}

export function getApiBaseUrl() {
  return API_BASE_URL || window.location.origin;
}

export function getConnectionMode() {
  if (isDemoMode()) {
    return "static-demo";
  }
  return API_BASE_URL ? "remote-api" : "same-origin-api";
}

function apiUrl(path: string) {
  if (path.startsWith("http://") || path.startsWith("https://")) {
    return path;
  }
  return `${API_BASE_URL}${path}`;
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

  const response = await fetch(apiUrl(path), { ...init, headers });
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
  try {
    const body = await atlasFetch("/demo/bootstrap", { method: "POST" });
    if (typeof body.api_key === "string") {
      setStoredApiKey(body.api_key);
      setDemoMode(false);
    }
    return body;
  } catch (error) {
    setDemoMode(true);
    return {
      api_key: "",
      mode: "static-demo",
      snapshot_id: "snap_static_demo",
      degraded: true,
      reason: error instanceof Error ? error.message : "Backend unavailable"
    };
  }
}

export async function fetchAnalyses(limit = 100): Promise<Analysis[]> {
  if (isDemoMode()) {
    return demoAnalyses.slice(0, limit);
  }
  const body = await atlasFetch(`/analyses?limit=${limit}`);
  return analysesResponseSchema.parse(body).analyses;
}

export async function fetchReports(limit = 100): Promise<ReportSummary[]> {
  if (isDemoMode()) {
    return demoReports.slice(0, limit);
  }
  const body = await atlasFetch(`/reports?limit=${limit}`);
  return reportsResponseSchema.parse(body).reports;
}

export async function fetchReport(analysisId: string): Promise<ReportDetail> {
  if (isDemoMode()) {
    const detail = demoReportDetails[analysisId] ?? demoReportDetails.run_ic_92f4a1c8;
    return reportDetailSchema.parse(detail);
  }
  const body = await atlasFetch(`/analyses/${analysisId}/report`);
  return reportDetailSchema.parse(body);
}

export async function buildReport(analysisId: string): Promise<ReportDetail> {
  if (isDemoMode()) {
    return fetchReport(analysisId);
  }
  const body = await atlasFetch(`/analyses/${analysisId}/report`, {
    method: "POST"
  });
  return reportDetailSchema.parse(body);
}

export async function fetchPortfolios(limit = 200): Promise<Portfolio[]> {
  if (isDemoMode()) {
    return demoPortfolios.slice(0, limit);
  }
  const body = await atlasFetch(`/portfolios?limit=${limit}`);
  return portfoliosResponseSchema.parse(body).portfolios;
}

export async function fetchHealth() {
  if (isDemoMode()) {
    return {
      status: "static-demo",
      ok: true,
      version: "frontend-only"
    };
  }
  const body = await atlasFetch("/health");
  return healthSchema.parse(body);
}
