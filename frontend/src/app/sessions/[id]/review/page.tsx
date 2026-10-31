"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";

import { findLedgerRecord, ReviewHistory } from "@/components/session/EvidencePanels";
import { regionTone } from "@/components/session/MaskViewer";
import { DecisionChip, FlagList, ModeTag } from "@/components/ui/Badges";
import { Button, Card, EmptyState, ErrorState, SkeletonRows } from "@/components/ui/primitives";
import { api, ApiError, invalidateSession, queryKeys, urls } from "@/lib/api";
import type { DetectionBundle, ImageAsset, LedgerRecord, MatchDecision } from "@/lib/types";
import { useSessionId } from "@/lib/use-session-id";

const CROP_PAD = 0.08;
// Mirrors backend rules (422/400) so the reviewer sees the problem before submitting.
const REVIEWER_MIN = 2;
const CONFIRM_NOTE_MIN = 10;
const HAS_LETTER = /\p{L}/u;

function reviewerError(reviewer: string): string | null {
  const trimmed = reviewer.trim();
  return trimmed.length >= REVIEWER_MIN && HAS_LETTER.test(trimmed)
    ? null
    : `Enter your name (at least ${REVIEWER_MIN} characters, including a letter).`;
}

function noteError(note: string): string | null {
  const count = note.replace(/\s/g, "").length;
  return count >= CONFIRM_NOTE_MIN ? null : `A confirmation needs a note of at least ${CONFIRM_NOTE_MIN} characters (${count} so far).`;
}

const INPUT = "mt-1 block min-h-10 w-full rounded-md border border-line-strong bg-surface-2 px-3 text-sm focus:border-accent focus:outline-none";

/** Crops via SVG viewBox: no canvas, no re-encoding, mask stays aligned. */
function EvidenceCrop({ bundle, image }: { bundle: DetectionBundle; image: ImageAsset }) {
  const { mask } = bundle.detection;
  const box = bundle.evidence?.evidence?.evidence_references[0]?.crop_box ?? mask.bounds;
  const [x1, y1, x2, y2] = box;
  const padX = (x2 - x1) * CROP_PAD;
  const padY = (y2 - y1) * CROP_PAD;
  const vx = Math.max(x1 - padX, 0);
  const vy = Math.max(y1 - padY, 0);
  const vw = Math.min(x2 + padX, image.width) - vx;
  const vh = Math.min(y2 + padY, image.height) - vy;
  const [bx1, by1, bx2, by2] = mask.bounds;
  return (
    <svg
      viewBox={`${vx} ${vy} ${vw} ${vh}`}
      role="img"
      aria-label={`Evidence crop from ${image.filename}`}
      className="h-48 w-full rounded-md border border-line bg-canvas"
    >
      <image href={urls.image(image)} width={image.width} height={image.height} />
      <g transform={`translate(${bx1} ${by1}) scale(${(bx2 - bx1) / mask.raster_w} ${(by2 - by1) / mask.raster_h})`}>
        <path d={mask.svg_path} fill={regionTone(bundle)} fillOpacity={0.25} stroke={regionTone(bundle)} vectorEffect="non-scaling-stroke" fillRule="evenodd" />
      </g>
    </svg>
  );
}

type ItemProps = { decision: MatchDecision; bundle?: DetectionBundle; image?: ImageAsset; ledger: LedgerRecord[]; sessionId: string };

function ReviewItem({ decision, bundle, image, ledger, sessionId }: ItemProps) {
  const queryClient = useQueryClient();
  const [assetId, setAssetId] = useState<string>(decision.matched_asset_id ?? decision.candidate_asset_ids[0] ?? "");
  const [reviewer, setReviewer] = useState("");
  const [note, setNote] = useState("");
  const [attempted, setAttempted] = useState<"confirm" | "reject" | null>(null);
  const review = useMutation({
    mutationFn: (action: "confirm" | "reject") =>
      api.review(decision.id, { action, reviewer: reviewer.trim(), note: note.trim(), asset_id: action === "confirm" ? assetId : null }),
    onSuccess: () => invalidateSession(queryClient, sessionId),
  });
  const isConflict = review.error instanceof ApiError && review.error.status === 409;
  const nameProblem = attempted ? reviewerError(reviewer) : null;
  const noteProblem = attempted === "confirm" ? noteError(note) : null;

  function submit(action: "confirm" | "reject") {
    setAttempted(action);
    if (reviewerError(reviewer) || (action === "confirm" && noteError(note))) return;
    review.mutate(action);
  }
  const ev = bundle?.evidence?.evidence;

  return (
    <li data-testid={`review-item-${decision.id}`}>
      <Card title={<span className="flex flex-wrap items-center gap-2"><DecisionChip decision={decision.decision} /> <span className="font-mono text-xs text-ink-muted">{decision.id}</span></span>} actions={bundle && <ModeTag mode={bundle.detection.mode} />}>
        <div className="grid gap-4 lg:grid-cols-[280px_minmax(0,1fr)_minmax(0,1fr)]">
          <div className="space-y-2 text-sm">
            {bundle && image ? <EvidenceCrop bundle={bundle} image={image} /> : <p className="text-ink-muted">Evidence crop unavailable.</p>}
            {ev && (
              <p className="text-ink-muted">
                {ev.observed_object_type} · {ev.visible_manufacturer ?? "?"} {ev.visible_model ?? ""} · SN{" "}
                <span className="font-mono text-ink">{ev.visible_serial_number ?? "not visible"}</span>
              </p>
            )}
          </div>
          <div className="space-y-2 text-sm">
            <p>{decision.explanation}</p>
            <p className="text-xs text-ink-muted">
              Rule score — not a probability: <span className="tabular text-ink">{decision.match_score.toFixed(2)}</span> · rule{" "}
              <span className="font-mono">{decision.matching_rule}</span>
            </p>
            <FlagList flags={decision.flags} />
            <fieldset>
              <legend className="text-xs uppercase tracking-wider text-ink-faint">Candidate ledger rows</legend>
              {decision.candidate_asset_ids.length === 0 && <p className="mt-1 text-ink-muted">No candidates — confirm is unavailable.</p>}
              <div className="mt-1 space-y-1">
                {decision.candidate_asset_ids.map((aid) => {
                  const r = findLedgerRecord(ledger, aid);
                  return (
                    <label key={aid} className="flex min-h-10 cursor-pointer items-start gap-2 rounded border border-line px-2 py-1.5 has-[:checked]:border-accent">
                      <input type="radio" name={`asset-${decision.id}`} value={aid} checked={assetId === aid} onChange={() => setAssetId(aid)} className="mt-1 accent-[#2dd4bf]" />
                      <span>
                        <span className="font-mono">{aid}</span>
                        {r && <span className="block text-xs text-ink-muted">{r.manufacturer ?? "?"} {r.model ?? ""} · SN {r.serial_number ?? "—"} · row {r.source_row}</span>}
                      </span>
                    </label>
                  );
                })}
              </div>
            </fieldset>
          </div>
          <form className="space-y-3" noValidate onSubmit={(e) => e.preventDefault()}>
            <div>
              <label htmlFor={`reviewer-${decision.id}`} className="text-sm font-medium">Reviewer name</label>
              <input
                id={`reviewer-${decision.id}`}
                className={INPUT}
                value={reviewer}
                required
                aria-invalid={!!nameProblem}
                aria-describedby={nameProblem ? `reviewer-error-${decision.id}` : undefined}
                onChange={(e) => setReviewer(e.target.value)}
                autoComplete="name"
              />
              {nameProblem && <p id={`reviewer-error-${decision.id}`} className="mt-1 text-xs text-st-mismatched">{nameProblem}</p>}
            </div>
            <div>
              <label htmlFor={`note-${decision.id}`} className="text-sm font-medium">Note <span className="font-normal text-ink-muted">(required to confirm)</span></label>
              <textarea
                id={`note-${decision.id}`}
                className={`${INPUT} py-2`}
                rows={3}
                value={note}
                aria-invalid={!!noteProblem}
                aria-describedby={`note-help-${decision.id}${noteProblem ? ` note-error-${decision.id}` : ""}`}
                onChange={(e) => setNote(e.target.value)}
              />
              <p id={`note-help-${decision.id}`} className="mt-1 text-xs text-ink-muted">
                Say what evidence supports this identity; human confirmations are reported separately from identifier matches.
              </p>
              {noteProblem && <p id={`note-error-${decision.id}`} className="mt-1 text-xs text-st-mismatched">{noteProblem}</p>}
            </div>
            <div className="flex flex-wrap gap-2">
              <Button variant="primary" data-testid="confirm-button" disabled={!assetId || review.isPending} onClick={() => submit("confirm")}>
                Confirm match
              </Button>
              <Button variant="danger" data-testid="reject-button" disabled={review.isPending} onClick={() => submit("reject")}>
                Reject
              </Button>
            </div>
            {review.isError && (
              <ErrorState title={isConflict ? "Conflict — review not recorded" : "Review not recorded"} error={review.error} />
            )}
          </form>
        </div>
        {(decision.review_history ?? []).length > 0 && (
          <div className="mt-4 border-t border-line pt-3">
            <ReviewHistory history={decision.review_history} />
          </div>
        )}
      </Card>
    </li>
  );
}

export default function ReviewPage() {
  const id = useSessionId();
  const queue = useQuery({ queryKey: queryKeys.reviewQueue(id), queryFn: () => api.reviewQueue(id) });
  const detections = useQuery({ queryKey: queryKeys.detections(id), queryFn: () => api.detections(id) });
  const images = useQuery({ queryKey: queryKeys.images(id), queryFn: () => api.images(id) });
  const ledger = useQuery({ queryKey: queryKeys.ledger(id), queryFn: () => api.ledger(id) });

  if (queue.isPending) return <SkeletonRows rows={4} label="Loading review queue" />;
  if (queue.isError) return <ErrorState error={queue.error} onRetry={() => queue.refetch()} />;
  if (queue.data.length === 0) {
    return <EmptyState title="Review queue is empty">No uncertain matches are awaiting a human decision.</EmptyState>;
  }

  return (
    <div className="space-y-3">
      <p className="text-sm text-ink-muted" aria-live="polite">{queue.data.length} decision(s) awaiting human review.</p>
      <ul className="space-y-4">
        {queue.data.map((d) => {
          const bundle = detections.data?.find((b) => b.detection.id === d.detection_id);
          return (
            <ReviewItem
              key={d.id}
              decision={d}
              bundle={bundle}
              image={images.data?.find((img) => img.id === d.image_id)}
              ledger={ledger.data ?? []}
              sessionId={id}
            />
          );
        })}
      </ul>
    </div>
  );
}
