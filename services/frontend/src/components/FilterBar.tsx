import { ChevronLeft, ChevronRight } from "lucide-react";
import type { SegmentFilters } from "../api/types";

interface SegmentValues {
  plans: string[];
  countries: string[];
  sources: string[];
  payment_methods: string[];
}

interface Props {
  month: string;
  onMonthChange: (m: string) => void;
  segments: SegmentValues | undefined;
  filters: SegmentFilters;
  onFilterChange: (f: SegmentFilters) => void;
}

function prevMonth(ym: string): string {
  const [y, m] = ym.split("-").map(Number);
  if (m === 1) return `${y - 1}-12`;
  return `${y}-${String(m - 1).padStart(2, "0")}`;
}

function nextMonth(ym: string): string {
  const [y, m] = ym.split("-").map(Number);
  if (m === 12) return `${y + 1}-01`;
  return `${y}-${String(m + 1).padStart(2, "0")}`;
}

function isCurrentOrFuture(ym: string): boolean {
  const now = new Date();
  const [y, m] = ym.split("-").map(Number);
  return y > now.getFullYear() || (y === now.getFullYear() && m >= now.getMonth() + 1);
}

const MONTH_NAMES = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"];
function formatMonth(ym: string): string {
  const [y, m] = ym.split("-").map(Number);
  return `${MONTH_NAMES[m - 1]} ${y}`;
}

function FilterSelect({ label, value, options, onChange }: {
  label: string; value: string; options: string[]; onChange: (v: string) => void;
}) {
  if (options.length === 0) return null;
  return (
    <div className="flex items-center gap-1.5">
      <label className="text-xs text-[var(--text-muted)] whitespace-nowrap">{label}</label>
      <select
        value={value}
        title={label}
        aria-label={label}
        onChange={(e) => onChange(e.target.value)}
        className="text-xs border border-[var(--border-default)] rounded-lg px-2.5 py-1.5 bg-[var(--bg-1)] text-[var(--text-primary)] focus:outline-none focus:ring-1 focus:ring-[var(--brand)] focus:border-[var(--brand)] transition-colors"
      >
        <option value="">All</option>
        {options.map((o) => (
          <option key={o} value={o}>{o}</option>
        ))}
      </select>
    </div>
  );
}

export default function FilterBar({ month, onMonthChange, segments, filters, onFilterChange }: Props) {
  const hasActiveFilter = !!(filters.planId || filters.country || filters.source || filters.paymentMethod);

  function update(patch: Partial<SegmentFilters>) {
    onFilterChange({ ...filters, ...patch });
  }

  return (
    <div className="flex flex-wrap items-center gap-3">
      {/* Month navigator */}
      <div className="flex items-center gap-1">
        <button
          type="button"
          aria-label="Previous month"
          onClick={() => onMonthChange(prevMonth(month))}
          className="w-7 h-7 flex items-center justify-center rounded-lg border border-[var(--border-default)] text-[var(--text-secondary)] hover:border-[var(--border-strong)] hover:text-[var(--text-primary)] transition-colors"
        >
          <ChevronLeft size={13} />
        </button>
        <span className="text-xs font-semibold text-[var(--text-primary)] border border-[var(--border-default)] rounded-lg px-3 py-1.5 min-w-[6.5rem] text-center select-none bg-[var(--surface-1)]">
          {formatMonth(month)}
        </span>
        <button
          type="button"
          aria-label="Next month"
          onClick={() => { if (!isCurrentOrFuture(month)) onMonthChange(nextMonth(month)); }}
          disabled={isCurrentOrFuture(month)}
          className="w-7 h-7 flex items-center justify-center rounded-lg border border-[var(--border-default)] text-[var(--text-secondary)] hover:border-[var(--border-strong)] hover:text-[var(--text-primary)] disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
        >
          <ChevronRight size={13} />
        </button>
      </div>

      <div className="w-px h-4 bg-[var(--border-subtle)]" />

      <FilterSelect label="Plan"    value={filters.planId ?? ""}        options={segments?.plans ?? []}           onChange={(v) => update({ planId: v || undefined })} />
      <FilterSelect label="Country" value={filters.country ?? ""}       options={segments?.countries ?? []}       onChange={(v) => update({ country: v || undefined })} />
      <FilterSelect label="Source"  value={filters.source ?? ""}        options={segments?.sources ?? []}         onChange={(v) => update({ source: v || undefined })} />
      <FilterSelect label="Payment" value={filters.paymentMethod ?? ""} options={segments?.payment_methods ?? []} onChange={(v) => update({ paymentMethod: v || undefined })} />

      {hasActiveFilter && (
        <button
          type="button"
          onClick={() => onFilterChange({})}
          className="text-xs text-[var(--brand)] hover:underline ml-1 transition-colors"
        >
          Clear
        </button>
      )}
    </div>
  );
}
