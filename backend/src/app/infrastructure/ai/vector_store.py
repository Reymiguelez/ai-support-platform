from abc import ABC, abstractmethod

from app.core.exceptions import VectorStoreException
from app.core.logging import get_logger

logger = get_logger(__name__)


class VectorStore(ABC):
    @abstractmethod
    async def add_documents(
        self,
        collection_name: str,
        documents: list[str],
        embeddings: list[list[float]],
        metadatas: list[dict],
        ids: list[str],
    ) -> None:
        pass

    @abstractmethod
    async def search(
        self,
        collection_name: str,
        query_embedding: list[float],
        top_k: int = 5,
        similarity_threshold: float = 0.7,
        filter_metadata: dict | None = None,
    ) -> list[dict]:
        pass

    @abstractmethod
    async def delete_documents(self, collection_name: str, ids: list[str]) -> None:
        pass

    @abstractmethod
    async def delete_collection(self, collection_name: str) -> None:
        pass


class ChromaVectorStore(VectorStore):
    def __init__(self, host: str = "localhost", port: int = 8000):
        self.host = host
        self.port = port
        self._client = None

    async def _get_client(self):
        if self._client is None:
            import chromadb

            self._client = chromadb.HttpClient(host=self.host, port=self.port)
        return self._client

    async def add_documents(
        self,
        collection_name: str,
        documents: list[str],
        embeddings: list[list[float]],
        metadatas: list[dict],
        ids: list[str],
    ) -> None:
        try:
            client = await self._get_client()
            collection = client.get_or_create_collection(name=collection_name)
            collection.add(
                documents=documents,
                embeddings=embeddings,
                metadatas=metadatas,
                ids=ids,
            )
            logger.info(
                "Documents added to vector store", collection=collection_name, count=len(documents)
            )
        except Exception as e:
            logger.error("Failed to add documents to vector store", error=str(e))
            raise VectorStoreException(f"Failed to add documents: {e!s}")

    async def search(
        self,
        collection_name: str,
        query_embedding: list[float],
        top_k: int = 5,
        similarity_threshold: float = 0.7,
        filter_metadata: dict | None = None,
    ) -> list[dict]:
        try:
            client = await self._get_client()
            collection = client.get_collection(name=collection_name)
            results = collection.query(
                query_embeddings=[query_embedding],
                n_results=top_k,
                where=filter_metadata,
            )

            documents = []
            if results["documents"] and results["documents"][0]:
                for i, doc in enumerate(results["documents"][0]):
                    distance = results["distances"][0][i] if results["distances"] else 1.0
                    similarity = 1 - distance
                    if similarity >= similarity_threshold:
                        documents.append(
                            {
                                "content": doc,
                                "metadata": (
                                    results["metadatas"][0][i] if results["metadatas"] else {}
                                ),
                                "id": results["ids"][0][i] if results["ids"] else "",
                                "similarity": similarity,
                            }
                        )

            logger.info(
                "Vector search completed", collection=collection_name, results=len(documents)
            )
            return documents

        except Exception as e:
            logger.error("Vector search failed", error=str(e))
            raise VectorStoreException(f"Vector search failed: {e!s}")

    async def delete_documents(self, collection_name: str, ids: list[str]) -> None:
        try:
            client = await self._get_client()
            collection = client.get_collection(name=collection_name)
            collection.delete(ids=ids)
            logger.info(
                "Documents deleted from vector store", collection=collection_name, count=len(ids)
            )
        except Exception as e:
            logger.error("Failed to delete documents from vector store", error=str(e))
            raise VectorStoreException(f"Failed to delete documents: {e!s}")

    async def delete_collection(self, collection_name: str) -> None:
        try:
            client = await self._get_client()
            client.delete_collection(name=collection_name)
            logger.info("Collection deleted", collection=collection_name)
        except Exception as e:
            logger.error("Failed to delete collection", error=str(e))
            raise VectorStoreException(f"Failed to delete collection: {e!s}")


class PGVectorStore(VectorStore):
    def __init__(self, connection_string: str):
        self.connection_string = connection_string
        self._pool = None

    async def _get_pool(self):
        if self._pool is None:
            import asyncpg

            self._pool = await asyncpg.create_pool(self.connection_string)
        return self._pool

    async def add_documents(
        self,
        collection_name: str,
        documents: list[str],
        embeddings: list[list[float]],
        metadatas: list[dict],
        ids: list[str],
    ) -> None:
        try:
            pool = await self._get_pool()
            async with pool.acquire() as conn:
                for doc, emb, meta, doc_id in zip(documents, embeddings, metadatas, ids):
                    await conn.execute(
                        f"""
                        INSERT INTO {collection_name} (id, content, embedding, metadata)
                        VALUES ($1, $2, $3, $4)
                        ON CONFLICT (id) DO UPDATE SET
                            content = EXCLUDED.content,
                            embedding = EXCLUDED.embedding,
                            metadata = EXCLUDED.metadata
                        """,
                        doc_id,
                        doc,
                        emb,
                        meta,
                    )
            logger.info(
                "Documents added to pgvector", collection=collection_name, count=len(documents)
            )
        except Exception as e:
            logger.error("Failed to add documents to pgvector", error=str(e))
            raise VectorStoreException(f"Failed to add documents: {e!s}")

    async def search(
        self,
        collection_name: str,
        query_embedding: list[float],
        top_k: int = 5,
        similarity_threshold: float = 0.7,
        filter_metadata: dict | None = None,
    ) -> list[dict]:
        try:
            pool = await self._get_pool()
            async with pool.acquire() as conn:
                filter_clause = ""
                params = [query_embedding, top_k, similarity_threshold]
                if filter_metadata:
                    filter_clause = "AND metadata @> $4"
                    params.append(filter_metadata)

                rows = await conn.fetch(
                    f"""
                    SELECT id, content, metadata, 1 - (embedding <=> $1) as similarity
                    FROM {collection_name}
                    WHERE 1 - (embedding <=> $1) >= $3
                    {filter_clause}
                    ORDER BY embedding <=> $1
                    LIMIT $2
                    """,
                    *params,
                )

            documents = [
                {
                    "content": row["content"],
                    "metadata": row["metadata"],
                    "id": row["id"],
                    "similarity": row["similarity"],
                }
                for row in rows
            ]

            logger.info(
                "pgvector search completed", collection=collection_name, results=len(documents)
            )
            return documents

        except Exception as e:
            logger.error("pgvector search failed", error=str(e))
            raise VectorStoreException(f"Vector search failed: {e!s}")

    async def delete_documents(self, collection_name: str, ids: list[str]) -> None:
        try:
            pool = await self._get_pool()
            async with pool.acquire() as conn:
                await conn.execute(
                    f"DELETE FROM {collection_name} WHERE id = ANY($1)",
                    ids,
                )
            logger.info(
                "Documents deleted from pgvector", collection=collection_name, count=len(ids)
            )
        except Exception as e:
            logger.error("Failed to delete documents from pgvector", error=str(e))
            raise VectorStoreException(f"Failed to delete documents: {e!s}")

    async def delete_collection(self, collection_name: str) -> None:
        try:
            pool = await self._get_pool()
            async with pool.acquire() as conn:
                await conn.execute(f"DROP TABLE IF EXISTS {collection_name}")
            logger.info("Collection deleted from pgvector", collection=collection_name)
        except Exception as e:
            logger.error("Failed to delete collection from pgvector", error=str(e))
            raise VectorStoreException(f"Failed to delete collection: {e!s}")
