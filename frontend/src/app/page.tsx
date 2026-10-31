"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import Link from "next/link";
import { useRouter } from "next/navigation";

import { StatusDonut } from "@/components/StatusDonut";
import { HUMAN_CONFIRMED_NOTE, ModeTag, UNVERIFIED_NOTE } from "@/components/ui/Badges";
import { Button, buttonClass, Card, EmptyState, ErrorState, Skeleton, Stat } from "@/components/ui/primitives";
import { api, queryKeys } from "@/lib/api";
import { formatDateTime } from "@/lib/format";
import type { Session } from "@/lib/types";

const DEMO_FACILITY = "WH-01"; // facility_id used by the bundled demo ledger
const TEST_SESSION_PATTERN = /^(e2e|verify)/i;

const PIPELINE = [
  ["Ledger", "Upload the borrower's equipment register (CSV) and site photos."],
  ["SAM 3.1", "Segments every instance of an asset type in each photo."],
  ["Muse Spark 1.3", "Reads visible identifiers — make, model, serial, asset tag — from each region."],
  ["Rule engine", "Deterministically matches evidence to ledger rows; no model decides a match."],
  ["Human review", "Anything uncertain goes to a named reviewer with a written note."],
  ["Evidence report", "Every status traces back to a photo crop, a reading and a rule."],
] as const;

function SessionRow({ session }: { session: Session }) {
  return (
    <li>
      <Link href={`/sessions/${session.id}`} className="flex flex-wrap items-center justify-between gap-2 px-4 py-3 hover:bg-surface-2">
        <div className="min-w-0">
          <p className="truncate font-medium">{session.name}</p>
          <p className="text-xs text-ink-muted">
            <span className="font-mono">{session.facility_id}</span> · {formatDateTime(session.created_at)}
          </p>
        </div>
        <div className="tabular flex items-center gap-3 text-xs text-ink-muted">
          <span>{session.ledger_count} assets</span>
          <span>{session.image_count} images</span>
          <span className="rounded border border-line px-1.5 py-0.5 uppercase">{session.status}</span>
        </div>
      </Link>
    </li>
  );
}

function ProductIntro({ isDemo }: { isDemo: boolean }) {
  const router = useRouter();
  const queryClient = useQueryClient();
  const guided = useMutation({
    mutationFn: async () => {
      const session = await api.createSession({ name: "Guided demo", facility_id: DEMO_FACILITY });
      await api.loadDemo(session.id);
      return session;
    },
    onSuccess: (session) => {
      queryClient.invalidateQueries({ queryKey: queryKeys.overview });
      router.push(`/sessions/${session.id}/inspect`);
    },
  });

  return (
    <section aria-labelledby="intro-heading" data-testid="product-intro" className="rounded-lg border border-line bg-surface p-5">
      <h2 id="intro-heading" className="text-lg font-semibold tracking-tight">
        Collateral audits: reconcile the equipment ledger against what the site photos actually show
      </h2>
      <p className="mt-1 max-w-3xl text-sm text-ink-muted">
        Lenders&apos; collateral auditors must confirm that pledged equipment exists and matches the register. AuditGlimmer turns site
        photos into traceable evidence and is explicit about what it could not see.
      </p>
      <ol className="mt-4 grid gap-2 sm:grid-cols-2 lg:grid-cols-3">
        {PIPELINE.map(([step, text], i) => (
          <li key={step} className="rounded-md border border-line bg-surface-2 p-3 text-sm">
            <p className="font-semibold">
              <span className="tabular mr-2 text-accent">{i + 1}</span>
              {step}
            </p>
            <p className="mt-0.5 text-ink-muted">{text}</p>
          </li>
        ))}
      </ol>
      <div className="mt-4 flex flex-wrap items-center gap-3">
        {isDemo ? (
          <Button data-testid="guided-demo-button" variant="primary" disabled={guided.isPending} onClick={() => guided.mutate()}>
            {guided.isPending ? "Preparing demo…" : "Start guided demo"}
          </Button>
        ) : (
          <Link href="/sessions/new" className={buttonClass("primary")}>
            Start an audit
          </Link>
        )}
        <Link href="/challenge" className={buttonClass()} data-testid="challenge-link">
          See the evidence challenge
        </Link>
        {isDemo && <p className="text-xs text-ink-muted">Creates a session with the synthetic demo ledger and photos, then opens visual inspection.</p>}
      </div>
      {guided.isError && (
        <div className="mt-3">
          <ErrorState title="Guided demo could not start" error={guided.error} />
        </div>
      )}
    </section>
  );
}

export default function OverviewPage() {
  const overview = useQuery({ queryKey: queryKeys.overview, queryFn: api.overview });
  const sessions = overview.data?.recent_sessions ?? [];
  const testSessions = sessions.filter((s) => TEST_SESSION_PATTERN.test(s.name));
  const userSessions = sessions.filter((s) => !TEST_SESSION_PATTERN.test(s.name));

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Audit overview</h1>
          <p className="mt-1 text-sm text-ink-muted">Counts are computed from stored sessions — zero means nothing exists yet.</p>
        </div>
        <Link href="/sessions/new" className={buttonClass("primary")}>
          New audit session
        </Link>
      </div>

      {overview.data && <ProductIntro isDemo={overview.data.mode === "demo"} />}

      {overview.isPending && (
        <div role="status" aria-label="Loading overview" className="grid grid-cols-2 gap-3 md:grid-cols-4">
          {Array.from({ length: 8 }, (_, i) => (
            <Skeleton key={i} className="h-24 w-full" />
          ))}
        </div>
      )}
      {overview.isError && <ErrorState error={overview.error} onRetry={() => overview.refetch()} />}

      {overview.data && (
        <>
          <div className="grid grid-cols-2 gap-3 md:grid-cols-3 xl:grid-cols-6" data-testid="overview-stats">
            <Stat label="Sessions" value={overview.data.sessions} />
            <Stat label="Ledger assets" value={overview.data.assets} />
            <Stat label="Images" value={overview.data.images} />
            <Stat label="Detections" value={overview.data.detections} />
            <Stat label="Runs" value={overview.data.runs} />
            <Stat label="Review pending" value={overview.data.review_pending} hint="Human decisions outstanding" />
          </div>

          {(overview.data.live_evidence_sessions ?? []).length > 0 && (
            <Card title="Real-photo evidence (recorded LIVE Meta runs)" bodyClassName="p-0">
              <p className="px-4 pt-3 text-xs text-ink-muted">
                Stored outputs from genuine SAM 3.1 / Muse Spark 1.3 calls on licensed real photos. Opening them replays
                the stored results; no new model call is made.
              </p>
              <ul className="divide-y divide-line" data-testid="live-evidence-list">
                {(overview.data.live_evidence_sessions ?? []).map((s) => (
                  <SessionRow key={s.id} session={s} />
                ))}
              </ul>
            </Card>
          )}

          <div className="grid grid-cols-1 gap-6 lg:grid-cols-[minmax(0,1.1fr)_minmax(0,1fr)]">
            <Card title="Asset status across all sessions">
              <StatusDonut byStatus={overview.data.by_status} />
              <p className="mt-3 text-xs text-ink-muted">{UNVERIFIED_NOTE}</p>
              <p className="mt-1 text-xs text-ink-muted">{HUMAN_CONFIRMED_NOTE}</p>
            </Card>
            <Card title="Recent sessions" bodyClassName="p-0">
              {sessions.length === 0 ? (
                <div className="p-4">
                  <EmptyState title="No audit sessions yet">Create a session to upload a ledger and warehouse photos.</EmptyState>
                </div>
              ) : (
                <>
                  {userSessions.length === 0 && (
                    <p className="px-4 py-3 text-sm text-ink-muted">Only automated test sessions are in the recent list.</p>
                  )}
                  <ul className="divide-y divide-line" data-testid="session-list">
                    {userSessions.map((s) => (
                      <SessionRow key={s.id} session={s} />
                    ))}
                  </ul>
                  {testSessions.length > 0 && (
                    <details data-testid="test-sessions" className="border-t border-line">
                      <summary className="cursor-pointer px-4 py-3 text-sm text-ink-muted hover:text-ink">
                        Automated test sessions ({testSessions.length})
                      </summary>
                      <ul className="divide-y divide-line border-t border-line">
                        {testSessions.map((s) => (
                          <SessionRow key={s.id} session={s} />
                        ))}
                      </ul>
                    </details>
                  )}
                </>
              )}
            </Card>
          </div>
          <p className="text-xs text-ink-faint">
            Backend mode: <ModeTag mode={overview.data.mode} />
          </p>
        </>
      )}
    </div>
  );
}
