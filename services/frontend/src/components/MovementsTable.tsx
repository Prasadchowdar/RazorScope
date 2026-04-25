import { useState, useEffect } from "react";
import { ChevronLeft, ChevronRight, Download } from "lucide-react";
import type { Movement } from "../api/mrr";
import { downloadMovementsCsv, fetchRiskScores, type RiskScore } from "../api/subscribers";
import SubscriberDrawer from "./SubscriberDrawer";
import Badge from "./Badge";
import RiskBadge from "./RiskBadge";
import { useAuth } from "../context/AuthContext";

interface Props {
  movements: Movement[];
  page: number;
  onPageChange: (p: number) => void;
  hasMore: boolean;
  month?: string;
  planId?: string;
}

type BadgeVariant = "positive" | "negative" | "warning" | "brand" | "neutral";

const TYPE_VARIANT: Record<string, BadgeVariant> = {
  new:          "positive",
  expansion:    "positive",
  reactivation: "brand",
  contraction:  "warning",
  churn:        "negative",
};

function fmtRupees(paise: number) {
  const prefix = paise >= 0 ? "+" : "";
  return `${prefix}₹${(paise / 100).toLocaleString("en-IN")}`;
}

export default function MovementsTable({ movements, page, onPageChange, hasMore, month, planId }: Props) {
  const { accessToken } = useAuth();
  const [selectedSub, setSelectedSub] = useState<string | null>(null);
  const [exporting, setExporting] = useState(false);
  const [riskMap, setRiskMap] = useState<Map<string, RiskScore>>(new Map());

  useEffect(() => {
    if (!accessToken) return;
    fetchRiskScores(accessToken, 200)
      .then(({ scores }) => setRiskMap(new Map(scores.map((s) => [s.razorpay_sub_id, s]))))
      .catch(() => {});
  }, [accessToken]);

  async function handleExport() {
    if (!month || !accessToken) return;
    setExporting(true);
    try {
      await downloadMovementsCsv(accessToken, month, planId);
    } finally {
      setExporting(false);
    }
  }

  return (
    <>
      <div className="rounded-xl overflow-hidden bg-[var(--bg-2)] border border-[var(--border-subtle)]">
        {/* Header */}
        <div className="px-6 py-4 border-b border-[var(--border-subtle)] flex items-center justify-between">
          <h2 className="text-sm font-semibold text-[var(--text-primary)]">MRR Movements</h2>
          {month && (
            <button
              onClick={handleExport}
              type="button"
              disabled={exporting}
              className="flex items-center gap-1.5 text-xs px-3 py-1.5 rounded-lg border border-[var(--border-default)] text-[var(--text-secondary)] hover:border-[var(--border-strong)] hover:text-[var(--text-primary)] disabled:opacity-40 transition-colors"
            >
              <Download size={12} />
              {exporting ? "Exporting…" : "Export CSV"}
            </button>
          )}
        </div>

        {/* Table */}
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="bg-[var(--bg-1)]">
                {["Subscription", "Type", "Delta", "Month", "Voluntary", "Risk"].map((h, i) => (
                  <th
                    key={h}
                    className={`px-6 py-3 text-[10px] font-semibold uppercase tracking-[0.08em] text-[var(--text-muted)] border-b border-[var(--border-subtle)] ${i === 2 ? "text-right" : "text-left"}`}
                  >
                    {h}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-[var(--border-subtle)]">
              {movements.length === 0 && (
                <tr>
                  <td colSpan={6} className="px-6 py-10 text-center text-sm text-[var(--text-muted)]">
                    No movements found.
                  </td>
                </tr>
              )}
              {movements.map((m, i) => (
                <tr
                  key={i}
                  className="hover:bg-[var(--surface-1)] cursor-pointer transition-colors"
                  onClick={() => setSelectedSub(m.razorpay_sub_id)}
                >
                  <td className="px-6 py-3 font-mono text-xs text-[var(--brand-2)] hover:underline">
                    {m.razorpay_sub_id}
                  </td>
                  <td className="px-6 py-3">
                    <Badge variant={TYPE_VARIANT[m.movement_type] ?? "neutral"}>
                      {m.movement_type}
                    </Badge>
                  </td>
                  <td
                    className="px-6 py-3 text-right font-semibold tabular text-sm"
                    style={{ color: m.delta_paise >= 0 ? "var(--positive)" : "var(--negative)" }}
                  >
                    {fmtRupees(m.delta_paise)}
                  </td>
                  <td className="px-6 py-3 text-[var(--text-muted)] text-xs">{m.period_month}</td>
                  <td className="px-6 py-3 text-[var(--text-muted)] text-xs">
                    {m.voluntary ? "Yes" : "No"}
                  </td>
                  <td className="px-6 py-3">
                    {(() => {
                      const r = riskMap.get(m.razorpay_sub_id);
                      return r ? <RiskBadge score={r.risk_score} label={r.risk_label} showScore /> : <span className="text-[var(--text-muted)]">—</span>;
                    })()}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        {/* Pagination */}
        <div className="px-6 py-3 flex items-center gap-2 border-t border-[var(--border-subtle)]">
          <button
            type="button"
            onClick={() => onPageChange(page - 1)}
            disabled={page <= 1}
            aria-label="Previous page"
            className="w-8 h-8 flex items-center justify-center rounded-lg border border-[var(--border-default)] text-[var(--text-secondary)] hover:border-[var(--border-strong)] hover:text-[var(--text-primary)] disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
          >
            <ChevronLeft size={14} />
          </button>
          <span className="text-xs text-[var(--text-muted)] tabular min-w-[4rem] text-center">
            Page {page}
          </span>
          <button
            type="button"
            onClick={() => onPageChange(page + 1)}
            disabled={!hasMore}
            aria-label="Next page"
            className="w-8 h-8 flex items-center justify-center rounded-lg border border-[var(--border-default)] text-[var(--text-secondary)] hover:border-[var(--border-strong)] hover:text-[var(--text-primary)] disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
          >
            <ChevronRight size={14} />
          </button>
        </div>
      </div>

      <SubscriberDrawer subId={selectedSub} onClose={() => setSelectedSub(null)} />
    </>
  );
}
