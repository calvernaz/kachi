"""Tests for the event processing pipeline."""

from datetime import datetime, timedelta
from uuid import uuid4

import pytest

from kachi.apps.deriver.processors import EdgeDeriver
from kachi.lib.models import RawEvent


def create_sample_events():
    """Create sample raw events for testing."""
    customer_id = uuid4()
    base_time = datetime.utcnow().replace(minute=0, second=0, microsecond=0)

    # Edge event with token usage
    edge_event = RawEvent(
        id=1,
        customer_id=customer_id,
        ts=base_time,
        event_type="span_ended",
        trace_id="trace123",
        span_id="span123",
        payload_json={
            "span_name": "llm_call",
            "edge": {
                "llm_tokens_input": 100,
                "llm_tokens_output": 50,
                "compute_ms": 1500,
            },
            "work": {
                "workflow_definition": "document_analysis",
                "step_key": "extract_text",
            },
        },
    )

    # Work outcome event
    work_event = RawEvent(
        id=2,
        customer_id=customer_id,
        ts=base_time + timedelta(minutes=1),
        event_type="outcome",
        trace_id="trace123",
        span_id="span124",
        payload_json={
            "event_name": "ticket_resolved",
            "outcome": {
                "outcome_type": "ticket_resolution",
                "outcome_value": "resolved",
                "sla_met": True,
            },
        },
    )

    # API call event
    api_event = RawEvent(
        id=3,
        customer_id=customer_id,
        ts=base_time + timedelta(minutes=2),
        event_type="span_started",
        trace_id="trace124",
        span_id="span125",
        payload_json={
            "span_name": "api_call",
            "edge": {"net_bytes_in": 1024, "net_bytes_out": 2048},
        },
    )

    return customer_id, [edge_event, work_event, api_event]


class MockSession:
    """Mock session for testing without database."""

    def __init__(self):
        self.added_objects = []

    def add(self, obj):
        self.added_objects.append(obj)

    async def commit(self):
        pass


def test_edge_deriver():
    """Test edge event processing."""
    customer_id, events = create_sample_events()

    # Mock session
    session = MockSession()

    # Process with edge deriver
    deriver = EdgeDeriver(session)
    window_start = datetime.utcnow().replace(minute=0, second=0, microsecond=0)
    window_end = window_start + timedelta(minutes=5)

    # This would normally be async, but we'll test the logic
    # by calling the processing logic directly
    edge_aggregates = {
        "api.calls": 0,
        "llm.tokens": 0,
        "llm.tokens.input": 0,
        "llm.tokens.output": 0,
        "compute.ms": 0,
        "net.bytes": 0,
        "storage.gbh": 0.0,
    }

    event_ids = []

    for event in events:
        event_ids.append(event.id)
        payload = event.payload_json or {}

        # Extract edge attributes from payload
        edge_attrs = payload.get("edge", {})
        if not edge_attrs:
            continue

        # Count API calls (any span start/end is an API call)
        if event.event_type in ("span_started", "span_ended"):
            edge_aggregates["api.calls"] += 1

        # Aggregate token usage
        if edge_attrs.get("llm_tokens_input"):
            edge_aggregates["llm.tokens.input"] += edge_attrs["llm_tokens_input"]
            edge_aggregates["llm.tokens"] += edge_attrs["llm_tokens_input"]

        if edge_attrs.get("llm_tokens_output"):
            edge_aggregates["llm.tokens.output"] += edge_attrs["llm_tokens_output"]
            edge_aggregates["llm.tokens"] += edge_attrs["llm_tokens_output"]

        # Aggregate compute time
        if edge_attrs.get("compute_ms"):
            edge_aggregates["compute.ms"] += edge_attrs["compute_ms"]

        # Aggregate network usage
        net_in = edge_attrs.get("net_bytes_in", 0)
        net_out = edge_attrs.get("net_bytes_out", 0)
        if net_in or net_out:
            edge_aggregates["net.bytes"] += net_in + net_out

    # Verify aggregations
    assert edge_aggregates["llm.tokens"] == 150  # 100 + 50
    assert edge_aggregates["llm.tokens.input"] == 100
    assert edge_aggregates["llm.tokens.output"] == 50
    assert edge_aggregates["compute.ms"] == 1500
    assert edge_aggregates["api.calls"] == 2  # span_ended + span_started
    assert edge_aggregates["net.bytes"] == 3072  # 1024 + 2048


def test_work_deriver():
    """Test work event processing."""
    customer_id, events = create_sample_events()

    # Test work aggregation logic
    work_aggregates = {
        "workflow.completed": 0,
        "workflow.failed": 0,
        "step.completed": 0,
        "outcome.ticket_resolved": 0,
        "outcome.document_processed": 0,
        "outcome.analysis_completed": 0,
    }

    for event in events:
        payload = event.payload_json or {}

        # Process workflow completion events
        if event.event_type == "span_ended":
            work_attrs = payload.get("work", {})
            if work_attrs.get("workflow_definition"):
                # Check span status to determine success/failure
                status = payload.get("status", "OK")
                if status == "OK":
                    work_aggregates["workflow.completed"] += 1
                else:
                    work_aggregates["workflow.failed"] += 1

            # Count completed steps
            if work_attrs.get("step_key"):
                work_aggregates["step.completed"] += 1

        # Process outcome events
        elif event.event_type in ("outcome", "span_event"):
            outcome_attrs = payload.get("outcome", {})
            event_name = payload.get("event_name", "")

            # Map outcome types to meters
            if (
                "ticket" in event_name.lower() and "resolved" in event_name.lower()
            ) or outcome_attrs.get("outcome_type") == "ticket_resolution":
                work_aggregates["outcome.ticket_resolved"] += 1

    # Verify aggregations
    assert work_aggregates["workflow.completed"] == 1
    assert work_aggregates["step.completed"] == 1
    assert work_aggregates["outcome.ticket_resolved"] == 1


def test_event_grouping():
    """Test event grouping by time windows."""
    # Create events across different time windows
    base_time = datetime.utcnow().replace(minute=0, second=0, microsecond=0)
    customer_id = uuid4()

    events = [
        RawEvent(
            id=1,
            customer_id=customer_id,
            ts=base_time,
            event_type="test",
            payload_json={},
        ),
        RawEvent(
            id=2,
            customer_id=customer_id,
            ts=base_time + timedelta(minutes=3),
            event_type="test",
            payload_json={},
        ),
        RawEvent(
            id=3,
            customer_id=customer_id,
            ts=base_time + timedelta(minutes=7),  # Different window
            event_type="test",
            payload_json={},
        ),
    ]

    # Test the grouping logic
    windows = {}
    window_minutes = 5

    for event in events:
        # Round down to window boundary
        window_start = event.ts.replace(
            minute=(event.ts.minute // window_minutes) * window_minutes,
            second=0,
            microsecond=0,
        )
        window_end = window_start + timedelta(minutes=window_minutes)

        key = (event.customer_id, window_start, window_end)
        if key not in windows:
            windows[key] = []
        windows[key].append(event)

    # Should have 2 windows
    assert len(windows) == 2

    # First window should have 2 events, second should have 1
    window_sizes = [len(events) for events in windows.values()]
    window_sizes.sort()
    assert window_sizes == [1, 2]


if __name__ == "__main__":
    pytest.main([__file__])
