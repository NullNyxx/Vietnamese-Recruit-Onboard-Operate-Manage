"""CV Processor Service for the Recruitment module.

Orchestrates the full CV processing pipeline: download attachments,
validate, upload to MinIO, OCR extraction, PII redaction, LLM parse,
confidence check, and candidate creation or flagging for review.

Requirements: 2.1, 2.2, 2.3, 2.4, 2.5, 2.6, 2.7, 3.1, 4.1, 4.2,
4.3, 4.4, 4.5, 4.7, 4.8, 4.9, 5.8, 16.1, 16.2, 16.4, 16.5, 16.6
"""

from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass
from typing import Protocol, runtime_checkable
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.recruitment.application.confidence import calculate_confidence_score
from src.modules.recruitment.application.validators import validate_attachment
from src.modules.recruitment.domain.entities import Candidate, CVDocument
from src.modules.recruitment.domain.enums import ProcessingStatus
from src.modules.recruitment.domain.exceptions import (
    CVDocumentNotFoundError,
    LLMParseError,
    OCRExtractionError,
    PipelineTimeoutError,
)
from src.modules.recruitment.domain.value_objects import ParsedCV
from src.modules.recruitment.infrastructure.audit_repository import log_audit
from src.modules.recruitment.infrastructure.config import RecruitmentSettings
from src.modules.recruitment.infrastructure.filename_sanitizer import sanitize_filename
from src.modules.recruitment.infrastructure.llm_adapter import LLMAdapter
from src.modules.recruitment.infrastructure.minio_client import RecruitmentMinIOClient
from src.modules.recruitment.infrastructure.ocr_adapter import OCRAdapter
from src.modules.recruitment.infrastructure.pii_redactor import PIIRedactor
from src.modules.recruitment.infrastructure.repositories import (
    CandidateRepository,
    CVDocumentRepository,
)

logger = logging.getLogger(__name__)


# Minimum OCR text length to proceed with LLM parsing
_MIN_OCR_TEXT_LENGTH = 50


@dataclass
class AttachmentInput:
    """Input data for a single attachment to process.

    Attributes:
        filename: Original filename of the attachment.
        mime_type: MIME type of the attachment.
        size_bytes: Size of the attachment in bytes.
        data: Raw binary data of the attachment.
    """

    filename: str
    mime_type: str
    size_bytes: int
    data: bytes


@runtime_checkable
class CandidateCreator(Protocol):
    """Protocol for creating/updating candidates from parsed CV data.

    Abstracts the CandidateService to avoid circular imports.
    """

    async def create_or_update_candidate(
        self,
        parsed_cv: ParsedCV,
        cv_document_id: UUID,
        source_email_id: UUID | None,
        confidence_score: float,
    ) -> Candidate:
        """Create new or update existing candidate by email match."""
        ...


class CVProcessorService:
    """Orchestrates the full CV processing pipeline.

    Coordinates downloading attachments, validating, uploading to MinIO,
    OCR text extraction, PII redaction, LLM parsing, confidence scoring,
    and candidate creation or flagging for manual review.

    Pipeline status transitions:
        pending → ocr_processing → llm_parsing → completed/needs_review/failed

    Args:
        minio_client: MinIO client for CV file storage.
        ocr_adapter: OCR adapter for text extraction.
        llm_adapter: LLM adapter for CV parsing.
        pii_redactor: PII redactor for sanitizing text before LLM.
        candidate_repo: Repository for candidate persistence.
        cv_document_repo: Repository for CV document persistence.
        settings: Recruitment module configuration.
        session: Async database session.
        candidate_creator: Optional protocol for creating candidates.
    """

    def __init__(
        self,
        minio_client: RecruitmentMinIOClient,
        ocr_adapter: OCRAdapter,
        llm_adapter: LLMAdapter,
        pii_redactor: PIIRedactor,
        candidate_repo: CandidateRepository,
        cv_document_repo: CVDocumentRepository,
        settings: RecruitmentSettings,
        session: AsyncSession,
        candidate_creator: CandidateCreator | None = None,
    ) -> None:
        self._minio_client = minio_client
        self._ocr_adapter = ocr_adapter
        self._llm_adapter = llm_adapter
        self._pii_redactor = pii_redactor
        self._candidate_repo = candidate_repo
        self._cv_document_repo = cv_document_repo
        self._settings = settings
        self._session = session
        self._candidate_creator = candidate_creator

    async def process_cv_from_email(
        self,
        email_message_id: UUID,
        attachments: list[AttachmentInput],
        gmail_message_id: str | None = None,
    ) -> list[CVDocument]:
        """Orchestrate full CV processing pipeline for an email's attachments.

        For each attachment:
        1. Validate MIME type and size — skip invalid ones
        2. Sanitize filename and upload to MinIO
        3. Run OCR text extraction
        4. PII-redact OCR text
        5. LLM parse into structured CV data
        6. Calculate confidence score
        7. Create candidate (if confidence >= threshold) or flag for review

        Uses asyncio.wait_for with pipeline_timeout_seconds for overall timeout.
        Processes attachments sequentially within the timeout boundary.
        If one attachment fails, continues processing the remaining ones.

        Args:
            email_message_id: UUID of the email message being processed.
            attachments: List of attachment data to process.
            gmail_message_id: Optional Gmail message ID string for storage path.

        Returns:
            List of CVDocument records created during processing.

        Raises:
            PipelineTimeoutError: If overall processing exceeds timeout.
        """
        msg_id_str = gmail_message_id or str(email_message_id)

        async def _process_all() -> list[CVDocument]:
            results: list[CVDocument] = []
            sanitized_names: list[str] = []

            for attachment in attachments:
                try:
                    cv_doc = await self.process_single_attachment(
                        email_message_id=email_message_id,
                        attachment=attachment,
                        gmail_message_id=msg_id_str,
                        existing_filenames=sanitized_names,
                    )
                    results.append(cv_doc)
                    sanitized_names.append(cv_doc.original_filename)
                except Exception as exc:
                    logger.error(
                        "Failed to process attachment '%s' for email %s: %s",
                        attachment.filename,
                        msg_id_str,
                        exc,
                        extra={
                            "gmail_message_id": msg_id_str,
                            "attachment_filename": attachment.filename,
                        },
                    )
                    # Continue processing remaining attachments
            return results

        try:
            return await asyncio.wait_for(
                _process_all(),
                timeout=self._settings.pipeline_timeout_seconds,
            )
        except TimeoutError:
            logger.error(
                "CV processing pipeline timed out for email %s (timeout: %ds)",
                msg_id_str,
                self._settings.pipeline_timeout_seconds,
                extra={"gmail_message_id": msg_id_str},
            )
            raise PipelineTimeoutError(
                f"CV processing pipeline timed out after "
                f"{self._settings.pipeline_timeout_seconds}s for email {msg_id_str}"
            )

    async def process_single_attachment(
        self,
        email_message_id: UUID,
        attachment: AttachmentInput,
        gmail_message_id: str,
        existing_filenames: list[str] | None = None,
    ) -> CVDocument:
        """Process one attachment through the full pipeline with status tracking.

        Pipeline steps:
        1. Validate MIME type and size
        2. Sanitize filename, upload to MinIO
        3. Create CVDocument record (status: pending)
        4. OCR text extraction (status: ocr_processing)
        5. PII redaction + LLM parse (status: llm_parsing)
        6. Confidence check → completed/needs_review

        Args:
            email_message_id: UUID of the source email message.
            attachment: The attachment data to process.
            gmail_message_id: Gmail message ID for storage path.
            existing_filenames: Already-used filenames for deduplication.

        Returns:
            The CVDocument record with final processing status.
        """
        start_time = time.monotonic()

        # Step 1: Validate attachment
        validation = validate_attachment(
            mime_type=attachment.mime_type,
            size_bytes=attachment.size_bytes,
            max_file_size_bytes=self._settings.max_file_size_bytes,
        )
        if not validation.is_valid:
            logger.warning(
                "Attachment '%s' failed validation for email %s: %s",
                attachment.filename,
                gmail_message_id,
                validation.error_message,
                extra={
                    "gmail_message_id": gmail_message_id,
                    "attachment_filename": attachment.filename,
                },
            )
            # Create a skipped CVDocument record
            cv_doc = CVDocument(
                gmail_message_id=gmail_message_id,
                original_filename=attachment.filename,
                mime_type=attachment.mime_type,
                size_bytes=attachment.size_bytes,
                file_path="",
                processing_status=ProcessingStatus.SKIPPED,
                processing_error=validation.error_message,
            )
            cv_doc = await self._cv_document_repo.create(cv_doc)
            await self._session.commit()
            return cv_doc

        # Step 2: Sanitize filename and upload to MinIO
        safe_filename = sanitize_filename(
            attachment.filename,
            existing_filenames=existing_filenames,
        )

        try:
            file_path = await self._minio_client.upload_cv(
                file_data=attachment.data,
                gmail_message_id=gmail_message_id,
                sanitized_filename=safe_filename,
                content_type=attachment.mime_type,
            )
        except Exception as exc:
            logger.error(
                "MinIO upload failed for '%s' (email %s): %s",
                safe_filename,
                gmail_message_id,
                exc,
            )
            cv_doc = CVDocument(
                gmail_message_id=gmail_message_id,
                original_filename=safe_filename,
                mime_type=attachment.mime_type,
                size_bytes=attachment.size_bytes,
                file_path="",
                processing_status=ProcessingStatus.UPLOAD_FAILED,
                processing_error=f"MinIO upload failed: {exc}",
            )
            cv_doc = await self._cv_document_repo.create(cv_doc)
            await self._session.commit()
            return cv_doc

        # Step 3: Create CVDocument record with status pending
        cv_doc = CVDocument(
            gmail_message_id=gmail_message_id,
            original_filename=safe_filename,
            mime_type=attachment.mime_type,
            size_bytes=attachment.size_bytes,
            file_path=file_path,
            processing_status=ProcessingStatus.PENDING,
        )
        cv_doc = await self._cv_document_repo.create(cv_doc)
        await self._session.commit()

        # Step 4: OCR text extraction
        cv_doc = await self._run_ocr(cv_doc, attachment.data, safe_filename)
        if cv_doc.processing_status == ProcessingStatus.FAILED:
            return cv_doc

        # Step 5: PII redaction + LLM parse
        cv_doc = await self._run_llm_parse(cv_doc)
        if cv_doc.processing_status == ProcessingStatus.FAILED:
            return cv_doc

        # Step 6: Confidence check and candidate creation
        cv_doc = await self._handle_confidence_routing(cv_doc, email_message_id)

        # Log audit entry for pipeline completion
        latency_ms = int((time.monotonic() - start_time) * 1000)
        await log_audit(
            session=self._session,
            operation_type="cv_pipeline_complete",
            entity_type="cv_document",
            entity_id=cv_doc.id,
            new_value={
                "processing_status": cv_doc.processing_status,
                "confidence_score": cv_doc.confidence_score,
                "gmail_message_id": gmail_message_id,
            },
            change_summary=(
                f"CV pipeline completed: status={cv_doc.processing_status}, "
                f"confidence={cv_doc.confidence_score}"
            ),
            latency_ms=latency_ms,
            success=cv_doc.processing_status
            in (ProcessingStatus.COMPLETED, ProcessingStatus.NEEDS_REVIEW),
        )

        return cv_doc

    async def retry_llm_parse(self, cv_document_id: UUID) -> ParsedCV | None:
        """Re-run LLM parse on stored OCR text for a specific CVDocument.

        Used for manual review retry when the initial LLM parse failed
        or produced low-confidence results.

        Args:
            cv_document_id: UUID of the CVDocument to retry parsing for.

        Returns:
            ParsedCV if parsing succeeds, None if it fails again.

        Raises:
            CVDocumentNotFoundError: If the CVDocument doesn't exist.
        """
        cv_doc = await self._cv_document_repo.get_by_id(cv_document_id)
        if cv_doc is None:
            raise CVDocumentNotFoundError(f"CV document not found: {cv_document_id}")

        if not cv_doc.ocr_output:
            logger.warning(
                "Cannot retry LLM parse for CV document %s: no OCR output stored",
                cv_document_id,
            )
            return None

        start_time = time.monotonic()

        # Update status to llm_parsing
        cv_doc.processing_status = ProcessingStatus.LLM_PARSING
        cv_doc.retry_count += 1
        cv_doc = await self._cv_document_repo.update(cv_doc)
        await self._session.commit()

        # PII redact the stored OCR text (guaranteed non-None by check above)
        redacted_text = self._pii_redactor.redact(cv_doc.ocr_output or "")

        try:
            parse_result = await self._llm_adapter.parse_cv(redacted_text)
            parsed_cv = parse_result.parsed_cv

            # Calculate confidence
            confidence = calculate_confidence_score(parsed_cv)

            # Update CVDocument with new parse results
            cv_doc.parsed_cv_data = parsed_cv.model_dump()
            cv_doc.confidence_score = confidence

            if confidence >= self._settings.auto_accept_threshold:
                cv_doc.processing_status = ProcessingStatus.COMPLETED
            else:
                cv_doc.processing_status = ProcessingStatus.NEEDS_REVIEW

            cv_doc.processing_error = None
            cv_doc = await self._cv_document_repo.update(cv_doc)
            await self._session.commit()

            # Log audit
            latency_ms = int((time.monotonic() - start_time) * 1000)
            await log_audit(
                session=self._session,
                operation_type="cv_parse_retry",
                entity_type="cv_document",
                entity_id=cv_doc.id,
                new_value={
                    "confidence_score": confidence,
                    "processing_status": cv_doc.processing_status,
                    "retry_count": cv_doc.retry_count,
                },
                change_summary=(f"LLM parse retry succeeded: confidence={confidence:.2f}"),
                model_name=self._settings.llm_model,
                token_usage=parse_result.token_usage,
                latency_ms=latency_ms,
                success=True,
            )

            return parsed_cv

        except LLMParseError as exc:
            cv_doc.processing_status = ProcessingStatus.FAILED
            cv_doc.processing_error = f"LLM parse retry failed: {exc}"
            cv_doc = await self._cv_document_repo.update(cv_doc)
            await self._session.commit()

            latency_ms = int((time.monotonic() - start_time) * 1000)
            await log_audit(
                session=self._session,
                operation_type="cv_parse_retry",
                entity_type="cv_document",
                entity_id=cv_doc.id,
                change_summary=f"LLM parse retry failed: {exc}",
                latency_ms=latency_ms,
                success=False,
            )

            logger.error(
                "LLM parse retry failed for CV document %s: %s",
                cv_document_id,
                exc,
            )
            return None

    # ─── Private pipeline steps ────────────────────────────────────────

    async def _run_ocr(self, cv_doc: CVDocument, file_data: bytes, filename: str) -> CVDocument:
        """Run OCR text extraction on the file and update CVDocument.

        Updates processing_status to ocr_processing during extraction,
        then stores the OCR output. Marks as failed if OCR fails or
        produces insufficient text.

        Args:
            cv_doc: The CVDocument record to update.
            file_data: Raw file bytes for OCR.
            filename: Filename for the OCR request.

        Returns:
            Updated CVDocument with OCR results or failure status.
        """
        # Transition to ocr_processing
        cv_doc.processing_status = ProcessingStatus.OCR_PROCESSING
        cv_doc = await self._cv_document_repo.update(cv_doc)
        await self._session.commit()

        start_time = time.monotonic()

        try:
            ocr_text = await self._ocr_adapter.extract_text(
                file_content=file_data,
                filename=filename,
                mime_type=cv_doc.mime_type,
            )
        except OCRExtractionError as exc:
            cv_doc.processing_status = ProcessingStatus.FAILED
            cv_doc.processing_error = f"OCR extraction failed: {exc}"
            cv_doc = await self._cv_document_repo.update(cv_doc)
            await self._session.commit()

            await log_audit(
                session=self._session,
                operation_type="ocr_extraction",
                entity_type="cv_document",
                entity_id=cv_doc.id,
                change_summary=f"OCR failed: {exc}",
                latency_ms=int((time.monotonic() - start_time) * 1000),
                success=False,
            )
            return cv_doc

        # Check minimum text length (Requirement 4.9)
        if len(ocr_text.strip()) < _MIN_OCR_TEXT_LENGTH:
            cv_doc.processing_status = ProcessingStatus.FAILED
            cv_doc.processing_error = "OCR produced insufficient text (< 50 chars)"
            cv_doc.ocr_output = ocr_text
            cv_doc = await self._cv_document_repo.update(cv_doc)
            await self._session.commit()

            await log_audit(
                session=self._session,
                operation_type="ocr_extraction",
                entity_type="cv_document",
                entity_id=cv_doc.id,
                change_summary=(f"OCR insufficient text: {len(ocr_text.strip())} chars"),
                latency_ms=int((time.monotonic() - start_time) * 1000),
                success=False,
            )
            return cv_doc

        # Store OCR output
        cv_doc.ocr_output = ocr_text
        cv_doc = await self._cv_document_repo.update(cv_doc)
        await self._session.commit()

        await log_audit(
            session=self._session,
            operation_type="ocr_extraction",
            entity_type="cv_document",
            entity_id=cv_doc.id,
            change_summary=f"OCR completed: {len(ocr_text)} chars extracted",
            latency_ms=int((time.monotonic() - start_time) * 1000),
            success=True,
        )

        return cv_doc

    async def _run_llm_parse(self, cv_doc: CVDocument) -> CVDocument:
        """Run PII redaction and LLM parse on OCR text.

        Updates processing_status to llm_parsing during the parse,
        then stores the parsed CV data and confidence score.

        Args:
            cv_doc: The CVDocument with OCR output to parse.

        Returns:
            Updated CVDocument with parse results or failure status.
        """
        # Transition to llm_parsing
        cv_doc.processing_status = ProcessingStatus.LLM_PARSING
        cv_doc = await self._cv_document_repo.update(cv_doc)
        await self._session.commit()

        start_time = time.monotonic()

        # PII redact OCR text before sending to LLM
        redacted_text = self._pii_redactor.redact(cv_doc.ocr_output or "")

        try:
            parse_result = await self._llm_adapter.parse_cv(redacted_text)
        except LLMParseError as exc:
            cv_doc.processing_status = ProcessingStatus.FAILED
            cv_doc.processing_error = f"LLM parse failed: {exc}"
            cv_doc = await self._cv_document_repo.update(cv_doc)
            await self._session.commit()

            await log_audit(
                session=self._session,
                operation_type="cv_parse",
                entity_type="cv_document",
                entity_id=cv_doc.id,
                change_summary=f"LLM parse failed: {exc}",
                model_name=self._settings.llm_model,
                latency_ms=int((time.monotonic() - start_time) * 1000),
                success=False,
            )
            return cv_doc

        parsed_cv = parse_result.parsed_cv
        confidence = calculate_confidence_score(parsed_cv)

        # Store parse results on CVDocument
        cv_doc.parsed_cv_data = parsed_cv.model_dump()
        cv_doc.confidence_score = confidence
        cv_doc = await self._cv_document_repo.update(cv_doc)
        await self._session.commit()

        # Log audit for successful parse
        latency_ms = int((time.monotonic() - start_time) * 1000)
        await log_audit(
            session=self._session,
            operation_type="cv_parse",
            entity_type="cv_document",
            entity_id=cv_doc.id,
            new_value={
                "confidence_score": confidence,
                "has_name": bool(parsed_cv.name),
                "has_email": bool(parsed_cv.email),
                "skills_count": len(parsed_cv.skills),
                "experience_count": len(parsed_cv.experience),
            },
            change_summary=(
                f"CV parsed: confidence={confidence:.2f}, "
                f"name={'yes' if parsed_cv.name else 'no'}, "
                f"email={'yes' if parsed_cv.email else 'no'}"
            ),
            model_name=self._settings.llm_model,
            token_usage=parse_result.token_usage,
            latency_ms=latency_ms,
            success=True,
        )

        return cv_doc

    async def _handle_confidence_routing(
        self,
        cv_doc: CVDocument,
        email_message_id: UUID,
    ) -> CVDocument:
        """Route CVDocument based on confidence score threshold.

        If confidence >= auto_accept_threshold (0.7): create/update candidate,
        set status to completed.
        If confidence < threshold: set status to needs_review.

        Args:
            cv_doc: CVDocument with parsed data and confidence score.
            email_message_id: UUID of the source email for candidate linking.

        Returns:
            Updated CVDocument with final processing status.
        """
        confidence = cv_doc.confidence_score or 0.0
        threshold = self._settings.auto_accept_threshold

        if confidence >= threshold:
            # Auto-accept: create or update candidate
            if self._candidate_creator and cv_doc.parsed_cv_data:
                try:
                    parsed_cv = ParsedCV.model_validate(cv_doc.parsed_cv_data)
                    await self._candidate_creator.create_or_update_candidate(
                        parsed_cv=parsed_cv,
                        cv_document_id=cv_doc.id,
                        source_email_id=email_message_id,
                        confidence_score=confidence,
                    )
                except Exception as exc:
                    logger.error(
                        "Failed to create candidate for CV document %s: %s",
                        cv_doc.id,
                        exc,
                    )
                    # Still mark as completed — candidate creation failure
                    # shouldn't block the pipeline
            cv_doc.processing_status = ProcessingStatus.COMPLETED
        else:
            # Below threshold: flag for manual review
            cv_doc.processing_status = ProcessingStatus.NEEDS_REVIEW

        cv_doc = await self._cv_document_repo.update(cv_doc)
        await self._session.commit()

        logger.info(
            "CV document %s routed: confidence=%.2f, threshold=%.2f, status=%s",
            cv_doc.id,
            confidence,
            threshold,
            cv_doc.processing_status,
            extra={
                "cv_document_id": str(cv_doc.id),
                "confidence_score": confidence,
                "processing_status": cv_doc.processing_status,
            },
        )

        return cv_doc
