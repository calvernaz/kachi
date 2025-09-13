"""Tests for COGS calculation pipeline."""

from datetime import datetime, timedelta
from decimal import Decimal

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from kachi.lib.cogs_calculator import COGSCalculator, COGSTracker
from kachi.lib.models import (
    Customer,
    MeterReading,
    WorkflowDefinition,
    WorkflowRun,
)


@pytest.fixture
async def sample_data(db_session: AsyncSession):
    """Create sample data for COGS testing."""
    # Create customer
    customer = Customer(
        lago_customer_id="test-customer-001",
        name="Test Customer",
        currency="USD",
    )
    db_session.add(customer)
    await db_session.commit()
    await db_session.refresh(customer)

    # Create workflow definition
    workflow_def = WorkflowDefinition(
        key="test-workflow",
        version=1,
        definition_schema={"steps": ["validate", "process", "complete"]},
    )
    db_session.add(workflow_def)
    await db_session.commit()
    await db_session.refresh(workflow_def)

    # Create workflow runs
    now = datetime.utcnow()
    runs = []
    for i in range(3):
        run = WorkflowRun(
            customer_id=customer.id,
            definition_id=workflow_def.id,
            started_at=now - timedelta(hours=i),
            ended_at=now - timedelta(hours=i) + timedelta(minutes=30),
            status="completed",
            metadata_json={"test": True},
        )
        db_session.add(run)
        runs.append(run)

    await db_session.commit()
    for run in runs:
        await db_session.refresh(run)

    return {
        "customer": customer,
        "workflow_def": workflow_def,
        "runs": runs,
    }


class TestCOGSTracker:
    """Test COGS tracking functionality."""

    async def test_record_llm_cost(self, db_session: AsyncSession, sample_data):
        """Test recording LLM costs."""
        tracker = COGSTracker(db_session)
        run = sample_data["runs"][0]

        cost_record = await tracker.record_llm_cost(
            workflow_run_id=run.id,
            input_tokens=1000,
            output_tokens=500,
            model="gpt-4",
            cost_per_input_token=Decimal("0.00003"),
            cost_per_output_token=Decimal("0.00006"),
        )

        assert cost_record.cost_type == "tokens"
        assert cost_record.cost_amount == Decimal(
            "0.06"
        )  # (1000 * 0.00003) + (500 * 0.00006)
        assert cost_record.details_json["model"] == "gpt-4"
        assert cost_record.details_json["input_tokens"] == 1000
        assert cost_record.details_json["output_tokens"] == 500

    async def test_record_compute_cost(self, db_session: AsyncSession, sample_data):
        """Test recording compute costs."""
        tracker = COGSTracker(db_session)
        run = sample_data["runs"][0]

        cost_record = await tracker.record_compute_cost(
            workflow_run_id=run.id,
            duration_ms=30000,  # 30 seconds
            cpu_cores=2.0,
            memory_gb=4.0,
            cost_per_core_hour=Decimal("0.10"),
            cost_per_gb_hour=Decimal("0.02"),
        )

        assert cost_record.cost_type == "compute"
        # 30 seconds = 0.00833 hours
        # CPU: 2.0 * 0.00833 * 0.10 = 0.001666
        # Memory: 4.0 * 0.00833 * 0.02 = 0.000666
        # Total: ~0.002332
        assert cost_record.cost_amount > Decimal("0.002")
        assert cost_record.cost_amount < Decimal("0.003")

    async def test_record_api_cost(self, db_session: AsyncSession, sample_data):
        """Test recording API costs."""
        tracker = COGSTracker(db_session)
        run = sample_data["runs"][0]

        cost_record = await tracker.record_api_cost(
            workflow_run_id=run.id,
            api_calls=10,
            service_name="external-api",
            cost_per_call=Decimal("0.001"),
        )

        assert cost_record.cost_type == "api"
        assert cost_record.cost_amount == Decimal("0.01")
        assert cost_record.details_json["service_name"] == "external-api"
        assert cost_record.details_json["api_calls"] == 10


class TestCOGSCalculator:
    """Test COGS calculation functionality."""

    async def test_calculate_period_cogs(self, db_session: AsyncSession, sample_data):
        """Test calculating total COGS for a period."""
        # Add some cost records
        tracker = COGSTracker(db_session)
        runs = sample_data["runs"]

        # Add costs to different runs
        await tracker.record_llm_cost(
            runs[0].id, 1000, 500, "gpt-4", Decimal("0.00003"), Decimal("0.00006")
        )
        await tracker.record_compute_cost(
            runs[1].id, 60000, 1.0, 2.0, Decimal("0.10"), Decimal("0.02")
        )
        await tracker.record_api_cost(runs[2].id, 5, "test-api", Decimal("0.002"))

        calculator = COGSCalculator(db_session)
        customer = sample_data["customer"]

        period_start = datetime.utcnow() - timedelta(hours=4)
        period_end = datetime.utcnow()

        cogs_data = await calculator.calculate_period_cogs(
            customer.id, period_start, period_end
        )

        assert cogs_data["total_cogs"] > Decimal("0")
        assert "tokens" in cogs_data["cogs_by_type"]
        assert "compute" in cogs_data["cogs_by_type"]
        assert "api" in cogs_data["cogs_by_type"]
        assert cogs_data["cost_records_count"] == 3

    async def test_calculate_meter_cogs(self, db_session: AsyncSession, sample_data):
        """Test calculating COGS for specific meters."""
        # Add cost records and meter readings
        tracker = COGSTracker(db_session)
        customer = sample_data["customer"]
        run = sample_data["runs"][0]

        # Add LLM cost
        await tracker.record_llm_cost(
            run.id, 1000, 500, "gpt-4", Decimal("0.00003"), Decimal("0.00006")
        )

        # Add meter reading for LLM tokens
        meter_reading = MeterReading(
            customer_id=customer.id,
            meter_key="llm.tokens",
            window_start=datetime.utcnow() - timedelta(hours=1),
            window_end=datetime.utcnow(),
            value=Decimal("1500"),  # 1000 input + 500 output
            src_event_ids=[],
        )
        db_session.add(meter_reading)
        await db_session.commit()

        calculator = COGSCalculator(db_session)
        period_start = datetime.utcnow() - timedelta(hours=2)
        period_end = datetime.utcnow()

        meter_cogs = await calculator.calculate_meter_cogs(
            customer.id, "llm.tokens", period_start, period_end
        )

        assert meter_cogs["meter_key"] == "llm.tokens"
        assert meter_cogs["total_usage"] == Decimal("1500")
        assert meter_cogs["attributed_cogs"] > Decimal("0")
        assert meter_cogs["cost_per_unit"] > Decimal("0")

    async def test_calculate_margin_analysis(
        self, db_session: AsyncSession, sample_data
    ):
        """Test comprehensive margin analysis."""
        # Setup cost data
        tracker = COGSTracker(db_session)
        customer = sample_data["customer"]
        run = sample_data["runs"][0]

        await tracker.record_llm_cost(
            run.id, 1000, 500, "gpt-4", Decimal("0.00003"), Decimal("0.00006")
        )

        calculator = COGSCalculator(db_session)
        period_start = datetime.utcnow() - timedelta(hours=2)
        period_end = datetime.utcnow()

        # Mock revenue lines
        revenue_lines = [
            {
                "meter_key": "llm.tokens",
                "amount": Decimal("1.00"),
                "line_type": "usage",
                "usage_quantity": Decimal("1500"),
            },
            {
                "meter_key": "api.calls",
                "amount": Decimal("0.50"),
                "line_type": "usage",
                "usage_quantity": Decimal("100"),
            },
        ]

        margin_analysis = await calculator.calculate_margin_analysis(
            customer.id, period_start, period_end, revenue_lines
        )

        assert "total_revenue" in margin_analysis
        assert "total_cogs" in margin_analysis
        assert "gross_margin" in margin_analysis
        assert "margin_percentage" in margin_analysis
        assert "meter_margins" in margin_analysis
        assert "profitability_score" in margin_analysis

        # Check that revenue is calculated correctly
        assert margin_analysis["total_revenue"] == Decimal("1.50")

    async def test_profitability_score(self, db_session: AsyncSession):
        """Test profitability score calculation."""
        calculator = COGSCalculator(db_session)

        # Test different margin scenarios
        assert (
            calculator._calculate_profitability_score(Decimal("60"), Decimal("100"))
            == "excellent"
        )
        assert (
            calculator._calculate_profitability_score(Decimal("40"), Decimal("100"))
            == "good"
        )
        assert (
            calculator._calculate_profitability_score(Decimal("20"), Decimal("100"))
            == "fair"
        )
        assert (
            calculator._calculate_profitability_score(Decimal("5"), Decimal("100"))
            == "poor"
        )
        assert (
            calculator._calculate_profitability_score(Decimal("-10"), Decimal("100"))
            == "loss"
        )
