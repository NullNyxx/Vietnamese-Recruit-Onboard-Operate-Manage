from typing import Sequence
from uuid import UUID

from sqlmodel import Session, select

from src.modules.employee.domain.entities import Employee
from src.modules.gmail.application.send_service import (
    AttachmentData,
    SendEmailParams,
    SendService,
)
from src.modules.gmail.infrastructure.email_repository import EmailRepository
from src.modules.gmail.infrastructure.gmail_adapter import GmailAdapter
from src.modules.identity.infrastructure.crypto_utils import CryptoUtils
from src.modules.identity.infrastructure.oauth_grant_repository import (
    OAuthGrantRepository,
)
from src.modules.employee.infrastructure.minio_client import MinIOClient
from src.modules.payroll.domain.entities import PayrollPeriod, Payslip
from src.modules.payroll.infrastructure.pdf_generator import generate_payslip_pdf


class PayslipEmailService:
    def __init__(self, session: Session, send_service: SendService, minio_client: MinIOClient):
        self.session = session
        self.send_service = send_service
        self.minio_client = minio_client

    async def send_payslip_email(
        self,
        user_id: UUID,
        employee: Employee,
        payslip: Payslip,
        period: PayrollPeriod,
    ) -> bool:
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

        if not payslip.pdf_url:
            storage_path = (
                f"payroll/payslips/{period.year}/{period.month:02d}/"
                f"{employee.employee_code}_{payslip.id}.pdf"
            )
            payslip.pdf_url = await self.minio_client.upload_file(
                storage_path,
                pdf_bytes,
                "application/pdf",
            )
            self.session.add(payslip)
            self.session.commit()
            self.session.refresh(payslip)

        attachment = AttachmentData(
            filename=f"payslip_{period.year}_{period.month}.pdf",
            content=pdf_bytes,
            mime_type="application/pdf",
        )

        params = SendEmailParams(
            to=[employee.email],
            subject=f"Phiếu lương tháng {period.month}/{period.year}",
            body_text=f"""Xin chào {employee.full_name},

Đính kèm là phiếu lương tháng {period.month}/{period.year}.

Lương thực nhận: {payslip.net_salary:,.0f} VNĐ

Vui lòng liên hệ HR nếu có thắc mắc.

Trân trọng,
HR Department""",
            attachments=[attachment],
        )

        try:
            await self.send_service.send_email(user_id, params)
            return True
        except Exception:
            return False

    async def send_period_payslips(
        self,
        user_id: UUID,
        period_id: UUID,
    ) -> dict:
        period = self.session.get(PayrollPeriod, period_id)
        if not period:
            return {"sent": 0, "failed": 0, "errors": ["Period not found"]}

        payslips = self.session.exec(
            select(Payslip).where(Payslip.period_id == period_id)
        ).all()

        sent = 0
        failed = 0
        errors = []

        for payslip in payslips:
            employee = self.session.get(Employee, payslip.employee_id)
            if not employee or not employee.email:
                failed += 1
                errors.append(f"Employee {payslip.employee_id} not found or no email")
                continue

            try:
                success = await self.send_payslip_email(
                    user_id, employee, payslip, period
                )
                if success:
                    sent += 1
                else:
                    failed += 1
            except Exception as e:
                failed += 1
                errors.append(f"Error sending to {employee.email}: {str(e)}")

        return {"sent": sent, "failed": failed, "errors": errors}