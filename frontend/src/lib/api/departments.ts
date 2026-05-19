import type { Department, DepartmentCreateData } from "./types";

const BASE = "/api/departments";

async function handleResponse<T>(res: Response): Promise<T> {
  if (!res.ok) {
    const error = await res.json().catch(() => ({ error: { message: res.statusText } }));
    throw new Error(error.error?.message || `Request failed: ${res.status}`);
  }
  return res.json();
}

export async function listDepartments(): Promise<Department[]> {
  const res = await fetch(BASE);
  return handleResponse<Department[]>(res);
}

export async function createDepartment(data: DepartmentCreateData): Promise<Department> {
  const res = await fetch(BASE, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
  return handleResponse<Department>(res);
}

export async function updateDepartment(id: string, data: Partial<DepartmentCreateData>): Promise<Department> {
  const res = await fetch(`${BASE}/${id}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
  return handleResponse<Department>(res);
}

export async function deleteDepartment(id: string): Promise<void> {
  const res = await fetch(`${BASE}/${id}`, { method: "DELETE" });
  if (!res.ok) {
    const error = await res.json().catch(() => ({ error: { message: "Delete failed" } }));
    throw new Error(error.error?.message || "Delete failed");
  }
}
