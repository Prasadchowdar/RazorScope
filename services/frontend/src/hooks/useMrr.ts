import { useQuery } from "@tanstack/react-query";
import { fetchSummary, fetchTrend, fetchMovements, fetchForecast } from "../api/mrr";
import { useAuth } from "../context/AuthContext";
import type { SegmentFilters } from "../api/types";

export function useSummary(month?: string, filters?: SegmentFilters) {
  const { accessToken } = useAuth();
  return useQuery({
    queryKey: ["mrr-summary", month, filters],
    queryFn: () => fetchSummary(accessToken!, month, filters),
    enabled: !!accessToken,
    staleTime: 60_000,
  });
}

export function useTrend(months = 12, filters?: SegmentFilters) {
  const { accessToken } = useAuth();
  return useQuery({
    queryKey: ["mrr-trend", months, filters],
    queryFn: () => fetchTrend(accessToken!, months, filters),
    enabled: !!accessToken,
    staleTime: 60_000,
  });
}

export function useMovements(month?: string, page = 1, filters?: SegmentFilters) {
  const { accessToken } = useAuth();
  return useQuery({
    queryKey: ["mrr-movements", month, page, filters],
    queryFn: () => fetchMovements(accessToken!, month, page, 50, filters),
    enabled: !!accessToken,
    staleTime: 60_000,
  });
}

export function useForecast(monthsHistory = 6, monthsAhead = 3) {
  const { accessToken } = useAuth();
  return useQuery({
    queryKey: ["mrr-forecast", monthsHistory, monthsAhead],
    queryFn: () => fetchForecast(accessToken!, monthsHistory, monthsAhead),
    enabled: !!accessToken,
    staleTime: 300_000,
  });
}
