"use client";

import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { usePathname } from "next/navigation";
import type { ReactNode } from "react";

import { ErrorState, Skeleton } from "@/components/ui/primitives";
import { api, queryKeys } from "@/lib/api";
import { formatDateTime } from "@/lib/format";
import { useSessionId } from "@/lib/use-session-id";

const TABS = [
  { slug: "", label: "Ledger" },
  { slug: "images", label: "Images" },
  { slug: "inspect", label: "Visual inspection" },
  { slug: "reconciliation", label: "Reconciliation" },
  { slug: "review", label: "Review queue" },
  { slug: "report", label: "Report" },
  { slug: "trace", label: "Observability" },
];

export default function SessionLayout({ children }: { children: ReactNode }) {
  const id = useSessionId();
  const pathname = usePathname();
  const session = useQuery({ queryKey: queryKeys.session(id), queryFn: () => api.session(id) });
  const base = `/sessions/${id}`;

  return (
    <div className="space-y-5">
      <div className="rounded-lg border border-line bg-surface p-4">
        {session.isPending && (
          <div role="status" aria-label="Loading session" className="space-y-2">
            <Skeleton className="h-6 w-64" />
            <Skeleton className="h-4 w-96 max-w-full" />
          </div>
        )}
        {session.isError && <ErrorState error={session.error} onRetry={() => session.refetch()} title="Session unavailable" />}
        {session.data && (
          <div className="flex flex-wrap items-end justify-between gap-3">
            <div className="min-w-0">
              <p className="text-xs uppercase tracking-wider text-ink-faint">Audit session</p>
              <h1 className="truncate text-xl font-semibold tracking-tight">{session.data.name}</h1>
              <p className="mt-0.5 text-xs text-ink-muted">
                Facility <span className="font-mono text-ink">{session.data.facility_id}</span> · created{" "}
                {formatDateTime(session.data.created_at)}
              </p>
            </div>
            <dl className="tabular flex gap-4 text-xs text-ink-muted">
              {(
                [
                  ["Assets", session.data.ledger_count],
                  ["Images", session.data.image_count],
                  ["Runs", session.data.run_count],
                ] as const
              ).map(([label, value]) => (
                <div key={label}>
                  <dt>{label}</dt>
                  <dd className="text-base font-semibold text-ink">{value}</dd>
                </div>
              ))}
              <div>
                <dt>Status</dt>
                <dd className="text-base font-semibold uppercase text-accent">{session.data.status}</dd>
              </div>
            </dl>
          </div>
        )}
      </div>

      <nav aria-label="Session sections" className="-mx-4 overflow-x-auto px-4 sm:mx-0 sm:px-0">
        <ul className="flex min-w-max gap-1 border-b border-line">
          {TABS.map((tab) => {
            const href = tab.slug ? `${base}/${tab.slug}` : base;
            const isActive = pathname === href;
            return (
              <li key={tab.label}>
                <Link
                  href={href}
                  aria-current={isActive ? "page" : undefined}
                  className={`-mb-px block border-b-2 px-3 py-2 text-sm ${
                    isActive ? "border-accent text-ink" : "border-transparent text-ink-muted hover:text-ink"
                  }`}
                >
                  {tab.label}
                </Link>
              </li>
            );
          })}
        </ul>
      </nav>

      {children}
    </div>
  );
}
