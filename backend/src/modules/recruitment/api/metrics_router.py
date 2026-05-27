"""FastAPI router for recruitment pipeline metrics.

Exposes GET /api/recruitment/metrics endpoint that returns rolling
24-hour processing metrics calculated from CVDocument records.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import col, select

from src.modules.identity.container import get_current_user, get_db_session
from src.modules.identity.domain.entities import User
from src.modules.recruitment.api.schemas import MetricsResponse
from src.modules.recruitment.domain.entities import CVDocument

# ---------------------------------------------------------------------------
# Type aliases
# ---------------------------------------------------------------------------

CurrentUserDep = Annotated[User, Depends(get_current_user)]
DbSessionDep = Annotated[AsyncSession, Depends(get_db_session)]

# ---------------------------------------------------------------------------
# Router
# ---------------------------------------------------------------------------

metrics_router = APIRouter(prefix="/api/recruitment", tags=["recruitment-metrics"])


@metrics_router.get("/metrics", response_model=MetricsResponse)
async def get_metrics(
    current_user: CurrentUserDep,
    session: DbSessionDep,
) -> MetricsResponse:
    """Return rolling 24-hour CV processing pipeline metrics.

    Calculates:
    - average_processing_time_ms: average elapsed time from created_at to
      updated_at for documents that reached a terminal status (completed,
      failed, needs_review) in the last 24 hours.
    - success_rate: percentage of completed documents out of all processed
      (completed + failed + needs_review) in the last 24 hours.
    - failure_rate: percentage of failed documents out of all processed
      in the last 24 hours.
    - queue_depth: count of documents currently in an active processing
      state (pending, ocr_processing, llm_parsing).

    Returns zeros when no documents have been processed in the window.
    """
    now = datetime.now(UTC)
    window_start = now - timedelta(hours=24)

    # Terminal statuses considered as "processed" in the last 24h
    terminal_statuses = ("completed", "failed", "needs_review")
    # Active processing statuses for queue depth
    active_statuses = ("pending", "ocr_processing", "llm_parsing")

    # --- Counts by terminal status in the 24h window ---
    counts_stmt = (
        select(
            col(CVDocument.processing_status),
            func.count().label("cnt"),
        )
        .where(
            col(CVDocument.processing_status).in_(terminal_statuses),
            col(CVDocument.updated_at) >= window_start,
        )
        .group_by(col(CVDocument.processing_status))
    )
    counts_result = await session.execute(counts_stmt)
    status_counts: dict[str, int] = {row.processing_status: row.cnt for row in counts_result}

    completed_count = status_counts.get("completed", 0)
    failed_count = status_counts.get("failed", 0)
    needs_review_count = status_counts.get("needs_review", 0)
    total_processed = completed_count + failed_count + needs_review_count

    # --- Success and failure rates ---
    if total_processed > 0:
        success_rate = completed_count / total_processed
        failure_rate = failed_count / total_processed
    else:
        success_rate = 0.0
        failure_rate = 0.0

    # --- Average processing time (ms) for terminal documents in window ---
    avg_time_stmt = select(
        func.avg(
            func.extract("epoch", col(CVDocument.updated_at))
            - func.extract("epoch", col(CVDocument.created_at))
        ).label("avg_seconds")
    ).where(
        col(CVDocument.processing_status).in_(terminal_statuses),
        col(CVDocument.updated_at) >= window_start,
    )
    avg_result = await session.execute(avg_time_stmt)
    avg_seconds = avg_result.scalar()
    average_processing_time_ms = (avg_seconds * 1000.0) if avg_seconds else 0.0

    # --- Queue depth: documents currently in active processing ---
    queue_stmt = select(func.count()).where(
        col(CVDocument.processing_status).in_(active_statuses),
    )
    queue_result = await session.execute(queue_stmt)
    queue_depth = queue_result.scalar() or 0

    return MetricsResponse(
        average_processing_time_ms=round(average_processing_time_ms, 2),
        success_rate=round(success_rate, 4),
        failure_rate=round(failure_rate, 4),
        queue_depth=queue_depth,
    )
