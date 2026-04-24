import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { fetchApiKeys, createApiKey, revokeApiKey, fetchAuditLog } from "../api/security";
import { useAuth } from "../context/AuthContext";

export function useApiKeys() {
  const { accessToken } = useAuth();
  return useQuery({
    queryKey: ["apiKeys"],
    queryFn: () => fetchApiKeys(accessToken!),
    enabled: !!accessToken,
    staleTime: 30_000,
  });
}

export function useCreateApiKey() {
  const { accessToken } = useAuth();
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ name, role, expires_at }: { name: string; role: "admin" | "viewer"; expires_at?: string }) =>
      createApiKey(accessToken!, name, role, expires_at),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["apiKeys"] }),
  });
}

export function useRevokeApiKey() {
  const { accessToken } = useAuth();
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (keyId: string) => revokeApiKey(accessToken!, keyId),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["apiKeys"] }),
  });
}

export function useAuditLog(limit = 100) {
  const { accessToken } = useAuth();
  return useQuery({
    queryKey: ["auditLog", limit],
    queryFn: () => fetchAuditLog(accessToken!, limit),
    enabled: !!accessToken,
    staleTime: 15_000,
  });
}
