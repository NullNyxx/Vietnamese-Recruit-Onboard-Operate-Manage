from datetime import date
from decimal import Decimal
from typing import Sequence
from uuid import UUID

from sqlmodel import Session

from src.modules.employee.domain.entities import Employee
from src.modules.payroll.domain.entities import Allowance, Dependent, SalaryConfig
from src.modules.payroll.domain.enums import AllowanceType
from src.modules.payroll.domain.exceptions import (
    AllowanceNotFoundError,
    DependentNotFoundError,
    DuplicateSalaryConfigError,
    SalaryConfigNotFoundError,
)
from src.modules.payroll.infrastructure.repositories import (
    AllowanceRepository,
    DependentRepository,
    SalaryConfigRepository,
)


class SalaryService:
    def __init__(self, session: Session):
        self.session = session
        self.config_repo = SalaryConfigRepository(session)
        self.allowance_repo = AllowanceRepository(session)
        self.dependent_repo = DependentRepository(session)

    def get_salary_config(self, employee_id: UUID) -> SalaryConfig | None:
        return self.config_repo.get_by_employee_id(employee_id)

    def create_salary_config(
        self,
        employee_id: UUID,
        gross_salary: Decimal,
        insurance_salary: Decimal,
        contract_type: str,
        effective_date: date,
    ) -> SalaryConfig:
        existing = self.config_repo.get_by_employee_id(employee_id)
        if existing:
            raise DuplicateSalaryConfigError(
                f"Salary config already exists for employee {employee_id}"
            )

        config = SalaryConfig(
            employee_id=employee_id,
            gross_salary=gross_salary,
            insurance_salary=insurance_salary,
            contract_type=contract_type,
            effective_date=effective_date,
        )
        return self.config_repo.create(config)

    def update_salary_config(
        self,
        employee_id: UUID,
        gross_salary: Decimal | None = None,
        insurance_salary: Decimal | None = None,
        contract_type: str | None = None,
        effective_date: date | None = None,
    ) -> SalaryConfig:
        config = self.config_repo.get_by_employee_id(employee_id)
        if not config:
            raise SalaryConfigNotFoundError(
                f"Salary config not found for employee {employee_id}"
            )

        if gross_salary is not None:
            config.gross_salary = gross_salary
        if insurance_salary is not None:
            config.insurance_salary = insurance_salary
        if contract_type is not None:
            config.contract_type = contract_type
        if effective_date is not None:
            config.effective_date = effective_date

        return self.config_repo.update(config)

    def delete_salary_config(self, employee_id: UUID) -> None:
        config = self.config_repo.get_by_employee_id(employee_id)
        if not config:
            raise SalaryConfigNotFoundError(
                f"Salary config not found for employee {employee_id}"
            )
        self.config_repo.delete(config)

    def get_allowances(self, employee_id: UUID) -> Sequence[Allowance]:
        return self.allowance_repo.get_active_by_employee(employee_id)

    def create_allowance(
        self,
        employee_id: UUID,
        allowance_type: AllowanceType,
        amount: Decimal,
        is_taxable: bool = True,
        effective_date: date | None = None,
        end_date: date | None = None,
    ) -> Allowance:
        allowance = Allowance(
            employee_id=employee_id,
            allowance_type=allowance_type.value,
            amount=amount,
            is_taxable=is_taxable,
            effective_date=effective_date or date.today(),
            end_date=end_date,
        )
        return self.allowance_repo.create(allowance)

    def update_allowance(
        self,
        allowance_id: UUID,
        amount: Decimal | None = None,
        is_taxable: bool | None = None,
        end_date: date | None = None,
    ) -> Allowance:
        session = self.session
        allowance = session.get(Allowance, allowance_id)
        if not allowance:
            raise AllowanceNotFoundError(f"Allowance {allowance_id} not found")

        if amount is not None:
            allowance.amount = amount
        if is_taxable is not None:
            allowance.is_taxable = is_taxable
        if end_date is not None:
            allowance.end_date = end_date

        return self.allowance_repo.update(allowance)

    def delete_allowance(self, allowance_id: UUID) -> None:
        session = self.session
        allowance = session.get(Allowance, allowance_id)
        if not allowance:
            raise AllowanceNotFoundError(f"Allowance {allowance_id} not found")
        self.allowance_repo.delete(allowance)

    def get_dependents(self, employee_id: UUID) -> Sequence[Dependent]:
        return self.dependent_repo.get_by_employee_id(employee_id)

    def count_tax_dependents(self, employee_id: UUID) -> int:
        return self.dependent_repo.count_tax_dependents(employee_id)

    def create_dependent(
        self,
        employee_id: UUID,
        name: str,
        relationship: str,
        date_of_birth: date | None = None,
        tax_dependent: bool = True,
    ) -> Dependent:
        dependent = Dependent(
            employee_id=employee_id,
            name=name,
            relationship=relationship,
            date_of_birth=date_of_birth,
            tax_dependent=tax_dependent,
        )
        return self.dependent_repo.create(dependent)

    def update_dependent(
        self,
        dependent_id: UUID,
        name: str | None = None,
        relationship: str | None = None,
        date_of_birth: date | None = None,
        tax_dependent: bool | None = None,
    ) -> Dependent:
        session = self.session
        dependent = session.get(Dependent, dependent_id)
        if not dependent:
            raise DependentNotFoundError(f"Dependent {dependent_id} not found")

        if name is not None:
            dependent.name = name
        if relationship is not None:
            dependent.relationship = relationship
        if date_of_birth is not None:
            dependent.date_of_birth = date_of_birth
        if tax_dependent is not None:
            dependent.tax_dependent = tax_dependent

        return self.dependent_repo.update(dependent)

    def delete_dependent(self, dependent_id: UUID) -> None:
        session = self.session
        dependent = session.get(Dependent, dependent_id)
        if not dependent:
            raise DependentNotFoundError(f"Dependent {dependent_id} not found")
        self.dependent_repo.delete(dependent)