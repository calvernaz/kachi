"""Rating policies and precedence logic for dual-rail billing."""

from collections import defaultdict
from decimal import Decimal
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class PricingTier(BaseModel):
    """A pricing tier with min/max usage and unit price."""

    min_usage: Decimal = Field(default=Decimal("0"))
    max_usage: Decimal | None = None  # None means unlimited
    unit_price: Decimal = Field(default=Decimal("0"))
    flat_fee: Decimal = Field(default=Decimal("0"))


class MeterPricing(BaseModel):
    """Pricing configuration for a specific meter."""

    meter_key: str
    included_quota: Decimal = Field(default=Decimal("0"))
    tiers: list[PricingTier] = Field(default_factory=list)
    unit: str = "count"  # count, tokens, ms, bytes, etc.


class RatingPolicy(BaseModel):
    """Complete rating policy for a customer plan."""

    precedence: str = "work_over_edges"  # work_over_edges, edges_over_work, parallel

    # Envelope configuration - edges included per work unit
    edges_included_per_work: dict[str, dict[str, Decimal]] = Field(default_factory=dict)

    # Exclusions - drop certain edges when work is present
    exclusions: list[dict[str, Any]] = Field(default_factory=list)

    # Whether edge overage spills over after envelopes are consumed
    overage_spill: bool = True

    # Meter pricing configurations
    meter_pricing: dict[str, MeterPricing] = Field(default_factory=dict)

    # Plan-level settings
    base_fee: Decimal = Field(default=Decimal("0"))
    spend_cap: Decimal | None = None
    discount_percent: Decimal = Field(default=Decimal("0"))


class UsageReading(BaseModel):
    """A single meter reading for rating."""

    meter_key: str
    value: Decimal
    customer_id: UUID
    period_start: str  # ISO datetime
    period_end: str  # ISO datetime


class RatedLine(BaseModel):
    """A single rated line item."""

    meter_key: str
    usage_quantity: Decimal
    billable_quantity: Decimal
    unit_price: Decimal
    amount: Decimal
    line_type: str  # "work", "edge", "outcome", "base_fee"
    description: str
    envelope_consumed: Decimal = Field(default=Decimal("0"))
    included_consumed: Decimal = Field(default=Decimal("0"))


class EnvelopeAllocation(BaseModel):
    """Tracks envelope allocations for edge meters."""

    edge_meter: str
    allocated: Decimal
    consumed: Decimal
    remaining: Decimal

    @property
    def is_exhausted(self) -> bool:
        return self.remaining <= 0


class RatingResult(BaseModel):
    """Complete rating result for a billing period."""

    customer_id: UUID
    period_start: str
    period_end: str
    lines: list[RatedLine]
    envelopes: dict[str, EnvelopeAllocation]
    subtotal: Decimal
    discount_amount: Decimal
    total: Decimal
    cogs_estimate: Decimal = Field(default=Decimal("0"))
    margin_estimate: Decimal = Field(default=Decimal("0"))


def allocate_work_envelopes(
    usage_readings: list[UsageReading], policy: RatingPolicy
) -> dict[str, Decimal]:
    """Allocate edge envelopes based on work completed."""
    envelopes = defaultdict(Decimal)

    # Get work meter readings
    work_usage = {
        r.meter_key: r.value for r in usage_readings if is_work_meter(r.meter_key)
    }

    # Allocate envelopes for each work type
    for work_meter, work_count in work_usage.items():
        edge_allowances = policy.edges_included_per_work.get(work_meter, {})

        for edge_meter, allowance_per_work in edge_allowances.items():
            envelope_size = Decimal(allowance_per_work) * work_count
            envelopes[edge_meter] += envelope_size

    return dict(envelopes)


def is_work_meter(meter_key: str) -> bool:
    """Check if a meter represents work/outcomes."""
    work_prefixes = ["workflow.", "outcome.", "step.", "task."]
    return any(meter_key.startswith(prefix) for prefix in work_prefixes)


def is_edge_meter(meter_key: str) -> bool:
    """Check if a meter represents resource consumption."""
    edge_prefixes = ["api.", "llm.", "compute.", "storage.", "net."]
    return any(meter_key.startswith(prefix) for prefix in edge_prefixes)


def calculate_tiered_pricing(
    usage: Decimal, pricing: MeterPricing
) -> tuple[Decimal, list[tuple[Decimal, Decimal, Decimal]]]:
    """Calculate tiered pricing for a meter.

    Returns:
        (total_amount, [(tier_usage, tier_price, tier_amount), ...])
    """
    if not pricing.tiers:
        return Decimal("0"), []

    total_amount = Decimal("0")
    tier_breakdown = []
    remaining_usage = usage
    usage_processed = Decimal("0")

    for tier in pricing.tiers:
        if remaining_usage <= 0:
            break

        # Calculate the range for this tier
        tier_start = tier.min_usage
        tier_end = (
            tier.max_usage
            if tier.max_usage is not None
            else usage_processed + remaining_usage
        )

        # Skip if we haven't reached this tier yet
        if usage_processed < tier_start:
            # Jump to the start of this tier
            skip_amount = tier_start - usage_processed
            if skip_amount >= remaining_usage:
                break  # All remaining usage is below this tier
            remaining_usage -= skip_amount
            usage_processed = tier_start

        # Calculate usage in this tier
        tier_capacity = tier_end - usage_processed
        tier_usage = min(remaining_usage, tier_capacity)

        if tier_usage > 0:
            tier_amount = tier_usage * tier.unit_price + tier.flat_fee
            total_amount += tier_amount
            tier_breakdown.append((tier_usage, tier.unit_price, tier_amount))
            remaining_usage -= tier_usage
            usage_processed += tier_usage

    return total_amount, tier_breakdown


def apply_exclusions(
    usage_readings: list[UsageReading], policy: RatingPolicy
) -> list[UsageReading]:
    """Apply exclusion rules to filter out certain meters."""
    if not policy.exclusions:
        return usage_readings

    # Build usage lookup
    usage_by_meter = {r.meter_key: r for r in usage_readings}
    excluded_meters = set()

    for exclusion in policy.exclusions:
        when_meter = exclusion.get("when")
        drop_meters = exclusion.get("drop", [])

        # Check if the condition meter has usage
        if (
            when_meter
            and when_meter in usage_by_meter
            and usage_by_meter[when_meter].value > 0
        ):
            excluded_meters.update(drop_meters)

    # Filter out excluded meters
    return [r for r in usage_readings if r.meter_key not in excluded_meters]


def bill_edge_spill(
    edge_total: Decimal, included: Decimal, envelope: Decimal, unit_price: Decimal
) -> Decimal:
    """Calculate billable amount for edge spill beyond included + envelope."""
    billable = max(Decimal("0"), edge_total - included - envelope)
    return billable * unit_price
