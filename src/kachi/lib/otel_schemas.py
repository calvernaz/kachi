"""OpenTelemetry attribute conventions and schemas."""

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class BillingAttributes(BaseModel):
    """Required billing attributes for all spans/events."""

    customer_id: UUID = Field(..., description="Customer UUID")
    workflow_run_id: UUID | None = Field(
        None, description="Workflow run UUID when applicable"
    )
    meter_candidates: list[str] = Field(
        default_factory=list, description="List of potential meters for this event"
    )


class EdgeAttributes(BaseModel):
    """Edge-specific attributes for resource consumption."""

    llm_tokens_input: int | None = Field(None, description="Input tokens consumed")
    llm_tokens_output: int | None = Field(None, description="Output tokens consumed")
    llm_tokens: int | None = Field(None, description="Total tokens (input + output)")
    compute_ms: int | None = Field(None, description="Compute milliseconds")
    net_bytes_in: int | None = Field(None, description="Network bytes in")
    net_bytes_out: int | None = Field(None, description="Network bytes out")
    storage_gb_hours: float | None = Field(None, description="Storage GB-hours")


class WorkAttributes(BaseModel):
    """Work-specific attributes for business outcomes."""

    workflow_definition: str | None = Field(None, description="Workflow definition key")
    workflow_version: int | None = Field(None, description="Workflow version")
    step_key: str | None = Field(None, description="Step identifier")
    actor_type: str | None = Field(None, description="Actor type: human|service|agent")


class OutcomeAttributes(BaseModel):
    """Outcome-specific attributes."""

    sla_met: bool | None = Field(None, description="Whether SLA was met")
    outcome_type: str | None = Field(None, description="Type of outcome")
    outcome_value: str | None = Field(None, description="Outcome value or result")


class OTelSpan(BaseModel):
    """OpenTelemetry span representation."""

    trace_id: str
    span_id: str
    parent_span_id: str | None = None
    operation_name: str
    start_time: datetime
    end_time: datetime | None = None
    status: str = "OK"  # OK, ERROR, TIMEOUT
    attributes: dict[str, Any] = Field(default_factory=dict)
    events: list[dict[str, Any]] = Field(default_factory=list)

    # Parsed billing attributes
    billing: BillingAttributes | None = None
    edge: EdgeAttributes | None = None
    work: WorkAttributes | None = None
    outcome: OutcomeAttributes | None = None


class OTelEvent(BaseModel):
    """OpenTelemetry event representation."""

    name: str
    timestamp: datetime
    attributes: dict[str, Any] = Field(default_factory=dict)
    trace_id: str | None = None
    span_id: str | None = None

    # Parsed billing attributes
    billing: BillingAttributes | None = None
    edge: EdgeAttributes | None = None
    work: WorkAttributes | None = None
    outcome: OutcomeAttributes | None = None


class OTelExportRequest(BaseModel):
    """OpenTelemetry export request payload."""

    resource_spans: list[dict[str, Any]] = Field(default_factory=list)
    resource_logs: list[dict[str, Any]] = Field(default_factory=list)
    resource_metrics: list[dict[str, Any]] = Field(default_factory=list)


class OutcomeEventRequest(BaseModel):
    """Direct outcome event submission."""

    customer_id: UUID
    workflow_run_id: UUID | None = None
    event_name: str
    timestamp: datetime | None = None
    attributes: dict[str, Any] = Field(default_factory=dict)
    trace_id: str | None = None
    span_id: str | None = None


class UsagePreviewRequest(BaseModel):
    """Usage preview request."""

    customer_id: UUID
    from_date: datetime
    to_date: datetime
    include_breakdown: bool = False


class UsagePreviewResponse(BaseModel):
    """Usage preview response."""

    customer_id: UUID
    period_start: datetime
    period_end: datetime
    meters: dict[str, float]
    estimated_cost: float
    breakdown: dict[str, Any] | None = None


# Meter catalog constants
EDGE_METERS = {
    "api.calls": "API calls made",
    "llm.tokens": "LLM tokens consumed",
    "llm.tokens.input": "LLM input tokens",
    "llm.tokens.output": "LLM output tokens",
    "compute.ms": "Compute milliseconds",
    "net.bytes": "Network bytes transferred",
    "storage.gbh": "Storage GB-hours",
}

WORK_METERS = {
    "workflow.completed": "Completed workflows",
    "workflow.failed": "Failed workflows",
    "step.completed": "Completed steps",
    "outcome.ticket_resolved": "Tickets resolved",
    "outcome.document_processed": "Documents processed",
    "outcome.analysis_completed": "Analyses completed",
}

ALL_METERS = {**EDGE_METERS, **WORK_METERS}
