import asyncio
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.config import settings
from app.core.logging import get_logger
from app.domain.models.base import Base

logger = get_logger(__name__)


engine: AsyncEngine = create_async_engine(
    str(settings.DATABASE_URL),
    echo=settings.DEBUG,
    pool_pre_ping=False,
    pool_size=10,
    max_overflow=20,
    pool_recycle=3600,
    connect_args={"ssl": False},
)

AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
    autocommit=False,
)


async def get_db() -> AsyncGenerator[AsyncSession]:
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


@asynccontextmanager
async def get_db_context() -> AsyncGenerator[AsyncSession]:
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def init_db() -> None:
    max_retries = 30
    retry_delay = 2
    initial_delay = 10

    logger.info(f"Waiting {initial_delay}s before first database connection attempt")
    await asyncio.sleep(initial_delay)

    # Test network connectivity
    import socket

    try:
        ip = socket.gethostbyname("postgres")
        logger.info(f"DNS resolution: postgres -> {ip}")
    except Exception as e:
        logger.warning(f"DNS resolution failed: {e}")

    try:
        s = socket.socket()
        s.settimeout(5)
        s.connect(("postgres", 5432))
        logger.info("TCP connection to postgres:5432 successful")
        s.close()
    except Exception as e:
        logger.warning(f"TCP connection test failed: {e}")

    for attempt in range(max_retries):
        url = str(settings.DATABASE_URL)
        logger.info(f"Attempting connection with URL: {url}")
        engine = create_async_engine(
            url,
            echo=settings.DEBUG,
            pool_pre_ping=False,
            pool_size=1,
            max_overflow=0,
            pool_recycle=3600,
            connect_args={"ssl": False},
        )
        try:
            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)
            logger.info("Database initialized successfully")
            await engine.dispose()
            return
        except Exception as e:
            await engine.dispose()
            logger.error(f"Connection error details: {type(e).__name__}: {e}")
            if attempt < max_retries - 1:
                logger.warning(
                    f"Database connection failed (attempt {attempt + 1}/{max_retries}), retrying in {retry_delay}s"
                )
                await asyncio.sleep(retry_delay)
            else:
                logger.error(f"Database connection failed after {max_retries} attempts")
                raise


async def close_db() -> None:
    await engine.dispose()
