"use client";

import { useQuery } from "@tanstack/react-query";

import { ASSET_STATUSES, DecisionChip, FlagTag, HUMAN_CONFIRMED_NOTE, StatusChip, UNVERIFIED_NOTE } from "@/components/ui/Badges";
import { Card, EmptyState, ErrorState, SkeletonRows, Stat, TABLE, TableWrap, TD, TH } from "@/components/ui/primitives";
import { api, queryKeys } from "@/lib/api";
import { formatDateTime, shortId } from "@/lib/format";
import { useSessionId } from "@/lib/use-session-id";

export default function ReconciliationPage() {
  const id = useSessionId();
  const recon = useQuery({ queryKey: queryKeys.reconciliation(id), queryFn: () => api.reconciliation(id) });
  const ledger = useQuery({ queryKey: queryKeys.ledger(id), queryFn: () => api.ledger(id) });

  if (recon.isPending) return <SkeletonRows rows={8} label="Loading reconciliation" />;
  if (recon.isError) return <ErrorState error={recon.error} onRetry={() => recon.refetch()} />;

  const { summary, assets, decisions } = recon.data;
  const recordById = new Map((ledger.data ?? []).map((r) => [r.id, r]));

  return (
    <div className="space-y-5">
      <div className="grid grid-cols-2 gap-3 md:grid-cols-3 xl:grid-cols-6">
        {ASSET_STATUSES.map((s) => (
          <div key={s} className="rounded-lg border border-line bg-surface-2 p-3">
            <StatusChip status={s} />
            <p className="tabular mt-2 text-2xl font-semibold">{summary.by_status[s] ?? 0}</p>
          </div>
        ))}
      </div>
      <p role="note" className="rounded-md border border-st-unverified/30 bg-surface-2 px-3 py-2 text-sm text-st-unverified">
        {UNVERIFIED_NOTE}
      </p>
      <p role="note" className="rounded-md border border-st-human/30 bg-surface-2 px-3 py-2 text-sm text-st-human">
        {HUMAN_CONFIRMED_NOTE}
      </p>
      <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
        <Stat label="Ledger assets" value={summary.assets_total} />
        <Stat label="Decisions" value={summary.decisions_total} />
        <Stat label="Review required" value={summary.review_required} />
        <Stat label="Reviewed" value={summary.reviewed} />
      </div>
      <p className="text-xs text-ink-faint">
        Computed {formatDateTime(recon.data.computed_at)} · concepts inspected:{" "}
        {summary.inspected_concepts.length ? summary.inspected_concepts.join(", ") : "none"}
      </p>

      <Card title={`Assets (${assets.length})`}>
        {assets.length === 0 ? (
          <EmptyState title="No ledger assets to reconcile">Upload a ledger first.</EmptyState>
        ) : (
          <TableWrap label="Asset reconciliation">
            <table data-testid="reconciliation-table" className={TABLE}>
              <thead>
                <tr>
                  {["Asset", "Ledger row", "Status", "Reason", "Human confirmed", "Decisions"].map((h) => (
                    <th key={h} scope="col" className={TH}>
                      {h}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {assets.map((a) => {
                  const rec = recordById.get(a.ledger_record_id);
                  return (
                    <tr key={a.ledger_record_id} data-status={a.status} className="hover:bg-surface-2">
                      <td className={`${TD} font-mono`}>{a.asset_id}</td>
                      <td className={`${TD} text-ink-muted`}>
                        {rec ? `#${rec.source_row} · ${rec.manufacturer ?? "?"} ${rec.model ?? ""}` : shortId(a.ledger_record_id)}
                      </td>
                      <td className={TD}>
                        <StatusChip status={a.status} />
                      </td>
                      <td className={TD}>
                        {a.reason}
                        {a.status === "UNVERIFIED" && (
                          <span className="mt-0.5 block text-xs text-ink-faint">Not adequately observed — not evidence of absence.</span>
                        )}
                      </td>
                      <td className={TD}>{a.human_confirmed ? "Yes" : "No"}</td>
                      <td className={`${TD} tabular`}>{a.decision_ids.length}</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </TableWrap>
        )}
      </Card>

      <Card title={`Match decisions (${decisions.length})`}>
        {decisions.length === 0 ? (
          <EmptyState title="No decisions yet">Run a visual inspection to produce evidence and decisions.</EmptyState>
        ) : (
          <TableWrap label="Match decisions">
            <table data-testid="decisions-table" className={TABLE}>
              <thead>
                <tr>
                  {["Decision", "Tier", "Matched asset", "Rule score (not a probability)", "Rule", "Explanation", "Flags"].map((h) => (
                    <th key={h} scope="col" className={TH}>
                      {h}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {decisions.map((d) => (
                  <tr key={d.id} className="hover:bg-surface-2">
                    <td className={TD}>
                      <DecisionChip decision={d.decision} />
                      {d.review_required && !d.review && <span className="mt-1 block text-xs text-st-probable">needs review</span>}
                      {d.review && (
                        <span className="mt-1 block text-xs text-ink-muted">
                          {d.review.action}ed by {d.review.reviewer}
                          {d.review_history.length > 1 && ` (${d.review_history.length} reviews)`}
                        </span>
                      )}
                    </td>
                    <td className={`${TD} tabular`}>{d.tier ?? "—"}</td>
                    <td className={`${TD} font-mono`}>{d.matched_asset_id ?? "—"}</td>
                    <td className={`${TD} tabular`}>{d.match_score.toFixed(2)}</td>
                    <td className={`${TD} font-mono text-xs`}>{d.matching_rule}</td>
                    <td className={TD}>{d.explanation}</td>
                    <td className={TD}>
                      <div className="flex flex-wrap gap-1">
                        {d.flags.length ? d.flags.map((f) => <FlagTag key={f} flag={f} />) : "—"}
                      </div>
                    </td>
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
