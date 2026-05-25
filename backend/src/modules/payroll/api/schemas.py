from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field


class SalaryConfigCreate(BaseModel):
    employee_id: UUID
    gross_salary: Decimal = Field(..., max_digits=12, decimal_places=2)
    insurance_salary: Decimal = Field(..., max_digits=12, decimal_places=2)
    contract_type: str = Field(..., max_length=20)
    effective_date: date


class SalaryConfigUpdate(BaseModel):
    gross_salary: Decimal | None = Field(None, max_digits=12, decimal_places=2)
    insurance_salary: Decimal | None = Field(None, max_digits=12, decimal_places=2)
    contract_type: str | None = Field(None, max_length=20)
    effective_date: date | None = None


class SalaryConfigResponse(BaseModel):
    id: UUID
    employee_id: UUID
    gross_salary: Decimal
    insurance_salary: Decimal
    contract_type: str
    effective_date: date
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class AllowanceCreate(BaseModel):
    employee_id: UUID
    allowance_type: str = Field(..., max_length=50)
    amount: Decimal = Field(..., max_digits=10, decimal_places=2)
    is_taxable: bool = True
    effective_date: date | None = None
    end_date: date | None = None


class AllowanceUpdate(BaseModel):
    amount: Decimal | None = Field(None, max_digits=10, decimal_places=2)
    is_taxable: bool | None = None
    end_date: date | None = None


class AllowanceResponse(BaseModel):
    id: UUID
    employee_id: UUID
    allowance_type: str
    amount: Decimal
    is_taxable: bool
    effective_date: date
    end_date: date | None
    created_at: datetime

    class Config:
        from_attributes = True


class DependentCreate(BaseModel):
    employee_id: UUID
    name: str = Field(..., max_length=200)
    relationship: str = Field(..., max_length=50)
    date_of_birth: date | None = None
    tax_dependent: bool = True


class DependentUpdate(BaseModel):
    name: str | None = Field(None, max_length=200)
    relationship: str | None = Field(None, max_length=50)
    date_of_birth: date | None = None
    tax_dependent: bool | None = None


class DependentResponse(BaseModel):
    id: UUID
    employee_id: UUID
    name: str
    relationship: str
    date_of_birth: date | None
    tax_dependent: bool
    created_at: datetime

    class Config:
        from_attributes = True


class PayrollPeriodCreate(BaseModel):
    month: int = Field(..., ge=1, le=12)
    year: int = Field(..., ge=2000)


class PayrollPeriodResponse(BaseModel):
    id: UUID
    month: int
    year: int
    status: str
    total_gross: Decimal
    total_net: Decimal
    total_tax: Decimal
    total_insurance: Decimal
    confirmed_at: datetime | None
    paid_at: datetime | None
    created_at: datetime

    class Config:
        from_attributes = True


class PayslipResponse(BaseModel):
    id: UUID
    period_id: UUID
    employee_id: UUID
    gross_salary: Decimal
    daily_rate: Decimal
    work_days: Decimal
    actual_work_days: Decimal
    actual_gross: Decimal
    total_allowances: Decimal
    total_ot_hours: Decimal
    total_ot_amount: Decimal
    gross_income: Decimal
    personal_deduction: Decimal
    dependent_deduction: Decimal
    taxable_income: Decimal
    income_tax: Decimal
    insurance_premium: Decimal
    net_salary: Decimal
    pdf_url: str | None
    created_at: datetime

    class Config:
        from_attributes = True


class EmployeeWithPayslip(BaseModel):
    employee_id: UUID
    employee_code: str
    full_name: str
    department_name: str | None
    position_name: str | None
    payslip: PayslipResponse | None = None


class PayrollCalculateRequest(BaseModel):
    pass


class PayrollConfirmRequest(BaseModel):
    pass


class PayrollMarkPaidRequest(BaseModel):
    pass


class PayslipSendResponse(BaseModel):
    sent: int
    failed: int
    errors: list[str]


class PositionSalaryCreate(BaseModel):
    position_id: UUID
    grade: str = Field(..., max_length=10)
    min_salary: Decimal = Field(..., max_digits=12, decimal_places=2)
    mid_salary: Decimal = Field(..., max_digits=12, decimal_places=2)
    max_salary: Decimal = Field(..., max_digits=12, decimal_places=2)
    effective_date: date


class PositionSalaryResponse(BaseModel):
    id: UUID
    position_id: UUID
    grade: str
    min_salary: Decimal
    mid_salary: Decimal
    max_salary: Decimal
    effective_date: date
    created_at: datetime

    class Config:
        from_attributes = True


class PositionSalarySuggestion(BaseModel):
    position_id: UUID
    position_name: str
    grades: list[PositionSalaryResponse]