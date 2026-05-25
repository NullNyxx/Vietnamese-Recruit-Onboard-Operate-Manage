"""Unit tests for PayrollService."""

from datetime import date
from decimal import Decimal
from uuid import uuid4

import pytest
from unittest.mock import MagicMock

from src.modules.payroll.application.payroll_service import PayrollService
from src.modules.payroll.domain.enums import PayrollStatus


class TestPayrollService:
    @pytest.fixture
    def mock_session(self):
        return MagicMock()

    @pytest.fixture
    def service(self, mock_session):
        return PayrollService(mock_session)

    def test_confirm_period(self, service, mock_session):
        mock_period = MagicMock()
        mock_period.status = PayrollStatus.DRAFT
        mock_session.get.return_value = mock_period

        service.confirm_period(uuid4(), uuid4())

        assert mock_period.status == PayrollStatus.CONFIRMED

    def test_mark_period_paid_not_confirmed(self, service, mock_session):
        mock_period = MagicMock()
        mock_period.status = PayrollStatus.DRAFT
        mock_session.get.return_value = mock_period

        from src.modules.payroll.domain.exceptions import PeriodAlreadyPaidError

        with pytest.raises(PeriodAlreadyPaidError):
            service.mark_period_paid(uuid4())

class StubConfigRepo:
    def __init__(self, gross_salary: Decimal, insurance_salary: Decimal):
        self._config = type("Config", (), {
            "gross_salary": gross_salary,
            "insurance_salary": insurance_salary,
        })()

    def get_by_employee_id(self, employee_id):
        return self._config


class StubAllowanceRepo:
    def __init__(self, allowances):
        self._allowances = allowances

    def get_active_by_employee(self, employee_id):
        return self._allowances


class StubDependentRepo:
    def __init__(self, count: int = 0):
        self._count = count

    def count_tax_dependents(self, employee_id):
        return self._count


class StubPayslipRepo:
    def __init__(self):
        self.created = None

    def create(self, payslip):
        self.created = payslip
        return payslip


class StubPeriodRepo:
    def get_by_id(self, period_id):
        return None


class AllowanceStub:
    def __init__(self, amount: Decimal, is_taxable: bool):
        self.amount = amount
        self.is_taxable = is_taxable


def test_calculate_employee_payslip_includes_non_taxable_allowance_in_net():
    service = PayrollService(MagicMock())
    service.config_repo = StubConfigRepo(Decimal("22000000"), Decimal("22000000"))
    service.allowance_repo = StubAllowanceRepo([
        AllowanceStub(Decimal("1000000"), True),
        AllowanceStub(Decimal("500000"), False),
    ])
    service.dependent_repo = StubDependentRepo(0)
    service.payslip_repo = StubPayslipRepo()
    service.period_repo = StubPeriodRepo()

    period = MagicMock()
    period.id = uuid4()
    period.total_work_days = 22

    payslip = service.calculate_employee_payslip(
        employee_id=uuid4(),
        period=period,
        work_days=Decimal("22"),
        actual_work_days=Decimal("22"),
        total_ot_hours=Decimal("0"),
    )

    assert payslip.total_allowances == Decimal("1500000")
    assert payslip.gross_income == Decimal("23500000")
    assert payslip.taxable_income == Decimal("9690000")
    assert payslip.net_salary == Decimal("20471000")
