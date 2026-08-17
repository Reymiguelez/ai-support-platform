
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import create_access_token
from app.domain.models import User


class TestChatAPI:
    @pytest.mark.asyncio
    async def test_create_conversation(self, client: AsyncClient, test_db: AsyncSession, test_user: User):
        test_db.add(test_user)
        await test_db.flush()

        token = create_access_token(subject=test_user.id, additional_claims={"role": test_user.role.value})
        headers = {"Authorization": f"Bearer {token}"}

        response = await client.post(
            "/api/v1/chat/conversations",
            json={"title": "Test Chat", "system_prompt": "You are a helpful assistant."},
            headers=headers,
        )
        assert response.status_code == 201
        data = response.json()
        assert data["title"] == "Test Chat"
        assert data["user_id"] == str(test_user.id)

    @pytest.mark.asyncio
    async def test_list_conversations(self, client: AsyncClient, test_db: AsyncSession, test_user: User):
        test_db.add(test_user)
        await test_db.flush()

        token = create_access_token(subject=test_user.id, additional_claims={"role": test_user.role.value})
        headers = {"Authorization": f"Bearer {token}"}

        # Create one conversation first
        await client.post(
            "/api/v1/chat/conversations",
            json={"title": "Test Chat 1"},
            headers=headers,
        )

        response = await client.get("/api/v1/chat/conversations", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 1

    @pytest.mark.asyncio
    async def test_get_conversation_by_id(self, client: AsyncClient, test_db: AsyncSession, test_user: User):
        test_db.add(test_user)
        await test_db.flush()

        token = create_access_token(subject=test_user.id, additional_claims={"role": test_user.role.value})
        headers = {"Authorization": f"Bearer {token}"}

        create_res = await client.post(
            "/api/v1/chat/conversations",
            json={"title": "Test Chat Details"},
            headers=headers,
        )
        conv_id = create_res.json()["id"]

        response = await client.get(f"/api/v1/chat/conversations/{conv_id}", headers=headers)
        assert response.status_code == 200
        assert response.json()["id"] == conv_id

    @pytest.mark.asyncio
    async def test_chat_message(self, client: AsyncClient, test_db: AsyncSession, test_user: User):
        test_db.add(test_user)
        await test_db.flush()

        token = create_access_token(subject=test_user.id, additional_claims={"role": test_user.role.value})
        headers = {"Authorization": f"Bearer {token}"}

        response = await client.post(
            "/api/v1/chat/chat",
            json={"message": "Hello AI!", "use_rag": False, "use_tools": False},
            headers=headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert "conversation_id" in data
