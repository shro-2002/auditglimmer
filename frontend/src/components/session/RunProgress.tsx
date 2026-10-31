"use client";

import { useQuery } from "@tanstack/react-query";
import { useEffect, useRef, useState } from "react";

import { ModeTag } from "@/components/ui/Badges";
import { Button, ErrorState } from "@/components/ui/primitives";
import { api, urls } from "@/lib/api";
import type { RunEvent, RunStatus } from "@/lib/types";

type StreamState = "connecting" | "streaming" | "ended" | "interrupted";

const TERMINAL: RunStatus[] = ["succeeded", "partial", "failed"];
const FALLBACK_POLL_MS = 2_000;
const LOG_LIMIT = 40;

/** Mount with key={runId}; the stream and its event log reset with a new run. */
export function RunProgress({ runId, onEnd }: { runId: string; onEnd: () => void }) {
  const [events, setEvents] = useState<RunEvent[]>([]);
  const [stream, setStream] = useState<StreamState>("connecting");
  const [attempt, setAttempt] = useState(0);

  const isInterrupted = stream === "interrupted";
  const hasNotifiedEnd = useRef(false);
  const run = useQuery({
    queryKey: ["run", runId, stream],
    queryFn: () => api.run(runId),
    // Polling only as a fallback when the SSE stream drops before `event: end`.
    refetchInterval: (q) =>
      isInterrupted && q.state.data && !TERMINAL.includes(q.state.data.status) ? FALLBACK_POLL_MS : false,
  });

  useEffect(() => {
    const source = new EventSource(urls.runEvents(runId));
    source.onopen = () => setStream("streaming");
    source.onmessage = (msg) => {
      try {
        const ev = JSON.parse(msg.data) as RunEvent;
        // Reconnects may replay; dedupe by seq.
        setEvents((prev) => (prev.some((p) => p.seq === ev.seq) ? prev : [...prev, ev].sort((a, b) => a.seq - b.seq)));
      } catch {
        setStream("interrupted");
      }
    };
    source.addEventListener("end", () => {
      source.close();
      setStream("ended");
      hasNotifiedEnd.current = true;
      onEnd();
    });
    source.onerror = () => {
      source.close();
      setStream((s) => (s === "ended" ? s : "interrupted"));
    };
    return () => source.close();
  }, [runId, attempt, onEnd]);

  const status = run.data?.status;
  // If the stream died (e.g. behind the access gate), the fallback poll is what sees the run finish.
  useEffect(() => {
    if (isInterrupted && status && TERMINAL.includes(status) && !hasNotifiedEnd.current) {
      hasNotifiedEnd.current = true;
      onEnd();
    }
  }, [isInterrupted, status, onEnd]);
  const latest = events.at(-1);
  const progressText = latest ? `${latest.stage} · ${latest.status} — ${latest.message}` : "Waiting for first event…";

  return (
    <div className="space-y-2">
      <div
        data-testid="run-status"
        data-run-id={runId}
        data-status={status ?? "unknown"}
        data-stream={stream}
        role="status"
        aria-live="polite"
        className="rounded-md border border-line bg-surface-2 p-3 text-sm"
      >
        <div className="flex flex-wrap items-center gap-2">
          <span className="font-semibold">Run {status ?? "starting"}</span>
          {run.data && <ModeTag mode={run.data.mode} />}
          <span className="text-xs text-ink-muted">
            stream: {stream}
            {run.data && ` · ${run.data.detections} detections · evidence ${run.data.evidence_ok} ok / ${run.data.evidence_failed} failed`}
          </span>
        </div>
        <p className="mt-1 text-ink-muted">{progressText}</p>
        {run.data?.error && <p className="mt-1 text-st-mismatched">Run error: {run.data.error}</p>}
      </div>

      {isInterrupted && status && !TERMINAL.includes(status) && (
        <div className="flex flex-wrap items-center gap-2 text-sm" role="alert">
          <span className="text-st-probable">Live progress stream interrupted; polling run status.</span>
          <Button className="min-h-8" onClick={() => setAttempt((a) => a + 1)}>
            Reconnect stream
          </Button>
        </div>
      )}
      {run.isError && <ErrorState error={run.error} onRetry={() => run.refetch()} title="Run status unavailable" />}

      {events.length > 0 && (
        <ol className="max-h-48 space-y-0.5 overflow-y-auto rounded-md border border-line bg-canvas p-2 font-mono text-xs" aria-label="Run event log">
          {events.slice(-LOG_LIMIT).map((ev) => (
            <li key={ev.seq} className={ev.status === "error" ? "text-st-mismatched" : "text-ink-muted"}>
              <span className="text-ink-faint">#{ev.seq}</span> {ev.stage}/{ev.status} {ev.message}
              {ev.latency_ms != null && <span className="text-ink-faint"> · {ev.latency_ms} ms</span>}
            </li>
          ))}
        </ol>
      )}
    </div>
  );
}
