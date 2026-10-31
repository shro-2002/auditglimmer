import { expect, test } from "@playwright/test";
import path from "node:path";

/**
 * LIVE journey through the real UI and real Meta Model API (paid, owner-approved).
 * Budget: exactly 1 SAM 3.1 call (one image, one concept) + 2 Muse Spark calls (two selected regions).
 * Skipped unless LIVE_JOURNEY=1 so the normal suite never spends.
 */
const REAL = path.resolve(__dirname, "../../fixtures/real");
const SHOTS = path.resolve(__dirname, "../../eval/results/live-journey");

test.skip(process.env.LIVE_JOURNEY !== "1", "set LIVE_JOURNEY=1 to run the paid live journey");
test.use({ video: "on", viewport: { width: 1440, height: 900 } });
test.setTimeout(300_000);

test("live journey: real photo → SAM masks → Muse evidence → reconcile → review → report → trace", async ({ page }) => {
  const shot = (name: string) => page.screenshot({ path: path.join(SHOTS, `${name}.png`), fullPage: true });

  await page.goto("/");
  await expect(page.getByTestId("mode-badge")).toContainText(/live/i);

  await page.goto("/sessions/new");
  await page.getByLabel("Session name").fill("Live collateral inspection — real photo");
  await page.getByPlaceholder("WH-07").fill("WH-R");
  await page.getByRole("button", { name: "Create session" }).click();
  await page.waitForURL(/\/sessions\/ses_/);
  const sessionUrl = page.url();

  await page.locator('input[type="file"]').setInputFiles(path.join(REAL, "ledger_real.csv"));
  await page.getByRole("button", { name: /upload & validate/i }).click();
  await expect(page.getByTestId("ledger-summary")).toContainText("7");
  await shot("01-ledger");

  await page.goto(`${sessionUrl}/images`);
  await page.locator('input[type="file"]').setInputFiles(path.join(REAL, "army_forklifts_row.jpg"));
  await page.getByRole("button", { name: /upload/i }).click();
  await expect(page.getByText(/Uploaded 1 image/)).toBeVisible();

  await page.goto(`${sessionUrl}/inspect`);
  const toggle = page.getByTestId("extract-all-toggle");
  await expect(toggle).not.toBeChecked(); // LIVE default: segment only, extract per selected region
  await page.getByTestId("concept-input").fill("forklift");
  await page.getByTestId("run-button").click(); // SAM call 1/1
  await expect(page.getByTestId("run-status")).toHaveAttribute("data-status", /succeeded|partial|failed/, { timeout: 180_000 });
  await expect(page.getByTestId("run-status")).toHaveAttribute("data-status", "succeeded");
  const regions = page.getByTestId("region-list").getByRole("button");
  await expect(regions.first()).toBeVisible();
  await shot("02-sam-masks");

  const count = Math.min(await regions.count(), 2);
  for (let i = 0; i < count; i++) { // Muse calls (max 2)
    await regions.nth(i).click();
    await page.getByTestId("extract-button").click();
    // the extraction card disappears only once validated evidence (status ok) is stored
    await expect(page.getByTestId("extract-button")).toHaveCount(0, { timeout: 180_000 });
    await expect(page.getByTestId("evidence-panel")).toContainText(/observed object/i);
    await expect(page.getByTestId("decision-panel")).toBeVisible();
    await shot(`03-muse-evidence-region-${i + 1}`);
  }

  await page.goto(`${sessionUrl}/reconciliation`);
  await expect(page.getByTestId("reconciliation-table")).toBeVisible();
  await shot("04-reconciliation");

  await page.goto(`${sessionUrl}/review`);
  const item = page.locator('[data-testid^="review-item-"]').first();
  await expect(item).toBeVisible();
  await item.locator('input[type="radio"]').first().check();
  await item.getByLabel("Reviewer name").fill("live-demo-reviewer");
  await item.getByTestId("confirm-button").click(); // human override of a candidate match
  await shot("05-review");

  await page.goto(`${sessionUrl}/report`);
  const [download] = await Promise.all([page.waitForEvent("download"), page.getByTestId("report-download-html").click()]);
  await download.saveAs(path.join(SHOTS, "live-audit-report.html"));
  await shot("06-report");

  await page.goto(`${sessionUrl}/trace`);
  await expect(page.getByTestId("trace-table")).toContainText("sam-3.1");
  await expect(page.getByTestId("trace-table")).toContainText("muse-spark-1.3");
  await shot("07-trace");
});
