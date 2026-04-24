import { createBearerClient } from "./client";

export interface QueryResponse {
  sql: string;
  columns: string[];
  rows: (string | number | null)[][];
  summary: string;
}

export interface ChurnPreview {
  razorpay_sub_id: string;
  customer_name: string;
  customer_email: string;
  plan_id: string;
  current_mrr_paise: number;
  contraction_count: number;
  draft_subject: string;
  draft_body: string;
}

export interface ChurnDefenderResponse {
  found: number;
  tasks_created: number;
  previews: ChurnPreview[];
}

export interface MonthlyBriefResponse {
  month: string;
  brief: string;
}

export async function queryAnalytics(token: string, question: string): Promise<QueryResponse> {
  const { data } = await createBearerClient(token).post("/api/v1/agents/query", { question });
  return data;
}

export async function runChurnDefender(token: string): Promise<ChurnDefenderResponse> {
  const { data } = await createBearerClient(token).post("/api/v1/agents/churn-defender/run");
  return data;
}

export async function generateMonthlyBrief(token: string, month: string): Promise<MonthlyBriefResponse> {
  const { data } = await createBearerClient(token).get("/api/v1/agents/monthly-brief", {
    params: { month },
  });
  return data;
}
