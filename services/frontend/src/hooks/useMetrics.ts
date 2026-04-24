import { useQuery } from "@tanstack/react-query";
import { fetchOverview, fetchPlans } from "../api/metrics";
import { useAuth } from "../context/AuthContext";
import type { SegmentFilters } from "../api/types";

export function useOverview(month?: string, filters?: SegmentFilters) {
  const { accessToken } = useAuth();
  return useQuery({
    queryKey: ["metrics-overview", month, filters],
    queryFn: () => fetchOverview(accessToken!, month, filters),
    enabled: !!accessToken,
    staleTime: 60_000,
  });
}

export function usePlans(month?: string) {
  const { accessToken } = useAuth();
  return useQuery({
    queryKey: ["metrics-plans", month],
    queryFn: () => fetchPlans(accessToken!, month),
    enabled: !!accessToken,
    staleTime: 60_000,
  });
}
