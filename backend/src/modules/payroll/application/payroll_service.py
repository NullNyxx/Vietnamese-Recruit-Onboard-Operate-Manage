from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Sequence
from uuid import UUID

from sqlmodel import Session, select

from src.modules.attendance.domain.entities import AttendanceRecord, OvertimeRequest
from src.modules.attendance.domain.enums import OvertimeStatus
from src.modules.employee.domain.entities import Employee
from src.modules.payroll.domain.entities import PayrollPeriod, Payslip
from src.modules.payroll.domain.enums import PayrollStatus
from src.modules.payroll.domain.exceptions import (
    PayrollPeriodNotFoundError,
    SalaryNotConfiguredError,
)
from src.modules.payroll.domain.tax_calculator import (
    calculate_gross_to_net,
    calculate_overtime_pay,
)
from src.modules.payroll.infrastructure.config import payroll_settings
from src.modules.payroll.infrastructure.repositories import (
    AllowanceRepository,
    DependentRepository,
    PayrollPeriodRepository,
    PayslipRepository,
    SalaryConfigRepository,
)


class PayrollService:
    def __init__(self, session: Session):
        self.session = session
        self.config_repo = SalaryConfigRepository(session)
        self.allowance_repo = AllowanceRepository(session)
        self.dependent_repo = DependentRepository(session)
        self.period_repo = PayrollPeriodRepository(session)
        self.payslip_repo = PayslipRepository(session)

    def get_period(self, period_id: UUID) -> PayrollPeriod:
        period = self.period_repo.get_by_id(period_id)
        if not period:
            raise PayrollPeriodNotFoundError(f"Period {period_id} not found")
        return period

    def create_period(self, month: int, year: int) -> PayrollPeriod:
        existing = self.period_repo.get_by_month_year(month, year)
        if existing:
            return existing

        period = PayrollPeriod(month=month, year=year, status=PayrollStatus.DRAFT)
        return self.period_repo.create(period)

    def get_all_periods(self) -> Sequence[PayrollPeriod]:
        return self.period_repo.get_all()

    def calculate_employee_payslip(
        self,
        employee_id: UUID,
        period: PayrollPeriod,
        work_days: Decimal,
        actual_work_days: Decimal,
        total_ot_hours: Decimal = Decimal("0"),
    ) -> Payslip:
        config = self.config_repo.get_by_employee_id(employee_id)
        if not config:
            raise SalaryNotConfiguredError(
                f"Salary config not found for employee {employee_id}"
            )

        gross_salary = config.gross_salary
        insurance_salary = config.insurance_salary

        standard_work_days = period.total_work_days if period.total_work_days else Decimal("26")
        daily_rate = gross_salary / standard_work_days
        actual_gross = daily_rate * actual_work_days

        allowances = self.allowance_repo.get_active_by_employee(employee_id)
        total_allowances = sum(a.amount for a in allowances)
        taxable_allowances = sum(a.amount for a in allowances if a.is_taxable)
        non_taxable_allowances = total_allowances - taxable_allowances

        hourly_rate = daily_rate / Decimal("8")
        ot_amount = calculate_overtime_pay(hourly_rate, total_ot_hours)

        gross_income = actual_gross + total_allowances + ot_amount

        num_dependents = self.dependent_repo.count_tax_dependents(employee_id)

        result = calculate_gross_to_net(
            gross_salary=actual_gross,
            total_allowances=taxable_allowances,
            non_taxable_allowances=non_taxable_allowances,
            total_ot_amount=ot_amount,
            num_dependents=num_dependents,
            insurance_salary=insurance_salary,
        )

        payslip = Payslip(
            period_id=period.id,
            employee_id=employee_id,
            gross_salary=gross_salary,
            daily_rate=daily_rate,
            work_days=work_days,
            actual_work_days=actual_work_days,
            actual_gross=actual_gross,
            total_allowances=total_allowances,
            total_ot_hours=total_ot_hours,
            total_ot_amount=ot_amount,
            gross_income=gross_income,
            personal_deduction=result["personal_deduction"],
            dependent_deduction=result["dependent_deduction"],
            taxable_income=result["taxable_income"],
            income_tax=result["income_tax"],
            insurance_premium=result["insurance_premium"],
            net_salary=result["net_salary"],
        )

        return self.payslip_repo.create(payslip)

    def calculate_all_employees(self, period_id: UUID) -> list[Payslip]:
        period = self.get_period(period_id)

        period.status = PayrollStatus.CALCULATING
        self.period_repo.update(period)

        self.payslip_repo.session.exec(
            select(Payslip).where(Payslip.period_id == period_id)
        )
        existing_payslips = self.payslip_repo.get_by_period_id(period_id)
        for p in existing_payslips:
            self.payslip_repo.session.delete(p)
        self.payslip_repo.session.commit()

        employees = self.session.exec(
            select(Employee).where(Employee.is_active == True)
        ).all()

        start_date = date(period.year, period.month, 1)
        if period.month == 12:
            end_date = date(period.year + 1, 1, 1)
        else:
            end_date = date(period.year, period.month + 1, 1)

        payslips = []
        total_gross = Decimal("0")
        total_net = Decimal("0")
        total_tax = Decimal("0")
        total_insurance = Decimal("0")

        for employee in employees:
            try:
                attendance_records = self.session.exec(
                    select(AttendanceRecord)
                    .where(AttendanceRecord.employee_id == employee.id)
                    .where(AttendanceRecord.work_date >= start_date)
                    .where(AttendanceRecord.work_date < end_date)
                ).all()
                approved_ot_requests = self.session.exec(
                    select(OvertimeRequest)
                    .where(OvertimeRequest.employee_id == employee.id)
                    .where(OvertimeRequest.status == OvertimeStatus.APPROVED)
                    .where(OvertimeRequest.work_date >= start_date)
                    .where(OvertimeRequest.work_date < end_date)
                ).all()

                actual_work_days = Decimal("0")
                total_ot_hours = Decimal("0")

                for record in attendance_records:
                    if record.status in ["present", "late", "early_leave", "on_leave"]:
                        actual_work_days += Decimal("1")

                for request in approved_ot_requests:
                    total_ot_hours += request.actual_hours or request.planned_hours or Decimal("0")

                work_days = Decimal(str(payroll_settings.DEFAULT_WORK_DAYS))

                payslip = self.calculate_employee_payslip(
                    employee.id, period, work_days, actual_work_days, total_ot_hours
                )
                payslips.append(payslip)

                total_gross += payslip.gross_income
                total_net += payslip.net_salary
                total_tax += payslip.income_tax
                total_insurance += payslip.insurance_premium

            except SalaryNotConfiguredError:
                continue

        period.total_gross = total_gross
        period.total_net = total_net
        period.total_tax = total_tax
        period.total_insurance = total_insurance
        period.status = PayrollStatus.DRAFT
        self.period_repo.update(period)

        return payslips

    def confirm_period(self, period_id: UUID, confirmed_by: UUID) -> PayrollPeriod:
        period = self.get_period(period_id)

        if period.status not in [PayrollStatus.DRAFT, PayrollStatus.CALCULATING]:
            from src.modules.payroll.domain.exceptions import (
                PeriodAlreadyConfirmedError,
            )
            raise PeriodAlreadyConfirmedError(
                f"Period {period_id} is already {period.status}"
            )

        period.status = PayrollStatus.CONFIRMED
        period.confirmed_at = datetime.now(UTC)
        period.confirmed_by = confirmed_by
        return self.period_repo.update(period)

    def mark_period_paid(self, period_id: UUID) -> PayrollPeriod:
        period = self.get_period(period_id)

        if period.status != PayrollStatus.CONFIRMED:
            from src.modules.payroll.domain.exceptions import PeriodAlreadyPaidError

            raise PeriodAlreadyPaidError(
                f"Period must be confirmed before marking as paid"
            )

        period.status = PayrollStatus.PAID
        period.paid_at = datetime.now(UTC)
        return self.period_repo.update(period)

    def get_payslips_by_period(self, period_id: UUID) -> Sequence[Payslip]:
        return self.payslip_repo.get_by_period_id(period_id)

    def get_payslip_by_employee(
        self, employee_id: UUID, period_id: UUID
    ) -> Payslip | None:
        return self.payslip_repo.get_by_employee_and_period(employee_id, period_id)

    def get_employee_payslips(self, employee_id: UUID) -> Sequence[Payslip]:
        return self.payslip_repo.get_by_employee_id(employee_id)