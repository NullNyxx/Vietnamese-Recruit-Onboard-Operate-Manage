"""Repository for EmployeeDocument entity CRUD operations.

Provides async database access for document listing, lookup,
creation, and hard-delete using SQLAlchemy async sessions with SQLModel.
"""

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from src.modules.employee.domain.entities import EmployeeDocument


class DocumentRepository:
    """Handles EmployeeDocument entity persistence using async SQLAlchemy sessions.

    Attributes:
        session: The async database session for executing queries.
    """

    def __init__(self, session: AsyncSession) -> None:
        """Initialize the repository with an async database session.

        Args:
            session: An SQLAlchemy AsyncSession instance for database operations.
        """
        self.session = session

    async def list_by_employee(self, employee_id: UUID) -> list[EmployeeDocument]:
        """Retrieve all documents for a given employee, ordered by upload date descending.

        Args:
            employee_id: The UUID of the employee whose documents to retrieve.

        Returns:
            A list of EmployeeDocument entities sorted by uploaded_at descending.
        """
        statement = (
            select(EmployeeDocument)
            .where(EmployeeDocument.employee_id == employee_id)
            .order_by(EmployeeDocument.uploaded_at.desc())  # type: ignore[union-attr]
        )
        result = await self.session.execute(statement)
        return list(result.scalars().all())

    async def get_by_id(self, document_id: UUID) -> EmployeeDocument | None:
        """Retrieve a single document by its unique identifier.

        Args:
            document_id: The UUID primary key of the document.

        Returns:
            The EmployeeDocument entity if found, None otherwise.
        """
        statement = select(EmployeeDocument).where(EmployeeDocument.id == document_id)
        result = await self.session.execute(statement)
        return result.scalars().first()

    async def create(self, document: EmployeeDocument) -> EmployeeDocument:
        """Persist a new document entity to the database.

        Args:
            document: The EmployeeDocument entity to create.

        Returns:
            The persisted EmployeeDocument entity with generated fields populated.
        """
        self.session.add(document)
        await self.session.flush()
        return document

    async def delete(self, document_id: UUID) -> bool:
        """Hard-delete a document from the database.

        Args:
            document_id: The UUID of the document to delete.

        Returns:
            True if the document was found and deleted, False otherwise.
        """
        statement = select(EmployeeDocument).where(EmployeeDocument.id == document_id)
        result = await self.session.execute(statement)
        document = result.scalars().first()

        if document is None:
            return False

        await self.session.delete(document)
        await self.session.flush()
        return True
