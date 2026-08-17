from collections.abc import Sequence
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.models.document import Document, DocumentChunk, DocumentStatus
from app.infrastructure.repositories.base import BaseRepository


class DocumentRepository(BaseRepository[Document]):
    def __init__(self, session: AsyncSession):
        super().__init__(Document, session)

    async def get_by_user(
        self,
        user_id: UUID,
        skip: int = 0,
        limit: int = 20,
        status: DocumentStatus | None = None,
    ) -> Sequence[Document]:
        query = select(Document).where(Document.user_id == user_id)
        if status:
            query = query.where(Document.status == status)
        query = query.order_by(Document.created_at.desc()).offset(skip).limit(limit)
        result = await self.session.execute(query)
        return result.scalars().all()

    async def count_by_user(self, user_id: UUID, status: DocumentStatus | None = None) -> int:
        query = select(func.count(Document.id)).where(Document.user_id == user_id)
        if status:
            query = query.where(Document.status == status)
        result = await self.session.execute(query)
        return result.scalar_one()

    async def update_status(
        self,
        document_id: UUID,
        status: DocumentStatus,
        error_message: str | None = None,
        chunk_count: int | None = None,
        page_count: int | None = None,
    ) -> Document | None:
        from datetime import UTC, datetime

        document = await self.get(document_id)
        if document:
            document.status = status
            if error_message:
                document.error_message = error_message
            if chunk_count is not None:
                document.chunk_count = chunk_count
            if page_count is not None:
                document.page_count = page_count
            if status == DocumentStatus.COMPLETED:
                document.processed_at = datetime.now(UTC)
            await self.session.flush()
            await self.session.refresh(document)
        return document


class DocumentChunkRepository(BaseRepository[DocumentChunk]):
    def __init__(self, session: AsyncSession):
        super().__init__(DocumentChunk, session)

    async def get_by_document(self, document_id: UUID) -> Sequence[DocumentChunk]:
        result = await self.session.execute(
            select(DocumentChunk)
            .where(DocumentChunk.document_id == document_id)
            .order_by(DocumentChunk.chunk_index)
        )
        return result.scalars().all()

    async def bulk_create(self, chunks: list[DocumentChunk]) -> list[DocumentChunk]:
        self.session.add_all(chunks)
        await self.session.flush()
        for chunk in chunks:
            await self.session.refresh(chunk)
        return chunks

    async def delete_by_document(self, document_id: UUID) -> int:
        from sqlalchemy import delete

        result = await self.session.execute(
            delete(DocumentChunk).where(DocumentChunk.document_id == document_id)
        )
        return result.rowcount
