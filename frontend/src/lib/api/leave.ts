/**
 * API client for Leave Management endpoints.
 */

const BASE = "/api/leave";

async function handleResponse<T>(res: Response): Promise<T> {
  if (!res.ok) {
    const error = await res.json().catch(() => ({ detail: { message: res.statusText } }));
    throw new Error(error.detail?.message || `Request failed: ${res.status}`);
  }
  return res.json();
}

// Types
export interface LeaveType {
  id: string;
  name: string;
  display_name: string;
  default_days_per_year: number;
  is_paid: boolean;
  requires_approval: boolean;
  requires_document: boolean;
}

export interface LeaveBalance {
  id: string;
  employee_id: string;
  leave_type_id: string;
  year: number;
  total_days: number;
  used_days: number;
  remaining_days: number;
}

export interface LeaveRequest {
  id: string;
  employee_id: string;
  leave_type_id: string;
  start_date: string;
  end_date: string;
  total_days: number;
  reason: string | null;
  status: string;
  approved_by: string | null;
  approved_at: string | null;
  rejection_reason: string | null;
  created_at: string;
  updated_at: string;
}

export interface LeaveRequestListResponse {
  items: LeaveRequest[];
  total: number;
  page: number;
  page_size: number;
}

// API functions
export async function listLeaveTypes(): Promise<LeaveType[]> {
  const res = await fetch(`${BASE}/types`);
  return handleResponse<LeaveType[]>(res);
}

export async function getBalance(employeeId: string, year?: number): Promise<LeaveBalance[]> {
  const params = new URLSearchParams();
  if (year) params.set("year", String(year));
  const url = params.toString()
    ? `${BASE}/balance/${employeeId}?${params}`
    : `${BASE}/balance/${employeeId}`;
  const res = await fetch(url);
  return handleResponse<LeaveBalance[]>(res);
}

export async function initializeBalance(data: {
  employee_id: string;
  year: number;
  start_date?: string;
}): Promise<LeaveBalance[]> {
  const res = await fetch(`${BASE}/balance/initialize`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
  return handleResponse<LeaveBalance[]>(res);
}

export async function listRequests(params?: {
  employee_id?: string;
  status?: string;
  page?: number;
  page_size?: number;
}): Promise<LeaveRequestListResponse> {
  const searchParams = new URLSearchParams();
  if (params?.employee_id) searchParams.set("employee_id", params.employee_id);
  if (params?.status) searchParams.set("status", params.status);
  if (params?.page) searchParams.set("page", String(params.page));
  if (params?.page_size) searchParams.set("page_size", String(params.page_size));

  const url = searchParams.toString() ? `${BASE}/requests?${searchParams}` : `${BASE}/requests`;
  const res = await fetch(url);
  return handleResponse<LeaveRequestListResponse>(res);
}

export async function createRequest(data: {
  employee_id: string;
  leave_type_id: string;
  start_date: string;
  end_date: string;
  reason?: string;
}): Promise<LeaveRequest> {
  const res = await fetch(`${BASE}/requests`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
  return handleResponse<LeaveRequest>(res);
}

export async function approveRequest(requestId: string): Promise<LeaveRequest> {
  const res = await fetch(`${BASE}/requests/${requestId}/approve`, { method: "PUT" });
  return handleResponse<LeaveRequest>(res);
}

export async function rejectRequest(requestId: string, reason?: string): Promise<LeaveRequest> {
  const res = await fetch(`${BASE}/requests/${requestId}/reject`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ reason }),
  });
  return handleResponse<LeaveRequest>(res);
}

export async function cancelRequest(requestId: string): Promise<LeaveRequest> {
  const res = await fetch(`${BASE}/requests/${requestId}/cancel`, { method: "PUT" });
  return handleResponse<LeaveRequest>(res);
}
