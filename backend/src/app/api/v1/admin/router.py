from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, Query
from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.auth.dependencies import require_role
from app.core.database import get_db
from app.domain.models.conversation import Conversation, ConversationStatus, Message, MessageRole
from app.domain.models.document import Document, DocumentStatus
from app.domain.models.knowledge import KnowledgeBase, KnowledgeBaseStatus
from app.domain.models.tool import AITool, ToolExecution
from app.domain.models.user import User, UserRole

router = APIRouter()


@router.get("/dashboard/stats")
async def get_dashboard_stats(
    current_user: User = Depends(require_role(UserRole.ADMIN, UserRole.SUPPORT_AGENT)),
    db: AsyncSession = Depends(get_db),
):
    total_users = await db.scalar(select(func.count(User.id)))
    total_customers = await db.scalar(
        select(func.count(User.id)).where(User.role == UserRole.CUSTOMER)
    )
    total_agents = await db.scalar(
        select(func.count(User.id)).where(User.role == UserRole.SUPPORT_AGENT)
    )
    total_admins = await db.scalar(select(func.count(User.id)).where(User.role == UserRole.ADMIN))

    total_conversations = await db.scalar(select(func.count(Conversation.id)))
    active_conversations = await db.scalar(
        select(func.count(Conversation.id)).where(Conversation.status == ConversationStatus.ACTIVE)
    )

    total_messages = await db.scalar(select(func.count(Message.id)))
    avg_messages_per_conv = total_messages / total_conversations if total_conversations > 0 else 0

    total_documents = await db.scalar(select(func.count(Document.id)))
    processed_documents = await db.scalar(
        select(func.count(Document.id)).where(Document.status == DocumentStatus.COMPLETED)
    )

    total_kbs = await db.scalar(select(func.count(KnowledgeBase.id)))
    active_kbs = await db.scalar(
        select(func.count(KnowledgeBase.id)).where(
            KnowledgeBase.status == KnowledgeBaseStatus.ACTIVE
        )
    )

    total_tools = await db.scalar(select(func.count(AITool.id)))
    active_tools = await db.scalar(select(func.count(AITool.id)).where(AITool.status == "active"))

    total_tool_executions = await db.scalar(select(func.count(ToolExecution.id)))
    successful_executions = await db.scalar(
        select(func.count(ToolExecution.id)).where(ToolExecution.status == "completed")
    )

    week_ago = datetime.now(UTC) - timedelta(days=7)
    new_users_week = await db.scalar(select(func.count(User.id)).where(User.created_at >= week_ago))
    new_conversations_week = await db.scalar(
        select(func.count(Conversation.id)).where(Conversation.created_at >= week_ago)
    )

    return {
        "users": {
            "total": total_users,
            "customers": total_customers,
            "agents": total_agents,
            "admins": total_admins,
            "new_this_week": new_users_week,
        },
        "conversations": {
            "total": total_conversations,
            "active": active_conversations,
            "total_messages": total_messages,
            "avg_messages_per_conversation": round(avg_messages_per_conv, 2),
            "new_this_week": new_conversations_week,
        },
        "documents": {
            "total": total_documents,
            "processed": processed_documents,
            "processing_rate": (
                round(processed_documents / total_documents * 100, 2) if total_documents > 0 else 0
            ),
        },
        "knowledge_bases": {
            "total": total_kbs,
            "active": active_kbs,
        },
        "tools": {
            "total": total_tools,
            "active": active_tools,
            "total_executions": total_tool_executions,
            "success_rate": (
                round(successful_executions / total_tool_executions * 100, 2)
                if total_tool_executions > 0
                else 0
            ),
        },
    }


@router.get("/dashboard/activity")
async def get_activity_chart(
    days: int = Query(30, ge=1, le=90),
    current_user: User = Depends(require_role(UserRole.ADMIN, UserRole.SUPPORT_AGENT)),
    db: AsyncSession = Depends(get_db),
):
    start_date = datetime.now(UTC) - timedelta(days=days)

    daily_users = await db.execute(
        select(
            func.date(User.created_at).label("date"),
            func.count(User.id).label("count"),
        )
        .where(User.created_at >= start_date)
        .group_by(func.date(User.created_at))
        .order_by(func.date(User.created_at))
    )

    daily_conversations = await db.execute(
        select(
            func.date(Conversation.created_at).label("date"),
            func.count(Conversation.id).label("count"),
        )
        .where(Conversation.created_at >= start_date)
        .group_by(func.date(Conversation.created_at))
        .order_by(func.date(Conversation.created_at))
    )

    daily_messages = await db.execute(
        select(
            func.date(Message.created_at).label("date"),
            func.count(Message.id).label("count"),
        )
        .where(Message.created_at >= start_date)
        .group_by(func.date(Message.created_at))
        .order_by(func.date(Message.created_at))
    )

    return {
        "users": [{"date": str(row.date), "count": row.count} for row in daily_users],
        "conversations": [
            {"date": str(row.date), "count": row.count} for row in daily_conversations
        ],
        "messages": [{"date": str(row.date), "count": row.count} for row in daily_messages],
    }


@router.get("/dashboard/ai-usage")
async def get_ai_usage(
    days: int = Query(30, ge=1, le=90),
    current_user: User = Depends(require_role(UserRole.ADMIN, UserRole.SUPPORT_AGENT)),
    db: AsyncSession = Depends(get_db),
):
    start_date = datetime.now(UTC) - timedelta(days=days)

    model_usage = await db.execute(
        select(
            Message.model,
            func.count(Message.id).label("count"),
            func.sum(Message.tokens).label("total_tokens"),
            func.avg(Message.execution_time_ms).label("avg_time_ms"),
        )
        .where(
            and_(
                Message.created_at >= start_date,
                Message.role == MessageRole.ASSISTANT,
                Message.model.isnot(None),
            )
        )
        .group_by(Message.model)
        .order_by(func.count(Message.id).desc())
    )

    tool_usage = await db.execute(
        select(
            AITool.name,
            AITool.category,
            func.count(ToolExecution.id).label("executions"),
            func.avg(ToolExecution.execution_time_ms).label("avg_time_ms"),
        )
        .join(ToolExecution, AITool.id == ToolExecution.tool_id)
        .where(ToolExecution.created_at >= start_date)
        .group_by(AITool.id, AITool.name, AITool.category)
        .order_by(func.count(ToolExecution.id).desc())
    )

    return {
        "models": [
            {
                "model": row.model,
                "requests": row.count,
                "total_tokens": row.total_tokens or 0,
                "avg_response_time_ms": round(row.avg_time_ms or 0, 2),
            }
            for row in model_usage
        ],
        "tools": [
            {
                "name": row.name,
                "category": row.category,
                "executions": row.executions,
                "avg_execution_time_ms": round(row.avg_time_ms or 0, 2),
            }
            for row in tool_usage
        ],
    }


@router.get("/system/config")
async def get_system_config(
    current_user: User = Depends(require_role(UserRole.ADMIN)),
):
    from app.core.config import settings

    return {
        "environment": settings.ENVIRONMENT,
        "version": settings.VERSION,
        "api_prefix": settings.API_V1_PREFIX,
        "openai_model": settings.OPENAI_MODEL,
        "embedding_model": settings.OPENAI_EMBEDDING_MODEL,
        "rate_limit": f"{settings.RATE_LIMIT_REQUESTS}/{settings.RATE_LIMIT_WINDOW}s",
        "vector_search": {
            "top_k": settings.VECTOR_SEARCH_TOP_K,
            "similarity_threshold": settings.VECTOR_SEARCH_SIMILARITY_THRESHOLD,
        },
        "conversation_memory_window": settings.CONVERSATION_MEMORY_WINDOW,
        "allowed_file_types": settings.ALLOWED_FILE_TYPES,
        "max_file_size_mb": settings.MAX_FILE_SIZE / (1024 * 1024),
    }


@router.get("/logs")
async def get_system_logs(
    level: str | None = Query(None),
    limit: int = Query(100, ge=1, le=1000),
    current_user: User = Depends(require_role(UserRole.ADMIN)),
):
    return {
        "message": "Log retrieval not implemented. Use external logging service (e.g., Datadog, Elasticsearch, Loki).",
        "suggestion": "Configure structured logging to send to your observability platform.",
    }
