import { useQuery } from "@tanstack/react-query";
import { fetchSegments } from "../api/segments";
import { useAuth } from "../context/AuthContext";

export function useSegments() {
  const { accessToken } = useAuth();
  return useQuery({
    queryKey: ["segments"],
    queryFn: () => fetchSegments(accessToken!),
    enabled: !!accessToken,
    staleTime: 5 * 60_000,
  });
}
