import { expect, test, type Page } from "@playwright/test";

async function runConceptInUi(page: Page, concept: string) {
  const status = page.getByTestId("run-status");
  const previousRunId = await status.getAttribute("data-run-id");
  await page.getByTestId("concept-input").fill(concept);
  await page.getByTestId("run-button").click();
  if (previousRunId) await expect(status).not.toHaveAttribute("data-run-id", previousRunId);
  await expect(status).toHaveAttribute("data-status", "partial", { timeout: 45_000 });
}

test("journey: create session, load demo, inspect, mask alignment, evidence", async ({ page }) => {
  await page.goto("/sessions/new");
  const form = page.getByTestId("create-session-form");
  await form.getByLabel("Session name").fill("E2E journey");
  await form.getByLabel("Facility ID").fill("E2E-1");
  await form.getByRole("button", { name: /create|start/i }).click();
  await expect(page).toHaveURL(/\/sessions\/ses_/);
  const sid = page.url().split("/sessions/")[1].split("/")[0];

  await page.getByTestId("load-demo-button").click();
  const summary = page.getByTestId("ledger-summary");
  await expect(summary.getByText("Accepted rows").locator("xpath=following-sibling::dd")).toHaveText("18");
  await expect(summary.getByText("Rejected rows").locator("xpath=following-sibling::dd")).toHaveText("2");

  await page.goto(`/sessions/${sid}/inspect`);
  await expect(page.getByTestId("run-status")).toHaveAttribute("data-status", "idle");
  await runConceptInUi(page, "industrial generator");
  await runConceptInUi(page, "forklift");

  // pick a thumbnail whose image has detections
  const thumbs = page.getByRole("group", { name: "Choose image" }).getByRole("button");
  const n = await thumbs.count();
  let found = false;
  for (let i = 0; i < n && !found; i++) {
    await thumbs.nth(i).click();
    await page.getByTestId("mask-overlay").waitFor();
    found = (await page.locator('[data-testid^="mask-path-"]').count()) > 0;
  }
  expect(found, "some image must show mask paths").toBeTruthy();

  const overlay = page.getByTestId("mask-overlay");
  const img = page.locator("img[alt^='Inspected photo']");
  await expect(img).toBeVisible();
  await expect.poll(() => img.evaluate((el) => (el as HTMLImageElement).complete && (el as HTMLImageElement).naturalWidth)).toBeGreaterThan(0);
  const [sb, ib] = [await overlay.boundingBox(), await img.boundingBox()];
  for (const k of ["x", "y", "width", "height"] as const) expect(Math.abs(sb![k] - ib![k])).toBeLessThanOrEqual(1);
  const natural = await img.evaluate((el) => [(el as HTMLImageElement).naturalWidth, (el as HTMLImageElement).naturalHeight]);
  const viewBox = (await overlay.getAttribute("viewBox"))!.split(/\s+/).map(Number);
  expect(viewBox).toEqual([0, 0, natural[0], natural[1]]);
  const path = page.locator('[data-testid^="mask-path-"]').first();
  expect(await path.getAttribute("d")).toMatch(/[ML]/);

  await page.getByTestId("region-list").getByRole("button").first().click();
  await expect(page.getByTestId("evidence-panel")).toBeVisible();
  await expect(page.getByTestId("decision-panel")).toBeVisible();
  await expect(page.getByTestId("evidence-panel")).toContainText(/not a model score/i); // DEMO: fixture-authored, never shown as a model score
  await expect(page.getByTestId("decision-panel")).toContainText(/not a probability/i);
});
