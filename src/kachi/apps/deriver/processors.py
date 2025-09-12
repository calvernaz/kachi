"""Event processors for deriving meter readings from raw events."""

from datetime import datetime, timedelta
from decimal import Decimal
from typing import Any
from uuid import UUID

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from kachi.lib.models import MeterReading, RawEvent

logger = structlog.get_logger()


class EdgeDeriver:
    """Derives edge-based meter readings from raw events."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def process_window(
        self,
        customer_id: UUID,
        window_start: datetime,
        window_end: datetime,
        events: list[RawEvent],
    ) -> int:
        """Process events in a time window to create edge meter readings."""
        readings_created = 0

        # Aggregate edge metrics by meter type
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

            if edge_attrs.get("llm_tokens"):
                edge_aggregates["llm.tokens"] += edge_attrs["llm_tokens"]

            # Aggregate compute time
            if edge_attrs.get("compute_ms"):
                edge_aggregates["compute.ms"] += edge_attrs["compute_ms"]

            # Aggregate network usage
            net_in = edge_attrs.get("net_bytes_in", 0)
            net_out = edge_attrs.get("net_bytes_out", 0)
            if net_in or net_out:
                edge_aggregates["net.bytes"] += net_in + net_out

            # Aggregate storage
            if edge_attrs.get("storage_gb_hours"):
                edge_aggregates["storage.gbh"] += edge_attrs["storage_gb_hours"]

        # Create meter readings for non-zero aggregates
        for meter_key, value in edge_aggregates.items():
            if value > 0:
                reading = MeterReading(
                    customer_id=customer_id,
                    meter_key=meter_key,
                    window_start=window_start,
                    window_end=window_end,
                    value=Decimal(str(value)),
                    src_event_ids=event_ids,
                )
                self.session.add(reading)
                readings_created += 1

        return readings_created


class WorkDeriver:
    """Derives work-based meter readings from raw events."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def process_window(
        self,
        customer_id: UUID,
        window_start: datetime,
        window_end: datetime,
        events: list[RawEvent],
    ) -> int:
        """Process events in a time window to create work meter readings."""
        readings_created = 0

        # Track work metrics
        work_aggregates = {
            "workflow.completed": 0,
            "workflow.failed": 0,
            "step.completed": 0,
            "outcome.ticket_resolved": 0,
            "outcome.document_processed": 0,
            "outcome.analysis_completed": 0,
        }

        event_ids = []

        for event in events:
            event_ids.append(event.id)
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
                if "ticket" in event_name.lower() and "resolved" in event_name.lower():
                    work_aggregates["outcome.ticket_resolved"] += 1
                elif (
                    "document" in event_name.lower()
                    and "processed" in event_name.lower()
                ):
                    work_aggregates["outcome.document_processed"] += 1
                elif (
                    "analysis" in event_name.lower()
                    and "completed" in event_name.lower()
                ):
                    work_aggregates["outcome.analysis_completed"] += 1
                elif outcome_attrs.get("outcome_type") == "ticket_resolution":
                    work_aggregates["outcome.ticket_resolved"] += 1
                elif outcome_attrs.get("outcome_type") == "document_processing":
                    work_aggregates["outcome.document_processed"] += 1
                elif outcome_attrs.get("outcome_type") == "analysis_completion":
                    work_aggregates["outcome.analysis_completed"] += 1

        # Create meter readings for non-zero aggregates
        for meter_key, value in work_aggregates.items():
            if value > 0:
                reading = MeterReading(
                    customer_id=customer_id,
                    meter_key=meter_key,
                    window_start=window_start,
                    window_end=window_end,
                    value=Decimal(str(value)),
                    src_event_ids=event_ids,
                )
                self.session.add(reading)
                readings_created += 1

        return readings_created


class AnomalyDetector:
    """Detects anomalies in meter readings for alerting."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def detect_usage_spikes(
        self, customer_id: UUID, meter_key: str, threshold_multiplier: float = 3.0
    ) -> list[dict[str, Any]]:
        """Detect usage spikes compared to historical average."""
        from sqlalchemy import select

        # Get recent readings for baseline
        recent_query = (
            select(MeterReading)
            .where(
                MeterReading.customer_id == customer_id,
                MeterReading.meter_key == meter_key,
                MeterReading.window_start >= datetime.utcnow() - timedelta(days=30),
            )
            .order_by(MeterReading.window_start.desc())
            .limit(100)
        )

        result = await self.session.execute(recent_query)
        readings = result.scalars().all()

        if len(readings) < 10:  # Need enough data for baseline
            return []

        # Calculate baseline average (excluding most recent reading)
        baseline_values = [float(r.value) for r in readings[1:]]
        baseline_avg = sum(baseline_values) / len(baseline_values)

        # Check if most recent reading is a spike
        latest_value = float(readings[0].value)
        if latest_value > baseline_avg * threshold_multiplier:
            return [
                {
                    "customer_id": str(customer_id),
                    "meter_key": meter_key,
                    "latest_value": latest_value,
                    "baseline_avg": baseline_avg,
                    "spike_ratio": latest_value / baseline_avg,
                    "window_start": readings[0].window_start.isoformat(),
                    "window_end": readings[0].window_end.isoformat(),
                }
            ]

        return []

    async def detect_zero_usage(
        self, customer_id: UUID, hours_threshold: int = 24
    ) -> list[dict[str, Any]]:
        """Detect customers with zero usage for extended periods."""
        from datetime import timedelta

        from sqlalchemy import func, select

        cutoff_time = datetime.utcnow() - timedelta(hours=hours_threshold)

        # Check if customer has any recent readings
        query = select(func.count(MeterReading.id)).where(
            MeterReading.customer_id == customer_id,
            MeterReading.window_start >= cutoff_time,
        )

        result = await self.session.execute(query)
        count = result.scalar()

        if count == 0:
            return [
                {
                    "customer_id": str(customer_id),
                    "issue": "zero_usage",
                    "hours_without_usage": hours_threshold,
                    "last_check": datetime.utcnow().isoformat(),
                }
            ]

        return []
