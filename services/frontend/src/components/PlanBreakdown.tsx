import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, ResponsiveContainer, Cell,
} from "recharts";
import { Tooltip } from "recharts";
import type { PlanRow } from "../api/metrics";
import ChartTooltip from "./ChartTooltip";

interface Props {
  plans: PlanRow[];
  totalMrrPaise: number;
}

const COLORS = ["#7ff7cb", "#6ab3ff", "#a78bfa", "#fbbf24", "#f472b6", "#34d399"];

function fmtRupees(paise: number) {
  const r = paise / 100;
  if (Math.abs(r) >= 1_00_000) return `₹${(r / 1_00_000).toFixed(2)}L`;
  return `₹${r.toLocaleString("en-IN")}`;
}

function fmtAxis(v: number) {
  if (Math.abs(v) >= 100000) return `₹${(v / 100000).toFixed(1)}L`;
  if (Math.abs(v) >= 1000) return `₹${(v / 1000).toFixed(0)}k`;
  return `₹${v}`;
}

export default function PlanBreakdown({ plans, totalMrrPaise }: Props) {
  if (!plans.length) {
    return (
      <div className="rounded-xl p-6 bg-[var(--bg-2)] border border-[var(--border-subtle)]">
        <h2 className="text-sm font-semibold text-[var(--text-primary)] mb-2">Plan Breakdown</h2>
        <p className="text-sm text-[var(--text-muted)]">No plan data for this month.</p>
      </div>
    );
  }

  const chartData = plans.map((p) => ({
    name: p.plan_id.length > 18 ? `${p.plan_id.slice(0, 16)}…` : p.plan_id,
    fullName: p.plan_id,
    mrr: p.net_mrr_delta_paise / 100,
    subs: p.subscriber_count,
    pct: p.pct_of_total,
  }));

  return (
    <div className="rounded-xl overflow-hidden bg-[var(--bg-2)] border border-[var(--border-subtle)]">
      <div className="px-6 py-4 border-b border-[var(--border-subtle)] flex items-center justify-between">
        <h2 className="text-sm font-semibold text-[var(--text-primary)]">Plan Breakdown</h2>
        <span className="text-xs text-[var(--text-muted)]">
          Total MRR {fmtRupees(totalMrrPaise)}
        </span>
      </div>

      <div className="p-6 grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Bar chart */}
        <ResponsiveContainer width="100%" height={220}>
          <BarChart data={chartData} layout="vertical" margin={{ left: 8, right: 16 }}>
            <CartesianGrid strokeDasharray="3 3" horizontal={false} stroke="rgba(255,255,255,0.05)" />
            <XAxis
              type="number"
              tickFormatter={fmtAxis}
              tick={{ fill: "#64748b", fontSize: 11 }}
              axisLine={false}
              tickLine={false}
            />
            <YAxis
              type="category"
              dataKey="name"
              width={90}
              tick={{ fill: "#94a3b8", fontSize: 11 }}
              axisLine={false}
              tickLine={false}
            />
            <Tooltip
              content={<ChartTooltip formatValue={(v) => fmtRupees(v * 100)} />}
              cursor={{ fill: "rgba(255,255,255,0.03)" }}
            />
            <Bar dataKey="mrr" name="MRR" radius={[0, 4, 4, 0]}>
              {chartData.map((_, i) => (
                <Cell key={i} fill={COLORS[i % COLORS.length]} />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>

        {/* Table */}
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-[var(--border-subtle)]">
                <th className="pb-2.5 text-left text-[10px] font-semibold uppercase tracking-[0.08em] text-[var(--text-muted)]">Plan</th>
                <th className="pb-2.5 text-right text-[10px] font-semibold uppercase tracking-[0.08em] text-[var(--text-muted)]">Subs</th>
                <th className="pb-2.5 text-right text-[10px] font-semibold uppercase tracking-[0.08em] text-[var(--text-muted)]">MRR</th>
                <th className="pb-2.5 text-right text-[10px] font-semibold uppercase tracking-[0.08em] text-[var(--text-muted)]">Share</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[var(--border-subtle)]">
              {plans.map((p, i) => (
                <tr key={p.plan_id} className="hover:bg-[var(--surface-1)] transition-colors">
                  <td className="py-2.5 font-mono text-xs text-[var(--text-secondary)] max-w-[140px] truncate">
                    <span
                      className="inline-block w-2 h-2 rounded-full mr-2 shrink-0"
                      style={{ background: COLORS[i % COLORS.length] }}
                    />
                    {p.plan_id}
                  </td>
                  <td className="py-2.5 text-right text-[var(--text-secondary)] tabular">{p.subscriber_count}</td>
                  <td className="py-2.5 text-right text-[var(--text-secondary)] tabular">{fmtRupees(Math.abs(p.net_mrr_delta_paise))}</td>
                  <td className="py-2.5 text-right text-[var(--text-muted)] tabular">{p.pct_of_total.toFixed(1)}%</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
