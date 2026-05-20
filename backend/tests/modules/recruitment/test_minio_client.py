"""Tests for Recruitment MinIO client adapter."""

from unittest.mock import AsyncMock, patch

import pytest
from botocore.exceptions import ClientError, EndpointConnectionError

from src.modules.recruitment.domain.exceptions import (
    CVFileNotFoundError,
    StorageServiceUnavailableError,
)
from src.modules.recruitment.infrastructure.config import RecruitmentSettings
from src.modules.recruitment.infrastructure.minio_client import RecruitmentMinIOClient


@pytest.fixture
def settings(monkeypatch: pytest.MonkeyPatch) -> RecruitmentSettings:
    monkeypatch.setenv("RECRUITMENT_MINIO_ENDPOINT", "localhost:9000")
    monkeypatch.setenv("RECRUITMENT_MINIO_ACCESS_KEY", "testkey")
    monkeypatch.setenv("RECRUITMENT_MINIO_SECRET_KEY", "testsecret")
    monkeypatch.setenv("RECRUITMENT_MINIO_BUCKET_NAME", "test-cv-bucket")
    monkeypatch.setenv("RECRUITMENT_PRESIGNED_URL_EXPIRY_SECONDS", "900")
    return RecruitmentSettings()


@pytest.fixture
def client(settings: RecruitmentSettings) -> RecruitmentMinIOClient:
    return RecruitmentMinIOClient(settings)


def _make_client_error(code: str) -> ClientError:
    """Helper to create a botocore ClientError with a specific error code."""
    return ClientError(
        error_response={"Error": {"Code": code, "Message": "test error"}},
        operation_name="test",
    )


class TestRecruitmentMinIOClientInit:
    """Verify RecruitmentMinIOClient initialization."""

    def test_endpoint_url_uses_http_prefix(self, client: RecruitmentMinIOClient) -> None:
        assert client._endpoint_url == "http://localhost:9000"

    def test_stores_settings(
        self, client: RecruitmentMinIOClient, settings: RecruitmentSettings
    ) -> None:
        assert client._settings is settings


class TestUploadCV:
    """Verify upload_cv behavior."""

    async def test_upload_cv_returns_correct_path(self, client: RecruitmentMinIOClient) -> None:
        mock_s3 = AsyncMock()
        mock_s3.head_bucket = AsyncMock()
        mock_s3.upload_fileobj = AsyncMock()

        mock_context = AsyncMock()
        mock_context.__aenter__ = AsyncMock(return_value=mock_s3)
        mock_context.__aexit__ = AsyncMock(return_value=False)

        with patch.object(client, "_client_context", return_value=mock_context):
            result = await client.upload_cv(
                file_data=b"pdf-content",
                gmail_message_id="msg123",
                sanitized_filename="resume.pdf",
                content_type="application/pdf",
            )

        assert result == "storage/cv/msg123/resume.pdf"

    async def test_upload_cv_calls_upload_fileobj_with_correct_params(
        self, client: RecruitmentMinIOClient
    ) -> None:
        mock_s3 = AsyncMock()
        mock_s3.head_bucket = AsyncMock()
        mock_s3.upload_fileobj = AsyncMock()

        mock_context = AsyncMock()
        mock_context.__aenter__ = AsyncMock(return_value=mock_s3)
        mock_context.__aexit__ = AsyncMock(return_value=False)

        with patch.object(client, "_client_context", return_value=mock_context):
            await client.upload_cv(
                file_data=b"data",
                gmail_message_id="abc456",
                sanitized_filename="cv.docx",
                content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            )

        mock_s3.upload_fileobj.assert_called_once()
        call_args = mock_s3.upload_fileobj.call_args
        assert call_args[0][1] == "test-cv-bucket"
        assert call_args[0][2] == "storage/cv/abc456/cv.docx"
        assert call_args[1]["ExtraArgs"] == {
            "ContentType": "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        }

    async def test_upload_cv_creates_bucket_if_not_exists(
        self, client: RecruitmentMinIOClient
    ) -> None:
        mock_s3 = AsyncMock()
        mock_s3.head_bucket = AsyncMock(side_effect=_make_client_error("404"))
        mock_s3.create_bucket = AsyncMock()
        mock_s3.upload_fileobj = AsyncMock()

        mock_context = AsyncMock()
        mock_context.__aenter__ = AsyncMock(return_value=mock_s3)
        mock_context.__aexit__ = AsyncMock(return_value=False)

        with patch.object(client, "_client_context", return_value=mock_context):
            await client.upload_cv(
                file_data=b"data",
                gmail_message_id="msg1",
                sanitized_filename="file.pdf",
                content_type="application/pdf",
            )

        mock_s3.create_bucket.assert_called_once_with(Bucket="test-cv-bucket")

    async def test_upload_cv_raises_storage_unavailable_on_connection_error(
        self, client: RecruitmentMinIOClient
    ) -> None:
        mock_context = AsyncMock()
        mock_context.__aenter__ = AsyncMock(
            side_effect=EndpointConnectionError(endpoint_url="http://localhost:9000")
        )
        mock_context.__aexit__ = AsyncMock(return_value=False)

        with patch.object(client, "_client_context", return_value=mock_context):
            with pytest.raises(StorageServiceUnavailableError):
                await client.upload_cv(
                    file_data=b"data",
                    gmail_message_id="msg1",
                    sanitized_filename="file.pdf",
                    content_type="application/pdf",
                )


class TestDownloadCV:
    """Verify download_cv behavior."""

    async def test_download_cv_returns_bytes(self, client: RecruitmentMinIOClient) -> None:
        mock_body = AsyncMock()
        mock_body.read = AsyncMock(return_value=b"file-content")

        mock_s3 = AsyncMock()
        mock_s3.get_object = AsyncMock(return_value={"Body": mock_body})

        mock_context = AsyncMock()
        mock_context.__aenter__ = AsyncMock(return_value=mock_s3)
        mock_context.__aexit__ = AsyncMock(return_value=False)

        with patch.object(client, "_client_context", return_value=mock_context):
            result = await client.download_cv("storage/cv/msg123/resume.pdf")

        assert result == b"file-content"

    async def test_download_cv_uses_correct_bucket_and_key(
        self, client: RecruitmentMinIOClient
    ) -> None:
        mock_body = AsyncMock()
        mock_body.read = AsyncMock(return_value=b"data")

        mock_s3 = AsyncMock()
        mock_s3.get_object = AsyncMock(return_value={"Body": mock_body})

        mock_context = AsyncMock()
        mock_context.__aenter__ = AsyncMock(return_value=mock_s3)
        mock_context.__aexit__ = AsyncMock(return_value=False)

        with patch.object(client, "_client_context", return_value=mock_context):
            await client.download_cv("storage/cv/msg456/doc.pdf")

        mock_s3.get_object.assert_called_once_with(
            Bucket="test-cv-bucket", Key="storage/cv/msg456/doc.pdf"
        )

    async def test_download_cv_raises_file_not_found_on_no_such_key(
        self, client: RecruitmentMinIOClient
    ) -> None:
        mock_s3 = AsyncMock()
        mock_s3.get_object = AsyncMock(side_effect=_make_client_error("NoSuchKey"))

        mock_context = AsyncMock()
        mock_context.__aenter__ = AsyncMock(return_value=mock_s3)
        mock_context.__aexit__ = AsyncMock(return_value=False)

        with patch.object(client, "_client_context", return_value=mock_context):
            with pytest.raises(CVFileNotFoundError):
                await client.download_cv("storage/cv/nonexistent/file.pdf")

    async def test_download_cv_raises_storage_unavailable_on_connection_error(
        self, client: RecruitmentMinIOClient
    ) -> None:
        mock_context = AsyncMock()
        mock_context.__aenter__ = AsyncMock(
            side_effect=EndpointConnectionError(endpoint_url="http://localhost:9000")
        )
        mock_context.__aexit__ = AsyncMock(return_value=False)

        with patch.object(client, "_client_context", return_value=mock_context):
            with pytest.raises(StorageServiceUnavailableError):
                await client.download_cv("storage/cv/msg1/file.pdf")


class TestDeleteCV:
    """Verify delete_cv behavior."""

    async def test_delete_cv_calls_delete_object(self, client: RecruitmentMinIOClient) -> None:
        mock_s3 = AsyncMock()
        mock_s3.delete_object = AsyncMock()

        mock_context = AsyncMock()
        mock_context.__aenter__ = AsyncMock(return_value=mock_s3)
        mock_context.__aexit__ = AsyncMock(return_value=False)

        with patch.object(client, "_client_context", return_value=mock_context):
            await client.delete_cv("storage/cv/msg123/resume.pdf")

        mock_s3.delete_object.assert_called_once_with(
            Bucket="test-cv-bucket", Key="storage/cv/msg123/resume.pdf"
        )

    async def test_delete_cv_returns_none(self, client: RecruitmentMinIOClient) -> None:
        mock_s3 = AsyncMock()
        mock_s3.delete_object = AsyncMock()

        mock_context = AsyncMock()
        mock_context.__aenter__ = AsyncMock(return_value=mock_s3)
        mock_context.__aexit__ = AsyncMock(return_value=False)

        with patch.object(client, "_client_context", return_value=mock_context):
            result = await client.delete_cv("storage/cv/msg1/file.pdf")

        assert result is None

    async def test_delete_cv_raises_storage_unavailable_on_connection_error(
        self, client: RecruitmentMinIOClient
    ) -> None:
        mock_context = AsyncMock()
        mock_context.__aenter__ = AsyncMock(
            side_effect=EndpointConnectionError(endpoint_url="http://localhost:9000")
        )
        mock_context.__aexit__ = AsyncMock(return_value=False)

        with patch.object(client, "_client_context", return_value=mock_context):
            with pytest.raises(StorageServiceUnavailableError):
                await client.delete_cv("storage/cv/msg1/file.pdf")


class TestGeneratePresignedUrl:
    """Verify generate_presigned_url behavior."""

    async def test_generate_presigned_url_returns_url(
        self, client: RecruitmentMinIOClient
    ) -> None:
        mock_s3 = AsyncMock()
        mock_s3.head_object = AsyncMock()
        mock_s3.generate_presigned_url = AsyncMock(
            return_value="http://localhost:9000/test-cv-bucket/storage/cv/msg1/file.pdf?signature=abc"
        )

        mock_context = AsyncMock()
        mock_context.__aenter__ = AsyncMock(return_value=mock_s3)
        mock_context.__aexit__ = AsyncMock(return_value=False)

        with patch.object(client, "_client_context", return_value=mock_context):
            result = await client.generate_presigned_url("storage/cv/msg1/file.pdf")

        assert "localhost:9000" in result
        assert "file.pdf" in result

    async def test_generate_presigned_url_uses_default_expiry(
        self, client: RecruitmentMinIOClient
    ) -> None:
        mock_s3 = AsyncMock()
        mock_s3.head_object = AsyncMock()
        mock_s3.generate_presigned_url = AsyncMock(return_value="http://url")

        mock_context = AsyncMock()
        mock_context.__aenter__ = AsyncMock(return_value=mock_s3)
        mock_context.__aexit__ = AsyncMock(return_value=False)

        with patch.object(client, "_client_context", return_value=mock_context):
            await client.generate_presigned_url("storage/cv/msg1/file.pdf")

        mock_s3.generate_presigned_url.assert_called_once_with(
            "get_object",
            Params={"Bucket": "test-cv-bucket", "Key": "storage/cv/msg1/file.pdf"},
            ExpiresIn=900,
        )

    async def test_generate_presigned_url_uses_custom_expiry(
        self, client: RecruitmentMinIOClient
    ) -> None:
        mock_s3 = AsyncMock()
        mock_s3.head_object = AsyncMock()
        mock_s3.generate_presigned_url = AsyncMock(return_value="http://url")

        mock_context = AsyncMock()
        mock_context.__aenter__ = AsyncMock(return_value=mock_s3)
        mock_context.__aexit__ = AsyncMock(return_value=False)

        with patch.object(client, "_client_context", return_value=mock_context):
            await client.generate_presigned_url("storage/cv/msg1/file.pdf", expires_seconds=300)

        mock_s3.generate_presigned_url.assert_called_once_with(
            "get_object",
            Params={"Bucket": "test-cv-bucket", "Key": "storage/cv/msg1/file.pdf"},
            ExpiresIn=300,
        )

    async def test_generate_presigned_url_raises_file_not_found(
        self, client: RecruitmentMinIOClient
    ) -> None:
        mock_s3 = AsyncMock()
        mock_s3.head_object = AsyncMock(side_effect=_make_client_error("404"))

        mock_context = AsyncMock()
        mock_context.__aenter__ = AsyncMock(return_value=mock_s3)
        mock_context.__aexit__ = AsyncMock(return_value=False)

        with patch.object(client, "_client_context", return_value=mock_context):
            with pytest.raises(CVFileNotFoundError):
                await client.generate_presigned_url("storage/cv/nonexistent/file.pdf")

    async def test_generate_presigned_url_raises_storage_unavailable_on_connection_error(
        self, client: RecruitmentMinIOClient
    ) -> None:
        mock_context = AsyncMock()
        mock_context.__aenter__ = AsyncMock(
            side_effect=EndpointConnectionError(endpoint_url="http://localhost:9000")
        )
        mock_context.__aexit__ = AsyncMock(return_value=False)

        with patch.object(client, "_client_context", return_value=mock_context):
            with pytest.raises(StorageServiceUnavailableError):
                await client.generate_presigned_url("storage/cv/msg1/file.pdf")
