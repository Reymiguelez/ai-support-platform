from collections.abc import Sequence
from uuid import UUID

from app.core.exceptions import NotFoundException, ValidationException
from app.core.logging import get_logger
from app.domain.models.knowledge import KnowledgeBase, KnowledgeBaseDocument, KnowledgeBaseStatus
from app.infrastructure.repositories.document import DocumentRepository
from app.infrastructure.repositories.knowledge import KnowledgeBaseRepository

logger = get_logger(__name__)


class KnowledgeService:
    def __init__(
        self,
        kb_repo: KnowledgeBaseRepository,
        document_repo: DocumentRepository,
    ):
        self.kb_repo = kb_repo
        self.document_repo = document_repo

    async def create_knowledge_base(
        self,
        name: str,
        description: str | None = None,
        embedding_model: str = "text-embedding-3-large",
        chunk_size: int = 1000,
        chunk_overlap: int = 200,
        top_k: int = 5,
        similarity_threshold: float = 0.7,
    ) -> KnowledgeBase:
        kb = await self.kb_repo.create(
            name=name,
            description=description,
            embedding_model=embedding_model,
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            top_k=top_k,
            similarity_threshold=similarity_threshold,
            status=KnowledgeBaseStatus.ACTIVE,
        )
        logger.info("Knowledge base created", kb_id=str(kb.id), name=name)
        return kb

    async def get_knowledge_base(self, kb_id: UUID) -> KnowledgeBase | None:
        return await self.kb_repo.get(kb_id)

    async def list_knowledge_bases(
        self,
        skip: int = 0,
        limit: int = 20,
        status: KnowledgeBaseStatus | None = None,
    ) -> tuple[Sequence[KnowledgeBase], int]:
        if status:
            kbs = await self.kb_repo.get_all_active(skip, limit)
        else:
            kbs = await self.kb_repo.get_all(skip, limit)
        total = len(kbs)
        return kbs, total

    async def update_knowledge_base(self, kb_id: UUID, **kwargs) -> KnowledgeBase | None:
        kb = await self.kb_repo.get(kb_id)
        if not kb:
            return None
        return await self.kb_repo.update(kb, **kwargs)

    async def delete_knowledge_base(self, kb_id: UUID) -> bool:
        kb = await self.kb_repo.get(kb_id)
        if not kb:
            return False
        await self.kb_repo.delete(kb)
        logger.info("Knowledge base deleted", kb_id=str(kb_id))
        return True

    async def add_document_to_kb(self, kb_id: UUID, document_id: UUID) -> KnowledgeBaseDocument:
        kb = await self.kb_repo.get(kb_id)
        if not kb:
            raise NotFoundException("Knowledge Base", str(kb_id))

        document = await self.document_repo.get(document_id)
        if not document:
            raise NotFoundException("Document", str(document_id))

        if document.status != "completed":
            raise ValidationException("Document must be processed before adding to knowledge base")

        kb_doc = await self.kb_repo.add_document(kb_id, document_id)
        logger.info("Document added to knowledge base", kb_id=str(kb_id), doc_id=str(document_id))
        return kb_doc

    async def remove_document_from_kb(self, kb_id: UUID, document_id: UUID) -> bool:
        result = await self.kb_repo.remove_document(kb_id, document_id)
        if result:
            logger.info(
                "Document removed from knowledge base", kb_id=str(kb_id), doc_id=str(document_id)
            )
        return result

    async def get_kb_documents(self, kb_id: UUID) -> Sequence[KnowledgeBaseDocument]:
        kb = await self.kb_repo.get(kb_id)
        if not kb:
            raise NotFoundException("Knowledge Base", str(kb_id))
        return await self.kb_repo.get_documents(kb_id)
