import { createBearerClient } from "./client";

export interface CohortPeriod {
  period_number: number;
  period_month: string;
  retained_count: number;
  retention_pct: number;
  revenue_paise: number;
}

export interface CohortRow {
  cohort_month: string;
  cohort_size: number;
  periods: CohortPeriod[];
}

export async function fetchCohort(token: string, months = 12): Promise<CohortRow[]> {
  const { data } = await createBearerClient(token).get("/api/v1/cohort", { params: { months } });
  return data.cohorts;
}
