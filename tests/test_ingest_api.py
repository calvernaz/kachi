"""Tests for the ingestion API."""

import os
from datetime import datetime
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from kachi.apps.ingest_api.main import app
from kachi.lib.db import get_session
from kachi.lib.models import Customer, SQLModel

# Test database setup - Use PostgreSQL for testing to match production

TEST_DATABASE_URL = os.getenv(
    "TEST_DATABASE_URL",
    "sqlite+aiosqlite:///:memory:",
)

test_engine = create_async_engine(TEST_DATABASE_URL, echo=False)
TestSessionLocal = sessionmaker(
    test_engine, class_=AsyncSession, expire_on_commit=False
)


async def get_test_session():
    """Override database session for testing."""
    async with TestSessionLocal() as session:
        yield session


app.dependency_overrides[get_session] = get_test_session

client = TestClient(app)


@pytest.fixture
async def setup_database():
    """Set up test database."""
    async with test_engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)

    # Create a test customer
    async with TestSessionLocal() as session:
        customer = Customer(
            id=uuid4(),
            name="Test Customer",
            lago_customer_id="test_customer_123",
            active=True,
        )
        session.add(customer)
        await session.commit()
        yield customer.id

    async with test_engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.drop_all)


def test_health_check():
    """Test health check endpoint."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "timestamp" in data


@pytest.mark.asyncio
async def test_outcome_event_submission(setup_database):
    """Test outcome event submission."""
    customer_id = await setup_database

    outcome_data = {
        "customer_id": str(customer_id),
        "event_name": "ticket_resolved",
        "timestamp": datetime.utcnow().isoformat(),
        "attributes": {
            "outcome.type": "ticket_resolution",
            "outcome.value": "resolved",
            "sla.met": True,
        },
    }

    response = client.post("/v1/events/outcome", json=outcome_data)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert "event_id" in data


@pytest.mark.asyncio
async def test_usage_preview(setup_database):
    """Test usage preview endpoint."""
    customer_id = await setup_database

    response = client.get(
        f"/v1/usage/preview?customer_id={customer_id}"
        f"&from_date=2024-01-01T00:00:00"
        f"&to_date=2024-01-31T23:59:59"
        f"&include_breakdown=true"
    )
    assert response.status_code == 200
    data = response.json()
    assert data["customer_id"] == str(customer_id)
    assert "meters" in data
    assert "estimated_cost" in data
    assert "breakdown" in data


def test_otel_export_invalid_data():
    """Test OTel export with invalid data."""
    invalid_data = {
        "resource_spans": [
            {
                "resource": {"attributes": {}},
                "scope_spans": [
                    {
                        "spans": [
                            {
                                "trace_id": "invalid_trace",
                                "span_id": "invalid_span",
                                "name": "test_span",
                                "start_time_unix_nano": 1640995200000000000,
                                "attributes": {},  # Missing billing.customer_id
                            }
                        ]
                    }
                ],
            }
        ]
    }

    response = client.post("/v1/otel", json=invalid_data)
    # The API returns 200 but logs errors for invalid spans
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert "processed_spans" in data


@pytest.mark.asyncio
async def test_adjustment_creation(setup_database):
    """Test billing adjustment creation."""
    customer_id = await setup_database

    adjustment_data = {
        "customer_id": str(customer_id),
        "amount": -50.0,
        "reason": "Service credit",
        "actor": "admin@example.com",
    }

    response = client.post("/v1/adjustments", json=adjustment_data)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert "adjustment_id" in data


if __name__ == "__main__":
    pytest.main([__file__])
