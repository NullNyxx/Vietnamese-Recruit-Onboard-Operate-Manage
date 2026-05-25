from decimal import Decimal


class PayrollSettings:
    PERSONAL_DEDUCTION: Decimal = Decimal("11000000")
    DEPENDENT_DEDUCTION: Decimal = Decimal("4400000")

    OT_RATE_WEEKDAY: Decimal = Decimal("1.5")
    OT_RATE_WEEKEND: Decimal = Decimal("2.0")
    OT_RATE_HOLIDAY: Decimal = Decimal("3.0")

    EMPLOYEE_INSURANCE_RATE: Decimal = Decimal("0.105")
    EMPLOYER_INSURANCE_RATE: Decimal = Decimal("0.215")

    DEFAULT_WORK_DAYS: int = 22

    def __init__(self):
        pass


payroll_settings = PayrollSettings()