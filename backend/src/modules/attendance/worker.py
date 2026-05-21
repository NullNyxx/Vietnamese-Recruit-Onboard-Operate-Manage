"""ARQ worker configuration for Attendance module.

Defines the cron job that runs daily at 23:00 to mark employees
without check-in as absent (skipping those with approved leave).

Usage:
    arq src.modules.attendance.worker.WorkerSettings
"""

from __future__ import annotations

import logging
import traceback
from datetime import UTC, date, datetime

from dotenv import load_dotenv

# Load .env before any settings are instantiated.
load_dotenv()

from arq import cron
from arq.connections import RedisSettings
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from src.modules.identity.infrastructure.config import AuthSettings

logger = logging.getLogger(__name__)


async def startup(ctx: dict) -> None:
    """ARQ worker startup hook.

    Initializes database engine and session maker.
    """
    auth_settings = AuthSettings()  # type: ignore[call-arg]

    engine = create_async_engine(auth_settings.database_url, echo=False)
    session_maker = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    ctx["session_maker"] = session_maker
    ctx["auth_settings"] = auth_settings

    logger.info("Attendance ARQ worker started successfully")


async def shutdown(ctx: dict) -> None:
    """ARQ worker shutdown hook."""
    logger.info("Attendance ARQ worker shut down")


async def auto_mark_absent(ctx: dict) -> None:
    """ARQ cron job: mark employees without check-in today as absent.

    Runs daily at 23:00. For each active employee who does not have
    an attendance record today AND does not have an approved leave
    covering today, creates an attendance record with status 'absent'.

    Also skips holidays.
    """
    session_maker: async_sessionmaker[AsyncSession] = ctx["session_maker"]
    today = datetime.now(UTC).date()

    async with session_maker() as session:
        try:
            # Check if today is a holiday
            holiday_check = await session.execute(
                text("SELECT 1 FROM holidays WHERE holiday_date = :today LIMIT 1"),
                {"today": today},
            )
            if holiday_check.scalar() is not None:
                logger.info("Today %s is a holiday, skipping auto_mark_absent", today)
                return

            # Get all active employees
            employees_result = await session.execute(
                text("SELECT id FROM employees WHERE is_active = true")
            )
            all_employee_ids = {row[0] for row in employees_result.all()}

            if not all_employee_ids:
                logger.info("No active employees found")
                return

            # Get employees who already have attendance records today
            attended_result = await session.execute(
                text(
                    "SELECT employee_id FROM attendance_records WHERE work_date = :today"
                ),
                {"today": today},
            )
            attended_ids = {row[0] for row in attended_result.all()}

            # Get employees with approved leave covering today
            on_leave_result = await session.execute(
                text(
                    """
                    SELECT employee_id FROM leave_requests
                    WHERE status = 'approved'
                      AND start_date <= :today
                      AND end_date >= :today
                    """
                ),
                {"today": today},
            )
            on_leave_ids = {row[0] for row in on_leave_result.all()}

            # Employees to mark as absent: active - attended - on_leave
            absent_ids = all_employee_ids - attended_ids - on_leave_ids

            if not absent_ids:
                logger.info("No employees to mark as absent for %s", today)
                return

            # Also mark on_leave employees who don't have a record yet
            leave_no_record_ids = on_leave_ids - attended_ids

            # Insert absent records
            now = datetime.now(UTC)
            for emp_id in absent_ids:
                await session.execute(
                    text(
                        """
                        INSERT INTO attendance_records
                            (id, employee_id, work_date, status, created_at, updated_at)
                        VALUES
                            (gen_random_uuid(), :emp_id, :today, 'absent', :now, :now)
                        ON CONFLICT (employee_id, work_date) DO NOTHING
                        """
                    ),
                    {"emp_id": emp_id, "today": today, "now": now},
                )

            # Insert on_leave records for those on approved leave
            for emp_id in leave_no_record_ids:
                await session.execute(
                    text(
                        """
                        INSERT INTO attendance_records
                            (id, employee_id, work_date, status, note, created_at, updated_at)
                        VALUES
                            (gen_random_uuid(), :emp_id, :today, 'on_leave', 'Nghỉ phép (tự động)', :now, :now)
                        ON CONFLICT (employee_id, work_date) DO NOTHING
                        """
                    ),
                    {"emp_id": emp_id, "today": today, "now": now},
                )

            await session.commit()

            logger.info(
                "auto_mark_absent completed for %s: %d absent, %d on_leave",
                today,
                len(absent_ids),
                len(leave_no_record_ids),
            )

        except Exception:
            logger.error(
                "Unhandled exception in auto_mark_absent:\n%s",
                traceback.format_exc(),
            )
            await session.rollback()
            raise


# Load settings for worker configuration.
_auth_settings = AuthSettings()  # type: ignore[call-arg]


class WorkerSettings:
    """ARQ worker settings for Attendance module.

    Configures the daily cron job at 23:00 to mark absent employees.
    """

    on_startup = startup
    on_shutdown = shutdown

    cron_jobs = [
        cron(
            auto_mark_absent,
            hour={23},
            minute={0},
            second={0},
        ),
    ]

    redis_settings = RedisSettings.from_dsn(_auth_settings.redis_url)
