import { useQuery } from "@tanstack/react-query";
import { fetchBenchmarks } from "../api/benchmarks";
import { useAuth } from "../context/AuthContext";

export function useBenchmarks(month?: string) {
  const { accessToken } = useAuth();
  return useQuery({
    queryKey: ["benchmarks", month],
    queryFn: () => fetchBenchmarks(accessToken!, month),
    enabled: !!accessToken,
    staleTime: 5 * 60_000,
  });
}
