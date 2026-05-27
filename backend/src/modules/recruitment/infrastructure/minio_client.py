"""MinIO client adapter for recruitment CV storage.

Provides async S3-compatible operations for uploading, downloading,
deleting CV files, and generating presigned URLs in MinIO via aioboto3.

Storage path format: storage/cv/{gmail_message_id}/{sanitized_filename}
"""

from io import BytesIO

import aioboto3
from botocore.exceptions import ClientError, EndpointConnectionError

from src.modules.recruitment.domain.exceptions import (
    CVFileNotFoundError,
    StorageServiceUnavailableError,
)
from src.modules.recruitment.infrastructure.config import RecruitmentSettings


class RecruitmentMinIOClient:
    """Async MinIO client for CV file storage using aioboto3.

    Follows the same pattern as the employee module MinIO client.
    The bucket is auto-created on first upload if it doesn't exist.

    Args:
        settings: RecruitmentSettings instance with MinIO connection details.
    """

    def __init__(self, settings: RecruitmentSettings) -> None:
        self._settings = settings
        self._session = aioboto3.Session()
        self._endpoint_url = f"http://{settings.minio_endpoint}"

    def _client_context(self):
        """Create an S3 client context manager."""
        return self._session.client(
            "s3",
            endpoint_url=self._endpoint_url,
            aws_access_key_id=self._settings.minio_access_key,
            aws_secret_access_key=self._settings.minio_secret_key,
        )

    async def _ensure_bucket(self, client) -> None:
        """Create the bucket if it doesn't already exist."""
        try:
            await client.head_bucket(Bucket=self._settings.minio_bucket_name)
        except ClientError:
            await client.create_bucket(Bucket=self._settings.minio_bucket_name)

    async def upload_cv(
        self, file_data: bytes, gmail_message_id: str, sanitized_filename: str, content_type: str
    ) -> str:
        """Upload a CV file to MinIO.

        Args:
            file_data: Raw file bytes to upload.
            gmail_message_id: Gmail message ID used in the storage path.
            sanitized_filename: Sanitized filename for the storage path.
            content_type: MIME type of the file.

        Returns:
            The storage path where the file was stored.

        Raises:
            StorageServiceUnavailableError: If MinIO is unreachable.
        """
        path = f"storage/cv/{gmail_message_id}/{sanitized_filename}"
        try:
            async with self._client_context() as client:
                await self._ensure_bucket(client)
                await client.upload_fileobj(
                    BytesIO(file_data),
                    self._settings.minio_bucket_name,
                    path,
                    ExtraArgs={"ContentType": content_type},
                )
        except EndpointConnectionError as exc:
            raise StorageServiceUnavailableError(f"Cannot connect to MinIO: {exc}") from exc
        except OSError as exc:
            raise StorageServiceUnavailableError(
                f"Storage service connection failed: {exc}"
            ) from exc
        return path

    async def download_cv(self, path: str) -> bytes:
        """Download a CV file from MinIO.

        Args:
            path: The storage path (key) within the bucket.

        Returns:
            The raw file bytes.

        Raises:
            CVFileNotFoundError: If the file does not exist in storage.
            StorageServiceUnavailableError: If MinIO is unreachable.
        """
        try:
            async with self._client_context() as client:
                response = await client.get_object(
                    Bucket=self._settings.minio_bucket_name,
                    Key=path,
                )
                data = await response["Body"].read()
        except ClientError as exc:
            error_code = exc.response.get("Error", {}).get("Code", "")
            if error_code in ("NoSuchKey", "404"):
                raise CVFileNotFoundError(f"CV file not found at path: {path}") from exc
            raise StorageServiceUnavailableError(
                f"Storage error while downloading CV: {exc}"
            ) from exc
        except EndpointConnectionError as exc:
            raise StorageServiceUnavailableError(f"Cannot connect to MinIO: {exc}") from exc
        except OSError as exc:
            raise StorageServiceUnavailableError(
                f"Storage service connection failed: {exc}"
            ) from exc
        return data

    async def delete_cv(self, path: str) -> None:
        """Delete a CV file from MinIO.

        Args:
            path: The storage path (key) within the bucket.

        Raises:
            StorageServiceUnavailableError: If MinIO is unreachable.
        """
        try:
            async with self._client_context() as client:
                await client.delete_object(
                    Bucket=self._settings.minio_bucket_name,
                    Key=path,
                )
        except EndpointConnectionError as exc:
            raise StorageServiceUnavailableError(f"Cannot connect to MinIO: {exc}") from exc
        except OSError as exc:
            raise StorageServiceUnavailableError(
                f"Storage service connection failed: {exc}"
            ) from exc

    async def generate_presigned_url(self, path: str, expires_seconds: int | None = None) -> str:
        """Generate a presigned download URL for a CV file.

        Args:
            path: The storage path (key) within the bucket.
            expires_seconds: URL expiry in seconds. Defaults to the configured
                presigned_url_expiry_seconds (15 minutes).

        Returns:
            A presigned URL string valid for the specified duration.

        Raises:
            CVFileNotFoundError: If the file does not exist in storage.
            StorageServiceUnavailableError: If MinIO is unreachable.
        """
        if expires_seconds is None:
            expires_seconds = self._settings.presigned_url_expiry_seconds

        try:
            async with self._client_context() as client:
                # Verify the object exists before generating URL
                await client.head_object(
                    Bucket=self._settings.minio_bucket_name,
                    Key=path,
                )
                url = await client.generate_presigned_url(
                    "get_object",
                    Params={
                        "Bucket": self._settings.minio_bucket_name,
                        "Key": path,
                    },
                    ExpiresIn=expires_seconds,
                )
        except ClientError as exc:
            error_code = exc.response.get("Error", {}).get("Code", "")
            if error_code in ("NoSuchKey", "404"):
                raise CVFileNotFoundError(f"CV file not found at path: {path}") from exc
            raise StorageServiceUnavailableError(
                f"Storage error while generating presigned URL: {exc}"
            ) from exc
        except EndpointConnectionError as exc:
            raise StorageServiceUnavailableError(f"Cannot connect to MinIO: {exc}") from exc
        except OSError as exc:
            raise StorageServiceUnavailableError(
                f"Storage service connection failed: {exc}"
            ) from exc
        return url
