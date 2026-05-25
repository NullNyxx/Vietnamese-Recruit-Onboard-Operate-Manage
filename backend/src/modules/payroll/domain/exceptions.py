class PeriodAlreadyConfirmedError(Exception):
    pass


class PeriodAlreadyPaidError(Exception):
    pass


class SalaryNotConfiguredError(Exception):
    pass


class PayslipNotFoundError(Exception):
    pass


class PayrollPeriodNotFoundError(Exception):
    pass


class DependentNotFoundError(Exception):
    pass


class AllowanceNotFoundError(Exception):
    pass


class SalaryConfigNotFoundError(Exception):
    pass


class DuplicateSalaryConfigError(Exception):
    pass