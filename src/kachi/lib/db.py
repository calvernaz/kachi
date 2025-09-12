"""Database configuration and session management."""

import os
from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlmodel import SQLModel

# Database configuration
DATABASE_URL = os.getenv(
    "DATABASE_URL", "postgresql+asyncpg://postgres:postgres@localhost:5432/kachi"
)

# Create async engine
engine = create_async_engine(
    DATABASE_URL,
    echo=bool(os.getenv("DB_ECHO", "False") == "True"),
    future=True,
)

# Create session maker
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """Get database session."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()


async def create_db_and_tables() -> None:
    """Create database tables."""
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)


async def drop_db_and_tables() -> None:
    """Drop database tables."""
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.drop_all)
