"""Main rating engine for dual-rail billing."""

import logging
from collections import defaultdict
from datetime import datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from kachi.lib.models import MeterReading, RatedUsage
from kachi.lib.rating_policies import (
    EnvelopeAllocation,
    RatedLine,
    RatingPolicy,
    RatingResult,
    UsageReading,
    allocate_work_envelopes,
    apply_exclusions,
    calculate_tiered_pricing,
    is_edge_meter,
    is_work_meter,
)

logger = logging.getLogger(__name__)


class RatingEngine:
    """Core rating engine for processing meter readings into billable amounts."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def rate_customer_period(
        self,
        customer_id: UUID,
        period_start: datetime,
        period_end: datetime,
        policy: RatingPolicy,
    ) -> RatingResult:
        """Rate a customer's usage for a specific period."""
        logger.info(
            f"Rating customer {customer_id} for period {period_start} to {period_end}"
        )

        # Load meter readings for the period
        usage_readings = await self._load_meter_readings(
            customer_id, period_start, period_end
        )

        if not usage_readings:
            logger.info(f"No usage found for customer {customer_id} in period")
            return self._create_empty_result(customer_id, period_start, period_end)

        # Apply exclusion rules
        filtered_readings = apply_exclusions(usage_readings, policy)

        # Allocate work envelopes
        envelopes = allocate_work_envelopes(filtered_readings, policy)
        envelope_allocations = {
            meter: EnvelopeAllocation(
                edge_meter=meter,
                allocated=amount,
                consumed=Decimal("0"),
                remaining=amount,
            )
            for meter, amount in envelopes.items()
        }

        # Rate based on precedence policy
        if policy.precedence == "work_over_edges":
            lines = await self._rate_work_over_edges(
                filtered_readings, policy, envelope_allocations
            )
        elif policy.precedence == "edges_over_work":
            lines = await self._rate_edges_over_work(
                filtered_readings, policy, envelope_allocations
            )
        else:  # parallel
            lines = await self._rate_parallel(
                filtered_readings, policy, envelope_allocations
            )

        # Add base fee if configured
        if policy.base_fee > 0:
            lines.append(
                RatedLine(
                    meter_key="base_fee",
                    usage_quantity=Decimal("1"),
                    billable_quantity=Decimal("1"),
                    unit_price=policy.base_fee,
                    amount=policy.base_fee,
                    line_type="base_fee",
                    description="Monthly base fee",
                )
            )

        # Calculate totals
        subtotal = sum(line.amount for line in lines)
        discount_amount = subtotal * (policy.discount_percent / Decimal("100"))
        total = subtotal - discount_amount

        # Apply spend cap if configured
        if policy.spend_cap and total > policy.spend_cap:
            cap_discount = total - policy.spend_cap
            discount_amount += cap_discount
            total = policy.spend_cap

        # Estimate COGS and margin
        cogs_estimate = await self._estimate_cogs(
            lines, customer_id, period_start, period_end
        )
        margin_estimate = total - cogs_estimate

        return RatingResult(
            customer_id=customer_id,
            period_start=period_start.isoformat(),
            period_end=period_end.isoformat(),
            lines=lines,
            envelopes=envelope_allocations,
            subtotal=subtotal,
            discount_amount=discount_amount,
            total=total,
            cogs_estimate=cogs_estimate,
            margin_estimate=margin_estimate,
        )

    async def _load_meter_readings(
        self, customer_id: UUID, period_start: datetime, period_end: datetime
    ) -> list[UsageReading]:
        """Load and aggregate meter readings for the period."""
        query = select(MeterReading).where(
            MeterReading.customer_id == customer_id,
            MeterReading.window_start >= period_start,
            MeterReading.window_end <= period_end,
        )

        result = await self.session.execute(query)
        readings = result.scalars().all()

        # Aggregate by meter key
        aggregated = defaultdict(Decimal)
        for reading in readings:
            aggregated[reading.meter_key] += reading.value

        return [
            UsageReading(
                meter_key=meter_key,
                value=total_value,
                customer_id=customer_id,
                period_start=period_start.isoformat(),
                period_end=period_end.isoformat(),
            )
            for meter_key, total_value in aggregated.items()
        ]

    async def _rate_work_over_edges(
        self,
        readings: list[UsageReading],
        policy: RatingPolicy,
        envelopes: dict[str, EnvelopeAllocation],
    ) -> list[RatedLine]:
        """Rate with work taking precedence over edges."""
        lines = []

        # First, rate all work meters
        for reading in readings:
            if is_work_meter(reading.meter_key):
                work_lines = await self._rate_meter(reading, policy)
                lines.extend(work_lines)

        # Then rate edge meters with envelope consumption
        for reading in readings:
            if is_edge_meter(reading.meter_key):
                edge_lines = await self._rate_edge_with_envelope(
                    reading, policy, envelopes
                )
                lines.extend(edge_lines)

        return lines

    async def _rate_edges_over_work(
        self,
        readings: list[UsageReading],
        policy: RatingPolicy,
        envelopes: dict[str, EnvelopeAllocation],
    ) -> list[RatedLine]:
        """Rate with edges taking precedence over work."""
        lines = []

        # First, rate all edge meters (no envelopes applied)
        for reading in readings:
            if is_edge_meter(reading.meter_key):
                edge_lines = await self._rate_meter(reading, policy)
                lines.extend(edge_lines)

        # Then rate work meters
        for reading in readings:
            if is_work_meter(reading.meter_key):
                work_lines = await self._rate_meter(reading, policy)
                lines.extend(work_lines)

        return lines

    async def _rate_parallel(
        self,
        readings: list[UsageReading],
        policy: RatingPolicy,
        envelopes: dict[str, EnvelopeAllocation],
    ) -> list[RatedLine]:
        """Rate work and edges in parallel (no precedence)."""
        lines = []

        # Rate all meters independently
        for reading in readings:
            if is_work_meter(reading.meter_key):
                work_lines = await self._rate_meter(reading, policy)
                lines.extend(work_lines)
            elif is_edge_meter(reading.meter_key):
                # In parallel mode, edges get reduced envelope benefit
                edge_lines = await self._rate_edge_with_envelope(
                    reading, policy, envelopes, reduction_factor=Decimal("0.5")
                )
                lines.extend(edge_lines)

        return lines

    async def _rate_meter(
        self, reading: UsageReading, policy: RatingPolicy
    ) -> list[RatedLine]:
        """Rate a single meter without envelope considerations."""
        meter_pricing = policy.meter_pricing.get(reading.meter_key)
        if not meter_pricing:
            # No pricing configured, skip
            return []

        # Apply included quota
        billable_usage = max(Decimal("0"), reading.value - meter_pricing.included_quota)

        if billable_usage <= 0:
            # All usage covered by included quota
            return [
                RatedLine(
                    meter_key=reading.meter_key,
                    usage_quantity=reading.value,
                    billable_quantity=Decimal("0"),
                    unit_price=Decimal("0"),
                    amount=Decimal("0"),
                    line_type="work" if is_work_meter(reading.meter_key) else "edge",
                    description=f"{reading.meter_key} (included in plan)",
                    included_consumed=reading.value,
                )
            ]

        # Calculate tiered pricing
        total_amount, tier_breakdown = calculate_tiered_pricing(
            billable_usage, meter_pricing
        )

        # Create line item
        avg_unit_price = (
            total_amount / billable_usage if billable_usage > 0 else Decimal("0")
        )

        return [
            RatedLine(
                meter_key=reading.meter_key,
                usage_quantity=reading.value,
                billable_quantity=billable_usage,
                unit_price=avg_unit_price,
                amount=total_amount,
                line_type="work" if is_work_meter(reading.meter_key) else "edge",
                description=f"{reading.meter_key} usage",
                included_consumed=meter_pricing.included_quota,
            )
        ]

    async def _rate_edge_with_envelope(
        self,
        reading: UsageReading,
        policy: RatingPolicy,
        envelopes: dict[str, EnvelopeAllocation],
        reduction_factor: Decimal = Decimal("1.0"),
    ) -> list[RatedLine]:
        """Rate an edge meter considering envelope allocation."""
        meter_pricing = policy.meter_pricing.get(reading.meter_key)
        if not meter_pricing:
            return []

        # Get envelope allocation
        envelope = envelopes.get(reading.meter_key)
        envelope_available = Decimal("0")
        if envelope and envelope.remaining > 0:
            envelope_available = envelope.remaining * reduction_factor

        # Calculate what's covered by included quota + envelope
        total_covered = meter_pricing.included_quota + envelope_available
        billable_usage = max(Decimal("0"), reading.value - total_covered)

        # Update envelope consumption
        if envelope:
            envelope_consumed = min(
                reading.value - meter_pricing.included_quota, envelope_available
            )
            envelope.consumed += envelope_consumed
            envelope.remaining -= envelope_consumed

        # Calculate pricing for billable portion
        if billable_usage <= 0:
            return [
                RatedLine(
                    meter_key=reading.meter_key,
                    usage_quantity=reading.value,
                    billable_quantity=Decimal("0"),
                    unit_price=Decimal("0"),
                    amount=Decimal("0"),
                    line_type="edge",
                    description=f"{reading.meter_key} (covered by plan + envelope)",
                    included_consumed=meter_pricing.included_quota,
                    envelope_consumed=envelope_available if envelope else Decimal("0"),
                )
            ]

        total_amount, _ = calculate_tiered_pricing(billable_usage, meter_pricing)
        avg_unit_price = (
            total_amount / billable_usage if billable_usage > 0 else Decimal("0")
        )

        return [
            RatedLine(
                meter_key=reading.meter_key,
                usage_quantity=reading.value,
                billable_quantity=billable_usage,
                unit_price=avg_unit_price,
                amount=total_amount,
                line_type="edge",
                description=f"{reading.meter_key} overage",
                included_consumed=meter_pricing.included_quota,
                envelope_consumed=envelope_available if envelope else Decimal("0"),
            )
        ]

    async def _estimate_cogs(
        self,
        lines: list[RatedLine],
        customer_id: UUID,
        period_start: datetime,
        period_end: datetime,
    ) -> Decimal:
        """Estimate cost of goods sold for the rated usage."""
        # This would integrate with cost tracking system
        # For now, return a simple estimate
        total_revenue = sum(line.amount for line in lines)
        return total_revenue * Decimal("0.3")  # Assume 30% COGS

    def _create_empty_result(
        self, customer_id: UUID, period_start: datetime, period_end: datetime
    ) -> RatingResult:
        """Create an empty rating result for periods with no usage."""
        return RatingResult(
            customer_id=customer_id,
            period_start=period_start.isoformat(),
            period_end=period_end.isoformat(),
            lines=[],
            envelopes={},
            subtotal=Decimal("0"),
            discount_amount=Decimal("0"),
            total=Decimal("0"),
        )


class RatingService:
    """High-level service for rating operations."""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.engine = RatingEngine(session)

    async def rate_and_store(
        self,
        customer_id: UUID,
        period_start: datetime,
        period_end: datetime,
        policy: RatingPolicy | None = None,
    ) -> RatingResult:
        """Rate a customer period and store the result."""
        if policy is None:
            policy = await self.get_customer_policy(customer_id)

        # Rate the period
        result = await self.engine.rate_customer_period(
            customer_id, period_start, period_end, policy
        )

        # Store the rated usage
        await self._store_rated_usage(result)

        return result

    async def _store_rated_usage(self, result: RatingResult) -> None:
        """Store rated usage in the database."""
        # Check if already exists
        existing_query = select(RatedUsage).where(
            RatedUsage.customer_id == result.customer_id,
            RatedUsage.period_start == datetime.fromisoformat(result.period_start),
            RatedUsage.period_end == datetime.fromisoformat(result.period_end),
        )

        existing_result = await self.session.execute(existing_query)
        existing = existing_result.scalar_one_or_none()

        if existing:
            # Update existing record
            existing.total_amount = result.total
            existing.line_items_json = {
                "lines": [line.dict() for line in result.lines],
                "envelopes": {k: v.dict() for k, v in result.envelopes.items()},
                "subtotal": str(result.subtotal),
                "discount_amount": str(result.discount_amount),
            }
            existing.cogs_amount = result.cogs_estimate
            existing.margin_amount = result.margin_estimate
        else:
            # Create new record
            rated_usage = RatedUsage(
                customer_id=UUID(result.customer_id),
                period_start=datetime.fromisoformat(result.period_start),
                period_end=datetime.fromisoformat(result.period_end),
                total_amount=result.total,
                line_items_json={
                    "lines": [line.dict() for line in result.lines],
                    "envelopes": {k: v.dict() for k, v in result.envelopes.items()},
                    "subtotal": str(result.subtotal),
                    "discount_amount": str(result.discount_amount),
                },
                cogs_amount=result.cogs_estimate,
                margin_amount=result.margin_estimate,
            )
            self.session.add(rated_usage)

        await self.session.commit()

    async def get_customer_policy(self, customer_id: UUID) -> RatingPolicy:
        """Get the rating policy for a customer."""
        # For now, return a default policy
        # In production, this would load from customer's plan
        return self._get_default_policy()

    def _get_default_policy(self) -> RatingPolicy:
        """Get the default rating policy."""
        from kachi.lib.rating_policies import MeterPricing, PricingTier

        return RatingPolicy(
            precedence="work_over_edges",
            edges_included_per_work={
                "workflow.completed": {
                    "llm.tokens": Decimal("50000"),
                    "api.calls": Decimal("10"),
                    "compute.ms": Decimal("30000"),
                }
            },
            exclusions=[{"when": "workflow.completed", "drop": ["api.calls"]}],
            overage_spill=True,
            meter_pricing={
                "workflow.completed": MeterPricing(
                    meter_key="workflow.completed",
                    included_quota=Decimal("100"),
                    tiers=[
                        PricingTier(
                            min_usage=Decimal("0"),
                            max_usage=Decimal("1000"),
                            unit_price=Decimal("0.50"),
                        ),
                        PricingTier(
                            min_usage=Decimal("1000"), unit_price=Decimal("0.40")
                        ),
                    ],
                ),
                "llm.tokens": MeterPricing(
                    meter_key="llm.tokens",
                    included_quota=Decimal("1000000"),
                    tiers=[
                        PricingTier(
                            min_usage=Decimal("0"),
                            unit_price=Decimal("0.000015"),  # $0.015 per 1K tokens
                        )
                    ],
                ),
                "api.calls": MeterPricing(
                    meter_key="api.calls",
                    included_quota=Decimal("10000"),
                    tiers=[
                        PricingTier(
                            min_usage=Decimal("0"),
                            unit_price=Decimal("0.001"),  # $0.001 per call
                        )
                    ],
                ),
            },
            base_fee=Decimal("99.00"),
            spend_cap=Decimal("10000.00"),
            discount_percent=Decimal("0"),
        )
