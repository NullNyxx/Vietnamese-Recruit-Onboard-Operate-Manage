/**
 * Admin API client — typed functions for all admin endpoints.
 *
 * Follows the same fetch + handleResponse pattern used by the existing
 * employees/departments/positions API modules.
 */

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export type WhitelistEntryType = "exact_email" | "domain_pattern";

export interface WhitelistEntry {
  id: string | null;
  value: string;
  entry_type: WhitelistEntryType;
  added_by_email: string;
  created_at: string | null;
  source: "database" | "file";
  is_readonly: boolean;
}

export interface WhitelistListResponse {
  items: WhitelistEntry[];
  total: number;
}

export interface WhitelistEntryCreated {
  id: string;
  value: string;
  entry_type: WhitelistEntryType;
  created_at: string;
}

export interface OAuthConfig {
  client_id: string;
  client_secret_masked: string;
  redirect_uri: string;
  updated_at: string | null;
  source: string;
}

export type UserRole = "admin" | "user";

export interface AdminUser {
  id: string;
  email: string;
  name: string;
  avatar_url: string | null;
  role: UserRole;
  is_active: boolean;
  created_at: string;
  last_login: string;
}

export type AuditActionType =
  | "whitelist_add"
  | "whitelist_remove"
  | "oauth_update"
  | "role_change";

export interface AuditLog {
  id: string;
  admin_email: string;
  action_type: AuditActionType;
  details: Record<string, unknown>;
  created_at: string;
}

export interface PaginatedAuditLogs {
  items: AuditLog[];
  total: number;
  page: number;
  page_size: number;
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

const BASE = "/api/admin";

async function handleResponse<T>(res: Response): Promise<T> {
  if (!res.ok) {
    const error = await res.json().catch(() => ({ detail: { message: res.statusText } }));
    const message =
      error?.detail?.message ?? error?.detail ?? `Request failed: ${res.status}`;
    throw new Error(typeof message === "string" ? message : JSON.stringify(message));
  }
  return res.json();
}

// ---------------------------------------------------------------------------
// Whitelist Endpoints
// ---------------------------------------------------------------------------

export async function listWhitelist(): Promise<WhitelistListResponse> {
  const res = await fetch(`${BASE}/whitelist`);
  return handleResponse<WhitelistListResponse>(res);
}

export async function addWhitelistEntry(value: string): Promise<WhitelistEntryCreated> {
  const res = await fetch(`${BASE}/whitelist`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ value }),
  });
  return handleResponse<WhitelistEntryCreated>(res);
}

export async function removeWhitelistEntry(id: string): Promise<void> {
  const res = await fetch(`${BASE}/whitelist/${id}`, { method: "DELETE" });
  if (!res.ok && res.status !== 204) {
    const error = await res.json().catch(() => ({ detail: { message: "Delete failed" } }));
    const message =
      error?.detail?.message ?? error?.detail ?? "Delete failed";
    throw new Error(typeof message === "string" ? message : JSON.stringify(message));
  }
}

// ---------------------------------------------------------------------------
// OAuth Config Endpoints
// ---------------------------------------------------------------------------

export async function getOAuthConfig(): Promise<OAuthConfig> {
  const res = await fetch(`${BASE}/oauth/config`);
  return handleResponse<OAuthConfig>(res);
}

export async function updateOAuthConfig(data: {
  client_id: string;
  client_secret: string;
  redirect_uri: string;
}): Promise<OAuthConfig> {
  const res = await fetch(`${BASE}/oauth/config`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
  return handleResponse<OAuthConfig>(res);
}

// ---------------------------------------------------------------------------
// User Management Endpoints
// ---------------------------------------------------------------------------

export async function listUsers(): Promise<AdminUser[]> {
  const res = await fetch(`${BASE}/users`);
  return handleResponse<AdminUser[]>(res);
}

export async function updateUserRole(
  userId: string,
  role: UserRole
): Promise<AdminUser> {
  const res = await fetch(`${BASE}/users/${userId}/role`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ role }),
  });
  return handleResponse<AdminUser>(res);
}

// ---------------------------------------------------------------------------
// Audit Log Endpoints
// ---------------------------------------------------------------------------

export interface AuditLogQueryParams {
  page?: number;
  page_size?: number;
  action_type?: string;
  start_date?: string;
  end_date?: string;
}

export async function getAuditLogs(
  params?: AuditLogQueryParams
): Promise<PaginatedAuditLogs> {
  const searchParams = new URLSearchParams();
  if (params?.page) searchParams.set("page", String(params.page));
  if (params?.page_size) searchParams.set("page_size", String(params.page_size));
  if (params?.action_type) searchParams.set("action_type", params.action_type);
  if (params?.start_date) searchParams.set("start_date", params.start_date);
  if (params?.end_date) searchParams.set("end_date", params.end_date);

  const url = searchParams.toString()
    ? `${BASE}/audit-logs?${searchParams}`
    : `${BASE}/audit-logs`;
  const res = await fetch(url);
  return handleResponse<PaginatedAuditLogs>(res);
}
