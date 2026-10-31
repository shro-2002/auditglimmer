"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useCallback, useRef, useState } from "react";

import { DecisionPanel, EvidencePanel } from "@/components/session/EvidencePanels";
import { MaskViewer, regionTone } from "@/components/session/MaskViewer";
import { RunProgress } from "@/components/session/RunProgress";
import { DecisionChip, ModeTag } from "@/components/ui/Badges";
import { Button, Card, EmptyState, ErrorState, Skeleton } from "@/components/ui/primitives";
import { api, ApiError, invalidateSession, queryKeys, urls } from "@/lib/api";
import { formatFraction } from "@/lib/format";
import { useSessionId } from "@/lib/use-session-id";

const CONCEPT_MIN = 2;
const CONCEPT_MAX = 60;
const SUPPORTED_CONCEPTS = [
  "compressor", "electric motor", "electrical equipment", "elevator", "engine", "excavator", "forklift", "generator",
  "locomotive", "outboard motor", "pump", "racking", "roller", "switchgear", "telehandler", "tractor", "transformer",
  "wheel loader",
];
const ACTIVE_RUN: string[] = ["queued", "running"];
const ACTIVE_POLL_MS = 2_000;

export default function InspectPage() {
  const id = useSessionId();
  const queryClient = useQueryClient();
  // generator first: in the guided demo it is the bay where a serial-backed VERIFIED match appears (N-02)
  const [concept, setConcept] = useState("generator");
  const [activeRunId, setActiveRunId] = useState<string | null>(null);
  const [pickedImageId, setPickedImageId] = useState<string | null>(null);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [hoveredId, setHoveredId] = useState<string | null>(null);
  const [showMasks, setShowMasks] = useState(true);
  const [extractChoice, setExtractChoice] = useState<boolean | null>(null);
  const [fullFrame, setFullFrame] = useState(false);

  const images = useQuery({ queryKey: queryKeys.images(id), queryFn: () => api.images(id) });
  const detections = useQuery({ queryKey: queryKeys.detections(id), queryFn: () => api.detections(id) });
  const ledger = useQuery({ queryKey: queryKeys.ledger(id), queryFn: () => api.ledger(id) });
  // Polls while any run for this session is active (including ones started in another tab).
  const trace = useQuery({
    queryKey: queryKeys.trace(id),
    queryFn: () => api.trace(id),
    refetchInterval: (q) => (q.state.data?.runs.some((r) => ACTIVE_RUN.includes(r.status)) ? ACTIVE_POLL_MS : false),
  });
  const config = useQuery({ queryKey: queryKeys.config, queryFn: api.config });
  const isLive = config.data?.mode === "live";
  // LIVE defaults to segment-only so every paid extraction is a deliberate, per-region choice.
  const extractAll = extractChoice ?? !isLive;

  const [isRunStreaming, setIsRunStreaming] = useState(false);
  // Synchronous guard: a double-click lands before React re-renders the disabled button.
  const isSubmitting = useRef(false);
  const startRun = useMutation({
    mutationFn: () =>
      api.createRun(id, { concept: concept.trim(), extract: extractAll, region: fullFrame ? "full_frame" : "sam" }),
    onSuccess: (run) => {
      setActiveRunId(run.id);
      setIsRunStreaming(true);
    },
    onError: (err) => {
      if (err instanceof ApiError && err.code === "RUN_IN_PROGRESS") queryClient.invalidateQueries({ queryKey: queryKeys.trace(id) });
    },
    onSettled: () => {
      isSubmitting.current = false;
    },
  });
  const extractRegion = useMutation({
    mutationFn: (detectionId: string) => api.extractDetection(detectionId),
    onSuccess: () => invalidateSession(queryClient, id),
  });
  const handleRunEnd = useCallback(() => {
    setIsRunStreaming(false);
    // Drop any manual pick so the view lands on the first image that has detections.
    setPickedImageId(null);
    setSelectedId(null);
    invalidateSession(queryClient, id);
  }, [queryClient, id]);
  const isRunActive = isRunStreaming || !!trace.data?.runs.some((r) => ACTIVE_RUN.includes(r.status));
  const isRunInProgressError = startRun.error instanceof ApiError && startRun.error.code === "RUN_IN_PROGRESS";

  const imageList = images.data ?? [];
  const firstWithDetections = imageList.find((img) => (detections.data ?? []).some((b) => b.detection.image_id === img.id));
  const image = imageList.find((img) => img.id === pickedImageId) ?? firstWithDetections ?? imageList[0];
  const regions = (detections.data ?? []).filter((b) => b.detection.image_id === image?.id);
  const selected = regions.find((b) => b.detection.id === selectedId) ?? null;
  const selectedCall = trace.data?.provider_calls.find((c) => c.id === selected?.evidence?.provider_call_id);

  const trimmed = concept.trim();
  const conceptError = trimmed.length < CONCEPT_MIN ? `Concept must be ${CONCEPT_MIN}–${CONCEPT_MAX} characters.` : null;

  return (
    <div className="space-y-5">
      <Card title="Visual inspection workspace">
        <form
          className="flex flex-wrap items-end gap-3"
          onSubmit={(e) => {
            e.preventDefault();
            if (conceptError || isSubmitting.current) return;
            isSubmitting.current = true;
            startRun.mutate();
          }}
        >
          <div className="min-w-[220px] flex-1">
            <label htmlFor="concept" className="text-sm font-medium">
              Concept to segment
            </label>
            <input
              id="concept"
              data-testid="concept-input"
              value={concept}
              maxLength={CONCEPT_MAX}
              onChange={(e) => setConcept(e.target.value)}
              list="supported-concepts"
              aria-describedby="concept-help"
              aria-invalid={!!conceptError}
              className="mt-1 block min-h-10 w-full rounded-md border border-line-strong bg-surface-2 px-3 font-mono text-sm focus:border-accent focus:outline-none"
            />
            <datalist id="supported-concepts">
              {SUPPORTED_CONCEPTS.map((c) => (
                <option key={c} value={c} />
              ))}
            </datalist>
            <p id="concept-help" className="mt-1 text-xs text-ink-muted">
              {conceptError ?? `Supported asset types: ${SUPPORTED_CONCEPTS.join(", ")}. Runs across all session images.`}
            </p>
          </div>
          <Button
            type="submit"
            variant="primary"
            data-testid="run-button"
            disabled={!!conceptError || startRun.isPending || isRunActive || imageList.length === 0}
          >
            {startRun.isPending ? "Starting…" : isRunActive ? "Run in progress…" : "Run inspection"}
          </Button>
          <label className="flex min-h-10 basis-full items-center gap-2 text-sm text-ink-muted">
            <input
              type="checkbox"
              data-testid="extract-all-toggle"
              checked={extractAll}
              onChange={(e) => setExtractChoice(e.target.checked)}
              className="h-4 w-4 accent-[var(--color-accent,#2dd4bf)]"
            />
            Extract evidence for every detection now
            {isLive && <span className="text-xs">(each region is one paid Muse Spark call; leave off to choose regions)</span>}
          </label>
          <label className="flex min-h-10 basis-full items-center gap-2 text-sm text-ink-muted">
            <input
              type="checkbox"
              data-testid="full-frame-toggle"
              checked={fullFrame}
              onChange={(e) => setFullFrame(e.target.checked)}
              className="h-4 w-4 accent-[var(--color-accent,#2dd4bf)]"
            />
            Each photo is a close-up of one asset&apos;s nameplate (skip SAM; the whole photo becomes one region)
          </label>
        </form>
        <div className="mt-3 space-y-2">
          {isRunInProgressError && (
            <p role="status" className="rounded-md border border-st-probable/40 bg-st-probable/10 p-3 text-sm text-st-probable">
              An inspection is already running for this session. The button re-enables when it finishes.
            </p>
          )}
          {startRun.isError && !isRunInProgressError && <ErrorState title="Run was not started" error={startRun.error} />}
          {activeRunId ? (
            <RunProgress key={activeRunId} runId={activeRunId} onEnd={handleRunEnd} />
          ) : (
            <p data-testid="run-status" data-status="idle" role="status" aria-live="polite" className="text-sm text-ink-muted">
              No run started in this view. Past runs are listed under Observability.
            </p>
          )}
        </div>
      </Card>

      {images.isPending && <Skeleton className="h-[50vh] w-full" />}
      {images.isError && <ErrorState error={images.error} onRetry={() => images.refetch()} />}
      {images.data?.length === 0 && (
        <EmptyState title="No images in this session">Upload photos (or load the demo dataset) before running an inspection.</EmptyState>
      )}

      {image && (
        <div className="grid grid-cols-[minmax(0,1fr)] gap-5 xl:grid-cols-[minmax(0,1fr)_420px]">
          <div className="space-y-3">
            {imageList.length > 1 && (
              <div role="group" aria-label="Choose image" className="flex gap-2 overflow-x-auto pb-1">
                {imageList.map((img) => {
                  const isActive = img.id === image.id;
                  const count = (detections.data ?? []).filter((b) => b.detection.image_id === img.id).length;
                  return (
                    <button
                      key={img.id}
                      type="button"
                      aria-pressed={isActive}
                      onClick={() => {
                        setPickedImageId(img.id);
                        setSelectedId(null);
                      }}
                      className={`relative shrink-0 overflow-hidden rounded border-2 ${isActive ? "border-accent" : "border-line hover:border-line-strong"}`}
                    >
                      {/* eslint-disable-next-line @next/next/no-img-element -- dynamic API-hosted thumbnail */}
                      <img src={urls.image(img)} alt={img.filename} className="h-16 w-24 object-cover" />
                      <span className="tabular absolute bottom-0 right-0 bg-canvas/85 px-1 text-[11px]">{count}</span>
                    </button>
                  );
                })}
              </div>
            )}
            <div className="flex flex-wrap items-center justify-between gap-2 text-sm">
              <p className="truncate text-ink-muted">
                {image.filename} · <span className="tabular">{image.width}×{image.height}</span>
                {image.fixture && <span className="ml-2 text-demo">synthetic demo fixture</span>}
              </p>
              <label className="inline-flex min-h-10 items-center gap-2">
                <input type="checkbox" className="h-4 w-4 accent-[#2dd4bf]" checked={showMasks} onChange={(e) => setShowMasks(e.target.checked)} />
                Show masks
              </label>
            </div>
            <MaskViewer
              image={image}
              regions={regions}
              selectedId={selectedId}
              hoveredId={hoveredId}
              showMasks={showMasks}
              onSelect={setSelectedId}
              onHover={setHoveredId}
            />
          </div>

          <div className="space-y-4">
            <Card title={`Detected regions (${regions.length})`} bodyClassName="p-2">
              {detections.isPending && <Skeleton className="h-24 w-full" />}
              {detections.isError && <ErrorState error={detections.error} onRetry={() => detections.refetch()} />}
              {detections.data && regions.length === 0 && (
                <p className="p-2 text-sm text-ink-muted">No detections for this image yet. Run an inspection.</p>
              )}
              <ul data-testid="region-list" className="space-y-1">
                {regions.map((b, i) => {
                  const isSelected = b.detection.id === selectedId;
                  return (
                    <li key={b.detection.id}>
                      <button
                        type="button"
                        aria-pressed={isSelected}
                        onClick={() => setSelectedId(b.detection.id)}
                        onMouseEnter={() => setHoveredId(b.detection.id)}
                        onMouseLeave={() => setHoveredId(null)}
                        onFocus={() => setHoveredId(b.detection.id)}
                        onBlur={() => setHoveredId(null)}
                        className={`flex w-full flex-wrap items-center gap-2 rounded px-2 py-2 text-left text-sm ${
                          isSelected ? "bg-surface-3 ring-1 ring-accent" : "hover:bg-surface-2"
                        }`}
                      >
                        <span
                          className="grid h-6 w-7 place-items-center rounded font-mono text-xs font-bold text-accent-ink"
                          style={{ background: regionTone(b) }}
                        >
                          {i + 1}
                        </span>
                        <span className="min-w-0 flex-1 truncate">
                          {b.evidence?.evidence?.observed_object_type ?? b.detection.concept}
                          <span className="ml-2 text-xs text-ink-faint">
                            {b.detection.mode === "demo" ? "fixture conf." : "det."} {formatFraction(b.detection.confidence)}
                          </span>
                        </span>
                        {b.decision && <DecisionChip decision={b.decision.decision} />}
                        <ModeTag mode={b.detection.mode} />
                      </button>
                    </li>
                  );
                })}
              </ul>
            </Card>
            {selected ? (
              <>
                {(!selected.evidence || selected.evidence.status !== "ok") && (
                  <Card title="Evidence extraction">
                    <p className="text-sm text-ink-muted">
                      {selected.evidence
                        ? `Previous attempt failed: ${selected.evidence.error ?? selected.evidence.status}`
                        : "No evidence extracted for this region yet."}
                      {isLive && " Sends this region's image crop to Muse Spark (one paid call)."}
                    </p>
                    <div className="mt-3">
                      <Button
                        variant="primary"
                        data-testid="extract-button"
                        disabled={extractRegion.isPending}
                        onClick={() => extractRegion.mutate(selected.detection.id)}
                      >
                        {extractRegion.isPending ? "Extracting…" : selected.evidence ? "Retry extraction" : "Extract evidence"}
                      </Button>
                    </div>
                    {extractRegion.isError && <div className="mt-3"><ErrorState title="Extraction failed" error={extractRegion.error} /></div>}
                  </Card>
                )}
                <EvidencePanel bundle={selected} call={selectedCall} />
                <DecisionPanel decision={selected.decision} ledger={ledger.data ?? []} />
              </>
            ) : (
              regions.length > 0 && <p className="text-sm text-ink-muted">Select a region to see its evidence and match decision.</p>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
