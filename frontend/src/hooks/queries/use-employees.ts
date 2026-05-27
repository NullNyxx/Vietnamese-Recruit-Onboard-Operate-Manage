"use client";

import { useQuery, useQueryClient } from "@tanstack/react-query";
import { employeesApi } from "@/lib/api";
import type { EmployeeListResponse, Employee } from "@/lib/api/types";

export const employeeKeys = {
  all: ["employees"] as const,
  lists: () => [...employeeKeys.all, "list"] as const,
  list: (params: Record<string, unknown>) =>
    [...employeeKeys.lists(), params] as const,
  details: () => [...employeeKeys.all, "detail"] as const,
  detail: (id: string) => [...employeeKeys.details(), id] as const,
};

interface UseEmployeesParams {
  page?: number;
  page_size?: number;
  search?: string;
  department_id?: string;
  position_id?: string;
  is_active?: boolean;
}

export function useEmployees(params: UseEmployeesParams = {}) {
  return useQuery<EmployeeListResponse>({
    queryKey: employeeKeys.list(params as Record<string, unknown>),
    queryFn: () => employeesApi.listEmployees(params),
    // List data is fresh for 30s
    staleTime: 30 * 1000,
    // Keep previous data while fetching new page (no flash)
    placeholderData: (previousData) => previousData,
  });
}

export function useEmployee(id: string) {
  return useQuery<Employee>({
    queryKey: employeeKeys.detail(id),
    queryFn: () => employeesApi.getEmployee(id),
    enabled: !!id,
    staleTime: 60 * 1000,
  });
}

/**
 * Prefetch employee list data — call on hover/focus of nav link
 */
export function usePrefetchEmployees() {
  const queryClient = useQueryClient();

  return (params: UseEmployeesParams = { page: 1, page_size: 20 }) => {
    queryClient.prefetchQuery({
      queryKey: employeeKeys.list(params as Record<string, unknown>),
      queryFn: () => employeesApi.listEmployees(params),
      staleTime: 30 * 1000,
    });
  };
}
