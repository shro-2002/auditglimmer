// Records a captioned walkthrough of the running app (DEMO API + stored live sessions). No model calls.
// Usage (from e2e/): node scripts/record-demo.mjs <outDir>   then convert the .webm with ffmpeg.
import { chromium } from "@playwright/test";

const BASE = process.env.BASE_URL ?? "http://localhost:3000";
const API = process.env.API_URL ?? "http://localhost:8000";
const outDir = process.argv[2] ?? "demo-video";

async function sessionId(name) {
  const sessions = await (await fetch(`${API}/api/sessions`)).json();
  const hit = sessions.find((s) => s.name.startsWith(name));
  if (!hit) throw new Error(`session not found: ${name}`);
  return hit.id;
}

async function caption(page, text) {
  await page.evaluate((t) => {
    let el = document.getElementById("__caption");
    if (!el) {
      el = document.createElement("div");
      el.id = "__caption";
      el.style.cssText = "position:fixed;left:24px;right:24px;bottom:24px;z-index:99999;padding:14px 18px;" +
        "background:rgba(0,0,0,.82);color:#fff;font:600 20px/1.35 system-ui;border-radius:10px;pointer-events:none";
      document.body.appendChild(el);
    }
    el.textContent = t;
  }, text);
}

async function scene(page, text, ms) {
  await caption(page, text);
  await page.waitForTimeout(ms);
}

const config = await (await fetch(`${API}/api/config`)).json();
if (config.mode !== "demo") throw new Error("refusing to record: API is not in DEMO mode");
const liveId = await sessionId("Live collateral inspection");
const holdoutId = await sessionId("Holdout study");

const browser = await chromium.launch();
const context = await browser.newContext({ viewport: { width: 1440, height: 900 }, recordVideo: { dir: outDir, size: { width: 1440, height: 900 } } });
const page = await context.newPage();

await page.goto(BASE);
await scene(page, "Lenders keep registers of pledged equipment. Checking them means reading nameplates on site. AuditGlimmer turns photos into an auditable reconciliation — and refuses to guess.", 7000);
await page.goto(`${BASE}/challenge`);
await page.getByTestId("case-live").waitFor();
await scene(page, "RECORDED LIVE (31 Oct, replayed, no new call): SAM 3.1 returned a pixel mask for each forklift in a real licensed photo.", 7000);
await page.getByTestId("case-live").getByText("Structured visual evidence").scrollIntoViewIfNeeded();
await scene(page, "Muse Spark 1.3 read only the crop: maker HYSTER, no legible serial — and it says so instead of guessing.", 7000);
await page.getByTestId("case-live").getByText("Match decision").scrollIntoViewIfNeeded();
await scene(page, "Deterministic rules, not the model, decide: two Hyster forklifts are registered, so nothing is auto-matched. A person reviews.", 7500);
await page.getByTestId("case-demo").scrollIntoViewIfNeeded();
await scene(page, "DEMO FIXTURE (synthetic, no model call): a supported Tier 1 match — no live photo has produced one yet, and the page says so.", 7000);
await page.getByTestId("case-demo").getByTestId("second-read").scrollIntoViewIfNeeded();
await scene(page, "Tier 1 needs a unique serial, a second independent read that agrees, a matching maker or model, no conflicts, and a segmented region. An experimental safeguard — not a guarantee.", 8500);
await page.goto(`${BASE}/sessions/${holdoutId}/reconciliation`);
await scene(page, "Fresh holdout, 14 new photos, frozen before the run (LIVE, $0.12): 5/6 serials read exactly, 0 unsafe matches, correct single suggestion 5/6. Whole-photo plates never auto-verify.", 9000);
await page.goto(`${BASE}/sessions/${holdoutId}/trace`);
await scene(page, "Every model call is logged: model id, latency, tokens, estimated cost, raw output. Total recorded: 7 SAM + 51 Muse calls ≈ $0.32.", 8000);
await page.goto(`${BASE}/sessions/${liveId}/report`);
await scene(page, "The audit report states what is verified, by which rule, and what is not evidence of absence. A prototype — not production-certified.", 8000);

await context.close();
await browser.close();
