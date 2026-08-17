from collections.abc import Sequence
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.models.user import User, UserRole
from app.infrastructure.repositories.base import BaseRepository


class UserRepository(BaseRepository[User]):
    def __init__(self, session: AsyncSession):
        super().__init__(User, session)

    async def get_by_email(self, email: str) -> User | None:
        result = await self.session.execute(select(User).where(User.email == email))
        return result.scalar_one_or_none()

    async def get_by_username(self, username: str) -> User | None:
        result = await self.session.execute(select(User).where(User.username == username))
        return result.scalar_one_or_none()

    async def get_by_role(self, role: UserRole, skip: int = 0, limit: int = 100) -> Sequence[User]:
        result = await self.session.execute(
            select(User).where(User.role == role).offset(skip).limit(limit)
        )
        return result.scalars().all()

    async def count_by_role(self, role: UserRole) -> int:
        result = await self.session.execute(select(func.count(User.id)).where(User.role == role))
        return result.scalar_one()

    async def update_last_login(self, user_id: UUID) -> None:
        from datetime import UTC, datetime

        user = await self.get(user_id)
        if user:
            user.last_login = datetime.now(UTC)
            await self.session.flush()
