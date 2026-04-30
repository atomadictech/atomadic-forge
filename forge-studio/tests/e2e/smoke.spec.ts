import { test, expect } from "@playwright/test";

test.describe("Forge Studio smoke", () => {
  test.beforeEach(async ({ page }) => { await page.goto("http://localhost:1420"); });

  test("header and nav tabs visible", async ({ page }) => {
    await expect(page.getByText("Forge Studio")).toBeVisible();
    for (const label of ["Project Scan","Architecture","Complexity","Debt Counter","Agent Topology"]) {
      await expect(page.getByRole("button", { name: label })).toBeVisible();
    }
  });

  test("Project Scan shows drop-zone input", async ({ page }) => {
    const dz = page.getByTestId("drop-zone");
    await expect(dz).toBeVisible();
    await expect(dz.getByRole("textbox")).toHaveAttribute("placeholder", /Drop a folder/);
  });

  test("Architecture tab shows empty-state before scan", async ({ page }) => {
    await page.getByRole("button", { name: "Architecture" }).click();
    await expect(page.getByText(/Scan a project to render the architecture graph/)).toBeVisible();
  });

  test("Agent Topology tab shows empty-state", async ({ page }) => {
    await page.getByRole("button", { name: "Agent Topology" }).click();
    await expect(page.getByText(/Connect to a project/)).toBeVisible();
  });
});