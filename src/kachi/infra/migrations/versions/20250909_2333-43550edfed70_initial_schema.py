"""Initial schema

Revision ID: 43550edfed70
Revises:
Create Date: 2025-09-09 23:33:48.613906

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "43550edfed70"
down_revision: str | Sequence[str] | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    # Create customers table
    op.create_table(
        "customers",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("lago_customer_id", sa.String(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("currency", sa.String(), nullable=False, server_default="EUR"),
        sa.Column("status", sa.String(), nullable=False, server_default="active"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("lago_customer_id"),
    )
    op.create_index(
        op.f("ix_customers_lago_customer_id"),
        "customers",
        ["lago_customer_id"],
        unique=True,
    )

    # Create workflow_definitions table
    op.create_table(
        "workflow_definitions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("key", sa.String(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column(
            "definition_schema", postgresql.JSONB(astext_type=sa.Text()), nullable=False
        ),
        sa.Column("active", sa.Boolean(), nullable=False, server_default="true"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("key", "version"),
    )

    # Create workflow_runs table
    op.create_table(
        "workflow_runs",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("customer_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("definition_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("started_at", postgresql.TIMESTAMP(timezone=True), nullable=False),
        sa.Column("ended_at", postgresql.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column(
            "metadata_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True
        ),
        sa.ForeignKeyConstraint(
            ["customer_id"],
            ["customers.id"],
        ),
        sa.ForeignKeyConstraint(
            ["definition_id"],
            ["workflow_definitions.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_workflow_runs_customer_id"),
        "workflow_runs",
        ["customer_id"],
        unique=False,
    )

    # Create raw_events table
    op.create_table(
        "raw_events",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("customer_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("ts", postgresql.TIMESTAMP(timezone=True), nullable=False),
        sa.Column("event_type", sa.String(), nullable=False),
        sa.Column("trace_id", sa.String(), nullable=True),
        sa.Column("span_id", sa.String(), nullable=True),
        sa.Column(
            "payload_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False
        ),
        sa.ForeignKeyConstraint(
            ["customer_id"],
            ["customers.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("trace_id", "span_id", "event_type", "ts"),
    )
    op.create_index(
        "idx_raw_events_customer_ts", "raw_events", ["customer_id", "ts"], unique=False
    )
    op.create_index("idx_raw_events_trace", "raw_events", ["trace_id"], unique=False)
    op.create_index(
        op.f("ix_raw_events_customer_id"), "raw_events", ["customer_id"], unique=False
    )

    # Create meter_readings table
    op.create_table(
        "meter_readings",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("customer_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("meter_key", sa.String(), nullable=False),
        sa.Column("window_start", postgresql.TIMESTAMP(timezone=True), nullable=False),
        sa.Column("window_end", postgresql.TIMESTAMP(timezone=True), nullable=False),
        sa.Column("value", sa.Numeric(precision=20, scale=6), nullable=False),
        sa.Column(
            "src_event_ids",
            postgresql.ARRAY(sa.BigInteger()),
            nullable=False,
            server_default="{}",
        ),
        sa.ForeignKeyConstraint(
            ["customer_id"],
            ["customers.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("customer_id", "meter_key", "window_start", "window_end"),
    )
    op.create_index(
        "idx_meter_readings_customer_meter",
        "meter_readings",
        ["customer_id", "meter_key"],
        unique=False,
    )
    op.create_index(
        "idx_meter_readings_window",
        "meter_readings",
        ["window_start", "window_end"],
        unique=False,
    )
    op.create_index(
        op.f("ix_meter_readings_customer_id"),
        "meter_readings",
        ["customer_id"],
        unique=False,
    )

    # Create cost_records table
    op.create_table(
        "cost_records",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("workflow_run_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("ts", postgresql.TIMESTAMP(timezone=True), nullable=False),
        sa.Column("cost_amount", sa.Numeric(precision=20, scale=6), nullable=False),
        sa.Column("cost_type", sa.String(), nullable=False),
        sa.Column(
            "details_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True
        ),
        sa.ForeignKeyConstraint(
            ["workflow_run_id"],
            ["workflow_runs.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    # Create rated_usage table
    op.create_table(
        "rated_usage",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("customer_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("period_start", sa.Text(), nullable=False),
        sa.Column("period_end", sa.Text(), nullable=False),
        sa.Column(
            "items_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False
        ),
        sa.Column("subtotal", sa.Numeric(precision=20, scale=6), nullable=False),
        sa.Column("cogs", sa.Numeric(precision=20, scale=6), nullable=False),
        sa.Column("margin", sa.Numeric(precision=20, scale=6), nullable=False),
        sa.ForeignKeyConstraint(
            ["customer_id"],
            ["customers.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("customer_id", "period_start", "period_end"),
    )
    op.create_index(
        "idx_rated_usage_customer_period",
        "rated_usage",
        ["customer_id", "period_start"],
        unique=False,
    )
    op.create_index(
        op.f("ix_rated_usage_customer_id"), "rated_usage", ["customer_id"], unique=False
    )

    # Create audit_log table
    op.create_table(
        "audit_log",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column(
            "ts",
            postgresql.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("actor", sa.String(), nullable=False),
        sa.Column("action", sa.String(), nullable=False),
        sa.Column("subject", sa.String(), nullable=False),
        sa.Column(
            "details_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True
        ),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table("audit_log")
    op.drop_index("idx_rated_usage_customer_period", table_name="rated_usage")
    op.drop_index(op.f("ix_rated_usage_customer_id"), table_name="rated_usage")
    op.drop_table("rated_usage")
    op.drop_table("cost_records")
    op.drop_index("idx_meter_readings_customer_meter", table_name="meter_readings")
    op.drop_index("idx_meter_readings_window", table_name="meter_readings")
    op.drop_index(op.f("ix_meter_readings_customer_id"), table_name="meter_readings")
    op.drop_table("meter_readings")
    op.drop_index("idx_raw_events_customer_ts", table_name="raw_events")
    op.drop_index("idx_raw_events_trace", table_name="raw_events")
    op.drop_index(op.f("ix_raw_events_customer_id"), table_name="raw_events")
    op.drop_table("raw_events")
    op.drop_index(op.f("ix_workflow_runs_customer_id"), table_name="workflow_runs")
    op.drop_table("workflow_runs")
    op.drop_table("workflow_definitions")
    op.drop_index(op.f("ix_customers_lago_customer_id"), table_name="customers")
    op.drop_table("customers")
