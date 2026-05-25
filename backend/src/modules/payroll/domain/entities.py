from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal
from uuid import UUID, uuid4

from sqlalchemy import Column, DateTime
from sqlmodel import Field, SQLModel


class PositionSalary(SQLModel, table=True):
    __tablename__ = "position_salaries"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    position_id: UUID = Field(foreign_key="positions.id", nullable=False, index=True)
    grade: str = Field(max_length=10, nullable=False, default="A")
    min_salary: Decimal = Field(max_digits=12, decimal_places=2, nullable=False)
    mid_salary: Decimal = Field(max_digits=12, decimal_places=2, nullable=False)
    max_salary: Decimal = Field(max_digits=12, decimal_places=2, nullable=False)
    effective_date: date = Field(nullable=False)
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )


class SalaryConfig(SQLModel, table=True):
    __tablename__ = "salary_configs"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    employee_id: UUID = Field(foreign_key="employees.id", nullable=False, unique=True, index=True)
    gross_salary: Decimal = Field(max_digits=12, decimal_places=2, nullable=False)
    insurance_salary: Decimal = Field(max_digits=12, decimal_places=2, nullable=False)
    contract_type: str = Field(max_length=20, nullable=False)
    effective_date: date = Field(nullable=False)
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )


class Allowance(SQLModel, table=True):
    __tablename__ = "allowances"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    employee_id: UUID = Field(foreign_key="employees.id", nullable=False, index=True)
    allowance_type: str = Field(max_length=50, nullable=False)
    amount: Decimal = Field(max_digits=10, decimal_places=2, nullable=False)
    is_taxable: bool = Field(default=True)
    effective_date: date = Field(nullable=False)
    end_date: date | None = Field(default=None)
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )


class Dependent(SQLModel, table=True):
    __tablename__ = "dependents"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    employee_id: UUID = Field(foreign_key="employees.id", nullable=False, index=True)
    name: str = Field(max_length=200, nullable=False)
    relationship: str = Field(max_length=50, nullable=False)
    date_of_birth: date | None = Field(default=None)
    tax_dependent: bool = Field(default=True)
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )


class PayrollPeriod(SQLModel, table=True):
    __tablename__ = "payroll_periods"
    __table_args__ = {"mysql_engine": "InnoDB", "mysql_charset": "utf8mb4"}

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    month: int = Field(nullable=False)
    year: int = Field(nullable=False)
    status: str = Field(max_length=20, nullable=False, default="draft")
    total_work_days: int = Field(default=26)
    total_gross: Decimal = Field(max_digits=14, decimal_places=2, default=Decimal("0"))
    total_net: Decimal = Field(max_digits=14, decimal_places=2, default=Decimal("0"))
    total_tax: Decimal = Field(max_digits=14, decimal_places=2, default=Decimal("0"))
    total_insurance: Decimal = Field(max_digits=14, decimal_places=2, default=Decimal("0"))
    confirmed_at: datetime | None = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True), nullable=True),
    )
    confirmed_by: UUID | None = Field(default=None, foreign_key="users.id")
    paid_at: datetime | None = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True), nullable=True),
    )
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )


class Payslip(SQLModel, table=True):
    __tablename__ = "payslips"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    period_id: UUID = Field(foreign_key="payroll_periods.id", nullable=False, index=True)
    employee_id: UUID = Field(foreign_key="employees.id", nullable=False, index=True)
    gross_salary: Decimal = Field(max_digits=12, decimal_places=2, nullable=False)
    daily_rate: Decimal = Field(max_digits=12, decimal_places=2, nullable=False)
    work_days: Decimal = Field(max_digits=4, decimal_places=2, nullable=False)
    actual_work_days: Decimal = Field(max_digits=4, decimal_places=2, nullable=False)
    actual_gross: Decimal = Field(max_digits=12, decimal_places=2, nullable=False)
    total_allowances: Decimal = Field(max_digits=10, decimal_places=2, default=Decimal("0"))
    total_ot_hours: Decimal = Field(max_digits=6, decimal_places=2, default=Decimal("0"))
    total_ot_amount: Decimal = Field(max_digits=10, decimal_places=2, default=Decimal("0"))
    gross_income: Decimal = Field(max_digits=12, decimal_places=2, nullable=False)
    personal_deduction: Decimal = Field(max_digits=10, decimal_places=2, default=Decimal("11000000"))
    dependent_deduction: Decimal = Field(max_digits=10, decimal_places=2, default=Decimal("0"))
    taxable_income: Decimal = Field(max_digits=12, decimal_places=2, nullable=False)
    income_tax: Decimal = Field(max_digits=10, decimal_places=2, default=Decimal("0"))
    insurance_premium: Decimal = Field(max_digits=10, decimal_places=2, default=Decimal("0"))
    net_salary: Decimal = Field(max_digits=12, decimal_places=2, nullable=False)
    pdf_url: str | None = Field(default=None, max_length=500)
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )