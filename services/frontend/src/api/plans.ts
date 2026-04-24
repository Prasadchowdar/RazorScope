import { createBearerClient } from "./client";

export async function fetchAvailablePlans(token: string): Promise<string[]> {
  const { data } = await createBearerClient(token).get("/api/v1/plans");
  return data.plans;
}
