"""Tests for the Dashboard API."""

from datetime import datetime, timedelta
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession

from kachi.apps.dashboard_api.main import app
from kachi.lib.db import get_session
from kachi.lib.models import Customer, MeterReading, WorkflowDefinition


@pytest.fixture
def client(db_session):
    """Create test client with database session override."""

    async def get_test_session():
        yield db_session

    app.dependency_overrides[get_session] = get_test_session
    return TestClient(app)


@pytest.fixture
async def sample_customer(db_session: AsyncSession):
    """Create a sample customer for testing."""
    customer = Customer(
        id=uuid4(),
        name="Test Customer",
        lago_customer_id="test_customer_123",
        active=True,
    )
    db_session.add(customer)
    await db_session.commit()
    await db_session.refresh(customer)
    return customer


@pytest.fixture
async def sample_workflow(db_session: AsyncSession):
    """Create a sample workflow definition."""
    workflow = WorkflowDefinition(
        id=uuid4(),
        key="test_workflow",
        version=1,
        definition_schema={"type": "test"},
        active=True,
    )
    db_session.add(workflow)
    await db_session.commit()
    await db_session.refresh(workflow)
    return workflow


@pytest.fixture
async def sample_meter_readings(
    db_session: AsyncSession, sample_customer, sample_workflow
):
    """Create sample meter readings."""
    base_time = datetime.utcnow().replace(minute=0, second=0, microsecond=0)

    readings = []
    for i in range(5):
        reading = MeterReading(
            id=uuid4(),
            customer_id=sample_customer.id,
            workflow_id=sample_workflow.id,
            meter_name="api_calls",
            value=100 + i * 10,
            window_start=base_time - timedelta(hours=i),
            window_end=base_time - timedelta(hours=i - 1),
            reading_type="edge",
        )
        readings.append(reading)
        db_session.add(reading)

    await db_session.commit()
    return readings


class TestDashboardAPI:
    """Test cases for Dashboard API endpoints."""

    def test_health_check(self, client):
        """Test health check endpoint."""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "timestamp" in data

    @pytest.mark.asyncio
    async def test_list_customers(self, client, sample_customer):
        """Test customer listing endpoint."""
        response = client.get("/v1/customers")
        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 1

        customer_data = next(c for c in data if c["id"] == str(sample_customer.id))
        assert customer_data["name"] == "Test Customer"
        assert customer_data["lago_customer_id"] == "test_customer_123"
        assert customer_data["active"] is True

    @pytest.mark.asyncio
    async def test_customer_usage_summary(
        self, client, sample_customer, sample_meter_readings
    ):
        """Test customer usage summary endpoint."""
        response = client.get(f"/v1/customers/{sample_customer.id}/usage/summary")
        assert response.status_code == 200
        data = response.json()

        assert data["customer_id"] == str(sample_customer.id)
        assert "meters" in data
        assert len(data["meters"]) > 0

        # Check meter data structure
        meter = data["meters"][0]
        assert "name" in meter
        assert "current_usage" in meter
        assert "limit" in meter
        assert "percentage" in meter

    @pytest.mark.asyncio
    async def test_customer_meter_details(
        self, client, sample_customer, sample_meter_readings
    ):
        """Test customer meter details endpoint."""
        response = client.get(
            f"/v1/customers/{sample_customer.id}/meters/api_calls"
            f"?from_date=2024-01-01T00:00:00"
            f"&to_date=2024-12-31T23:59:59"
        )
        assert response.status_code == 200
        data = response.json()

        assert data["customer_id"] == str(sample_customer.id)
        assert data["meter_name"] == "api_calls"
        assert "usage_data" in data
        assert len(data["usage_data"]) > 0

    def test_customer_not_found(self, client):
        """Test customer not found scenarios."""
        fake_id = str(uuid4())

        response = client.get(f"/v1/customers/{fake_id}/usage/summary")
        assert response.status_code == 404

    def test_cors_headers(self, client):
        """Test CORS headers are present."""
        response = client.get("/v1/customers")
        assert response.status_code == 200
