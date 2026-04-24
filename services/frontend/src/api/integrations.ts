import { createBearerClient } from "./client";

export interface RazorpayIntegration {
  merchant_id: string;
  mode_basic: {
    webhook_url: string;
    webhook_secret: string;
  };
  mode_advanced: {
    razorpay_key_id: string;
    has_api_credentials: boolean;
    backfill_ready: boolean;
  };
}

export async function getRazorpayIntegration(token: string): Promise<RazorpayIntegration> {
  const { data } = await createBearerClient(token).get("/api/v1/integrations/razorpay");
  return data;
}

export async function saveRazorpayCredentials(
  token: string,
  razorpayKeyId: string,
  razorpayKeySecret: string,
): Promise<RazorpayIntegration> {
  const { data } = await createBearerClient(token).put("/api/v1/integrations/razorpay", {
    razorpay_key_id: razorpayKeyId,
    razorpay_key_secret: razorpayKeySecret,
  });
  return data;
}
