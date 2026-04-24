import { createBearerClient } from "./client";

const BASE = (window as any).__ENV__?.VITE_API_BASE
  ?? import.meta.env.VITE_API_BASE
  ?? "";

export interface TimelineEntry {
  razorpay_sub_id: string;
  customer_id: string;
  plan_id: string;
  movement_type: string;
  amount_paise: number;
  prev_amount_paise: number;
  delta_paise: number;
  voluntary: boolean;
  period_month: string;
}

export interface SubscriberDetail {
  razorpay_sub_id: string;
  customer_id: string;
  plan_id: string;
  current_amount_paise: number;
  timeline: TimelineEntry[];
}

export async function fetchSubscriber(token: string, subId: string): Promise<SubscriberDetail> {
  const { data } = await createBearerClient(token).get(`/api/v1/subscribers/${subId}`);
  return data;
}

export async function downloadMovementsCsv(
  token: string,
  month: string,
  planId?: string,
): Promise<void> {
  const params = new URLSearchParams({ month });
  if (planId) params.set("plan_id", planId);
  const resp = await fetch(
    `${BASE}/api/v1/mrr/movements/export?${params}`,
    { headers: { Authorization: `Bearer ${token}` } },
  );
  if (!resp.ok) throw new Error(`Export failed: ${resp.status}`);
  const blob = await resp.blob();
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = `mrr_movements_${month}.csv`;
  a.click();
  URL.revokeObjectURL(url);
}
