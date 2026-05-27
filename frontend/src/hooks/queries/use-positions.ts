"use client";

import { useQuery, useQueryClient } from "@tanstack/react-query";
import { positionsApi } from "@/lib/api";
import type { Position } from "@/lib/api/types";

export const positionKeys = {
  all: ["positions"] as const,
  list: () => [...positionKeys.all, "list"] as const,
};

export function usePositions() {
  return useQuery<Position[]>({
    queryKey: positionKeys.list(),
    queryFn: positionsApi.listPositions,
    // Positions rarely change — keep fresh for 5 minutes
    staleTime: 5 * 60 * 1000,
    gcTime: 30 * 60 * 1000,
  });
}

export function usePrefetchPositions() {
  const queryClient = useQueryClient();

  return () => {
    queryClient.prefetchQuery({
      queryKey: positionKeys.list(),
      queryFn: positionsApi.listPositions,
      staleTime: 5 * 60 * 1000,
    });
  };
}
