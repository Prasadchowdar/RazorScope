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

export interface MrrSummary {
  month: string;
  opening_mrr_paise: number;
  closing_mrr_paise: number;
  net_new_mrr_paise: number;
  movements: Record<string, number>;
}

export interface TrendMonth {
  month: string;
  opening_mrr_paise: number;
  closing_mrr_paise: number;
  net_new_mrr_paise: number;
  movements: Record<string, number>;
}

export interface Movement {
  razorpay_sub_id: string;
  movement_type: string;
  delta_paise: number;
  period_month: string;
  voluntary: boolean;
}

export async function fetchSummary(
  token: string,
  month?: string,
  filters?: SegmentFilters,
): Promise<MrrSummary> {
  const params: Record<string, unknown> = { ...segParams(filters) };
  if (month) params.month = month;
  const { data } = await createBearerClient(token).get("/api/v1/mrr/summary", { params });
  return data;
}

export async function fetchTrend(
  token: string,
  months = 12,
  filters?: SegmentFilters,
): Promise<TrendMonth[]> {
  const params: Record<string, unknown> = { months, ...segParams(filters) };
  const { data } = await createBearerClient(token).get("/api/v1/mrr/trend", { params });
  return data.months;
}

export async function fetchMovements(
  token: string,
  month?: string,
  page = 1,
  pageSize = 50,
  filters?: SegmentFilters,
): Promise<{ movements: Movement[]; page: number; page_size: number }> {
  const params: Record<string, unknown> = { page, page_size: pageSize, ...segParams(filters) };
  if (month) params.month = month;
  const { data } = await createBearerClient(token).get("/api/v1/mrr/movements", { params });
  return data;
}

export interface ForecastMonth {
  month: string;
  closing_mrr_paise: number;
  net_new_mrr_paise: number;
  is_forecast: true;
  confidence_low: number;
  confidence_high: number;
}

export async function fetchForecast(
  token: string,
  monthsHistory = 6,
  monthsAhead = 3,
): Promise<{ forecasted_months: ForecastMonth[]; warning?: string }> {
  const { data } = await createBearerClient(token).get("/api/v1/mrr/forecast", {
    params: { months_history: monthsHistory, months_ahead: monthsAhead },
  });
  return data;
}
