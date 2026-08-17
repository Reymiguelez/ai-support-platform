from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.auth.dependencies import get_current_user, require_role
from app.core.database import get_db
from app.core.security import get_password_hash, verify_password
from app.domain.models.user import User, UserRole
from app.infrastructure.repositories.user import UserRepository
from app.schemas.auth import PasswordChangeRequest, UserResponse, UserUpdate

router = APIRouter()


async def get_user_repo(db: AsyncSession = Depends(get_db)) -> UserRepository:
    return UserRepository(db)


@router.get("/me", response_model=UserResponse)
async def get_current_user_profile(current_user: User = Depends(get_current_user)):
    return current_user


@router.patch("/me", response_model=UserResponse)
async def update_current_user(
    data: UserUpdate,
    current_user: User = Depends(get_current_user),
    user_repo: UserRepository = Depends(get_user_repo),
):
    updated = await user_repo.update(current_user, **data.model_dump(exclude_unset=True))
    return updated


@router.post("/me/change-password")
async def change_password(
    data: PasswordChangeRequest,
    current_user: User = Depends(get_current_user),
    user_repo: UserRepository = Depends(get_user_repo),
):
    if not verify_password(data.current_password, current_user.hashed_password):
        raise HTTPException(status_code=400, detail="Current password is incorrect")

    current_user.hashed_password = get_password_hash(data.new_password)
    await user_repo.session.flush()
    return {"message": "Password changed successfully"}


@router.get("", response_model=list[UserResponse])
async def list_users(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    role: str | None = Query(None),
    current_user: User = Depends(require_role(UserRole.ADMIN, UserRole.SUPPORT_AGENT)),
    user_repo: UserRepository = Depends(get_user_repo),
):
    if role:
        from app.domain.models.user import UserRole

        user_role = UserRole(role)
        users = await user_repo.get_by_role(user_role, skip, limit)
        total = await user_repo.count_by_role(user_role)
    else:
        users = await user_repo.get_all(skip, limit)
        total = len(users)
    return users


@router.get("/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: UUID,
    current_user: User = Depends(require_role(UserRole.ADMIN, UserRole.SUPPORT_AGENT)),
    user_repo: UserRepository = Depends(get_user_repo),
):
    user = await user_repo.get(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


@router.patch("/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: UUID,
    data: UserUpdate,
    current_user: User = Depends(require_role(UserRole.ADMIN)),
    user_repo: UserRepository = Depends(get_user_repo),
):
    user = await user_repo.get(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    updated = await user_repo.update(user, **data.model_dump(exclude_unset=True))
    return updated


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(
    user_id: UUID,
    current_user: User = Depends(require_role(UserRole.ADMIN)),
    user_repo: UserRepository = Depends(get_user_repo),
):
    user = await user_repo.get(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if user.id == current_user.id:
        raise HTTPException(status_code=400, detail="Cannot delete yourself")

    await user_repo.delete(user)
