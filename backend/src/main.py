"""Vroom HR Backend - FastAPI application entrypoint."""

from dotenv import load_dotenv

# Load .env file before any settings are instantiated.
load_dotenv()

from fastapi import FastAPI

from src.modules.identity.api.error_handler import register_auth_error_handlers
from src.modules.identity.api.router import router as auth_router

app = FastAPI(
    title="Vroom HR",
    description="Vietnamese Recruit-Onboard-Operate-Manage platform",
    version="0.1.0",
)

# Register module routers.
app.include_router(auth_router)

# Register exception handlers.
register_auth_error_handlers(app)


@app.get("/health")
async def health_check() -> dict[str, str]:
    """Health check endpoint for Docker healthcheck."""
    return {"status": "ok"}
