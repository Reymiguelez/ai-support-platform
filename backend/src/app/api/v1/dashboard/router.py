from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, Query
from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.auth.dependencies import get_current_user
from app.core.database import get_db
from app.domain.models.conversation import Conversation, Message, MessageRole
from app.domain.models.document import Document
from app.domain.models.knowledge import KnowledgeBase
from app.domain.models.tool import AITool, ToolExecution
from app.domain.models.user import User, UserRole

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


@router.get("/stats")
async def get_user_dashboard_stats(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get dashboard stats for the current user (works for all roles)"""
    if current_user.role == UserRole.ADMIN or current_user.role == UserRole.SUPPORT_AGENT:
        # Admin/support agents see full platform stats
        total_users = await db.scalar(select(func.count(User.id)))
        total_customers = await db.scalar(
            select(func.count(User.id)).where(User.role == "customer")
        )
        total_agents = await db.scalar(
            select(func.count(User.id)).where(User.role == "support_agent")
        )
        total_admins = await db.scalar(select(func.count(User.id)).where(User.role == "admin"))

        total_conversations = await db.scalar(select(func.count(Conversation.id)))
        active_conversations = await db.scalar(
            select(func.count(Conversation.id)).where(Conversation.status == "active")
        )

        total_messages = await db.scalar(select(func.count(Message.id)))
        avg_messages_per_conv = (
            total_messages / total_conversations if total_conversations > 0 else 0
        )

        total_documents = await db.scalar(select(func.count(Document.id)))
        processed_documents = await db.scalar(
            select(func.count(Document.id)).where(Document.status == "completed")
        )

        total_kbs = await db.scalar(select(func.count(KnowledgeBase.id)))
        active_kbs = await db.scalar(
            select(func.count(KnowledgeBase.id)).where(KnowledgeBase.status == "active")
        )

        total_tools = await db.scalar(select(func.count(AITool.id)))
        active_tools = await db.scalar(
            select(func.count(AITool.id)).where(AITool.status == "active")
        )

        total_tool_executions = await db.scalar(select(func.count(ToolExecution.id)))
        successful_executions = await db.scalar(
            select(func.count(ToolExecution.id)).where(ToolExecution.status == "completed")
        )

        week_ago = datetime.now(UTC) - timedelta(days=7)
        new_users_week = await db.scalar(
            select(func.count(User.id)).where(User.created_at >= week_ago)
        )
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
                    round(processed_documents / total_documents * 100, 2)
                    if total_documents > 0
                    else 0
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
    # Customer users see only their own stats
    user_conversations = await db.scalar(
        select(func.count(Conversation.id)).where(Conversation.user_id == current_user.id)
    )
    active_conversations = await db.scalar(
        select(func.count(Conversation.id)).where(
            and_(Conversation.user_id == current_user.id, Conversation.status == "active")
        )
    )

    user_messages = await db.scalar(
        select(func.count(Message.id))
        .join(Conversation, Message.conversation_id == Conversation.id)
        .where(Conversation.user_id == current_user.id)
    )

    user_documents = await db.scalar(
        select(func.count(Document.id)).where(Document.user_id == current_user.id)
    )
    processed_user_documents = await db.scalar(
        select(func.count(Document.id)).where(
            and_(Document.user_id == current_user.id, Document.status == "completed")
        )
    )

    user_tool_executions = await db.scalar(
        select(func.count(ToolExecution.id)).where(ToolExecution.user_id == current_user.id)
    )
    successful_user_executions = await db.scalar(
        select(func.count(ToolExecution.id)).where(
            and_(ToolExecution.user_id == current_user.id, ToolExecution.status == "completed")
        )
    )

    return {
        "conversations": {
            "total": user_conversations,
            "active": active_conversations,
            "total_messages": user_messages,
            "avg_messages_per_conversation": (
                round(user_messages / user_conversations, 2) if user_conversations > 0 else 0
            ),
        },
        "documents": {
            "total": user_documents,
            "processed": processed_user_documents,
            "processing_rate": (
                round(processed_user_documents / user_documents * 100, 2)
                if user_documents > 0
                else 0
            ),
        },
        "tools": {
            "total_executions": user_tool_executions,
            "success_rate": (
                round(successful_user_executions / user_tool_executions * 100, 2)
                if user_tool_executions > 0
                else 0
            ),
        },
    }


@router.get("/activity")
async def get_user_activity_chart(
    days: int = Query(30, ge=1, le=90),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    start_date = datetime.now(UTC) - timedelta(days=days)

    if current_user.role in [UserRole.ADMIN, UserRole.SUPPORT_AGENT]:
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
    daily_conversations = await db.execute(
        select(
            func.date(Conversation.created_at).label("date"),
            func.count(Conversation.id).label("count"),
        )
        .where(and_(Conversation.user_id == current_user.id, Conversation.created_at >= start_date))
        .group_by(func.date(Conversation.created_at))
        .order_by(func.date(Conversation.created_at))
    )

    daily_messages = await db.execute(
        select(
            func.date(Message.created_at).label("date"),
            func.count(Message.id).label("count"),
        )
        .where(and_(Message.created_at >= start_date, Message.role == "user"))
        .group_by(func.date(Message.created_at))
        .order_by(func.date(Message.created_at))
    )

    return {
        "conversations": [
            {"date": str(row.date), "count": row.count} for row in daily_conversations
        ],
        "messages": [{"date": str(row.date), "count": row.count} for row in daily_messages],
    }


@router.get("/ai-usage")
async def get_user_ai_usage(
    days: int = Query(30, ge=1, le=90),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    start_date = datetime.now(UTC) - timedelta(days=days)

    if current_user.role in [UserRole.ADMIN, UserRole.SUPPORT_AGENT]:
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
    user_model_usage = await db.execute(
        select(
            Message.model,
            func.count(Message.id).label("count"),
            func.sum(Message.tokens).label("total_tokens"),
            func.avg(Message.execution_time_ms).label("avg_time_ms"),
        )
        .join(Conversation, Message.conversation_id == Conversation.id)
        .where(
            and_(
                Conversation.user_id == current_user.id,
                Message.created_at >= start_date,
                Message.role == "assistant",
                Message.model.isnot(None),
            )
        )
        .group_by(Message.model)
        .order_by(func.count(Message.id).desc())
    )

    user_tool_usage = await db.execute(
        select(
            AITool.name,
            AITool.category,
            func.count(ToolExecution.id).label("executions"),
            func.avg(ToolExecution.execution_time_ms).label("avg_time_ms"),
        )
        .join(ToolExecution, AITool.id == ToolExecution.tool_id)
        .where(
            and_(
                ToolExecution.user_id == current_user.id,
                ToolExecution.created_at >= start_date,
            )
        )
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
            for row in user_model_usage
        ],
        "tools": [
            {
                "name": row.name,
                "category": row.category,
                "executions": row.executions,
                "avg_execution_time_ms": round(row.avg_time_ms or 0, 2),
            }
            for row in user_tool_usage
        ],
    }
