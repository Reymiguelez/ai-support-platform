import asyncio
from collections.abc import AsyncGenerator
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

import app.domain.models
from app.core.database import Base, get_db
from app.domain.models import User, UserRole
from app.main import app


@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
async def test_engine():
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()


@pytest.fixture
async def test_db(test_engine) -> AsyncGenerator[AsyncSession]:
    async_session = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)
    async with async_session() as session:
        yield session
        await session.rollback()
    async with test_engine.begin() as conn:
        for table in reversed(Base.metadata.sorted_tables):
            await conn.execute(table.delete())


@pytest.fixture
async def client(test_db) -> AsyncGenerator[AsyncClient]:
    async def _override_get_db():
        yield test_db

    app.dependency_overrides[get_db] = _override_get_db
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()


@pytest.fixture
def test_user() -> User:
    from app.core.security import get_password_hash

    return User(
        id=uuid4(),
        email="test@example.com",
        username="testuser",
        full_name="Test User",
        hashed_password=get_password_hash("password123"),
        role=UserRole.CUSTOMER,
        is_active=True,
        is_verified=True,
    )


@pytest.fixture
def admin_user() -> User:
    from app.core.security import get_password_hash

    return User(
        id=uuid4(),
        email="admin@example.com",
        username="adminuser",
        full_name="Admin User",
        hashed_password=get_password_hash("password123"),
        role=UserRole.ADMIN,
        is_active=True,
        is_verified=True,
    )


@pytest.fixture
def auth_headers(test_user):
    from app.core.security import create_access_token

    token = create_access_token(
        subject=test_user.id, additional_claims={"role": test_user.role.value}
    )
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def admin_auth_headers(admin_user):
    from app.core.security import create_access_token

    token = create_access_token(
        subject=admin_user.id, additional_claims={"role": admin_user.role.value}
    )
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture(autouse=True)
def mock_openai():
    from unittest.mock import MagicMock

    async def _mock_chat_completion(*args, **kwargs):
        chunk = MagicMock()
        chunk.choices = [MagicMock(delta=MagicMock(content="Mocked AI response", tool_calls=None))]
        yield chunk

    with (
        patch("app.infrastructure.ai.client.openai_client") as mock1,
        patch("app.services.chat.openai_client") as mock2,
    ):
        mock1.chat_completion = _mock_chat_completion
        mock1.create_embedding = AsyncMock(return_value=[0.1] * 1536)
        mock1.create_embeddings_batch = AsyncMock(return_value=[[0.1] * 1536])
        mock2.chat_completion = _mock_chat_completion
        mock2.create_embedding = AsyncMock(return_value=[0.1] * 1536)
        mock2.create_embeddings_batch = AsyncMock(return_value=[[0.1] * 1536])
        yield mock1


@pytest.fixture(autouse=True)
def mock_vector_store():
    with patch("app.infrastructure.ai.rag.rag_service.vector_store") as mock:
        mock.add_documents = AsyncMock()
        mock.search = AsyncMock(return_value=[])
        mock.delete_documents = AsyncMock()
        mock.delete_collection = AsyncMock()
        yield mock


@pytest.fixture(autouse=True)
def mock_rate_limiter():
    from app.utils.rate_limiter import limiter
    limiter.enabled = False
    yield
    limiter.enabled = True


@pytest.fixture(autouse=True)
def mock_email():
    with (
        patch("app.services.email.send_email_verification", new_callable=AsyncMock) as mock_verify,
        patch("app.services.email.send_password_reset_email", new_callable=AsyncMock) as mock_reset,
    ):
        mock_verify.return_value = True
        mock_reset.return_value = True
        yield
