import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { login, probeAuthenticatedConnection } from "./api";

const storage = new Map<string, string>();

describe("authenticated frontend connection", () => {
  beforeEach(() => {
    storage.clear();
    vi.stubGlobal("sessionStorage", {
      getItem: (key: string) => storage.get(key) ?? null,
      setItem: (key: string, value: string) => storage.set(key, value),
      removeItem: (key: string) => storage.delete(key)
    });
  });

  afterEach(() => {
    vi.unstubAllGlobals();
    vi.restoreAllMocks();
  });

  it("verifies an authenticated endpoint without exposing an API key", async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ portfolios: [] }), {
        status: 200,
        headers: { "Content-Type": "application/json" }
      })
    );
    vi.stubGlobal("fetch", fetchMock);

    await expect(probeAuthenticatedConnection()).resolves.toBe(true);

    const [, init] = fetchMock.mock.calls[0] as [string, RequestInit];
    expect(init.credentials).toBe("same-origin");
    expect(new Headers(init.headers).has("X-API-Key")).toBe(false);
  });

  it("sends the API key once in a header to establish a session", async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ authenticated: true }), {
        status: 200,
        headers: { "Content-Type": "application/json" }
      })
    );
    vi.stubGlobal("fetch", fetchMock);

    await login("atlas_secret_key");

    const [url, init] = fetchMock.mock.calls[0] as [string, RequestInit];
    expect(String(url)).toContain("/auth/session");
    expect(init.method).toBe("POST");
    expect(init.credentials).toBe("same-origin"); // so the Set-Cookie is stored
    expect(new Headers(init.headers).get("X-API-Key")).toBe("atlas_secret_key");
    expect(storage.get("atlas_demo_mode")).toBeUndefined(); // demo mode cleared
  });

  it("rejects an invalid key so the UI can surface the failure", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        new Response(JSON.stringify({ detail: "invalid API key" }), {
          status: 401,
          headers: { "Content-Type": "application/json" }
        })
      )
    );

    await expect(login("atlas_wrong")).rejects.toThrow();
  });

  it("marks a missing or unauthenticated backend unavailable", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        new Response(JSON.stringify({ detail: "not configured" }), {
          status: 500,
          headers: { "Content-Type": "application/json" }
        })
      )
    );

    await expect(probeAuthenticatedConnection()).resolves.toBe(false);
  });
});
