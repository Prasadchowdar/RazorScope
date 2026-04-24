import { createBearerClient } from "./client";

export interface ApiKey {
  id: string;
  name: string;
  key_prefix: string;
  role: "admin" | "viewer";
  last_used_at: string | null;
  expires_at: string | null;
  created_at: string;
  revoked_at: string | null;
}

export interface NewApiKey extends ApiKey {
  raw_key: string;
}

export interface AuditEntry {
  id: string;
  actor_key: string | null;
  action: string;
  resource: string | null;
  detail: Record<string, unknown> | null;
  ip_addr: string | null;
  created_at: string;
}

export async function fetchApiKeys(token: string): Promise<ApiKey[]> {
  const r = await createBearerClient(token).get("/api/v1/security/keys");
  return r.data.keys;
}

export async function createApiKey(
  token: string,
  name: string,
  role: "admin" | "viewer",
  expires_at?: string,
): Promise<NewApiKey> {
  const r = await createBearerClient(token).post("/api/v1/security/keys", { name, role, expires_at });
  return r.data;
}

export async function revokeApiKey(token: string, keyId: string): Promise<void> {
  await createBearerClient(token).delete(`/api/v1/security/keys/${keyId}`);
}

export async function fetchAuditLog(token: string, limit = 100): Promise<AuditEntry[]> {
  const r = await createBearerClient(token).get("/api/v1/security/audit", { params: { limit } });
  return r.data.entries;
}
