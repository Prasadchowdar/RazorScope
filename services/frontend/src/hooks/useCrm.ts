import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  fetchPipeline,
  fetchLead,
  createLead,
  updateLead,
  deleteLead,
  addActivity,
  enrichLead,
  createStage,
  deleteStage,
  fetchTasks,
  createTask,
  updateTask,
  deleteTask,
  fetchSequences,
  createSequence,
  getSequence,
  deleteSequence,
  addSequenceStep,
  deleteSequenceStep,
  enrollLead,
  unenrollLead,
  fetchLeadEnrollments,
  fetchRepStats,
  type Lead,
  type Task,
} from "../api/crm";
import { useAuth } from "../context/AuthContext";

export function usePipeline() {
  const { accessToken } = useAuth();
  return useQuery({
    queryKey: ["crm-pipeline"],
    queryFn: () => fetchPipeline(accessToken!),
    enabled: !!accessToken,
    staleTime: 30_000,
  });
}

export function useLead(leadId: string | null) {
  const { accessToken } = useAuth();
  return useQuery({
    queryKey: ["crm-lead", leadId],
    queryFn: () => fetchLead(accessToken!, leadId!),
    enabled: !!accessToken && !!leadId,
    staleTime: 15_000,
  });
}

export function useCreateLead() {
  const { accessToken } = useAuth();
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (lead: Omit<Lead, "id" | "customer_id" | "created_at" | "updated_at">) =>
      createLead(accessToken!, lead),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["crm-pipeline"] }),
  });
}

export function useUpdateLead() {
  const { accessToken } = useAuth();
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ leadId, patch }: { leadId: string; patch: Partial<Lead> }) =>
      updateLead(accessToken!, leadId, patch),
    onSuccess: (_data, vars) => {
      qc.invalidateQueries({ queryKey: ["crm-pipeline"] });
      qc.invalidateQueries({ queryKey: ["crm-lead", vars.leadId] });
    },
  });
}

export function useDeleteLead() {
  const { accessToken } = useAuth();
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (leadId: string) => deleteLead(accessToken!, leadId),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["crm-pipeline"] }),
  });
}

export function useAddActivity() {
  const { accessToken } = useAuth();
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ leadId, type, body }: { leadId: string; type: string; body: string }) =>
      addActivity(accessToken!, leadId, type, body),
    onSuccess: (_data, vars) => {
      qc.invalidateQueries({ queryKey: ["crm-lead", vars.leadId] });
    },
  });
}

export function useCreateStage() {
  const { accessToken } = useAuth();
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ name, color }: { name: string; color: string }) =>
      createStage(accessToken!, name, color),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["crm-pipeline"] }),
  });
}

export function useDeleteStage() {
  const { accessToken } = useAuth();
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (stageId: string) => deleteStage(accessToken!, stageId),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["crm-pipeline"] }),
  });
}

export function useEnrichLead() {
  const { accessToken } = useAuth();
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (leadId: string) => enrichLead(accessToken!, leadId),
    onSuccess: (_data, leadId) => {
      qc.invalidateQueries({ queryKey: ["crm-lead", leadId] });
      qc.invalidateQueries({ queryKey: ["crm-pipeline"] });
    },
  });
}

// ── Tasks ─────────────────────────────────────────────────────────────────────

export function useTasks(leadId?: string, status?: string) {
  const { accessToken } = useAuth();
  return useQuery({
    queryKey: ["crm-tasks", leadId, status],
    queryFn: () => fetchTasks(accessToken!, leadId, status),
    enabled: !!accessToken,
    staleTime: 15_000,
  });
}

export function useCreateTask() {
  const { accessToken } = useAuth();
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (task: { title: string; lead_id?: string; description?: string; assignee?: string; due_date?: string }) =>
      createTask(accessToken!, task),
    onSuccess: (_data, vars) => {
      qc.invalidateQueries({ queryKey: ["crm-tasks", vars.lead_id] });
      qc.invalidateQueries({ queryKey: ["crm-tasks"] });
    },
  });
}

export function useUpdateTask() {
  const { accessToken } = useAuth();
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ taskId, patch }: { taskId: string; patch: Partial<Task> }) =>
      updateTask(accessToken!, taskId, patch),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["crm-tasks"] }),
  });
}

export function useDeleteTask() {
  const { accessToken } = useAuth();
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (taskId: string) => deleteTask(accessToken!, taskId),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["crm-tasks"] }),
  });
}

// ── Sequences ─────────────────────────────────────────────────────────────────

export function useSequences() {
  const { accessToken } = useAuth();
  return useQuery({
    queryKey: ["crm-sequences"],
    queryFn: () => fetchSequences(accessToken!),
    enabled: !!accessToken,
    staleTime: 60_000,
  });
}

export function useSequenceDetail(seqId: string | null) {
  const { accessToken } = useAuth();
  return useQuery({
    queryKey: ["crm-sequence", seqId],
    queryFn: () => getSequence(accessToken!, seqId!),
    enabled: !!accessToken && !!seqId,
    staleTime: 30_000,
  });
}

export function useCreateSequence() {
  const { accessToken } = useAuth();
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (name: string) => createSequence(accessToken!, name),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["crm-sequences"] }),
  });
}

export function useDeleteSequence() {
  const { accessToken } = useAuth();
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (seqId: string) => deleteSequence(accessToken!, seqId),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["crm-sequences"] }),
  });
}

export function useAddSequenceStep() {
  const { accessToken } = useAuth();
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ seqId, step }: { seqId: string; step: { step_num: number; delay_days: number; subject: string; body: string } }) =>
      addSequenceStep(accessToken!, seqId, step),
    onSuccess: (_data, vars) => qc.invalidateQueries({ queryKey: ["crm-sequence", vars.seqId] }),
  });
}

export function useDeleteSequenceStep() {
  const { accessToken } = useAuth();
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ seqId, stepId }: { seqId: string; stepId: string }) =>
      deleteSequenceStep(accessToken!, seqId, stepId),
    onSuccess: (_data, vars) => qc.invalidateQueries({ queryKey: ["crm-sequence", vars.seqId] }),
  });
}

export function useEnrollLead() {
  const { accessToken } = useAuth();
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ seqId, leadId }: { seqId: string; leadId: string }) =>
      enrollLead(accessToken!, seqId, leadId),
    onSuccess: (_data, vars) => {
      qc.invalidateQueries({ queryKey: ["crm-enrollments", vars.leadId] });
      qc.invalidateQueries({ queryKey: ["crm-sequences"] });
    },
  });
}

export function useUnenrollLead() {
  const { accessToken } = useAuth();
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ seqId, leadId }: { seqId: string; leadId: string }) =>
      unenrollLead(accessToken!, seqId, leadId),
    onSuccess: (_data, vars) => {
      qc.invalidateQueries({ queryKey: ["crm-enrollments", vars.leadId] });
      qc.invalidateQueries({ queryKey: ["crm-sequences"] });
    },
  });
}

export function useLeadEnrollments(leadId: string | null) {
  const { accessToken } = useAuth();
  return useQuery({
    queryKey: ["crm-enrollments", leadId],
    queryFn: () => fetchLeadEnrollments(accessToken!, leadId!),
    enabled: !!accessToken && !!leadId,
    staleTime: 15_000,
  });
}

// ── Rep Stats ─────────────────────────────────────────────────────────────────

export function useRepStats() {
  const { accessToken } = useAuth();
  return useQuery({
    queryKey: ["crm-reps"],
    queryFn: () => fetchRepStats(accessToken!),
    enabled: !!accessToken,
    staleTime: 60_000,
  });
}
