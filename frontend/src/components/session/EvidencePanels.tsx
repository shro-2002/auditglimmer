import { DecisionChip, FlagList, ModeTag } from "@/components/ui/Badges";
import { Card, Field } from "@/components/ui/primitives";
import { formatDateTime, formatFraction, formatNumber } from "@/lib/format";
import type { DetectionBundle, LedgerRecord, MatchDecision, Mode, ProviderCall, ReviewAction } from "@/lib/types";

/** DEMO confidences are written into fixtures by hand; never let them read as a model score. */
export function confidenceLabel(mode: Mode, kind: "Detector" | "Model"): string {
  return mode === "demo" ? "Fixture-authored confidence (not a model score)" : `${kind} confidence (model-reported, uncalibrated)`;
}

/** Full review chronology, oldest first. A list, not a table, so it fits the narrow decision panel. */
export function ReviewHistory({ history }: { history: ReviewAction[] }) {
  if (history.length === 0) return null;
  return (
    <div data-testid="review-history">
      <p className="text-xs uppercase tracking-wider text-ink-faint">Review history ({history.length}, oldest first)</p>
      <ol className="mt-1 divide-y divide-line rounded-md border border-line text-sm">
        {history.map((r) => (
          <li key={r.id} className="space-y-0.5 px-3 py-2">
            <p className="flex flex-wrap items-center gap-x-2">
              <span className={`font-semibold uppercase ${r.action === "confirm" ? "text-st-human" : "text-st-mismatched"}`}>{r.action}</span>
              {r.asset_id && <span className="font-mono">{r.asset_id}</span>}
              <span>by {r.reviewer}</span>
              <time dateTime={r.created_at} className="text-xs text-ink-muted">
                {formatDateTime(r.created_at)}
              </time>
            </p>
            <p className="text-ink-muted">{r.note || "No note."}</p>
          </li>
        ))}
      </ol>
    </div>
  );
}

/** candidate_asset_ids are ledger asset IDs; fall back to internal row id in case the backend sends those. */
export function findLedgerRecord(records: LedgerRecord[], assetId: string): LedgerRecord | undefined {
  return records.find((r) => r.asset_id === assetId) ?? records.find((r) => r.id === assetId);
}

/** Tier 1 gate second read. Experimental safeguard: agreement is supporting evidence, not proof. */
function SecondRead({ confirmation }: { confirmation: Record<string, unknown> }) {
  const ev = confirmation.evidence as { visible_serial_number?: string | null } | null;
  const ok = confirmation.status === "ok";
  return (
    <div data-testid="second-read" className="border-t border-line pt-3">
      <p className="text-xs uppercase tracking-wider text-ink-faint">
        Second read (Tier 1 gate · experimental safeguard, not a safety guarantee)
      </p>
      <dl className="mt-2 grid grid-cols-2 gap-3">
        <Field label="Second-read serial" value={ok ? (ev?.visible_serial_number ?? "not visible") : `failed (${String(confirmation.status)})`} mono={ok} />
        <Field label="View" value={String(confirmation.view ?? "—")} />
      </dl>
    </div>
  );
}

export function EvidencePanel({ bundle, call }: { bundle: DetectionBundle; call: ProviderCall | undefined }) {
  const { detection, evidence: record } = bundle;
  const ev = record?.evidence ?? null;
  return (
    <Card testId="evidence-panel" title="Structured visual evidence" actions={record && <ModeTag mode={record.mode} />}>
      <div className="space-y-4">
        <dl className="grid grid-cols-2 gap-3">
          <Field label="Detection" value={`${detection.concept} · provider object id ${detection.object_index}`} />
          <Field
            label="Segmentation"
            value={
              detection.provider === "full-frame"
                ? "SAM skipped — whole photo declared as one region by the auditor (no claim it shows the registered unit)"
                : `${detection.provider} · ${detection.model}`
            }
            mono={detection.provider !== "full-frame"}
          />
          <Field label={confidenceLabel(detection.mode, "Detector")} value={formatFraction(detection.confidence)} />
          <Field label="Mask encoding" value={detection.mask.encoding} mono />
        </dl>

        {!record && <p className="text-sm text-ink-muted">No extraction recorded for this detection.</p>}
        {record && record.status !== "ok" && (
          <div role="alert" className="rounded-md border border-danger/40 bg-danger/10 p-3 text-sm">
            <p className="font-semibold text-st-mismatched">Extraction {record.status}</p>
            <p className="mt-1">{record.error ?? "No usable evidence was produced."}</p>
          </div>
        )}

        {ev && (
          <>
            <dl className="grid grid-cols-2 gap-3 border-t border-line pt-3">
              <Field label="Observed object" value={ev.observed_object_type} />
              <Field label="Visible manufacturer" value={ev.visible_manufacturer ?? "not visible"} />
              <Field label="Visible model" value={ev.visible_model ?? "not visible"} />
              <Field label="Visible serial" value={ev.visible_serial_number ?? "not visible"} mono />
              <Field label={confidenceLabel(record?.mode ?? detection.mode, "Model")} value={formatFraction(ev.model_confidence)} />
            </dl>
            {ev.visible_identifiers.length > 0 && (
              <div>
                <p className="text-xs uppercase tracking-wider text-ink-faint">Visible identifiers</p>
                <ul className="mt-1 space-y-1 text-sm">
                  {ev.visible_identifiers.map((idf, i) => (
                    <li key={`${idf.kind}-${i}`} className="flex flex-wrap gap-2">
                      <span className="text-ink-muted">{idf.kind}</span>
                      <span className="font-mono">{idf.value}</span>
                      {!idf.readable && <span className="text-st-probable">(partially readable)</span>}
                    </li>
                  ))}
                </ul>
              </div>
            )}
            {ev.visible_condition_observations.length > 0 && (
              <div>
                <p className="text-xs uppercase tracking-wider text-ink-faint">Condition observations</p>
                <ul className="mt-1 list-disc space-y-0.5 pl-5 text-sm">
                  {ev.visible_condition_observations.map((o, i) => (
                    <li key={i}>{o}</li>
                  ))}
                </ul>
              </div>
            )}
            <div>
              <p className="text-xs uppercase tracking-wider text-ink-faint">Uncertainties</p>
              {ev.uncertainties.length === 0 ? (
                <p className="mt-1 text-sm text-ink-muted">None reported.</p>
              ) : (
                <ul className="mt-1 space-y-1 text-sm">
                  {ev.uncertainties.map((u, i) => (
                    <li key={i} className="rounded border-l-2 border-st-probable/60 bg-surface-2 px-2 py-1">
                      {u.field && <span className="mr-2 font-mono text-xs text-st-probable">{u.field}</span>}
                      {u.note}
                    </li>
                  ))}
                </ul>
              )}
            </div>
          </>
        )}

        {record?.confirmation && <SecondRead confirmation={record.confirmation} />}

        {record && (
          <dl className="grid grid-cols-2 gap-3 border-t border-line pt-3">
            <Field label="Extraction provider" value={`${record.provider} · ${record.model}`} mono />
            <Field label="Extraction latency" value={call ? `${formatNumber(call.latency_ms)} ms` : "—"} />
          </dl>
        )}
      </div>
    </Card>
  );
}

export function DecisionPanel({ decision, ledger }: { decision: MatchDecision | null; ledger: LedgerRecord[] }) {
  if (!decision) {
    return (
      <Card testId="decision-panel" title="Match decision">
        <p className="text-sm text-ink-muted">No match decision for this detection yet.</p>
      </Card>
    );
  }
  return (
    <Card testId="decision-panel" title="Match decision" actions={<DecisionChip decision={decision.decision} />}>
      <div className="space-y-3">
        <p className="text-sm">{decision.explanation}</p>
        <dl className="grid grid-cols-2 gap-3">
          <Field label="Tier" value={decision.tier ?? "—"} />
          <Field label="Matching rule" value={decision.matching_rule} mono />
          <Field label="Rule score — not a probability" value={decision.match_score.toFixed(2)} />
          <Field label="Matched asset" value={decision.matched_asset_id ?? "none"} mono />
          <Field label="Review" value={decision.review ? `${decision.review.action} by ${decision.review.reviewer}` : decision.review_required ? "required — pending" : "not required"} />
        </dl>
        <FlagList flags={decision.flags} />
        {decision.unmatched_fields.length > 0 && (
          <p className="text-xs text-ink-muted">
            Unmatched fields: <span className="font-mono">{decision.unmatched_fields.join(", ")}</span>
          </p>
        )}
        <div>
          <p className="text-xs uppercase tracking-wider text-ink-faint">Candidate ledger rows ({decision.candidate_asset_ids.length})</p>
          {decision.candidate_asset_ids.length === 0 ? (
            <p className="mt-1 text-sm text-ink-muted">No candidate rows.</p>
          ) : (
            <ul className="mt-1 divide-y divide-line rounded-md border border-line text-sm">
              {decision.candidate_asset_ids.map((aid) => {
                const r = findLedgerRecord(ledger, aid);
                return (
                  <li key={aid} className="flex flex-wrap justify-between gap-2 px-3 py-2">
                    <span className="font-mono">{aid}</span>
                    <span className="text-ink-muted">
                      {r ? `${r.manufacturer ?? "?"} ${r.model ?? ""} · SN ${r.serial_number ?? "—"} · row ${r.source_row}` : "not in loaded ledger"}
                    </span>
                  </li>
                );
              })}
            </ul>
          )}
        </div>
        <ReviewHistory history={decision.review_history ?? []} />
      </div>
    </Card>
  );
}
