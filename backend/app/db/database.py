"""
Database Configuration - SQLAlchemy Async Support for PostgreSQL.
Sử dụng async engine để không block event loop.
"""
from typing import AsyncGenerator
from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.pool import NullPool
import logging

from ..config import settings

logger = logging.getLogger(__name__)


# Async Engine - sử dụng asyncpg driver
DATABASE_URL = (
    f"postgresql+asyncpg://{settings.postgres_user}:{settings.postgres_password}"
    f"@{settings.postgres_host}:{settings.postgres_port}/{settings.postgres_db}"
)

# Sync Engine - cho migrations và scripts
SYNC_DATABASE_URL = (
    f"postgresql://{settings.postgres_user}:{settings.postgres_password}"
    f"@{settings.postgres_host}:{settings.postgres_port}/{settings.postgres_db}"
)


# Create async engine
engine = create_async_engine(
    DATABASE_URL,
    echo=settings.database_echo,  # SQL echo mode for debugging
    poolclass=NullPool,  # NullPool cho async context, tránh connection stuck
    pool_pre_ping=True,  # Verify connections trước khi dùng
)

# Session factory
async_session_factory = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


class Base(DeclarativeBase):
    """Base class cho tất cả SQLAlchemy models."""
    pass


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency cho FastAPI - inject database session vào route.
    
    Usage:
        @app.get("/items")
        async def get_items(db: AsyncSession = Depends(get_db)):
            ...
    """
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def init_db() -> None:
    """
    Initialize database - tạo tất cả tables.
    Gọi khi app start.
    """
    from ..admin.models import Session, ChatLog, UsageStats, Document  # noqa
    
    async with engine.begin() as conn:
        # Create all tables
        await conn.run_sync(Base.metadata.create_all)
    
    logger.info("Database tables created successfully")


async def drop_db() -> None:
    """
    Drop tất cả tables (DANGER - chỉ dùng trong development).
    """
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    
    logger.warning("All database tables dropped")


@asynccontextmanager
async def get_db_context() -> AsyncGenerator[AsyncSession, None]:
    """
    Context manager cho non-FastAPI contexts (scripts, background tasks).
    
    Usage:
        async with get_db_context() as db:
            result = await db.execute(select(User))
    """
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
