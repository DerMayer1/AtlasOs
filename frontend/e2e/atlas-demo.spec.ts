import { expect, test } from "@playwright/test";

test.beforeEach(async ({ page }) => {
  await page.addInitScript(() => sessionStorage.setItem("atlas_demo_mode", "1"));
});

test("opens the decision memo from the overview", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByRole("heading", { name: "Overview", level: 1 })).toBeVisible();

  await page.getByRole("button", { name: "Reports" }).click();

  await expect(page).toHaveURL(/#reports$/);
  await expect(page.getByRole("heading", { name: "Committee memo" })).toBeVisible();
  await expect(page.getByText("Mean P(impairment)")).toBeVisible();
  await expect(page.getByRole("heading", { name: "Actions" })).toBeVisible();
});

test("filters completed analyses and builds a report", async ({ page }) => {
  await page.goto("/#analyses");
  await expect(page.getByRole("heading", { name: "Analyses", level: 1 })).toBeVisible();

  await page.getByLabel("Engine").selectOption("impairment");
  await page.getByLabel("Status").selectOption("succeeded");
  await expect(page.getByText("run_macro_77b91d0e")).toHaveCount(0);

  await page.getByRole("row", { name: /run_ic_92f4a1c8/ }).getByRole("button", { name: "Report" }).click();

  await expect(page).toHaveURL(/#reports$/);
  await expect(page.getByText("Strategic Credit requires committee review", { exact: false }).first()).toBeVisible();
});
