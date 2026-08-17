from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class KnowledgeBaseCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: str | None = None
    embedding_model: str = Field(default="text-embedding-3-large")
    chunk_size: int = Field(default=1000, ge=100, le=5000)
    chunk_overlap: int = Field(default=200, ge=0, le=1000)
    top_k: int = Field(default=5, ge=1, le=20)
    similarity_threshold: float = Field(default=0.7, ge=0.0, le=1.0)


class KnowledgeBaseUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=255)
    description: str | None = None
    embedding_model: str | None = None
    chunk_size: int | None = Field(None, ge=100, le=5000)
    chunk_overlap: int | None = Field(None, ge=0, le=1000)
    top_k: int | None = Field(None, ge=1, le=20)
    similarity_threshold: float | None = Field(None, ge=0.0, le=1.0)
    status: str | None = None


class KnowledgeBaseResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    description: str | None = None
    status: str
    embedding_model: str
    chunk_size: int
    chunk_overlap: int
    top_k: int
    similarity_threshold: float
    metadata: dict
    created_at: datetime
    updated_at: datetime


class KnowledgeBaseDocumentAdd(BaseModel):
    document_id: UUID
