import { useRepStats } from "../hooks/useCrm";
import type { RepStat } from "../api/crm";

function paise(v: number) {
  return v === 0 ? "—" : `₹${(v / 100).toLocaleString("en-IN")}`;
}

function WinRate({ won, total }: { won: number; total: number }) {
  if (total === 0) return <span className="text-[var(--text-muted)]">—</span>;
  const pct = Math.round((won / total) * 100);
  const color = pct >= 30 ? "var(--positive)" : pct >= 15 ? "var(--warning)" : "var(--negative)";
  return <span className="font-semibold tabular" style={{ color }}>{pct}%</span>;
}

export default function RepPerformance() {
  const stats = useRepStats();

  if (stats.isPending) {
    return (
      <div className="rounded-xl bg-[var(--bg-2)] border border-[var(--border-subtle)] p-6">
        <div className="space-y-3">
          {Array.from({ length: 3 }).map((_, i) => (
            <div key={i} className="h-10 rounded-lg animate-pulse bg-[var(--surface-1)]" />
          ))}
        </div>
      </div>
    );
  }

  const reps = stats.data ?? [];

  return (
    <div className="rounded-xl overflow-hidden bg-[var(--bg-2)] border border-[var(--border-subtle)]">
      <div className="px-6 py-4 border-b border-[var(--border-subtle)]">
        <h2 className="text-sm font-semibold text-[var(--text-primary)]">Rep Performance</h2>
        <p className="text-xs text-[var(--text-muted)] mt-0.5">Lead pipeline metrics per sales rep</p>
      </div>

      {reps.length === 0 ? (
        <div className="p-6 text-sm text-[var(--text-muted)] text-center">
          No leads yet. Add leads and assign them to reps to see performance.
        </div>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="bg-[var(--bg-1)]">
                {["Rep", "Leads", "New (30d)", "Won", "Win Rate", "Pipeline MRR"].map((h, i) => (
                  <th
                    key={h}
                    className={`px-${i === 0 || i === 5 ? "6" : "4"} py-3 text-[10px] font-semibold uppercase tracking-[0.08em] text-[var(--text-muted)] border-b border-[var(--border-subtle)] ${i === 0 ? "text-left" : "text-right"}`}
                  >
                    {h}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-[var(--border-subtle)]">
              {reps.map((r: RepStat) => (
                <tr key={r.rep} className="hover:bg-[var(--surface-1)] transition-colors">
                  <td className="px-6 py-3">
                    <div className="flex items-center gap-2.5">
                      <div
                        className="w-7 h-7 rounded-full flex items-center justify-center text-xs font-semibold shrink-0"
                        style={{ background: "var(--brand-dim)", color: "var(--brand)" }}
                      >
                        {r.rep === "Unassigned" ? "?" : r.rep.slice(0, 1).toUpperCase()}
                      </div>
                      <span className="font-medium text-[var(--text-primary)]">{r.rep}</span>
                    </div>
                  </td>
                  <td className="px-4 py-3 text-right text-[var(--text-secondary)] tabular">{r.total_leads}</td>
                  <td className="px-4 py-3 text-right tabular">
                    {r.new_leads_30d > 0
                      ? <span className="text-[var(--positive)] font-semibold">+{r.new_leads_30d}</span>
                      : <span className="text-[var(--text-muted)]">—</span>}
                  </td>
                  <td className="px-4 py-3 text-right text-[var(--text-secondary)] tabular">{r.won_leads}</td>
                  <td className="px-4 py-3 text-right">
                    <WinRate won={r.won_leads} total={r.total_leads - r.lost_leads} />
                  </td>
                  <td className="px-6 py-3 text-right font-semibold tabular text-[var(--text-primary)]">
                    {paise(r.pipeline_mrr_paise)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
