"use client";

import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { usePathname } from "next/navigation";

import { api, API_BASE, queryKeys } from "@/lib/api";

import { Button } from "./ui/primitives";

const NAV = [
  { href: "/", label: "Overview" },
  { href: "/sessions/new", label: "New session" },
];

function ConfigStatus() {
  const config = useQuery({ queryKey: queryKeys.config, queryFn: api.config });

  if (config.isPending) {
    return (
      <span data-testid="mode-badge" data-mode="unknown" className="rounded border border-line px-2 py-1 text-xs text-ink-muted">
        Checking mode…
      </span>
    );
  }
  if (config.isError) {
    return (
      <div className="flex items-center gap-2" role="alert">
        <span
          data-testid="mode-badge"
          data-mode="unreachable"
          className="rounded border border-danger/60 bg-danger/10 px-2 py-1 text-xs font-bold text-st-mismatched"
          title={`API base: ${API_BASE}`}
        >
          API UNREACHABLE
        </span>
        <Button variant="ghost" className="min-h-8 px-2 text-xs" onClick={() => config.refetch()}>
          Retry
        </Button>
      </div>
    );
  }

  const c = config.data;
  const isDemo = c.mode === "demo";
  return (
    <div className="flex flex-wrap items-center gap-x-3 gap-y-1 text-xs">
      <span
        data-testid="mode-badge"
        data-mode={c.mode}
        className={`rounded border px-2.5 py-1 text-sm font-bold tracking-widest ${
          isDemo ? "border-demo/60 bg-demo/15 text-demo" : "border-accent/60 bg-accent/15 text-accent"
        }`}
      >
        {isDemo ? "DEMO" : "LIVE"}
      </span>
      <dl className="hidden items-center gap-3 text-ink-muted md:flex">
        <div className="flex gap-1">
          <dt>credentials:</dt>
          <dd className="text-ink">{c.credentials_present ? "present" : "absent"}</dd>
        </div>
        <div className="flex gap-1">
          <dt>live approved:</dt>
          <dd className="text-ink">{c.live_approved ? "yes" : "no"}</dd>
        </div>
        <div className="hidden gap-1 lg:flex">
          <dt>models:</dt>
          <dd className="font-mono text-ink">
            {c.segmentation_model} · {c.extraction_model}
          </dd>
        </div>
      </dl>
    </div>
  );
}

export function AppHeader() {
  const pathname = usePathname();
  return (
    <header className="sticky top-0 z-30 border-b border-line bg-canvas/90 backdrop-blur">
      <div className="mx-auto flex max-w-[1440px] flex-wrap items-center justify-between gap-3 px-4 py-3 sm:px-6">
        <div className="flex items-center gap-6">
          <Link href="/" className="flex items-center gap-2 font-semibold tracking-tight">
            <span aria-hidden="true" className="grid h-7 w-7 place-items-center rounded bg-accent/15 font-mono text-accent">
              AG
            </span>
            AuditGlimmer
          </Link>
          <nav aria-label="Main" className="flex gap-1 text-sm">
            {NAV.map((item) => {
              const isActive = pathname === item.href;
              return (
                <Link
                  key={item.href}
                  href={item.href}
                  aria-current={isActive ? "page" : undefined}
                  className={`rounded px-2.5 py-1.5 ${isActive ? "bg-surface-3 text-ink" : "text-ink-muted hover:text-ink"}`}
                >
                  {item.label}
                </Link>
              );
            })}
          </nav>
        </div>
        <ConfigStatus />
      </div>
    </header>
  );
}
