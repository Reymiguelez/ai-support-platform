from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class ConversationCreate(BaseModel):
    title: str = Field(default="New Conversation", min_length=1, max_length=255)
    system_prompt: str | None = None
    model: str = Field(default="gpt-4-turbo-preview")
    temperature: float = Field(default=0.7, ge=0.0, le=2.0)


class ConversationUpdate(BaseModel):
    title: str | None = Field(None, min_length=1, max_length=255)
    system_prompt: str | None = None
    model: str | None = None
    temperature: float | None = Field(None, ge=0.0, le=2.0)
    status: str | None = None


class ConversationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID
    title: str
    status: str
    model: str
    temperature: float
    system_prompt: str | None = None
    extra_metadata: dict
    created_at: datetime
    updated_at: datetime


class MessageResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    conversation_id: UUID
    role: str
    content: str
    tokens: int
    model: str | None = None
    execution_time_ms: int | None = None
    tool_calls: list
    tool_results: list
    extra_metadata: dict
    created_at: datetime


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1)
    conversation_id: UUID | None = None
    use_rag: bool = True
    knowledge_base_id: UUID | None = None
    use_tools: bool = True


class ChatResponse(BaseModel):
    conversation_id: UUID
    message: str
    message_id: UUID | None = None
