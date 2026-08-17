from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.auth.dependencies import get_current_user
from app.core.database import get_db
from app.domain.models.user import User
from app.infrastructure.repositories.conversation import ConversationRepository, MessageRepository
from app.infrastructure.repositories.document import DocumentChunkRepository, DocumentRepository
from app.infrastructure.repositories.knowledge import KnowledgeBaseRepository
from app.infrastructure.repositories.tool import ToolExecutionRepository, ToolRepository
from app.schemas.chat import (
    ChatRequest,
    ChatResponse,
    ConversationCreate,
    ConversationResponse,
    ConversationUpdate,
    MessageResponse,
)
from app.schemas.document import (
    DocumentResponse,
    DocumentUploadResponse,
)
from app.schemas.knowledge import (
    KnowledgeBaseCreate,
    KnowledgeBaseDocumentAdd,
    KnowledgeBaseResponse,
    KnowledgeBaseUpdate,
)
from app.services.chat import ChatService
from app.services.document import DocumentService
from app.services.knowledge import KnowledgeService

router = APIRouter()


async def get_conversation_repo(db: AsyncSession = Depends(get_db)) -> ConversationRepository:
    return ConversationRepository(db)


async def get_message_repo(db: AsyncSession = Depends(get_db)) -> MessageRepository:
    return MessageRepository(db)


async def get_document_repo(db: AsyncSession = Depends(get_db)) -> DocumentRepository:
    return DocumentRepository(db)


async def get_chunk_repo(db: AsyncSession = Depends(get_db)) -> DocumentChunkRepository:
    return DocumentChunkRepository(db)


async def get_knowledge_repo(db: AsyncSession = Depends(get_db)) -> KnowledgeBaseRepository:
    return KnowledgeBaseRepository(db)


async def get_tool_repo(db: AsyncSession = Depends(get_db)) -> ToolRepository:
    return ToolRepository(db)


async def get_execution_repo(db: AsyncSession = Depends(get_db)) -> ToolExecutionRepository:
    return ToolExecutionRepository(db)


async def get_chat_service(
    conversation_repo: ConversationRepository = Depends(get_conversation_repo),
    message_repo: MessageRepository = Depends(get_message_repo),
) -> ChatService:
    return ChatService(conversation_repo, message_repo)


async def get_document_service(
    document_repo: DocumentRepository = Depends(get_document_repo),
    chunk_repo: DocumentChunkRepository = Depends(get_chunk_repo),
) -> DocumentService:
    return DocumentService(document_repo, chunk_repo)


async def get_knowledge_service(
    kb_repo: KnowledgeBaseRepository = Depends(get_knowledge_repo),
    document_repo: DocumentRepository = Depends(get_document_repo),
) -> KnowledgeService:
    return KnowledgeService(kb_repo, document_repo)


@router.post("/conversations", response_model=ConversationResponse, status_code=201)
async def create_conversation(
    data: ConversationCreate,
    current_user: User = Depends(get_current_user),
    chat_service: ChatService = Depends(get_chat_service),
):
    conversation = await chat_service.create_conversation(
        user_id=current_user.id,
        title=data.title,
        system_prompt=data.system_prompt,
        model=data.model,
        temperature=data.temperature,
    )
    return conversation


@router.get("/conversations", response_model=list[ConversationResponse])
async def list_conversations(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    status: str | None = Query(None),
    current_user: User = Depends(get_current_user),
    chat_service: ChatService = Depends(get_chat_service),
):
    from app.domain.models.conversation import ConversationStatus

    conv_status = ConversationStatus(status) if status else None
    conversations, total = await chat_service.list_conversations(
        current_user.id, skip, limit, conv_status
    )
    return conversations


@router.get("/conversations/{conversation_id}", response_model=ConversationResponse)
async def get_conversation(
    conversation_id: UUID,
    current_user: User = Depends(get_current_user),
    chat_service: ChatService = Depends(get_chat_service),
):
    conversation = await chat_service.get_conversation(conversation_id, current_user.id)
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return conversation


@router.patch("/conversations/{conversation_id}", response_model=ConversationResponse)
async def update_conversation(
    conversation_id: UUID,
    data: ConversationUpdate,
    current_user: User = Depends(get_current_user),
    chat_service: ChatService = Depends(get_chat_service),
):
    conversation = await chat_service.update_conversation(
        conversation_id, current_user.id, **data.model_dump(exclude_unset=True)
    )
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return conversation


@router.delete("/conversations/{conversation_id}", status_code=204)
async def delete_conversation(
    conversation_id: UUID,
    current_user: User = Depends(get_current_user),
    chat_service: ChatService = Depends(get_chat_service),
):
    deleted = await chat_service.delete_conversation(conversation_id, current_user.id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Conversation not found")


@router.get("/conversations/{conversation_id}/messages", response_model=list[MessageResponse])
async def get_messages(
    conversation_id: UUID,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    current_user: User = Depends(get_current_user),
    chat_service: ChatService = Depends(get_chat_service),
):
    messages = await chat_service.get_messages(conversation_id, current_user.id, skip, limit)
    return messages


@router.post("/chat", response_model=ChatResponse)
async def chat(
    data: ChatRequest,
    current_user: User = Depends(get_current_user),
    chat_service: ChatService = Depends(get_chat_service),
):
    if not data.conversation_id:
        conversation = await chat_service.create_conversation(
            current_user.id, title=data.message[:50]
        )
        conversation_id = conversation.id
    else:
        conversation_id = data.conversation_id

    message = await chat_service.chat(
        conversation_id=conversation_id,
        user_id=current_user.id,
        user_message=data.message,
        use_rag=data.use_rag,
        knowledge_base_id=data.knowledge_base_id,
        use_tools=data.use_tools,
    )

    return ChatResponse(
        conversation_id=conversation_id,
        message=message.content if message else "",
        message_id=message.id if message else None,
    )


@router.post("/chat/stream")
async def chat_stream(
    data: ChatRequest,
    current_user: User = Depends(get_current_user),
    chat_service: ChatService = Depends(get_chat_service),
):
    if not data.conversation_id:
        conversation = await chat_service.create_conversation(
            current_user.id, title=data.message[:50]
        )
        conversation_id = conversation.id
    else:
        conversation_id = data.conversation_id

    async def event_generator():
        async for chunk in chat_service.stream_chat(
            conversation_id=conversation_id,
            user_id=current_user.id,
            user_message=data.message,
            use_rag=data.use_rag,
            knowledge_base_id=data.knowledge_base_id,
            use_tools=data.use_tools,
        ):
            yield f"data: {chunk}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@router.post("/documents/upload", response_model=DocumentUploadResponse)
async def upload_document(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    document_service: DocumentService = Depends(get_document_service),
):
    content = await file.read()
    document = await document_service.upload_document(
        current_user.id, content, file.filename, file.content_type
    )
    return DocumentUploadResponse(
        document_id=document.id,
        filename=document.filename,
        status=document.status,
        message="Document uploaded successfully. Processing will start shortly.",
    )


@router.post("/documents/{document_id}/process", response_model=DocumentResponse)
async def process_document(
    document_id: UUID,
    current_user: User = Depends(get_current_user),
    document_service: DocumentService = Depends(get_document_service),
):
    document = await document_service.process_document(document_id)
    return document


@router.get("/documents", response_model=list[DocumentResponse])
async def list_documents(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    status: str | None = Query(None),
    current_user: User = Depends(get_current_user),
    document_service: DocumentService = Depends(get_document_service),
):
    from app.domain.models.document import DocumentStatus

    doc_status = DocumentStatus(status) if status else None
    documents, total = await document_service.list_documents(
        current_user.id, skip, limit, doc_status
    )
    return documents


@router.get("/documents/{document_id}", response_model=DocumentResponse)
async def get_document(
    document_id: UUID,
    current_user: User = Depends(get_current_user),
    document_service: DocumentService = Depends(get_document_service),
):
    document = await document_service.get_document(document_id, current_user.id)
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    return document


@router.delete("/documents/{document_id}", status_code=204)
async def delete_document(
    document_id: UUID,
    current_user: User = Depends(get_current_user),
    document_service: DocumentService = Depends(get_document_service),
):
    deleted = await document_service.delete_document(document_id, current_user.id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Document not found")


@router.post("/knowledge-bases", response_model=KnowledgeBaseResponse, status_code=201)
async def create_knowledge_base(
    data: KnowledgeBaseCreate,
    current_user: User = Depends(get_current_user),
    knowledge_service: KnowledgeService = Depends(get_knowledge_service),
):
    kb = await knowledge_service.create_knowledge_base(
        name=data.name,
        description=data.description,
        embedding_model=data.embedding_model,
        chunk_size=data.chunk_size,
        chunk_overlap=data.chunk_overlap,
        top_k=data.top_k,
        similarity_threshold=data.similarity_threshold,
    )
    return kb


@router.get("/knowledge-bases", response_model=list[KnowledgeBaseResponse])
async def list_knowledge_bases(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    status: str | None = Query(None),
    current_user: User = Depends(get_current_user),
    knowledge_service: KnowledgeService = Depends(get_knowledge_service),
):
    from app.domain.models.knowledge import KnowledgeBaseStatus

    kb_status = KnowledgeBaseStatus(status) if status else None
    kbs, total = await knowledge_service.list_knowledge_bases(skip, limit, kb_status)
    return kbs


@router.get("/knowledge-bases/{kb_id}", response_model=KnowledgeBaseResponse)
async def get_knowledge_base(
    kb_id: UUID,
    current_user: User = Depends(get_current_user),
    knowledge_service: KnowledgeService = Depends(get_knowledge_service),
):
    kb = await knowledge_service.get_knowledge_base(kb_id)
    if not kb:
        raise HTTPException(status_code=404, detail="Knowledge base not found")
    return kb


@router.patch("/knowledge-bases/{kb_id}", response_model=KnowledgeBaseResponse)
async def update_knowledge_base(
    kb_id: UUID,
    data: KnowledgeBaseUpdate,
    current_user: User = Depends(get_current_user),
    knowledge_service: KnowledgeService = Depends(get_knowledge_service),
):
    kb = await knowledge_service.update_knowledge_base(kb_id, **data.model_dump(exclude_unset=True))
    if not kb:
        raise HTTPException(status_code=404, detail="Knowledge base not found")
    return kb


@router.delete("/knowledge-bases/{kb_id}", status_code=204)
async def delete_knowledge_base(
    kb_id: UUID,
    current_user: User = Depends(get_current_user),
    knowledge_service: KnowledgeService = Depends(get_knowledge_service),
):
    deleted = await knowledge_service.delete_knowledge_base(kb_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Knowledge base not found")


@router.post("/knowledge-bases/{kb_id}/documents", status_code=201)
async def add_document_to_kb(
    kb_id: UUID,
    data: KnowledgeBaseDocumentAdd,
    current_user: User = Depends(get_current_user),
    knowledge_service: KnowledgeService = Depends(get_knowledge_service),
):
    kb_doc = await knowledge_service.add_document_to_kb(kb_id, data.document_id)
    return {"message": "Document added to knowledge base", "kb_document_id": str(kb_doc.id)}


@router.delete("/knowledge-bases/{kb_id}/documents/{document_id}", status_code=204)
async def remove_document_from_kb(
    kb_id: UUID,
    document_id: UUID,
    current_user: User = Depends(get_current_user),
    knowledge_service: KnowledgeService = Depends(get_knowledge_service),
):
    removed = await knowledge_service.remove_document_from_kb(kb_id, document_id)
    if not removed:
        raise HTTPException(status_code=404, detail="Document not found in knowledge base")


@router.get("/knowledge-bases/{kb_id}/documents")
async def get_kb_documents(
    kb_id: UUID,
    current_user: User = Depends(get_current_user),
    knowledge_service: KnowledgeService = Depends(get_knowledge_service),
):
    docs = await knowledge_service.get_kb_documents(kb_id)
    return docs
