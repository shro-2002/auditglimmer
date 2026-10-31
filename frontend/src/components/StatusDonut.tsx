"use client";

import { Cell, Pie, PieChart, ResponsiveContainer, Tooltip } from "recharts";

import type { AssetStatus } from "@/lib/types";

import { ASSET_STATUSES, STATUS_HEX, StatusChip } from "./ui/Badges";

const CHART_HEIGHT = 220;

/** Donut + text legend table; the table is the accessible source of truth, the chart is decoration. */
export function StatusDonut({ byStatus }: { byStatus: Record<AssetStatus, number> }) {
  const data = ASSET_STATUSES.map((status) => ({ status, value: byStatus[status] ?? 0 }));
  const total = data.reduce((sum, d) => sum + d.value, 0);

  return (
    <div className="grid items-center gap-4 sm:grid-cols-[220px_1fr]">
      <div className="relative" style={{ height: CHART_HEIGHT }} aria-hidden="true">
        {total > 0 ? (
          <ResponsiveContainer width="100%" height="100%">
            <PieChart accessibilityLayer={false}>
              <Pie rootTabIndex={-1}
                data={data.filter((d) => d.value > 0)}
                dataKey="value"
                nameKey="status"
                innerRadius="62%"
                outerRadius="92%"
                stroke="#13161b"
                strokeWidth={2}
                isAnimationActive={false}
              >
                {data
                  .filter((d) => d.value > 0)
                  .map((d) => (
                    <Cell key={d.status} fill={STATUS_HEX[d.status]} />
                  ))}
              </Pie>
              <Tooltip
                contentStyle={{ background: "#20252d", border: "1px solid #3a4250", borderRadius: 6 }}
                itemStyle={{ color: "#e7eaef" }}
              />
            </PieChart>
          </ResponsiveContainer>
        ) : (
          <div className="grid h-full place-items-center rounded-full border-[18px] border-surface-3" />
        )}
        <div className="pointer-events-none absolute inset-0 grid place-items-center text-center">
          <div>
            <p className="tabular text-2xl font-semibold">{total}</p>
            <p className="text-xs text-ink-muted">assets</p>
          </div>
        </div>
      </div>
      <table className="w-full text-sm">
        <caption className="sr-only">Assets by reconciliation status</caption>
        <tbody>
          {data.map((d) => (
            <tr key={d.status} className="border-b border-line/60 last:border-0">
              <th scope="row" className="py-1.5 text-left font-normal">
                <StatusChip status={d.status} />
              </th>
              <td className="tabular py-1.5 text-right font-medium">{d.value}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
