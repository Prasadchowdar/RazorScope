import { Plus } from "lucide-react";
import type { StageWithLeads, Lead, Stage } from "../api/crm";
import { useUpdateLead } from "../hooks/useCrm";

function paise(v: number) {
  if (v === 0) return "";
  return `₹${(v / 100).toLocaleString("en-IN")}`;
}

function initials(name: string) {
  return name.split(" ").slice(0, 2).map((w) => w[0]?.toUpperCase() ?? "").join("");
}

interface LeadCardProps {
  lead: Lead;
  stages: Stage[];
  onClick: () => void;
}

function LeadCard({ lead, stages, onClick }: LeadCardProps) {
  const updateLead = useUpdateLead();

  async function handleStageChange(e: React.ChangeEvent<HTMLSelectElement>) {
    e.stopPropagation();
    const newStageId = e.target.value || null;
    await updateLead.mutateAsync({ leadId: lead.id, patch: { stage_id: newStageId } });
  }

  return (
    <div
      onClick={onClick}
      className="rounded-xl p-3.5 cursor-pointer transition-all group bg-[var(--bg-2)] border border-[var(--border-subtle)] hover:border-[var(--border-default)] hover:bg-[var(--surface-2)]"
    >
      <div className="flex items-start gap-2.5 mb-2.5">
        <div
          className="w-7 h-7 rounded-full flex items-center justify-center text-xs font-semibold flex-shrink-0"
          style={{ background: "var(--brand-dim)", color: "var(--brand)" }}
        >
          {initials(lead.name)}
        </div>
        <div className="flex-1 min-w-0">
          <p className="text-sm font-medium text-[var(--text-primary)] truncate">{lead.name}</p>
          {lead.company && (
            <p className="text-xs text-[var(--text-muted)] truncate">{lead.company}</p>
          )}
        </div>
      </div>

      <div className="flex items-center justify-between gap-2">
        <div className="flex gap-1.5 flex-wrap">
          {lead.plan_interest && (
            <span className="text-[10px] font-medium px-1.5 py-0.5 rounded-full bg-[rgba(167,139,250,0.15)] text-violet-300 border border-[rgba(167,139,250,0.2)]">
              {lead.plan_interest}
            </span>
          )}
          {lead.mrr_estimate_paise > 0 && (
            <span className="text-[10px] font-medium px-1.5 py-0.5 rounded-full bg-[var(--positive-dim)] text-[var(--positive)] border border-[rgba(52,211,153,0.2)]">
              {paise(lead.mrr_estimate_paise)}
            </span>
          )}
          {lead.source && (
            <span className="text-[10px] font-medium px-1.5 py-0.5 rounded-full bg-[var(--surface-1)] text-[var(--text-muted)] border border-[var(--border-subtle)]">
              {lead.source}
            </span>
          )}
        </div>
        <select
          value={lead.stage_id ?? ""}
          onChange={handleStageChange}
          onClick={(e) => e.stopPropagation()}
          disabled={updateLead.isPending}
          title="Move to stage"
          className="text-xs border-0 bg-transparent text-[var(--text-muted)] focus:outline-none cursor-pointer hover:text-[var(--brand)] hidden group-hover:block"
        >
          <option value="">Unassigned</option>
          {stages.map((s) => <option key={s.id} value={s.id}>{s.name}</option>)}
        </select>
      </div>
    </div>
  );
}

interface Props {
  pipeline: StageWithLeads[];
  unassigned: Lead[];
  onLeadClick: (leadId: string) => void;
  onAddLead: (stageId?: string) => void;
}

export default function PipelineBoard({ pipeline, unassigned, onLeadClick, onAddLead }: Props) {
  const stages = pipeline.map(({ leads: _, ...s }) => s);
  const allColumns = [
    ...pipeline,
    ...(unassigned.length > 0
      ? [{ id: "__none__", name: "Unassigned", position: -1, color: "#4b6480", leads: unassigned }]
      : []),
  ];

  return (
    <div className="flex gap-4 overflow-x-auto pb-4" style={{ minHeight: "60vh" }}>
      {allColumns.map((stage) => (
        <div key={stage.id} className="flex-shrink-0 w-64 flex flex-col">
          {/* Column header */}
          <div className="flex items-center justify-between mb-3">
            <div className="flex items-center gap-2">
              <div
                className="w-2 h-2 rounded-full flex-shrink-0"
                style={{ backgroundColor: stage.color }}
              />
              <span className="text-xs font-semibold text-[var(--text-secondary)] truncate">{stage.name}</span>
              <span className="text-[10px] font-medium px-1.5 py-0.5 rounded-full bg-[var(--surface-1)] text-[var(--text-muted)] border border-[var(--border-subtle)]">
                {stage.leads.length}
              </span>
            </div>
            {stage.id !== "__none__" && (
              <button
                onClick={() => onAddLead(stage.id)}
                title="Add lead"
                aria-label="Add lead"
                className="w-6 h-6 flex items-center justify-center rounded-lg text-[var(--text-muted)] hover:text-[var(--brand)] hover:bg-[var(--surface-1)] transition-colors"
              >
                <Plus size={13} />
              </button>
            )}
          </div>

          {/* Cards */}
          <div className="flex flex-col gap-2 flex-1">
            {stage.leads.map((lead) => (
              <LeadCard
                key={lead.id}
                lead={lead}
                stages={stages}
                onClick={() => onLeadClick(lead.id)}
              />
            ))}
          </div>
        </div>
      ))}

      {/* Add lead placeholder */}
      <div className="flex-shrink-0 w-64">
        <button
          onClick={() => onAddLead()}
          className="w-full h-10 rounded-xl border-2 border-dashed border-[var(--border-subtle)] text-[var(--text-muted)] text-xs hover:border-[var(--brand)] hover:text-[var(--brand)] transition-colors"
        >
          + Add Lead
        </button>
      </div>
    </div>
  );
}
