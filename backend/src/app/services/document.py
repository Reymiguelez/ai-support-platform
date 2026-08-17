import os
from collections.abc import Sequence
from datetime import UTC, datetime
from uuid import UUID, uuid4

import aiofiles

from app.core.config import settings
from app.core.exceptions import DocumentProcessingException, NotFoundException, ValidationException
from app.core.logging import get_logger
from app.domain.models.document import Document, DocumentChunk, DocumentStatus, DocumentType
from app.infrastructure.ai.document_processor import process_document
from app.infrastructure.ai.rag import rag_service
from app.infrastructure.repositories.document import DocumentChunkRepository, DocumentRepository

logger = get_logger(__name__)


class DocumentService:
    def __init__(
        self,
        document_repo: DocumentRepository,
        chunk_repo: DocumentChunkRepository,
    ):
        self.document_repo = document_repo
        self.chunk_repo = chunk_repo

    def _get_upload_path(self, user_id: UUID, filename: str) -> tuple[str, str]:
        date_path = datetime.now(UTC).strftime("%Y/%m/%d")
        unique_filename = f"{uuid4().hex}_{filename}"
        relative_path = os.path.join(settings.UPLOAD_DIR, str(user_id), date_path, unique_filename)
        full_path = os.path.join(settings.UPLOAD_DIR, str(user_id), date_path)
        return full_path, relative_path

    async def upload_document(
        self,
        user_id: UUID,
        file_content: bytes,
        filename: str,
        mime_type: str,
    ) -> Document:
        if len(file_content) > settings.MAX_FILE_SIZE:
            raise ValidationException(
                f"File size exceeds maximum allowed: {settings.MAX_FILE_SIZE} bytes"
            )

        if mime_type not in settings.ALLOWED_FILE_TYPES:
            raise ValidationException(f"File type not allowed: {mime_type}")

        full_dir, relative_path = self._get_upload_path(user_id, filename)
        os.makedirs(full_dir, exist_ok=True)
        full_file_path = os.path.join(full_dir, os.path.basename(relative_path))

        async with aiofiles.open(full_file_path, "wb") as f:
            await f.write(file_content)

        doc_type_map = {
            "application/pdf": DocumentType.PDF,
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document": DocumentType.DOCX,
            "text/plain": DocumentType.TXT,
            "text/markdown": DocumentType.MARKDOWN,
            "text/html": DocumentType.HTML,
        }

        document = await self.document_repo.create(
            user_id=user_id,
            filename=os.path.basename(relative_path),
            original_filename=filename,
            file_path=relative_path,
            file_size=len(file_content),
            mime_type=mime_type,
            document_type=doc_type_map.get(mime_type, DocumentType.TXT),
            status=DocumentStatus.PENDING,
        )

        logger.info(
            "Document uploaded",
            document_id=str(document.id),
            filename=filename,
            user_id=str(user_id),
        )
        return document

    async def process_document(self, document_id: UUID) -> Document:
        document = await self.document_repo.get(document_id)
        if not document:
            raise NotFoundException("Document", str(document_id))

        await self.document_repo.update_status(document_id, DocumentStatus.PROCESSING)

        try:
            async with aiofiles.open(document.file_path, "rb") as f:
                file_content = await f.read()

            text, page_count, chunks = await process_document(
                file_content=file_content,
                mime_type=document.mime_type,
                chunk_size=1000,
                chunk_overlap=200,
            )

            chunk_objects = [
                DocumentChunk(
                    document_id=document_id,
                    content=chunk["content"],
                    chunk_index=chunk["chunk_index"],
                    token_count=chunk["token_count"],
                    metadata=chunk["metadata"],
                )
                for chunk in chunks
            ]

            await self.chunk_repo.bulk_create(chunk_objects)

            await rag_service.index_document_chunks(document_id, chunks)

            updated_doc = await self.document_repo.update_status(
                document_id,
                DocumentStatus.COMPLETED,
                chunk_count=len(chunks),
                page_count=page_count,
            )

            logger.info(
                "Document processed successfully", document_id=str(document_id), chunks=len(chunks)
            )
            return updated_doc

        except Exception as e:
            logger.error("Document processing failed", document_id=str(document_id), error=str(e))
            await self.document_repo.update_status(
                document_id, DocumentStatus.FAILED, error_message=str(e)
            )
            raise DocumentProcessingException(f"Document processing failed: {e!s}")

    async def get_document(self, document_id: UUID, user_id: UUID) -> Document | None:
        document = await self.document_repo.get(document_id)
        if document and document.user_id == user_id:
            return document
        return None

    async def list_documents(
        self,
        user_id: UUID,
        skip: int = 0,
        limit: int = 20,
        status: DocumentStatus | None = None,
    ) -> tuple[Sequence[Document], int]:
        documents = await self.document_repo.get_by_user(user_id, skip, limit, status)
        total = await self.document_repo.count_by_user(user_id, status)
        return documents, total

    async def delete_document(self, document_id: UUID, user_id: UUID) -> bool:
        document = await self.get_document(document_id, user_id)
        if not document:
            return False

        await self.chunk_repo.delete_by_document(document_id)
        await rag_service.delete_document_chunks(document_id)

        try:
            if os.path.exists(document.file_path):
                os.remove(document.file_path)
        except Exception as e:
            logger.warning("Failed to delete file", path=document.file_path, error=str(e))

        await self.document_repo.delete(document)
        logger.info("Document deleted", document_id=str(document_id))
        return True

    async def get_document_chunks(
        self, document_id: UUID, user_id: UUID
    ) -> Sequence[DocumentChunk]:
        document = await self.get_document(document_id, user_id)
        if not document:
            raise NotFoundException("Document", str(document_id))
        return await self.chunk_repo.get_by_document(document_id)
