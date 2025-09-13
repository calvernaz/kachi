"""COGS (Cost of Goods Sold) calculation pipeline for margin intelligence."""

import logging
from collections import defaultdict
from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from kachi.lib.models import CostRecord, MeterReading, WorkflowRun

logger = logging.getLogger(__name__)


class COGSCalculator:
    """Calculate COGS and margin for billing periods and meter readings."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def calculate_period_cogs(
        self,
        customer_id: UUID,
        period_start: datetime,
        period_end: datetime,
    ) -> dict[str, Any]:
        """Calculate total COGS for a customer billing period."""
        # Get all cost records for the period
        cost_result = await self.session.execute(
            select(CostRecord)
            .join(WorkflowRun, CostRecord.workflow_run_id == WorkflowRun.id)
            .where(
                WorkflowRun.customer_id == customer_id,
                CostRecord.ts >= period_start,
                CostRecord.ts <= period_end,
            )
        )
        cost_records = cost_result.scalars().all()

        # Aggregate costs by type
        cogs_by_type = defaultdict(Decimal)
        total_cogs = Decimal("0")

        for record in cost_records:
            cogs_by_type[record.cost_type] += record.cost_amount
            total_cogs += record.cost_amount

        return {
            "total_cogs": total_cogs,
            "cogs_by_type": dict(cogs_by_type),
            "cost_records_count": len(cost_records),
            "period_start": period_start.isoformat(),
            "period_end": period_end.isoformat(),
        }

    async def calculate_meter_cogs(
        self,
        customer_id: UUID,
        meter_key: str,
        period_start: datetime,
        period_end: datetime,
    ) -> dict[str, Any]:
        """Calculate COGS attribution for a specific meter."""
        # Get meter readings for the period
        meter_result = await self.session.execute(
            select(MeterReading).where(
                MeterReading.customer_id == customer_id,
                MeterReading.meter_key == meter_key,
                MeterReading.window_start >= period_start,
                MeterReading.window_end <= period_end,
            )
        )
        meter_readings = meter_result.scalars().all()

        if not meter_readings:
            return {
                "meter_key": meter_key,
                "total_usage": Decimal("0"),
                "attributed_cogs": Decimal("0"),
                "cost_per_unit": Decimal("0"),
            }

        total_usage = sum(reading.value for reading in meter_readings)

        # Calculate COGS attribution based on meter type
        attributed_cogs = await self._calculate_meter_attribution(
            customer_id, meter_key, meter_readings, period_start, period_end
        )

        cost_per_unit = (
            attributed_cogs / total_usage if total_usage > 0 else Decimal("0")
        )

        return {
            "meter_key": meter_key,
            "total_usage": total_usage,
            "attributed_cogs": attributed_cogs,
            "cost_per_unit": cost_per_unit,
            "readings_count": len(meter_readings),
        }

    async def _calculate_meter_attribution(
        self,
        customer_id: UUID,
        meter_key: str,
        meter_readings: list[MeterReading],
        period_start: datetime,
        period_end: datetime,
    ) -> Decimal:
        """Calculate COGS attribution for a specific meter based on its type."""
        # Get workflow runs that contributed to these meter readings
        workflow_runs = await self._get_related_workflow_runs(
            customer_id, meter_readings, period_start, period_end
        )

        if not workflow_runs:
            return Decimal("0")

        # Get cost records for these workflow runs
        cost_result = await self.session.execute(
            select(CostRecord).where(
                CostRecord.workflow_run_id.in_([run.id for run in workflow_runs]),
                CostRecord.ts >= period_start,
                CostRecord.ts <= period_end,
            )
        )
        cost_records = cost_result.scalars().all()

        # Attribution logic based on meter type
        if meter_key.startswith("llm."):
            return self._attribute_llm_costs(cost_records, meter_key)
        elif meter_key.startswith("compute."):
            return self._attribute_compute_costs(cost_records)
        elif meter_key.startswith("storage."):
            return self._attribute_storage_costs(cost_records)
        elif meter_key.startswith("api."):
            return self._attribute_api_costs(cost_records)
        elif meter_key.startswith("workflow."):
            return self._attribute_workflow_costs(cost_records)
        else:
            # Default: proportional attribution
            return sum(record.cost_amount for record in cost_records)

    async def _get_related_workflow_runs(
        self,
        customer_id: UUID,
        meter_readings: list[MeterReading],
        period_start: datetime,
        period_end: datetime,
    ) -> list[WorkflowRun]:
        """Get workflow runs related to the meter readings."""
        # For now, get all workflow runs in the period
        # TODO: Improve this by using src_event_ids to trace back to specific runs
        result = await self.session.execute(
            select(WorkflowRun).where(
                WorkflowRun.customer_id == customer_id,
                WorkflowRun.started_at >= period_start,
                WorkflowRun.started_at <= period_end,
            )
        )
        return result.scalars().all()

    def _attribute_llm_costs(
        self, cost_records: list[CostRecord], meter_key: str
    ) -> Decimal:
        """Attribute LLM-related costs."""
        llm_costs = [
            record.cost_amount
            for record in cost_records
            if record.cost_type in ("tokens", "llm_api", "openai", "anthropic")
        ]
        return sum(llm_costs)

    def _attribute_compute_costs(self, cost_records: list[CostRecord]) -> Decimal:
        """Attribute compute-related costs."""
        compute_costs = [
            record.cost_amount
            for record in cost_records
            if record.cost_type in ("compute", "cpu", "gpu", "memory")
        ]
        return sum(compute_costs)

    def _attribute_storage_costs(self, cost_records: list[CostRecord]) -> Decimal:
        """Attribute storage-related costs."""
        storage_costs = [
            record.cost_amount
            for record in cost_records
            if record.cost_type in ("storage", "s3", "database", "disk")
        ]
        return sum(storage_costs)

    def _attribute_api_costs(self, cost_records: list[CostRecord]) -> Decimal:
        """Attribute API-related costs."""
        api_costs = [
            record.cost_amount
            for record in cost_records
            if record.cost_type in ("api", "vendor_api", "external_service")
        ]
        return sum(api_costs)

    def _attribute_workflow_costs(self, cost_records: list[CostRecord]) -> Decimal:
        """Attribute workflow completion costs (all costs for the workflow)."""
        return sum(record.cost_amount for record in cost_records)

    async def calculate_margin_analysis(
        self,
        customer_id: UUID,
        period_start: datetime,
        period_end: datetime,
        revenue_lines: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """Calculate comprehensive margin analysis."""
        # Calculate total COGS
        cogs_data = await self.calculate_period_cogs(
            customer_id, period_start, period_end
        )
        total_cogs = cogs_data["total_cogs"]

        # Calculate total revenue
        total_revenue = sum(
            Decimal(str(line.get("amount", 0))) for line in revenue_lines
        )

        # Calculate margins
        gross_margin = total_revenue - total_cogs
        margin_percentage = (
            (gross_margin / total_revenue * 100) if total_revenue > 0 else Decimal("0")
        )

        # Calculate meter-level margins
        meter_margins = {}
        for line in revenue_lines:
            meter_key = line.get("meter_key")
            if meter_key:
                meter_cogs_data = await self.calculate_meter_cogs(
                    customer_id, meter_key, period_start, period_end
                )
                meter_revenue = Decimal(str(line.get("amount", 0)))
                meter_cogs = meter_cogs_data["attributed_cogs"]
                meter_margin = meter_revenue - meter_cogs
                meter_margin_pct = (
                    (meter_margin / meter_revenue * 100)
                    if meter_revenue > 0
                    else Decimal("0")
                )

                meter_margins[meter_key] = {
                    "revenue": meter_revenue,
                    "cogs": meter_cogs,
                    "margin": meter_margin,
                    "margin_percentage": meter_margin_pct,
                    "cost_per_unit": meter_cogs_data["cost_per_unit"],
                }

        return {
            "customer_id": str(customer_id),
            "period_start": period_start.isoformat(),
            "period_end": period_end.isoformat(),
            "total_revenue": total_revenue,
            "total_cogs": total_cogs,
            "gross_margin": gross_margin,
            "margin_percentage": margin_percentage,
            "cogs_by_type": cogs_data["cogs_by_type"],
            "meter_margins": meter_margins,
            "profitability_score": self._calculate_profitability_score(
                margin_percentage, total_revenue
            ),
        }

    def _calculate_profitability_score(
        self, margin_percentage: Decimal, total_revenue: Decimal
    ) -> str:
        """Calculate a profitability score based on margin and revenue."""
        if margin_percentage >= 50:
            return "excellent"
        elif margin_percentage >= 30:
            return "good"
        elif margin_percentage >= 15:
            return "fair"
        elif margin_percentage >= 0:
            return "poor"
        else:
            return "loss"


class COGSTracker:
    """Track and record COGS in real-time during workflow execution."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def record_cost(
        self,
        workflow_run_id: UUID | None,
        cost_amount: Decimal,
        cost_type: str,
        details: dict[str, Any] | None = None,
        timestamp: datetime | None = None,
    ) -> CostRecord:
        """Record a cost entry."""
        cost_record = CostRecord(
            workflow_run_id=workflow_run_id,
            ts=timestamp or datetime.utcnow(),
            cost_amount=cost_amount,
            cost_type=cost_type,
            details_json=details,
        )

        self.session.add(cost_record)
        await self.session.commit()
        await self.session.refresh(cost_record)

        logger.info(
            f"Recorded cost: {cost_amount} {cost_type} for workflow {workflow_run_id}"
        )
        return cost_record

    async def record_llm_cost(
        self,
        workflow_run_id: UUID,
        input_tokens: int,
        output_tokens: int,
        model: str,
        cost_per_input_token: Decimal,
        cost_per_output_token: Decimal,
    ) -> CostRecord:
        """Record LLM usage cost."""
        input_cost = Decimal(input_tokens) * cost_per_input_token
        output_cost = Decimal(output_tokens) * cost_per_output_token
        total_cost = input_cost + output_cost

        details = {
            "model": model,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "cost_per_input_token": str(cost_per_input_token),
            "cost_per_output_token": str(cost_per_output_token),
            "input_cost": str(input_cost),
            "output_cost": str(output_cost),
        }

        return await self.record_cost(
            workflow_run_id=workflow_run_id,
            cost_amount=total_cost,
            cost_type="tokens",
            details=details,
        )

    async def record_compute_cost(
        self,
        workflow_run_id: UUID,
        duration_ms: int,
        cpu_cores: float,
        memory_gb: float,
        cost_per_core_hour: Decimal,
        cost_per_gb_hour: Decimal,
    ) -> CostRecord:
        """Record compute usage cost."""
        duration_hours = Decimal(duration_ms) / Decimal(3600000)  # ms to hours
        cpu_cost = Decimal(cpu_cores) * duration_hours * cost_per_core_hour
        memory_cost = Decimal(memory_gb) * duration_hours * cost_per_gb_hour
        total_cost = cpu_cost + memory_cost

        details = {
            "duration_ms": duration_ms,
            "duration_hours": str(duration_hours),
            "cpu_cores": cpu_cores,
            "memory_gb": memory_gb,
            "cost_per_core_hour": str(cost_per_core_hour),
            "cost_per_gb_hour": str(cost_per_gb_hour),
            "cpu_cost": str(cpu_cost),
            "memory_cost": str(memory_cost),
        }

        return await self.record_cost(
            workflow_run_id=workflow_run_id,
            cost_amount=total_cost,
            cost_type="compute",
            details=details,
        )

    async def record_api_cost(
        self,
        workflow_run_id: UUID,
        api_calls: int,
        service_name: str,
        cost_per_call: Decimal,
    ) -> CostRecord:
        """Record external API usage cost."""
        total_cost = Decimal(api_calls) * cost_per_call

        details = {
            "api_calls": api_calls,
            "service_name": service_name,
            "cost_per_call": str(cost_per_call),
        }

        return await self.record_cost(
            workflow_run_id=workflow_run_id,
            cost_amount=total_cost,
            cost_type="api",
            details=details,
        )
