"""Integration tests for the complete billing pipeline."""

import asyncio
from datetime import datetime, timedelta
from uuid import uuid4

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from kachi.apps.deriver.processors import EdgeDeriver, WorkDeriver
from kachi.apps.rater.main import RatingEngine
from kachi.lib.models import (
    BillingAdjustment,
    Customer,
    Event,
    MeterReading,
    WorkflowDefinition,
)


@pytest.fixture
async def integration_setup(db_session: AsyncSession):
    """Set up integration test data."""
    # Create customer
    customer = Customer(
        id=uuid4(),
        name="Integration Test Customer",
        lago_customer_id="integration_test_123",
        active=True,
    )
    db_session.add(customer)

    # Create workflow
    workflow = WorkflowDefinition(
        id=uuid4(),
        key="integration_workflow",
        version=1,
        definition_schema={
            "meters": {
                "api_calls": {"type": "edge", "aggregation": "sum"},
                "processing_time": {"type": "work", "aggregation": "sum"},
            }
        },
        active=True,
    )
    db_session.add(workflow)

    await db_session.commit()
    await db_session.refresh(customer)
    await db_session.refresh(workflow)

    return {"customer": customer, "workflow": workflow, "session": db_session}


class TestBillingPipelineIntegration:
    """Integration tests for the complete billing pipeline."""

    @pytest.mark.asyncio
    async def test_end_to_end_billing_flow(self, integration_setup):
        """Test complete end-to-end billing flow."""
        setup = integration_setup
        customer = setup["customer"]
        workflow = setup["workflow"]
        session = setup["session"]

        # Step 1: Create raw events
        base_time = datetime.utcnow().replace(minute=0, second=0, microsecond=0)

        events = []
        for i in range(10):
            event = Event(
                id=uuid4(),
                customer_id=customer.id,
                workflow_id=workflow.id,
                event_name="api_call",
                timestamp=base_time + timedelta(minutes=i * 5),
                attributes={
                    "endpoint": "/api/v1/test",
                    "method": "GET",
                    "response_time": 150 + i * 10,
                    "status_code": 200,
                },
                processed=False,
            )
            events.append(event)
            session.add(event)

        await session.commit()

        # Step 2: Process events through derivers
        edge_deriver = EdgeDeriver()
        work_deriver = WorkDeriver()

        # Process edge events (API calls)
        for event in events:
            await edge_deriver.process_event(event, session)

        # Process work events (processing time)
        for event in events:
            await work_deriver.process_event(event, session)

        await session.commit()

        # Step 3: Verify meter readings were created
        edge_readings = await session.execute(
            select(MeterReading).where(
                MeterReading.customer_id == customer.id,
                MeterReading.reading_type == "edge",
            )
        )
        edge_readings = edge_readings.scalars().all()
        assert len(edge_readings) > 0

        work_readings = await session.execute(
            select(MeterReading).where(
                MeterReading.customer_id == customer.id,
                MeterReading.reading_type == "work",
            )
        )
        work_readings = work_readings.scalars().all()
        assert len(work_readings) > 0

        # Step 4: Test rating engine
        rating_engine = RatingEngine()

        # Calculate costs for the meter readings
        total_cost = 0
        for reading in edge_readings + work_readings:
            cost = await rating_engine.calculate_cost(reading, session)
            total_cost += cost

        assert total_cost > 0

        # Step 5: Test billing adjustments
        adjustment = BillingAdjustment(
            id=uuid4(),
            customer_id=customer.id,
            amount=-10.0,  # $10 credit
            reason="Integration test credit",
            actor="test_system",
            applied=False,
        )
        session.add(adjustment)
        await session.commit()

        # Verify adjustment was created
        adjustments = await session.execute(
            select(BillingAdjustment).where(
                BillingAdjustment.customer_id == customer.id
            )
        )
        adjustments = adjustments.scalars().all()
        assert len(adjustments) == 1
        assert adjustments[0].amount == -10.0

    @pytest.mark.asyncio
    async def test_concurrent_event_processing(self, integration_setup):
        """Test concurrent processing of events."""
        setup = integration_setup
        customer = setup["customer"]
        workflow = setup["workflow"]
        session = setup["session"]

        # Create multiple events simultaneously
        base_time = datetime.utcnow()
        events = []

        for i in range(50):
            event = Event(
                id=uuid4(),
                customer_id=customer.id,
                workflow_id=workflow.id,
                event_name=f"concurrent_event_{i}",
                timestamp=base_time + timedelta(seconds=i),
                attributes={"batch_id": "concurrent_test", "sequence": i},
                processed=False,
            )
            events.append(event)
            session.add(event)

        await session.commit()

        # Process events concurrently
        edge_deriver = EdgeDeriver()

        async def process_event_batch(event_batch):
            for event in event_batch:
                await edge_deriver.process_event(event, session)

        # Split events into batches for concurrent processing
        batch_size = 10
        batches = [
            events[i : i + batch_size] for i in range(0, len(events), batch_size)
        ]

        # Process batches concurrently
        tasks = [process_event_batch(batch) for batch in batches]
        await asyncio.gather(*tasks)

        await session.commit()

        # Verify all events were processed
        processed_events = await session.execute(
            select(Event).where(Event.customer_id == customer.id, Event.processed)
        )
        processed_events = processed_events.scalars().all()

        # All events should be marked as processed
        assert len(processed_events) == len(events)

    @pytest.mark.asyncio
    async def test_data_consistency_across_components(self, integration_setup):
        """Test data consistency across different components."""
        setup = integration_setup
        customer = setup["customer"]
        workflow = setup["workflow"]
        session = setup["session"]

        # Create events with specific patterns
        base_time = datetime.utcnow().replace(minute=0, second=0, microsecond=0)

        # Create hourly events for 24 hours
        events = []
        for hour in range(24):
            for minute in [0, 30]:  # Two events per hour
                event = Event(
                    id=uuid4(),
                    customer_id=customer.id,
                    workflow_id=workflow.id,
                    event_name="hourly_api_call",
                    timestamp=base_time + timedelta(hours=hour, minutes=minute),
                    attributes={"hour": hour, "minute": minute, "value": 1},
                    processed=False,
                )
                events.append(event)
                session.add(event)

        await session.commit()

        # Process all events
        edge_deriver = EdgeDeriver()
        for event in events:
            await edge_deriver.process_event(event, session)

        await session.commit()

        # Verify data consistency
        # Check that meter readings aggregate correctly
        total_readings = await session.execute(
            select(func.sum(MeterReading.value)).where(
                MeterReading.customer_id == customer.id,
                MeterReading.reading_type == "edge",
            )
        )
        total_value = total_readings.scalar()

        # Should have 48 events (24 hours * 2 events per hour)
        assert total_value == 48

        # Check hourly aggregation
        hourly_readings = await session.execute(
            select(MeterReading)
            .where(
                MeterReading.customer_id == customer.id,
                MeterReading.reading_type == "edge",
            )
            .order_by(MeterReading.window_start)
        )
        hourly_readings = hourly_readings.scalars().all()

        # Each hour should have 2 events aggregated
        for reading in hourly_readings:
            if reading.value > 0:  # Skip empty windows
                assert reading.value == 2

    @pytest.mark.asyncio
    async def test_error_handling_and_recovery(self, integration_setup):
        """Test error handling and recovery mechanisms."""
        setup = integration_setup
        customer = setup["customer"]
        workflow = setup["workflow"]
        session = setup["session"]

        # Create events with some invalid data
        base_time = datetime.utcnow()

        valid_events = []
        invalid_events = []

        for i in range(10):
            if i % 3 == 0:  # Every third event is invalid
                event = Event(
                    id=uuid4(),
                    customer_id=customer.id,
                    workflow_id=workflow.id,
                    event_name="invalid_event",
                    timestamp=base_time + timedelta(minutes=i),
                    attributes={},  # Missing required attributes
                    processed=False,
                )
                invalid_events.append(event)
            else:
                event = Event(
                    id=uuid4(),
                    customer_id=customer.id,
                    workflow_id=workflow.id,
                    event_name="valid_event",
                    timestamp=base_time + timedelta(minutes=i),
                    attributes={"value": 1, "type": "test"},
                    processed=False,
                )
                valid_events.append(event)

            session.add(event)

        await session.commit()

        # Process events with error handling
        edge_deriver = EdgeDeriver()
        processed_count = 0
        error_count = 0

        for event in valid_events + invalid_events:
            try:
                await edge_deriver.process_event(event, session)
                processed_count += 1
            except Exception:
                error_count += 1
                # In real implementation, we'd log the error and continue
                continue

        await session.commit()

        # Verify that valid events were processed despite errors
        assert processed_count > 0
        assert error_count > 0

        # Valid events should create meter readings
        readings = await session.execute(
            select(MeterReading).where(MeterReading.customer_id == customer.id)
        )
        readings = readings.scalars().all()

        # Should have readings from valid events only
        assert len(readings) > 0
