import { createBearerClient } from "./client";

export interface BackfillJob {
  job_id: string;
  status: "pending" | "running" | "done" | "failed";
  from_date: string;
  to_date: string;
  pages_fetched: number;
  total_pages: number | null;
  error_detail: string | null;
  created_at: string | null;
  completed_at: string | null;
}

export async function createBackfillJob(
  token: string,
  fromDate: string,
  toDate: string,
): Promise<{ job_id: string; status: string }> {
  const { data } = await createBearerClient(token).post("/api/v1/backfill", {
    from_date: fromDate,
    to_date: toDate,
  });
  return data;
}

export async function listBackfillJobs(token: string): Promise<BackfillJob[]> {
  const { data } = await createBearerClient(token).get("/api/v1/backfill");
  return data.jobs;
}
