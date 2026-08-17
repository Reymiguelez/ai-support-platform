from uuid import UUID

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.exceptions import AuthenticationException, AuthorizationException
from app.core.security import decode_token
from app.domain.models.user import User, UserRole

security = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db),
) -> User:
    if not credentials:
        raise AuthenticationException("Not authenticated")

    payload = decode_token(credentials.credentials)
    if not payload or payload.get("type") != "access":
        raise AuthenticationException("Invalid or expired token")

    user_id_str = payload.get("sub")
    if not user_id_str:
        raise AuthenticationException("Invalid token payload")

    try:
        user_id = UUID(user_id_str) if isinstance(user_id_str, str) else user_id_str
    except ValueError:
        raise AuthenticationException("Invalid user ID in token")

    user = await db.get(User, user_id)
    if not user:
        raise AuthenticationException("User not found")

    if not user.is_active:
        raise AuthorizationException("Account is deactivated")

    return user


def require_role(*allowed_roles: UserRole):
    async def role_checker(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in allowed_roles:
            raise AuthorizationException("Insufficient permissions")
        return current_user

    return role_checker


async def get_current_user_optional(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db),
) -> User | None:
    if not credentials:
        return None

    payload = decode_token(credentials.credentials)
    if not payload or payload.get("type") != "access":
        return None

    user_id_str = payload.get("sub")
    if not user_id_str:
        return None

    try:
        user_id = UUID(user_id_str) if isinstance(user_id_str, str) else user_id_str
    except ValueError:
        return None

    user = await db.get(User, user_id)
    if not user or not user.is_active:
        return None

    return user
