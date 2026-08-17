from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class DocumentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID
    filename: str
    original_filename: str
    file_path: str
    file_size: int
    mime_type: str
    document_type: str
    status: str
    page_count: int | None = None
    chunk_count: int
    error_message: str | None = None
    metadata: dict
    created_at: datetime
    updated_at: datetime
    processed_at: datetime | None = None


class DocumentUploadResponse(BaseModel):
    document_id: UUID
    filename: str
    status: str
    message: str


class DocumentProcessRequest(BaseModel):
    pass
