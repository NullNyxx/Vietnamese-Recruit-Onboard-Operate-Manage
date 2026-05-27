"use client";

import { useQuery, useQueryClient } from "@tanstack/react-query";
import { departmentsApi } from "@/lib/api";
import type { Department } from "@/lib/api/types";

export const departmentKeys = {
  all: ["departments"] as const,
  list: () => [...departmentKeys.all, "list"] as const,
};

export function useDepartments() {
  return useQuery<Department[]>({
    queryKey: departmentKeys.list(),
    queryFn: departmentsApi.listDepartments,
    // Departments rarely change — keep fresh for 5 minutes
    staleTime: 5 * 60 * 1000,
    gcTime: 30 * 60 * 1000,
  });
}

export function usePrefetchDepartments() {
  const queryClient = useQueryClient();

  return () => {
    queryClient.prefetchQuery({
      queryKey: departmentKeys.list(),
      queryFn: departmentsApi.listDepartments,
      staleTime: 5 * 60 * 1000,
    });
  };
}
