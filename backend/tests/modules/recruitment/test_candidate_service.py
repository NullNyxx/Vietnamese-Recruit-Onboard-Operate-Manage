"""Unit tests for CandidateService — status transitions and actions.

Tests the candidate lifecycle state machine, reject, accept, archive,
schedule_interview, and send_email_to_candidate operations.

Requirements: 9.1-9.7, 10.1-10.8, 11.1-11.6, 12.1-12.5, 13.1-13.6
"""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from src.modules.recruitment.application.candidate_service import (
    VALID_TRANSITIONS,
    CandidateService,
)
from src.modules.recruitment.domain.entities import Candidate
from src.modules.recruitment.domain.enums import CandidateStatus
from src.modules.recruitment.domain.exceptions import (
    CandidateNotFoundError,
    GmailNotConnectedError,
    InvalidStatusTransitionError,
)


# ─── Fixtures ──────────────────────────────────────────────────────────


@pytest.fixture
def mock_minio_client():
    """Create a mock MinIO client."""
    return AsyncMock()


@pytest.fixture
def mock_candidate_repo():
    """Create a mock candidate repository."""
    repo = AsyncMock()
    repo.update = AsyncMock(side_effect=lambda c: c)
    return repo


@pytest.fixture
def mock_cv_document_repo():
    """Create a mock CV document repository."""
    return AsyncMock()


@pytest.fixture
def mock_session():
    """Create a mock async session."""
    session = AsyncMock()
    session.commit = AsyncMock()
    session.execute = AsyncMock()
    return session


@pytest.fixture
def mock_gmail_sender():
    """Create a mock Gmail sender."""
    sender = AsyncMock()
    sender.send_email = AsyncMock()
    return sender


@pytest.fixture
def mock_gmail_checker():
    """Create a mock Gmail connection checker."""
    checker = AsyncMock()
    checker.is_connected = AsyncMock(return_value=True)
    return checker


@pytest.fixture
def mock_event_publisher():
    """Create a mock domain event publisher."""
    publisher = AsyncMock()
    publisher.publish = AsyncMock()
    return publisher


@pytest.fixture
def user_id():
    """Create a test user ID."""
    return uuid4()


@pytest.fixture
def service(
    mock_candidate_repo,
    mock_cv_document_repo,
    mock_minio_client,
    mock_session,
    mock_gmail_sender,
    mock_gmail_checker,
    mock_event_publisher,
    user_id,
):
    """Create a CandidateService with all mocked dependencies."""
    return CandidateService(
        candidate_repo=mock_candidate_repo,
        cv_document_repo=mock_cv_document_repo,
        minio_client=mock_minio_client,
        session=mock_session,
        gmail_sender=mock_gmail_sender,
        gmail_checker=mock_gmail_checker,
        event_publisher=mock_event_publisher,
        user_id=user_id,
    )


def _make_candidate(
    status: str = CandidateStatus.NEW,
    email: str = "test@example.com",
) -> Candidate:
    """Create a test Candidate entity with given status."""
    return Candidate(
        id=uuid4(),
        name="Nguyen Van A",
        email=email,
        phone="0901234567",
        skills=["Python"],
        experience=[],
        education=[],
        summary="Test candidate",
        status=status,
        confidence_score=0.85,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )


# ─── State Machine Validation Tests ───────────────────────────────────


class TestStateTransitions:
    """Tests for the candidate status state machine."""

    def test_valid_transitions_from_new(self):
        """new → reviewing, interview_scheduled, rejected, archived."""
        expected = {
            CandidateStatus.REVIEWING,
            CandidateStatus.INTERVIEW_SCHEDULED,
            CandidateStatus.REJECTED,
            CandidateStatus.ARCHIVED,
        }
        assert VALID_TRANSITIONS[CandidateStatus.NEW] == expected

    def test_valid_transitions_from_reviewing(self):
        """reviewing → interview_scheduled, accepted, rejected, archived."""
        expected = {
            CandidateStatus.INTERVIEW_SCHEDULED,
            CandidateStatus.ACCEPTED,
            CandidateStatus.REJECTED,
            CandidateStatus.ARCHIVED,
        }
        assert VALID_TRANSITIONS[CandidateStatus.REVIEWING] == expected

    def test_valid_transitions_from_interview_scheduled(self):
        """interview_scheduled → accepted, rejected, archived."""
        expected = {
            CandidateStatus.ACCEPTED,
            CandidateStatus.REJECTED,
            CandidateStatus.ARCHIVED,
        }
        assert VALID_TRANSITIONS[CandidateStatus.INTERVIEW_SCHEDULED] == expected

    def test_no_transitions_from_accepted(self):
        """accepted → (no transitions)."""
        assert VALID_TRANSITIONS[CandidateStatus.ACCEPTED] == set()

    def test_no_transitions_from_rejected(self):
        """rejected → (no transitions)."""
        assert VALID_TRANSITIONS[CandidateStatus.REJECTED] == set()

    def test_no_transitions_from_archived(self):
        """archived → (no transitions except idempotent re-archive)."""
        assert VALID_TRANSITIONS[CandidateStatus.ARCHIVED] == set()


# ─── Reject Candidate Tests ───────────────────────────────────────────


class TestRejectCandidate:
    """Tests for reject_candidate action."""

    @pytest.mark.parametrize(
        "initial_status",
        [CandidateStatus.NEW, CandidateStatus.REVIEWING, CandidateStatus.INTERVIEW_SCHEDULED],
    )
    async def test_reject_from_valid_statuses(
        self, service, mock_candidate_repo, initial_status
    ):
        """Should transition to rejected from new, reviewing, interview_scheduled."""
        candidate = _make_candidate(status=initial_status)
        mock_candidate_repo.get_by_id.return_value = candidate

        result = await service.reject_candidate(candidate.id, reason="Not qualified")

        assert result.status == CandidateStatus.REJECTED
        assert result.rejection_reason == "Not qualified"
        assert result.rejected_at is not None

    async def test_reject_stores_reason(self, service, mock_candidate_repo):
        """Should store the rejection reason."""
        candidate = _make_candidate(status=CandidateStatus.NEW)
        mock_candidate_repo.get_by_id.return_value = candidate

        result = await service.reject_candidate(
            candidate.id, reason="Insufficient experience"
        )

        assert result.rejection_reason == "Insufficient experience"

    async def test_reject_without_reason(self, service, mock_candidate_repo):
        """Should allow rejection without a reason."""
        candidate = _make_candidate(status=CandidateStatus.NEW)
        mock_candidate_repo.get_by_id.return_value = candidate

        result = await service.reject_candidate(candidate.id, reason=None)

        assert result.status == CandidateStatus.REJECTED
        assert result.rejection_reason is None

    async def test_reject_from_rejected_raises(self, service, mock_candidate_repo):
        """Should raise InvalidStatusTransitionError from rejected status."""
        candidate = _make_candidate(status=CandidateStatus.REJECTED)
        mock_candidate_repo.get_by_id.return_value = candidate

        with pytest.raises(InvalidStatusTransitionError) as exc_info:
            await service.reject_candidate(candidate.id)

        assert exc_info.value.current_status == CandidateStatus.REJECTED
        assert exc_info.value.attempted_action == "reject"

    async def test_reject_from_archived_raises(self, service, mock_candidate_repo):
        """Should raise InvalidStatusTransitionError from archived status."""
        candidate = _make_candidate(status=CandidateStatus.ARCHIVED)
        mock_candidate_repo.get_by_id.return_value = candidate

        with pytest.raises(InvalidStatusTransitionError):
            await service.reject_candidate(candidate.id)

    async def test_reject_from_accepted_raises(self, service, mock_candidate_repo):
        """Should raise InvalidStatusTransitionError from accepted status."""
        candidate = _make_candidate(status=CandidateStatus.ACCEPTED)
        mock_candidate_repo.get_by_id.return_value = candidate

        with pytest.raises(InvalidStatusTransitionError):
            await service.reject_candidate(candidate.id)

    async def test_reject_nonexistent_candidate_raises(
        self, service, mock_candidate_repo
    ):
        """Should raise CandidateNotFoundError for nonexistent candidate."""
        mock_candidate_repo.get_by_id.return_value = None

        with pytest.raises(CandidateNotFoundError):
            await service.reject_candidate(uuid4())


# ─── Accept Candidate Tests ───────────────────────────────────────────


class TestAcceptCandidate:
    """Tests for accept_candidate action."""

    @pytest.mark.parametrize(
        "initial_status",
        [CandidateStatus.REVIEWING, CandidateStatus.INTERVIEW_SCHEDULED],
    )
    async def test_accept_from_valid_statuses(
        self, service, mock_candidate_repo, initial_status
    ):
        """Should transition to accepted from reviewing and interview_scheduled."""
        candidate = _make_candidate(status=initial_status)
        mock_candidate_repo.get_by_id.return_value = candidate

        result = await service.accept_candidate(candidate.id)

        assert result.status == CandidateStatus.ACCEPTED
        assert result.accepted_at is not None

    async def test_accept_emits_domain_event(
        self, service, mock_candidate_repo, mock_event_publisher
    ):
        """Should emit candidate_accepted domain event."""
        candidate = _make_candidate(status=CandidateStatus.INTERVIEW_SCHEDULED)
        mock_candidate_repo.get_by_id.return_value = candidate

        await service.accept_candidate(candidate.id)

        mock_event_publisher.publish.assert_called_once_with(
            event_type="candidate_accepted",
            payload={
                "candidate_id": str(candidate.id),
                "name": candidate.name,
                "email": candidate.email,
            },
        )

    async def test_accept_from_new_raises(self, service, mock_candidate_repo):
        """Should raise InvalidStatusTransitionError from new status."""
        candidate = _make_candidate(status=CandidateStatus.NEW)
        mock_candidate_repo.get_by_id.return_value = candidate

        with pytest.raises(InvalidStatusTransitionError) as exc_info:
            await service.accept_candidate(candidate.id)

        assert exc_info.value.current_status == CandidateStatus.NEW
        assert exc_info.value.attempted_action == "accept"

    async def test_accept_from_rejected_raises(self, service, mock_candidate_repo):
        """Should raise InvalidStatusTransitionError from rejected status."""
        candidate = _make_candidate(status=CandidateStatus.REJECTED)
        mock_candidate_repo.get_by_id.return_value = candidate

        with pytest.raises(InvalidStatusTransitionError):
            await service.accept_candidate(candidate.id)

    async def test_accept_from_archived_raises(self, service, mock_candidate_repo):
        """Should raise InvalidStatusTransitionError from archived status."""
        candidate = _make_candidate(status=CandidateStatus.ARCHIVED)
        mock_candidate_repo.get_by_id.return_value = candidate

        with pytest.raises(InvalidStatusTransitionError):
            await service.accept_candidate(candidate.id)

    async def test_accept_nonexistent_candidate_raises(
        self, service, mock_candidate_repo
    ):
        """Should raise CandidateNotFoundError for nonexistent candidate."""
        mock_candidate_repo.get_by_id.return_value = None

        with pytest.raises(CandidateNotFoundError):
            await service.accept_candidate(uuid4())


# ─── Archive Candidate Tests ──────────────────────────────────────────


class TestArchiveCandidate:
    """Tests for archive_candidate action."""

    @pytest.mark.parametrize(
        "initial_status",
        [CandidateStatus.NEW, CandidateStatus.REVIEWING, CandidateStatus.INTERVIEW_SCHEDULED],
    )
    async def test_archive_from_valid_statuses(
        self, service, mock_candidate_repo, initial_status
    ):
        """Should transition to archived from new, reviewing, interview_scheduled."""
        candidate = _make_candidate(status=initial_status)
        mock_candidate_repo.get_by_id.return_value = candidate

        result = await service.archive_candidate(candidate.id)

        assert result.status == CandidateStatus.ARCHIVED
        assert result.archived_at is not None

    async def test_archive_idempotent_for_already_archived(
        self, service, mock_candidate_repo
    ):
        """Should return existing record without modification for already-archived."""
        archived_at = datetime(2024, 1, 15, 10, 0, 0, tzinfo=UTC)
        candidate = _make_candidate(status=CandidateStatus.ARCHIVED)
        candidate.archived_at = archived_at
        mock_candidate_repo.get_by_id.return_value = candidate

        result = await service.archive_candidate(candidate.id)

        assert result.status == CandidateStatus.ARCHIVED
        assert result.archived_at == archived_at
        # Should NOT call update since it's a no-op
        mock_candidate_repo.update.assert_not_called()

    async def test_archive_from_accepted_raises(self, service, mock_candidate_repo):
        """Should raise InvalidStatusTransitionError from accepted status."""
        candidate = _make_candidate(status=CandidateStatus.ACCEPTED)
        mock_candidate_repo.get_by_id.return_value = candidate

        with pytest.raises(InvalidStatusTransitionError) as exc_info:
            await service.archive_candidate(candidate.id)

        assert exc_info.value.current_status == CandidateStatus.ACCEPTED
        assert exc_info.value.attempted_action == "archive"

    async def test_archive_from_rejected_raises(self, service, mock_candidate_repo):
        """Should raise InvalidStatusTransitionError from rejected status."""
        candidate = _make_candidate(status=CandidateStatus.REJECTED)
        mock_candidate_repo.get_by_id.return_value = candidate

        with pytest.raises(InvalidStatusTransitionError):
            await service.archive_candidate(candidate.id)

    async def test_archive_nonexistent_candidate_raises(
        self, service, mock_candidate_repo
    ):
        """Should raise CandidateNotFoundError for nonexistent candidate."""
        mock_candidate_repo.get_by_id.return_value = None

        with pytest.raises(CandidateNotFoundError):
            await service.archive_candidate(uuid4())


# ─── Schedule Interview Tests ─────────────────────────────────────────


class TestScheduleInterview:
    """Tests for schedule_interview action."""

    @pytest.mark.parametrize(
        "initial_status",
        [CandidateStatus.NEW, CandidateStatus.REVIEWING],
    )
    async def test_schedule_from_valid_statuses(
        self, service, mock_candidate_repo, mock_session, initial_status
    ):
        """Should transition to interview_scheduled from new and reviewing."""
        candidate = _make_candidate(status=initial_status)
        mock_candidate_repo.get_by_id.return_value = candidate

        # Mock employee validation - all IDs found
        interviewer_ids = [uuid4(), uuid4()]
        from unittest.mock import MagicMock
        mock_result = MagicMock()
        mock_result.all.return_value = [(id,) for id in interviewer_ids]
        mock_session.execute.return_value = mock_result

        result = await service.schedule_interview(
            candidate_id=candidate.id,
            interviewer_ids=interviewer_ids,
        )

        assert result.status == CandidateStatus.INTERVIEW_SCHEDULED

    async def test_schedule_emits_domain_event(
        self, service, mock_candidate_repo, mock_session, mock_event_publisher
    ):
        """Should emit interview_scheduled domain event."""
        candidate = _make_candidate(status=CandidateStatus.NEW)
        mock_candidate_repo.get_by_id.return_value = candidate

        interviewer_ids = [uuid4()]
        from unittest.mock import MagicMock
        mock_result = MagicMock()
        mock_result.all.return_value = [(interviewer_ids[0],)]
        mock_session.execute.return_value = mock_result

        await service.schedule_interview(
            candidate_id=candidate.id,
            interviewer_ids=interviewer_ids,
            date="2025-02-01",
            time="10:00",
            duration_minutes=60,
            notes="Technical interview",
        )

        mock_event_publisher.publish.assert_called_once()
        call_args = mock_event_publisher.publish.call_args
        assert call_args.kwargs["event_type"] == "interview_scheduled"

    async def test_schedule_validates_interviewer_ids(
        self, service, mock_candidate_repo, mock_session
    ):
        """Should raise ValueError when interviewer IDs don't match employees."""
        candidate = _make_candidate(status=CandidateStatus.NEW)
        mock_candidate_repo.get_by_id.return_value = candidate

        valid_id = uuid4()
        invalid_id = uuid4()
        from unittest.mock import MagicMock
        mock_result = MagicMock()
        mock_result.all.return_value = [(valid_id,)]  # Only one found
        mock_session.execute.return_value = mock_result

        with pytest.raises(ValueError, match="Invalid interviewer IDs"):
            await service.schedule_interview(
                candidate_id=candidate.id,
                interviewer_ids=[valid_id, invalid_id],
            )

    async def test_schedule_from_rejected_raises(
        self, service, mock_candidate_repo
    ):
        """Should raise InvalidStatusTransitionError from rejected status."""
        candidate = _make_candidate(status=CandidateStatus.REJECTED)
        mock_candidate_repo.get_by_id.return_value = candidate

        with pytest.raises(InvalidStatusTransitionError):
            await service.schedule_interview(
                candidate_id=candidate.id,
                interviewer_ids=[uuid4()],
            )

    async def test_schedule_from_archived_raises(
        self, service, mock_candidate_repo
    ):
        """Should raise InvalidStatusTransitionError from archived status."""
        candidate = _make_candidate(status=CandidateStatus.ARCHIVED)
        mock_candidate_repo.get_by_id.return_value = candidate

        with pytest.raises(InvalidStatusTransitionError):
            await service.schedule_interview(
                candidate_id=candidate.id,
                interviewer_ids=[uuid4()],
            )

    async def test_schedule_nonexistent_candidate_raises(
        self, service, mock_candidate_repo
    ):
        """Should raise CandidateNotFoundError for nonexistent candidate."""
        mock_candidate_repo.get_by_id.return_value = None

        with pytest.raises(CandidateNotFoundError):
            await service.schedule_interview(
                candidate_id=uuid4(),
                interviewer_ids=[uuid4()],
            )


# ─── Send Email Tests ─────────────────────────────────────────────────


class TestSendEmailToCandidate:
    """Tests for send_email_to_candidate action."""

    async def test_send_email_success(
        self, service, mock_candidate_repo, mock_gmail_sender
    ):
        """Should send email via Gmail adapter."""
        candidate = _make_candidate(email="valid@example.com")
        mock_candidate_repo.get_by_id.return_value = candidate

        await service.send_email_to_candidate(
            candidate_id=candidate.id,
            subject="Interview Invitation",
            body_html="<p>Hello</p>",
        )

        mock_gmail_sender.send_email.assert_called_once()

    async def test_send_email_gmail_not_connected_raises(
        self, mock_candidate_repo, mock_cv_document_repo, mock_minio_client, mock_session, user_id
    ):
        """Should raise GmailNotConnectedError when Gmail not connected."""
        candidate = _make_candidate(email="valid@example.com")
        mock_candidate_repo.get_by_id.return_value = candidate

        checker = AsyncMock()
        checker.is_connected = AsyncMock(return_value=False)

        svc = CandidateService(
            candidate_repo=mock_candidate_repo,
            cv_document_repo=mock_cv_document_repo,
            minio_client=mock_minio_client,
            session=mock_session,
            gmail_sender=AsyncMock(),
            gmail_checker=checker,
            user_id=user_id,
        )

        with pytest.raises(GmailNotConnectedError):
            await svc.send_email_to_candidate(
                candidate_id=candidate.id,
                subject="Test",
                body_html="<p>Test</p>",
            )

    async def test_send_email_invalid_candidate_email_raises(
        self, service, mock_candidate_repo
    ):
        """Should raise ValueError when candidate email is invalid."""
        candidate = _make_candidate(email="")
        mock_candidate_repo.get_by_id.return_value = candidate

        with pytest.raises(ValueError, match="invalid"):
            await service.send_email_to_candidate(
                candidate_id=candidate.id,
                subject="Test",
                body_html="<p>Test</p>",
            )

    async def test_send_email_invalid_format_raises(
        self, service, mock_candidate_repo
    ):
        """Should raise ValueError when candidate email has no @ sign."""
        candidate = _make_candidate(email="no-at-sign")
        mock_candidate_repo.get_by_id.return_value = candidate

        with pytest.raises(ValueError, match="invalid"):
            await service.send_email_to_candidate(
                candidate_id=candidate.id,
                subject="Test",
                body_html="<p>Test</p>",
            )

    async def test_send_email_nonexistent_candidate_raises(
        self, service, mock_candidate_repo
    ):
        """Should raise CandidateNotFoundError for nonexistent candidate."""
        mock_candidate_repo.get_by_id.return_value = None

        with pytest.raises(CandidateNotFoundError):
            await service.send_email_to_candidate(
                candidate_id=uuid4(),
                subject="Test",
                body_html="<p>Test</p>",
            )

    async def test_send_email_no_gmail_sender_raises(
        self, mock_candidate_repo, mock_cv_document_repo, mock_minio_client, mock_session, user_id
    ):
        """Should raise GmailNotConnectedError when no Gmail sender configured."""
        candidate = _make_candidate(email="valid@example.com")
        mock_candidate_repo.get_by_id.return_value = candidate

        svc = CandidateService(
            candidate_repo=mock_candidate_repo,
            cv_document_repo=mock_cv_document_repo,
            minio_client=mock_minio_client,
            session=mock_session,
            gmail_sender=None,
            gmail_checker=None,
            user_id=user_id,
        )

        with pytest.raises(GmailNotConnectedError):
            await svc.send_email_to_candidate(
                candidate_id=candidate.id,
                subject="Test",
                body_html="<p>Test</p>",
            )
