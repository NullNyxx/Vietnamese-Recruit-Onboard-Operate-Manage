"""Vroom HR Backend - FastAPI application entrypoint."""

from dotenv import load_dotenv

# Load .env file before any settings are instantiated.
load_dotenv()

from fastapi import FastAPI

from src.modules.employee.api.error_handler import register_employee_error_handlers
from src.modules.employee.api.router import router as employee_router
from src.modules.gmail.api.error_handler import register_gmail_error_handlers
from src.modules.gmail.api.router import router as gmail_router
from src.modules.identity.api.error_handler import register_auth_error_handlers
from src.modules.identity.api.router import router as auth_router
from src.modules.recruitment.api.candidate_router import candidate_router
from src.modules.recruitment.api.cv_review_router import cv_review_router
from src.modules.recruitment.api.error_handler import register_recruitment_error_handlers
from src.modules.recruitment.api.metrics_router import metrics_router

app = FastAPI(
    title="Vroom HR",
    description="Vietnamese Recruit-Onboard-Operate-Manage platform",
    version="0.1.0",
)

# Register module routers.
app.include_router(auth_router)
app.include_router(employee_router)
app.include_router(gmail_router)
app.include_router(candidate_router)
app.include_router(cv_review_router)
app.include_router(metrics_router)

# Register exception handlers.
register_auth_error_handlers(app)
register_employee_error_handlers(app)
register_gmail_error_handlers(app)
register_recruitment_error_handlers(app)


@app.get("/health")
async def health_check() -> dict[str, str]:
    """Health check endpoint for Docker healthcheck."""
    return {"status": "ok"}
