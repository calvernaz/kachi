"""Core data models for Kachi billing platform."""

from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import Column, Index, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import ARRAY, BIGINT, JSONB, TIMESTAMP
from sqlmodel import Field, SQLModel


class Customer(SQLModel, table=True):
    """Customer entity."""

    __tablename__ = "customers"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    lago_customer_id: str = Field(unique=True, index=True)
    name: str
    currency: str = Field(default="EUR")
    status: str = Field(default="active")


class WorkflowDefinition(SQLModel, table=True):
    """Workflow definition with versioning."""

    __tablename__ = "workflow_definitions"
    __table_args__ = (UniqueConstraint("key", "version"),)

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    key: str
    version: int
    definition_schema: dict[str, Any] = Field(sa_column=Column(JSONB))
    active: bool = Field(default=True)


class WorkflowRun(SQLModel, table=True):
    """Individual workflow execution."""

    __tablename__ = "workflow_runs"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    customer_id: UUID = Field(foreign_key="customers.id", index=True)
    definition_id: UUID = Field(foreign_key="workflow_definitions.id")
    started_at: datetime = Field(sa_column=Column(TIMESTAMP(timezone=True)))
    ended_at: datetime | None = Field(
        sa_column=Column(TIMESTAMP(timezone=True)), default=None
    )
    status: str
    metadata_json: dict[str, Any] | None = Field(sa_column=Column(JSONB), default=None)


class RawEvent(SQLModel, table=True):
    """Raw telemetry events from OpenTelemetry."""

    __tablename__ = "raw_events"
    __table_args__ = (
        UniqueConstraint("trace_id", "span_id", "event_type", "ts"),
        Index("idx_raw_events_customer_ts", "customer_id", "ts"),
        Index("idx_raw_events_trace", "trace_id"),
    )

    id: int = Field(sa_column=Column(BIGINT, primary_key=True, autoincrement=True))
    customer_id: UUID = Field(foreign_key="customers.id", index=True)
    ts: datetime = Field(sa_column=Column(TIMESTAMP(timezone=True)))
    event_type: str  # span_started, span_ended, outcome, counter, etc.
    trace_id: str | None = Field(default=None)
    span_id: str | None = Field(default=None)
    payload_json: dict[str, Any] = Field(sa_column=Column(JSONB))


class MeterReading(SQLModel, table=True):
    """Aggregated meter readings per time window."""

    __tablename__ = "meter_readings"
    __table_args__ = (
        UniqueConstraint("customer_id", "meter_key", "window_start", "window_end"),
        Index("idx_meter_readings_customer_meter", "customer_id", "meter_key"),
        Index("idx_meter_readings_window", "window_start", "window_end"),
    )

    id: int = Field(sa_column=Column(BIGINT, primary_key=True, autoincrement=True))
    customer_id: UUID = Field(foreign_key="customers.id", index=True)
    meter_key: str
    window_start: datetime = Field(sa_column=Column(TIMESTAMP(timezone=True)))
    window_end: datetime = Field(sa_column=Column(TIMESTAMP(timezone=True)))
    value: Decimal = Field(decimal_places=6, max_digits=20)
    src_event_ids: list[int] = Field(
        sa_column=Column(ARRAY(BIGINT)), default_factory=list
    )


class CostRecord(SQLModel, table=True):
    """Cost tracking for workflow runs."""

    __tablename__ = "cost_records"

    id: int = Field(sa_column=Column(BIGINT, primary_key=True, autoincrement=True))
    workflow_run_id: UUID | None = Field(foreign_key="workflow_runs.id", default=None)
    ts: datetime = Field(sa_column=Column(TIMESTAMP(timezone=True)))
    cost_amount: Decimal = Field(decimal_places=6, max_digits=20)
    cost_type: str  # tokens, compute, storage, vendor_api
    details_json: dict[str, Any] | None = Field(sa_column=Column(JSONB), default=None)


class RatedUsage(SQLModel, table=True):
    """Pre-invoice usage breakdown with COGS and margin."""

    __tablename__ = "rated_usage"
    __table_args__ = (
        UniqueConstraint("customer_id", "period_start", "period_end"),
        Index("idx_rated_usage_customer_period", "customer_id", "period_start"),
    )

    id: int = Field(sa_column=Column(BIGINT, primary_key=True, autoincrement=True))
    customer_id: UUID = Field(foreign_key="customers.id", index=True)
    period_start: datetime = Field(sa_column=Column("period_start", Text))  # date
    period_end: datetime = Field(sa_column=Column("period_end", Text))  # date
    items_json: dict[str, Any] = Field(sa_column=Column(JSONB))  # detailed lines
    subtotal: Decimal = Field(decimal_places=6, max_digits=20)
    cogs: Decimal = Field(decimal_places=6, max_digits=20)
    margin: Decimal = Field(decimal_places=6, max_digits=20)


class AuditLog(SQLModel, table=True):
    """Audit trail for all adjustments and disputes."""

    __tablename__ = "audit_log"

    id: int = Field(sa_column=Column(BIGINT, primary_key=True, autoincrement=True))
    ts: datetime = Field(
        sa_column=Column(TIMESTAMP(timezone=True)), default_factory=datetime.utcnow
    )
    actor: str
    action: str
    subject: str
    details_json: dict[str, Any] | None = Field(sa_column=Column(JSONB), default=None)
