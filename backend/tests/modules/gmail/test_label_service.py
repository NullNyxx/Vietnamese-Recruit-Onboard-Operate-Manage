"""Unit tests for LabelService."""

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from src.modules.gmail.application.label_service import LabelService
from src.modules.gmail.domain.exceptions import (
    GmailFetchError,
    LabelNamespaceViolationException,
)
from src.modules.gmail.infrastructure.config import GmailSettings


@pytest.fixture
def settings() -> GmailSettings:
    """Create GmailSettings with defaults."""
    return GmailSettings()


@pytest.fixture
def gmail_adapter() -> AsyncMock:
    """Create a mocked GmailAdapter."""
    adapter = AsyncMock()
    adapter.list_labels = AsyncMock(return_value=[])
    adapter.create_label = AsyncMock(return_value="Label_123")
    adapter.modify_labels = AsyncMock()
    adapter.batch_modify_labels = AsyncMock()
    return adapter


@pytest.fixture
def label_repo() -> AsyncMock:
    """Create a mocked LabelRepository."""
    repo = AsyncMock()
    repo.get_mappings = AsyncMock(return_value=[])
    repo.upsert_mappings = AsyncMock(return_value=[])
    repo.get_label_id_by_name = AsyncMock(return_value="Label_123")
    return repo


@pytest.fixture
def audit_logger() -> AsyncMock:
    """Create a mocked AuditLogger."""
    logger = AsyncMock()
    logger.log_operation = AsyncMock()
    return logger


@pytest.fixture
def label_service(
    gmail_adapter: AsyncMock,
    label_repo: AsyncMock,
    settings: GmailSettings,
    audit_logger: AsyncMock,
) -> LabelService:
    """Create a LabelService with mocked dependencies."""
    return LabelService(
        gmail_adapter=gmail_adapter,
        label_repo=label_repo,
        settings=settings,
        audit_logger=audit_logger,
    )


class TestValidateNamespace:
    """Tests for LabelService.validate_namespace."""

    def test_accepts_label_with_vroomhr_prefix(
        self, label_service: LabelService
    ) -> None:
        """Labels starting with VroomHR/ are valid."""
        assert label_service.validate_namespace("VroomHR/processed") is True

    def test_accepts_all_required_labels(
        self, label_service: LabelService
    ) -> None:
        """All required VroomHR labels pass validation."""
        assert label_service.validate_namespace("VroomHR/recruitment") is True
        assert label_service.validate_namespace("VroomHR/interview") is True
        assert label_service.validate_namespace("VroomHR/onboarding") is True

    def test_rejects_label_without_prefix(
        self, label_service: LabelService
    ) -> None:
        """Labels without VroomHR/ prefix are invalid."""
        assert label_service.validate_namespace("INBOX") is False

    def test_rejects_empty_string(self, label_service: LabelService) -> None:
        """Empty string is invalid."""
        assert label_service.validate_namespace("") is False

    def test_rejects_similar_prefix(
        self, label_service: LabelService
    ) -> None:
        """Labels with similar but incorrect prefix are invalid."""
        assert label_service.validate_namespace("VroomHR") is False
        assert label_service.validate_namespace("vroomhr/processed") is False
        assert label_service.validate_namespace("Vroom/processed") is False

    def test_rejects_system_labels(
        self, label_service: LabelService
    ) -> None:
        """System Gmail labels are invalid."""
        assert label_service.validate_namespace("SENT") is False
        assert label_service.validate_namespace("TRASH") is False
        assert label_service.validate_namespace("SPAM") is False


class TestInitializeLabels:
    """Tests for LabelService.initialize_labels."""

    @pytest.mark.asyncio
    async def test_creates_all_labels_when_none_exist(
        self,
        label_service: LabelService,
        gmail_adapter: AsyncMock,
        label_repo: AsyncMock,
    ) -> None:
        """Creates all 4 required labels when none exist on Gmail."""
        user_id = uuid4()
        gmail_adapter.list_labels.return_value = []
        gmail_adapter.create_label.return_value = "Label_new"

        await label_service.initialize_labels(user_id, "token_abc")

        assert gmail_adapter.list_labels.call_count == 1
        assert gmail_adapter.create_label.call_count == 4
        label_repo.upsert_mappings.assert_called_once()

        # Verify all 4 labels were passed to upsert
        call_args = label_repo.upsert_mappings.call_args
        assert call_args[0][0] == user_id
        mappings = call_args[0][1]
        assert len(mappings) == 4
        label_names = {m["label_name"] for m in mappings}
        assert label_names == {
            "VroomHR/processed",
            "VroomHR/recruitment",
            "VroomHR/interview",
            "VroomHR/onboarding",
        }

    @pytest.mark.asyncio
    async def test_reuses_existing_labels(
        self,
        label_service: LabelService,
        gmail_adapter: AsyncMock,
        label_repo: AsyncMock,
    ) -> None:
        """Reuses existing label IDs without creating duplicates."""
        user_id = uuid4()

        # Simulate 2 labels already existing
        existing_label_1 = MagicMock()
        existing_label_1.name = "VroomHR/processed"
        existing_label_1.id = "Label_existing_1"
        existing_label_2 = MagicMock()
        existing_label_2.name = "VroomHR/recruitment"
        existing_label_2.id = "Label_existing_2"

        gmail_adapter.list_labels.return_value = [existing_label_1, existing_label_2]
        gmail_adapter.create_label.return_value = "Label_new"

        await label_service.initialize_labels(user_id, "token_abc")

        # Only 2 labels should be created (interview, onboarding)
        assert gmail_adapter.create_label.call_count == 2

        # Verify mappings include both existing and new
        call_args = label_repo.upsert_mappings.call_args
        mappings = call_args[0][1]
        assert len(mappings) == 4

        # Check existing labels reuse their IDs
        processed_mapping = next(
            m for m in mappings if m["label_name"] == "VroomHR/processed"
        )
        assert processed_mapping["gmail_label_id"] == "Label_existing_1"

    @pytest.mark.asyncio
    async def test_reuses_all_labels_when_all_exist(
        self,
        label_service: LabelService,
        gmail_adapter: AsyncMock,
        label_repo: AsyncMock,
    ) -> None:
        """Does not create any labels when all already exist."""
        user_id = uuid4()

        existing_labels = []
        for i, name in enumerate(
            ["VroomHR/processed", "VroomHR/recruitment", "VroomHR/interview", "VroomHR/onboarding"]
        ):
            label = MagicMock()
            label.name = name
            label.id = f"Label_{i}"
            existing_labels.append(label)

        gmail_adapter.list_labels.return_value = existing_labels

        await label_service.initialize_labels(user_id, "token_abc")

        gmail_adapter.create_label.assert_not_called()
        label_repo.upsert_mappings.assert_called_once()

    @pytest.mark.asyncio
    async def test_retries_on_creation_failure(
        self,
        label_service: LabelService,
        gmail_adapter: AsyncMock,
        label_repo: AsyncMock,
    ) -> None:
        """Retries label creation up to 3 times with exponential backoff."""
        user_id = uuid4()
        gmail_adapter.list_labels.return_value = []

        # Fail twice, succeed on third attempt
        gmail_adapter.create_label.side_effect = [
            GmailFetchError("API error"),
            GmailFetchError("API error"),
            "Label_success",
            # Remaining 3 labels succeed immediately
            "Label_2",
            "Label_3",
            "Label_4",
        ]

        with patch("asyncio.sleep", new_callable=AsyncMock):
            await label_service.initialize_labels(user_id, "token_abc")

        # 2 failures + 1 success for first label + 3 successes for others = 6 calls
        assert gmail_adapter.create_label.call_count == 6

    @pytest.mark.asyncio
    async def test_skips_label_after_all_retries_exhausted(
        self,
        label_service: LabelService,
        gmail_adapter: AsyncMock,
        label_repo: AsyncMock,
        audit_logger: AsyncMock,
    ) -> None:
        """Skips a label and continues with others when all retries fail."""
        user_id = uuid4()
        gmail_adapter.list_labels.return_value = []

        # First label fails all 3 retries, rest succeed
        gmail_adapter.create_label.side_effect = [
            GmailFetchError("API error"),
            GmailFetchError("API error"),
            GmailFetchError("API error"),
            "Label_2",
            "Label_3",
            "Label_4",
        ]

        with patch("asyncio.sleep", new_callable=AsyncMock):
            await label_service.initialize_labels(user_id, "token_abc")

        # Only 3 labels should be in mappings (first one failed)
        call_args = label_repo.upsert_mappings.call_args
        mappings = call_args[0][1]
        assert len(mappings) == 3

        # Audit should log with success=False
        audit_logger.log_operation.assert_called_once()
        audit_call = audit_logger.log_operation.call_args
        assert audit_call[1]["success"] is False

    @pytest.mark.asyncio
    async def test_logs_audit_on_success(
        self,
        label_service: LabelService,
        gmail_adapter: AsyncMock,
        audit_logger: AsyncMock,
    ) -> None:
        """Logs audit entry on successful initialization."""
        user_id = uuid4()
        gmail_adapter.list_labels.return_value = []
        gmail_adapter.create_label.return_value = "Label_new"

        await label_service.initialize_labels(user_id, "token_abc")

        audit_logger.log_operation.assert_called_once()
        call_kwargs = audit_logger.log_operation.call_args[1]
        assert call_kwargs["operation_type"] == "label_initialize"
        assert call_kwargs["user_id"] == user_id
        assert call_kwargs["success"] is True
        assert call_kwargs["message_count"] == 4


class TestAddLabel:
    """Tests for LabelService.add_label."""

    @pytest.mark.asyncio
    async def test_adds_label_to_message(
        self,
        label_service: LabelService,
        gmail_adapter: AsyncMock,
        label_repo: AsyncMock,
    ) -> None:
        """Adds a valid VroomHR label to a message."""
        user_id = uuid4()
        label_repo.get_label_id_by_name.return_value = "Label_123"

        await label_service.add_label(
            user_id, "msg_abc", "VroomHR/processed", "token_xyz"
        )

        gmail_adapter.modify_labels.assert_called_once_with(
            access_token="token_xyz",
            message_ids=["msg_abc"],
            add_labels=["Label_123"],
            remove_labels=None,
        )

    @pytest.mark.asyncio
    async def test_raises_on_namespace_violation(
        self,
        label_service: LabelService,
        gmail_adapter: AsyncMock,
    ) -> None:
        """Raises LabelNamespaceViolationException for non-VroomHR labels."""
        user_id = uuid4()

        with pytest.raises(LabelNamespaceViolationException):
            await label_service.add_label(
                user_id, "msg_abc", "INBOX", "token_xyz"
            )

        gmail_adapter.modify_labels.assert_not_called()

    @pytest.mark.asyncio
    async def test_raises_when_label_not_in_mappings(
        self,
        label_service: LabelService,
        label_repo: AsyncMock,
        gmail_adapter: AsyncMock,
    ) -> None:
        """Raises GmailFetchError when label ID is not found in repository."""
        user_id = uuid4()
        label_repo.get_label_id_by_name.return_value = None

        with pytest.raises(GmailFetchError):
            await label_service.add_label(
                user_id, "msg_abc", "VroomHR/processed", "token_xyz"
            )

        gmail_adapter.modify_labels.assert_not_called()

    @pytest.mark.asyncio
    async def test_logs_audit_on_success(
        self,
        label_service: LabelService,
        audit_logger: AsyncMock,
    ) -> None:
        """Logs audit entry after successful label addition."""
        user_id = uuid4()

        await label_service.add_label(
            user_id, "msg_abc", "VroomHR/processed", "token_xyz"
        )

        audit_logger.log_operation.assert_called_once()
        call_kwargs = audit_logger.log_operation.call_args[1]
        assert call_kwargs["operation_type"] == "label_modify"
        assert call_kwargs["metadata"]["action"] == "add"


class TestRemoveLabel:
    """Tests for LabelService.remove_label."""

    @pytest.mark.asyncio
    async def test_removes_label_from_message(
        self,
        label_service: LabelService,
        gmail_adapter: AsyncMock,
        label_repo: AsyncMock,
    ) -> None:
        """Removes a valid VroomHR label from a message."""
        user_id = uuid4()
        label_repo.get_label_id_by_name.return_value = "Label_456"

        await label_service.remove_label(
            user_id, "msg_abc", "VroomHR/recruitment", "token_xyz"
        )

        gmail_adapter.modify_labels.assert_called_once_with(
            access_token="token_xyz",
            message_ids=["msg_abc"],
            add_labels=None,
            remove_labels=["Label_456"],
        )

    @pytest.mark.asyncio
    async def test_raises_on_namespace_violation(
        self,
        label_service: LabelService,
        gmail_adapter: AsyncMock,
    ) -> None:
        """Raises LabelNamespaceViolationException for non-VroomHR labels."""
        user_id = uuid4()

        with pytest.raises(LabelNamespaceViolationException):
            await label_service.remove_label(
                user_id, "msg_abc", "SENT", "token_xyz"
            )

        gmail_adapter.modify_labels.assert_not_called()

    @pytest.mark.asyncio
    async def test_raises_when_label_not_in_mappings(
        self,
        label_service: LabelService,
        label_repo: AsyncMock,
        gmail_adapter: AsyncMock,
    ) -> None:
        """Raises GmailFetchError when label ID is not found in repository."""
        user_id = uuid4()
        label_repo.get_label_id_by_name.return_value = None

        with pytest.raises(GmailFetchError):
            await label_service.remove_label(
                user_id, "msg_abc", "VroomHR/processed", "token_xyz"
            )

        gmail_adapter.modify_labels.assert_not_called()

    @pytest.mark.asyncio
    async def test_logs_audit_on_success(
        self,
        label_service: LabelService,
        audit_logger: AsyncMock,
    ) -> None:
        """Logs audit entry after successful label removal."""
        user_id = uuid4()

        await label_service.remove_label(
            user_id, "msg_abc", "VroomHR/processed", "token_xyz"
        )

        audit_logger.log_operation.assert_called_once()
        call_kwargs = audit_logger.log_operation.call_args[1]
        assert call_kwargs["operation_type"] == "label_modify"
        assert call_kwargs["metadata"]["action"] == "remove"


class TestBatchAddLabel:
    """Tests for LabelService.batch_add_label."""

    @pytest.mark.asyncio
    async def test_batch_adds_label_to_messages(
        self,
        label_service: LabelService,
        gmail_adapter: AsyncMock,
        label_repo: AsyncMock,
    ) -> None:
        """Batch adds a label to multiple messages."""
        user_id = uuid4()
        message_ids = ["msg_1", "msg_2", "msg_3"]
        label_repo.get_label_id_by_name.return_value = "Label_789"

        await label_service.batch_add_label(
            user_id, message_ids, "VroomHR/processed", "token_xyz"
        )

        gmail_adapter.batch_modify_labels.assert_called_once_with(
            access_token="token_xyz",
            message_ids=message_ids,
            add_labels=["Label_789"],
            remove_labels=None,
        )

    @pytest.mark.asyncio
    async def test_handles_empty_message_list(
        self,
        label_service: LabelService,
        gmail_adapter: AsyncMock,
    ) -> None:
        """Returns early without API call for empty message list."""
        user_id = uuid4()

        await label_service.batch_add_label(
            user_id, [], "VroomHR/processed", "token_xyz"
        )

        gmail_adapter.batch_modify_labels.assert_not_called()

    @pytest.mark.asyncio
    async def test_raises_on_namespace_violation(
        self,
        label_service: LabelService,
        gmail_adapter: AsyncMock,
    ) -> None:
        """Raises LabelNamespaceViolationException for non-VroomHR labels."""
        user_id = uuid4()

        with pytest.raises(LabelNamespaceViolationException):
            await label_service.batch_add_label(
                user_id, ["msg_1"], "INBOX", "token_xyz"
            )

        gmail_adapter.batch_modify_labels.assert_not_called()

    @pytest.mark.asyncio
    async def test_raises_when_label_not_in_mappings(
        self,
        label_service: LabelService,
        label_repo: AsyncMock,
        gmail_adapter: AsyncMock,
    ) -> None:
        """Raises GmailFetchError when label ID is not found in repository."""
        user_id = uuid4()
        label_repo.get_label_id_by_name.return_value = None

        with pytest.raises(GmailFetchError):
            await label_service.batch_add_label(
                user_id, ["msg_1"], "VroomHR/processed", "token_xyz"
            )

        gmail_adapter.batch_modify_labels.assert_not_called()

    @pytest.mark.asyncio
    async def test_logs_audit_with_message_count(
        self,
        label_service: LabelService,
        audit_logger: AsyncMock,
    ) -> None:
        """Logs audit entry with correct message count."""
        user_id = uuid4()
        message_ids = [f"msg_{i}" for i in range(50)]

        await label_service.batch_add_label(
            user_id, message_ids, "VroomHR/processed", "token_xyz"
        )

        audit_logger.log_operation.assert_called_once()
        call_kwargs = audit_logger.log_operation.call_args[1]
        assert call_kwargs["operation_type"] == "label_modify"
        assert call_kwargs["message_count"] == 50
        assert call_kwargs["metadata"]["action"] == "batch_add"
        assert call_kwargs["metadata"]["message_count"] == 50
