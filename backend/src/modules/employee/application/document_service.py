"""Application service for Employee Document Vault operations.

Orchestrates document listing, upload, download, and deletion by
coordinating between DocumentRepository, EmployeeRepository, and
MinIOClient while enforcing file size and MIME type constraints.
"""

from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import UUID

from src.modules.employee.domain.entities import EmployeeDocument
from src.modules.employee.domain.exceptions import (
    EmployeeError,
    EmployeeNotFoundError,
    FileTooLargeError,
    UnsupportedFileTypeError,
)

if TYPE_CHECKING:
    from src.modules.employee.infrastructure.config import EmployeeSettings
    from src.modules.employee.infrastructure.document_repository import (
        DocumentRepository,
    )
    from src.modules.employee.infrastructure.employee_repository import (
        EmployeeRepository,
    )
    from src.modules.employee.infrastructure.minio_client import MinIOClient

#: MIME types accepted for document uploads.
ALLOWED_MIME_TYPES: set[str] = {
    "application/pdf",
    "image/jpeg",
    "image/png",
    "image/gif",
    "application/msword",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
}


class DocumentService:
    """Handles document vault business logic and coordinates storage.

    Validates employee existence, file size limits, and MIME type
    restrictions before delegating to MinIO for storage and
    DocumentRepository for metadata persistence.

    Args:
        document_repository: Repository for document metadata persistence.
        employee_repository: Repository for employee existence checks.
        minio_client: MinIO adapter for file storage operations.
        settings: Employee module settings (file size limits, etc.).
    """

    def __init__(
        self,
        document_repository: DocumentRepository,
        employee_repository: EmployeeRepository,
        minio_client: MinIOClient,
        settings: EmployeeSettings,
    ) -> None:
        """Initialize DocumentService with required dependencies.

        Args:
            document_repository: Repository for document CRUD operations.
            employee_repository: Repository for employee lookups.
            minio_client: MinIO client for file storage.
            settings: Employee module configuration.
        """
        self._document_repo = document_repository
        self._employee_repo = employee_repository
        self._minio_client = minio_client
        self._settings = settings

    async def list_documents(self, employee_id: UUID) -> list[EmployeeDocument]:
        """Retrieve all documents for a given employee.

        Args:
            employee_id: The UUID of the employee whose documents to list.

        Returns:
            A list of EmployeeDocument entities sorted by uploaded_at descending.

        Raises:
            EmployeeNotFoundError: If no employee exists with the given ID.
        """
        employee = await self._employee_repo.get_by_id(employee_id)
        if employee is None:
            raise EmployeeNotFoundError()

        return await self._document_repo.list_by_employee(employee_id)

    async def upload_document(
        self,
        employee_id: UUID,
        document_type: str,
        file_name: str,
        file_data: bytes,
        content_type: str,
    ) -> EmployeeDocument:
        """Upload a document to the employee document vault.

        Validates employee existence, file size, and MIME type before
        storing the file in MinIO and persisting metadata.

        Args:
            employee_id: The UUID of the employee to attach the document to.
            document_type: Category of the document (e.g., "cccd", "degree").
            file_name: Original filename of the uploaded file.
            file_data: Raw file bytes.
            content_type: MIME type of the file.

        Returns:
            The created EmployeeDocument entity with metadata.

        Raises:
            EmployeeNotFoundError: If no employee exists with the given ID.
            FileTooLargeError: If file_data exceeds the configured max size.
            UnsupportedFileTypeError: If content_type is not in the allowed list.
        """
        # Validate employee exists
        employee = await self._employee_repo.get_by_id(employee_id)
        if employee is None:
            raise EmployeeNotFoundError()

        # Validate file size
        max_bytes = self._settings.max_file_size_mb * 1024 * 1024
        if len(file_data) > max_bytes:
            raise FileTooLargeError()

        # Validate MIME type
        if content_type not in ALLOWED_MIME_TYPES:
            raise UnsupportedFileTypeError()

        # Generate storage path
        storage_path = f"employees/{employee_id}/{document_type}/{file_name}"

        # Upload to MinIO
        await self._minio_client.upload_file(storage_path, file_data, content_type)

        # Create metadata record
        document = EmployeeDocument(
            employee_id=employee_id,
            document_type=document_type,
            file_name=file_name,
            storage_path=storage_path,
            file_size=len(file_data),
            mime_type=content_type,
        )

        return await self._document_repo.create(document)

    async def download_document(self, document_id: UUID) -> tuple[EmployeeDocument, bytes]:
        """Download a document from the vault.

        Retrieves document metadata and fetches the file bytes from MinIO.

        Args:
            document_id: The UUID of the document to download.

        Returns:
            A tuple of (EmployeeDocument metadata, raw file bytes).

        Raises:
            EmployeeError: If no document exists with the given ID.
        """
        document = await self._document_repo.get_by_id(document_id)
        if document is None:
            raise EmployeeError("Document not found")

        file_data = await self._minio_client.download_file(document.storage_path)
        return document, file_data

    async def delete_document(self, document_id: UUID) -> None:
        """Delete a document from the vault.

        Removes the file from MinIO and deletes the metadata record.

        Args:
            document_id: The UUID of the document to delete.

        Raises:
            EmployeeError: If no document exists with the given ID.
        """
        document = await self._document_repo.get_by_id(document_id)
        if document is None:
            raise EmployeeError("Document not found")

        # Delete from MinIO
        await self._minio_client.delete_file(document.storage_path)

        # Delete metadata from DB
        await self._document_repo.delete(document_id)
