import type { EvidenceGraph, GraphNodeType } from "@/lib/types";

const LAYERS: GraphNodeType[] = ["LedgerAsset", "Image", "Detection", "Evidence", "Decision", "Review"];
const LAYER_TONE: Record<GraphNodeType, string> = {
  LedgerAsset: "#cbd5e1",
  Image: "#7dd3fc",
  Detection: "#2dd4bf",
  Evidence: "#c4b5fd",
  Decision: "#fcd34d",
  Review: "#5eead4",
};
const COL_W = 190;
const NODE_W = 160;
const NODE_H = 30;
const ROW_GAP = 10;
const TOP = 34;
const LABEL_MAX = 22;

/** Layered provenance graph: one column per node type, edges as curves. No graph library needed. */
export function EvidenceGraphView({ graph }: { graph: EvidenceGraph }) {
  const pos = new Map<string, { x: number; y: number }>();
  const columns = LAYERS.map((type, col) => {
    const nodes = graph.nodes.filter((n) => n.type === type);
    nodes.forEach((n, row) => pos.set(n.id, { x: col * COL_W, y: TOP + row * (NODE_H + ROW_GAP) }));
    return { type, nodes };
  });
  const maxRows = Math.max(1, ...columns.map((c) => c.nodes.length));
  const height = TOP + maxRows * (NODE_H + ROW_GAP);
  const width = LAYERS.length * COL_W;

  return (
    <div className="space-y-2">
      <p className="text-xs text-ink-muted">
        {graph.nodes.length} nodes · {graph.edges.length} edges ·{" "}
        {columns.map((c) => `${c.type}: ${c.nodes.length}`).join(" · ")}
      </p>
      <div className="overflow-auto rounded-md border border-line bg-canvas" tabIndex={0} role="region" aria-label="Evidence provenance graph">
        <svg width={width} height={height} viewBox={`0 0 ${width} ${height}`} role="img" aria-label="Provenance graph from ledger assets through images, detections, evidence and decisions to reviews">
          {LAYERS.map((type, col) => (
            <text key={type} x={col * COL_W + 8} y={18} fill="#7d8696" fontSize={11} fontWeight={600}>
              {type.toUpperCase()}
            </text>
          ))}
          {graph.edges.map((e, i) => {
            const a = pos.get(e.source);
            const b = pos.get(e.target);
            if (!a || !b) return null;
            const [left, right] = a.x <= b.x ? [a, b] : [b, a];
            const x1 = left.x + NODE_W;
            const y1 = left.y + NODE_H / 2;
            const x2 = right.x;
            const y2 = right.y + NODE_H / 2;
            const mid = (x1 + x2) / 2;
            return (
              <path key={i} d={`M${x1},${y1} C${mid},${y1} ${mid},${y2} ${x2},${y2}`} fill="none" stroke="#3a4250" strokeWidth={1}>
                <title>{e.type}</title>
              </path>
            );
          })}
          {graph.nodes.map((n) => {
            const p = pos.get(n.id);
            if (!p) return null;
            const label = n.label.length > LABEL_MAX ? `${n.label.slice(0, LABEL_MAX - 1)}…` : n.label;
            return (
              <g key={n.id} transform={`translate(${p.x + 4} ${p.y})`}>
                <title>{`${n.type}: ${n.label}`}</title>
                <rect width={NODE_W} height={NODE_H} rx={4} fill="#191d23" stroke={LAYER_TONE[n.type]} strokeOpacity={0.7} />
                <rect width={3} height={NODE_H} fill={LAYER_TONE[n.type]} />
                <text x={10} y={NODE_H / 2 + 4} fill="#e7eaef" fontSize={11} fontFamily="ui-monospace, monospace">
                  {label}
                </text>
              </g>
            );
          })}
        </svg>
      </div>
    </div>
  );
}
