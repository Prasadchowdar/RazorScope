import { useState } from "react";
import { Menu } from "lucide-react";
import AddLeadModal from "../components/AddLeadModal";
import ApiKeyManager from "../components/ApiKeyManager";
import AuditLog from "../components/AuditLog";
import BenchmarkGauge from "../components/BenchmarkGauge";
import CohortHeatmap from "../components/CohortHeatmap";
import FilterBar from "../components/FilterBar";
import LeadDrawer from "../components/LeadDrawer";
import LeadsTable from "../components/LeadsTable";
import MetricsOverviewPanel from "../components/MetricsOverview";
import MovementsTable from "../components/MovementsTable";
import MrrChart from "../components/MrrChart";
import PipelineBoard from "../components/PipelineBoard";
import PlanBreakdown from "../components/PlanBreakdown";
import AiCopilot from "../components/AiCopilot";
import RazorpayConnectionPanel from "../components/RazorpayConnectionPanel";
import RepPerformance from "../components/RepPerformance";
import SetupGuide from "../components/SetupGuide";
import Sidebar from "../components/Sidebar";
import StatCard from "../components/StatCard";
import { useBenchmarks } from "../hooks/useBenchmarks";
import { useCohort } from "../hooks/useCohort";
import { useLead, usePipeline } from "../hooks/useCrm";
import { useOverview, usePlans } from "../hooks/useMetrics";
import { useMovements, useSummary, useTrend } from "../hooks/useMrr";
import { useSegments } from "../hooks/useSegments";
import { useAuth } from "../context/AuthContext";
import type { SegmentFilters } from "../api/types";

type Tab = "mrr" | "cohort" | "metrics" | "benchmarks" | "crm" | "setup" | "settings" | "ai";

function currentMonth() {
  const d = new Date();
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}`;
}

const TAB_LABELS: Record<Tab, string> = {
  mrr:        "MRR",
  cohort:     "Cohort Retention",
  metrics:    "Metrics",
  benchmarks: "Benchmarks",
  crm:        "CRM",
  setup:      "Setup",
  settings:   "Settings",
  ai:         "AI Copilot",
};

function Skeleton({ className = "" }: { className?: string }) {
  return (
    <div
      className={`animate-pulse rounded-xl ${className}`}
      style={{ background: "var(--bg-2)", border: "1px solid var(--border-subtle)" }}
    />
  );
}

export default function Dashboard() {
  const { userName, clearSession } = useAuth();
  const [tab, setTab] = useState<Tab>("mrr");
  const [page, setPage] = useState(1);
  const [month, setMonth] = useState(currentMonth);
  const [filters, setFilters] = useState<SegmentFilters>({});
  const [selectedLeadId, setSelectedLeadId] = useState<string | null>(null);
  const [showAddLead, setShowAddLead] = useState(false);
  const [addLeadStageId, setAddLeadStageId] = useState<string | undefined>();
  const [crmView, setCrmView] = useState<"board" | "table">("board");
  const [sidebarCollapsed, setSidebarCollapsed] = useState(
    () => localStorage.getItem("sidebar_collapsed") === "1"
  );
  const [mobileSidebarOpen, setMobileSidebarOpen] = useState(false);

  const segments = useSegments();
  const summary = useSummary(month, filters);
  const trend = useTrend(12, filters);
  const movements = useMovements(month, page, filters);
  const cohort = useCohort(24);
  const overview = useOverview(month, filters);
  const plans = usePlans(month);
  const benchmarks = useBenchmarks(month);
  const pipeline = usePipeline();
  const selectedLead = useLead(selectedLeadId);

  function handleMonthChange(m: string) {
    setMonth(m);
    setPage(1);
  }

  function handleFilterChange(f: SegmentFilters) {
    setFilters(f);
    setPage(1);
  }

  function handleSidebarToggle() {
    setSidebarCollapsed((c) => {
      const next = !c;
      localStorage.setItem("sidebar_collapsed", next ? "1" : "0");
      return next;
    });
  }

  if (summary.isError) {
    const status = (summary.error as { response?: { status: number } })?.response?.status;
    const msg =
      status === 401
        ? "Session expired. Please log in again."
        : "Failed to load data. Is the API server running?";
    return (
      <div className="flex min-h-screen items-center justify-center text-sm" style={{ color: "var(--negative)" }}>
        {msg}
      </div>
    );
  }

  const stages = pipeline.data?.pipeline.map(({ leads: _ignored, ...stage }) => stage) ?? [];
  const allLeads = [
    ...(pipeline.data?.pipeline.flatMap((stage) => stage.leads) ?? []),
    ...(pipeline.data?.unassigned ?? []),
  ];

  const showFilterBar = tab === "mrr" || tab === "metrics";

  return (
    <div className="flex min-h-screen" style={{ background: "var(--bg-0)" }}>
      <Sidebar
        activeTab={tab}
        onTabChange={setTab}
        collapsed={sidebarCollapsed}
        onToggle={handleSidebarToggle}
        userName={userName}
        onSignOut={clearSession}
        mobileSidebarOpen={mobileSidebarOpen}
        onMobileSidebarClose={() => setMobileSidebarOpen(false)}
      />

      {/* Main content shifts with sidebar */}
      <div
        className={`flex flex-1 flex-col min-h-screen transition-[margin] duration-200 ${
          sidebarCollapsed ? "md:ml-[52px]" : "md:ml-[220px]"
        }`}
      >
        {/* Sticky topbar */}
        <header
          className="h-14 flex items-center justify-between px-4 md:px-6 gap-4 sticky top-0 z-20 border-b"
          style={{ background: "var(--bg-1)", borderColor: "var(--border-subtle)" }}
        >
          {/* Mobile hamburger */}
          <button
            type="button"
            aria-label="Open menu"
            className="md:hidden flex items-center justify-center w-8 h-8 rounded-lg transition-colors"
            style={{ color: "var(--text-secondary)" }}
            onClick={() => setMobileSidebarOpen(true)}
          >
            <Menu size={18} />
          </button>

          <h1 className="text-sm font-semibold truncate" style={{ color: "var(--text-primary)" }}>
            {TAB_LABELS[tab]}
          </h1>

          {/* CRM view toggle — in topbar for CRM */}
          {tab === "crm" && (
            <div className="flex items-center gap-2 ml-auto">
              <div
                className="flex gap-0.5 rounded-lg p-0.5"
                style={{ background: "var(--surface-1)", border: "1px solid var(--border-subtle)" }}
              >
                {(["board", "table"] as const).map((v) => (
                  <button
                    key={v}
                    type="button"
                    onClick={() => setCrmView(v)}
                    className="rounded-md px-3 py-1 text-xs font-medium transition-colors"
                    style={
                      crmView === v
                        ? { background: "var(--surface-3)", color: "var(--text-primary)" }
                        : { color: "var(--text-secondary)" }
                    }
                  >
                    {v === "board" ? "Kanban" : "Table"}
                  </button>
                ))}
              </div>
              <button
                type="button"
                onClick={() => { setAddLeadStageId(undefined); setShowAddLead(true); }}
                className="rounded-lg px-3 py-1.5 text-xs font-semibold transition-all hover:brightness-110"
                style={{ background: "var(--brand)", color: "#020d07" }}
              >
                + Add Lead
              </button>
            </div>
          )}

          {/* FilterBar inline in topbar */}
          {showFilterBar && (
            <div className="ml-auto">
              <FilterBar
                month={month}
                onMonthChange={handleMonthChange}
                segments={segments.data}
                filters={filters}
                onFilterChange={handleFilterChange}
              />
            </div>
          )}
        </header>

        {/* Page content */}
        <main className="flex-1 p-4 md:p-6 overflow-auto">

          {/* ── MRR ──────────────────────────────────── */}
          {tab === "mrr" && (
            <div className="space-y-5">
              <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
                {summary.isPending
                  ? Array.from({ length: 3 }).map((_, i) => <Skeleton key={i} className="h-28" />)
                  : (
                    <>
                      <StatCard label="Opening MRR" valuePaise={summary.data!.opening_mrr_paise} />
                      <StatCard label="Net New MRR" valuePaise={summary.data!.net_new_mrr_paise} positive />
                      <StatCard label="Closing MRR" valuePaise={summary.data!.closing_mrr_paise} />
                    </>
                  )}
              </div>

              {trend.isPending
                ? <Skeleton className="h-72" />
                : trend.data
                  ? <MrrChart data={trend.data} />
                  : null}

              {movements.data && (
                <MovementsTable
                  movements={movements.data.movements}
                  page={page}
                  onPageChange={setPage}
                  hasMore={movements.data.movements.length === movements.data.page_size}
                  month={month}
                  planId={filters.planId}
                />
              )}
            </div>
          )}

          {/* ── Cohort ───────────────────────────────── */}
          {tab === "cohort" && (
            cohort.isPending
              ? <Skeleton className="h-48" />
              : <CohortHeatmap cohorts={cohort.data ?? []} />
          )}

          {/* ── Metrics ──────────────────────────────── */}
          {tab === "metrics" && (
            <div className="space-y-5">
              {overview.isPending
                ? <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
                    {Array.from({ length: 8 }).map((_, i) => <Skeleton key={i} className="h-24" />)}
                  </div>
                : overview.data
                  ? <MetricsOverviewPanel data={overview.data} />
                  : null}

              {plans.isPending
                ? <Skeleton className="h-48" />
                : plans.data
                  ? <PlanBreakdown plans={plans.data.plans} totalMrrPaise={plans.data.total_mrr_paise} />
                  : null}
            </div>
          )}

          {/* ── Benchmarks ───────────────────────────── */}
          {tab === "benchmarks" && (
            benchmarks.isPending
              ? <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
                  {Array.from({ length: 5 }).map((_, i) => <Skeleton key={i} className="h-44" />)}
                </div>
              : benchmarks.data
                ? <BenchmarkGauge items={benchmarks.data.benchmarks} dataSource={benchmarks.data.data_source} />
                : null
          )}

          {/* ── CRM ──────────────────────────────────── */}
          {tab === "crm" && (
            <div className="space-y-6">
              {pipeline.isPending
                ? <div className="flex gap-4 overflow-x-auto pb-4">
                    {Array.from({ length: 4 }).map((_, i) => (
                      <Skeleton key={i} className="h-64 w-64 flex-shrink-0" />
                    ))}
                  </div>
                : pipeline.data
                  ? crmView === "board"
                    ? (
                      <PipelineBoard
                        pipeline={pipeline.data.pipeline}
                        unassigned={pipeline.data.unassigned}
                        onLeadClick={(id) => setSelectedLeadId(id)}
                        onAddLead={(stageId) => { setAddLeadStageId(stageId); setShowAddLead(true); }}
                      />
                    ) : (
                      <LeadsTable
                        leads={allLeads}
                        stages={stages}
                        onLeadClick={(id) => setSelectedLeadId(id)}
                        onAddLead={() => { setAddLeadStageId(undefined); setShowAddLead(true); }}
                      />
                    )
                  : null}

              <RepPerformance />
            </div>
          )}

          {/* ── Setup ────────────────────────────────── */}
          {tab === "setup" && (
            <SetupGuide audience="private" onOpenSettings={() => setTab("settings")} />
          )}

          {/* ── Settings ─────────────────────────────── */}
          {tab === "settings" && (
            <div className="space-y-5">
              <RazorpayConnectionPanel />
              <ApiKeyManager />
              <AuditLog />
            </div>
          )}

          {/* ── AI ───────────────────────────────────── */}
          {tab === "ai" && <AiCopilot />}

        </main>
      </div>

      {/* Drawers / Modals */}
      {selectedLeadId && (
        <LeadDrawer
          lead={selectedLead.data}
          loading={selectedLead.isPending}
          stages={stages}
          onClose={() => setSelectedLeadId(null)}
          onDeleted={() => setSelectedLeadId(null)}
        />
      )}

      {showAddLead && (
        <AddLeadModal
          stages={stages}
          defaultStageId={addLeadStageId}
          onClose={() => setShowAddLead(false)}
        />
      )}
    </div>
  );
}
