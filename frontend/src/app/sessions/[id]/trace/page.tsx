"use client";

import { useQuery } from "@tanstack/react-query";
import { Bar, BarChart, CartesianGrid, Legend, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

import { EvidenceGraphView } from "@/components/session/EvidenceGraphView";
import { EvidenceModeNote } from "@/components/session/EvidenceModeNote";
import { ModeTag } from "@/components/ui/Badges";
import { Card, EmptyState, ErrorState, SkeletonRows, Stat, TABLE, TableWrap, TD, TH } from "@/components/ui/primitives";
import { api, queryKeys } from "@/lib/api";
import { formatDateTime, formatNumber, formatUsd, shortId } from "@/lib/format";
import type { Trace } from "@/lib/types";
import { useSessionId } from "@/lib/use-session-id";

const CHART_H = 240;
const EVENT_LIMIT = 200;

function LatencyChart({ latency }: { latency: Trace["latency"] }) {
  if (latency.length === 0) return <EmptyState title="No provider calls yet" />;
  return (
    <>
      <div style={{ height: CHART_H }} aria-hidden="true">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={latency} margin={{ top: 8, right: 8, bottom: 0, left: 0 }}>
            <CartesianGrid stroke="#2a303a" vertical={false} />
            <XAxis dataKey="operation" stroke="#a3acba" fontSize={12} />
            <YAxis stroke="#a3acba" fontSize={12} unit=" ms" width={70} />
            <Tooltip contentStyle={{ background: "#20252d", border: "1px solid #3a4250", borderRadius: 6 }} cursor={{ fill: "#20252d" }} />
            <Legend />
            <Bar dataKey="p50_ms" name="p50" fill="#2dd4bf" isAnimationActive={false} />
            <Bar dataKey="p95_ms" name="p95" fill="#fcd34d" isAnimationActive={false} />
          </BarChart>
        </ResponsiveContainer>
      </div>
      <table className="tabular mt-3 w-full text-sm">
        <caption className="sr-only">Latency by operation</caption>
        <thead>
          <tr className="text-left text-xs text-ink-faint">
            <th scope="col">Operation</th><th scope="col">Calls</th><th scope="col">p50</th><th scope="col">p95</th><th scope="col">max</th>
          </tr>
        </thead>
        <tbody>
          {latency.map((l) => (
            <tr key={l.operation}>
              <th scope="row" className="text-left font-normal">{l.operation}</th>
              <td>{l.count}</td><td>{formatNumber(l.p50_ms)} ms</td><td>{formatNumber(l.p95_ms)} ms</td><td>{formatNumber(l.max_ms)} ms</td>
            </tr>
          ))}
        </tbody>
      </table>
    </>
  );
}

export default function TracePage() {
  const id = useSessionId();
  const trace = useQuery({ queryKey: queryKeys.trace(id), queryFn: () => api.trace(id) });
  const graph = useQuery({ queryKey: queryKeys.graph(id), queryFn: () => api.evidenceGraph(id) });
  const config = useQuery({ queryKey: queryKeys.config, queryFn: api.config });

  if (trace.isPending) return <SkeletonRows rows={8} label="Loading trace" />;
  if (trace.isError) return <ErrorState error={trace.error} onRetry={() => trace.refetch()} />;
  const t = trace.data;
  const failedCalls = t.provider_calls.filter((c) => c.status !== "ok").length;

  return (
    <div className="space-y-5">
      <EvidenceModeNote callModes={t.provider_calls.map((c) => c.mode)} serverMode={config.data?.mode} />
      <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
        <Stat label="Runs" value={t.runs.length} />
        <Stat label="Provider calls" value={t.provider_calls.length} />
        <Stat label="Failed calls" value={failedCalls} />
        <Stat label="Estimated cost" value={formatUsd(t.total_estimated_cost_usd)} hint="Estimate, not an invoice" />
      </div>

      <div className="grid gap-5 xl:grid-cols-2">
        <Card title="Runs">
          {t.runs.length === 0 ? (
            <EmptyState title="No runs yet" />
          ) : (
            <TableWrap label="Runs">
              <table className={TABLE}>
                <thead><tr>{["Run", "Concept", "Status", "Mode", "Detections", "Evidence ok/failed", "Started", "Error"].map((h) => <th key={h} scope="col" className={TH}>{h}</th>)}</tr></thead>
                <tbody>
                  {t.runs.map((r) => (
                    <tr key={r.id}>
                      <td className={`${TD} font-mono`}>{shortId(r.id)}</td>
                      <td className={TD}>{r.concept}</td>
                      <td className={`${TD} uppercase`}>{r.status}</td>
                      <td className={TD}><ModeTag mode={r.mode} /></td>
                      <td className={`${TD} tabular`}>{r.detections}</td>
                      <td className={`${TD} tabular`}>{r.evidence_ok} / {r.evidence_failed}</td>
                      <td className={TD}>{formatDateTime(r.started_at)}</td>
                      <td className={`${TD} text-st-mismatched`}>{r.error ?? ""}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </TableWrap>
          )}
        </Card>
        <Card title="Latency p50 / p95 by operation">
          <LatencyChart latency={t.latency} />
        </Card>
      </div>

      <Card title={`Provider calls (${t.provider_calls.length})`}>
        {t.provider_calls.length === 0 ? (
          <EmptyState title="No provider calls recorded" />
        ) : (
          <TableWrap label="Provider calls">
            <table data-testid="trace-table" className={TABLE}>
              <thead><tr>{["Operation", "Provider / model", "Mode", "Status", "Latency", "Tokens in/out", "Images", "Est. cost", "Started", "Correlation", "Error"].map((h) => <th key={h} scope="col" className={TH}>{h}</th>)}</tr></thead>
              <tbody>
                {t.provider_calls.map((c) => (
                  <tr key={c.id} data-status={c.status}>
                    <td className={TD}>{c.operation}</td>
                    <td className={`${TD} font-mono text-xs`}>{c.provider}<br />{c.model}</td>
                    <td className={TD}><ModeTag mode={c.mode} /></td>
                    <td className={`${TD} ${c.status === "ok" ? "text-st-verified" : "text-st-mismatched"}`}>{c.status}</td>
                    <td className={`${TD} tabular text-right`}>{formatNumber(c.latency_ms)} ms</td>
                    <td className={`${TD} tabular`}>{formatNumber(c.input_tokens)} / {formatNumber(c.output_tokens)}</td>
                    <td className={`${TD} tabular`}>{c.images}</td>
                    <td className={`${TD} tabular`}>{formatUsd(c.estimated_cost_usd)}</td>
                    <td className={TD}>{formatDateTime(c.started_at)}</td>
                    <td className={`${TD} font-mono text-xs`}>{shortId(c.correlation_id)}</td>
                    <td className={`${TD} text-st-mismatched`}>{c.error ?? ""}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </TableWrap>
        )}
      </Card>

      <Card title="Evidence / provenance graph">
        {graph.isPending && <SkeletonRows rows={3} label="Loading graph" />}
        {graph.isError && <ErrorState error={graph.error} onRetry={() => graph.refetch()} />}
        {graph.data && (graph.data.nodes.length === 0 ? <EmptyState title="Graph is empty" /> : <EvidenceGraphView graph={graph.data} />)}
      </Card>

      <Card title={`Event log (${t.events.length})`}>
        {t.events.length === 0 ? (
          <EmptyState title="No events recorded" />
        ) : (
          <ol className="max-h-80 space-y-0.5 overflow-y-auto font-mono text-xs" tabIndex={0} aria-label="Run event log">
            {t.events.slice(-EVENT_LIMIT).map((ev) => (
              <li key={`${ev.run_id}-${ev.seq}`} className={ev.status === "error" ? "text-st-mismatched" : "text-ink-muted"}>
                <span className="text-ink-faint">{formatDateTime(ev.ts)} {shortId(ev.run_id)}#{ev.seq}</span> {ev.stage}/{ev.status} {ev.message}
                {ev.latency_ms != null && <span className="text-ink-faint"> · {ev.latency_ms} ms</span>}
              </li>
            ))}
          </ol>
        )}
      </Card>
    </div>
  );
}
