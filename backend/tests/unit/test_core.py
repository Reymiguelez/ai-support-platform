from uuid import uuid4

from app.core.config import settings
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    get_password_hash,
    is_token_expired,
    verify_password,
)


class TestSecurity:
    def test_password_hashing(self):
        password = "testpassword123"
        hashed = get_password_hash(password)
        assert verify_password(password, hashed)
        assert not verify_password("wrongpassword", hashed)

    def test_create_access_token(self):
        user_id = uuid4()
        token = create_access_token(subject=user_id, additional_claims={"role": "admin"})
        assert token is not None
        payload = decode_token(token)
        assert payload is not None
        assert payload["sub"] == str(user_id)
        assert payload["type"] == "access"
        assert payload["role"] == "admin"

    def test_create_refresh_token(self):
        user_id = uuid4()
        token = create_refresh_token(subject=user_id)
        assert token is not None
        payload = decode_token(token)
        assert payload is not None
        assert payload["sub"] == str(user_id)
        assert payload["type"] == "refresh"

    def test_token_expiry(self):
        user_id = uuid4()
        token = create_access_token(subject=user_id, expires_delta=None)
        assert not is_token_expired(token)

    def test_invalid_token(self):
        assert decode_token("invalid.token.here") is None
        assert is_token_expired("invalid.token.here")


class TestConfig:
    def test_settings_loaded(self):
        assert settings.PROJECT_NAME == "AI Support Platform"
        assert settings.VERSION == "0.1.0"
        assert settings.API_V1_PREFIX == "/api/v1"
        assert settings.ALGORITHM == "HS256"
        assert settings.ACCESS_TOKEN_EXPIRE_MINUTES == 30

    def test_database_url_construction(self):
        assert "postgresql+asyncpg://" in str(settings.DATABASE_URL)
        assert settings.POSTGRES_USER in str(settings.DATABASE_URL)
        assert settings.POSTGRES_DB in str(settings.DATABASE_URL)

    def test_redis_url_construction(self):
        assert "redis://" in str(settings.REDIS_URL)
        assert str(settings.REDIS_PORT) in str(settings.REDIS_URL)
