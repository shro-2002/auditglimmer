import { expect, type APIRequestContext } from "@playwright/test";

export const API = "http://localhost:8000";
const POLL_MS = 250;
const RUN_TIMEOUT_MS = 30_000;

export async function createSession(request: APIRequestContext, withDemo = true): Promise<string> {
  const res = await request.post(`${API}/api/sessions`, {
    data: { name: `e2e ${Date.now()}`, facility_id: "E2E" },
  });
  expect(res.status()).toBe(201);
  const { id } = await res.json();
  if (withDemo) expect((await request.post(`${API}/api/sessions/${id}/demo`)).ok()).toBeTruthy();
  return id;
}

export async function runConcept(request: APIRequestContext, sid: string, concept: string): Promise<void> {
  const res = await request.post(`${API}/api/sessions/${sid}/runs`, { data: { concept } });
  expect(res.status()).toBe(202);
  const { id } = await res.json();
  const deadline = Date.now() + RUN_TIMEOUT_MS;
  while (Date.now() < deadline) {
    const run = await (await request.get(`${API}/api/runs/${id}`)).json();
    if (!["queued", "running"].includes(run.status)) return;
    await new Promise((r) => setTimeout(r, POLL_MS));
  }
  throw new Error(`run ${id} did not finish`);
}

export async function seededSession(request: APIRequestContext): Promise<string> {
  const sid = await createSession(request);
  await runConcept(request, sid, "industrial generator");
  await runConcept(request, sid, "forklift");
  return sid;
}
