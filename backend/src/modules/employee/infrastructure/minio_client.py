"""MinIO client adapter for employee document storage.

Provides async S3-compatible operations for uploading, downloading,
and deleting files in MinIO via aioboto3.
"""

from io import BytesIO

import aioboto3

from src.modules.employee.infrastructure.config import EmployeeSettings


class MinIOClient:
    """Async MinIO client using aioboto3 for S3-compatible operations.

    The bucket is auto-created on first upload if it doesn't exist.

    Args:
        settings: EmployeeSettings instance with MinIO connection details.
    """

    def __init__(self, settings: EmployeeSettings) -> None:
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
            await client.head_bucket(Bucket=self._settings.minio_bucket)
        except client.exceptions.ClientError:
            await client.create_bucket(Bucket=self._settings.minio_bucket)

    async def upload_file(self, path: str, file_data: bytes, content_type: str) -> str:
        """Upload a file to MinIO.

        Args:
            path: The storage path (key) within the bucket.
            file_data: Raw file bytes to upload.
            content_type: MIME type of the file.

        Returns:
            The storage path where the file was stored.
        """
        async with self._client_context() as client:
            await self._ensure_bucket(client)
            await client.upload_fileobj(
                BytesIO(file_data),
                self._settings.minio_bucket,
                path,
                ExtraArgs={"ContentType": content_type},
            )
        return path

    async def download_file(self, path: str) -> bytes:
        """Download a file from MinIO.

        Args:
            path: The storage path (key) within the bucket.

        Returns:
            The raw file bytes.
        """
        async with self._client_context() as client:
            response = await client.get_object(
                Bucket=self._settings.minio_bucket,
                Key=path,
            )
            data = await response["Body"].read()
        return data

    async def delete_file(self, path: str) -> None:
        """Delete a file from MinIO.

        Args:
            path: The storage path (key) within the bucket.
        """
        async with self._client_context() as client:
            await client.delete_object(
                Bucket=self._settings.minio_bucket,
                Key=path,
            )

    async def generate_presigned_url(self, path: str, expires_seconds: int = 900) -> str:
        """Generate a pre-signed download URL for a file.

        Args:
            path: The storage path (key) within the bucket.
            expires_seconds: URL expiry in seconds. Defaults to 900 (15 minutes).

        Returns:
            A pre-signed URL string valid for the specified duration.

        Raises:
            FileNotFoundError: If the file does not exist in storage.
            OSError: If MinIO is unreachable or another storage error occurs.
        """
        async with self._client_context() as client:
            # Verify the object exists before generating URL
            try:
                await client.head_object(
                    Bucket=self._settings.minio_bucket,
                    Key=path,
                )
            except Exception as exc:
                raise FileNotFoundError(f"File not found at path: {path}") from exc

            url: str = await client.generate_presigned_url(
                "get_object",
                Params={
                    "Bucket": self._settings.minio_bucket,
                    "Key": path,
                },
                ExpiresIn=expires_seconds,
            )
            return url
