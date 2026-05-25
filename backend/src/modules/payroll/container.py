from sqlmodel import Session

from src.modules.payroll.application.payroll_service import PayrollService
from src.modules.payroll.application.salary_service import SalaryService
from src.modules.payroll.infrastructure.repositories import (
    AllowanceRepository,
    DependentRepository,
    PayrollPeriodRepository,
    PayslipRepository,
    SalaryConfigRepository,
)


def get_salary_service(session: Session) -> SalaryService:
    return SalaryService(session)


def get_payroll_service(session: Session) -> PayrollService:
    return PayrollService(session)