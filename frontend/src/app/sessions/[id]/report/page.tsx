"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { EvidenceModeNote } from "@/components/session/EvidenceModeNote";
import { Button, Card, ErrorState, Skeleton, SkeletonRows } from "@/components/ui/primitives";
import { api, invalidateSession, queryKeys } from "@/lib/api";
import type { ReportSummary } from "@/lib/types";
import { useSessionId } from "@/lib/use-session-id";

function ReportState({ report }: { report: ReportSummary }) {
  const isFinal = report.report_state === "FINAL";
  return (
    <div
      data-testid="report-state"
      data-state={report.report_state}
      className={`flex flex-wrap items-center gap-x-6 gap-y-2 rounded-md border p-4 ${
        isFinal ? "border-st-verified/40 bg-st-verified/5" : "border-st-probable/50 bg-st-probable/10"
      }`}
    >
      <p className={`text-2xl font-bold tracking-widest ${isFinal ? "text-st-verified" : "text-st-probable"}`}>{report.report_state}</p>
      <dl className="tabular flex gap-6 text-sm">
        <div>
          <dt className="text-xs uppercase tracking-wider text-ink-faint">Open reviews</dt>
          <dd data-testid="report-open-reviews" className="text-xl font-semibold">{report.open_reviews}</dd>
        </div>
        <div>
          <dt className="text-xs uppercase tracking-wider text-ink-faint">Conflicting reviews</dt>
          <dd className="text-xl font-semibold">{report.conflicting_reviews}</dd>
        </div>
      </dl>
      <p className="basis-full text-sm text-ink-muted">
        {isFinal
          ? "All decisions are reviewed. A downloaded export marks the session as reported."
          : "Draft: resolve open and conflicting reviews before exporting a final report. Viewing this page changes nothing."}
      </p>
    </div>
  );
}

export default function ReportPage() {
  const id = useSessionId();
  const queryClient = useQueryClient();
  const report = useQuery({ queryKey: queryKeys.report(id), queryFn: () => api.report(id) });
  const html = useQuery({ queryKey: queryKeys.reportHtml(id), queryFn: () => api.reportHtml(id) });
  const download = useMutation({
    mutationFn: (format: "html" | "csv") => api.downloadReport(id, format),
    // A final export can move the session to "reported"; refresh the header.
    onSuccess: () => invalidateSession(queryClient, id),
  });

  return (
    <div className="space-y-5">
      <Card title="Audit report">
        {report.isPending && <SkeletonRows rows={2} label="Loading report state" />}
        {report.isError && <ErrorState error={report.error} onRetry={() => report.refetch()} />}
        {report.data && (
          <div className="space-y-3">
            <ReportState report={report.data} />
            <EvidenceModeNote callModes={report.data.provider_modes_used} serverMode={report.data.mode} />
          </div>
        )}
        <div className="mt-4 flex flex-wrap gap-2">
          <Button data-testid="report-download-html" variant="primary" disabled={download.isPending} onClick={() => download.mutate("html")}>
            Export HTML report
          </Button>
          <Button data-testid="report-download-csv" disabled={download.isPending} onClick={() => download.mutate("csv")}>
            Export CSV
          </Button>
        </div>
        {download.isError && (
          <div className="mt-3">
            <ErrorState title="Export failed" error={download.error} />
          </div>
        )}
      </Card>
      <Card title="Report preview">
        {html.isPending && <Skeleton className="h-[60vh] w-full" />}
        {html.isError && <ErrorState error={html.error} onRetry={() => html.refetch()} />}
        {html.data && (
          // Empty sandbox: the backend HTML renders with no scripts, forms or same-origin access.
          <iframe
            data-testid="report-frame"
            title="Audit report preview"
            sandbox=""
            srcDoc={html.data}
            className="h-[75vh] w-full rounded-md border border-line bg-white"
          />
        )}
      </Card>
    </div>
  );
}
