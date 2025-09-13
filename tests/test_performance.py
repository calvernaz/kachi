"""Performance tests for the billing system."""

import asyncio
import os
import time
from datetime import datetime, timedelta
from uuid import uuid4

import psutil
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from kachi.apps.dashboard_api.main import app
from kachi.apps.deriver.processors import EdgeDeriver
from kachi.lib.db import get_session
from kachi.lib.models import Customer, Event, MeterReading, WorkflowDefinition


@pytest.fixture
async def performance_setup(db_session: AsyncSession):
    """Set up performance test data."""
    # Create customer
    customer = Customer(
        id=uuid4(),
        name="Performance Test Customer",
        lago_customer_id="perf_test_123",
        active=True,
    )
    db_session.add(customer)

    # Create workflow
    workflow = WorkflowDefinition(
        id=uuid4(),
        key="performance_workflow",
        version=1,
        definition_schema={
            "meters": {"api_calls": {"type": "edge", "aggregation": "sum"}}
        },
        active=True,
    )
    db_session.add(workflow)

    await db_session.commit()
    await db_session.refresh(customer)
    await db_session.refresh(workflow)

    return {"customer": customer, "workflow": workflow, "session": db_session}


class TestPerformance:
    """Performance tests for billing system components."""

    @pytest.mark.asyncio
    async def test_bulk_event_processing_performance(self, performance_setup):
        """Test performance of processing large numbers of events."""
        setup = performance_setup
        customer = setup["customer"]
        workflow = setup["workflow"]
        session = setup["session"]

        # Create a large number of events
        event_count = 1000
        base_time = datetime.utcnow()

        events = []
        for i in range(event_count):
            event = Event(
                id=uuid4(),
                customer_id=customer.id,
                workflow_id=workflow.id,
                event_name="bulk_test_event",
                timestamp=base_time + timedelta(seconds=i),
                attributes={"sequence": i, "value": 1},
                processed=False,
            )
            events.append(event)
            session.add(event)

        await session.commit()

        # Measure processing time
        start_time = time.time()

        edge_deriver = EdgeDeriver()
        for event in events:
            await edge_deriver.process_event(event, session)

        await session.commit()

        end_time = time.time()
        processing_time = end_time - start_time

        # Performance assertions
        events_per_second = event_count / processing_time

        # Should process at least 100 events per second
        assert events_per_second >= 100, (
            f"Processing rate too slow: {events_per_second:.2f} events/sec"
        )

        # Total processing time should be reasonable
        assert processing_time < 30, (
            f"Processing took too long: {processing_time:.2f} seconds"
        )

        print(
            f"Processed {event_count} events in {processing_time:.2f}s ({events_per_second:.2f} events/sec)"
        )

    @pytest.mark.asyncio
    async def test_concurrent_processing_performance(self, performance_setup):
        """Test performance of concurrent event processing."""
        setup = performance_setup
        customer = setup["customer"]
        workflow = setup["workflow"]
        session = setup["session"]

        # Create events for concurrent processing
        event_count = 500
        batch_size = 50
        base_time = datetime.utcnow()

        events = []
        for i in range(event_count):
            event = Event(
                id=uuid4(),
                customer_id=customer.id,
                workflow_id=workflow.id,
                event_name="concurrent_test_event",
                timestamp=base_time + timedelta(seconds=i),
                attributes={"sequence": i, "value": 1},
                processed=False,
            )
            events.append(event)
            session.add(event)

        await session.commit()

        # Measure concurrent processing time
        start_time = time.time()

        edge_deriver = EdgeDeriver()

        async def process_batch(event_batch):
            for event in event_batch:
                await edge_deriver.process_event(event, session)

        # Split into batches and process concurrently
        batches = [
            events[i : i + batch_size] for i in range(0, len(events), batch_size)
        ]

        # Process batches concurrently
        await asyncio.gather(*[process_batch(batch) for batch in batches])

        await session.commit()

        end_time = time.time()
        processing_time = end_time - start_time

        # Performance assertions
        events_per_second = event_count / processing_time

        # Concurrent processing should be faster
        assert events_per_second >= 200, (
            f"Concurrent processing rate too slow: {events_per_second:.2f} events/sec"
        )

        print(
            f"Concurrently processed {event_count} events in {processing_time:.2f}s ({events_per_second:.2f} events/sec)"
        )

    @pytest.mark.asyncio
    async def test_database_query_performance(self, performance_setup):
        """Test performance of database queries."""
        setup = performance_setup
        customer = setup["customer"]
        workflow = setup["workflow"]
        session = setup["session"]

        # Create meter readings for query testing
        reading_count = 1000
        base_time = datetime.utcnow().replace(minute=0, second=0, microsecond=0)

        readings = []
        for i in range(reading_count):
            reading = MeterReading(
                id=uuid4(),
                customer_id=customer.id,
                workflow_id=workflow.id,
                meter_name="api_calls",
                value=i + 1,
                window_start=base_time + timedelta(hours=i),
                window_end=base_time + timedelta(hours=i + 1),
                reading_type="edge",
            )
            readings.append(reading)
            session.add(reading)

        await session.commit()

        # Test query performance
        # Test 1: Simple customer query
        start_time = time.time()

        for _ in range(100):  # Run query 100 times
            result = await session.execute(
                select(MeterReading)
                .where(MeterReading.customer_id == customer.id)
                .limit(10)
            )
            result.scalars().all()

        simple_query_time = time.time() - start_time

        # Test 2: Aggregation query
        start_time = time.time()

        for _ in range(100):  # Run query 100 times
            result = await session.execute(
                select(func.sum(MeterReading.value)).where(
                    MeterReading.customer_id == customer.id,
                    MeterReading.window_start >= base_time,
                    MeterReading.window_start < base_time + timedelta(days=1),
                )
            )
            result.scalar()

        aggregation_query_time = time.time() - start_time

        # Test 3: Complex query with joins and filters
        start_time = time.time()

        for _ in range(50):  # Run query 50 times
            result = await session.execute(
                select(MeterReading, Customer)
                .join(Customer)
                .where(
                    Customer.active,
                    MeterReading.window_start >= base_time - timedelta(hours=24),
                    MeterReading.value > 100,
                )
                .order_by(MeterReading.window_start.desc())
                .limit(20)
            )
            result.all()

        complex_query_time = time.time() - start_time

        # Performance assertions
        assert simple_query_time < 5.0, (
            f"Simple queries too slow: {simple_query_time:.2f}s for 100 queries"
        )
        assert aggregation_query_time < 10.0, (
            f"Aggregation queries too slow: {aggregation_query_time:.2f}s for 100 queries"
        )
        assert complex_query_time < 15.0, (
            f"Complex queries too slow: {complex_query_time:.2f}s for 50 queries"
        )

        print("Query performance:")
        print(
            f"  Simple queries: {simple_query_time:.2f}s for 100 queries ({100 / simple_query_time:.1f} queries/sec)"
        )
        print(
            f"  Aggregation queries: {aggregation_query_time:.2f}s for 100 queries ({100 / aggregation_query_time:.1f} queries/sec)"
        )
        print(
            f"  Complex queries: {complex_query_time:.2f}s for 50 queries ({50 / complex_query_time:.1f} queries/sec)"
        )

    @pytest.mark.asyncio
    async def test_memory_usage_during_bulk_operations(self, performance_setup):
        """Test memory usage during bulk operations."""

        setup = performance_setup
        customer = setup["customer"]
        workflow = setup["workflow"]
        session = setup["session"]

        # Get initial memory usage
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB

        # Create a large number of events in batches to test memory efficiency
        total_events = 5000
        batch_size = 100

        edge_deriver = EdgeDeriver()
        base_time = datetime.utcnow()

        for batch_num in range(0, total_events, batch_size):
            # Create batch of events
            events = []
            for i in range(batch_size):
                event = Event(
                    id=uuid4(),
                    customer_id=customer.id,
                    workflow_id=workflow.id,
                    event_name="memory_test_event",
                    timestamp=base_time + timedelta(seconds=batch_num + i),
                    attributes={"batch": batch_num, "sequence": i},
                    processed=False,
                )
                events.append(event)
                session.add(event)

            await session.commit()

            # Process events
            for event in events:
                await edge_deriver.process_event(event, session)

            await session.commit()

            # Clear session to free memory
            session.expunge_all()

        # Get final memory usage
        final_memory = process.memory_info().rss / 1024 / 1024  # MB
        memory_increase = final_memory - initial_memory

        # Memory usage should not grow excessively
        assert memory_increase < 500, (
            f"Memory usage increased too much: {memory_increase:.2f} MB"
        )

        print(
            f"Memory usage: {initial_memory:.2f} MB -> {final_memory:.2f} MB (increase: {memory_increase:.2f} MB)"
        )

    @pytest.mark.asyncio
    async def test_api_response_time_performance(self, performance_setup):
        """Test API response time performance."""

        setup = performance_setup
        customer = setup["customer"]
        session = setup["session"]

        # Override database session
        async def get_test_session():
            yield session

        app.dependency_overrides[get_session] = get_test_session
        client = TestClient(app)

        # Create some test data
        base_time = datetime.utcnow().replace(minute=0, second=0, microsecond=0)
        for i in range(100):
            reading = MeterReading(
                id=uuid4(),
                customer_id=customer.id,
                workflow_id=setup["workflow"].id,
                meter_name="api_calls",
                value=i + 1,
                window_start=base_time + timedelta(hours=i),
                window_end=base_time + timedelta(hours=i + 1),
                reading_type="edge",
            )
            session.add(reading)

        await session.commit()

        # Test API response times
        endpoints = [
            "/health",
            "/v1/customers",
            f"/v1/customers/{customer.id}/usage/summary",
            f"/v1/customers/{customer.id}/meters/api_calls",
        ]

        for endpoint in endpoints:
            response_times = []

            # Make 10 requests to each endpoint
            for _ in range(10):
                start_time = time.time()
                response = client.get(endpoint)
                end_time = time.time()

                assert response.status_code == 200
                response_times.append(end_time - start_time)

            avg_response_time = sum(response_times) / len(response_times)
            max_response_time = max(response_times)

            # API responses should be fast
            assert avg_response_time < 1.0, (
                f"{endpoint} average response time too slow: {avg_response_time:.3f}s"
            )
            assert max_response_time < 2.0, (
                f"{endpoint} max response time too slow: {max_response_time:.3f}s"
            )

            print(
                f"{endpoint}: avg {avg_response_time:.3f}s, max {max_response_time:.3f}s"
            )
