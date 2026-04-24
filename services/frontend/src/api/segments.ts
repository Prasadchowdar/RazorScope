import { createBearerClient } from "./client";

export interface SegmentValues {
  plans: string[];
  countries: string[];
  sources: string[];
  payment_methods: string[];
}

export async function fetchSegments(token: string): Promise<SegmentValues> {
  const { data } = await createBearerClient(token).get("/api/v1/segments");
  return data;
}
