from collections.abc import Sequence
from uuid import UUID

from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.models.conversation import Conversation, ConversationStatus, Message, MessageRole
from app.infrastructure.repositories.base import BaseRepository


class ConversationRepository(BaseRepository[Conversation]):
    def __init__(self, session: AsyncSession):
        super().__init__(Conversation, session)

    async def get_by_user(
        self,
        user_id: UUID,
        skip: int = 0,
        limit: int = 20,
        status: ConversationStatus | None = None,
    ) -> Sequence[Conversation]:
        query = select(Conversation).where(Conversation.user_id == user_id)
        if status:
            query = query.where(Conversation.status == status)
        query = query.order_by(desc(Conversation.updated_at)).offset(skip).limit(limit)
        result = await self.session.execute(query)
        return result.scalars().all()

    async def count_by_user(self, user_id: UUID, status: ConversationStatus | None = None) -> int:
        query = select(func.count(Conversation.id)).where(Conversation.user_id == user_id)
        if status:
            query = query.where(Conversation.status == status)
        result = await self.session.execute(query)
        return result.scalar_one()

    async def get_with_messages(self, conversation_id: UUID) -> Conversation | None:
        result = await self.session.execute(
            select(Conversation).where(Conversation.id == conversation_id)
        )
        return result.scalar_one_or_none()


class MessageRepository(BaseRepository[Message]):
    def __init__(self, session: AsyncSession):
        super().__init__(Message, session)

    async def get_by_conversation(
        self,
        conversation_id: UUID,
        skip: int = 0,
        limit: int = 100,
    ) -> Sequence[Message]:
        result = await self.session.execute(
            select(Message)
            .where(Message.conversation_id == conversation_id)
            .order_by(Message.created_at)
            .offset(skip)
            .limit(limit)
        )
        return result.scalars().all()

    async def get_recent_by_conversation(
        self,
        conversation_id: UUID,
        limit: int = 10,
    ) -> Sequence[Message]:
        result = await self.session.execute(
            select(Message)
            .where(Message.conversation_id == conversation_id)
            .order_by(desc(Message.created_at))
            .limit(limit)
        )
        return list(reversed(result.scalars().all()))

    async def count_by_conversation(self, conversation_id: UUID) -> int:
        result = await self.session.execute(
            select(func.count(Message.id)).where(Message.conversation_id == conversation_id)
        )
        return result.scalar_one()

    async def create_user_message(
        self,
        conversation_id: UUID,
        content: str,
    ) -> Message:
        message = Message(
            conversation_id=conversation_id,
            role=MessageRole.USER,
            content=content,
        )
        self.session.add(message)
        await self.session.flush()
        await self.session.refresh(message)
        return message

    async def create_assistant_message(
        self,
        conversation_id: UUID,
        content: str,
        tokens: int = 0,
        model: str | None = None,
        execution_time_ms: int | None = None,
        tool_calls: list | None = None,
        tool_results: list | None = None,
    ) -> Message:
        message = Message(
            conversation_id=conversation_id,
            role=MessageRole.ASSISTANT,
            content=content,
            tokens=tokens,
            model=model,
            execution_time_ms=execution_time_ms,
            tool_calls=tool_calls or [],
            tool_results=tool_results or [],
        )
        self.session.add(message)
        await self.session.flush()
        await self.session.refresh(message)
        return message
