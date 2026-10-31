// Screenshot a stored session's pages (read-only, makes no provider calls). Usage: node capture-session.mjs <sessionId> <outDir>
import { chromium } from "@playwright/test";
const [sid, out] = process.argv.slice(2);
const browser = await chromium.launch();
const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });
const base = `http://localhost:3000/sessions/${sid}`;
await page.goto(`${base}/inspect`);
const regions = page.getByTestId("region-list").getByRole("button");
await regions.last().click();
await page.getByTestId("evidence-panel").waitFor();
await page.screenshot({ path: `${out}/demo-inspect-evidence.png`, fullPage: true });
for (const tab of ["reconciliation", "review", "report", "trace"]) {
  await page.goto(`${base}/${tab}`);
  await page.waitForTimeout(1500);
  await page.screenshot({ path: `${out}/demo-${tab}.png`, fullPage: true });
}
await browser.close();
