import { useState } from "react";
import {
  useSequences,
  useSequenceDetail,
  useCreateSequence,
  useDeleteSequence,
  useAddSequenceStep,
  useDeleteSequenceStep,
  useEnrollLead,
} from "../hooks/useCrm";
import type { Sequence, SequenceStep } from "../api/crm";

interface Props {
  leadId?: string;
}

export default function SequenceBuilder({ leadId }: Props) {
  const sequences = useSequences();
  const createSeq = useCreateSequence();
  const deleteSeq = useDeleteSequence();
  const addStep = useAddSequenceStep();
  const deleteStep = useDeleteSequenceStep();
  const enrollLead = useEnrollLead();

  const [selectedId, setSelectedId] = useState<string | null>(null);
  const detail = useSequenceDetail(selectedId);

  const [showCreate, setShowCreate] = useState(false);
  const [newSeqName, setNewSeqName] = useState("");
  const [showAddStep, setShowAddStep] = useState(false);
  const [stepSubject, setStepSubject] = useState("");
  const [stepBody, setStepBody] = useState("");
  const [stepDelay, setStepDelay] = useState(0);

  async function handleCreateSeq(e: React.FormEvent) {
    e.preventDefault();
    if (!newSeqName.trim()) return;
    const seq = await createSeq.mutateAsync(newSeqName.trim());
    setSelectedId(seq.id);
    setNewSeqName("");
    setShowCreate(false);
  }

  async function handleAddStep(e: React.FormEvent) {
    e.preventDefault();
    if (!selectedId || !stepSubject.trim() || !stepBody.trim()) return;
    const nextNum = (detail.data?.steps.length ?? 0) + 1;
    await addStep.mutateAsync({ seqId: selectedId, step: { step_num: nextNum, delay_days: stepDelay, subject: stepSubject.trim(), body: stepBody.trim() } });
    setStepSubject("");
    setStepBody("");
    setStepDelay(0);
    setShowAddStep(false);
  }

  async function handleEnroll(seqId: string) {
    if (!leadId) return;
    await enrollLead.mutateAsync({ seqId, leadId });
    alert("Lead enrolled in sequence.");
  }

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <p className="text-xs font-semibold text-gray-500 uppercase">Email Sequences</p>
        <button onClick={() => setShowCreate(true)} className="text-xs text-indigo-600 hover:text-indigo-800">+ New</button>
      </div>

      {showCreate && (
        <form onSubmit={handleCreateSeq} className="flex gap-2">
          <input
            autoFocus
            value={newSeqName}
            onChange={(e) => setNewSeqName(e.target.value)}
            placeholder="Sequence name"
            className="flex-1 border border-gray-200 rounded-lg px-2.5 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-300"
          />
          <button type="button" onClick={() => setShowCreate(false)} className="text-xs text-gray-400">✕</button>
          <button type="submit" disabled={!newSeqName.trim() || createSeq.isPending}
            className="text-xs px-3 py-1.5 bg-indigo-600 text-white rounded-lg disabled:opacity-50">
            Create
          </button>
        </form>
      )}

      {sequences.isPending ? (
        <div className="h-16 bg-gray-100 rounded animate-pulse" />
      ) : !sequences.data?.length ? (
        <p className="text-xs text-gray-400">No sequences yet.</p>
      ) : (
        <div className="space-y-1">
          {sequences.data.map((s: Sequence) => (
            <div key={s.id} className={`border rounded-lg overflow-hidden ${selectedId === s.id ? "border-indigo-200" : "border-gray-100"}`}>
              <div
                className="flex items-center justify-between px-3 py-2 cursor-pointer hover:bg-gray-50"
                onClick={() => setSelectedId(selectedId === s.id ? null : s.id)}
              >
                <div>
                  <p className="text-sm font-medium text-gray-800">{s.name}</p>
                  <p className="text-xs text-gray-400">{s.step_count} step{s.step_count !== 1 ? "s" : ""} · {s.active_enrollments} active</p>
                </div>
                <div className="flex items-center gap-2">
                  {leadId && (
                    <button
                      onClick={(e) => { e.stopPropagation(); handleEnroll(s.id); }}
                      disabled={enrollLead.isPending}
                      className="text-xs px-2.5 py-1 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 disabled:opacity-50"
                    >
                      Enroll
                    </button>
                  )}
                  <button
                    onClick={(e) => { e.stopPropagation(); if (confirm(`Delete "${s.name}"?`)) deleteSeq.mutateAsync(s.id); }}
                    className="text-xs text-gray-300 hover:text-red-400"
                  >
                    ✕
                  </button>
                </div>
              </div>

              {selectedId === s.id && (
                <div className="border-t border-gray-100 bg-gray-50 p-3 space-y-2">
                  {detail.isPending ? (
                    <div className="h-8 bg-gray-200 rounded animate-pulse" />
                  ) : (detail.data?.steps ?? []).map((step: SequenceStep) => (
                    <div key={step.id} className="flex items-start gap-2 group">
                      <div className="shrink-0 w-6 h-6 bg-indigo-100 text-indigo-700 rounded-full flex items-center justify-center text-xs font-bold">
                        {step.step_num}
                      </div>
                      <div className="flex-1 min-w-0">
                        <p className="text-xs font-medium text-gray-700">{step.subject}</p>
                        <p className="text-xs text-gray-400 truncate">{step.body}</p>
                        {step.delay_days > 0 && <p className="text-xs text-gray-400">After {step.delay_days}d</p>}
                      </div>
                      <button
                        onClick={() => deleteStep.mutateAsync({ seqId: s.id, stepId: step.id })}
                        className="opacity-0 group-hover:opacity-100 text-xs text-gray-300 hover:text-red-400"
                      >
                        ✕
                      </button>
                    </div>
                  ))}

                  {showAddStep ? (
                    <form onSubmit={handleAddStep} className="space-y-2 pt-1">
                      <input
                        autoFocus
                        value={stepSubject}
                        onChange={(e) => setStepSubject(e.target.value)}
                        placeholder="Email subject"
                        className="w-full border border-gray-200 rounded px-2.5 py-1.5 text-xs focus:outline-none focus:ring-2 focus:ring-indigo-300"
                      />
                      <textarea
                        rows={2}
                        value={stepBody}
                        onChange={(e) => setStepBody(e.target.value)}
                        placeholder="Email body"
                        className="w-full border border-gray-200 rounded px-2.5 py-1.5 text-xs resize-none focus:outline-none focus:ring-2 focus:ring-indigo-300"
                      />
                      <div className="flex items-center gap-2">
                        <label className="text-xs text-gray-500">Delay (days)</label>
                        <input
                          type="number"
                          min={0}
                          value={stepDelay}
                          onChange={(e) => setStepDelay(Number(e.target.value))}
                          className="w-16 border border-gray-200 rounded px-2 py-1 text-xs"
                        />
                        <button type="button" onClick={() => setShowAddStep(false)} className="text-xs text-gray-400 ml-auto">Cancel</button>
                        <button type="submit" disabled={!stepSubject.trim() || !stepBody.trim() || addStep.isPending}
                          className="text-xs px-3 py-1 bg-indigo-600 text-white rounded disabled:opacity-50">
                          Add
                        </button>
                      </div>
                    </form>
                  ) : (
                    <button onClick={() => setShowAddStep(true)}
                      className="text-xs text-indigo-600 hover:text-indigo-800 mt-1">
                      + Add step
                    </button>
                  )}
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
