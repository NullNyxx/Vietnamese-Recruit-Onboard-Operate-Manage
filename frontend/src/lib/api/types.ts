export interface Employee {
  id: string;
  employee_code: string;
  full_name: string;
  email: string;
  phone: string | null;
  date_of_birth: string | null;
  gender: string | null;
  address: string | null;
  department_id: string | null;
  position_id: string | null;
  start_date: string | null;
  id_number: string | null;
  tax_code: string | null;
  contract_type: string | null;
  candidate_id: string | null;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface EmployeeListResponse {
  items: Employee[];
  total: number;
  page: number;
  page_size: number;
}

export interface Department {
  id: string;
  name: string;
  description: string | null;
  created_at: string;
}

export interface Position {
  id: string;
  name: string;
  department_id: string | null;
  created_at: string;
}

export interface EmployeeDocument {
  id: string;
  employee_id: string;
  document_type: string;
  file_name: string;
  file_size: number;
  mime_type: string;
  description: string | null;
  uploaded_at: string;
}

export interface ImportResult {
  total_rows: number;
  success_count: number;
  error_count: number;
  errors: Array<{ row: number; message: string }>;
  departments_created?: number;
  positions_created?: number;
}

export interface EmployeeCreateData {
  full_name: string;
  email: string;
  phone?: string;
  date_of_birth?: string;
  gender?: string;
  address?: string;
  department_id?: string;
  position_id?: string;
  start_date?: string;
  id_number?: string;
  tax_code?: string;
  contract_type?: string;
}

export type EmployeeUpdateData = Partial<EmployeeCreateData>;

export interface DepartmentCreateData {
  name: string;
  description?: string;
}

export interface PositionCreateData {
  name: string;
  department_id?: string;
}

// ---------------------------------------------------------------------------
// Gmail Integration Types
// ---------------------------------------------------------------------------

export type ConnectionStatus = "connected" | "disconnected" | "token_expired";

export interface ConnectionStatusResponse {
  status: ConnectionStatus;
  email: string | null;
}

export interface ConnectResponse {
  status: ConnectionStatus | null;
  redirect_url: string | null;
}

export interface EmailMessage {
  id: string;
  gmail_message_id: string;
  gmail_thread_id: string;
  subject: string;
  sender_email: string;
  sender_name: string;
  recipient_emails: string[];
  cc_emails: string[];
  received_at: string; // ISO datetime
  snippet: string;
  label_ids: string[];
  has_attachments: boolean;
  category: string | null;
}

export interface MessageBodyResponse {
  plain_text: string | null;
  html: string | null;
}

export interface SendEmailRequest {
  to: string[];
  cc?: string[];
  subject: string;
  body_html?: string;
  body_text?: string;
  reply_to_message_id?: string;
}

export interface SendEmailResponse {
  message_id: string;
  thread_id: string;
}

export interface LabelRemoveRequest {
  label_name: string;
}

export interface SyncResponse {
  synced_count: number;
  status: string;
}

export interface AttachmentMetadata {
  attachment_id: string;
  filename: string;
  mime_type: string;
  size_bytes: number;
}

export interface AttachmentsResponse {
  fetched_count: number;
  skipped_count: number;
  total_count: number;
  attachments: AttachmentMetadata[];
}

export class ApiError extends Error {
  public statusCode: number;
  public errorCode: string;
  public details?: Record<string, unknown>;

  constructor(
    statusCode: number,
    errorCode: string,
    message: string,
    details?: Record<string, unknown>,
  ) {
    super(message);
    this.name = "ApiError";
    this.statusCode = statusCode;
    this.errorCode = errorCode;
    this.details = details;
  }
}
