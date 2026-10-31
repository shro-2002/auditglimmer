import { AxeBuilder } from "@axe-core/playwright";
import { expect, test } from "@playwright/test";

import { API, seededSession } from "./helpers";

const EXPECTED: Record<string, string> = {
  "A-001": "VERIFIED", "A-004": "PROBABLE",
  "A-003": "MISMATCHED", "A-010": "MISMATCHED",
  "A-002": "PROBABLE", "A-005": "PROBABLE", "A-006": "PROBABLE", "A-007": "PROBABLE", "A-011": "PROBABLE", "A-012": "PROBABLE",
  "A-008": "UNVERIFIED", "A-009": "UNVERIFIED", "A-013": "UNVERIFIED", "A-014": "UNVERIFIED", "A-015": "UNVERIFIED",
  "A-020": "NOT_OBSERVABLE", "A-021": "NOT_OBSERVABLE", "A-022": "NOT_OBSERVABLE",
};

test("reconciliation table shows fixture ground-truth statuses and UNVERIFIED caveat", async ({ page, request }) => {
  const sid = await seededSession(request);
  await page.goto(`/sessions/${sid}/reconciliation`);
  const table = page.getByTestId("reconciliation-table");
  await expect(table).toBeVisible();
  for (const [asset, status] of Object.entries(EXPECTED)) {
    const row = table.getByRole("row").filter({ has: page.getByRole("cell", { name: asset, exact: true }) });
    await expect(row, asset).toHaveAttribute("data-status", status);
    await expect(row, asset).toContainText(status);
  }
  await expect(page.getByText(/not adequately observed/i).first()).toBeVisible();
  await expect(page.getByText(/not evidence the asset is missing/i).first()).toBeVisible();
});

test("review: confirm needs a note, records HUMAN_CONFIRMED, second confirm conflicts with 409", async ({ page, request }) => {
  const sid = await seededSession(request);
  const queue: { id: string; flags: string[] }[] = await (await request.get(`${API}/api/sessions/${sid}/review-queue`)).json();
  const ambiguous = queue.filter((d) => d.flags.includes("AMBIGUOUS_CANDIDATES")).map((d) => d.id);
  expect(ambiguous.length).toBe(2);

  await page.goto(`/sessions/${sid}/review`);
  const confirmInto = async (id: string) => {
    const item = page.getByTestId(`review-item-${id}`);
    await item.locator('input[type="radio"][value="A-011"]').check();
    await item.getByLabel("Reviewer name").fill("e2e-reviewer");
    await item.getByLabel(/^Note/).fill("Serial plate legible in crop, matches ledger row.");
    await item.getByTestId("confirm-button").click();
    return item;
  };

  // Inline validation: confirm without a note is blocked client-side with the help line visible.
  const first = page.getByTestId(`review-item-${ambiguous[0]}`);
  await expect(first.getByText(/human confirmations are reported separately/i)).toBeVisible();
  await first.getByLabel("Reviewer name").fill("e2e-reviewer");
  await first.getByTestId("confirm-button").click();
  await expect(first.getByText(/needs a note of at least 10 characters/i)).toBeVisible();
  await expect(first.getByLabel(/^Note/)).toHaveAttribute("aria-invalid", "true");

  await confirmInto(ambiguous[0]);
  await expect(page.getByTestId(`review-item-${ambiguous[0]}`)).toHaveCount(0);

  const second = await confirmInto(ambiguous[1]);
  await expect(second.getByRole("alert")).toContainText(/conflict/i);
  await expect(second.getByRole("alert")).toContainText(/409/);

  await page.goto(`/sessions/${sid}/reconciliation`);
  const row = page.getByTestId("reconciliation-table").getByRole("row").filter({ has: page.getByRole("cell", { name: "A-011", exact: true }) });
  await expect(row).toHaveAttribute("data-status", "HUMAN_CONFIRMED");
  await expect(row).toContainText("Human-confirmed");
  await expect(row).not.toContainText("VERIFIED");
  await expect(row).toContainText(/yes/i);
});

test("review: reviewer name without a letter is blocked inline", async ({ page, request }) => {
  const sid = await seededSession(request);
  const queue: { id: string; candidate_asset_ids: string[] }[] = await (await request.get(`${API}/api/sessions/${sid}/review-queue`)).json();
  const target = queue.find((d) => d.candidate_asset_ids.length > 0)!;
  // "12" passes length but has no letter: client blocks it inline.
  await page.goto(`/sessions/${sid}/review`);
  const item = page.getByTestId(`review-item-${target.id}`);
  await item.getByLabel("Reviewer name").fill("12");
  await item.getByTestId("reject-button").click();
  await expect(item.getByText(/including a letter/i)).toBeVisible();
});

test("report: renders inline as DRAFT without changing status; exports download", async ({ page, request }) => {
  const sid = await seededSession(request);
  await page.goto(`/sessions/${sid}/report`);
  await expect(page.getByTestId("report-state")).toHaveAttribute("data-state", "DRAFT");
  await expect(page.getByTestId("report-open-reviews")).not.toHaveText("0");
  await expect(page.getByTestId("report-json")).toHaveCount(0);
  await expect(page.getByText(/pdf/i)).toHaveCount(0);
  const frame = page.frameLocator('[data-testid="report-frame"]');
  await expect(frame.getByText(/DRAFT/).first()).toBeVisible();
  await expect(page.locator("main")).not.toContainText('"report_version"');
  expect((await (await request.get(`${API}/api/sessions/${sid}`)).json()).status).not.toBe("reported");
  const [html] = await Promise.all([page.waitForEvent("download"), page.getByTestId("report-download-html").click()]);
  const htmlText = (await import("node:fs")).readFileSync((await html.path())!, "utf8");
  expect(html.suggestedFilename()).toMatch(/\.html$/);
  expect(htmlText).toContain("DEMO MODE");
  expect(htmlText).toContain("A photograph does not prove legal ownership");
  const [csv] = await Promise.all([page.waitForEvent("download"), page.getByTestId("report-download-csv").click()]);
  const csvText = (await import("node:fs")).readFileSync((await csv.path())!, "utf8");
  expect(csv.suggestedFilename()).toMatch(/\.csv$/);
  expect(csvText).toContain("A-001");
});

test("observability: trace table lists timeout and invalid_output calls", async ({ page, request }) => {
  const sid = await seededSession(request);
  await page.goto(`/sessions/${sid}/trace`);
  const table = page.getByTestId("trace-table");
  await expect(table).toBeVisible();
  await expect(table.getByRole("cell", { name: "timeout", exact: true }).first()).toBeVisible();
  await expect(table.getByRole("cell", { name: "invalid_output", exact: true }).first()).toBeVisible();
  await expect(table.getByRole("cell", { name: "segment", exact: true }).first()).toBeVisible();
});

test("failure state: unreachable API shows error with retry, no fake data", async ({ page }) => {
  await page.route(/localhost:8000/, (route) => route.abort());
  await page.goto("/");
  const alert = page.getByRole("alert").first();
  await expect(alert).toBeVisible();
  await expect(alert.getByRole("button", { name: "Retry" })).toBeVisible();
  await expect(page.getByTestId("overview-stats")).toHaveCount(0);
});

test("accessibility smoke (axe): record serious/critical counts", async ({ page, request }, info) => {
  const sid = await seededSession(request);
  const results: Record<string, { id: string; impact: string; nodes: number }[]> = {};
  for (const [name, path] of [["overview", "/"], ["inspect", `/sessions/${sid}/inspect`], ["reconciliation", `/sessions/${sid}/reconciliation`]]) {
    await page.goto(path);
    await page.waitForLoadState("networkidle");
    if (name === "inspect") await page.getByTestId("mask-overlay").waitFor();
    const axe = await new AxeBuilder({ page }).analyze();
    results[name] = axe.violations.map((v) => ({ id: v.id, impact: String(v.impact), nodes: v.nodes.length }));
  }
  const serious = Object.entries(results).map(([k, v]) => `${k}: ${v.filter((x) => ["serious", "critical"].includes(x.impact)).length} serious/critical of ${v.length} total`);
  console.log("AXE", JSON.stringify(results));
  info.annotations.push({ type: "axe", description: serious.join("; ") });
});

test("responsive 375x812: no horizontal scroll on overview and inspect", async ({ page, request }) => {
  const sid = await seededSession(request);
  await page.setViewportSize({ width: 375, height: 812 });
  for (const path of ["/", `/sessions/${sid}/inspect`]) {
    await page.goto(path);
    await page.waitForLoadState("networkidle");
    const { sw, cw } = await page.evaluate(() => ({ sw: document.documentElement.scrollWidth, cw: document.documentElement.clientWidth }));
    expect(sw, `${path} scrollWidth ${sw} > clientWidth ${cw}`).toBeLessThanOrEqual(cw);
  }
});
