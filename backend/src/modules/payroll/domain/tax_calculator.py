from decimal import Decimal
from typing import NamedTuple


class TaxBracket(NamedTuple):
    min_income: Decimal
    max_income: Decimal
    rate: Decimal


TAX_BRACKETS = [
    TaxBracket(Decimal("0"), Decimal("5000000"), Decimal("0.05")),
    TaxBracket(Decimal("5000000"), Decimal("10000000"), Decimal("0.10")),
    TaxBracket(Decimal("10000000"), Decimal("18000000"), Decimal("0.15")),
    TaxBracket(Decimal("18000000"), Decimal("32000000"), Decimal("0.20")),
    TaxBracket(Decimal("32000000"), Decimal("52000000"), Decimal("0.25")),
    TaxBracket(Decimal("52000000"), Decimal("80000000"), Decimal("0.30")),
    TaxBracket(Decimal("80000000"), Decimal("1000000000"), Decimal("0.35")),
]

PERSONAL_DEDUCTION = Decimal("11000000")
DEPENDENT_DEDUCTION = Decimal("4400000")

EMPLOYEE_INSURANCE_RATE = Decimal("0.105")
SOCIAL_RATE = Decimal("0.08")
HEALTH_RATE = Decimal("0.015")
UNEMPLOYMENT_RATE = Decimal("0.01")

OT_RATE_WEEKDAY = Decimal("1.5")
OT_RATE_WEEKEND = Decimal("2.0")
OT_RATE_HOLIDAY = Decimal("3.0")


def calculate_progressive_tax(monthly_taxable_income: Decimal) -> Decimal:
    if monthly_taxable_income <= 0:
        return Decimal("0")

    tax = Decimal("0")
    remaining = monthly_taxable_income

    for bracket in TAX_BRACKETS:
        if remaining <= 0:
            break

        bracket_width = bracket.max_income - bracket.min_income
        taxable_in_bracket = min(remaining, bracket_width)

        if taxable_in_bracket > 0:
            tax += taxable_in_bracket * bracket.rate
            remaining -= taxable_in_bracket

    return tax.quantize(Decimal("1"))


def calculate_personal_deduction() -> Decimal:
    return PERSONAL_DEDUCTION


def calculate_dependent_deduction(num_dependents: int) -> Decimal:
    return DEPENDENT_DEDUCTION * num_dependents


def calculate_insurance_premium(insurance_salary: Decimal) -> Decimal:
    return (insurance_salary * EMPLOYEE_INSURANCE_RATE).quantize(Decimal("1"))


def calculate_overtime_pay(
    hourly_rate: Decimal,
    ot_hours: Decimal,
    is_weekend: bool = False,
    is_holiday: bool = False,
) -> Decimal:
    if ot_hours <= 0:
        return Decimal("0")

    if is_holiday:
        rate = OT_RATE_HOLIDAY
    elif is_weekend:
        rate = OT_RATE_WEEKEND
    else:
        rate = OT_RATE_WEEKDAY

    return (hourly_rate * ot_hours * rate).quantize(Decimal("1"))


def calculate_gross_to_net(
    gross_salary: Decimal,
    total_allowances: Decimal = Decimal("0"),
    non_taxable_allowances: Decimal = Decimal("0"),
    total_ot_amount: Decimal = Decimal("0"),
    num_dependents: int = 0,
    insurance_salary: Decimal | None = None,
) -> dict:
    gross_income = gross_salary + total_allowances + non_taxable_allowances + total_ot_amount

    if insurance_salary is None:
        insurance_salary = gross_salary

    insurance_premium = calculate_insurance_premium(insurance_salary)

    personal_deduction = PERSONAL_DEDUCTION
    dependent_deduction = DEPENDENT_DEDUCTION * num_dependents
    total_deduction = personal_deduction + dependent_deduction

    taxable_income = (gross_salary + total_allowances + total_ot_amount) - insurance_premium - total_deduction
    if taxable_income < 0:
        taxable_income = Decimal("0")

    income_tax = calculate_progressive_tax(taxable_income)

    net_salary = gross_income - income_tax - insurance_premium

    return {
        "gross_salary": gross_salary,
        "total_allowances": total_allowances,
        "total_ot_amount": total_ot_amount,
        "gross_income": gross_income,
        "personal_deduction": personal_deduction,
        "dependent_deduction": dependent_deduction,
        "total_deduction": total_deduction,
        "taxable_income": taxable_income,
        "income_tax": income_tax,
        "insurance_premium": insurance_premium,
        "net_salary": net_salary,
    }


def calculate_employer_insurance(insurance_salary: Decimal) -> Decimal:
    total_rate = Decimal("0.215")
    return (insurance_salary * total_rate).quantize(Decimal("1"))