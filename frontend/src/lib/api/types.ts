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

export interface EmployeeUpdateData extends Partial<EmployeeCreateData> {}

export interface DepartmentCreateData {
  name: string;
  description?: string;
}

export interface PositionCreateData {
  name: string;
  department_id?: string;
}
