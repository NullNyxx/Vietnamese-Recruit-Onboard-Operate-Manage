"""Unit tests for the IntentClassifierService."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from src.modules.recruitment.application.intent_classifier import (
    IntentClassifierService,
)
from src.modules.recruitment.domain.enums import EmailIntent
from src.modules.recruitment.domain.exceptions import LLMParseError
from src.modules.recruitment.infrastructure.llm_adapter import IntentResult
from src.modules.recruitment.infrastructure.pii_redactor import PIIRedactor


@pytest.fixture
def pii_redactor():
    """Create a real PIIRedactor instance."""
    return PIIRedactor()


@pytest.fixture
def mock_llm_adapter():
    """Create a mock LLM adapter."""
    adapter = AsyncMock()
    adapter._model = "NullNyx-Combo"
    return adapter


@pytest.fixture
def mock_session():
    """Create a mock async database session."""
    session = AsyncMock()
    session.execute = AsyncMock()
    session.flush = AsyncMock()
    session.add = MagicMock()
    return session


@pytest.fixture
def mock_gmail_label_service():
    """Create a mock Gmail label service."""
    service = AsyncMock()
    service.add_label = AsyncMock()
    return service


@pytest.fixture
def mock_enqueue_func():
    """Create a mock enqueue function."""
    return AsyncMock()


@pytest.fixture
def service(
    mock_llm_adapter,
    pii_redactor,
    mock_session,
    mock_gmail_label_service,
    mock_enqueue_func,
):
    """Create an IntentClassifierService with mocked dependencies."""
    return IntentClassifierService(
        llm_adapter=mock_llm_adapter,
        pii_redactor=pii_redactor,
        session=mock_session,
        gmail_label_service=mock_gmail_label_service,
        enqueue_func=mock_enqueue_func,
    )


class TestClassifyEmail:
    """Tests for the classify_email method."""

    async def test_successful_cv_classification(self, service, mock_llm_adapter):
        """Successfully classifies an email as CV intent."""
        expected_result = IntentResult(
            intent=EmailIntent.CV,
            token_usage={"prompt_tokens": 50, "completion_tokens": 1, "total_tokens": 51},
        )
        mock_llm_adapter.classify_intent = AsyncMock(return_value=expected_result)

        result = await service.classify_email(
            subject="Ứng tuyển vị trí Developer",
            sender="candidate@example.com",
            snippet="Kính gửi phòng nhân sự, tôi xin gửi CV...",
            attachment_filenames=["CV_NguyenVanA.pdf"],
            gmail_message_id="msg_123",
            email_message_id=uuid4(),
            user_id=uuid4(),
        )

        assert result.intent == EmailIntent.CV
        assert result.token_usage["total_tokens"] == 51

    async def test_successful_other_classification(self, service, mock_llm_adapter):
        """Successfully classifies an email as OTHER intent."""
        expected_result = IntentResult(
            intent=EmailIntent.OTHER,
            token_usage={"prompt_tokens": 40, "completion_tokens": 1, "total_tokens": 41},
        )
        mock_llm_adapter.classify_intent = AsyncMock(return_value=expected_result)

        result = await service.classify_email(
            subject="Meeting tomorrow",
            sender="colleague@company.com",
            snippet="Hi, let's meet tomorrow at 10am",
            attachment_filenames=[],
            gmail_message_id="msg_456",
        )

        assert result.intent == EmailIntent.OTHER

    async def test_pii_redaction_applied_before_llm_call(
        self, mock_llm_adapter, mock_session, mock_gmail_label_service, mock_enqueue_func
    ):
        """PII in snippet is redacted before being sent to LLM."""
        expected_result = IntentResult(
            intent=EmailIntent.CV,
            token_usage={"prompt_tokens": 50, "completion_tokens": 1, "total_tokens": 51},
        )
        mock_llm_adapter.classify_intent = AsyncMock(return_value=expected_result)

        pii_redactor = PIIRedactor()
        svc = IntentClassifierService(
            llm_adapter=mock_llm_adapter,
            pii_redactor=pii_redactor,
            session=mock_session,
            gmail_label_service=mock_gmail_label_service,
            enqueue_func=mock_enqueue_func,
        )

        # Snippet contains a CCCD number (12 digits)
        snippet_with_pii = "CCCD: 012345678901, xin ứng tuyển"

        await svc.classify_email(
            subject="Ứng tuyển",
            sender="candidate@example.com",
            snippet=snippet_with_pii,
            attachment_filenames=["CV.pdf"],
            gmail_message_id="msg_789",
        )

        # Verify the LLM was called with redacted snippet
        call_args = mock_llm_adapter.classify_intent.call_args
        assert "[REDACTED]" in call_args.kwargs["snippet"]
        assert "012345678901" not in call_args.kwargs["snippet"]

    async def test_llm_failure_returns_other_and_marks_failed(
        self, service, mock_llm_adapter
    ):
        """When LLM fails after retries, returns OTHER and marks email as failed."""
        mock_llm_adapter.classify_intent = AsyncMock(
            side_effect=LLMParseError("Failed after 3 attempts")
        )

        email_message_id = uuid4()
        result = await service.classify_email(
            subject="Test email",
            sender="test@example.com",
            snippet="Some content",
            attachment_filenames=[],
            gmail_message_id="msg_fail",
            email_message_id=email_message_id,
        )

        # Should default to OTHER on failure
        assert result.intent == EmailIntent.OTHER
        assert result.token_usage["total_tokens"] == 0

    async def test_pii_redaction_failure_returns_other(
        self, mock_llm_adapter, mock_session, mock_gmail_label_service, mock_enqueue_func
    ):
        """When PII redaction fails, returns OTHER and marks email as failed."""
        # Create a PIIRedactor that raises an exception
        broken_redactor = MagicMock()
        broken_redactor.redact = MagicMock(side_effect=RuntimeError("Regex engine crash"))

        svc = IntentClassifierService(
            llm_adapter=mock_llm_adapter,
            pii_redactor=broken_redactor,
            session=mock_session,
            gmail_label_service=mock_gmail_label_service,
            enqueue_func=mock_enqueue_func,
        )

        email_message_id = uuid4()
        result = await svc.classify_email(
            subject="Test",
            sender="test@example.com",
            snippet="Some content",
            attachment_filenames=[],
            gmail_message_id="msg_pii_fail",
            email_message_id=email_message_id,
        )

        assert result.intent == EmailIntent.OTHER
        assert result.token_usage["total_tokens"] == 0

    async def test_classify_email_with_attachments(self, service, mock_llm_adapter):
        """Attachment filenames are passed to the LLM adapter."""
        expected_result = IntentResult(
            intent=EmailIntent.CV,
            token_usage={"prompt_tokens": 60, "completion_tokens": 1, "total_tokens": 61},
        )
        mock_llm_adapter.classify_intent = AsyncMock(return_value=expected_result)

        filenames = ["CV_NguyenVanA.pdf", "Cover_Letter.docx"]
        await service.classify_email(
            subject="Application",
            sender="candidate@example.com",
            snippet="Please find my CV attached",
            attachment_filenames=filenames,
            gmail_message_id="msg_attach",
        )

        call_args = mock_llm_adapter.classify_intent.call_args
        assert call_args.kwargs["attachment_filenames"] == filenames


class TestProcessClassificationResult:
    """Tests for the process_classification_result method."""

    async def test_cv_intent_applies_label_and_enqueues(
        self, service, mock_gmail_label_service, mock_enqueue_func
    ):
        """CV intent triggers label application and CV processing enqueue."""
        intent_result = IntentResult(
            intent=EmailIntent.CV,
            token_usage={"prompt_tokens": 50, "completion_tokens": 1, "total_tokens": 51},
        )
        email_message_id = uuid4()
        user_id = uuid4()

        await service.process_classification_result(
            intent_result=intent_result,
            gmail_message_id="msg_cv",
            email_message_id=email_message_id,
            user_id=user_id,
            access_token="test_token",
        )

        # Verify label was applied
        mock_gmail_label_service.add_label.assert_called_once_with(
            user_id=user_id,
            message_id="msg_cv",
            label_name="VroomHR/recruitment",
            access_token="test_token",
        )

        # Verify CV processing was enqueued
        mock_enqueue_func.assert_called_once_with(
            "process_cv_from_email", email_message_id
        )

    async def test_other_intent_does_not_enqueue(
        self, service, mock_gmail_label_service, mock_enqueue_func
    ):
        """Non-CV intents do not trigger label or enqueue."""
        intent_result = IntentResult(
            intent=EmailIntent.PARTNER,
            token_usage={"prompt_tokens": 40, "completion_tokens": 1, "total_tokens": 41},
        )

        await service.process_classification_result(
            intent_result=intent_result,
            gmail_message_id="msg_partner",
            email_message_id=uuid4(),
            user_id=uuid4(),
            access_token="test_token",
        )

        # Label should NOT be applied for non-CV intents
        mock_gmail_label_service.add_label.assert_not_called()
        # Enqueue should NOT be called for non-CV intents
        mock_enqueue_func.assert_not_called()

    async def test_cv_intent_without_access_token_skips_label(
        self, service, mock_gmail_label_service, mock_enqueue_func
    ):
        """CV intent without access token skips label but still enqueues."""
        intent_result = IntentResult(
            intent=EmailIntent.CV,
            token_usage={"prompt_tokens": 50, "completion_tokens": 1, "total_tokens": 51},
        )
        email_message_id = uuid4()

        await service.process_classification_result(
            intent_result=intent_result,
            gmail_message_id="msg_no_token",
            email_message_id=email_message_id,
            user_id=None,
            access_token=None,
        )

        # Label should NOT be applied without access token
        mock_gmail_label_service.add_label.assert_not_called()
        # Enqueue should still be called
        mock_enqueue_func.assert_called_once_with(
            "process_cv_from_email", email_message_id
        )

    async def test_label_failure_does_not_block_enqueue(
        self, service, mock_gmail_label_service, mock_enqueue_func
    ):
        """If label application fails, CV processing is still enqueued."""
        mock_gmail_label_service.add_label = AsyncMock(
            side_effect=RuntimeError("Gmail API error")
        )

        intent_result = IntentResult(
            intent=EmailIntent.CV,
            token_usage={"prompt_tokens": 50, "completion_tokens": 1, "total_tokens": 51},
        )
        email_message_id = uuid4()
        user_id = uuid4()

        await service.process_classification_result(
            intent_result=intent_result,
            gmail_message_id="msg_label_fail",
            email_message_id=email_message_id,
            user_id=user_id,
            access_token="test_token",
        )

        # Enqueue should still be called despite label failure
        mock_enqueue_func.assert_called_once_with(
            "process_cv_from_email", email_message_id
        )

    async def test_all_non_cv_intents_skip_enqueue(
        self, service, mock_gmail_label_service, mock_enqueue_func
    ):
        """All non-CV intents (partner, event, internal, other) skip enqueue."""
        non_cv_intents = [
            EmailIntent.PARTNER,
            EmailIntent.EVENT,
            EmailIntent.INTERNAL,
            EmailIntent.OTHER,
        ]

        for intent in non_cv_intents:
            mock_enqueue_func.reset_mock()
            mock_gmail_label_service.reset_mock()

            intent_result = IntentResult(
                intent=intent,
                token_usage={"prompt_tokens": 40, "completion_tokens": 1, "total_tokens": 41},
            )

            await service.process_classification_result(
                intent_result=intent_result,
                gmail_message_id=f"msg_{intent.value}",
                email_message_id=uuid4(),
                user_id=uuid4(),
                access_token="test_token",
            )

            mock_gmail_label_service.add_label.assert_not_called()
            mock_enqueue_func.assert_not_called()
