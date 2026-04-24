import type { SegmentFilters } from "./types";
import { createBearerClient } from "./client";

function segParams(f?: SegmentFilters): Record<string, unknown> {
  if (!f) return {};
  const p: Record<string, unknown> = {};
  if (f.planId) p.plan_id = f.planId;
  if (f.country) p.country = f.country;
  if (f.source) p.source = f.source;
  if (f.paymentMethod) p.payment_method = f.paymentMethod;
  return p;
}

export interface MetricsOverview {
  month: string;
  active_subscribers: number;
  new_subscribers: number;
  churned_subscribers: number;
  reactivated_subscribers: number;
  arpu_paise: number;
  customer_churn_rate: number;
  revenue_churn_rate: number;
  nrr_pct: number;
  ltv_months: number | null;
  opening_mrr_paise: number;
  closing_mrr_paise: number;
}

export interface PlanRow {
  plan_id: string;
  subscriber_count: number;
  net_mrr_delta_paise: number;
  pct_of_total: number;
}

export interface MetricsPlans {
  month: string;
  total_mrr_paise: number;
  plans: PlanRow[];
}

export async function fetchOverview(
  token: string,
  month?: string,
  filters?: SegmentFilters,
): Promise<MetricsOverview> {
  const params: Record<string, unknown> = { ...segParams(filters) };
  if (month) params.month = month;
  const { data } = await createBearerClient(token).get("/api/v1/metrics/overview", { params });
  return data;
}

export async function fetchPlans(token: string, month?: string): Promise<MetricsPlans> {
  const params = month ? { month } : {};
  const { data } = await createBearerClient(token).get("/api/v1/metrics/plans", { params });
  return data;
}
