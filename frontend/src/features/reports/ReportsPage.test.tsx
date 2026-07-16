import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { ReportsPage } from "./ReportsPage";
import { fetchReports } from "../../lib/api";

vi.mock("../../lib/api", () => ({
  fetchReport: vi.fn(),
  fetchReports: vi.fn()
}));

describe("ReportsPage", () => {
  beforeEach(() => {
    vi.mocked(fetchReports).mockReset();
  });

  it("shows an actionable state when the reports endpoint fails", async () => {
    vi.mocked(fetchReports).mockRejectedValue(new Error("Backend timed out"));
    const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });

    render(
      <QueryClientProvider client={client}>
        <ReportsPage />
      </QueryClientProvider>
    );

    expect(await screen.findByText("Unable to load reports")).toBeInTheDocument();
    expect(screen.getByText("Backend timed out")).toBeInTheDocument();
  });
});
