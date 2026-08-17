from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Request, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.core.exceptions import (
    AuthenticationException,
    AuthorizationException,
    ConflictException,
)
from app.core.security import (
    create_access_token,
    create_email_verification_token,
    create_password_reset_token,
    create_refresh_token,
    decode_token,
    get_password_hash,
    verify_password,
)
from app.domain.models.user import User
from app.schemas.auth import (
    EmailVerificationRequest,
    PasswordResetConfirm,
    PasswordResetRequest,
    RegisterRequest,
    TokenRefreshRequest,
    TokenResponse,
    UserResponse,
)
from app.services.email import send_email_verification, send_password_reset_email
from app.utils.rate_limiter import limiter

router = APIRouter()


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit("5/minute")
async def register(
    request: Request,
    data: RegisterRequest,
    db: AsyncSession = Depends(get_db),
):
    existing_user = await db.execute(select(User).where(User.email == data.email))
    if existing_user.scalar_one_or_none():
        raise ConflictException("Email already registered", details={"email": data.email})

    existing_username = await db.execute(select(User).where(User.username == data.username))
    if existing_username.scalar_one_or_none():
        raise ConflictException("Username already taken", details={"username": data.username})

    hashed_password = get_password_hash(data.password)
    user = User(
        email=data.email,
        username=data.username,
        full_name=data.full_name,
        hashed_password=hashed_password,
        role="customer",
        is_active=True,
        is_verified=False,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)

    verification_token = create_email_verification_token(user.email)
    await send_email_verification(user.email, verification_token)

    access_token = create_access_token(
        subject=user.id,
        additional_claims={"role": user.role.value if hasattr(user.role, "value") else str(user.role)},
    )
    refresh_token = create_refresh_token(subject=user.id)

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        user=UserResponse.model_validate(user),
    )


@router.post("/login", response_model=TokenResponse)
@limiter.limit("10/minute")
async def login(
    request: Request,
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    db: AsyncSession = Depends(get_db),
):
    user = await db.execute(select(User).where(User.email == form_data.username))
    user = user.scalar_one_or_none()

    if not user or not verify_password(form_data.password, user.hashed_password):
        raise AuthenticationException("Incorrect email or password")

    if not user.is_active:
        raise AuthorizationException("Account is deactivated")

    access_token = create_access_token(
        subject=user.id,
        additional_claims={"role": user.role.value if hasattr(user.role, "value") else str(user.role)},
    )
    refresh_token = create_refresh_token(subject=user.id)

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        user=UserResponse.model_validate(user),
    )


@router.post("/refresh", response_model=TokenResponse)
@limiter.limit("20/minute")
async def refresh_token(
    request: Request,
    data: TokenRefreshRequest,
    db: AsyncSession = Depends(get_db),
):
    payload = decode_token(data.refresh_token)
    if not payload or payload.get("type") != "refresh":
        raise AuthenticationException("Invalid refresh token")

    user_id_str = payload.get("sub")
    if not user_id_str:
        raise AuthenticationException("Invalid token payload")
    try:
        user_id = UUID(user_id_str) if isinstance(user_id_str, str) else user_id_str
    except ValueError:
        raise AuthenticationException("Invalid user ID in token")

    user = await db.get(User, user_id)
    if not user or not user.is_active:
        raise AuthenticationException("User not found or inactive")

    access_token = create_access_token(
        subject=user.id,
        additional_claims={"role": user.role.value if hasattr(user.role, "value") else str(user.role)},
    )
    new_refresh_token = create_refresh_token(subject=user.id)

    return TokenResponse(
        access_token=access_token,
        refresh_token=new_refresh_token,
        token_type="bearer",
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        user=UserResponse.model_validate(user),
    )


@router.post("/logout")
@limiter.limit("10/minute")
async def logout(request: Request):
    return {"message": "Successfully logged out"}


@router.post("/password-reset/request")
@limiter.limit("3/hour")
async def request_password_reset(
    request: Request,
    data: PasswordResetRequest,
    db: AsyncSession = Depends(get_db),
):
    user = await db.execute(select(User).where(User.email == data.email))
    user = user.scalar_one_or_none()

    if user:
        reset_token = create_password_reset_token(user.email)
        await send_password_reset_email(user.email, reset_token)

    return {"message": "If the email exists, a password reset link has been sent"}


@router.post("/password-reset/confirm")
@limiter.limit("5/hour")
async def confirm_password_reset(
    request: Request,
    data: PasswordResetConfirm,
    db: AsyncSession = Depends(get_db),
):
    payload = decode_token(data.token)
    if not payload or payload.get("type") != "password_reset":
        raise AuthenticationException("Invalid or expired reset token")

    email = payload.get("sub")
    user = await db.execute(select(User).where(User.email == email))
    user = user.scalar_one_or_none()

    if not user:
        raise AuthenticationException("Invalid or expired reset token")

    user.hashed_password = get_password_hash(data.new_password)
    await db.commit()

    return {"message": "Password has been reset successfully"}


@router.post("/email/verify")
@limiter.limit("5/hour")
async def verify_email(
    request: Request,
    data: EmailVerificationRequest,
    db: AsyncSession = Depends(get_db),
):
    payload = decode_token(data.token)
    if not payload or payload.get("type") != "email_verification":
        raise AuthenticationException("Invalid or expired verification token")

    email = payload.get("sub")
    user = await db.execute(select(User).where(User.email == email))
    user = user.scalar_one_or_none()

    if not user:
        raise AuthenticationException("Invalid or expired verification token")

    user.is_verified = True
    await db.commit()

    return {"message": "Email verified successfully"}


@router.post("/email/resend-verification")
@limiter.limit("3/hour")
async def resend_verification(
    request: Request,
    data: EmailVerificationRequest,
    db: AsyncSession = Depends(get_db),
):
    payload = decode_token(data.token)
    if not payload or payload.get("type") != "email_verification":
        raise AuthenticationException("Invalid or expired verification token")

    email = payload.get("sub")
    user = await db.execute(select(User).where(User.email == email))
    user = user.scalar_one_or_none()

    if user and not user.is_verified:
        new_token = create_email_verification_token(user.email)
        await send_email_verification(user.email, new_token)

    return {
        "message": "If the email exists and is not verified, a new verification link has been sent"
    }


from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

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

    user_id = payload.get("sub")
    user = await db.get(User, user_id)
    if not user:
        raise AuthenticationException("User not found")

    if not user.is_active:
        raise AuthorizationException("Account is deactivated")

    return user


def require_role(*allowed_roles: str):
    async def role_checker(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role.value not in allowed_roles:
            raise AuthorizationException("Insufficient permissions")
        return current_user

    return role_checker
