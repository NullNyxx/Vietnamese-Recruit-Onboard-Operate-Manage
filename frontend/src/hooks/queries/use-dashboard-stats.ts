"use client";

import { useQuery } from "@tanstack/react-query";
import { employeesApi, departmentsApi, positionsApi } from "@/lib/api";

export interface DashboardStats {
  employees: number;
  departments: number;
  positions: number;
  activeToday: number;
}

export const dashboardKeys = {
  stats: ["dashboard", "stats"] as const,
};

async function fetchDashboardStats(): Promise<DashboardStats> {
  const [employeesRes, departments, positions] = await Promise.all([
    employeesApi.listEmployees({ page: 1, page_size: 1 }),
    departmentsApi.listDepartments(),
    positionsApi.listPositions(),
  ]);

  return {
    employees: employeesRes.total,
    departments: departments.length,
    positions: positions.length,
    activeToday: 0,
  };
}

export function useDashboardStats() {
  return useQuery<DashboardStats>({
    queryKey: dashboardKeys.stats,
    queryFn: fetchDashboardStats,
    staleTime: 60 * 1000, // Fresh for 1 minute
    gcTime: 10 * 60 * 1000,
  });
}
