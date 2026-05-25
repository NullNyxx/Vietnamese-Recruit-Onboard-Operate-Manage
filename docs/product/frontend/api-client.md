# Frontend API Client

## Overview

The frontend communicates with the backend FastAPI server via REST API. All API calls are made from client components using the API client functions defined in `src/lib/api/`.

## API Base URL

| Environment | URL                       |
| ----------- | ------------------------- |
| Development | `http://localhost:8000`   |
| Production  | `https://api.vroomhr.com` |

All API endpoints are prefixed with `/api/v1/`:

```
GET    /api/v1/employees
POST   /api/v1/employees
GET    /api/v1/employees/{id}
PUT    /api/v1/employees/{id}
DELETE /api/v1/employees/{id}
```

## API Client Structure

### File Organization

```
src/lib/api/
├── index.ts        # Re-exports all API modules
├── types.ts        # Shared TypeScript interfaces
├── admin.ts        # Admin endpoints
├── attendance.ts   # Attendance endpoints
├── departments.ts  # Department endpoints
├── employees.ts    # Employee endpoints
├── ess.ts          # Employee Self-Service endpoints
├── gmail.ts        # Gmail endpoints
├── leave.ts        # Leave endpoints
├── payroll.ts      # Payroll endpoints
├── positions.ts    # Position endpoints
└── recruitment.ts  # Recruitment endpoints
```

### Response Handling Pattern

Each API file follows the same response handling pattern:

```typescript
// Basic response handler
async function handleResponse<T>(res: Response): Promise<T> {
  if (!res.ok) {
    const error = await res
      .json()
      .catch(() => ({ detail: { message: res.statusText } }));
    throw new Error(error.detail?.message || `Request failed: ${res.status}`);
  }
  return res.json();
}

// Handler with status code (for 409 conflict handling)
async function handleResponseWithStatus<T>(
  res: Response,
): Promise<{ data: T; status: number }> {
  if (!res.ok) {
    const error = await res
      .json()
      .catch(() => ({ detail: { message: res.statusText, code: "" } }));
    const err = new Error(
      error.detail?.message || `Request failed: ${res.status}`,
    ) as Error & { statusCode: number; errorCode: string };
    err.statusCode = res.status;
    err.errorCode = error.detail?.code || "";
    throw err;
  }
  const data = await res.json();
  return { data, status: res.status };
}
```

## API Modules

### Employees API

**File:** `src/lib/api/employees.ts`

```typescript
import { handleResponse, handleResponseWithStatus } from "./index";

export interface Employee {
  id: string;
  email: string;
  full_name: string;
  phone_number?: string;
  department_id: string;
  department_name?: string;
  position_id: string;
  position_name?: string;
  hire_date: string;
  is_active: boolean;
  created_at?: string;
  updated_at?: string;
}

export interface CreateEmployeeData {
  email: string;
  full_name: string;
  phone_number?: string;
  department_id: string;
  position_id: string;
  hire_date: string;
}

export interface UpdateEmployeeData extends Partial<CreateEmployeeData> {
  is_active?: boolean;
}

// List all employees
export async function getEmployees(): Promise<Employee[]> {
  const res = await fetch("/api/v1/employees");
  return handleResponse<Employee[]>(res);
}

// Get employee by ID
export async function getEmployee(id: string): Promise<Employee> {
  const res = await fetch(`/api/v1/employees/${id}`);
  return handleResponse<Employee>(res);
}

// Create new employee
export async function createEmployee(
  data: CreateEmployeeData,
): Promise<Employee> {
  const res = await fetch("/api/v1/employees", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
  return handleResponse<Employee>(res);
}

// Update employee
export async function updateEmployee(
  id: string,
  data: UpdateEmployeeData,
): Promise<Employee> {
  const res = await fetch(`/api/v1/employees/${id}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
  return handleResponse<Employee>(res);
}

// Delete (soft) employee
export async function deleteEmployee(id: string): Promise<void> {
  const res = await fetch(`/api/v1/employees/${id}`, {
    method: "DELETE",
  });
  return handleResponse<void>(res);
}
```

### ESS API (Employee Self-Service)

**File:** `src/lib/api/ess.ts`

```typescript
// Dashboard data
export interface DashboardData {
  today_attendance: AttendanceStatus;
  pending_leave_count: number;
  pending_overtime_count: number;
  monthly_summary: MonthlySummary;
  annual_leave_remaining: number | null;
}

export async function getDashboard(): Promise<DashboardData> {
  const res = await fetch("/api/v1/ess/dashboard");
  return handleResponse<DashboardData>(res);
}

// Check-in
export async function checkIn(): Promise<CheckInOutResponse> {
  const res = await fetch("/api/v1/ess/attendance/check-in", {
    method: "POST",
  });
  const { data } = await handleResponseWithStatus<CheckInOutResponse>(res);
  return data;
}

// Check-out
export async function checkOut(): Promise<CheckInOutResponse> {
  const res = await fetch("/api/v1/ess/attendance/check-out", {
    method: "POST",
  });
  const { data } = await handleResponseWithStatus<CheckInOutResponse>(res);
  return data;
}

// Leave balance
export async function getLeaveBalances(): Promise<LeaveBalance[]> {
  const res = await fetch("/api/v1/ess/leave/balances");
  return handleResponse<LeaveBalance[]>(res);
}

// Leave requests
export async function getLeaveRequests(): Promise<LeaveRequestResponse[]> {
  const res = await fetch("/api/v1/ess/leave/requests");
  return handleResponse<LeaveRequestResponse[]>(res);
}

export async function createLeaveRequest(
  data: CreateLeaveRequestPayload,
): Promise<LeaveRequestResponse> {
  const res = await fetch("/api/v1/ess/leave/requests", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
  const { data: result } =
    await handleResponseWithStatus<LeaveRequestResponse>(res);
  return result;
}

// Overtime requests
export async function getOvertimeRequests(): Promise<
  OvertimeRequestResponse[]
> {
  const res = await fetch("/api/v1/ess/overtime/requests");
  return handleResponse<OvertimeRequestResponse[]>(res);
}

export async function createOvertimeRequest(
  data: CreateOvertimeRequestData,
): Promise<OvertimeRequestResponse> {
  const res = await fetch("/api/v1/ess/overtime/requests", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
  return handleResponse<OvertimeRequestResponse>(res);
}
```

### Attendance API (Admin)

**File:** `src/lib/api/attendance.ts`

```typescript
// Get all attendance records
export async function getAttendanceRecords(params?: {
  start_date?: string;
  end_date?: string;
  employee_id?: string;
}): Promise<AttendanceRecord[]> {
  const query = new URLSearchParams();
  if (params?.start_date) query.set("start_date", params.start_date);
  if (params?.end_date) query.set("end_date", params.end_date);
  if (params?.employee_id) query.set("employee_id", params.employee_id);

  const url = `/api/v1/attendance/records${query.toString() ? `?${query}` : ""}`;
  const res = await fetch(url);
  return handleResponse<AttendanceRecord[]>(res);
}

// Manual check-in
export async function manualCheckIn(
  employeeId: string,
): Promise<AttendanceRecord> {
  const res = await fetch(
    `/api/v1/attendance/employees/${employeeId}/check-in`,
    {
      method: "POST",
    },
  );
  return handleResponse<AttendanceRecord>(res);
}
```

### Leave API (Admin)

**File:** `src/lib/api/leave.ts`

```typescript
// Get all leave requests
export async function getLeaveRequestsAdmin(params?: {
  status?: "pending" | "approved" | "rejected";
  employee_id?: string;
}): Promise<LeaveRequestResponse[]> {
  const query = new URLSearchParams();
  if (params?.status) query.set("status", params.status);
  if (params?.employee_id) query.set("employee_id", params.employee_id);

  const url = `/api/v1/leave/requests${query.toString() ? `?${query}` : ""}`;
  const res = await fetch(url);
  return handleResponse<LeaveRequestResponse[]>(res);
}

// Approve leave request
export async function approveLeaveRequest(
  id: string,
  data?: { review_note?: string },
): Promise<LeaveRequestResponse> {
  const res = await fetch(`/api/v1/leave/requests/${id}/approve`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data || {}),
  });
  return handleResponse<LeaveRequestResponse>(res);
}

// Reject leave request
export async function rejectLeaveRequest(
  id: string,
  data: { review_note: string },
): Promise<LeaveRequestResponse> {
  const res = await fetch(`/api/v1/leave/requests/${id}/reject`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
  return handleResponse<LeaveRequestResponse>(res);
}
```

### Departments & Positions API

**File:** `src/lib/api/departments.ts`

```typescript
export interface Department {
  id: string;
  name: string;
  description?: string;
  is_active: boolean;
  created_at: string;
}

export async function getDepartments(): Promise<Department[]> {
  const res = await fetch("/api/v1/departments");
  return handleResponse<Department[]>(res);
}

export async function createDepartment(
  data: CreateDepartmentData,
): Promise<Department> {
  const res = await fetch("/api/v1/departments", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
  return handleResponse<Department>(res);
}
```

## Error Handling

### Basic Error Handling

```typescript
import { toast } from "sonner";

async function loadEmployees() {
  try {
    const employees = await getEmployees();
    setEmployees(employees);
  } catch (error) {
    toast.error("Failed to load employees");
    console.error(error);
  }
}
```

### Handling Specific Error Codes

```typescript
import { toast } from "sonner";

async function handleCheckIn() {
  try {
    await checkIn();
    toast.success("Checked in successfully");
    await refreshAttendance();
  } catch (error) {
    const err = error as Error & { statusCode?: number; errorCode?: string };

    if (err.statusCode === 409) {
      // Already checked in or out
      toast.error(err.message);
    } else if (err.statusCode === 422) {
      // Validation error
      toast.error("Cannot check in: " + err.message);
    } else {
      toast.error("Failed to check in");
    }
  }
}
```

### Common Error Codes

| Code                  | HTTP Status | Meaning            | Handling                 |
| --------------------- | ----------- | ------------------ | ------------------------ |
| `UNAUTHORIZED`        | 401         | Not logged in      | Redirect to login        |
| `FORBIDDEN`           | 403         | No permission      | Show error message       |
| `NOT_FOUND`           | 404         | Resource not found | Show "not found" message |
| `VALIDATION_ERROR`    | 422         | Invalid data       | Show validation errors   |
| `RATE_LIMIT_EXCEEDED` | 429         | Too many requests  | Show retry message       |
| `INTERNAL_ERROR`      | 500         | Server error       | Show generic error       |

### API Error Type

```typescript
interface ApiError extends Error {
  statusCode?: number;
  errorCode?: string;
}

// Check for specific error
if (error instanceof Error) {
  const apiError = error as ApiError;
  if (apiError.statusCode === 409) {
    // Handle conflict
  }
}
```

## Authentication

### How Auth Works

1. User logs in via Google OAuth at `/login`
2. Backend sets HTTP-only cookies: `access_token`, `refresh_token`
3. All subsequent requests include cookies automatically
4. Frontend checks cookies via middleware for route protection

### Protected Routes

Routes are protected by `src/middleware.ts`:

```typescript
// If no token, redirect to login
if (!token) {
  return Response.redirect(new URL("/login", request.url));
}
```

### Getting Current User

```typescript
import { useCurrentUser } from "@/hooks/use-current-user";

function Component() {
  const { user, isLoading } = useCurrentUser();

  if (isLoading) return <Skeleton />;

  return <div>Welcome, {user?.full_name}</div>;
}
```

## Using API in Components

### Fetching Data with useEffect

```typescript
"use client";

import { useEffect, useState } from "react";
import { getEmployees, type Employee } from "@/lib/api/employees";

export function EmployeeList() {
  const [employees, setEmployees] = useState<Employee[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function load() {
      try {
        const data = await getEmployees();
        setEmployees(data);
      } catch (error) {
        console.error(error);
      } finally {
        setLoading(false);
      }
    }
    load();
  }, []);

  if (loading) return <div>Loading...</div>;

  return (
    <ul>
      {employees.map((emp) => (
        <li key={emp.id}>{emp.full_name}</li>
      ))}
    </ul>
  );
}
```

### Optimistic Updates

```typescript
async function handleApprove(id: string) {
  // Optimistic update
  setRequests((prev) =>
    prev.map((r) => (r.id === id ? { ...r, status: "approved" } : r)),
  );

  try {
    await approveRequest(id);
    toast.success("Approved");
  } catch (error) {
    // Revert on error
    setRequests((prev) =>
      prev.map((r) => (r.id === id ? { ...r, status: "pending" } : r)),
    );
    toast.error("Failed to approve");
  }
}
```

### Refetching After Mutation

```typescript
import { useRouter } from "next/navigation";

async function handleCreate(data: CreateEmployeeData) {
  await createEmployee(data);
  toast.success("Employee created");
  router.refresh(); // Refresh server components
  router.push("/employees"); // Navigate to list
}
```

## API Endpoints Summary

### Employees

| Method | Endpoint                 | Description          |
| ------ | ------------------------ | -------------------- |
| GET    | `/api/v1/employees`      | List employees       |
| POST   | `/api/v1/employees`      | Create employee      |
| GET    | `/api/v1/employees/{id}` | Get employee         |
| PUT    | `/api/v1/employees/{id}` | Update employee      |
| DELETE | `/api/v1/employees/{id}` | Soft delete employee |

### ESS (Employee Self-Service)

| Method | Endpoint                           | Description           |
| ------ | ---------------------------------- | --------------------- |
| GET    | `/api/v1/ess/dashboard`            | Get dashboard data    |
| POST   | `/api/v1/ess/attendance/check-in`  | Check in              |
| POST   | `/api/v1/ess/attendance/check-out` | Check out             |
| GET    | `/api/v1/ess/leave/balances`       | Get leave balances    |
| GET    | `/api/v1/ess/leave/requests`       | Get my leave requests |
| POST   | `/api/v1/ess/leave/requests`       | Create leave request  |

### Admin - Leave

| Method | Endpoint                              | Description       |
| ------ | ------------------------------------- | ----------------- |
| GET    | `/api/v1/leave/requests`              | List all requests |
| POST   | `/api/v1/leave/requests/{id}/approve` | Approve           |
| POST   | `/api/v1/leave/requests/{id}/reject`  | Reject            |

### Departments & Positions

| Method | Endpoint              | Description       |
| ------ | --------------------- | ----------------- |
| GET    | `/api/v1/departments` | List departments  |
| POST   | `/api/v1/departments` | Create department |
| GET    | `/api/v1/positions`   | List positions    |
| POST   | `/api/v1/positions`   | Create position   |

## Best Practices

### 1. Always handle errors

```typescript
// ❌ Bad
const data = await fetchData();

// ✅ Good
try {
  const data = await fetchData();
} catch (error) {
  toast.error("Failed to load data");
}
```

### 2. Show loading states

```typescript
const [loading, setLoading] = useState(true);
useEffect(() => {
  loadData().finally(() => setLoading(false));
}, []);

if (loading) return <Skeleton />;
```

### 3. Use proper TypeScript types

```typescript
// ❌ Bad
const [data, setData] = useState(null);

// ✅ Good
const [employees, setEmployees] = useState<Employee[]>([]);
```

### 4. Clean up on unmount

```typescript
useEffect(() => {
  let cancelled = false;

  async function load() {
    const data = await fetchData();
    if (!cancelled) setData(data);
  }
  load();

  return () => {
    cancelled = true;
  };
}, []);
```

### 5. Use toast for user feedback

```typescript
toast.success("Saved successfully");
toast.error("Failed to save");
toast.warning("Please complete all fields");
```
