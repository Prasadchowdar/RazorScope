import { useState } from "react";
import { useCreateLead } from "../hooks/useCrm";
import type { Stage } from "../api/crm";

interface Props {
  stages: Stage[];
  defaultStageId?: string;
  onClose: () => void;
}

const SOURCES = ["organic", "referral", "paid", "outbound", "event", "other"];

export default function AddLeadModal({ stages, defaultStageId, onClose }: Props) {
  const createLead = useCreateLead();
  const [form, setForm] = useState({
    name: "",
    email: "",
    company: "",
    phone: "",
    stage_id: defaultStageId ?? (stages[0]?.id ?? ""),
    plan_interest: "",
    mrr_estimate_paise: 0,
    source: "",
    owner: "",
    notes: "",
  });
  const [error, setError] = useState<string | null>(null);

  function field(key: keyof typeof form) {
    return (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement>) =>
      setForm((f) => ({ ...f, [key]: e.target.value }));
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    try {
      await createLead.mutateAsync({
        ...form,
        stage_id: form.stage_id || null,
        email: form.email || null,
        company: form.company || null,
        phone: form.phone || null,
        plan_interest: form.plan_interest || null,
        source: form.source || null,
        owner: form.owner || null,
        notes: form.notes || null,
        mrr_estimate_paise: Number(form.mrr_estimate_paise) || 0,
      });
      onClose();
    } catch {
      setError("Failed to create lead.");
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/40" onClick={onClose}>
      <div
        className="bg-white rounded-2xl shadow-2xl w-full max-w-md p-6"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between mb-5">
          <h2 className="text-base font-semibold text-gray-900">Add Lead</h2>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600 text-xl leading-none">×</button>
        </div>

        <form onSubmit={handleSubmit} className="space-y-3">
          <div>
            <label className="block text-xs text-gray-500 mb-1">Name *</label>
            <input
              required
              type="text"
              value={form.name}
              onChange={field("name")}
              className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-300"
              placeholder="Contact or company name"
            />
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-xs text-gray-500 mb-1">Email</label>
              <input type="email" value={form.email} onChange={field("email")}
                className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-300"
                placeholder="contact@company.com" />
            </div>
            <div>
              <label className="block text-xs text-gray-500 mb-1">Company</label>
              <input type="text" value={form.company} onChange={field("company")}
                className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-300"
                placeholder="Acme Inc." />
            </div>
            <div>
              <label className="block text-xs text-gray-500 mb-1">Stage</label>
              <select value={form.stage_id} onChange={field("stage_id")}
                className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-300">
                <option value="">Unassigned</option>
                {stages.map((s) => <option key={s.id} value={s.id}>{s.name}</option>)}
              </select>
            </div>
            <div>
              <label className="block text-xs text-gray-500 mb-1">Source</label>
              <select value={form.source} onChange={field("source")}
                className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-300">
                <option value="">—</option>
                {SOURCES.map((s) => <option key={s} value={s}>{s}</option>)}
              </select>
            </div>
            <div>
              <label className="block text-xs text-gray-500 mb-1">Plan Interest</label>
              <input type="text" value={form.plan_interest} onChange={field("plan_interest")}
                className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-300"
                placeholder="Pro / Enterprise" />
            </div>
            <div>
              <label className="block text-xs text-gray-500 mb-1">MRR Estimate (paise)</label>
              <input type="number" min={0} value={form.mrr_estimate_paise} onChange={field("mrr_estimate_paise")}
                className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-300"
                placeholder="50000" />
            </div>
            <div>
              <label className="block text-xs text-gray-500 mb-1">Owner</label>
              <input type="text" value={form.owner} onChange={field("owner")}
                className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-300"
                placeholder="alice" />
            </div>
            <div>
              <label className="block text-xs text-gray-500 mb-1">Phone</label>
              <input type="tel" value={form.phone} onChange={field("phone")}
                className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-300"
                placeholder="+91 98765 43210" />
            </div>
          </div>

          <div>
            <label className="block text-xs text-gray-500 mb-1">Notes</label>
            <textarea rows={2} value={form.notes} onChange={field("notes")}
              className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm resize-none focus:outline-none focus:ring-2 focus:ring-indigo-300"
              placeholder="Any context…" />
          </div>

          {error && <p className="text-xs text-red-500">{error}</p>}

          <div className="flex justify-end gap-2 pt-1">
            <button type="button" onClick={onClose}
              className="text-sm px-4 py-2 rounded-lg border border-gray-200 text-gray-600 hover:bg-gray-50">
              Cancel
            </button>
            <button type="submit" disabled={createLead.isPending}
              className="text-sm px-4 py-2 rounded-lg bg-indigo-600 text-white hover:bg-indigo-700 disabled:opacity-50">
              {createLead.isPending ? "Saving…" : "Add Lead"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
