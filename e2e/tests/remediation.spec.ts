import { expect, test } from "@playwright/test";

import { API, createSession, runConcept, seededSession } from "./helpers";

test("landing: product explanation, guided demo action, e2e sessions collapsed", async ({ page, request }) => {
  await createSession(request, false); // guarantees at least one "e2e …" session exists
  await page.goto("/");
  const intro = page.getByTestId("product-intro");
  await expect(intro).toContainText(/collateral auditors/i);
  await expect(intro).toContainText("SAM 3.1");
  await expect(intro).toContainText("Muse Spark 1.3");
  await expect(intro).toContainText(/human review/i);
  await expect(page.getByTestId("guided-demo-button")).toBeVisible();

  const details = page.getByTestId("test-sessions");
  await expect(details).toBeVisible();
  await expect(details).not.toHaveAttribute("open", /.*/);
  await expect(details.locator("summary")).toContainText(/Automated test sessions \(\d+\)/);
  await expect(page.getByTestId("session-list").getByText(/^e2e /i)).toHaveCount(0);
});

test("inspect: run button cannot double-fire and stays disabled while the run is active", async ({ page, request }) => {
  const sid = await createSession(request);
  let posts = 0;
  page.on("request", (r) => {
    if (r.method() === "POST" && r.url().endsWith(`/api/sessions/${sid}/runs`)) posts += 1;
  });
  await page.goto(`/sessions/${sid}/inspect`);
  await page.getByTestId("concept-input").fill("forklift");
  const button = page.getByTestId("run-button");
  await button.dblclick();
  await expect(button).toBeDisabled();
  await expect(page.getByTestId("run-status")).toHaveAttribute("data-status", /partial|succeeded/, { timeout: 45_000 });
  await expect(button).toBeEnabled();
  expect(posts).toBe(1);
});

test("inspect: supported concepts hinted; unsupported concept shows the server message", async ({ page, request }) => {
  const sid = await createSession(request);
  await page.goto(`/sessions/${sid}/inspect`);
  await expect(page.getByText(/compressor, electric motor, electrical equipment, elevator, engine, excavator, forklift, generator/)).toBeVisible();
  await page.getByTestId("concept-input").fill("spaceship");
  await page.getByTestId("run-button").click();
  await expect(page.getByRole("alert").filter({ hasText: "Run was not started" })).toContainText(/unsupported asset concept/i);
});

test("inspect: lands on an image with detections; DEMO confidence is labelled as fixture-authored", async ({ page, request }) => {
  const sid = await createSession(request);
  await runConcept(request, sid, "forklift");
  await page.goto(`/sessions/${sid}/inspect`);
  const regions = page.getByTestId("region-list").getByRole("button");
  await expect(regions.first()).toBeVisible();
  await expect(regions.first()).toContainText("fixture conf.");
  await expect(page.getByTestId("region-list")).not.toContainText("det. ");
});

test("reconciliation shows Human-confirmed status and reviewer after an API confirmation", async ({ page, request }) => {
  const sid = await seededSession(request);
  const queue: { id: string; detection_id: string; image_id: string; candidate_asset_ids: string[] }[] =
    await (await request.get(`${API}/api/sessions/${sid}/review-queue`)).json();
  const d = queue.find((x) => x.candidate_asset_ids.length > 0)!;
  const res = await request.post(`${API}/api/decisions/${d.id}/review`, {
    data: { action: "confirm", asset_id: d.candidate_asset_ids[0], reviewer: "E2E Reviewer", note: "Plate readable in crop, model matches." },
  });
  expect(res.ok()).toBeTruthy();
  await page.goto(`/sessions/${sid}/reconciliation`);
  await expect(page.getByTestId("decisions-table")).toContainText("E2E Reviewer");
  await expect(page.getByTestId("reconciliation-table").getByText("Human-confirmed").first()).toBeVisible();
});

test("inspect: 409 RUN_IN_PROGRESS is explained instead of a raw error", async ({ page, request }) => {
  const sid = await createSession(request);
  await page.route(`**/api/sessions/${sid}/runs`, (route) =>
    route.request().method() === "POST"
      ? route.fulfill({
          status: 409,
          contentType: "application/json",
          body: JSON.stringify({ error: { code: "RUN_IN_PROGRESS", message: "an inspection is already running", details: [], correlation_id: "e2e" } }),
        })
      : route.continue(),
  );
  await page.goto(`/sessions/${sid}/inspect`);
  await page.getByTestId("run-button").click();
  await expect(page.getByText(/already running for this session/i)).toBeVisible();
  await expect(page.getByText("Run was not started")).toHaveCount(0);
});

test("access gate: 401 opens the access-code prompt; code is sent as header and on image URLs", async ({ page, request }) => {
  const sid = await createSession(request);
  const CODE = "e2e-code";
  let sawHeader = false;
  // Simulates the backend gate (the shared dev backend runs without one).
  await page.route(/localhost:8000\/api\//, (route) => {
    const req = route.request();
    const isImage = /\/api\/images\//.test(req.url());
    const supplied = req.headers()["x-access-code"] ?? (isImage ? new URL(req.url()).searchParams.get("access_code") : null);
    if (supplied !== CODE) {
      return route.fulfill({
        status: 401,
        contentType: "application/json",
        body: JSON.stringify({ error: { code: "UNAUTHORIZED", message: "a valid access code is required", details: [], correlation_id: "e2e" } }),
      });
    }
    if (req.headers()["x-access-code"] === CODE) sawHeader = true;
    return route.continue();
  });
  await page.goto(`/sessions/${sid}/images`);
  const dialog = page.getByRole("dialog", { name: "Access code" });
  await expect(dialog).toBeVisible();
  await dialog.getByLabel("Code").fill(CODE);
  await dialog.getByRole("button", { name: "Continue" }).click();
  await expect(dialog).toBeHidden();
  const img = page.locator("img[alt^='Warehouse photo']").first();
  await expect(img).toHaveAttribute("src", /access_code=e2e-code/);
  await expect.poll(() => img.evaluate((el) => (el as HTMLImageElement).naturalWidth)).toBeGreaterThan(0);
  expect(sawHeader).toBeTruthy();
});

test("evidence challenge: sources are labelled; DEMO case is prepared without model calls", async ({ page }) => {
  await page.goto("/");
  await page.getByTestId("challenge-link").click();
  await expect(page.getByRole("heading", { name: "Evidence challenge" })).toBeVisible();
  const prepare = page.getByTestId("prepare-demo-case");
  if (await prepare.isVisible().catch(() => false)) await prepare.click();
  const demo = page.getByTestId("case-demo");
  await expect(demo).toBeVisible({ timeout: 30_000 });
  await expect(demo.getByTestId("source-demo")).toContainText(/no model was called/i);
  await expect(demo).toContainText("R1_UNIQUE_SERIAL_MATCH");
  await expect(demo.getByTestId("second-read")).toBeVisible();
  const live = page.getByTestId("case-live");
  if (await live.isVisible().catch(() => false)) {
    await expect(live.getByTestId("source-live")).toContainText("Recorded LIVE");
    await expect(live).toContainText(/meta-sam/);
  }
});
