"""Unit tests for the LLM Adapter service."""

from __future__ import annotations

import asyncio
import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.modules.recruitment.domain.enums import EmailIntent
from src.modules.recruitment.domain.exceptions import LLMParseError
from src.modules.recruitment.domain.value_objects import ParsedCV
from src.modules.recruitment.infrastructure.config import RecruitmentSettings
from src.modules.recruitment.infrastructure.llm_adapter import (
    IntentResult,
    LLMAdapter,
    ParsedCVResult,
)


@pytest.fixture
def settings() -> RecruitmentSettings:
    """Create test settings."""
    return RecruitmentSettings(
        llm_base_url="http://localhost:20128/v1",
        llm_api_key="test-key",
        llm_model="test-model",
        llm_intent_timeout_seconds=15,
        llm_parse_timeout_seconds=30,
        llm_max_retries=3,
    )


@pytest.fixture
def adapter(settings: RecruitmentSettings) -> LLMAdapter:
    """Create an LLMAdapter instance for testing."""
    return LLMAdapter(settings)


def _make_completion_response(content: str, prompt_tokens: int = 50, completion_tokens: int = 10):
    """Create a mock chat completion response."""
    response = MagicMock()
    response.choices = [MagicMock()]
    response.choices[0].message.content = content
    response.usage = MagicMock()
    response.usage.prompt_tokens = prompt_tokens
    response.usage.completion_tokens = completion_tokens
    response.usage.total_tokens = prompt_tokens + completion_tokens
    return response


class TestClassifyIntent:
    """Tests for the classify_intent method."""

    @pytest.mark.asyncio
    async def test_classifies_cv_intent(self, adapter: LLMAdapter):
        """Should correctly classify a CV email."""
        mock_response = _make_completion_response("cv")

        with patch.object(
            adapter._client.chat.completions, "create", new_callable=AsyncMock
        ) as mock_create:
            mock_create.return_value = mock_response

            result = await adapter.classify_intent(
                subject="Ứng tuyển vị trí Backend Developer",
                sender="candidate@gmail.com",
                snippet="Kính gửi phòng nhân sự, tôi xin gửi CV...",
                attachment_filenames=["CV_NguyenVanA.pdf"],
            )

        assert isinstance(result, IntentResult)
        assert result.intent == EmailIntent.CV
        assert result.token_usage["prompt_tokens"] == 50
        assert result.token_usage["completion_tokens"] == 10
        assert result.token_usage["total_tokens"] == 60

    @pytest.mark.asyncio
    async def test_classifies_partner_intent(self, adapter: LLMAdapter):
        """Should correctly classify a partner email."""
        mock_response = _make_completion_response("partner")

        with patch.object(
            adapter._client.chat.completions, "create", new_callable=AsyncMock
        ) as mock_create:
            mock_create.return_value = mock_response

            result = await adapter.classify_intent(
                subject="Hợp tác kinh doanh",
                sender="partner@company.com",
                snippet="Chúng tôi muốn đề xuất hợp tác...",
                attachment_filenames=[],
            )

        assert result.intent == EmailIntent.PARTNER

    @pytest.mark.asyncio
    async def test_classifies_event_intent(self, adapter: LLMAdapter):
        """Should correctly classify an event email."""
        mock_response = _make_completion_response("event")

        with patch.object(
            adapter._client.chat.completions, "create", new_callable=AsyncMock
        ) as mock_create:
            mock_create.return_value = mock_response

            result = await adapter.classify_intent(
                subject="Mời tham dự hội thảo",
                sender="events@techconf.vn",
                snippet="Kính mời quý công ty tham dự...",
                attachment_filenames=["invitation.pdf"],
            )

        assert result.intent == EmailIntent.EVENT

    @pytest.mark.asyncio
    async def test_defaults_to_other_on_invalid_response(self, adapter: LLMAdapter):
        """Should default to OTHER when LLM returns unparseable response."""
        mock_response = _make_completion_response("I think this is a job application")

        with patch.object(
            adapter._client.chat.completions, "create", new_callable=AsyncMock
        ) as mock_create:
            mock_create.return_value = mock_response

            result = await adapter.classify_intent(
                subject="Test",
                sender="test@test.com",
                snippet="Test snippet",
                attachment_filenames=[],
            )

        assert result.intent == EmailIntent.OTHER

    @pytest.mark.asyncio
    async def test_handles_response_with_quotes(self, adapter: LLMAdapter):
        """Should handle LLM response wrapped in quotes."""
        mock_response = _make_completion_response('"cv"')

        with patch.object(
            adapter._client.chat.completions, "create", new_callable=AsyncMock
        ) as mock_create:
            mock_create.return_value = mock_response

            result = await adapter.classify_intent(
                subject="Apply for position",
                sender="candidate@email.com",
                snippet="Please find my CV attached",
                attachment_filenames=["resume.pdf"],
            )

        assert result.intent == EmailIntent.CV

    @pytest.mark.asyncio
    async def test_handles_response_with_period(self, adapter: LLMAdapter):
        """Should handle LLM response with trailing period."""
        mock_response = _make_completion_response("internal.")

        with patch.object(
            adapter._client.chat.completions, "create", new_callable=AsyncMock
        ) as mock_create:
            mock_create.return_value = mock_response

            result = await adapter.classify_intent(
                subject="Internal memo",
                sender="hr@company.com",
                snippet="Team meeting tomorrow",
                attachment_filenames=[],
            )

        assert result.intent == EmailIntent.INTERNAL

    @pytest.mark.asyncio
    async def test_raises_after_max_retries_on_timeout(self, adapter: LLMAdapter):
        """Should raise LLMParseError after all retries are exhausted on timeout."""
        with patch.object(
            adapter._client.chat.completions, "create", new_callable=AsyncMock
        ) as mock_create:
            mock_create.side_effect = asyncio.TimeoutError()

            with patch("asyncio.sleep", new_callable=AsyncMock):
                with pytest.raises(LLMParseError):
                    await adapter.classify_intent(
                        subject="Test",
                        sender="test@test.com",
                        snippet="Test",
                        attachment_filenames=[],
                    )

        assert mock_create.call_count == 3

    @pytest.mark.asyncio
    async def test_retries_on_api_error(self, adapter: LLMAdapter):
        """Should retry on API errors and succeed if a retry works."""
        from openai import APIConnectionError

        mock_response = _make_completion_response("cv")

        with patch.object(
            adapter._client.chat.completions, "create", new_callable=AsyncMock
        ) as mock_create:
            mock_create.side_effect = [
                APIConnectionError(request=MagicMock()),
                mock_response,
            ]

            with patch("asyncio.sleep", new_callable=AsyncMock):
                result = await adapter.classify_intent(
                    subject="Apply",
                    sender="candidate@email.com",
                    snippet="CV attached",
                    attachment_filenames=["cv.pdf"],
                )

        assert result.intent == EmailIntent.CV
        assert mock_create.call_count == 2

    @pytest.mark.asyncio
    async def test_prompt_includes_all_metadata(self, adapter: LLMAdapter):
        """Should include subject, sender, snippet, and attachments in prompt."""
        mock_response = _make_completion_response("cv")

        with patch.object(
            adapter._client.chat.completions, "create", new_callable=AsyncMock
        ) as mock_create:
            mock_create.return_value = mock_response

            await adapter.classify_intent(
                subject="Ứng tuyển Backend",
                sender="nguyen@gmail.com",
                snippet="Xin gửi CV ứng tuyển",
                attachment_filenames=["CV.pdf", "Cover_Letter.docx"],
            )

        # Check the user message content
        call_kwargs = mock_create.call_args[1]
        messages = call_kwargs["messages"]
        user_message = messages[1]["content"]

        assert "Ứng tuyển Backend" in user_message
        assert "nguyen@gmail.com" in user_message
        assert "Xin gửi CV ứng tuyển" in user_message
        assert "CV.pdf" in user_message
        assert "Cover_Letter.docx" in user_message
        assert "2 files" in user_message

    @pytest.mark.asyncio
    async def test_prompt_shows_no_attachments(self, adapter: LLMAdapter):
        """Should indicate no attachments when list is empty."""
        mock_response = _make_completion_response("other")

        with patch.object(
            adapter._client.chat.completions, "create", new_callable=AsyncMock
        ) as mock_create:
            mock_create.return_value = mock_response

            await adapter.classify_intent(
                subject="Hello",
                sender="someone@email.com",
                snippet="Just a message",
                attachment_filenames=[],
            )

        call_kwargs = mock_create.call_args[1]
        messages = call_kwargs["messages"]
        user_message = messages[1]["content"]
        assert "none" in user_message.lower()


class TestParseCV:
    """Tests for the parse_cv method."""

    @pytest.mark.asyncio
    async def test_parses_valid_cv_json(self, adapter: LLMAdapter):
        """Should parse a valid JSON response into ParsedCV."""
        cv_json = json.dumps({
            "name": "Nguyễn Văn A",
            "email": "nguyenvana@gmail.com",
            "phone": "0901234567",
            "skills": ["Python", "FastAPI", "PostgreSQL"],
            "experience": [
                {
                    "company": "Tech Corp",
                    "title": "Backend Developer",
                    "duration": "2020-2023",
                    "description": "Developed REST APIs",
                }
            ],
            "education": [
                {
                    "institution": "HCMUT",
                    "degree": "Bachelor",
                    "field": "Computer Science",
                    "year": "2020",
                }
            ],
            "summary": "Experienced backend developer",
        })
        mock_response = _make_completion_response(cv_json, prompt_tokens=200, completion_tokens=150)

        with patch.object(
            adapter._client.chat.completions, "create", new_callable=AsyncMock
        ) as mock_create:
            mock_create.return_value = mock_response

            result = await adapter.parse_cv("Some OCR text from a CV...")

        assert isinstance(result, ParsedCVResult)
        assert result.parsed_cv.name == "Nguyễn Văn A"
        assert result.parsed_cv.email == "nguyenvana@gmail.com"
        assert result.parsed_cv.phone == "0901234567"
        assert "Python" in result.parsed_cv.skills
        assert len(result.parsed_cv.experience) == 1
        assert result.parsed_cv.experience[0].company == "Tech Corp"
        assert len(result.parsed_cv.education) == 1
        assert result.parsed_cv.education[0].institution == "HCMUT"
        assert result.token_usage["prompt_tokens"] == 200
        assert result.token_usage["total_tokens"] == 350

    @pytest.mark.asyncio
    async def test_handles_markdown_code_block_response(self, adapter: LLMAdapter):
        """Should handle JSON wrapped in markdown code blocks."""
        cv_json = json.dumps({
            "name": "Trần Thị B",
            "email": "tranthib@email.com",
            "phone": "",
            "skills": ["Java"],
            "experience": [],
            "education": [],
            "summary": "",
        })
        wrapped = f"```json\n{cv_json}\n```"
        mock_response = _make_completion_response(wrapped)

        with patch.object(
            adapter._client.chat.completions, "create", new_callable=AsyncMock
        ) as mock_create:
            mock_create.return_value = mock_response

            result = await adapter.parse_cv("OCR text...")

        assert result.parsed_cv.name == "Trần Thị B"
        assert result.parsed_cv.email == "tranthib@email.com"

    @pytest.mark.asyncio
    async def test_retries_with_simplified_prompt_on_invalid_json(self, adapter: LLMAdapter):
        """Should retry with simplified prompt when initial response is invalid JSON."""
        invalid_response = _make_completion_response("Here is the parsed CV: {invalid json}")
        valid_json = json.dumps({
            "name": "Test User",
            "email": "test@email.com",
            "phone": "",
            "skills": [],
            "experience": [],
            "education": [],
            "summary": "",
        })
        valid_response = _make_completion_response(valid_json)

        with patch.object(
            adapter._client.chat.completions, "create", new_callable=AsyncMock
        ) as mock_create:
            # First call returns invalid JSON, second (simplified) returns valid
            mock_create.side_effect = [invalid_response, valid_response]

            result = await adapter.parse_cv("Some CV text")

        assert result.parsed_cv.name == "Test User"
        assert result.parsed_cv.email == "test@email.com"
        # Should have been called twice: initial + simplified retry
        assert mock_create.call_count == 2

    @pytest.mark.asyncio
    async def test_raises_after_all_retries_exhausted(self, adapter: LLMAdapter):
        """Should raise LLMParseError when all retries fail."""
        with patch.object(
            adapter._client.chat.completions, "create", new_callable=AsyncMock
        ) as mock_create:
            mock_create.side_effect = asyncio.TimeoutError()

            with patch("asyncio.sleep", new_callable=AsyncMock):
                with pytest.raises(LLMParseError):
                    await adapter.parse_cv("Some CV text")

    @pytest.mark.asyncio
    async def test_handles_minimal_valid_cv(self, adapter: LLMAdapter):
        """Should parse a CV with only required fields."""
        cv_json = json.dumps({
            "name": "Minimal User",
            "email": "minimal@email.com",
        })
        mock_response = _make_completion_response(cv_json)

        with patch.object(
            adapter._client.chat.completions, "create", new_callable=AsyncMock
        ) as mock_create:
            mock_create.return_value = mock_response

            result = await adapter.parse_cv("Short CV text")

        assert result.parsed_cv.name == "Minimal User"
        assert result.parsed_cv.email == "minimal@email.com"
        assert result.parsed_cv.phone == ""
        assert result.parsed_cv.skills == []

    @pytest.mark.asyncio
    async def test_handles_no_usage_in_response(self, adapter: LLMAdapter):
        """Should handle response without usage data gracefully."""
        cv_json = json.dumps({
            "name": "Test",
            "email": "test@test.com",
        })
        response = MagicMock()
        response.choices = [MagicMock()]
        response.choices[0].message.content = cv_json
        response.usage = None

        with patch.object(
            adapter._client.chat.completions, "create", new_callable=AsyncMock
        ) as mock_create:
            mock_create.return_value = response

            result = await adapter.parse_cv("CV text")

        assert result.token_usage == {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}

    @pytest.mark.asyncio
    async def test_timeout_uses_parse_timeout_setting(self, adapter: LLMAdapter):
        """Should use the configured parse timeout (30s)."""
        cv_json = json.dumps({"name": "Test", "email": "t@t.com"})
        mock_response = _make_completion_response(cv_json)

        with patch.object(
            adapter._client.chat.completions, "create", new_callable=AsyncMock
        ) as mock_create:
            mock_create.return_value = mock_response

            with patch("asyncio.wait_for", new_callable=AsyncMock) as mock_wait:
                mock_wait.return_value = mock_response

                await adapter.parse_cv("CV text")

                # Verify timeout parameter
                _, kwargs = mock_wait.call_args
                assert kwargs["timeout"] == 30


class TestParseIntentResponse:
    """Tests for the _parse_intent_response helper."""

    def test_parses_exact_intent_values(self, adapter: LLMAdapter):
        """Should parse exact intent enum values."""
        assert adapter._parse_intent_response("cv") == EmailIntent.CV
        assert adapter._parse_intent_response("partner") == EmailIntent.PARTNER
        assert adapter._parse_intent_response("event") == EmailIntent.EVENT
        assert adapter._parse_intent_response("internal") == EmailIntent.INTERNAL
        assert adapter._parse_intent_response("other") == EmailIntent.OTHER

    def test_handles_uppercase(self, adapter: LLMAdapter):
        """Should handle uppercase responses (already lowered before calling)."""
        assert adapter._parse_intent_response("cv") == EmailIntent.CV

    def test_handles_quoted_response(self, adapter: LLMAdapter):
        """Should strip quotes from response."""
        assert adapter._parse_intent_response('"cv"') == EmailIntent.CV
        assert adapter._parse_intent_response("'partner'") == EmailIntent.PARTNER

    def test_handles_response_with_period(self, adapter: LLMAdapter):
        """Should strip trailing period."""
        assert adapter._parse_intent_response("event.") == EmailIntent.EVENT

    def test_handles_substring_match(self, adapter: LLMAdapter):
        """Should find intent as substring in longer response."""
        assert adapter._parse_intent_response("the intent is cv") == EmailIntent.CV

    def test_defaults_to_other_for_garbage(self, adapter: LLMAdapter):
        """Should default to OTHER for completely unrecognizable response."""
        assert adapter._parse_intent_response("xyz123") == EmailIntent.OTHER
        assert adapter._parse_intent_response("") == EmailIntent.OTHER


class TestParseCVJson:
    """Tests for the _parse_cv_json helper."""

    def test_parses_valid_json(self, adapter: LLMAdapter):
        """Should parse valid JSON into ParsedCV."""
        content = json.dumps({"name": "Test", "email": "test@test.com"})
        result = adapter._parse_cv_json(content)
        assert result is not None
        assert result.name == "Test"

    def test_returns_none_for_invalid_json(self, adapter: LLMAdapter):
        """Should return None for invalid JSON."""
        assert adapter._parse_cv_json("not json at all") is None
        assert adapter._parse_cv_json("{invalid}") is None

    def test_returns_none_for_non_dict_json(self, adapter: LLMAdapter):
        """Should return None for JSON that is not a dict."""
        assert adapter._parse_cv_json("[1, 2, 3]") is None
        assert adapter._parse_cv_json('"just a string"') is None

    def test_strips_markdown_code_blocks(self, adapter: LLMAdapter):
        """Should strip markdown code block wrappers."""
        content = '```json\n{"name": "Test", "email": "t@t.com"}\n```'
        result = adapter._parse_cv_json(content)
        assert result is not None
        assert result.name == "Test"

    def test_strips_plain_code_blocks(self, adapter: LLMAdapter):
        """Should strip plain code block wrappers (no language tag)."""
        content = '```\n{"name": "Test", "email": "t@t.com"}\n```'
        result = adapter._parse_cv_json(content)
        assert result is not None
        assert result.name == "Test"


class TestTokenUsageExtraction:
    """Tests for the _extract_token_usage helper."""

    def test_extracts_usage_from_response(self, adapter: LLMAdapter):
        """Should extract token usage from response."""
        response = MagicMock()
        response.usage = MagicMock()
        response.usage.prompt_tokens = 100
        response.usage.completion_tokens = 50
        response.usage.total_tokens = 150

        result = LLMAdapter._extract_token_usage(response)
        assert result == {"prompt_tokens": 100, "completion_tokens": 50, "total_tokens": 150}

    def test_handles_none_usage(self, adapter: LLMAdapter):
        """Should return zeros when usage is None."""
        response = MagicMock()
        response.usage = None

        result = LLMAdapter._extract_token_usage(response)
        assert result == {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}

    def test_handles_missing_usage_attribute(self, adapter: LLMAdapter):
        """Should handle response without usage attribute."""
        response = MagicMock(spec=[])  # No attributes

        result = LLMAdapter._extract_token_usage(response)
        assert result == {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
