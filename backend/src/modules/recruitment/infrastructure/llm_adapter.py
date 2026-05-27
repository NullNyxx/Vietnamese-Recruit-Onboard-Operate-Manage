"""LLM Adapter for the Recruitment module.

Communicates with an OpenAI-compatible API (via the openai Python SDK)
for email intent classification and CV parsing into structured data.

Features:
- Intent classification with 15-second timeout
- CV parsing with 30-second timeout
- Retry with exponential backoff (1s, 2s, 4s) up to 3 attempts
- Invalid JSON retry with simplified prompt
- Token usage tracking for audit logging
- Structured logging for retry attempts
"""

from __future__ import annotations

import asyncio
import json
import logging
from dataclasses import dataclass
from typing import Any

from openai import APIConnectionError, APIStatusError, APITimeoutError, AsyncOpenAI

from src.modules.recruitment.domain.enums import EmailIntent
from src.modules.recruitment.domain.exceptions import LLMParseError
from src.modules.recruitment.domain.value_objects import ParsedCV
from src.modules.recruitment.infrastructure.config import RecruitmentSettings

logger = logging.getLogger(__name__)


# Backoff delays in seconds for retry attempts
_BACKOFF_DELAYS = [1, 2, 4]


@dataclass(frozen=True)
class IntentResult:
    """Result of intent classification including token usage for audit."""

    intent: EmailIntent
    token_usage: dict[str, int]


@dataclass(frozen=True)
class ParsedCVResult:
    """Result of CV parsing including token usage for audit."""

    parsed_cv: ParsedCV
    token_usage: dict[str, int]


class LLMAdapter:
    """Communicates with LLM via OpenAI-compatible API for intent classification and CV parsing.

    Uses the openai Python SDK (AsyncOpenAI) with a custom base_url pointing
    to the configured LLM endpoint (default: 9Router at http://127.0.0.1:20128/v1).

    Args:
        settings: RecruitmentSettings instance with LLM connection details.
    """

    def __init__(self, settings: RecruitmentSettings) -> None:
        self._settings = settings
        self._client = AsyncOpenAI(
            base_url=settings.llm_base_url,
            api_key=settings.llm_api_key or "not-needed",
            timeout=settings.llm_parse_timeout_seconds,
        )
        self._model = settings.llm_model

    async def classify_intent(
        self,
        subject: str,
        sender: str,
        snippet: str,
        attachment_filenames: list[str],
    ) -> IntentResult:
        """Classify email intent using LLM.

        Constructs a prompt with email metadata and asks the LLM to classify
        the email into one of the valid intents: cv, partner, event, internal, other.

        Args:
            subject: Email subject line.
            sender: Sender email address.
            snippet: First 200 characters of email body.
            attachment_filenames: List of attachment filenames.

        Returns:
            IntentResult with the classified intent and token usage.

        Raises:
            LLMParseError: If all retry attempts are exhausted.
        """
        prompt = self._build_intent_prompt(subject, sender, snippet, attachment_filenames)
        messages = [
            {
                "role": "system",
                "content": (
                    "You are an email classifier for an HR recruitment system. "
                    "Classify the email into exactly one category. "
                    "Respond with ONLY one word: cv, partner, event, internal, or other. "
                    "No explanation, no punctuation, just the category word."
                ),
            },
            {"role": "user", "content": prompt},
        ]

        last_error: Exception | None = None
        max_retries = self._settings.llm_max_retries

        for attempt in range(max_retries):
            try:
                response = await asyncio.wait_for(
                    self._client.chat.completions.create(
                        model=self._model,
                        messages=messages,
                        temperature=0.0,
                        max_tokens=10,
                    ),
                    timeout=self._settings.llm_intent_timeout_seconds,
                )

                raw_content = (response.choices[0].message.content or "").strip().lower()
                token_usage = self._extract_token_usage(response)

                # Parse the intent from the response
                intent = self._parse_intent_response(raw_content)
                return IntentResult(intent=intent, token_usage=token_usage)

            except TimeoutError as exc:
                last_error = exc
                logger.warning(
                    "LLM intent classification timeout on attempt %d/%d",
                    attempt + 1,
                    max_retries,
                    extra={
                        "attempt": attempt + 1,
                        "timeout_seconds": self._settings.llm_intent_timeout_seconds,
                    },
                )
            except (APITimeoutError, APIConnectionError, APIStatusError) as exc:
                last_error = exc
                logger.warning(
                    "LLM intent classification error on attempt %d/%d: %s",
                    attempt + 1,
                    max_retries,
                    str(exc),
                    extra={"attempt": attempt + 1, "error_type": type(exc).__name__},
                )

            # Apply exponential backoff before next retry
            if attempt < max_retries - 1:
                delay = _BACKOFF_DELAYS[min(attempt, len(_BACKOFF_DELAYS) - 1)]
                logger.info(
                    "Retrying intent classification in %ds (attempt %d/%d)",
                    delay,
                    attempt + 2,
                    max_retries,
                )
                await asyncio.sleep(delay)

        raise LLMParseError(
            f"Intent classification failed after {max_retries} attempts: {last_error}"
        )

    async def parse_cv(self, ocr_text: str) -> ParsedCVResult:
        """Parse OCR text into structured CV data using LLM.

        Constructs a prompt instructing the LLM to extract structured JSON
        matching the ParsedCV schema from the OCR text.

        Args:
            ocr_text: OCR-extracted text from the CV document.

        Returns:
            ParsedCVResult with the parsed CV data and token usage.

        Raises:
            LLMParseError: If all retry attempts are exhausted (including
                the simplified prompt retry for invalid JSON).
        """
        messages = self._build_cv_parse_messages(ocr_text)

        last_error: Exception | None = None
        max_retries = self._settings.llm_max_retries

        for attempt in range(max_retries):
            try:
                response = await asyncio.wait_for(
                    self._client.chat.completions.create(
                        model=self._model,
                        messages=messages,
                        temperature=0.0,
                        max_tokens=4096,
                    ),
                    timeout=self._settings.llm_parse_timeout_seconds,
                )

                raw_content = (response.choices[0].message.content or "").strip()
                token_usage = self._extract_token_usage(response)

                # Try to parse the JSON response
                parsed_cv = self._parse_cv_json(raw_content)
                if parsed_cv is not None:
                    return ParsedCVResult(parsed_cv=parsed_cv, token_usage=token_usage)

                # Invalid JSON — retry once with simplified prompt
                logger.warning(
                    "LLM returned invalid JSON on attempt %d/%d, retrying with simplified prompt",
                    attempt + 1,
                    max_retries,
                    extra={"attempt": attempt + 1, "raw_response_length": len(raw_content)},
                )
                simplified_result = await self._retry_with_simplified_prompt(ocr_text)
                if simplified_result is not None:
                    return simplified_result

                # Simplified prompt also failed
                last_error = ValueError("Invalid JSON from LLM after simplified retry")

            except TimeoutError as exc:
                last_error = exc
                logger.warning(
                    "LLM CV parse timeout on attempt %d/%d",
                    attempt + 1,
                    max_retries,
                    extra={
                        "attempt": attempt + 1,
                        "timeout_seconds": self._settings.llm_parse_timeout_seconds,
                    },
                )
            except (APITimeoutError, APIConnectionError, APIStatusError) as exc:
                last_error = exc
                logger.warning(
                    "LLM CV parse error on attempt %d/%d: %s",
                    attempt + 1,
                    max_retries,
                    str(exc),
                    extra={"attempt": attempt + 1, "error_type": type(exc).__name__},
                )

            # Apply exponential backoff before next retry
            if attempt < max_retries - 1:
                delay = _BACKOFF_DELAYS[min(attempt, len(_BACKOFF_DELAYS) - 1)]
                logger.info(
                    "Retrying CV parse in %ds (attempt %d/%d)",
                    delay,
                    attempt + 2,
                    max_retries,
                )
                await asyncio.sleep(delay)

        raise LLMParseError(f"CV parsing failed after {max_retries} attempts: {last_error}")

    # ─── Private helpers ───────────────────────────────────────────────

    def _build_intent_prompt(
        self,
        subject: str,
        sender: str,
        snippet: str,
        attachment_filenames: list[str],
    ) -> str:
        """Build the classification prompt with all email metadata."""
        attachments_info = ""
        if attachment_filenames:
            attachments_info = f"\nAttachments ({len(attachment_filenames)} files): " + ", ".join(
                attachment_filenames
            )
        else:
            attachments_info = "\nAttachments: none"

        return (
            f"Classify this email into one of: cv, partner, event, internal, other\n\n"
            f"Subject: {subject}\n"
            f"Sender: {sender}\n"
            f"Snippet: {snippet}"
            f"{attachments_info}\n\n"
            f"Category:"
        )

    def _build_cv_parse_messages(self, ocr_text: str) -> list[dict[str, str]]:
        """Build the CV parse prompt messages."""
        system_prompt = (
            "You are a CV/resume parser. Extract structured information from the CV text below. "
            "Respond with ONLY valid JSON matching this exact schema:\n"
            "{\n"
            '  "name": "string (full name, max 200 chars)",\n'
            '  "email": "string (email address, max 254 chars)",\n'
            '  "phone": "string (phone number, max 20 chars, empty string if not found)",\n'
            '  "skills": ["string array of skills, max 50 items"],\n'
            '  "experience": [{"company": "string", "title": "string", '
            '"duration": "string", "description": "string"}],\n'
            '  "education": [{"institution": "string", "degree": "string", '
            '"field": "string", "year": "string"}],\n'
            '  "summary": "string (brief professional summary, max 500 chars)"\n'
            "}\n\n"
            "Rules:\n"
            "- Return ONLY the JSON object, no markdown code blocks, no explanation\n"
            "- If a field is not found in the CV, use empty string or empty array\n"
            "- Extract Vietnamese names and content as-is with diacritics preserved\n"
            "- For experience and education, extract up to 20 and 10 items respectively"
        )

        return [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Parse this CV:\n\n{ocr_text}"},
        ]

    async def _retry_with_simplified_prompt(self, ocr_text: str) -> ParsedCVResult | None:
        """Retry CV parsing with a simplified prompt emphasizing JSON format.

        This is called when the initial parse returns invalid JSON.
        Uses a more explicit prompt that strongly emphasizes the JSON requirement.

        Returns:
            ParsedCVResult if successful, None if the simplified retry also fails.
        """
        simplified_system = (
            "You are a JSON extractor. Your ONLY job is to output valid JSON.\n"
            "Extract these fields from the text and return ONLY a JSON object:\n"
            '{"name":"","email":"","phone":"","skills":[],'
            '"experience":[],"education":[],"summary":""}\n'
            "IMPORTANT: Output ONLY the JSON. No text before or after. No markdown."
        )

        messages = [
            {"role": "system", "content": simplified_system},
            {"role": "user", "content": ocr_text[:3000]},  # Truncate for simplified retry
        ]

        try:
            response = await asyncio.wait_for(
                self._client.chat.completions.create(
                    model=self._model,
                    messages=messages,
                    temperature=0.0,
                    max_tokens=2048,
                ),
                timeout=self._settings.llm_parse_timeout_seconds,
            )

            raw_content = (response.choices[0].message.content or "").strip()
            token_usage = self._extract_token_usage(response)

            parsed_cv = self._parse_cv_json(raw_content)
            if parsed_cv is not None:
                return ParsedCVResult(parsed_cv=parsed_cv, token_usage=token_usage)

        except (TimeoutError, APITimeoutError, APIConnectionError, APIStatusError) as exc:
            logger.warning(
                "Simplified prompt retry also failed: %s",
                str(exc),
                extra={"error_type": type(exc).__name__},
            )

        return None

    def _parse_intent_response(self, raw_response: str) -> EmailIntent:
        """Parse the LLM response into an EmailIntent enum value.

        If the response cannot be mapped to a valid intent, defaults to OTHER
        per requirement 1.10.

        Args:
            raw_response: Raw lowercase response from the LLM.

        Returns:
            The parsed EmailIntent value.
        """
        # Clean up common LLM response artifacts
        cleaned = raw_response.strip().strip('"').strip("'").strip(".").lower()

        try:
            return EmailIntent(cleaned)
        except ValueError:
            # Check if the response contains a valid intent as a substring
            for intent in EmailIntent:
                if intent.value in cleaned:
                    return intent

            logger.warning(
                "LLM returned unparseable intent response, defaulting to OTHER: %r",
                raw_response,
                extra={"raw_response": raw_response},
            )
            return EmailIntent.OTHER

    def _parse_cv_json(self, raw_content: str) -> ParsedCV | None:
        """Attempt to parse the LLM response as a ParsedCV JSON object.

        Handles common LLM response issues like markdown code blocks.

        Args:
            raw_content: Raw response content from the LLM.

        Returns:
            ParsedCV if parsing succeeds, None otherwise.
        """
        # Strip markdown code block wrappers if present
        content = raw_content
        if content.startswith("```"):
            # Remove opening ```json or ``` line
            lines = content.split("\n")
            if lines[0].startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]
            content = "\n".join(lines)

        try:
            data = json.loads(content)
        except (json.JSONDecodeError, ValueError):
            return None

        if not isinstance(data, dict):
            return None

        try:
            return ParsedCV.model_validate(data)
        except Exception:
            return None

    @staticmethod
    def _extract_token_usage(response: Any) -> dict[str, int]:
        """Extract token usage from the API response.

        Args:
            response: The chat completion response object.

        Returns:
            Dictionary with prompt_tokens, completion_tokens, and total_tokens.
        """
        usage = getattr(response, "usage", None)
        if usage is None:
            return {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}

        return {
            "prompt_tokens": getattr(usage, "prompt_tokens", 0) or 0,
            "completion_tokens": getattr(usage, "completion_tokens", 0) or 0,
            "total_tokens": getattr(usage, "total_tokens", 0) or 0,
        }
