import { createBearerClient } from "./client";

export interface Stage {
  id: string;
  name: string;
  position: number;
  color: string;
}

export interface Lead {
  id: string;
  stage_id: string | null;
  customer_id: string | null;
  name: string;
  email: string | null;
  company: string | null;
  phone: string | null;
  plan_interest: string | null;
  mrr_estimate_paise: number;
  source: string | null;
  owner: string | null;
  notes: string | null;
  created_at: string;
  updated_at: string;
}

export interface Activity {
  id: string;
  type: string;
  body: string;
  created_at: string;
}

export interface LeadWithActivities extends Lead {
  activities: Activity[];
}

export interface StageWithLeads extends Stage {
  leads: Lead[];
}

export interface PipelineResponse {
  pipeline: StageWithLeads[];
  unassigned: Lead[];
}

// ── Stages ────────────────────────────────────────────────────────────────────

export async function fetchStages(token: string): Promise<Stage[]> {
  const { data } = await createBearerClient(token).get("/api/v1/crm/stages");
  return data.stages;
}

export async function createStage(token: string, name: string, color?: string): Promise<Stage> {
  const { data } = await createBearerClient(token).post("/api/v1/crm/stages", { name, color });
  return data;
}

export async function updateStage(
  token: string,
  stageId: string,
  patch: Partial<Pick<Stage, "name" | "color" | "position">>,
): Promise<Stage> {
  const { data } = await createBearerClient(token).put(`/api/v1/crm/stages/${stageId}`, patch);
  return data;
}

export async function deleteStage(token: string, stageId: string): Promise<void> {
  await createBearerClient(token).delete(`/api/v1/crm/stages/${stageId}`);
}

// ── Leads ─────────────────────────────────────────────────────────────────────

export async function fetchLeads(token: string, stageId?: string): Promise<Lead[]> {
  const params = stageId ? { stage_id: stageId } : {};
  const { data } = await createBearerClient(token).get("/api/v1/crm/leads", { params });
  return data.leads;
}

export async function fetchPipeline(token: string): Promise<PipelineResponse> {
  const { data } = await createBearerClient(token).get("/api/v1/crm/pipeline");
  return data;
}

export async function fetchLead(token: string, leadId: string): Promise<LeadWithActivities> {
  const { data } = await createBearerClient(token).get(`/api/v1/crm/leads/${leadId}`);
  return data;
}

export async function createLead(
  token: string,
  lead: Omit<Lead, "id" | "customer_id" | "created_at" | "updated_at">,
): Promise<Lead> {
  const { data } = await createBearerClient(token).post("/api/v1/crm/leads", lead);
  return data;
}

export async function updateLead(
  token: string,
  leadId: string,
  patch: Partial<Omit<Lead, "id" | "customer_id" | "created_at" | "updated_at">>,
): Promise<Lead> {
  const { data } = await createBearerClient(token).put(`/api/v1/crm/leads/${leadId}`, patch);
  return data;
}

export async function deleteLead(token: string, leadId: string): Promise<void> {
  await createBearerClient(token).delete(`/api/v1/crm/leads/${leadId}`);
}

export async function addActivity(
  token: string,
  leadId: string,
  type: string,
  body: string,
): Promise<Activity> {
  const { data } = await createBearerClient(token).post(`/api/v1/crm/leads/${leadId}/activities`, { type, body });
  return data;
}

export async function enrichLead(token: string, leadId: string): Promise<Lead> {
  const { data } = await createBearerClient(token).post(`/api/v1/crm/leads/${leadId}/enrich`);
  return data;
}

// ── Tasks ─────────────────────────────────────────────────────────────────────

export interface Task {
  id: string;
  lead_id: string | null;
  title: string;
  description: string | null;
  assignee: string | null;
  due_date: string | null;
  status: "open" | "done";
  created_at: string;
  updated_at: string;
}

export async function fetchTasks(token: string, leadId?: string, status?: string): Promise<Task[]> {
  const params: Record<string, string> = {};
  if (leadId) params.lead_id = leadId;
  if (status) params.status = status;
  const { data } = await createBearerClient(token).get("/api/v1/crm/tasks", { params });
  return data.tasks;
}

export async function createTask(
  token: string,
  task: { title: string; lead_id?: string; description?: string; assignee?: string; due_date?: string },
): Promise<Task> {
  const { data } = await createBearerClient(token).post("/api/v1/crm/tasks", task);
  return data;
}

export async function updateTask(
  token: string,
  taskId: string,
  patch: Partial<Pick<Task, "title" | "description" | "assignee" | "due_date" | "status">>,
): Promise<Task> {
  const { data } = await createBearerClient(token).put(`/api/v1/crm/tasks/${taskId}`, patch);
  return data;
}

export async function deleteTask(token: string, taskId: string): Promise<void> {
  await createBearerClient(token).delete(`/api/v1/crm/tasks/${taskId}`);
}

// ── Sequences ─────────────────────────────────────────────────────────────────

export interface SequenceStep {
  id: string;
  step_num: number;
  delay_days: number;
  subject: string;
  body: string;
}

export interface Sequence {
  id: string;
  name: string;
  created_at: string;
  step_count: number;
  active_enrollments: number;
}

export interface SequenceDetail extends Sequence {
  steps: SequenceStep[];
}

export interface Enrollment {
  id: string;
  sequence_id: string;
  sequence_name: string;
  current_step: number;
  status: "active" | "completed" | "stopped";
  enrolled_at: string;
}

export interface RepStat {
  rep: string;
  total_leads: number;
  won_leads: number;
  lost_leads: number;
  pipeline_mrr_paise: number;
  new_leads_30d: number;
}

export async function fetchSequences(token: string): Promise<Sequence[]> {
  const { data } = await createBearerClient(token).get("/api/v1/crm/sequences");
  return data.sequences;
}

export async function createSequence(token: string, name: string): Promise<Sequence> {
  const { data } = await createBearerClient(token).post("/api/v1/crm/sequences", { name });
  return data;
}

export async function getSequence(token: string, seqId: string): Promise<SequenceDetail> {
  const { data } = await createBearerClient(token).get(`/api/v1/crm/sequences/${seqId}`);
  return data;
}

export async function deleteSequence(token: string, seqId: string): Promise<void> {
  await createBearerClient(token).delete(`/api/v1/crm/sequences/${seqId}`);
}

export async function addSequenceStep(
  token: string,
  seqId: string,
  step: { step_num: number; delay_days: number; subject: string; body: string },
): Promise<SequenceStep> {
  const { data } = await createBearerClient(token).post(`/api/v1/crm/sequences/${seqId}/steps`, step);
  return data;
}

export async function deleteSequenceStep(token: string, seqId: string, stepId: string): Promise<void> {
  await createBearerClient(token).delete(`/api/v1/crm/sequences/${seqId}/steps/${stepId}`);
}

export async function enrollLead(token: string, seqId: string, leadId: string): Promise<Enrollment> {
  const { data } = await createBearerClient(token).post(`/api/v1/crm/sequences/${seqId}/enroll`, { lead_id: leadId });
  return data;
}

export async function unenrollLead(token: string, seqId: string, leadId: string): Promise<void> {
  await createBearerClient(token).delete(`/api/v1/crm/sequences/${seqId}/enroll/${leadId}`);
}

export async function fetchLeadEnrollments(token: string, leadId: string): Promise<Enrollment[]> {
  const { data } = await createBearerClient(token).get(`/api/v1/crm/leads/${leadId}/enrollments`);
  return data.enrollments;
}

export async function fetchRepStats(token: string): Promise<RepStat[]> {
  const { data } = await createBearerClient(token).get("/api/v1/crm/reps");
  return data.reps;
}
