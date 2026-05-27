import { QueryClient } from "@tanstack/react-query";

/**
 * Shared QueryClient instance with aggressive caching defaults
 * for instant navigation between modules.
 *
 * Strategy: stale-while-revalidate
 * - Show cached data immediately (instant navigation)
 * - Refetch in background when stale
 * - Keep unused data in cache for 10 minutes
 */
export function createQueryClient() {
  return new QueryClient({
    defaultOptions: {
      queries: {
        // Data is fresh for 30 seconds — no refetch during this window
        staleTime: 30 * 1000,
        // Keep unused cache entries for 10 minutes
        gcTime: 10 * 60 * 1000,
        // Show stale data while refetching (instant navigation)
        refetchOnWindowFocus: false,
        // Don't retry on 4xx errors
        retry: (failureCount, error) => {
          if (error instanceof Error && error.message.includes("401"))
            return false;
          if (error instanceof Error && error.message.includes("403"))
            return false;
          if (error instanceof Error && error.message.includes("404"))
            return false;
          return failureCount < 2;
        },
        retryDelay: (attemptIndex) => Math.min(1000 * 2 ** attemptIndex, 10000),
      },
    },
  });
}

// Singleton for client-side usage
let browserQueryClient: QueryClient | undefined;

export function getQueryClient() {
  if (typeof window === "undefined") {
    // Server: always create a new client
    return createQueryClient();
  }
  // Browser: reuse singleton
  if (!browserQueryClient) {
    browserQueryClient = createQueryClient();
  }
  return browserQueryClient;
}
