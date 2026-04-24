import { useQuery } from "@tanstack/react-query";
import { fetchCohort } from "../api/cohort";
import { useAuth } from "../context/AuthContext";

export function useCohort(months = 12) {
  const { accessToken } = useAuth();
  return useQuery({
    queryKey: ["cohort", months],
    queryFn: () => fetchCohort(accessToken!, months),
    enabled: !!accessToken,
    staleTime: 5 * 60_000,
  });
}
