"""Vroom HR Backend - FastAPI application entrypoint."""

from fastapi import FastAPI

app = FastAPI(
    title="Vroom HR",
    description="Vietnamese Recruit-Onboard-Operate-Manage platform",
    version="0.1.0",
)


@app.get("/health")
async def health_check() -> dict[str, str]:
    """Health check endpoint for Docker healthcheck."""
    return {"status": "ok"}
