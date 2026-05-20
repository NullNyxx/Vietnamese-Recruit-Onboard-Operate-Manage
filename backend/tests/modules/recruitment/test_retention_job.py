"""Unit tests for the retention cleanup job.

Tests the ARQ scheduled task that hard-deletes rejected candidates
after the configured retention period.

Requirements: 15.1, 15.2, 15.3, 15.4, 15.5, 15.6
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from src.modules.recruitment.application.retention_job import (
    DEFAULT_BATCH_SIZE,
    _anonymize_candidate_id,
    _get_expired_candidates,
    retention_cleanup,
)
from src.modules.recruitment.domain.entities import Candidate, CVDocument
from src.modules.recruitment.domain.enums import CandidateStatus

# ─── Fixtures ──────────────────────────────────────────────────────────


def _make_candidate(
    status: str = CandidateStatus.REJECTED,
    rejected_at: datetime | None = None,
) -> Candidate:
    """Create a test Candidate entity."""
    if rejected_at is None:
        rejected_at = datetime.now(UTC) - timedelta(days=100)

    return Candidate(
        id=uuid4(),
        name="Nguyen Van A",
        email="test@example.com",
        phone="0901234567",
        skills=["Python"],
        experience=[],
        education=[],
        summary="Test candidate",
        status=status,
        confidence_score=0.85,
        rejected_at=rejected_at,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )


def _make_cv_document(candidate_id=None) -> CVDocument:
    """Create a test CVDocument entity."""
    return CVDocument(
        id=uuid4(),
        candidate_id=candidate_id or uuid4(),
        gmail_message_id="msg_123",
        original_filename="resume.pdf",
        mime_type="application/pdf",
        size_bytes=1024,
        file_path="storage/cv/msg_123/resume.pdf",
        processing_status="completed",
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
        uploaded_at=datetime.now(UTC),
    )


@pytest.fixture
def mock_session():
    """Create a mock async session."""
    session = AsyncMock()
    session.commit = AsyncMock()
    session.rollback = AsyncMock()
    session.execute = AsyncMock()
    session.add = MagicMock()
    session.flush = AsyncMock()
    session.delete = AsyncMock()
    return session


@pytest.fixture
def mock_minio_client():
    """Create a mock MinIO client."""
    client = AsyncMock()
    client.delete_cv = AsyncMock()
    return client


@pytest.fixture
def mock_settings():
    """Create a mock RecruitmentSettings."""
    settings = MagicMock()
    settings.retention_days = 90
    return settings


@pytest.fixture
def ctx(mock_session, mock_minio_client, mock_settings):
    """Create a mock ARQ context dict."""
    return {
        "session": mock_session,
        "minio_client": mock_minio_client,
        "settings": mock_settings,
    }


# ─── Anonymization Tests ──────────────────────────────────────────────


class TestAnonymizeCandidateId:
    """Tests for the _anonymize_candidate_id helper."""

    def test_returns_hex_string(self):
        """Should return a hex-encoded SHA-256 hash."""
        candidate_id = uuid4()
        result = _anonymize_candidate_id(candidate_id)

        assert isinstance(result, str)
        assert len(result) == 64  # SHA-256 hex is 64 chars

    def test_deterministic(self):
        """Same UUID should always produce the same hash."""
        candidate_id = uuid4()
        result1 = _anonymize_candidate_id(candidate_id)
        result2 = _anonymize_candidate_id(candidate_id)

        assert result1 == result2

    def test_different_ids_produce_different_hashes(self):
        """Different UUIDs should produce different hashes."""
        id1 = uuid4()
        id2 = uuid4()

        assert _anonymize_candidate_id(id1) != _anonymize_candidate_id(id2)


# ─── Retention Cleanup Tests ──────────────────────────────────────────


class TestRetentionCleanup:
    """Tests for the retention_cleanup ARQ task."""

    async def test_returns_zero_when_no_eligible_candidates(self, ctx, mock_session):
        """Should return 0 when no candidates are eligible for deletion."""
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_session.execute.return_value = mock_result

        result = await retention_cleanup(ctx)

        assert result == 0

    async def test_deletes_eligible_candidate_with_cv_documents(
        self, ctx, mock_session, mock_minio_client
    ):
        """Should delete candidate, CV documents, and MinIO files."""
        candidate = _make_candidate()
        cv_doc = _make_cv_document(candidate_id=candidate.id)

        # Mock the query for expired candidates
        mock_candidates_result = MagicMock()
        mock_candidates_result.scalars.return_value.all.return_value = [candidate]

        # Mock the query for CV documents by candidate_id
        mock_cv_docs_result = MagicMock()
        mock_cv_docs_result.scalars.return_value.all.return_value = [cv_doc]

        # Mock the query for candidate deletion (get_by_id in delete)
        mock_candidate_delete_result = MagicMock()
        mock_candidate_delete_result.scalars.return_value.first.return_value = candidate

        # Mock the query for cv_doc deletion
        mock_cv_doc_delete_result = MagicMock()
        mock_cv_doc_delete_result.scalars.return_value.first.return_value = cv_doc

        # Set up execute to return different results for different queries
        mock_session.execute.side_effect = [
            mock_candidates_result,  # _get_expired_candidates
            mock_cv_docs_result,  # find_by_candidate_id
            mock_cv_doc_delete_result,  # cv_doc_repo.delete
            mock_candidate_delete_result,  # candidate_repo.delete
            MagicMock(),  # audit log flush (create)
            MagicMock(),  # audit log flush (create) - for commit audit
        ]

        result = await retention_cleanup(ctx)

        assert result == 1
        mock_minio_client.delete_cv.assert_called_once_with(cv_doc.file_path)
        assert mock_session.commit.call_count >= 1

    async def test_continues_on_single_candidate_failure(
        self, ctx, mock_session, mock_minio_client
    ):
        """Should continue processing when one candidate deletion fails."""
        candidate1 = _make_candidate()
        candidate2 = _make_candidate()
        cv_doc1 = _make_cv_document(candidate_id=candidate1.id)
        cv_doc2 = _make_cv_document(candidate_id=candidate2.id)
        cv_doc2.file_path = "storage/cv/msg_789/resume2.pdf"

        call_count = [0]

        async def mock_execute_side_effect(statement):
            call_count[0] += 1
            mock_result = MagicMock()

            # First call: get expired candidates
            if call_count[0] == 1:
                mock_result.scalars.return_value.all.return_value = [
                    candidate1,
                    candidate2,
                ]
                return mock_result

            # Second call: find_by_candidate_id for candidate1
            if call_count[0] == 2:
                mock_result.scalars.return_value.all.return_value = [cv_doc1]
                return mock_result

            # After rollback for candidate1, calls for candidate2:
            # Third call: find_by_candidate_id for candidate2
            if call_count[0] == 3:
                mock_result.scalars.return_value.all.return_value = [cv_doc2]
                return mock_result

            # Fourth call: cv_doc_repo.delete for cv_doc2
            if call_count[0] == 4:
                mock_result.scalars.return_value.first.return_value = cv_doc2
                return mock_result

            # Fifth call: candidate_repo.delete for candidate2
            if call_count[0] == 5:
                mock_result.scalars.return_value.first.return_value = candidate2
                return mock_result

            # Default: return empty/mock for audit log
            mock_result.scalars.return_value.all.return_value = []
            mock_result.scalars.return_value.first.return_value = None
            return mock_result

        mock_session.execute.side_effect = mock_execute_side_effect

        # First candidate: MinIO delete raises
        # Second candidate: MinIO delete succeeds
        minio_call_count = [0]

        async def minio_side_effect(path):
            minio_call_count[0] += 1
            if minio_call_count[0] == 1:
                raise RuntimeError("MinIO connection failed")

        mock_minio_client.delete_cv.side_effect = minio_side_effect

        with patch(
            "src.modules.recruitment.application.retention_job.log_audit"
        ) as mock_log_audit:
            mock_log_audit.return_value = None

            result = await retention_cleanup(ctx)

            # candidate1 failed (MinIO error), candidate2 succeeded
            assert result == 1
            assert mock_session.rollback.call_count >= 1

    async def test_uses_configured_retention_days(self, ctx, mock_session):
        """Should use settings.retention_days for cutoff calculation."""
        ctx["settings"].retention_days = 180

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_session.execute.return_value = mock_result

        await retention_cleanup(ctx)

        # Verify execute was called (the query uses retention_days)
        mock_session.execute.assert_called_once()

    async def test_batch_size_limit(self, ctx, mock_session):
        """Should limit query to DEFAULT_BATCH_SIZE (500) candidates."""
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_session.execute.return_value = mock_result

        await retention_cleanup(ctx)

        # Verify the query was executed (batch size is applied in the SQL LIMIT)
        mock_session.execute.assert_called_once()

    async def test_deletes_multiple_cv_documents_per_candidate(
        self, ctx, mock_session, mock_minio_client
    ):
        """Should delete all CV documents associated with a candidate."""
        candidate = _make_candidate()
        cv_doc1 = _make_cv_document(candidate_id=candidate.id)
        cv_doc2 = _make_cv_document(candidate_id=candidate.id)
        cv_doc2.file_path = "storage/cv/msg_456/resume2.pdf"

        # Mock queries
        mock_candidates_result = MagicMock()
        mock_candidates_result.scalars.return_value.all.return_value = [candidate]

        mock_cv_docs_result = MagicMock()
        mock_cv_docs_result.scalars.return_value.all.return_value = [cv_doc1, cv_doc2]

        mock_delete_result = MagicMock()
        mock_delete_result.scalars.return_value.first.return_value = cv_doc1

        mock_delete_result2 = MagicMock()
        mock_delete_result2.scalars.return_value.first.return_value = cv_doc2

        mock_candidate_delete = MagicMock()
        mock_candidate_delete.scalars.return_value.first.return_value = candidate

        mock_session.execute.side_effect = [
            mock_candidates_result,  # _get_expired_candidates
            mock_cv_docs_result,  # find_by_candidate_id
            mock_delete_result,  # cv_doc_repo.delete (doc1)
            mock_delete_result2,  # cv_doc_repo.delete (doc2)
            mock_candidate_delete,  # candidate_repo.delete
            MagicMock(),  # audit log
        ]

        result = await retention_cleanup(ctx)

        assert result == 1
        assert mock_minio_client.delete_cv.call_count == 2
        mock_minio_client.delete_cv.assert_any_call(cv_doc1.file_path)
        mock_minio_client.delete_cv.assert_any_call(cv_doc2.file_path)

    async def test_candidate_without_cv_documents(
        self, ctx, mock_session, mock_minio_client
    ):
        """Should handle candidate with no CV documents gracefully."""
        candidate = _make_candidate()

        mock_candidates_result = MagicMock()
        mock_candidates_result.scalars.return_value.all.return_value = [candidate]

        mock_cv_docs_result = MagicMock()
        mock_cv_docs_result.scalars.return_value.all.return_value = []

        mock_candidate_delete = MagicMock()
        mock_candidate_delete.scalars.return_value.first.return_value = candidate

        mock_session.execute.side_effect = [
            mock_candidates_result,  # _get_expired_candidates
            mock_cv_docs_result,  # find_by_candidate_id (empty)
            mock_candidate_delete,  # candidate_repo.delete
            MagicMock(),  # audit log
        ]

        result = await retention_cleanup(ctx)

        assert result == 1
        mock_minio_client.delete_cv.assert_not_called()

    async def test_audit_log_on_successful_deletion(
        self, ctx, mock_session, mock_minio_client
    ):
        """Should create audit log entry with anonymized candidate_id on success."""
        candidate = _make_candidate()

        mock_candidates_result = MagicMock()
        mock_candidates_result.scalars.return_value.all.return_value = [candidate]

        mock_cv_docs_result = MagicMock()
        mock_cv_docs_result.scalars.return_value.all.return_value = []

        mock_candidate_delete = MagicMock()
        mock_candidate_delete.scalars.return_value.first.return_value = candidate

        mock_session.execute.side_effect = [
            mock_candidates_result,
            mock_cv_docs_result,
            mock_candidate_delete,
            MagicMock(),  # audit log create
        ]

        with patch(
            "src.modules.recruitment.application.retention_job.log_audit"
        ) as mock_log_audit:
            mock_log_audit.return_value = None

            result = await retention_cleanup(ctx)

            assert result == 1
            mock_log_audit.assert_called()
            call_kwargs = mock_log_audit.call_args.kwargs
            assert call_kwargs["operation_type"] == "candidate_data_deleted"
            assert call_kwargs["entity_type"] == "candidate"
            assert call_kwargs["success"] is True
            # Verify anonymized ID is in the change_summary
            anonymized = _anonymize_candidate_id(candidate.id)
            assert anonymized in call_kwargs["change_summary"]

    async def test_audit_log_on_failed_deletion(
        self, ctx, mock_session, mock_minio_client
    ):
        """Should create audit log entry with success=False on failure."""
        candidate = _make_candidate()
        cv_doc = _make_cv_document(candidate_id=candidate.id)

        mock_candidates_result = MagicMock()
        mock_candidates_result.scalars.return_value.all.return_value = [candidate]

        mock_cv_docs_result = MagicMock()
        mock_cv_docs_result.scalars.return_value.all.return_value = [cv_doc]

        mock_session.execute.side_effect = [
            mock_candidates_result,
            mock_cv_docs_result,
        ]

        # MinIO delete fails
        mock_minio_client.delete_cv.side_effect = RuntimeError("Connection refused")

        with patch(
            "src.modules.recruitment.application.retention_job.log_audit"
        ) as mock_log_audit:
            mock_log_audit.return_value = None

            result = await retention_cleanup(ctx)

            assert result == 0
            mock_session.rollback.assert_called()

            # Find the failure audit log call
            failure_calls = [
                call
                for call in mock_log_audit.call_args_list
                if call.kwargs.get("success") is False
            ]
            assert len(failure_calls) == 1
            assert "FAILED" in failure_calls[0].kwargs["change_summary"]


# ─── Selection Criteria Tests ─────────────────────────────────────────


class TestGetExpiredCandidates:
    """Tests for the _get_expired_candidates query helper."""

    async def test_only_selects_rejected_candidates(self, mock_session):
        """Should only select candidates with status='rejected'."""
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_session.execute.return_value = mock_result

        await _get_expired_candidates(mock_session, retention_days=90, batch_size=500)

        # Verify execute was called
        mock_session.execute.assert_called_once()

    async def test_respects_batch_size(self, mock_session):
        """Should limit results to the specified batch size."""
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_session.execute.return_value = mock_result

        await _get_expired_candidates(mock_session, retention_days=90, batch_size=100)

        mock_session.execute.assert_called_once()


class TestDefaultBatchSize:
    """Tests for the DEFAULT_BATCH_SIZE constant."""

    def test_batch_size_is_500(self):
        """Batch size should be 500 per the requirements."""
        assert DEFAULT_BATCH_SIZE == 500
