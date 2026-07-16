import { fireEvent, render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { ApiKeyProvider, useApiKey } from "./ApiKeyProvider";
import {
  getConnectionMode,
  isDemoMode,
  probeAuthenticatedConnection,
  setDemoMode
} from "../lib/api";

vi.mock("../lib/api", () => ({
  getConnectionMode: vi.fn(),
  isDemoMode: vi.fn(),
  probeAuthenticatedConnection: vi.fn(),
  setDemoMode: vi.fn()
}));

function ConnectionProbe() {
  const value = useApiKey();
  return (
    <div>
      <span data-testid="state">{value.connectionState}</span>
      <span data-testid="configured">{String(value.configured)}</span>
      <button type="button" onClick={value.enableDemoMode}>Use demo</button>
    </div>
  );
}

describe("ApiKeyProvider", () => {
  beforeEach(() => {
    vi.mocked(isDemoMode).mockReturnValue(false);
    vi.mocked(getConnectionMode).mockReturnValue("same-origin-api");
    vi.mocked(probeAuthenticatedConnection).mockReset();
    vi.mocked(setDemoMode).mockReset();
  });

  it("marks a successful authenticated probe as ready", async () => {
    vi.mocked(probeAuthenticatedConnection).mockResolvedValue(true);
    render(<ApiKeyProvider><ConnectionProbe /></ApiKeyProvider>);

    expect(await screen.findByText("ready", { selector: "[data-testid='state']" })).toBeInTheDocument();
    expect(screen.getByTestId("configured")).toHaveTextContent("true");
  });

  it("exposes an unavailable backend without reporting a configured connection", async () => {
    vi.mocked(probeAuthenticatedConnection).mockResolvedValue(false);
    render(<ApiKeyProvider><ConnectionProbe /></ApiKeyProvider>);

    expect(await screen.findByText("unavailable", { selector: "[data-testid='state']" })).toBeInTheDocument();
    expect(screen.getByTestId("configured")).toHaveTextContent("false");
  });

  it("switches to deterministic demo mode", async () => {
    vi.mocked(probeAuthenticatedConnection).mockResolvedValue(false);
    render(<ApiKeyProvider><ConnectionProbe /></ApiKeyProvider>);

    fireEvent.click(screen.getByRole("button", { name: "Use demo" }));

    expect(setDemoMode).toHaveBeenCalledWith(true);
    expect(await screen.findByText("ready", { selector: "[data-testid='state']" })).toBeInTheDocument();
    expect(screen.getByTestId("configured")).toHaveTextContent("true");
  });
});
