import type {
  Employee,
  EmployeeListResponse,
  EmployeeCreateData,
  EmployeeUpdateData,
  EmployeeDocument,
  ImportResult,
} from "./types";

const BASE = "/api/employees";

async function handleResponse<T>(res: Response): Promise<T> {
  if (!res.ok) {
    const error = await res.json().catch(() => ({ error: { message: res.statusText } }));
    throw new Error(error.error?.message || `Request failed: ${res.status}`);
  }
  return res.json();
}

export async function listEmployees(params?: {
  page?: number;
  page_size?: number;
  search?: string;
  department_id?: string;
  position_id?: string;
  is_active?: boolean;
}): Promise<EmployeeListResponse> {
  const searchParams = new URLSearchParams();
  if (params?.page) searchParams.set("page", String(params.page));
  if (params?.page_size) searchParams.set("page_size", String(params.page_size));
  if (params?.search) searchParams.set("search", params.search);
  if (params?.department_id) searchParams.set("department_id", params.department_id);
  if (params?.position_id) searchParams.set("position_id", params.position_id);
  if (params?.is_active !== undefined) searchParams.set("is_active", String(params.is_active));

  const url = searchParams.toString() ? `${BASE}?${searchParams}` : BASE;
  const res = await fetch(url);
  return handleResponse<EmployeeListResponse>(res);
}

export async function getEmployee(id: string): Promise<Employee> {
  const res = await fetch(`${BASE}/${id}`);
  return handleResponse<Employee>(res);
}

export async function createEmployee(data: EmployeeCreateData): Promise<Employee> {
  const res = await fetch(BASE, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
  return handleResponse<Employee>(res);
}

export async function updateEmployee(id: string, data: EmployeeUpdateData): Promise<Employee> {
  const res = await fetch(`${BASE}/${id}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
  return handleResponse<Employee>(res);
}

export async function deleteEmployee(id: string): Promise<Employee> {
  const res = await fetch(`${BASE}/${id}`, { method: "DELETE" });
  return handleResponse<Employee>(res);
}

export async function importEmployees(file: File): Promise<ImportResult> {
  const formData = new FormData();
  formData.append("file", file);
  const res = await fetch(`${BASE}/import`, {
    method: "POST",
    body: formData,
  });
  return handleResponse<ImportResult>(res);
}

export async function listDocuments(employeeId: string): Promise<EmployeeDocument[]> {
  const res = await fetch(`${BASE}/${employeeId}/documents`);
  return handleResponse<EmployeeDocument[]>(res);
}

export async function uploadDocument(
  employeeId: string,
  file: File,
  documentType: string,
  description?: string
): Promise<EmployeeDocument> {
  const formData = new FormData();
  formData.append("file", file);
  formData.append("document_type", documentType);
  if (description) formData.append("description", description);
  const res = await fetch(`${BASE}/${employeeId}/documents`, {
    method: "POST",
    body: formData,
  });
  return handleResponse<EmployeeDocument>(res);
}

export async function downloadDocument(documentId: string): Promise<Blob> {
  const res = await fetch(`/api/documents/${documentId}/download`);
  if (!res.ok) throw new Error("Download failed");
  return res.blob();
}

export async function deleteDocument(documentId: string): Promise<void> {
  const res = await fetch(`/api/documents/${documentId}`, { method: "DELETE" });
  if (!res.ok) {
    const error = await res.json().catch(() => ({ error: { message: "Delete failed" } }));
    throw new Error(error.error?.message || "Delete failed");
  }
}
