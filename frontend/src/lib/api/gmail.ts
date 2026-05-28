import type {
  ConnectionStatusResponse,
  ConnectResponse,
  SyncResponse,
  MessageBodyResponse,
  SendEmailRequest,
  SendEmailResponse,
  AttachmentsResponse,
} from "./types";
import { ApiError } from "./types";

const BASE = "/api/gmail";

async function handleResponse<T>(res: Response): Promise<T> {
  if (!res.ok) {
    const body = await res.json().catch(() => ({
      detail: res.statusText,
    }));
    const message =
      body?.detail || body?.error?.message || `Request failed: ${res.status}`;
    const errorCode = body?.error_code || "UNKNOWN_ERROR";
    throw new ApiError(res.status, errorCode, message, body);
  }
  return res.json();
}

export async function getStatus(): Promise<ConnectionStatusResponse> {
  const res = await fetch(`${BASE}/status`);
  return handleResponse<ConnectionStatusResponse>(res);
}

export async function connect(): Promise<ConnectResponse> {
  const res = await fetch(`${BASE}/connect`, {
    method: "POST",
  });
  return handleResponse<ConnectResponse>(res);
}

export async function disconnect(): Promise<ConnectionStatusResponse> {
  const res = await fetch(`${BASE}/disconnect`, {
    method: "POST",
  });
  return handleResponse<ConnectionStatusResponse>(res);
}

export async function syncEmails(): Promise<SyncResponse> {
  const res = await fetch(`${BASE}/sync`, {
    method: "POST",
  });
  return handleResponse<SyncResponse>(res);
}

export async function getMessageBody(
  messageId: string,
): Promise<MessageBodyResponse> {
  const res = await fetch(`${BASE}/messages/${messageId}/body`);
  return handleResponse<MessageBodyResponse>(res);
}

export async function removeLabel(
  messageId: string,
  labelName: string,
): Promise<void> {
  const res = await fetch(`${BASE}/messages/${messageId}/labels/remove`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ label_name: labelName }),
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({
      detail: res.statusText,
    }));
    const message =
      body?.detail || body?.error?.message || `Request failed: ${res.status}`;
    const errorCode = body?.error_code || "UNKNOWN_ERROR";
    throw new ApiError(res.status, errorCode, message, body);
  }
}

export async function sendEmail(
  data: SendEmailRequest,
): Promise<SendEmailResponse> {
  const res = await fetch(`${BASE}/send`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
  return handleResponse<SendEmailResponse>(res);
}

export async function getAttachments(
  messageId: string,
): Promise<AttachmentsResponse> {
  const res = await fetch(`${BASE}/messages/${messageId}/attachments`, {
    method: "POST",
  });
  return handleResponse<AttachmentsResponse>(res);
}

export interface ClassifyResponse {
  classified_count: number;
  total: number;
  remaining: number;
  message: string;
  results: Array<{ subject: string; category: string | null }>;
}

/**
 * Classify a small batch of emails (default 5).
 * Call repeatedly from FE to process all emails with progress.
 */
export async function classifyBatch(
  limit: number = 5,
): Promise<ClassifyResponse> {
  const res = await fetch(`${BASE}/classify?limit=${limit}`, {
    method: "POST",
  });
  return handleResponse<ClassifyResponse>(res);
}
