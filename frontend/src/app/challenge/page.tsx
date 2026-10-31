"use client";

import Link from "next/link";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";

import { DecisionPanel, EvidencePanel, findLedgerRecord } from "@/components/session/EvidencePanels";
import { MaskViewer } from "@/components/session/MaskViewer";
import { Button, Card, ErrorState, SkeletonRows, buttonClass } from "@/components/ui/primitives";
import { api, queryKeys as keys } from "@/lib/api";
import type { DetectionBundle, Session } from "@/lib/types";

const DEMO_FACILITY = "WH-01";
const DEMO_CASE_NAME = "Evidence challenge (DEMO)";
const RUN_POLL_MS = 500;
const RUN_DONE = ["succeeded", "partial", "failed"];

type Pick = (bundles: DetectionBundle[]) => DetectionBundle | undefined;

/** Recorded LIVE: a SAM-segmented region with Muse evidence that the rules sent to a human. */
const pickLiveAmbiguous: Pick = (bundles) =>
  bundles.find((b) => b.detection.provider === "meta-sam" && b.evidence?.status === "ok" && b.decision?.review_required);

/** DEMO fixture: a serial-backed Tier 1 match (both reads agree, maker corroborates). */
const pickDemoVerified: Pick = (bundles) => bundles.find((b) => b.decision?.decision === "VERIFIED");

/** Prefer a case where Muse read something (a maker) yet the rules still needed a person: the most instructive. */
async function findLiveSession(): Promise<{ session: Session; bundle: DetectionBundle } | null> {
  const overview = await api.overview();
  let fallback: { session: Session; bundle: DetectionBundle } | null = null;
  for (const session of overview.live_evidence_sessions ?? []) {
    const bundles = await api.detections(session.id);
    const read = pickLiveAmbiguous(bundles.filter((b) => b.evidence?.evidence?.visible_manufacturer));
    if (read) return { session, bundle: read };
    const any = pickLiveAmbiguous(bundles);
    if (any && !fallback) fallback = { session, bundle: any };
  }
  return fallback;
}

async function findDemoSession(): Promise<{ session: Session; bundle: DetectionBundle } | null> {
  const sessions = (await api.sessions()).filter((s) => s.name === DEMO_CASE_NAME);
  for (const session of sessions) {
    const bundle = pickDemoVerified(await api.detections(session.id));
    if (bundle) return { session, bundle };
  }
  return null;
}

async function prepareDemoSession(): Promise<void> {
  const session = await api.createSession({ name: DEMO_CASE_NAME, facility_id: DEMO_FACILITY });
  await api.loadDemo(session.id);
  let run = await api.createRun(session.id, { concept: "generator", extract: true });
  while (!RUN_DONE.includes(run.status)) {
    await new Promise((resolve) => setTimeout(resolve, RUN_POLL_MS));
    run = await api.run(run.id);
  }
}

function SourceBanner({ live }: { live: boolean }) {
  return live ? (
    <p className="rounded-md border border-accent/40 bg-accent/10 px-3 py-2 text-sm" data-testid="source-live">
      <strong>Recorded LIVE</strong> — stored outputs of real <span className="font-mono">sam-3.1</span> and{" "}
      <span className="font-mono">muse-spark-1.3</span> calls on a licensed real photo (31 Oct). Replayed; no new model call.
    </p>
  ) : (
    <p className="rounded-md border border-demo/40 bg-demo/10 px-3 py-2 text-sm" data-testid="source-demo">
      <strong>DEMO fixture</strong> — synthetic image and hand-authored provider outputs; no model was called. Shown because no
      recorded live photo has yet produced a Tier 1 match.
    </p>
  );
}

function CaseView({ title, session, bundle, live }: { title: string; session: Session; bundle: DetectionBundle; live: boolean }) {
  const [selectedId, setSelectedId] = useState(bundle.detection.id);
  const [hoveredId, setHoveredId] = useState<string | null>(null);
  const detections = useQuery({ queryKey: keys.detections(session.id), queryFn: () => api.detections(session.id) });
  const images = useQuery({ queryKey: keys.images(session.id), queryFn: () => api.images(session.id) });
  const ledger = useQuery({ queryKey: keys.ledger(session.id), queryFn: () => api.ledger(session.id) });
  const trace = useQuery({ queryKey: keys.trace(session.id), queryFn: () => api.trace(session.id) });
  const image = images.data?.find((i) => i.id === bundle.detection.image_id);
  const regions = (detections.data ?? []).filter((b) => b.detection.image_id === bundle.detection.image_id);
  const selected = regions.find((b) => b.detection.id === selectedId) ?? bundle;
  const candidates = (selected.decision?.candidate_asset_ids ?? [])
    .map((id) => findLedgerRecord(ledger.data ?? [], id))
    .filter((r) => r !== undefined);
  const call = trace.data?.provider_calls.find((c) => c.id === selected.evidence?.provider_call_id);

  return (
    <section className="space-y-3" data-testid={live ? "case-live" : "case-demo"}>
      <h2 className="text-lg font-semibold">{title}</h2>
      <SourceBanner live={live} />
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-[minmax(0,1.2fr)_minmax(0,1fr)]">
        <Card title={`1 · Photo and ${live ? "SAM 3.1 masks" : "fixture masks"}`}>
          {image ? (
            <MaskViewer image={image} regions={regions} selectedId={selected.detection.id} hoveredId={hoveredId}
              showMasks onSelect={setSelectedId} onHover={setHoveredId} />
          ) : (
            <SkeletonRows rows={3} label="Loading photo" />
          )}
        </Card>
        <Card title="2 · Register rows the rules considered">
          {candidates.length === 0 ? (
            <p className="text-sm text-ink-muted">No register row is supported by this evidence.</p>
          ) : (
            <ul className="space-y-1 text-sm" data-testid="candidate-rows">
              {candidates.map((r) => (
                <li key={r.id} className="rounded border border-line px-2 py-1">
                  <span className="font-mono">{r.asset_id}</span> · {r.asset_type} · {r.manufacturer ?? "?"} {r.model ?? ""} ·
                  SN <span className="font-mono">{r.serial_number ?? "—"}</span> · row {r.source_row}
                </li>
              ))}
            </ul>
          )}
        </Card>
      </div>
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        <EvidencePanel bundle={selected} call={call} />
        <DecisionPanel decision={selected.decision} ledger={ledger.data ?? []} />
      </div>
      <p className="flex flex-wrap gap-2 text-sm">
        <Link className={buttonClass()} href={`/sessions/${session.id}/report`}>5 · Audit report</Link>
        <Link className={buttonClass()} href={`/sessions/${session.id}/trace`}>6 · Provenance and model calls</Link>
      </p>
    </section>
  );
}

export default function EvidenceChallengePage() {
  const client = useQueryClient();
  const live = useQuery({ queryKey: ["challenge", "live"], queryFn: findLiveSession });
  const demo = useQuery({ queryKey: ["challenge", "demo"], queryFn: findDemoSession });
  const prepare = useMutation({
    mutationFn: prepareDemoSession,
    onSuccess: () => client.invalidateQueries({ queryKey: ["challenge", "demo"] }),
  });

  return (
    <main className="mx-auto max-w-7xl space-y-8 px-4 py-6">
      <header className="space-y-2">
        <h1 className="text-2xl font-semibold">Evidence challenge</h1>
        <p className="max-w-3xl text-ink-muted">
          One photo, one register. SAM 3.1 isolates each piece of equipment; Muse Spark 1.3 reads only what is printed on it;
          deterministic rules decide; anything ambiguous goes to a person. Below: one ambiguous case from a real recorded
          run, and one supported match. Every panel names its source.
        </p>
      </header>

      {live.isPending && <SkeletonRows rows={4} label="Loading recorded live evidence" />}
      {live.isError && <ErrorState error={live.error} onRetry={() => live.refetch()} />}
      {live.data && (
        <CaseView title="Case A — ambiguous: needs human review" session={live.data.session} bundle={live.data.bundle} live />
      )}
      {live.data === null && <p className="text-sm text-ink-muted">No recorded live SAM + Muse evidence is stored here.</p>}

      {demo.isPending && <SkeletonRows rows={4} label="Loading DEMO case" />}
      {demo.isError && <ErrorState error={demo.error} onRetry={() => demo.refetch()} />}
      {demo.data && (
        <CaseView title="Case B — supported match (Tier 1)" session={demo.data.session} bundle={demo.data.bundle} live={false} />
      )}
      {demo.data === null && (
        <Card title="Case B — supported match (Tier 1)">
          <SourceBanner live={false} />
          <Button className="mt-3" variant="primary" data-testid="prepare-demo-case" disabled={prepare.isPending}
            onClick={() => prepare.mutate()}>
            {prepare.isPending ? "Preparing DEMO case…" : "Prepare DEMO case (no model call)"}
          </Button>
          {prepare.isError && <ErrorState title="DEMO case could not be prepared" error={prepare.error} />}
        </Card>
      )}
    </main>
  );
}
