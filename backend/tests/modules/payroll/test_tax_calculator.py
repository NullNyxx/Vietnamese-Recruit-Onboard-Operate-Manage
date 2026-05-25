"""Unit tests for tax_calculator module."""

from decimal import Decimal

import pytest

from src.modules.payroll.domain.tax_calculator import (
    calculate_gross_to_net,
    calculate_insurance_premium,
    calculate_overtime_pay,
    calculate_personal_deduction,
    calculate_dependent_deduction,
    calculate_progressive_tax,
    PERSONAL_DEDUCTION,
    DEPENDENT_DEDUCTION,
)


class TestCalculateProgressiveTax:
    def test_zero_income(self):
        assert calculate_progressive_tax(Decimal("0")) == Decimal("0")

    def test_bracket_1_full(self):
        tax = calculate_progressive_tax(Decimal("5000000"))
        assert tax == Decimal("250000")

    def test_bracket_2_full(self):
        tax = calculate_progressive_tax(Decimal("10000000"))
        assert tax == Decimal("750000")

    def test_bracket_3_full(self):
        tax = calculate_progressive_tax(Decimal("18000000"))
        assert tax == Decimal("1950000")

    def test_bracket_4_full(self):
        tax = calculate_progressive_tax(Decimal("32000000"))
        assert tax == Decimal("4750000")

    def test_bracket_5_full(self):
        tax = calculate_progressive_tax(Decimal("52000000"))
        assert tax == Decimal("9750000")

    def test_bracket_6_full(self):
        tax = calculate_progressive_tax(Decimal("80000000"))
        assert tax == Decimal("18150000")

    def test_bracket_7_full(self):
        tax = calculate_progressive_tax(Decimal("100000000"))
        assert tax == Decimal("25150000")


class TestPersonalDeduction:
    def test_personal_deduction_value(self):
        assert calculate_personal_deduction() == PERSONAL_DEDUCTION
        assert PERSONAL_DEDUCTION == Decimal("11000000")


class TestDependentDeduction:
    def test_zero_dependents(self):
        assert calculate_dependent_deduction(0) == Decimal("0")

    def test_one_dependent(self):
        assert calculate_dependent_deduction(1) == DEPENDENT_DEDUCTION

    def test_two_dependents(self):
        assert calculate_dependent_deduction(2) == DEPENDENT_DEDUCTION * 2


class TestInsurancePremium:
    def test_insurance_calculation(self):
        premium = calculate_insurance_premium(Decimal("10000000"))
        assert premium == Decimal("1050000")

    def test_insurance_with_zero_salary(self):
        premium = calculate_insurance_premium(Decimal("0"))
        assert premium == Decimal("0")


class TestOvertimePay:
    def test_zero_hours(self):
        assert calculate_overtime_pay(Decimal("50000"), Decimal("0")) == Decimal("0")

    def test_weekday_overtime(self):
        pay = calculate_overtime_pay(Decimal("50000"), Decimal("2"))
        assert pay == Decimal("150000")

    def test_weekend_overtime(self):
        pay = calculate_overtime_pay(Decimal("50000"), Decimal("2"), is_weekend=True)
        assert pay == Decimal("200000")

    def test_holiday_overtime(self):
        pay = calculate_overtime_pay(Decimal("50000"), Decimal("2"), is_holiday=True)
        assert pay == Decimal("300000")


class TestGrossToNet:
    def test_basic_calculation(self):
        result = calculate_gross_to_net(
            gross_salary=Decimal("20000000"),
            total_allowances=Decimal("0"),
            total_ot_amount=Decimal("0"),
            num_dependents=0,
            insurance_salary=Decimal("18000000"),
        )

        assert result["gross_salary"] == Decimal("20000000")
        assert result["personal_deduction"] == Decimal("11000000")
        assert result["dependent_deduction"] == Decimal("0")
        assert result["total_deduction"] == Decimal("11000000")
        assert result["insurance_premium"] == Decimal("1890000")
        assert result["taxable_income"] == Decimal("7110000")
        assert result["income_tax"] > Decimal("0")
        assert result["net_salary"] > Decimal("0")

    def test_with_dependents(self):
        result = calculate_gross_to_net(
            gross_salary=Decimal("20000000"),
            total_allowances=Decimal("0"),
            total_ot_amount=Decimal("0"),
            num_dependents=2,
            insurance_salary=Decimal("18000000"),
        )

        assert result["dependent_deduction"] == DEPENDENT_DEDUCTION * 2
        assert result["total_deduction"] == PERSONAL_DEDUCTION + (DEPENDENT_DEDUCTION * 2)

    def test_with_allowances(self):
        result = calculate_gross_to_net(
            gross_salary=Decimal("20000000"),
            total_allowances=Decimal("2000000"),
            total_ot_amount=Decimal("0"),
            num_dependents=0,
            insurance_salary=Decimal("18000000"),
        )

        assert result["gross_income"] == Decimal("22000000")

    def test_with_overtime(self):
        result = calculate_gross_to_net(
            gross_salary=Decimal("20000000"),
            total_allowances=Decimal("0"),
            total_ot_amount=Decimal("1000000"),
            num_dependents=0,
            insurance_salary=Decimal("18000000"),
        )

        assert result["gross_income"] == Decimal("21000000")

    def test_low_income_no_tax(self):
        result = calculate_gross_to_net(
            gross_salary=Decimal("5000000"),
            total_allowances=Decimal("0"),
            total_ot_amount=Decimal("0"),
            num_dependents=0,
        )

        assert result["income_tax"] == Decimal("0")
    def test_with_non_taxable_allowances(self):
        result = calculate_gross_to_net(
            gross_salary=Decimal("20000000"),
            total_allowances=Decimal("1000000"),
            non_taxable_allowances=Decimal("500000"),
            total_ot_amount=Decimal("0"),
            num_dependents=0,
            insurance_salary=Decimal("18000000"),
        )

        assert result["gross_income"] == Decimal("21500000")
        assert result["taxable_income"] == Decimal("8110000")
        assert result["net_salary"] == Decimal("19049000")
