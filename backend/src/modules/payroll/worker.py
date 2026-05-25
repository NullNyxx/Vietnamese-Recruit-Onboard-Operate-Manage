"""ARQ worker configuration for Payroll module.

Defines cron jobs that run monthly:
- auto_calculate_payroll: Runs on day 25 at 00:00 to auto-calculate payroll
- remind_payroll_confirmation: Runs on day 27 at 09:00 to remind HR to confirm

Usage:
    arq src.modules.payroll.worker.WorkerSettings
"""

from __future__ import annotations

import logging
import traceback
from datetime import UTC, datetime

from dotenv import load_dotenv

load_dotenv()

from arq import cron
from arq.connections import RedisSettings
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlmodel import Session

from src.database import engine
from src.modules.identity.infrastructure.config import AuthSettings
from src.modules.payroll.application.payroll_service import PayrollService

logger = logging.getLogger(__name__)


async def startup(ctx: dict) -> None:
    auth_settings = AuthSettings()
    engine = create_async_engine(auth_settings.database_url, echo=False)
    session_maker = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    ctx["session_maker"] = session_maker
    ctx["auth_settings"] = auth_settings

    logger.info("Payroll ARQ worker started")


async def shutdown(ctx: dict) -> None:
    logger.info("Payroll ARQ worker shut down")


async def auto_calculate_payroll(ctx: dict) -> None:
    """ARQ cron job: auto-create and calculate payroll for the previous month.

    Runs on day 25 at 00:00. Creates a payroll period if not exists,
    then calculates payslips for all employees with salary configs.
    """
    session_maker: async_sessionmaker[AsyncSession] = ctx["session_maker"]
    today = datetime.now(UTC).date()

    if today.month == 1:
        target_month = 12
        target_year = today.year - 1
    else:
        target_month = today.month - 1
        target_year = today.year

    async with session_maker() as session:
        try:
            existing = await session.execute(
                text("SELECT id FROM payroll_periods WHERE month = :month AND year = :year"),
                {"month": target_month, "year": target_year},
            )
            period_uuid = existing.scalar()

            if period_uuid is None:
                period_id = await session.execute(
                    text("""
                        INSERT INTO payroll_periods (id, month, year, status, created_at)
                        VALUES (gen_random_uuid(), :month, :year, 'draft', now())
                        RETURNING id
                    """),
                    {"month": target_month, "year": target_year},
                )
                period_uuid = period_id.scalar()
                await session.commit()
                logger.info(f"Created payroll period {target_month}/{target_year}: {period_uuid}")
            else:
                logger.info(f"Payroll period {target_month}/{target_year} already exists: {period_uuid}")

            with Session(engine) as sync_session:
                PayrollService(sync_session).calculate_all_employees(period_uuid)
                sync_session.commit()
            logger.info(f"Calculated payroll period {target_month}/{target_year}: {period_uuid}")

        except Exception:
            logger.error("Error creating payroll period: %s", traceback.format_exc())
            await session.rollback()


async def remind_payroll_confirmation(ctx: dict) -> None:
    """ARQ cron job: remind HR to confirm payroll.

    Runs on day 27 at 09:00. Logs a reminder for unconfirmed payroll periods.
    Could be extended to send email to HR.
    """
    session_maker: async_sessionmaker[AsyncSession] = ctx["session_maker"]
    today = datetime.now(UTC).date()

    if today.month == 1:
        target_month = 12
        target_year = today.year - 1
    else:
        target_month = today.month - 1
        target_year = today.year

    async with session_maker() as session:
        try:
            result = await session.execute(
                text("""
                    SELECT id, month, year, status
                    FROM payroll_periods
                    WHERE month = :month AND year = :year AND status = 'draft'
                """),
                {"month": target_month, "year": target_year},
            )
            period = result.first()

            if period:
                logger.info(
                    f"REMINDER: Payroll {period[1]}/{period[2]} (ID: {period[0]}) "
                    f"needs confirmation. Please confirm before month end."
                )
            else:
                logger.info(f"No unconfirmed payroll period found for {target_month}/{target_year}")

        except Exception:
            logger.error("Error in remind_payroll_confirmation: %s", traceback.format_exc())


_auth_settings = AuthSettings()


class WorkerSettings:
    on_startup = startup
    on_shutdown = shutdown

    cron_jobs = [
        cron(
            auto_calculate_payroll,
            day={25},
            hour={0},
            minute={0},
            second={0},
        ),
        cron(
            remind_payroll_confirmation,
            day={27},
            hour={9},
            minute={0},
            second={0},
        ),
    ]

    redis_settings = RedisSettings.from_dsn(_auth_settings.redis_url)