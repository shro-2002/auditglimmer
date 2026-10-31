"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";

import { Button, Card, EmptyState, ErrorState, SkeletonRows, TABLE, TableWrap, TD, TH } from "@/components/ui/primitives";
import { api, invalidateSession, queryKeys, withReplaceConsent } from "@/lib/api";
import { formatMoney } from "@/lib/format";
import type { LedgerUploadResult } from "@/lib/types";
import { useSessionId } from "@/lib/use-session-id";

function UploadSummary({ result }: { result: LedgerUploadResult }) {
  return (
    <div className="space-y-3">
      <dl className="tabular grid grid-cols-2 gap-3 sm:grid-cols-4">
        <div className="rounded-md border border-st-verified/30 bg-st-verified/5 p-3">
          <dt className="text-xs uppercase tracking-wider text-ink-faint">Accepted rows</dt>
          <dd className="text-2xl font-semibold text-st-verified">{result.accepted}</dd>
        </div>
        <div className="rounded-md border border-st-mismatched/30 bg-st-mismatched/5 p-3">
          <dt className="text-xs uppercase tracking-wider text-ink-faint">Rejected rows</dt>
          <dd className="text-2xl font-semibold text-st-mismatched">{result.rejected}</dd>
        </div>
        <div className="col-span-2 rounded-md border border-line bg-surface-2 p-3">
          <dt className="text-xs uppercase tracking-wider text-ink-faint">File SHA-256 (provenance)</dt>
          <dd className="truncate font-mono text-xs text-ink" title={result.file_sha256}>
            {result.file_sha256}
          </dd>
        </div>
      </dl>
      {result.issues.length === 0 ? (
        <p className="text-sm text-ink-muted">No validation issues.</p>
      ) : (
        <TableWrap label="Ledger validation issues">
          <table className={TABLE}>
            <caption className="sr-only">Validation issues ({result.issues.length})</caption>
            <thead>
              <tr>
                {["Row", "Field", "Severity", "Code", "Message"].map((h) => (
                  <th key={h} scope="col" className={TH}>
                    {h}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {result.issues.map((issue, i) => (
                <tr key={`${issue.row}-${issue.code}-${i}`}>
                  <td className={`${TD} tabular`}>{issue.row}</td>
                  <td className={`${TD} font-mono`}>{issue.field ?? "—"}</td>
                  <td className={TD}>
                    <span className={issue.severity === "error" ? "text-st-mismatched" : "text-st-probable"}>
                      {issue.severity.toUpperCase()}
                    </span>
                  </td>
                  <td className={`${TD} font-mono text-xs`}>{issue.code}</td>
                  <td className={TD}>{issue.message}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </TableWrap>
      )}
    </div>
  );
}

export default function LedgerPage() {
  const id = useSessionId();
  const queryClient = useQueryClient();
  const [lastResult, setLastResult] = useState<LedgerUploadResult | null>(null);
  const [file, setFile] = useState<File | null>(null);

  const config = useQuery({ queryKey: queryKeys.config, queryFn: api.config });
  const ledger = useQuery({ queryKey: queryKeys.ledger(id), queryFn: () => api.ledger(id) });

  const upload = useMutation({
    mutationFn: (f: File) => withReplaceConsent((replace) => api.uploadLedger(id, f, replace)),
    onSuccess: (result) => {
      setLastResult(result);
      invalidateSession(queryClient, id);
    },
  });
  const demo = useMutation({
    mutationFn: () => withReplaceConsent((replace) => api.loadDemo(id, replace)),
    onSuccess: (result) => {
      setLastResult(result.ledger);
      invalidateSession(queryClient, id);
    },
  });

  const records = ledger.data ?? [];

  return (
    <div className="space-y-5">
      <Card
        title="Ledger upload & validation"
        actions={
          config.data?.mode === "demo" && (
            <Button data-testid="load-demo-button" variant="primary" disabled={demo.isPending} onClick={() => demo.mutate()}>
              {demo.isPending ? "Loading demo dataset…" : "Load demo dataset"}
            </Button>
          )
        }
      >
        <form
          className="flex flex-wrap items-end gap-3"
          onSubmit={(e) => {
            e.preventDefault();
            if (file) upload.mutate(file);
          }}
        >
          <div>
            <label htmlFor="ledger-file" className="text-sm font-medium">
              Ledger CSV (≤ 2 MB, replaces current ledger)
            </label>
            <input
              id="ledger-file"
              type="file"
              accept=".csv,text/csv"
              className="mt-1 block text-sm text-ink-muted file:mr-3 file:min-h-10 file:rounded-md file:border file:border-line-strong file:bg-surface-3 file:px-3 file:text-ink"
              onChange={(e) => setFile(e.target.files?.[0] ?? null)}
            />
          </div>
          <Button type="submit" disabled={!file || upload.isPending}>
            {upload.isPending ? "Validating…" : "Upload & validate"}
          </Button>
        </form>
        <div className="mt-4 space-y-3" data-testid="ledger-summary" aria-live="polite">
          {upload.isError && <ErrorState title="Ledger upload failed" error={upload.error} />}
          {demo.isError && <ErrorState title="Demo dataset could not be loaded" error={demo.error} />}
          {lastResult ? (
            <UploadSummary result={lastResult} />
          ) : (
            <p className="text-sm text-ink-muted">
              {ledger.data
                ? `${records.length} ledger records on file. Upload a CSV to see per-row validation results.`
                : "Upload a CSV to validate it."}
            </p>
          )}
        </div>
      </Card>

      <Card title={`Ledger records${ledger.data ? ` (${records.length})` : ""}`}>
        {ledger.isPending && <SkeletonRows label="Loading ledger" />}
        {ledger.isError && <ErrorState error={ledger.error} onRetry={() => ledger.refetch()} />}
        {ledger.data && records.length === 0 && (
          <EmptyState title="No ledger records">Upload the bank or insurer&apos;s asset register as CSV.</EmptyState>
        )}
        {records.length > 0 && (
          <TableWrap label="Ledger records">
            <table className={TABLE}>
              <thead>
                <tr>
                  {["CSV row", "Asset ID", "Type", "Manufacturer", "Model", "Serial", "Location", "Value"].map((h) => (
                    <th key={h} scope="col" className={TH}>
                      {h}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {records.map((r) => (
                  <tr key={r.id} className="hover:bg-surface-2">
                    <td className={`${TD} tabular text-ink-muted`}>{r.source_row}</td>
                    <td className={`${TD} font-mono`}>{r.asset_id}</td>
                    <td className={TD}>{r.asset_type}</td>
                    <td className={TD}>{r.manufacturer ?? "—"}</td>
                    <td className={TD}>{r.model ?? "—"}</td>
                    <td className={`${TD} font-mono`}>{r.serial_number ?? "—"}</td>
                    <td className={TD}>{r.expected_location ?? "—"}</td>
                    <td className={`${TD} tabular text-right`}>{formatMoney(r.ledger_value, r.currency)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </TableWrap>
        )}
      </Card>
    </div>
  );
}
