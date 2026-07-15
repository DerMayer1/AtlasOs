import { describe, expect, it } from "vitest";
import { portfolioSchema } from "./schemas";

describe("portfolio API contract", () => {
  it("accepts the canonical backend company shape", () => {
    const portfolio = portfolioSchema.parse({
      portfolio_id: "pf_test",
      name: "Test Portfolio",
      companies: [
        {
          name: "Alpha",
          sector: "industrial",
          geography: "global",
          ebitda: 100,
          multiple: 8,
          carrying_value: 750
        }
      ],
      company_count: 1,
      current_version_id: "pfv_1",
      version_number: 1,
      created_at: "2026-07-15T00:00:00Z",
      updated_at: "2026-07-15T00:00:00Z"
    });

    expect(portfolio.companies?.[0]?.name).toBe("Alpha");
    expect(portfolio.company_count).toBe(1);
  });

  it("rejects the obsolete frontend-only company field", () => {
    expect(() =>
      portfolioSchema.parse({
        portfolio_id: "pf_test",
        name: "Test Portfolio",
        companies: [
          { company: "Alpha", ebitda: 100, multiple: 8, carrying_value: 750 }
        ]
      })
    ).toThrow();
  });
});
