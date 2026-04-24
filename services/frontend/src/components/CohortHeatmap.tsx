import { useState } from "react";
import type { CohortRow } from "../api/cohort";

interface Props {
  cohorts: CohortRow[];
}

function heatColor(pct: number): { bg: string; color: string } {
  if (pct <= 0)  return { bg: "rgba(255,255,255,0.04)", color: "#4b6480" };
  if (pct >= 90) return { bg: "#065f46", color: "#6ee7b7" };
  if (pct >= 70) return { bg: "#047857", color: "#a7f3d0" };
  if (pct >= 50) return { bg: "#059669", color: "#d1fae5" };
  if (pct >= 30) return { bg: "#10b981", color: "#fff" };
  if (pct >= 15) return { bg: "rgba(52,211,153,0.25)", color: "#6ee7b7" };
  return         { bg: "rgba(52,211,153,0.10)", color: "#34d399" };
}

interface CellTooltip {
  periodMonth: string;
  retained: number;
  total: number;
  revenue: number;
  pct: number;
  x: number;
  y: number;
}

export default function CohortHeatmap({ cohorts }: Props) {
  const [tooltip, setTooltip] = useState<CellTooltip | null>(null);

  if (!cohorts.length) {
    return (
      <div className="rounded-xl p-6 bg-[var(--bg-2)] border border-[var(--border-subtle)]">
        <h2 className="text-sm font-semibold text-[var(--text-primary)] mb-2">Cohort Retention</h2>
        <p className="text-sm text-[var(--text-muted)]">No cohort data yet — populates after the daily job runs.</p>
      </div>
    );
  }

  const maxPeriods = Math.max(...cohorts.map((c) => c.periods.length));

  const LEGEND = [
    { bg: "rgba(52,211,153,0.10)", label: "<15%" },
    { bg: "rgba(52,211,153,0.25)", label: "15–30%" },
    { bg: "#10b981",               label: "30–50%" },
    { bg: "#059669",               label: "50–70%" },
    { bg: "#047857",               label: "70–90%" },
    { bg: "#065f46",               label: "≥90%" },
  ];

  return (
    <div className="rounded-xl overflow-hidden bg-[var(--bg-2)] border border-[var(--border-subtle)] relative">
      <div className="px-6 py-4 border-b border-[var(--border-subtle)]">
        <h2 className="text-sm font-semibold text-[var(--text-primary)]">Cohort Retention</h2>
        <p className="text-xs text-[var(--text-muted)] mt-0.5">
          % of subscribers still active N months after first payment
        </p>
      </div>

      <div className="overflow-x-auto">
        <table className="text-xs border-collapse min-w-max">
          <thead>
            <tr className="bg-[var(--bg-1)]">
              <th className="px-4 py-2.5 text-left text-[var(--text-muted)] font-semibold border-b border-r border-[var(--border-subtle)] sticky left-0 bg-[var(--bg-1)] z-10 uppercase tracking-[0.06em]">
                Cohort
              </th>
              <th className="px-3 py-2.5 text-[var(--text-muted)] font-semibold border-b border-[var(--border-subtle)] text-center uppercase tracking-[0.06em]">
                Size
              </th>
              {Array.from({ length: maxPeriods }, (_, i) => (
                <th
                  key={i}
                  className="px-3 py-2.5 text-[var(--text-muted)] font-semibold border-b border-[var(--border-subtle)] text-center uppercase tracking-[0.06em]"
                >
                  M{i}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {cohorts.map((cohort) => (
              <tr key={cohort.cohort_month} className="hover:bg-[var(--surface-1)] transition-colors">
                <td className="px-4 py-2 text-[var(--text-secondary)] font-medium border-r border-[var(--border-subtle)] sticky left-0 bg-[var(--bg-2)] whitespace-nowrap z-10">
                  {cohort.cohort_month}
                </td>
                <td className="px-3 py-2 text-center text-[var(--text-muted)] border-r border-[var(--border-subtle)]">
                  {cohort.cohort_size}
                </td>
                {Array.from({ length: maxPeriods }, (_, i) => {
                  const period = cohort.periods.find((p) => p.period_number === i);
                  if (!period) return <td key={i} className="p-0.5"><div className="w-14 h-8" /></td>;

                  const { bg, color } = heatColor(period.retention_pct);
                  return (
                    <td key={i} className="p-0.5">
                      <div
                        className="cohort-cell w-14 h-8 flex items-center justify-center rounded text-xs font-semibold cursor-default"
                        style={{ backgroundColor: bg, color }}
                        onMouseEnter={(e) => {
                          const rect = (e.target as HTMLElement).getBoundingClientRect();
                          setTooltip({
                            periodMonth: period.period_month,
                            retained: period.retained_count,
                            total: cohort.cohort_size,
                            revenue: period.revenue_paise,
                            pct: period.retention_pct,
                            x: rect.left + rect.width / 2,
                            y: rect.top,
                          });
                        }}
                        onMouseLeave={() => setTooltip(null)}
                      >
                        {period.retention_pct.toFixed(0)}%
                      </div>
                    </td>
                  );
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Hover tooltip */}
      {tooltip && (
        <div
          className="fixed z-50 pointer-events-none rounded-lg px-3 py-2 text-xs shadow-xl"
          style={{
            left: tooltip.x,
            top: tooltip.y - 8,
            transform: "translate(-50%, -100%)",
            background: "rgba(13,23,38,0.96)",
            border: "1px solid rgba(255,255,255,0.10)",
          }}
        >
          <p className="font-semibold text-[var(--text-primary)] mb-1">{tooltip.periodMonth}</p>
          <p className="text-[var(--text-secondary)]">{tooltip.retained}/{tooltip.total} retained ({tooltip.pct.toFixed(1)}%)</p>
          <p className="text-[var(--text-muted)] mt-0.5">
            ₹{(tooltip.revenue / 100).toLocaleString("en-IN")} revenue
          </p>
        </div>
      )}

      {/* Legend */}
      <div className="px-6 py-3 border-t border-[var(--border-subtle)] flex flex-wrap items-center gap-3 text-xs text-[var(--text-muted)]">
        <span>Retention:</span>
        {LEGEND.map(({ bg, label }) => (
          <span key={label} className="flex items-center gap-1.5">
            <span className="w-3 h-3 rounded-sm shrink-0" style={{ backgroundColor: bg }} />
            {label}
          </span>
        ))}
      </div>
    </div>
  );
}
