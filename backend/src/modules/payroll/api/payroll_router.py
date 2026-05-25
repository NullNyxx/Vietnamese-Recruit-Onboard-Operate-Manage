from typing import Sequence
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import Response
from sqlmodel import Session, select

from src.database import get_session
from src.modules.employee.container import get_minio_client
from src.modules.employee.domain.entities import Department, Employee, Position
from src.modules.gmail.application.send_service import SendService
from src.modules.gmail.container import get_send_service
from src.modules.identity.container import get_current_user
from src.modules.identity.domain.entities import User
from src.modules.payroll.application.payroll_service import PayrollService
from src.modules.payroll.application.payslip_email_service import PayslipEmailService
from src.modules.payroll.api import schemas

router = APIRouter(prefix="/api/payroll", tags=["Payroll"])


def get_payroll_service(session: Session = Depends(get_session)) -> PayrollService:
    return PayrollService(session)


async def get_payslip_email_service(
    session: Session = Depends(get_session),
    send_service: SendService = Depends(get_send_service),
) -> PayslipEmailService:
    return PayslipEmailService(session, send_service, get_minio_client())


@router.post("/periods", response_model=schemas.PayrollPeriodResponse)
def create_period(
    data: schemas.PayrollPeriodCreate,
    service: PayrollService = Depends(get_payroll_service),
):
    return service.create_period(data.month, data.year)


@router.get("/periods", response_model=list[schemas.PayrollPeriodResponse])
def get_all_periods(
    service: PayrollService = Depends(get_payroll_service),
):
    return service.get_all_periods()


@router.get("/periods/{period_id}", response_model=schemas.PayrollPeriodResponse)
def get_period(
    period_id: UUID,
    service: PayrollService = Depends(get_payroll_service),
):
    try:
        return service.get_period(period_id)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.post("/periods/{period_id}/calculate", response_model=list[schemas.PayslipResponse])
def calculate_payroll(
    period_id: UUID,
    service: PayrollService = Depends(get_payroll_service),
):
    try:
        return service.calculate_all_employees(period_id)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/periods/{period_id}/confirm", response_model=schemas.PayrollPeriodResponse)
def confirm_period(
    period_id: UUID,
    confirmed_by: UUID,
    service: PayrollService = Depends(get_payroll_service),
):
    try:
        return service.confirm_period(period_id, confirmed_by)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/periods/{period_id}/mark-paid", response_model=schemas.PayrollPeriodResponse)
def mark_period_paid(
    period_id: UUID,
    service: PayrollService = Depends(get_payroll_service),
):
    try:
        return service.mark_period_paid(period_id)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/periods/{period_id}/send-payslips", response_model=schemas.PayslipSendResponse)
async def send_period_payslips(
    period_id: UUID,
    current_user: User = Depends(get_current_user),
    email_service: PayslipEmailService = Depends(get_payslip_email_service),
):
    try:
        return await email_service.send_period_payslips(current_user.id, period_id)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/periods/{period_id}/payslips", response_model=list[schemas.PayslipResponse])
def get_period_payslips(
    period_id: UUID,
    service: PayrollService = Depends(get_payroll_service),
):
    return service.get_payslips_by_period(period_id)


@router.get("/payslips/{employee_id}", response_model=list[schemas.PayslipResponse])
def get_employee_payslips(
    employee_id: UUID,
    service: PayrollService = Depends(get_payroll_service),
):
    return service.get_employee_payslips(employee_id)


@router.get("/periods/{period_id}/employees", response_model=list[schemas.EmployeeWithPayslip])
def get_period_employees_with_payslips(
    period_id: UUID,
    session: Session = Depends(get_session),
    service: PayrollService = Depends(get_payroll_service),
):
    try:
        service.get_period(period_id)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))

    payslips = service.get_payslips_by_period(period_id)
    payslip_map = {p.employee_id: p for p in payslips}

    employees = session.exec(
        select(Employee, Position, Department)
        .join(Position, Employee.position_id == Position.id, isouter=True)
        .join(Department, Employee.department_id == Department.id, isouter=True)
        .where(Employee.is_active == True)
    ).all()

    result = []
    for employee, position, department in employees:
        payslip = payslip_map.get(employee.id)
        result.append(
            schemas.EmployeeWithPayslip(
                employee_id=employee.id,
                employee_code=employee.employee_code,
                full_name=employee.full_name,
                department_name=department.name if department else None,
                position_name=position.name if position else None,
                payslip=schemas.PayslipResponse.model_validate(payslip) if payslip else None,
            )
        )

    return result


@router.get("/payslips/{payslip_id}/pdf")
async def get_payslip_pdf(
    payslip_id: UUID,
    session: Session = Depends(get_session),
):
    from src.modules.payroll.domain.entities import PayrollPeriod, Payslip
    from src.modules.payroll.infrastructure.pdf_generator import generate_payslip_pdf

    payslip = session.get(Payslip, payslip_id)
    if not payslip:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Payslip not found")

    period = session.get(PayrollPeriod, payslip.period_id)
    employee = session.get(Employee, payslip.employee_id)

    if not period or not employee:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Payslip data not found")

    if payslip.pdf_url:
        pdf_bytes = await get_minio_client().download_file(payslip.pdf_url)
    else:
        pdf_bytes = generate_payslip_pdf(
            employee_name=employee.full_name,
            employee_code=employee.employee_code,
            department=None,
            position=None,
            period_month=period.month,
            period_year=period.year,
            gross_salary=float(payslip.gross_salary),
            total_allowances=float(payslip.total_allowances),
            total_ot_amount=float(payslip.total_ot_amount),
            gross_income=float(payslip.gross_income),
            personal_deduction=float(payslip.personal_deduction),
            dependent_deduction=float(payslip.dependent_deduction),
            taxable_income=float(payslip.taxable_income),
            income_tax=float(payslip.income_tax),
            insurance_premium=float(payslip.insurance_premium),
            net_salary=float(payslip.net_salary),
            work_days=float(payslip.work_days),
            actual_work_days=float(payslip.actual_work_days),
        )
        storage_path = (
            f"payroll/payslips/{period.year}/{period.month:02d}/"
            f"{employee.employee_code}_{payslip.id}.pdf"
        )
        payslip.pdf_url = await get_minio_client().upload_file(
            storage_path,
            pdf_bytes,
            "application/pdf",
        )
        session.add(payslip)
        session.commit()
        session.refresh(payslip)

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=payslip_{period.year}_{period.month}.pdf"},
    )
