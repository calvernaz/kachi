"""Event processing logic for OpenTelemetry data."""

from datetime import datetime
from typing import Any
from uuid import UUID

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from kachi.lib.models import AuditLog, Customer, RawEvent
from kachi.lib.otel_schemas import (
    BillingAttributes,
    EdgeAttributes,
    OTelExportRequest,
    OutcomeAttributes,
    OutcomeEventRequest,
    UsagePreviewResponse,
    WorkAttributes,
)

logger = structlog.get_logger()


class EventProcessor:
    """Processes OpenTelemetry events and stores them as raw events."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def process_otel_export(self, request: OTelExportRequest) -> dict[str, Any]:
        """Process an OpenTelemetry export request."""
        spans_processed = 0
        events_processed = 0
        errors = []

        # Process resource spans
        for resource_span in request.resource_spans:
            try:
                resource_attrs = resource_span.get("resource", {}).get("attributes", {})
                scope_spans = resource_span.get("scope_spans", [])

                for scope_span in scope_spans:
                    spans = scope_span.get("spans", [])
                    for span_data in spans:
                        try:
                            await self._process_span(span_data, resource_attrs)
                            spans_processed += 1
                        except Exception as e:
                            errors.append(f"Failed to process span: {e!s}")
                            logger.error("Span processing error", error=str(e))

                        # Process span events
                        span_events = span_data.get("events", [])
                        for event_data in span_events:
                            try:
                                await self._process_span_event(
                                    event_data, span_data, resource_attrs
                                )
                                events_processed += 1
                            except Exception as e:
                                errors.append(f"Failed to process span event: {e!s}")
                                logger.error(
                                    "Span event processing error", error=str(e)
                                )

            except Exception as e:
                errors.append(f"Failed to process resource span: {e!s}")
                logger.error("Resource span processing error", error=str(e))

        await self.session.commit()

        return {
            "spans_processed": spans_processed,
            "events_processed": events_processed,
            "errors": errors,
        }

    async def _process_span(
        self, span_data: dict[str, Any], resource_attrs: dict[str, Any]
    ) -> None:
        """Process a single span."""
        # Extract billing attributes
        all_attrs = {**resource_attrs, **span_data.get("attributes", {})}
        billing_attrs = self._extract_billing_attributes(all_attrs)

        if not billing_attrs or not billing_attrs.customer_id:
            raise ValueError("Missing required billing.customer_id attribute")

        # Verify customer exists
        await self._verify_customer_exists(billing_attrs.customer_id)

        # Create span start event
        start_event = RawEvent(
            customer_id=billing_attrs.customer_id,
            ts=self._parse_timestamp(span_data.get("start_time_unix_nano")),
            event_type="span_started",
            trace_id=span_data.get("trace_id"),
            span_id=span_data.get("span_id"),
            payload_json={
                "span_name": span_data.get("name"),
                "parent_span_id": span_data.get("parent_span_id"),
                "attributes": all_attrs,
                "billing": billing_attrs.model_dump() if billing_attrs else None,
                "edge": self._extract_edge_attributes(all_attrs).model_dump(),
                "work": self._extract_work_attributes(all_attrs).model_dump(),
            },
        )
        self.session.add(start_event)

        # Create span end event if span is completed
        if span_data.get("end_time_unix_nano"):
            end_event = RawEvent(
                customer_id=billing_attrs.customer_id,
                ts=self._parse_timestamp(span_data.get("end_time_unix_nano")),
                event_type="span_ended",
                trace_id=span_data.get("trace_id"),
                span_id=span_data.get("span_id"),
                payload_json={
                    "span_name": span_data.get("name"),
                    "status": span_data.get("status", {}).get("code", "OK"),
                    "duration_ns": (
                        span_data.get("end_time_unix_nano", 0)
                        - span_data.get("start_time_unix_nano", 0)
                    ),
                    "attributes": all_attrs,
                    "billing": billing_attrs.model_dump() if billing_attrs else None,
                    "edge": self._extract_edge_attributes(all_attrs).model_dump(),
                    "work": self._extract_work_attributes(all_attrs).model_dump(),
                },
            )
            self.session.add(end_event)

    async def _process_span_event(
        self,
        event_data: dict[str, Any],
        span_data: dict[str, Any],
        resource_attrs: dict[str, Any],
    ) -> None:
        """Process a span event."""
        # Extract billing attributes from span and resource
        all_attrs = {
            **resource_attrs,
            **span_data.get("attributes", {}),
            **event_data.get("attributes", {}),
        }
        billing_attrs = self._extract_billing_attributes(all_attrs)

        if not billing_attrs or not billing_attrs.customer_id:
            raise ValueError("Missing required billing.customer_id attribute")

        event = RawEvent(
            customer_id=billing_attrs.customer_id,
            ts=self._parse_timestamp(event_data.get("time_unix_nano")),
            event_type="span_event",
            trace_id=span_data.get("trace_id"),
            span_id=span_data.get("span_id"),
            payload_json={
                "event_name": event_data.get("name"),
                "attributes": all_attrs,
                "billing": billing_attrs.model_dump() if billing_attrs else None,
                "outcome": self._extract_outcome_attributes(all_attrs).model_dump(),
            },
        )
        self.session.add(event)

    async def process_outcome_event(self, request: OutcomeEventRequest) -> int:
        """Process a direct outcome event submission."""
        # Verify customer exists
        await self._verify_customer_exists(request.customer_id)

        timestamp = request.timestamp or datetime.utcnow()

        event = RawEvent(
            customer_id=request.customer_id,
            ts=timestamp,
            event_type="outcome",
            trace_id=request.trace_id,
            span_id=request.span_id,
            payload_json={
                "event_name": request.event_name,
                "workflow_run_id": str(request.workflow_run_id)
                if request.workflow_run_id
                else None,
                "attributes": request.attributes,
                "outcome": self._extract_outcome_attributes(
                    request.attributes
                ).model_dump(),
            },
        )
        self.session.add(event)
        await self.session.commit()

        return event.id

    async def generate_usage_preview(
        self,
        customer_id: UUID,
        from_date: datetime,
        to_date: datetime,
        include_breakdown: bool = False,
    ) -> UsagePreviewResponse:
        """Generate a usage preview for a customer."""
        # This is a placeholder implementation
        # In a real implementation, this would query meter_readings table
        # and apply pricing policies to estimate costs

        return UsagePreviewResponse(
            customer_id=customer_id,
            period_start=from_date,
            period_end=to_date,
            meters={
                "api.calls": 1250.0,
                "llm.tokens": 45000.0,
                "workflow.completed": 23.0,
            },
            estimated_cost=125.50,
            breakdown={
                "base_fee": 50.0,
                "usage_charges": 75.50,
                "included_allowances": {"llm.tokens": 10000, "api.calls": 1000},
                "overage_charges": {"llm.tokens": 70.0, "api.calls": 5.50},
            }
            if include_breakdown
            else None,
        )

    async def create_adjustment(self, adjustment_data: dict[str, Any]) -> int:
        """Create a billing adjustment."""
        audit_entry = AuditLog(
            actor=adjustment_data.get("actor", "system"),
            action="adjustment_created",
            subject=f"customer:{adjustment_data.get('customer_id')}",
            details_json=adjustment_data,
        )
        self.session.add(audit_entry)
        await self.session.commit()

        return audit_entry.id

    async def _verify_customer_exists(self, customer_id: UUID) -> None:
        """Verify that a customer exists."""
        result = await self.session.execute(
            select(Customer).where(Customer.id == customer_id)
        )
        customer = result.scalar_one_or_none()
        if not customer:
            raise ValueError(f"Customer {customer_id} not found")

    def _extract_billing_attributes(
        self, attributes: dict[str, Any]
    ) -> BillingAttributes | None:
        """Extract billing attributes from span/event attributes."""
        try:
            return BillingAttributes(
                customer_id=UUID(attributes.get("billing.customer_id")),
                workflow_run_id=UUID(attributes.get("billing.workflow_run_id"))
                if attributes.get("billing.workflow_run_id")
                else None,
                meter_candidates=attributes.get("billing.meter_candidates", []),
            )
        except (ValueError, TypeError):
            return None

    def _extract_edge_attributes(self, attributes: dict[str, Any]) -> EdgeAttributes:
        """Extract edge attributes from span/event attributes."""
        return EdgeAttributes(
            llm_tokens_input=attributes.get("llm.tokens_input"),
            llm_tokens_output=attributes.get("llm.tokens_output"),
            llm_tokens=attributes.get("llm.tokens"),
            compute_ms=attributes.get("compute.ms"),
            net_bytes_in=attributes.get("net.bytes_in"),
            net_bytes_out=attributes.get("net.bytes_out"),
            storage_gb_hours=attributes.get("storage.gb_hours"),
        )

    def _extract_work_attributes(self, attributes: dict[str, Any]) -> WorkAttributes:
        """Extract work attributes from span/event attributes."""
        return WorkAttributes(
            workflow_definition=attributes.get("workflow.definition"),
            workflow_version=attributes.get("workflow.version"),
            step_key=attributes.get("step.key"),
            actor_type=attributes.get("actor.type"),
        )

    def _extract_outcome_attributes(
        self, attributes: dict[str, Any]
    ) -> OutcomeAttributes:
        """Extract outcome attributes from span/event attributes."""
        return OutcomeAttributes(
            sla_met=attributes.get("sla.met"),
            outcome_type=attributes.get("outcome.type"),
            outcome_value=attributes.get("outcome.value"),
        )

    def _parse_timestamp(self, unix_nano: int | None) -> datetime:
        """Parse Unix nanosecond timestamp to datetime."""
        if unix_nano is None:
            return datetime.utcnow()
        return datetime.utcfromtimestamp(unix_nano / 1_000_000_000)
