"""Service for sending monthly attendance reports via email.

Generates HTML email with attendance summary and sends to each employee
using the Gmail module's SendService.
"""

from __future__ import annotations

import calendar
import logging
from datetime import date
from uuid import UUID

from sqlalchemy import text as sa_text
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.attendance.infrastructure.attendance_repository import AttendanceRepository

logger = logging.getLogger(__name__)


def _build_attendance_email_html(
    employee_name: str,
    month: int,
    year: int,
    summary: dict,
    records: list,
) -> str:
    """Build HTML email body for monthly attendance report."""

    status_labels = {
        "present": "✅ Có mặt",
        "late": "⚠️ Đi muộn",
        "early_leave": "🟠 Về sớm",
        "absent": "❌ Vắng mặt",
        "on_leave": "🔵 Nghỉ phép",
        "holiday": "🟣 Ngày lễ",
    }

    # Build records table rows
    rows_html = ""
    for r in records:
        check_in_str = r.check_in.strftime("%H:%M") if r.check_in else "—"
        check_out_str = r.check_out.strftime("%H:%M") if r.check_out else "—"
        work_h = f"{float(r.work_hours):.1f}h" if r.work_hours else "—"
        ot_h = f"{float(r.overtime_hours):.1f}h" if r.overtime_hours and float(r.overtime_hours) > 0 else "—"
        status_text = status_labels.get(r.status, r.status)
        date_str = r.work_date.strftime("%d/%m")
        day_names = ["T2", "T3", "T4", "T5", "T6", "T7", "CN"]
        day_name = day_names[r.work_date.weekday()]

        rows_html += f"""
        <tr>
            <td style="padding:6px;border:1px solid #ddd;">{date_str} ({day_name})</td>
            <td style="padding:6px;border:1px solid #ddd;text-align:center;">{check_in_str}</td>
            <td style="padding:6px;border:1px solid #ddd;text-align:center;">{check_out_str}</td>
            <td style="padding:6px;border:1px solid #ddd;text-align:center;">{work_h}</td>
            <td style="padding:6px;border:1px solid #ddd;text-align:center;">{ot_h}</td>
            <td style="padding:6px;border:1px solid #ddd;">{status_text}</td>
        </tr>"""

    html = f"""
    <div style="font-family:Arial,sans-serif;max-width:700px;margin:0 auto;">
        <h2 style="color:#1a56db;">📋 Báo Cáo Chấm Công Tháng {month}/{year}</h2>
        <p>Xin chào <strong>{employee_name}</strong>,</p>
        <p>Dưới đây là tổng hợp chấm công của bạn trong tháng {month}/{year}:</p>
        
        <table style="border-collapse:collapse;margin:16px 0;width:100%;">
            <tr style="background:#f0f7ff;">
                <td style="padding:8px;"><strong>Ngày có mặt:</strong></td>
                <td style="padding:8px;">{summary['present_days']} ngày</td>
                <td style="padding:8px;"><strong>Tổng giờ làm:</strong></td>
                <td style="padding:8px;">{summary['total_work_hours']}h</td>
            </tr>
            <tr>
                <td style="padding:8px;"><strong>Ngày đi muộn:</strong></td>
                <td style="padding:8px;">{summary['late_days']} ngày</td>
                <td style="padding:8px;"><strong>Tổng giờ OT:</strong></td>
                <td style="padding:8px;">{summary['total_overtime_hours']}h</td>
            </tr>
            <tr style="background:#f0f7ff;">
                <td style="padding:8px;"><strong>Ngày vắng:</strong></td>
                <td style="padding:8px;">{summary['absent_days']} ngày</td>
                <td style="padding:8px;"><strong>Ngày nghỉ phép:</strong></td>
                <td style="padding:8px;">{summary['leave_days']} ngày</td>
            </tr>
        </table>

        <h3>Chi tiết chấm công:</h3>
        <table style="border-collapse:collapse;width:100%;font-size:13px;">
            <thead>
                <tr style="background:#1a56db;color:white;">
                    <th style="padding:8px;border:1px solid #ddd;">Ngày</th>
                    <th style="padding:8px;border:1px solid #ddd;">Vào</th>
                    <th style="padding:8px;border:1px solid #ddd;">Ra</th>
                    <th style="padding:8px;border:1px solid #ddd;">Giờ làm</th>
                    <th style="padding:8px;border:1px solid #ddd;">OT</th>
                    <th style="padding:8px;border:1px solid #ddd;">Trạng thái</th>
                </tr>
            </thead>
            <tbody>
                {rows_html}
            </tbody>
        </table>

        <p style="margin-top:20px;color:#666;font-size:12px;">
            Email này được gửi tự động từ hệ thống Vroom HR.<br>
            Nếu có thắc mắc, vui lòng liên hệ phòng Nhân sự.
        </p>
    </div>
    """
    return html


class EmailReportService:
    """Sends monthly attendance reports to employees via Gmail.

    Uses the Gmail module's send functionality to deliver HTML emails
    containing attendance summaries to each employee.
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._attendance_repo = AttendanceRepository(session)

    async def send_monthly_reports(
        self, month: int, year: int, user_id: UUID
    ) -> dict:
        """Send attendance report emails to all active employees.

        Args:
            month: Report month (1-12).
            year: Report year.
            user_id: The HR user ID (for Gmail send authentication).

        Returns:
            Dict with sent_count, failed_count, errors.
        """
        from src.modules.gmail.application.send_service import SendEmailParams, SendService
        from src.modules.gmail.infrastructure.config import GmailSettings
        from src.modules.gmail.infrastructure.gmail_adapter import GmailAdapter
        from src.modules.gmail.infrastructure.audit_logger import AuditLogger
        from src.modules.gmail.infrastructure.email_repository import EmailRepository
        from src.modules.gmail.infrastructure.quota_tracker import QuotaTracker
        from src.modules.identity.infrastructure.config import AuthSettings
        from src.modules.identity.infrastructure.crypto_utils import CryptoUtils
        from src.modules.identity.infrastructure.oauth_grant_repository import OAuthGrantRepository
        import httpx
        import redis.asyncio as redis

        # Get all active employees with email
        emp_result = await self._session.execute(
            sa_text("SELECT id, full_name, email FROM employees WHERE is_active = true")
        )
        employees = emp_result.fetchall()

        if not employees:
            return {"sent_count": 0, "failed_count": 0, "errors": []}

        sent_count = 0
        failed_count = 0
        errors: list[dict] = []

        # Build SendService manually (can't use FastAPI Depends outside request)
        auth_settings = AuthSettings()  # type: ignore[call-arg]
        gmail_settings = GmailSettings()  # type: ignore[call-arg]
        crypto = CryptoUtils(auth_settings.oauth_token_encryption_key)
        redis_client = redis.from_url(auth_settings.redis_url, decode_responses=True)
        quota_tracker = QuotaTracker(redis_client, gmail_settings)
        http_client = httpx.AsyncClient()

        gmail_adapter = GmailAdapter(
            settings=gmail_settings,
            quota_tracker=quota_tracker,
            http_client=http_client,
            user_id=user_id,
        )
        email_repo = EmailRepository(self._session)
        oauth_grant_repo = OAuthGrantRepository(self._session)
        audit_logger = AuditLogger(self._session, gmail_settings)

        send_service = SendService(
            gmail_adapter=gmail_adapter,
            email_repo=email_repo,
            oauth_grant_repo=oauth_grant_repo,
            crypto=crypto,
            audit_logger=audit_logger,
            settings=gmail_settings,
            client_id=auth_settings.google_client_id,
            client_secret=auth_settings.google_client_secret,
        )

        for emp in employees:
            emp_id, emp_name, emp_email = emp

            if not emp_email:
                errors.append({"employee": emp_name, "error": "Không có email"})
                failed_count += 1
                continue

            try:
                # Get monthly report
                records = await self._attendance_repo.get_monthly_report(
                    emp_id, year, month
                )

                # Calculate summary
                present_days = sum(1 for r in records if r.status in ("present", "late", "early_leave"))
                late_days = sum(1 for r in records if r.status == "late")
                absent_days = sum(1 for r in records if r.status == "absent")
                leave_days = sum(1 for r in records if r.status == "on_leave")
                total_work_hours = round(sum(float(r.work_hours or 0) for r in records), 1)
                total_ot_hours = round(sum(float(r.overtime_hours or 0) for r in records), 1)

                summary = {
                    "present_days": present_days,
                    "late_days": late_days,
                    "absent_days": absent_days,
                    "leave_days": leave_days,
                    "total_work_hours": total_work_hours,
                    "total_overtime_hours": total_ot_hours,
                }

                # Build email
                html_body = _build_attendance_email_html(
                    employee_name=emp_name,
                    month=month,
                    year=year,
                    summary=summary,
                    records=records,
                )

                # Send via Gmail
                params = SendEmailParams(
                    to=[emp_email],
                    subject=f"[Vroom HR] Báo cáo chấm công tháng {month}/{year}",
                    body_html=html_body,
                    body_text=f"Báo cáo chấm công tháng {month}/{year} cho {emp_name}",
                    cc=[],
                    attachments=[],
                )

                await send_service.send_email(user_id, params)
                sent_count += 1

                logger.info("Sent attendance report to %s (%s)", emp_name, emp_email)

            except Exception as exc:
                logger.error("Failed to send report to %s: %s", emp_name, exc)
                errors.append({"employee": emp_name, "error": str(exc)})
                failed_count += 1

        return {
            "sent_count": sent_count,
            "failed_count": failed_count,
            "total": len(employees),
            "errors": errors,
        }
