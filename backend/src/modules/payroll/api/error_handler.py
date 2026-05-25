from fastapi import HTTPException, status

from src.modules.payroll.domain.exceptions import (
    AllowanceNotFoundError,
    DependentNotFoundError,
    DuplicateSalaryConfigError,
    PayrollPeriodNotFoundError,
    PeriodAlreadyConfirmedError,
    PeriodAlreadyPaidError,
    SalaryConfigNotFoundError,
    SalaryNotConfiguredError,
)


def map_payroll_exceptions(e: Exception) -> HTTPException:
    match e:
        case DuplicateSalaryConfigError():
            return HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Salary config already exists for this employee",
            )
        case SalaryConfigNotFoundError():
            return HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Salary config not found",
            )
        case AllowanceNotFoundError():
            return HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Allowance not found",
            )
        case DependentNotFoundError():
            return HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Dependent not found",
            )
        case PayrollPeriodNotFoundError():
            return HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Payroll period not found",
            )
        case PeriodAlreadyConfirmedError():
            return HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Period already confirmed",
            )
        case PeriodAlreadyPaidError():
            return HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Period already paid",
            )
        case SalaryNotConfiguredError():
            return HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Salary not configured for employee",
            )
        case _:
            return HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=str(e),
            )