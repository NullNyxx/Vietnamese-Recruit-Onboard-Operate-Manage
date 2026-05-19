import type { Position, PositionCreateData } from "./types";

const BASE = "/api/positions";

async function handleResponse<T>(res: Response): Promise<T> {
  if (!res.ok) {
    const error = await res.json().catch(() => ({ error: { message: res.statusText } }));
    throw new Error(error.error?.message || `Request failed: ${res.status}`);
  }
  return res.json();
}

export async function listPositions(): Promise<Position[]> {
  const res = await fetch(BASE);
  return handleResponse<Position[]>(res);
}

export async function createPosition(data: PositionCreateData): Promise<Position> {
  const res = await fetch(BASE, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
  return handleResponse<Position>(res);
}

export async function updatePosition(id: string, data: Partial<PositionCreateData>): Promise<Position> {
  const res = await fetch(`${BASE}/${id}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
  return handleResponse<Position>(res);
}

export async function deletePosition(id: string): Promise<void> {
  const res = await fetch(`${BASE}/${id}`, { method: "DELETE" });
  if (!res.ok) {
    const error = await res.json().catch(() => ({ error: { message: "Delete failed" } }));
    throw new Error(error.error?.message || "Delete failed");
  }
}
