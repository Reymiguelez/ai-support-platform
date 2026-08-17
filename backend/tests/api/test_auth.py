from unittest.mock import patch
from uuid import uuid4

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.models import User, UserRole


class TestAuthAPI:
    @pytest.mark.asyncio
    async def test_register_success(self, client: AsyncClient):
        response = await client.post(
            "/api/v1/auth/register",
            json={
                "email": "newuser@example.com",
                "username": "newuser",
                "full_name": "New User",
                "password": "password123",
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"
        assert data["user"]["email"] == "newuser@example.com"

    @pytest.mark.asyncio
    async def test_register_duplicate_email(self, client: AsyncClient, test_db: AsyncSession, test_user: User):
        test_db.add(test_user)
        await test_db.flush()

        response = await client.post(
            "/api/v1/auth/register",
            json={
                "email": test_user.email,
                "username": "anotheruser",
                "full_name": "Another User",
                "password": "password123",
            },
        )
        assert response.status_code == 409
        assert "already registered" in response.json()["error"]["message"].lower()

    @pytest.mark.asyncio
    async def test_register_duplicate_username(self, client: AsyncClient, test_db: AsyncSession, test_user: User):
        test_db.add(test_user)
        await test_db.flush()

        response = await client.post(
            "/api/v1/auth/register",
            json={
                "email": "another@example.com",
                "username": test_user.username,
                "full_name": "Another User",
                "password": "password123",
            },
        )
        assert response.status_code == 409
        assert "already taken" in response.json()["error"]["message"].lower()

    @pytest.mark.asyncio
    async def test_register_invalid_email(self, client: AsyncClient):
        response = await client.post(
            "/api/v1/auth/register",
            json={
                "email": "invalid-email",
                "username": "testuser",
                "full_name": "Test User",
                "password": "password123",
            },
        )
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_register_short_password(self, client: AsyncClient):
        response = await client.post(
            "/api/v1/auth/register",
            json={
                "email": "test@example.com",
                "username": "testuser",
                "full_name": "Test User",
                "password": "short",
            },
        )
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_login_success(self, client: AsyncClient, test_db: AsyncSession, test_user: User):
        test_db.add(test_user)
        await test_db.flush()

        with patch("app.core.security.verify_password", return_value=True):
            response = await client.post(
                "/api/v1/auth/login", data={"username": test_user.email, "password": "password123"}
            )
            assert response.status_code == 200
            data = response.json()
            assert "access_token" in data
            assert "refresh_token" in data

    @pytest.mark.asyncio
    async def test_login_invalid_credentials(self, client: AsyncClient, test_db: AsyncSession, test_user: User):
        test_db.add(test_user)
        await test_db.flush()

        with patch("app.core.security.verify_password", return_value=False):
            response = await client.post(
                "/api/v1/auth/login",
                data={"username": test_user.email, "password": "wrongpassword"},
            )
            assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_login_inactive_user(self, client: AsyncClient, test_db: AsyncSession):
        from app.core.security import get_password_hash

        inactive_user = User(
            id=uuid4(),
            email="inactive@example.com",
            username="inactiveuser",
            full_name="Inactive User",
            hashed_password=get_password_hash("password123"),
            role=UserRole.CUSTOMER,
            is_active=False,
            is_verified=True,
        )
        test_db.add(inactive_user)
        await test_db.flush()

        with patch("app.core.security.verify_password", return_value=True):
            response = await client.post(
                "/api/v1/auth/login",
                data={"username": "inactive@example.com", "password": "password123"},
            )
            assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_refresh_token_success(self, client: AsyncClient, test_db: AsyncSession, test_user: User):
        from app.core.security import create_refresh_token

        test_db.add(test_user)
        await test_db.flush()

        refresh_token = create_refresh_token(subject=test_user.id)

        response = await client.post(
            "/api/v1/auth/refresh", json={"refresh_token": refresh_token}
        )
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data

    @pytest.mark.asyncio
    async def test_refresh_token_invalid(self, client: AsyncClient):
        response = await client.post(
            "/api/v1/auth/refresh", json={"refresh_token": "invalid.token.here"}
        )
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_logout(self, client: AsyncClient):
        response = await client.post("/api/v1/auth/logout")
        assert response.status_code == 200
        assert response.json()["message"] == "Successfully logged out"

    @pytest.mark.asyncio
    async def test_password_reset_request(self, client: AsyncClient, test_db: AsyncSession, test_user: User):
        test_db.add(test_user)
        await test_db.flush()

        response = await client.post(
            "/api/v1/auth/password-reset/request", json={"email": test_user.email}
        )
        assert response.status_code == 200
        assert "password reset link has been sent" in response.json()["message"]

    @pytest.mark.asyncio
    async def test_password_reset_request_nonexistent(self, client: AsyncClient):
        response = await client.post(
            "/api/v1/auth/password-reset/request", json={"email": "nonexistent@example.com"}
        )
        assert response.status_code == 200
        assert "password reset link has been sent" in response.json()["message"]

    @pytest.mark.asyncio
    async def test_password_reset_confirm(self, client: AsyncClient, test_db: AsyncSession, test_user: User):
        from app.core.security import create_password_reset_token

        test_db.add(test_user)
        await test_db.flush()

        reset_token = create_password_reset_token(test_user.email)

        response = await client.post(
            "/api/v1/auth/password-reset/confirm",
            json={"token": reset_token, "new_password": "newpassword123"},
        )
        assert response.status_code == 200
        assert "password has been reset" in response.json()["message"].lower()

    @pytest.mark.asyncio
    async def test_email_verification(self, client: AsyncClient, test_db: AsyncSession, test_user: User):
        from app.core.security import create_email_verification_token

        test_db.add(test_user)
        await test_db.flush()

        verify_token = create_email_verification_token(test_user.email)

        response = await client.post("/api/v1/auth/email/verify", json={"token": verify_token})
        assert response.status_code == 200
        assert "verified" in response.json()["message"].lower()

    @pytest.mark.asyncio
    async def test_resend_verification(self, client: AsyncClient, test_db: AsyncSession, test_user: User):
        from app.core.security import create_email_verification_token

        test_db.add(test_user)
        await test_db.flush()

        verify_token = create_email_verification_token(test_user.email)

        response = await client.post(
            "/api/v1/auth/email/resend-verification", json={"token": verify_token}
        )
        assert response.status_code == 200
