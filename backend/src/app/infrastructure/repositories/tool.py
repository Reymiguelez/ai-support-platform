from collections.abc import Sequence
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.models.tool import AITool, ToolCategory, ToolExecution, ToolStatus
from app.infrastructure.repositories.base import BaseRepository


class ToolRepository(BaseRepository[AITool]):
    def __init__(self, session: AsyncSession):
        super().__init__(AITool, session)

    async def get_active(self, category: ToolCategory | None = None) -> Sequence[AITool]:
        query = select(AITool).where(AITool.status == ToolStatus.ACTIVE)
        if category:
            query = query.where(AITool.category == category)
        result = await self.session.execute(query)
        return result.scalars().all()

    async def get_by_name(self, name: str) -> AITool | None:
        result = await self.session.execute(select(AITool).where(AITool.name == name))
        return result.scalar_one_or_none()


class ToolExecutionRepository(BaseRepository[ToolExecution]):
    def __init__(self, session: AsyncSession):
        super().__init__(ToolExecution, session)

    async def create_execution(
        self,
        tool_id: UUID,
        user_id: UUID,
        arguments: dict,
        conversation_id: UUID | None = None,
        message_id: UUID | None = None,
    ) -> ToolExecution:
        execution = ToolExecution(
            tool_id=tool_id,
            user_id=user_id,
            arguments=arguments,
            conversation_id=conversation_id,
            message_id=message_id,
            status="pending",
        )
        self.session.add(execution)
        await self.session.flush()
        await self.session.refresh(execution)
        return execution

    async def complete_execution(
        self,
        execution_id: UUID,
        result: dict | None = None,
        error: str | None = None,
        execution_time_ms: int = 0,
    ) -> ToolExecution | None:
        from datetime import UTC, datetime

        execution = await self.get(execution_id)
        if execution:
            execution.result = result
            execution.error = error
            execution.execution_time_ms = execution_time_ms
            execution.status = "completed" if not error else "failed"
            execution.completed_at = datetime.now(UTC)
            await self.session.flush()
            await self.session.refresh(execution)
        return execution

    async def get_by_conversation(self, conversation_id: UUID) -> Sequence[ToolExecution]:
        result = await self.session.execute(
            select(ToolExecution)
            .where(ToolExecution.conversation_id == conversation_id)
            .order_by(ToolExecution.created_at)
        )
        return result.scalars().all()

    async def get_by_user(
        self, user_id: UUID, skip: int = 0, limit: int = 50
    ) -> Sequence[ToolExecution]:
        result = await self.session.execute(
            select(ToolExecution)
            .where(ToolExecution.user_id == user_id)
            .order_by(ToolExecution.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        return result.scalars().all()
