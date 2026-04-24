import { useQuery } from "@tanstack/react-query";
import { fetchAvailablePlans } from "../api/plans";
import { useAuth } from "../context/AuthContext";

export function usePlanList() {
  const { accessToken } = useAuth();
  return useQuery({
    queryKey: ["available-plans"],
    queryFn: () => fetchAvailablePlans(accessToken!),
    enabled: !!accessToken,
    staleTime: 5 * 60_000,
  });
}
