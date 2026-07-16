import { fireEvent, render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { App } from "./App";

vi.mock("../features/overview/OverviewPage", () => ({
  OverviewPage: () => <div>Overview content</div>
}));
vi.mock("../features/reports/ReportsPage", () => ({
  ReportsPage: () => (
    <section>
      <h2>Committee memo</h2>
      <span>Mean P(impairment)</span>
    </section>
  )
}));

describe("App navigation", () => {
  beforeEach(() => {
    sessionStorage.setItem("atlas_demo_mode", "1");
    window.location.hash = "#overview";
  });

  it("navigates from the overview to a persisted committee report", async () => {
    render(<App />);

    expect(await screen.findByRole("heading", { name: "Overview", level: 1 })).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Reports" }));

    expect(await screen.findByRole("heading", { name: "Reports", level: 1 })).toBeInTheDocument();
    expect(await screen.findByRole("heading", { name: "Committee memo" })).toBeInTheDocument();
    expect(screen.getByText("Mean P(impairment)")).toBeInTheDocument();
    expect(window.location.hash).toBe("#reports");
  });
});
