import { ApiError } from "./types";

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

const BASE = "/api/recruitment";
const TIMEOUT_MS = 30_000;

// ---------------------------------------------------------------------------
// Enums / Type Aliases
// ---------------------------------------------------------------------------

export type CandidateStatus =
  | "new"
  | "reviewing"
  | "interview_scheduled"
  | "accepted"
  | "rejected"
  | "archived";

export type ProcessingStatus =
  | "pending"
  | "ocr_processing"
  | "llm_parsing"
  | "completed"
  | "needs_review"
  | "failed"
  | "skipped"
  | "dismissed"
  | "upload_failed"
  | "permanently_failed";

// ---------------------------------------------------------------------------
// Response Interfaces
// ---------------------------------------------------------------------------

export interface CandidateListItem {
  id: string;
  name: string;
  email: string;
  phone: string;
  skills: string[];
  status: CandidateStatus;
  confidence_score: number;
  created_at: string;
  has_cv: boolean;
}

export interface CandidateListResponse {
  candidates: CandidateListItem[];
  total_count: number;
  page: number;
  page_size: number;
}

export interface ExperienceItem {
  company: string;
  role: string;
  duration: string;
}

export interface EducationItem {
  institution: string;
  degree: string;
  year: string;
}

export interface CVDocument {
  id: string;
  original_filename: string;
  mime_type: string;
  size_bytes: number;
  uploaded_at: string;
  presigned_url: string | null;
  processing_status: ProcessingStatus;
}

export interface CandidateDetail {
  id: string;
  name: string;
  email: string;
  phone: string;
  skills: string[];
  experience: ExperienceItem[];
  education: EducationItem[];
  summary: string;
  status: CandidateStatus;
  confidence_score: number;
  source_email_message_id: string | null;
  rejection_reason: string | null;
  rejected_at: string | null;
  accepted_at: string | null;
  archived_at: string | null;
  created_at: string;
  updated_at: string;
  cv_documents: CVDocument[];
}

// ---------------------------------------------------------------------------
// CV Review Types
// ---------------------------------------------------------------------------

export interface ParsedCVData {
  name?: string;
  email?: string;
  phone?: string;
  skills?: string[];
  experience?: ExperienceItem[];
  education?: EducationItem[];
  summary?: string;
}

export interface ValidationError {
  field: string;
  message: string;
}

export interface CVReviewItem {
  id: string;
  candidate_id: string | null;
  gmail_message_id: string;
  original_filename: string;
  mime_type: string;
  size_bytes: number;
  ocr_output: string | null;
  parsed_cv_data: ParsedCVData | null;
  confidence_score: number | null;
  processing_status: ProcessingStatus;
  processing_error: string | null;
  validation_errors: ValidationError[] | null;
  retry_count: number;
  uploaded_at: string;
  created_at: string;
}

export interface CVReviewListResponse {
  items: CVReviewItem[];
  total: number;
  page: number;
  page_size: number;
}

// ---------------------------------------------------------------------------
// Metrics Types
// ---------------------------------------------------------------------------

export interface MetricsResponse {
  average_processing_time_ms: number;
  success_rate: number; // 0.0–1.0
  failure_rate: number; // 0.0–1.0
  queue_depth: number;
}

// ---------------------------------------------------------------------------
// Request Types
// ---------------------------------------------------------------------------

export interface CandidateListParams {
  page?: number;
  page_size?: number;
  search?: string;
  status?: CandidateStatus[];
  from_date?: string; // YYYY-MM-DD
  to_date?: string; // YYYY-MM-DD
  min_confidence?: number; // 0.0–1.0
  skills?: string; // comma-separated
}

export interface ScheduleInterviewRequest {
  date: string; // YYYY-MM-DD
  time: string; // HH:mm
  duration_minutes: number;
  interviewer_ids: string[];
  notes?: string;
}

export interface SendEmailRequest {
  subject: string;
  body_html: string;
  template_name?: string;
}

export interface RejectRequest {
  reason: string;
}

export interface ParsedCVInput {
  name: string;
  email: string;
  phone: string;
  skills: string[];
  experience: ExperienceItem[];
  education: EducationItem[];
  summary: string;
}

export interface CVPresignedUrlResponse {
  presigned_url: string;
  filename: string;
  mime_type: string;
  size_bytes: number;
}

// ---------------------------------------------------------------------------
// Internal Helpers
// ---------------------------------------------------------------------------

async function fetchWithTimeout(
  url: string,
  options: RequestInit = {}
): Promise<Response> {
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), TIMEOUT_MS);
  try {
    return await fetch(url, {
      ...options,
      credentials: "include",
      signal: controller.signal,
    });
  } catch (err) {
    if (err instanceof DOMException && err.name === "AbortError") {
      throw new ApiError(0, "TIMEOUT", "Yêu cầu đã hết thời gian chờ");
    }
    throw new ApiError(0, "NETWORK_ERROR", "Lỗi kết nối mạng");
  } finally {
    clearTimeout(timeoutId);
  }
}

async function handleResponse<T>(res: Response): Promise<T> {
  if (res.status === 401) {
    window.location.href = "/login";
    return new Promise(() => {}); // never resolves
  }
  if (!res.ok) {
    const body = await res.json().catch(() => null);
    const message =
      body?.detail ||
      body?.error?.message ||
      `Yêu cầu thất bại: ${res.status}`;
    const errorCode = body?.error_code || body?.error?.code || "UNKNOWN_ERROR";
    throw new ApiError(res.status, errorCode, message, body);
  }
  if (res.status === 204) return undefined as T;
  return res.json();
}

// ---------------------------------------------------------------------------
// Exported API Functions
// ---------------------------------------------------------------------------

/**
 * List candidates with pagination, search, and filters.
 */
export async function listCandidates(
  params: CandidateListParams = {}
): Promise<CandidateListResponse> {
  const searchParams = new URLSearchParams();

  if (params.page) searchParams.set("page", String(params.page));
  if (params.page_size) searchParams.set("page_size", String(params.page_size));
  if (params.search) searchParams.set("search", params.search);
  if (params.status && params.status.length > 0) {
    for (const s of params.status) {
      searchParams.append("status", s);
    }
  }
  if (params.from_date) searchParams.set("from_date", params.from_date);
  if (params.to_date) searchParams.set("to_date", params.to_date);
  if (params.min_confidence !== undefined && params.min_confidence > 0) {
    searchParams.set("min_confidence", String(params.min_confidence));
  }
  if (params.skills) searchParams.set("skills", params.skills);

  const query = searchParams.toString();
  const url = `${BASE}/candidates${query ? `?${query}` : ""}`;
  const res = await fetchWithTimeout(url);
  return handleResponse<CandidateListResponse>(res);
}

/**
 * Get full candidate detail by ID.
 */
export async function getCandidate(id: string): Promise<CandidateDetail> {
  const res = await fetchWithTimeout(`${BASE}/candidates/${id}`);
  return handleResponse<CandidateDetail>(res);
}

/**
 * Get a presigned URL for viewing/downloading a candidate's CV document.
 */
export async function getCVPresignedUrl(
  candidateId: string,
  documentId: string
): Promise<CVPresignedUrlResponse> {
  const res = await fetchWithTimeout(
    `${BASE}/candidates/${candidateId}/cv/${documentId}`
  );
  return handleResponse<CVPresignedUrlResponse>(res);
}

/**
 * Schedule an interview for a candidate.
 */
export async function scheduleInterview(
  id: string,
  data: ScheduleInterviewRequest
): Promise<void> {
  const res = await fetchWithTimeout(
    `${BASE}/candidates/${id}/schedule-interview`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(data),
    }
  );
  await handleResponse<unknown>(res);
}

/**
 * Send an email to a candidate.
 */
export async function sendEmail(
  id: string,
  data: SendEmailRequest
): Promise<void> {
  const res = await fetchWithTimeout(`${BASE}/candidates/${id}/send-email`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
  await handleResponse<unknown>(res);
}

/**
 * Reject a candidate with a reason.
 */
export async function rejectCandidate(
  id: string,
  data: RejectRequest
): Promise<void> {
  const res = await fetchWithTimeout(`${BASE}/candidates/${id}/reject`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
  await handleResponse<unknown>(res);
}

/**
 * Accept a candidate.
 */
export async function acceptCandidate(id: string): Promise<void> {
  const res = await fetchWithTimeout(`${BASE}/candidates/${id}/accept`, {
    method: "POST",
  });
  await handleResponse<unknown>(res);
}

/**
 * Archive a candidate.
 */
export async function archiveCandidate(id: string): Promise<void> {
  const res = await fetchWithTimeout(`${BASE}/candidates/${id}/archive`, {
    method: "POST",
  });
  await handleResponse<unknown>(res);
}

/**
 * List CV documents in the review queue.
 */
export async function listReviewQueue(
  params: { page?: number; page_size?: number } = {}
): Promise<CVReviewListResponse> {
  const searchParams = new URLSearchParams();
  if (params.page) searchParams.set("page", String(params.page));
  if (params.page_size) searchParams.set("page_size", String(params.page_size));

  const query = searchParams.toString();
  const url = `${BASE}/cv-review${query ? `?${query}` : ""}`;
  const res = await fetchWithTimeout(url);
  return handleResponse<CVReviewListResponse>(res);
}

/**
 * Submit corrected CV data for a document in the review queue.
 */
export async function submitCorrection(
  cvDocumentId: string,
  data: ParsedCVInput
): Promise<void> {
  const res = await fetchWithTimeout(`${BASE}/cv-review/${cvDocumentId}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
  await handleResponse<unknown>(res);
}

/**
 * Retry LLM parse for a CV document in the review queue.
 */
export async function retryParse(cvDocumentId: string): Promise<CVReviewItem> {
  const res = await fetchWithTimeout(
    `${BASE}/cv-review/${cvDocumentId}/retry`,
    {
      method: "POST",
    }
  );
  return handleResponse<CVReviewItem>(res);
}

/**
 * Dismiss a CV document from the review queue.
 */
export async function dismissReview(cvDocumentId: string): Promise<void> {
  const res = await fetchWithTimeout(
    `${BASE}/cv-review/${cvDocumentId}/dismiss`,
    {
      method: "DELETE",
    }
  );
  await handleResponse<void>(res);
}

/**
 * Get pipeline processing metrics (rolling 24-hour window).
 */
export async function getMetrics(): Promise<MetricsResponse> {
  const res = await fetchWithTimeout(`${BASE}/metrics`);
  return handleResponse<MetricsResponse>(res);
}
