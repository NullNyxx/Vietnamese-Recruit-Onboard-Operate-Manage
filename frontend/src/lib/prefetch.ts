import { getQueryClient } from "./query-client";
import { employeesApi, departmentsApi, positionsApi } from "./api";

/**
 * Route-based data prefetching.
 * Called on hover/focus of navigation links to preload data
 * before the user actually navigates.
 */

const prefetchedRoutes = new Set<string>();

export function prefetchRouteData(href: string) {
  // Don't prefetch the same route twice within a session
  if (prefetchedRoutes.has(href)) return;
  prefetchedRoutes.add(href);

  // Clear after 60s to allow re-prefetch of stale data
  setTimeout(() => prefetchedRoutes.delete(href), 60 * 1000);

  const queryClient = getQueryClient();

  switch (true) {
    case href === "/":
      // Dashboard — prefetch stats
      queryClient.prefetchQuery({
        queryKey: ["dashboard", "stats"],
        queryFn: async () => {
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
        },
        staleTime: 60 * 1000,
      });
      break;

    case href === "/employees":
      // Employees list — prefetch first page + lookup data
      queryClient.prefetchQuery({
        queryKey: ["employees", "list", { page: 1, page_size: 20 }],
        queryFn: () => employeesApi.listEmployees({ page: 1, page_size: 20 }),
        staleTime: 30 * 1000,
      });
      queryClient.prefetchQuery({
        queryKey: ["departments", "list"],
        queryFn: departmentsApi.listDepartments,
        staleTime: 5 * 60 * 1000,
      });
      queryClient.prefetchQuery({
        queryKey: ["positions", "list"],
        queryFn: positionsApi.listPositions,
        staleTime: 5 * 60 * 1000,
      });
      break;

    case href.startsWith("/settings/departments"):
      queryClient.prefetchQuery({
        queryKey: ["departments", "list"],
        queryFn: departmentsApi.listDepartments,
        staleTime: 5 * 60 * 1000,
      });
      break;

    case href.startsWith("/settings/positions"):
      queryClient.prefetchQuery({
        queryKey: ["positions", "list"],
        queryFn: positionsApi.listPositions,
        staleTime: 5 * 60 * 1000,
      });
      break;

    // Gmail, Recruitment, Admin — no prefetch needed (or add as modules grow)
    default:
      break;
  }
}
