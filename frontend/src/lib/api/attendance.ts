/**
 * API client for Attendance & Overtime endpoints.
 */

async function handleResponse<T>(res: Response): Promise<T> {
  if (!res.ok) {
    const error = await res.json().catch(() => ({ detail: { message: res.statusText } }));
    throw new Error(error.detail?.message || `Request failed: ${res.status}`);
  }
  return res.json();
}

// Types
export interface AttendanceRecord {
  id: string;
  employee_id: string;
  work_date: string;
  check_in: string | null;
  check_out: string | null;
  work_hours: number | null;
  overtime_hours: number;
  status: string;
  note: string | null;
  created_at: string;
  updated_at: string;
}

export interface MonthlyReport {
  employee_id: string;
  year: number;
  month: number;
  summary: {
    present_days: number;
    late_days: number;
    absent_days: number;
    leave_days: number;
    total_work_hours: number;
    total_overtime_hours: number;
  };
  records: AttendanceRecord[];
}

export interface OvertimeRequest {
  id: string;
  employee_id: string;
  work_date: string;
  planned_hours: number;
  actual_hours: number | null;
  reason: string;
  status: string;
  approved_by: string | null;
  created_at: string;
}

export interface OvertimeListResponse {
  items: OvertimeRequest[];
  total: number;
  page: number;
  page_size: number;
}

export interface WorkSchedule {
  id: string;
  name: string;
  start_time: string;
  end_time: string;
  break_minutes: number;
  late_threshold_minutes: number;
  early_leave_threshold_minutes: number;
  is_default: boolean;
}

export interface Holiday {
  id: string;
  holiday_date: string;
  name: string;
  is_recurring: boolean;
}

// Attendance API
export async function checkIn(employeeId: string, checkInTime?: string): Promise<AttendanceRecord> {
  const res = await fetch("/api/attendance/check-in", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ employee_id: employeeId, check_in_time: checkInTime }),
  });
  return handleResponse<AttendanceRecord>(res);
}

export async function checkOut(employeeId: string, checkOutTime?: string): Promise<AttendanceRecord> {
  const res = await fetch("/api/attendance/check-out", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ employee_id: employeeId, check_out_time: checkOutTime }),
  });
  return handleResponse<AttendanceRecord>(res);
}

export async function getToday(employeeId: string): Promise<AttendanceRecord | null> {
  const res = await fetch(`/api/attendance/today/${employeeId}`);
  if (res.status === 200) {
    const data = await res.json();
    return data;
  }
  return null;
}

export async function getMonthlyReport(
  employeeId: string,
  year: number,
  month: number
): Promise<MonthlyReport> {
  const res = await fetch(`/api/attendance/report/${employeeId}?year=${year}&month=${month}`);
  return handleResponse<MonthlyReport>(res);
}

export async function getTeamToday(workDate?: string): Promise<AttendanceRecord[]> {
  const url = workDate ? `/api/attendance/team?work_date=${workDate}` : "/api/attendance/team";
  const res = await fetch(url);
  return handleResponse<AttendanceRecord[]>(res);
}

export async function manualRecord(data: {
  employee_id: string;
  work_date: string;
  check_in?: string;
  check_out?: string;
  status: string;
  note?: string;
}): Promise<AttendanceRecord> {
  const res = await fetch("/api/attendance/manual", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
  return handleResponse<AttendanceRecord>(res);
}

// Overtime API
export async function createOvertimeRequest(data: {
  employee_id: string;
  work_date: string;
  planned_hours: number;
  reason: string;
}): Promise<OvertimeRequest> {
  const res = await fetch("/api/overtime/requests", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
  return handleResponse<OvertimeRequest>(res);
}

export async function listOvertimeRequests(params?: {
  status?: string;
  page?: number;
  page_size?: number;
}): Promise<OvertimeListResponse> {
  const searchParams = new URLSearchParams();
  if (params?.status) searchParams.set("status", params.status);
  if (params?.page) searchParams.set("page", String(params.page));
  if (params?.page_size) searchParams.set("page_size", String(params.page_size));

  const url = searchParams.toString()
    ? `/api/overtime/requests?${searchParams}`
    : "/api/overtime/requests";
  const res = await fetch(url);
  return handleResponse<OvertimeListResponse>(res);
}

export async function approveOvertime(requestId: string): Promise<OvertimeRequest> {
  const res = await fetch(`/api/overtime/requests/${requestId}/approve`, { method: "PUT" });
  return handleResponse<OvertimeRequest>(res);
}

export async function rejectOvertime(requestId: string): Promise<OvertimeRequest> {
  const res = await fetch(`/api/overtime/requests/${requestId}/reject`, { method: "PUT" });
  return handleResponse<OvertimeRequest>(res);
}

// Schedule & Holiday API
export async function listSchedules(): Promise<WorkSchedule[]> {
  const res = await fetch("/api/schedules");
  return handleResponse<WorkSchedule[]>(res);
}

export async function listHolidays(year?: number): Promise<Holiday[]> {
  const url = year ? `/api/holidays?year=${year}` : "/api/holidays";
  const res = await fetch(url);
  return handleResponse<Holiday[]>(res);
}

export async function createHoliday(data: {
  holiday_date: string;
  name: string;
  is_recurring?: boolean;
}): Promise<Holiday> {
  const res = await fetch("/api/holidays", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
  return handleResponse<Holiday>(res);
}

export async function deleteHoliday(holidayId: string): Promise<void> {
  const res = await fetch(`/api/holidays/${holidayId}`, { method: "DELETE" });
  if (!res.ok) throw new Error("Delete failed");
}
