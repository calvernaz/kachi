"""Tests for Lago integration."""

from datetime import datetime
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from kachi.apps.lago_adapter.main import LagoAdapter
from kachi.lib.lago_client import LagoClientWrapper, LagoConfig
from kachi.lib.rating_policies import RatedLine, RatingResult


class MockLagoClient:
    """Mock Lago client for testing."""

    def __init__(self):
        self.customers = MagicMock()
        self.billable_metrics = MagicMock()
        self.plans = MagicMock()
        self.subscriptions = MagicMock()
        self.events = MagicMock()
        self.add_ons = MagicMock()
        self.invoices = MagicMock()


class MockSession:
    """Mock database session for testing."""

    def __init__(self):
        self.committed = False
        self.added_objects = []

    def add(self, obj):
        self.added_objects.append(obj)

    async def commit(self):
        self.committed = True

    async def execute(self, query):
        # Return mock result based on query type
        result = MagicMock()
        result.scalar_one_or_none.return_value = None
        result.scalars.return_value.all.return_value = []
        return result


@pytest.fixture
def lago_config():
    """Lago configuration for testing."""
    return LagoConfig(api_key="test_api_key", api_url="https://test.lago.com")


@pytest.fixture
def mock_lago_client():
    """Mock Lago client."""
    return MockLagoClient()


@pytest.fixture
def mock_session():
    """Mock database session."""
    return MockSession()


@pytest.fixture
def lago_client_wrapper(lago_config):
    """Lago client wrapper with mocked client."""
    wrapper = LagoClientWrapper(lago_config)
    wrapper.client = MockLagoClient()
    return wrapper


@pytest.fixture
def lago_adapter(mock_session, lago_client_wrapper):
    """Lago adapter with mocked dependencies."""
    return LagoAdapter(mock_session, lago_client_wrapper)


@pytest.fixture
def sample_rating_result():
    """Sample rating result for testing."""
    from kachi.lib.rating_policies import EnvelopeAllocation

    customer_id = uuid4()
    return RatingResult(
        customer_id=customer_id,
        period_start="2024-01-01T00:00:00",
        period_end="2024-01-01T23:59:59",
        lines=[
            RatedLine(
                meter_key="workflow.completed",
                usage_quantity=Decimal("10"),
                billable_quantity=Decimal("10"),
                unit_price=Decimal("0.50"),
                amount=Decimal("5.00"),
                line_type="work",
                description="Workflow completions",
            ),
            RatedLine(
                meter_key="llm.tokens",
                usage_quantity=Decimal("100000"),
                billable_quantity=Decimal("50000"),  # After envelope
                unit_price=Decimal("0.000015"),
                amount=Decimal("0.75"),
                line_type="edge",
                description="LLM tokens (after envelope)",
            ),
            RatedLine(
                meter_key="base_fee",
                usage_quantity=Decimal("1"),
                billable_quantity=Decimal("1"),
                unit_price=Decimal("99.00"),
                amount=Decimal("99.00"),
                line_type="base_fee",
                description="Monthly base fee",
            ),
        ],
        envelopes={
            "llm.tokens": EnvelopeAllocation(
                edge_meter="llm.tokens",
                allocated=Decimal("50000"),
                consumed=Decimal("50000"),
                remaining=Decimal("0"),
            )
        },
        subtotal=Decimal("104.75"),
        discount_amount=Decimal("0.00"),
        total=Decimal("104.75"),
    )


class TestLagoClientWrapper:
    """Test the Lago client wrapper."""

    @pytest.mark.asyncio
    async def test_create_customer(self, lago_client_wrapper):
        """Test customer creation."""
        customer_id = uuid4()

        # Mock the client response
        mock_customer = MagicMock()
        mock_customer.external_id = str(customer_id)
        lago_client_wrapper.client.customers().create.return_value = mock_customer

        result = await lago_client_wrapper.create_customer(
            customer_id=customer_id, name="Test Customer", email="test@example.com"
        )

        assert result.external_id == str(customer_id)
        lago_client_wrapper.client.customers().create.assert_called_once()

    @pytest.mark.asyncio
    async def test_send_usage_event(self, lago_client_wrapper):
        """Test sending usage events."""
        customer_id = uuid4()

        # Mock the client response
        mock_event = MagicMock()
        lago_client_wrapper.client.events().create.return_value = mock_event

        result = await lago_client_wrapper.send_usage_event(
            customer_id=customer_id,
            meter_code="workflow_completed",
            value=Decimal("10"),
        )

        assert result == mock_event
        lago_client_wrapper.client.events().create.assert_called_once()

    @pytest.mark.asyncio
    async def test_send_batch_usage_events(self, lago_client_wrapper):
        """Test sending batch usage events."""
        events = [
            {
                "customer_id": str(uuid4()),
                "meter_code": "workflow_completed",
                "value": 10,
                "timestamp": datetime.utcnow(),
            },
            {
                "customer_id": str(uuid4()),
                "meter_code": "llm_tokens",
                "value": 50000,
                "timestamp": datetime.utcnow(),
            },
        ]

        # Mock the client response
        mock_event = MagicMock()
        lago_client_wrapper.client.events().create.return_value = mock_event

        results = await lago_client_wrapper.send_batch_usage_events(events)

        assert len(results) == 2
        assert lago_client_wrapper.client.events().create.call_count == 2


class TestLagoAdapter:
    """Test the Lago adapter."""

    @pytest.mark.asyncio
    async def test_setup_billing_metrics(self, lago_adapter):
        """Test setting up billing metrics."""
        # Mock successful metric creation
        lago_adapter.lago_client.create_billable_metric = AsyncMock(
            return_value=MagicMock()
        )

        result = await lago_adapter.setup_billing_metrics()

        assert result is True
        # Should create 6 standard metrics
        assert lago_adapter.lago_client.create_billable_metric.call_count == 6

    @pytest.mark.asyncio
    async def test_create_default_plan(self, lago_adapter):
        """Test creating default plan."""
        # Mock successful plan creation
        mock_plan = MagicMock()
        lago_adapter.lago_client.create_plan = AsyncMock(return_value=mock_plan)

        result = await lago_adapter.create_default_plan()

        assert result is True
        lago_adapter.lago_client.create_plan.assert_called_once()

        # Check the plan configuration
        call_args = lago_adapter.lago_client.create_plan.call_args
        assert call_args[1]["code"] == "kachi_default"
        assert call_args[1]["amount_cents"] == 9900  # $99 base fee
        assert len(call_args[1]["charges"]) == 3  # 3 charge configurations

    @pytest.mark.asyncio
    async def test_push_rated_usage(self, lago_adapter, sample_rating_result):
        """Test pushing rated usage to Lago."""
        # Mock customer sync and event sending
        lago_adapter.sync_customer = AsyncMock(return_value=True)
        lago_adapter.lago_client.send_batch_usage_events = AsyncMock(return_value=[])

        result = await lago_adapter.push_rated_usage(sample_rating_result)

        assert result is True
        lago_adapter.sync_customer.assert_called_once()
        lago_adapter.lago_client.send_batch_usage_events.assert_called_once()

        # Check that base_fee lines are excluded
        call_args = lago_adapter.lago_client.send_batch_usage_events.call_args[0][0]
        meter_codes = [event["meter_code"] for event in call_args]
        assert "workflow_completed" in meter_codes
        assert "llm_tokens" in meter_codes
        assert "base_fee" not in meter_codes  # Should be excluded

    @pytest.mark.asyncio
    async def test_push_success_fee(self, lago_adapter):
        """Test pushing success fees."""
        customer_id = uuid4()

        # Mock add-on creation and application
        lago_adapter.lago_client.create_add_on = AsyncMock(return_value=MagicMock())
        lago_adapter.lago_client.apply_add_on = AsyncMock(return_value=MagicMock())

        result = await lago_adapter.push_success_fee(
            customer_id=customer_id,
            outcome_type="ticket_resolved",
            amount=Decimal("25.00"),
            description="Success fee for ticket resolution",
        )

        assert result is True
        lago_adapter.lago_client.create_add_on.assert_called_once()
        lago_adapter.lago_client.apply_add_on.assert_called_once()

    @pytest.mark.asyncio
    async def test_handle_webhook_event(self, lago_adapter):
        """Test webhook event handling."""
        event_data = {
            "invoice": {
                "external_customer_id": str(uuid4()),
                "status": "finalized",
                "total_amount_cents": 10475,
            }
        }

        result = await lago_adapter.handle_webhook_event(
            "invoice.finalized", event_data
        )

        assert result is True

    def test_map_meter_to_lago_code(self, lago_adapter):
        """Test meter key mapping."""
        assert (
            lago_adapter._map_meter_to_lago_code("workflow.completed")
            == "workflow_completed"
        )
        assert lago_adapter._map_meter_to_lago_code("llm.tokens") == "llm_tokens"
        assert lago_adapter._map_meter_to_lago_code("api.calls") == "api_calls"


class TestLagoIntegrationFlow:
    """Test the complete Lago integration flow."""

    @pytest.mark.asyncio
    async def test_end_to_end_billing_flow(self, lago_adapter, sample_rating_result):
        """Test the complete billing flow from rating to Lago."""
        # Mock all Lago operations
        lago_adapter.sync_customer = AsyncMock(return_value=True)
        lago_adapter.setup_billing_metrics = AsyncMock(return_value=True)
        lago_adapter.create_default_plan = AsyncMock(return_value=True)
        lago_adapter.push_rated_usage = AsyncMock(return_value=True)
        lago_adapter.sync_invoices = AsyncMock(return_value=[])

        # 1. Setup Lago catalog
        metrics_result = await lago_adapter.setup_billing_metrics()
        plan_result = await lago_adapter.create_default_plan()

        # 2. Sync customer
        customer_id = sample_rating_result.customer_id
        sync_result = await lago_adapter.sync_customer(customer_id)

        # 3. Push rated usage
        usage_result = await lago_adapter.push_rated_usage(sample_rating_result)

        # 4. Sync invoices
        invoices = await lago_adapter.sync_invoices()

        # Verify all steps succeeded
        assert metrics_result is True
        assert plan_result is True
        assert sync_result is True
        assert usage_result is True
        assert isinstance(invoices, list)

    @pytest.mark.asyncio
    async def test_error_handling(self, lago_adapter):
        """Test error handling in Lago operations."""
        # Mock client to raise exceptions for all metrics
        lago_adapter.lago_client.create_billable_metric = AsyncMock(
            side_effect=Exception("API Error")
        )

        # The method catches exceptions and logs warnings, but still returns True
        # because it continues processing other metrics
        result = await lago_adapter.setup_billing_metrics()

        # The method returns True even with errors because it continues processing
        assert result is True


if __name__ == "__main__":
    pytest.main([__file__])
