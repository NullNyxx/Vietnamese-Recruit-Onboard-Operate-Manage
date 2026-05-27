"use client";

import { useQuery, useQueryClient } from "@tanstack/react-query";

export type UserRole = "admin" | "user";

export interface CurrentUser {
  id: string;
  email: string;
  name: string;
  avatar_url: string | null;
  employee_id?: string | null;
  role: UserRole;
  gmail_grant_valid: boolean;
  calendar_grant_valid: boolean;
  created_at: string;
  last_login: string;
}

export const currentUserQueryKey = ["current-user"] as const;

async function fetchCurrentUser(): Promise<CurrentUser | null> {
  const res = await fetch("/api/auth/me");
  if (!res.ok) {
    if (res.status === 401) return null;
    throw new Error(`Failed to fetch user: ${res.status}`);
  }
  return res.json();
}

/**
 * Cached current user hook — fetches once, shares across all components.
 * No more re-fetching on every navigation.
 */
export function useCurrentUser() {
  const queryClient = useQueryClient();

  const {
    data: user,
    isLoading: loading,
    error,
  } = useQuery({
    queryKey: currentUserQueryKey,
    queryFn: fetchCurrentUser,
    // User data is stable — keep fresh for 5 minutes
    staleTime: 5 * 60 * 1000,
    gcTime: 30 * 60 * 1000,
    // Don't refetch on every window focus
    refetchOnWindowFocus: false,
    refetchOnMount: false,
  });

  const refetch = async () => {
    await queryClient.invalidateQueries({ queryKey: currentUserQueryKey });
  };

  return {
    user: user ?? null,
    loading,
    error: error?.message ?? null,
    refetch,
  };
}
