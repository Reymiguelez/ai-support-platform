from collections.abc import Sequence
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.models.knowledge import KnowledgeBase, KnowledgeBaseDocument, KnowledgeBaseStatus
from app.infrastructure.repositories.base import BaseRepository


class KnowledgeBaseRepository(BaseRepository[KnowledgeBase]):
    def __init__(self, session: AsyncSession):
        super().__init__(KnowledgeBase, session)

    async def get_all_active(self, skip: int = 0, limit: int = 100) -> Sequence[KnowledgeBase]:
        result = await self.session.execute(
            select(KnowledgeBase)
            .where(KnowledgeBase.status == KnowledgeBaseStatus.ACTIVE)
            .offset(skip)
            .limit(limit)
        )
        return result.scalars().all()

    async def add_document(self, kb_id: UUID, document_id: UUID) -> KnowledgeBaseDocument:
        kb_doc = KnowledgeBaseDocument(knowledge_base_id=kb_id, document_id=document_id)
        self.session.add(kb_doc)
        await self.session.flush()
        await self.session.refresh(kb_doc)
        return kb_doc

    async def remove_document(self, kb_id: UUID, document_id: UUID) -> bool:
        from sqlalchemy import delete

        result = await self.session.execute(
            delete(KnowledgeBaseDocument).where(
                KnowledgeBaseDocument.knowledge_base_id == kb_id,
                KnowledgeBaseDocument.document_id == document_id,
            )
        )
        return result.rowcount > 0

    async def get_documents(self, kb_id: UUID) -> Sequence[KnowledgeBaseDocument]:
        result = await self.session.execute(
            select(KnowledgeBaseDocument).where(KnowledgeBaseDocument.knowledge_base_id == kb_id)
        )
        return result.scalars().all()
