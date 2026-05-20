"""Unit tests for AuditRepository and log_audit helper.

Tests cover:
- AuditRepository CRUD and query operations
- log_audit PII redaction on change_summary
- log_audit graceful failure handling
"""

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from src.modules.recruitment.domain.entities import RecruitmentAuditLog
from src.modules.recruitment.infrastructure.audit_repository import (
    AuditRepository,
    log_audit,
)


@pytest.fixture
def mock_session() -> AsyncMock:
    """Create a mock AsyncSession for testing."""
    session = AsyncMock()
    session.add = MagicMock()
    session.flush = AsyncMock()
    return session


@pytest.fixture
def sample_audit_log() -> RecruitmentAuditLog:
    """Create a sample audit log entry for testing."""
    return RecruitmentAuditLog(
        operation_type="candidate_rejected",
        entity_type="candidate",
        entity_id=uuid4(),
        user_id=uuid4(),
        change_summary="Candidate rejected by HR",
        success=True,
    )


class TestAuditRepositoryCreate:
    """Tests for AuditRepository.create method."""

    async def test_create_adds_and_flushes(
        self, mock_session: AsyncMock, sample_audit_log: RecruitmentAuditLog
    ):
        """create() should add the entity to session and flush."""
        repo = AuditRepository(mock_session)
        result = await repo.create(sample_audit_log)

        mock_session.add.assert_called_once_with(sample_audit_log)
        mock_session.flush.assert_awaited_once()
        assert result is sample_audit_log

    async def test_create_returns_the_log_entry(
        self, mock_session: AsyncMock
    ):
        """create() should return the persisted log entry."""
        log = RecruitmentAuditLog(
            operation_type="cv_parse",
            entity_type="cv_document",
            model_name="NullNyx-Combo",
            token_usage={"prompt_tokens": 100, "completion_tokens": 50},
            latency_ms=1500,
            success=True,
        )
        repo = AuditRepository(mock_session)
        result = await repo.create(log)

        assert result.operation_type == "cv_parse"
        assert result.model_name == "NullNyx-Combo"
        assert result.latency_ms == 1500


class TestAuditRepositoryFindByEntityId:
    """Tests for AuditRepository.find_by_entity_id method."""

    async def test_find_by_entity_id_executes_query(self, mock_session: AsyncMock):
        """find_by_entity_id() should execute a select query filtered by entity_id."""
        entity_id = uuid4()
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = []
        mock_result = MagicMock()
        mock_result.scalars.return_value = mock_scalars
        mock_session.execute.return_value = mock_result

        repo = AuditRepository(mock_session)
        result = await repo.find_by_entity_id(entity_id)

        mock_session.execute.assert_awaited_once()
        assert result == []

    async def test_find_by_entity_id_returns_matching_logs(self, mock_session: AsyncMock):
        """find_by_entity_id() should return all logs matching the entity_id."""
        entity_id = uuid4()
        log1 = RecruitmentAuditLog(
            operation_type="cv_parse", entity_type="cv_document", entity_id=entity_id
        )
        log2 = RecruitmentAuditLog(
            operation_type="candidate_created", entity_type="candidate", entity_id=entity_id
        )

        mock_scalars = MagicMock()
        mock_scalars.all.return_value = [log1, log2]
        mock_result = MagicMock()
        mock_result.scalars.return_value = mock_scalars
        mock_session.execute.return_value = mock_result

        repo = AuditRepository(mock_session)
        result = await repo.find_by_entity_id(entity_id)

        assert len(result) == 2
        assert result[0] is log1
        assert result[1] is log2


class TestAuditRepositoryFindByUserId:
    """Tests for AuditRepository.find_by_user_id method."""

    async def test_find_by_user_id_returns_paginated_results(self, mock_session: AsyncMock):
        """find_by_user_id() should return paginated results with total count."""
        user_id = uuid4()
        log1 = RecruitmentAuditLog(
            operation_type="candidate_rejected", entity_type="candidate", user_id=user_id
        )

        # Mock count query
        mock_count_result = MagicMock()
        mock_count_result.scalar.return_value = 5

        # Mock data query
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = [log1]
        mock_data_result = MagicMock()
        mock_data_result.scalars.return_value = mock_scalars

        mock_session.execute.side_effect = [mock_count_result, mock_data_result]

        repo = AuditRepository(mock_session)
        results, total = await repo.find_by_user_id(user_id, page=1, page_size=20)

        assert total == 5
        assert len(results) == 1
        assert results[0] is log1

    async def test_find_by_user_id_with_pagination(self, mock_session: AsyncMock):
        """find_by_user_id() should respect page and page_size parameters."""
        user_id = uuid4()

        mock_count_result = MagicMock()
        mock_count_result.scalar.return_value = 0

        mock_scalars = MagicMock()
        mock_scalars.all.return_value = []
        mock_data_result = MagicMock()
        mock_data_result.scalars.return_value = mock_scalars

        mock_session.execute.side_effect = [mock_count_result, mock_data_result]

        repo = AuditRepository(mock_session)
        results, total = await repo.find_by_user_id(user_id, page=3, page_size=10)

        assert total == 0
        assert results == []


class TestAuditRepositoryFindByOperationType:
    """Tests for AuditRepository.find_by_operation_type method."""

    async def test_find_by_operation_type_returns_matching_logs(self, mock_session: AsyncMock):
        """find_by_operation_type() should return logs matching the operation type."""
        log1 = RecruitmentAuditLog(
            operation_type="intent_classify", entity_type="email_message"
        )

        mock_scalars = MagicMock()
        mock_scalars.all.return_value = [log1]
        mock_result = MagicMock()
        mock_result.scalars.return_value = mock_scalars
        mock_session.execute.return_value = mock_result

        repo = AuditRepository(mock_session)
        result = await repo.find_by_operation_type("intent_classify")

        assert len(result) == 1
        assert result[0].operation_type == "intent_classify"


class TestAuditRepositoryFindByTimestampRange:
    """Tests for AuditRepository.find_by_timestamp_range method."""

    async def test_find_by_timestamp_range_returns_matching_logs(self, mock_session: AsyncMock):
        """find_by_timestamp_range() should return logs within the time range."""
        now = datetime.now(UTC)
        start = now - timedelta(days=7)
        end = now

        log1 = RecruitmentAuditLog(
            operation_type="cv_parse", entity_type="cv_document"
        )

        mock_scalars = MagicMock()
        mock_scalars.all.return_value = [log1]
        mock_result = MagicMock()
        mock_result.scalars.return_value = mock_scalars
        mock_session.execute.return_value = mock_result

        repo = AuditRepository(mock_session)
        result = await repo.find_by_timestamp_range(start, end)

        assert len(result) == 1
        mock_session.execute.assert_awaited_once()


class TestLogAuditHelper:
    """Tests for the log_audit helper function."""

    async def test_log_audit_creates_entry(self, mock_session: AsyncMock):
        """log_audit() should create a RecruitmentAuditLog entry."""
        entity_id = uuid4()
        user_id = uuid4()

        result = await log_audit(
            session=mock_session,
            operation_type="candidate_rejected",
            entity_type="candidate",
            entity_id=entity_id,
            user_id=user_id,
            change_summary="Candidate rejected due to lack of experience",
            success=True,
        )

        assert result is not None
        assert result.operation_type == "candidate_rejected"
        assert result.entity_type == "candidate"
        assert result.entity_id == entity_id
        assert result.user_id == user_id
        assert result.success is True
        mock_session.add.assert_called_once()
        mock_session.flush.assert_awaited_once()

    async def test_log_audit_redacts_pii_from_change_summary(self, mock_session: AsyncMock):
        """log_audit() should apply PII redaction to change_summary (Req 17.3)."""
        # change_summary contains a CCCD number (12 digits)
        result = await log_audit(
            session=mock_session,
            operation_type="candidate_created",
            entity_type="candidate",
            change_summary="Created candidate with CCCD 012345678901",
        )

        assert result is not None
        assert "012345678901" not in (result.change_summary or "")
        assert "[REDACTED]" in (result.change_summary or "")

    async def test_log_audit_redacts_salary_from_change_summary(self, mock_session: AsyncMock):
        """log_audit() should redact salary figures from change_summary."""
        result = await log_audit(
            session=mock_session,
            operation_type="candidate_updated",
            entity_type="candidate",
            change_summary="Updated salary expectation: 15 triệu",
        )

        assert result is not None
        assert "15 triệu" not in (result.change_summary or "")
        assert "[REDACTED]" in (result.change_summary or "")

    async def test_log_audit_redacts_bank_account_from_change_summary(
        self, mock_session: AsyncMock
    ):
        """log_audit() should redact bank account numbers from change_summary."""
        result = await log_audit(
            session=mock_session,
            operation_type="candidate_updated",
            entity_type="candidate",
            change_summary="Bank account: 19036482751",
        )

        assert result is not None
        assert "19036482751" not in (result.change_summary or "")
        assert "[REDACTED]" in (result.change_summary or "")

    async def test_log_audit_preserves_non_pii_change_summary(self, mock_session: AsyncMock):
        """log_audit() should preserve change_summary text that has no PII."""
        result = await log_audit(
            session=mock_session,
            operation_type="candidate_archived",
            entity_type="candidate",
            change_summary="Status changed from new to archived",
        )

        assert result is not None
        assert result.change_summary == "Status changed from new to archived"

    async def test_log_audit_handles_none_change_summary(self, mock_session: AsyncMock):
        """log_audit() should handle None change_summary gracefully."""
        result = await log_audit(
            session=mock_session,
            operation_type="cv_parse",
            entity_type="cv_document",
            change_summary=None,
        )

        assert result is not None
        assert result.change_summary is None

    async def test_log_audit_stores_llm_metadata(self, mock_session: AsyncMock):
        """log_audit() should store model_name, token_usage, and latency_ms."""
        result = await log_audit(
            session=mock_session,
            operation_type="cv_parse",
            entity_type="cv_document",
            model_name="NullNyx-Combo",
            token_usage={"prompt_tokens": 500, "completion_tokens": 200},
            latency_ms=2500,
            success=True,
        )

        assert result is not None
        assert result.model_name == "NullNyx-Combo"
        assert result.token_usage == {"prompt_tokens": 500, "completion_tokens": 200}
        assert result.latency_ms == 2500

    async def test_log_audit_graceful_failure_does_not_raise(self, mock_session: AsyncMock):
        """log_audit() should not raise if audit logging fails (Req 17.5)."""
        mock_session.flush.side_effect = Exception("Database connection lost")

        result = await log_audit(
            session=mock_session,
            operation_type="candidate_rejected",
            entity_type="candidate",
            entity_id=uuid4(),
        )

        # Should return None instead of raising
        assert result is None

    async def test_log_audit_graceful_failure_logs_error(self, mock_session: AsyncMock):
        """log_audit() should log the error when audit logging fails."""
        mock_session.flush.side_effect = Exception("Database connection lost")

        with patch(
            "src.modules.recruitment.infrastructure.audit_repository.logger"
        ) as mock_logger:
            await log_audit(
                session=mock_session,
                operation_type="candidate_rejected",
                entity_type="candidate",
                entity_id=uuid4(),
            )

            mock_logger.error.assert_called_once()

    async def test_log_audit_with_previous_and_new_value(self, mock_session: AsyncMock):
        """log_audit() should store previous_value and new_value dicts."""
        result = await log_audit(
            session=mock_session,
            operation_type="candidate_updated",
            entity_type="candidate",
            previous_value={"status": "new"},
            new_value={"status": "reviewing"},
        )

        assert result is not None
        assert result.previous_value == {"status": "new"}
        assert result.new_value == {"status": "reviewing"}

    async def test_log_audit_default_success_is_true(self, mock_session: AsyncMock):
        """log_audit() should default success to True."""
        result = await log_audit(
            session=mock_session,
            operation_type="intent_classify",
            entity_type="email_message",
        )

        assert result is not None
        assert result.success is True

    async def test_log_audit_can_record_failure(self, mock_session: AsyncMock):
        """log_audit() should allow recording failed operations."""
        result = await log_audit(
            session=mock_session,
            operation_type="cv_parse",
            entity_type="cv_document",
            success=False,
            change_summary="LLM parse failed: timeout",
        )

        assert result is not None
        assert result.success is False
        assert result.change_summary == "LLM parse failed: timeout"
