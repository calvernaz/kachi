"""Pytest configuration and shared fixtures."""

import asyncio
import json
import os
from collections.abc import AsyncGenerator

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from kachi.lib.models import SQLModel

# Test database configuration
TEST_DATABASE_URL = os.getenv("TEST_DATABASE_URL", "sqlite+aiosqlite:///:memory:")

# For SQLite testing, we need to handle JSONB compatibility
if "sqlite" in TEST_DATABASE_URL:
    # Override JSONB with TEXT for SQLite compatibility
    import sys
    from unittest.mock import MagicMock
    from sqlalchemy import Text

    # Create a mock module that replaces JSONB with Text
    mock_postgresql = MagicMock()
    mock_postgresql.JSONB = Text
    mock_postgresql.ARRAY = Text  # Also handle ARRAY
    mock_postgresql.BIGINT = Text  # And BIGINT
    mock_postgresql.TIMESTAMP = Text  # And TIMESTAMP

    # Replace the postgresql module in sys.modules
    sys.modules['sqlalchemy.dialects.postgresql'] = mock_postgresql
    from sqlalchemy.types import TEXT, TypeDecorator

    class JSONBCompat(TypeDecorator):
        """JSONB compatibility layer for SQLite."""

        impl = TEXT
        cache_ok = True

        def process_bind_param(self, value, dialect):
            if value is not None:
                return json.dumps(value)
            return value

        def process_result_value(self, value, dialect):
            if value is not None:
                return json.loads(value)
            return value

    # Update the mock to use JSONBCompat
    mock_postgresql.JSONB = JSONBCompat


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
async def test_engine():
    """Create test database engine."""
    engine = create_async_engine(TEST_DATABASE_URL, echo=False)

    # Create all tables
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)

    yield engine

    # Clean up
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.drop_all)

    await engine.dispose()


@pytest.fixture
async def db_session(test_engine) -> AsyncGenerator[AsyncSession, None]:
    """Create a database session for testing."""
    TestSessionLocal = sessionmaker(
        test_engine, class_=AsyncSession, expire_on_commit=False
    )

    async with TestSessionLocal() as session:
        yield session
        await session.rollback()


@pytest.fixture
async def clean_db(test_engine):
    """Clean database between tests."""
    async with test_engine.begin() as conn:
        # Get all table names
        tables = await conn.run_sync(lambda sync_conn: SQLModel.metadata.tables.keys())

        # Truncate all tables
        for table_name in tables:
            await conn.execute(f"DELETE FROM {table_name}")

        await conn.commit()
