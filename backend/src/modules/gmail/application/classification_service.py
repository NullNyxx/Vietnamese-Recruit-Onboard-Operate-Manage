"""Email Classification Service for the Gmail module.

Orchestrates automatic email categorization after sync using a two-tier
approach: rule-based pre-filter for obvious patterns, then LLM fallback
for ambiguous emails. Designed for Vietnamese HR context.

Flow:
1. Email synced → processing_status = "unprocessed"
2. ClassificationService.classify_batch() called
3. Rule-based classifier handles ~60% of emails (free, <10ms)
4. LLM classifier handles remaining ~40% (Gemma 4, ~1-2s)
5. Category assigned → Gmail label applied → processing_status = "classified"
"""

from __future__ import annotations

import asyncio
import logging
import time
from typing import TYPE_CHECKING
from uuid import UUID

from src.modules.gmail.domain.enums import EmailCategory
from src.modules.gmail.infrastructure.config import GmailSettings

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

    from src.modules.gmail.application.rules_classifier import RulesClassifier
    from src.modules.gmail.domain.entities import EmailMessage
    from src.modules.gmail.infrastructure.ai_classifier import (
        AIClassifier,
        ClassificationResult,
    )
    from src.modules.gmail.infrastructure.audit_logger import AuditLogger
    from src.modules.gmail.infrastructure.email_repository import EmailRepository

logger = logging.getLogger(__name__)


class ClassificationService:
    """Orchestrates email classification using rules + AI fallback.

    Processes unclassified emails in batches. For each email:
    1. Try rule-based classification (fast, free)
    2. If rules return low confidence → call AI classifier
    3. Update email category in DB
    4. Optionally apply Gmail label

    Args:
        rules_classifier: Rule-based pre-filter for obvious patterns.
        ai_classifier: LLM-based classifier for ambiguous emails.
        email_repo: Repository for email message persistence.
        audit_logger: Audit logger for tracking classification operations.
        settings: Gmail module configuration.
        session: Async database session.
    """

    def __init__(
        self,
        rules_classifier: RulesClassifier,
        ai_classifier: AIClassifier,
        email_repo: EmailRepository,
        audit_logger: AuditLogger,
        settings: GmailSettings,
        session: AsyncSession,
    ) -> None:
        self._rules = rules_classifier
        self._ai = ai_classifier
        self._email_repo = email_repo
        self._audit_logger = audit_logger
        self._settings = settings
        self._session = session

    async def classify_batch(
        self,
        user_id: UUID,
        emails: list[EmailMessage],
    ) -> int:
        """Classify a batch of unprocessed emails.

        Processes each email through the two-tier classification pipeline.
        Failures for individual emails are logged but do not stop the batch.

        Args:
            user_id: The UUID of the user who owns the emails.
            emails: List of EmailMessage entities to classify.

        Returns:
            Number of emails successfully classified.
        """
        sem = asyncio.Semaphore(self._settings.classification_batch_concurrency)

        async def _classify_one(email: EmailMessage) -> int:
            """Classify a single email under semaphore control.

            Returns 1 on success, 0 on failure.
            """
            async with sem:
                try:
                    result = await self._classify_single(email)
                    await self._apply_classification(email, result)
                    return 1
                except Exception as exc:
                    logger.error(
                        "Classification failed for email %s: %s",
                        email.gmail_message_id,
                        exc,
                        extra={"gmail_message_id": email.gmail_message_id},
                    )
                    # Mark as classification_failed for manual review
                    email.processing_status = "classification_failed"
                    self._session.add(email)
                    return 0

        results = await asyncio.gather(*[_classify_one(email) for email in emails])
        classified_count = sum(results)

        await self._session.flush()

        # Audit log the batch operation
        await self._audit_logger.log_operation(
            operation_type="classify_batch",
            user_id=user_id,
            message_count=classified_count,
            success=classified_count > 0,
            metadata={
                "total_emails": len(emails),
                "classified_count": classified_count,
                "failed_count": len(emails) - classified_count,
            },
        )

        return classified_count

    async def classify_single_email(
        self,
        user_id: UUID,
        email: EmailMessage,
    ) -> EmailCategory:
        """Classify a single email and persist the result.

        Convenience method for on-demand classification (e.g., reclassify).

        Args:
            user_id: The UUID of the user who owns the email.
            email: The EmailMessage entity to classify.

        Returns:
            The assigned EmailCategory.
        """
        result = await self._classify_single(email)
        await self._apply_classification(email, result)
        await self._session.flush()
        return result.category

    async def _classify_single(self, email: EmailMessage) -> ClassificationResult:
        """Run the two-tier classification on a single email.

        Tier 1: Rule-based classifier (keywords, sender domain, attachments).
        Tier 2: AI classifier (LLM) if rules confidence < threshold.

        Args:
            email: The EmailMessage entity to classify.

        Returns:
            ClassificationResult with category and confidence.
        """
        from src.modules.gmail.infrastructure.ai_classifier import ClassificationResult

        start_time = time.monotonic()

        # Tier 1: Rule-based classification
        rules_result = self._rules.classify(
            subject=email.subject,
            sender_email=email.sender_email,
            snippet=email.snippet,
            has_attachments=email.has_attachments,
        )

        if rules_result.confidence >= self._settings.classification_confidence_threshold:
            latency_ms = int((time.monotonic() - start_time) * 1000)
            logger.info(
                "Email %s classified by RULES as %s (confidence=%.2f, %dms) signals=%s",
                email.gmail_message_id[:10],
                rules_result.category.value,
                rules_result.confidence,
                latency_ms,
                rules_result.matched_signals[:3],
            )
            return rules_result

        # Tier 2: AI classification (LLM fallback)
        logger.info(
            "Email %s rules confidence too low (%.2f < %.2f), calling AI...",
            email.gmail_message_id[:10],
            rules_result.confidence,
            self._settings.classification_confidence_threshold,
        )
        try:
            ai_result = await self._ai.classify(
                subject=email.subject,
                sender_email=email.sender_email,
                sender_name=email.sender_name,
                snippet=email.snippet,
                has_attachments=email.has_attachments,
            )
            latency_ms = int((time.monotonic() - start_time) * 1000)
            logger.debug(
                "Email %s classified by AI as %s (confidence=%.2f, %dms)",
                email.gmail_message_id,
                ai_result.category.value,
                ai_result.confidence,
                latency_ms,
            )
            return ai_result
        except Exception as exc:
            # AI failed — fall back to rules result even if low confidence
            latency_ms = int((time.monotonic() - start_time) * 1000)
            logger.warning(
                "AI classification failed for email %s (%dms), falling back to rules result: %s",
                email.gmail_message_id,
                latency_ms,
                exc,
            )
            # If rules had some result, use it; otherwise uncategorized
            if rules_result.confidence > 0:
                return rules_result
            return ClassificationResult(
                category=EmailCategory.uncategorized,
                confidence=0.0,
                source="fallback",
            )

    async def _apply_classification(
        self,
        email: EmailMessage,
        result: ClassificationResult,
    ) -> None:
        """Persist classification result to the email record.

        Updates the email's category and processing_status fields.

        Args:
            email: The EmailMessage entity to update.
            result: The classification result to apply.
        """
        email.category = result.category.value
        email.processing_status = "classified"
        self._session.add(email)
