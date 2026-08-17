
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import create_access_token
from app.domain.models import User


class TestUsersAPI:
    @pytest.mark.asyncio
    async def test_get_current_user_profile(self, client: AsyncClient, test_db: AsyncSession, test_user: User):
        test_db.add(test_user)
        await test_db.flush()

        token = create_access_token(subject=test_user.id, additional_claims={"role": test_user.role.value})
        headers = {"Authorization": f"Bearer {token}"}

        response = await client.get("/api/v1/users/me", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert data["email"] == test_user.email
        assert data["username"] == test_user.username

    @pytest.mark.asyncio
    async def test_update_current_user_profile(self, client: AsyncClient, test_db: AsyncSession, test_user: User):
        test_db.add(test_user)
        await test_db.flush()

        token = create_access_token(subject=test_user.id, additional_claims={"role": test_user.role.value})
        headers = {"Authorization": f"Bearer {token}"}

        response = await client.patch(
            "/api/v1/users/me",
            json={"full_name": "Updated Name"},
            headers=headers,
        )
        assert response.status_code == 200
        assert response.json()["full_name"] == "Updated Name"

    @pytest.mark.asyncio
    async def test_change_password_success(self, client: AsyncClient, test_db: AsyncSession, test_user: User):
        test_db.add(test_user)
        await test_db.flush()

        token = create_access_token(subject=test_user.id, additional_claims={"role": test_user.role.value})
        headers = {"Authorization": f"Bearer {token}"}

        response = await client.post(
            "/api/v1/users/me/change-password",
            json={"current_password": "password123", "new_password": "newpassword123"},
            headers=headers,
        )
        assert response.status_code == 200
        assert response.json()["message"] == "Password changed successfully"

    @pytest.mark.asyncio
    async def test_change_password_incorrect_current(self, client: AsyncClient, test_db: AsyncSession, test_user: User):
        test_db.add(test_user)
        await test_db.flush()

        token = create_access_token(subject=test_user.id, additional_claims={"role": test_user.role.value})
        headers = {"Authorization": f"Bearer {token}"}

        response = await client.post(
            "/api/v1/users/me/change-password",
            json={"current_password": "wrongpassword", "new_password": "newpassword123"},
            headers=headers,
        )
        assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_list_users_as_admin(self, client: AsyncClient, test_db: AsyncSession, admin_user: User):
        test_db.add(admin_user)
        await test_db.flush()

        token = create_access_token(subject=admin_user.id, additional_claims={"role": admin_user.role.value})
        headers = {"Authorization": f"Bearer {token}"}

        response = await client.get("/api/v1/users", headers=headers)
        assert response.status_code == 200
        assert isinstance(response.json(), list)

    @pytest.mark.asyncio
    async def test_get_user_by_id_as_admin(self, client: AsyncClient, test_db: AsyncSession, admin_user: User, test_user: User):
        test_db.add(admin_user)
        test_db.add(test_user)
        await test_db.flush()

        token = create_access_token(subject=admin_user.id, additional_claims={"role": admin_user.role.value})
        headers = {"Authorization": f"Bearer {token}"}

        response = await client.get(f"/api/v1/users/{test_user.id}", headers=headers)
        assert response.status_code == 200
        assert response.json()["id"] == str(test_user.id)
