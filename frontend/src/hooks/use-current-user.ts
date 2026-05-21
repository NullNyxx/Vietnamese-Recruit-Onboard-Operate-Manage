"use client";

import { useCallback, useEffect, useState } from "react";

export type UserRole = "admin" | "user";

export interface CurrentUser {
  id: string;
  email: string;
  name: string;
  avatar_url: string | null;
  role: UserRole;
  gmail_grant_valid: boolean;
  calendar_grant_valid: boolean;
  created_at: string;
  last_login: string;
}

interface UseCurrentUserResult {
  user: CurrentUser | null;
  loading: boolean;
  error: string | null;
  refetch: () => Promise<void>;
}

export function useCurrentUser(): UseCurrentUserResult {
  const [user, setUser] = useState<CurrentUser | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchUser = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const res = await fetch("/api/auth/me");
      if (!res.ok) {
        if (res.status === 401) {
          setUser(null);
          return;
        }
        throw new Error(`Failed to fetch user: ${res.status}`);
      }
      const data: CurrentUser = await res.json();
      setUser(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unknown error");
      setUser(null);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchUser();
  }, [fetchUser]);

  return { user, loading, error, refetch: fetchUser };
}
