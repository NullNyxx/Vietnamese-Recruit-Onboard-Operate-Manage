const BASE = "/api/payroll";

async function handleResponse<T>(res: Response): Promise<T> {
  if (!res.ok) {
    const error = await res.json().catch(() => ({ detail: { message: res.statusText } }));
    throw new Error(error.detail?.message || `Request failed: ${res.status}`);
  }
  return res.json();
}

export interface SalaryConfig {
  id: string;
  employee_id: string;
  gross_salary: number;
  insurance_salary: number;
  contract_type: string;
  effective_date: string;
  created_at: string;
  updated_at: string;
}

export interface SalaryConfigCreate {
  employee_id: string;
  gross_salary: number;
  insurance_salary: number;
  contract_type: string;
  effective_date: string;
}

export interface SalaryConfigUpdate {
  gross_salary?: number;
  insurance_salary?: number;
  contract_type?: string;
  effective_date?: string;
}

export interface Allowance {
  id: string;
  employee_id: string;
  allowance_type: string;
  amount: number;
  is_taxable: boolean;
  effective_date: string;
  end_date: string | null;
  created_at: string;
}

export interface AllowanceCreate {
  employee_id: string;
  allowance_type: string;
  amount: number;
  is_taxable?: boolean;
  effective_date?: string;
  end_date?: string;
}

export interface Dependent {
  id: string;
  employee_id: string;
  name: string;
  relationship: string;
  date_of_birth: string | null;
  tax_dependent: boolean;
  created_at: string;
}

export interface DependentCreate {
  employee_id: string;
  name: string;
  relationship: string;
  date_of_birth?: string;
  tax_dependent?: boolean;
}

export interface PayrollPeriod {
  id: string;
  month: number;
  year: number;
  status: string;
  total_gross: number;
  total_net: number;
  total_tax: number;
  total_insurance: number;
  confirmed_at: string | null;
  paid_at: string | null;
  created_at: string;
}

export interface PayrollPeriodCreate {
  month: number;
  year: number;
}

export interface Payslip {
  id: string;
  period_id: string;
  employee_id: string;
  gross_salary: number;
  daily_rate: number;
  work_days: number;
  actual_work_days: number;
  actual_gross: number;
  total_allowances: number;
  total_ot_hours: number;
  total_ot_amount: number;
  gross_income: number;
  personal_deduction: number;
  dependent_deduction: number;
  taxable_income: number;
  income_tax: number;
  insurance_premium: number;
  net_salary: number;
  pdf_url: string | null;
  created_at: string;
}

export interface PayslipSendResult {
  sent: number;
  failed: number;
  errors: string[];
}

export interface EmployeeWithPayslip {
  employee_id: string;
  employee_code: string;
  full_name: string;
  department_name: string | null;
  position_name: string | null;
  payslip: Payslip | null;
}

export async function createSalaryConfig(data: SalaryConfigCreate): Promise<SalaryConfig> {
  const res = await fetch(`${BASE}/salary/config`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
  return handleResponse(res);
}

export async function getSalaryConfig(employeeId: string): Promise<SalaryConfig> {
  const res = await fetch(`${BASE}/salary/config/${employeeId}`);
  return handleResponse(res);
}

export async function updateSalaryConfig(employeeId: string, data: SalaryConfigUpdate): Promise<SalaryConfig> {
  const res = await fetch(`${BASE}/salary/config/${employeeId}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
  return handleResponse(res);
}

export async function deleteSalaryConfig(employeeId: string): Promise<void> {
  const res = await fetch(`${BASE}/salary/config/${employeeId}`, { method: "DELETE" });
  if (!res.ok) {
    throw new Error(`Request failed: ${res.status}`);
  }
}

export async function createAllowance(data: AllowanceCreate): Promise<Allowance> {
  const res = await fetch(`${BASE}/salary/allowances`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
  return handleResponse(res);
}

export async function getAllowances(employeeId: string): Promise<Allowance[]> {
  const res = await fetch(`${BASE}/salary/allowances/${employeeId}`);
  return handleResponse(res);
}

export async function updateAllowance(allowanceId: string, data: Partial<AllowanceCreate>): Promise<Allowance> {
  const res = await fetch(`${BASE}/salary/allowances/${allowanceId}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
  return handleResponse(res);
}

export async function deleteAllowance(allowanceId: string): Promise<void> {
  const res = await fetch(`${BASE}/salary/allowances/${allowanceId}`, { method: "DELETE" });
  if (!res.ok) {
    throw new Error(`Request failed: ${res.status}`);
  }
}

export async function createDependent(data: DependentCreate): Promise<Dependent> {
  const res = await fetch(`${BASE}/salary/dependents`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
  return handleResponse(res);
}

export async function getDependents(employeeId: string): Promise<Dependent[]> {
  const res = await fetch(`${BASE}/salary/dependents/${employeeId}`);
  return handleResponse(res);
}

export async function deleteDependent(dependentId: string): Promise<void> {
  const res = await fetch(`${BASE}/salary/dependents/${dependentId}`, { method: "DELETE" });
  if (!res.ok) {
    throw new Error(`Request failed: ${res.status}`);
  }
}

export async function createPayrollPeriod(data: PayrollPeriodCreate): Promise<PayrollPeriod> {
  const res = await fetch(`${BASE}/periods`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
  return handleResponse(res);
}

export async function getPayrollPeriods(): Promise<PayrollPeriod[]> {
  const res = await fetch(`${BASE}/periods`);
  return handleResponse(res);
}

export async function getPayrollPeriod(periodId: string): Promise<PayrollPeriod> {
  const res = await fetch(`${BASE}/periods/${periodId}`);
  return handleResponse(res);
}

export async function calculatePayroll(periodId: string): Promise<Payslip[]> {
  const res = await fetch(`${BASE}/periods/${periodId}/calculate`, { method: "POST" });
  return handleResponse(res);
}

export async function confirmPayrollPeriod(periodId: string, confirmedBy: string): Promise<PayrollPeriod> {
  const res = await fetch(`${BASE}/periods/${periodId}/confirm?confirmed_by=${confirmedBy}`, { method: "POST" });
  return handleResponse(res);
}

export async function markPayrollPaid(periodId: string): Promise<PayrollPeriod> {
  const res = await fetch(`${BASE}/periods/${periodId}/mark-paid`, { method: "POST" });
  return handleResponse(res);
}

export async function getPeriodPayslips(periodId: string): Promise<Payslip[]> {
  const res = await fetch(`${BASE}/periods/${periodId}/payslips`);
  return handleResponse(res);
}

export async function getPeriodEmployees(periodId: string): Promise<EmployeeWithPayslip[]> {
  const res = await fetch(`${BASE}/periods/${periodId}/employees`);
  return handleResponse(res);
}

export async function getEmployeePayslips(employeeId: string): Promise<Payslip[]> {
  const res = await fetch(`${BASE}/payslips/${employeeId}`);
  return handleResponse(res);
}

export async function getPayslipPdf(payslipId: string): Promise<Blob> {
  const res = await fetch(`${BASE}/payslips/${payslipId}/pdf`);
  if (!res.ok) {
    throw new Error(`Request failed: ${res.status}`);
  }
  return res.blob();
}
export async function sendPayslips(periodId: string): Promise<PayslipSendResult> {
  const res = await fetch(`${BASE}/periods/${periodId}/send-payslips`, { method: "POST" });
  return handleResponse(res);
}
