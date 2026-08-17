from datetime import UTC, datetime, timedelta
from uuid import UUID

from celery import shared_task

from app.core.database import get_db_context
from app.core.logging import get_logger
from app.domain.models.document import Document, DocumentStatus
from app.infrastructure.ai.document_processor import process_document
from app.infrastructure.ai.rag import rag_service
from app.infrastructure.repositories.document import DocumentChunkRepository, DocumentRepository
from app.services.email import send_email_verification, send_password_reset_email

logger = get_logger(__name__)


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def process_document_task(self, document_id: str):
    async def _process():
        async with get_db_context() as db:
            doc_repo = DocumentRepository(db)
            chunk_repo = DocumentChunkRepository(db)

            document = await doc_repo.get(UUID(document_id))
            if not document:
                logger.error("Document not found", document_id=document_id)
                return

            await doc_repo.update_status(UUID(document_id), DocumentStatus.PROCESSING)

            try:

                import aiofiles

                async with aiofiles.open(document.file_path, "rb") as f:
                    file_content = await f.read()

                text, page_count, chunks = await process_document(
                    file_content=file_content,
                    mime_type=document.mime_type,
                    chunk_size=1000,
                    chunk_overlap=200,
                )

                from app.domain.models.document import DocumentChunk

                chunk_objects = [
                    DocumentChunk(
                        document_id=UUID(document_id),
                        content=chunk["content"],
                        chunk_index=chunk["chunk_index"],
                        token_count=chunk["token_count"],
                        metadata=chunk["metadata"],
                    )
                    for chunk in chunks
                ]

                await chunk_repo.bulk_create(chunk_objects)
                await rag_service.index_document_chunks(UUID(document_id), chunks)

                await doc_repo.update_status(
                    UUID(document_id),
                    DocumentStatus.COMPLETED,
                    chunk_count=len(chunks),
                    page_count=page_count,
                )

                logger.info(
                    "Document processed successfully", document_id=document_id, chunks=len(chunks)
                )

            except Exception as e:
                logger.error("Document processing failed", document_id=document_id, error=str(e))
                await doc_repo.update_status(
                    UUID(document_id), DocumentStatus.FAILED, error_message=str(e)
                )
                raise

    import asyncio

    asyncio.run(_process())


@shared_task
def process_pending_documents():
    from sqlalchemy import select

    async def _process():
        async with get_db_context() as db:
            result = await db.execute(
                select(Document).where(Document.status == DocumentStatus.PENDING).limit(10)
            )
            documents = result.scalars().all()

            for doc in documents:
                process_document_task.delay(str(doc.id))

    import asyncio

    asyncio.run(_process())


@shared_task(bind=True, max_retries=3, default_retry_delay=30)
def send_verification_email_task(self, email: str, token: str):
    import asyncio

    asyncio.run(send_email_verification(email, token))


@shared_task(bind=True, max_retries=3, default_retry_delay=30)
def send_password_reset_email_task(self, email: str, token: str):
    import asyncio

    asyncio.run(send_password_reset_email(email, token))


@shared_task
def cleanup_expired_tokens():
    async def _cleanup():
        async with get_db_context() as db:
            pass

    import asyncio

    asyncio.run(_cleanup())
    logger.info("Expired tokens cleanup completed")


@shared_task
def cleanup_old_conversations():
    from sqlalchemy import delete

    from app.domain.models.conversation import Conversation, ConversationStatus

    async def _cleanup():
        async with get_db_context() as db:
            cutoff = datetime.now(UTC) - timedelta(days=365)
            result = await db.execute(
                delete(Conversation).where(
                    Conversation.status == ConversationStatus.ARCHIVED,
                    Conversation.updated_at < cutoff,
                )
            )
            logger.info("Old conversations cleaned up", count=result.rowcount)

    import asyncio

    asyncio.run(_cleanup())
