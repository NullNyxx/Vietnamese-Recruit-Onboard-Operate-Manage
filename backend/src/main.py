"""Vroom HR Backend - FastAPI application entrypoint."""

import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from dotenv import load_dotenv

# Load .env file before any settings are instantiated.
load_dotenv()

from fastapi import FastAPI

from src.modules.attendance.api.attendance_router import attendance_router
from src.modules.attendance.api.error_handler import register_attendance_error_handlers
from src.modules.attendance.api.overtime_router import overtime_router
from src.modules.attendance.api.router import leave_router
from src.modules.attendance.api.schedule_router import schedule_router
from src.modules.employee.api.error_handler import register_employee_error_handlers
from src.modules.employee.api.router import router as employee_router
from src.modules.gmail.api.error_handler import register_gmail_error_handlers
from src.modules.gmail.api.router import router as gmail_router
from src.modules.identity.api.admin_router import admin_router
from src.modules.identity.api.error_handler import register_auth_error_handlers
from src.modules.identity.api.router import router as auth_router
from src.modules.recruitment.api.candidate_router import candidate_router
from src.modules.recruitment.api.cv_review_router import cv_review_router
from src.modules.recruitment.api.error_handler import register_recruitment_error_handlers
from src.modules.payroll.api.payroll_router import router as payroll_router
from src.modules.payroll.api.salary_router import router as salary_router
from src.modules.recruitment.api.metrics_router import metrics_router
from src.modules.self_service.api.audit_middleware import ESSAuditMiddleware
from src.modules.self_service.api.router import ess_router

logger = logging.getLogger(__name__)


async def _bootstrap_super_admin() -> None:
    """Bootstrap the super admin user at application startup.

    If AUTH_SUPER_ADMIN_EMAIL is configured, ensures that user has the admin
    role. If not configured and no admin exists, logs a warning.
    """
    from sqlalchemy import func
    from sqlmodel import select

    from src.modules.identity.application.role_service import RoleService
    from src.modules.identity.container import _get_async_session_maker, get_settings
    from src.modules.identity.domain.entities import User, UserRole

    settings = get_settings()
    super_admin_email = settings.super_admin_email

    session_maker = _get_async_session_maker()
    async with session_maker() as session:
        if super_admin_email:
            role_service = RoleService(session=session, super_admin_email=super_admin_email)
            await role_service.ensure_super_admin(super_admin_email)
            await session.commit()
            logger.info("Super admin bootstrap completed for '%s'.", super_admin_email)
        else:
            # Check if any admin exists in the database.
            statement = select(func.count()).select_from(User).where(User.role == UserRole.ADMIN)
            result = await session.execute(statement)
            admin_count = result.scalar_one()
            if admin_count == 0:
                logger.warning(
                    "No AUTH_SUPER_ADMIN_EMAIL configured and no admin user exists. "
                    "Set AUTH_SUPER_ADMIN_EMAIL environment variable to bootstrap "
                    "the first administrator."
                )


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan handler for startup and shutdown events."""
    # Startup
    await _bootstrap_super_admin()
    yield
    # Shutdown (nothing to clean up currently)


app = FastAPI(
    title="Vroom HR",
    description="Vietnamese Recruit-Onboard-Operate-Manage platform",
    version="0.1.0",
    lifespan=lifespan,
)

# Register audit logging middleware for ESS endpoints (Requirement 12.4).
app.add_middleware(ESSAuditMiddleware)

# Register module routers.
app.include_router(auth_router)
app.include_router(admin_router)
app.include_router(employee_router)
app.include_router(gmail_router)
app.include_router(candidate_router)
app.include_router(cv_review_router)
app.include_router(metrics_router)
app.include_router(leave_router)
app.include_router(attendance_router)
app.include_router(overtime_router)
app.include_router(schedule_router)
app.include_router(ess_router)
app.include_router(salary_router)
app.include_router(payroll_router)

# Register exception handlers.
register_auth_error_handlers(app)
register_employee_error_handlers(app)
register_gmail_error_handlers(app)
register_recruitment_error_handlers(app)
register_attendance_error_handlers(app)


@app.get("/health")
async def health_check() -> dict[str, str]:
    """Health check endpoint for Docker healthcheck."""
    return {"status": "ok"}
