from uuid import UUID

from app.core.config import settings
from app.core.logging import get_logger
from app.infrastructure.ai.client import openai_client
from app.infrastructure.ai.vector_store import ChromaVectorStore, VectorStore

logger = get_logger(__name__)


class RAGService:
    def __init__(self, vector_store: VectorStore | None = None):
        self.vector_store = vector_store or ChromaVectorStore(
            host=settings.CHROMA_HOST,
            port=settings.CHROMA_PORT,
        )
        self.collection_name = settings.CHROMA_COLLECTION_NAME

    async def index_document_chunks(
        self,
        document_id: UUID,
        chunks: list[dict],
        knowledge_base_id: UUID | None = None,
    ) -> list[str]:
        if not chunks:
            return []

        texts = [chunk["content"] for chunk in chunks]
        metadatas = [
            {
                "document_id": str(document_id),
                "chunk_index": chunk["chunk_index"],
                "knowledge_base_id": str(knowledge_base_id) if knowledge_base_id else None,
                **chunk.get("metadata", {}),
            }
            for chunk in chunks
        ]
        ids = [f"{document_id}_{chunk['chunk_index']}" for chunk in chunks]

        logger.info("Generating embeddings for chunks", count=len(texts))
        embeddings = await openai_client.create_embeddings_batch(texts)

        await self.vector_store.add_documents(
            collection_name=self.collection_name,
            documents=texts,
            embeddings=embeddings,
            metadatas=metadatas,
            ids=ids,
        )

        logger.info("Document chunks indexed", document_id=str(document_id), chunks=len(chunks))
        return ids

    async def search_relevant_chunks(
        self,
        query: str,
        top_k: int = 5,
        similarity_threshold: float = 0.7,
        knowledge_base_id: UUID | None = None,
    ) -> list[dict]:
        query_embedding = await openai_client.create_embedding(query)

        filter_metadata = {}
        if knowledge_base_id:
            filter_metadata["knowledge_base_id"] = str(knowledge_base_id)

        results = await self.vector_store.search(
            collection_name=self.collection_name,
            query_embedding=query_embedding,
            top_k=top_k,
            similarity_threshold=similarity_threshold,
            filter_metadata=filter_metadata if filter_metadata else None,
        )

        logger.info("RAG search completed", query=query[:50], results=len(results))
        return results

    async def delete_document_chunks(self, document_id: UUID) -> None:
        ids = [f"{document_id}_{i}" for i in range(10000)]
        await self.vector_store.delete_documents(self.collection_name, ids)
        logger.info("Document chunks deleted from vector store", document_id=str(document_id))

    async def build_context(self, chunks: list[dict], max_tokens: int = 3000) -> str:
        context_parts = []
        current_tokens = 0

        for chunk in chunks:
            chunk_text = f"[Source: {chunk.get('metadata', {}).get('document_id', 'unknown')}]\n{chunk['content']}"
            chunk_tokens = len(chunk_text.split()) * 1.3

            if current_tokens + chunk_tokens > max_tokens:
                break

            context_parts.append(chunk_text)
            current_tokens += chunk_tokens

        return "\n\n---\n\n".join(context_parts)


rag_service = RAGService()
