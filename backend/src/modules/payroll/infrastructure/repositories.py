from datetime import date
from typing import Sequence
from uuid import UUID

from sqlmodel import Session, select

from src.modules.employee.domain.entities import Employee
from src.modules.payroll.domain.entities import (
    Allowance,
    Dependent,
    PayrollPeriod,
    Payslip,
    PositionSalary,
    SalaryConfig,
)
from src.modules.payroll.domain.enums import PayrollStatus


class SalaryConfigRepository:
    def __init__(self, session: Session):
        self.session = session

    def get_by_employee_id(self, employee_id: UUID) -> SalaryConfig | None:
        return self.session.exec(
            select(SalaryConfig).where(SalaryConfig.employee_id == employee_id)
        ).first()

    def create(self, config: SalaryConfig) -> SalaryConfig:
        self.session.add(config)
        self.session.commit()
        self.session.refresh(config)
        return config

    def update(self, config: SalaryConfig) -> SalaryConfig:
        self.session.add(config)
        self.session.commit()
        self.session.refresh(config)
        return config

    def delete(self, config: SalaryConfig) -> None:
        self.session.delete(config)
        self.session.commit()


class AllowanceRepository:
    def __init__(self, session: Session):
        self.session = session

    def get_by_employee_id(self, employee_id: UUID) -> Sequence[Allowance]:
        return self.session.exec(
            select(Allowance)
            .where(Allowance.employee_id == employee_id)
            .where(Allowance.end_date.is_(None) | (Allowance.end_date >= date.today()))
        ).all()

    def get_active_by_employee(self, employee_id: UUID) -> Sequence[Allowance]:
        today = date.today()
        return self.session.exec(
            select(Allowance)
            .where(Allowance.employee_id == employee_id)
            .where(Allowance.effective_date <= today)
            .where((Allowance.end_date.is_(None)) | (Allowance.end_date >= today))
        ).all()

    def create(self, allowance: Allowance) -> Allowance:
        self.session.add(allowance)
        self.session.commit()
        self.session.refresh(allowance)
        return allowance

    def update(self, allowance: Allowance) -> Allowance:
        self.session.add(allowance)
        self.session.commit()
        self.session.refresh(allowance)
        return allowance

    def delete(self, allowance: Allowance) -> None:
        self.session.delete(allowance)
        self.session.commit()


class DependentRepository:
    def __init__(self, session: Session):
        self.session = session

    def get_by_employee_id(self, employee_id: UUID) -> Sequence[Dependent]:
        return self.session.exec(
            select(Dependent).where(Dependent.employee_id == employee_id)
        ).all()

    def get_tax_dependents(self, employee_id: UUID) -> Sequence[Dependent]:
        return self.session.exec(
            select(Dependent)
            .where(Dependent.employee_id == employee_id)
            .where(Dependent.tax_dependent == True)
        ).all()

    def count_tax_dependents(self, employee_id: UUID) -> int:
        return len(list(self.get_tax_dependents(employee_id)))

    def create(self, dependent: Dependent) -> Dependent:
        self.session.add(dependent)
        self.session.commit()
        self.session.refresh(dependent)
        return dependent

    def update(self, dependent: Dependent) -> Dependent:
        self.session.add(dependent)
        self.session.commit()
        self.session.refresh(dependent)
        return dependent

    def delete(self, dependent: Dependent) -> None:
        self.session.delete(dependent)
        self.session.commit()


class PayrollPeriodRepository:
    def __init__(self, session: Session):
        self.session = session

    def get_by_id(self, period_id: UUID) -> PayrollPeriod | None:
        return self.session.get(PayrollPeriod, period_id)

    def get_by_month_year(self, month: int, year: int) -> PayrollPeriod | None:
        return self.session.exec(
            select(PayrollPeriod)
            .where(PayrollPeriod.month == month)
            .where(PayrollPeriod.year == year)
        ).first()

    def get_all(self) -> Sequence[PayrollPeriod]:
        return self.session.exec(
            select(PayrollPeriod).order_by(PayrollPeriod.year.desc(), PayrollPeriod.month.desc())
        ).all()

    def get_by_status(self, status: PayrollStatus) -> Sequence[PayrollPeriod]:
        return self.session.exec(
            select(PayrollPeriod)
            .where(PayrollPeriod.status == status)
            .order_by(PayrollPeriod.year.desc(), PayrollPeriod.month.desc())
        ).all()

    def create(self, period: PayrollPeriod) -> PayrollPeriod:
        self.session.add(period)
        self.session.commit()
        self.session.refresh(period)
        return period

    def update(self, period: PayrollPeriod) -> PayrollPeriod:
        self.session.add(period)
        self.session.commit()
        self.session.refresh(period)
        return period


class PayslipRepository:
    def __init__(self, session: Session):
        self.session = session

    def get_by_id(self, payslip_id: UUID) -> Payslip | None:
        return self.session.get(Payslip, payslip_id)

    def get_by_period_id(self, period_id: UUID) -> Sequence[Payslip]:
        return self.session.exec(
            select(Payslip).where(Payslip.period_id == period_id)
        ).all()

    def get_by_employee_and_period(
        self, employee_id: UUID, period_id: UUID
    ) -> Payslip | None:
        return self.session.exec(
            select(Payslip)
            .where(Payslip.employee_id == employee_id)
            .where(Payslip.period_id == period_id)
        ).first()

    def get_by_employee_id(self, employee_id: UUID) -> Sequence[Payslip]:
        return self.session.exec(
            select(Payslip)
            .where(Payslip.employee_id == employee_id)
            .order_by(Payslip.created_at.desc())
        ).all()

    def create(self, payslip: Payslip) -> Payslip:
        self.session.add(payslip)
        self.session.commit()
        self.session.refresh(payslip)
        return payslip

    def create_many(self, payslips: list[Payslip]) -> None:
        self.session.add_all(payslips)
        self.session.commit()

    def update(self, payslip: Payslip) -> Payslip:
        self.session.add(payslip)
        self.session.commit()
        self.session.refresh(payslip)
        return payslip


class PositionSalaryRepository:
    def __init__(self, session: Session):
        self.session = session

    def get_by_position_id(self, position_id: UUID) -> Sequence[PositionSalary]:
        return self.session.exec(
            select(PositionSalary)
            .where(PositionSalary.position_id == position_id)
            .order_by(PositionSalary.grade)
        ).all()

    def get_by_position_and_grade(self, position_id: UUID, grade: str) -> PositionSalary | None:
        return self.session.exec(
            select(PositionSalary)
            .where(PositionSalary.position_id == position_id)
            .where(PositionSalary.grade == grade)
        ).first()

    def create(self, ps: PositionSalary) -> PositionSalary:
        self.session.add(ps)
        self.session.commit()
        self.session.refresh(ps)
        return ps

    def update(self, ps: PositionSalary) -> PositionSalary:
        self.session.add(ps)
        self.session.commit()
        self.session.refresh(ps)
        return ps

    def delete(self, ps: PositionSalary) -> None:
        self.session.delete(ps)
        self.session.commit()