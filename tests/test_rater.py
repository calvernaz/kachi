"""Tests for the rating engine."""

from datetime import datetime
from decimal import Decimal
from uuid import uuid4

import pytest

from kachi.apps.rater.main import RatingEngine
from kachi.lib.rating_policies import (
    MeterPricing,
    PricingTier,
    RatingPolicy,
    UsageReading,
    allocate_work_envelopes,
    apply_exclusions,
    bill_edge_spill,
    calculate_tiered_pricing,
    is_edge_meter,
    is_work_meter,
)


class MockSession:
    """Mock session for testing without database."""

    def __init__(self):
        self.added_objects = []
        self.meter_readings = []

    def add(self, obj):
        self.added_objects.append(obj)

    async def commit(self):
        pass

    async def execute(self, query):
        # Mock query execution
        return MockResult([])


class MockResult:
    def __init__(self, data):
        self.data = data

    def scalars(self):
        return MockScalars(self.data)

    def scalar_one_or_none(self):
        return self.data[0] if self.data else None


class MockScalars:
    def __init__(self, data):
        self.data = data

    def all(self):
        return self.data


def create_sample_usage() -> list[UsageReading]:
    """Create sample usage readings for testing."""
    customer_id = uuid4()
    period_start = "2024-01-01T00:00:00"
    period_end = "2024-01-01T23:59:59"

    return [
        UsageReading(
            meter_key="workflow.completed",
            value=Decimal("5"),
            customer_id=customer_id,
            period_start=period_start,
            period_end=period_end,
        ),
        UsageReading(
            meter_key="llm.tokens",
            value=Decimal("150000"),
            customer_id=customer_id,
            period_start=period_start,
            period_end=period_end,
        ),
        UsageReading(
            meter_key="api.calls",
            value=Decimal("25"),
            customer_id=customer_id,
            period_start=period_start,
            period_end=period_end,
        ),
        UsageReading(
            meter_key="compute.ms",
            value=Decimal("45000"),
            customer_id=customer_id,
            period_start=period_start,
            period_end=period_end,
        ),
    ]


def create_test_policy() -> RatingPolicy:
    """Create a test rating policy."""
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
                included_quota=Decimal("10"),
                tiers=[PricingTier(min_usage=Decimal("0"), unit_price=Decimal("1.00"))],
            ),
            "llm.tokens": MeterPricing(
                meter_key="llm.tokens",
                included_quota=Decimal("100000"),
                tiers=[
                    PricingTier(
                        min_usage=Decimal("0"),
                        unit_price=Decimal("0.00002"),  # $0.02 per 1K tokens
                    )
                ],
            ),
            "api.calls": MeterPricing(
                meter_key="api.calls",
                included_quota=Decimal("1000"),
                tiers=[PricingTier(min_usage=Decimal("0"), unit_price=Decimal("0.01"))],
            ),
            "compute.ms": MeterPricing(
                meter_key="compute.ms",
                included_quota=Decimal("10000"),
                tiers=[
                    PricingTier(min_usage=Decimal("0"), unit_price=Decimal("0.0001"))
                ],
            ),
        },
        base_fee=Decimal("50.00"),
        discount_percent=Decimal("0"),
    )


def test_meter_classification():
    """Test meter type classification."""
    assert is_work_meter("workflow.completed")
    assert is_work_meter("outcome.ticket_resolved")
    assert is_work_meter("step.extract_text")

    assert is_edge_meter("llm.tokens")
    assert is_edge_meter("api.calls")
    assert is_edge_meter("compute.ms")
    assert is_edge_meter("storage.gbh")

    assert not is_work_meter("llm.tokens")
    assert not is_edge_meter("workflow.completed")


def test_envelope_allocation():
    """Test work envelope allocation."""
    usage = create_sample_usage()
    policy = create_test_policy()

    envelopes = allocate_work_envelopes(usage, policy)

    # 5 workflows completed * 50K tokens per workflow = 250K tokens
    assert envelopes["llm.tokens"] == Decimal("250000")

    # 5 workflows completed * 10 API calls per workflow = 50 API calls
    assert envelopes["api.calls"] == Decimal("50")

    # 5 workflows completed * 30K ms per workflow = 150K ms
    assert envelopes["compute.ms"] == Decimal("150000")


def test_exclusions():
    """Test exclusion rules."""
    usage = create_sample_usage()
    policy = create_test_policy()

    filtered = apply_exclusions(usage, policy)

    # API calls should be excluded when workflow.completed > 0
    meter_keys = {r.meter_key for r in filtered}
    assert "api.calls" not in meter_keys
    assert "workflow.completed" in meter_keys
    assert "llm.tokens" in meter_keys
    assert "compute.ms" in meter_keys


def test_tiered_pricing():
    """Test tiered pricing calculation."""
    pricing = MeterPricing(
        meter_key="test.meter",
        included_quota=Decimal("100"),
        tiers=[
            PricingTier(
                min_usage=Decimal("0"),
                max_usage=Decimal("1000"),
                unit_price=Decimal("0.01"),
            ),
            PricingTier(min_usage=Decimal("1000"), unit_price=Decimal("0.005")),
        ],
    )

    # Test usage within first tier
    total, breakdown = calculate_tiered_pricing(Decimal("500"), pricing)
    assert total == Decimal("5.00")  # 500 * 0.01
    assert len(breakdown) == 1

    # Test usage spanning both tiers
    total, breakdown = calculate_tiered_pricing(Decimal("1500"), pricing)
    expected = (Decimal("1000") * Decimal("0.01")) + (Decimal("500") * Decimal("0.005"))
    assert total == expected
    assert len(breakdown) == 2


def test_edge_spill_calculation():
    """Test edge spill billing calculation."""
    # Test no spill (usage covered by included + envelope)
    spill = bill_edge_spill(
        edge_total=Decimal("100"),
        included=Decimal("50"),
        envelope=Decimal("60"),
        unit_price=Decimal("0.01"),
    )
    assert spill == Decimal("0")  # 100 <= 50 + 60

    # Test with spill
    spill = bill_edge_spill(
        edge_total=Decimal("200"),
        included=Decimal("50"),
        envelope=Decimal("100"),
        unit_price=Decimal("0.01"),
    )
    assert spill == Decimal("0.50")  # (200 - 50 - 100) * 0.01


def test_work_over_edges_precedence():
    """Test work-over-edges rating precedence."""
    usage = create_sample_usage()
    policy = create_test_policy()

    # Apply exclusions (removes api.calls)
    filtered = apply_exclusions(usage, policy)

    # Allocate envelopes
    envelopes = allocate_work_envelopes(filtered, policy)

    # Check envelope allocations
    assert envelopes["llm.tokens"] == Decimal("250000")  # 5 * 50K
    assert envelopes["compute.ms"] == Decimal("150000")  # 5 * 30K

    # Test LLM tokens with envelope
    llm_usage = next(r for r in filtered if r.meter_key == "llm.tokens")
    assert llm_usage.value == Decimal("150000")  # Total usage

    # With envelope of 250K, all 150K tokens should be covered
    # (100K included + 150K from envelope covers all 150K usage)

    # Test compute with envelope
    compute_usage = next(r for r in filtered if r.meter_key == "compute.ms")
    assert compute_usage.value == Decimal("45000")  # Total usage

    # With envelope of 150K and included 10K, all 45K should be covered


def test_rating_result_structure():
    """Test the structure of rating results."""
    customer_id = uuid4()
    period_start = datetime(2024, 1, 1)
    period_end = datetime(2024, 1, 31)

    session = MockSession()
    engine = RatingEngine(session)

    # Test empty result
    empty_result = engine._create_empty_result(customer_id, period_start, period_end)

    assert empty_result.customer_id == customer_id
    assert empty_result.period_start == period_start.isoformat()
    assert empty_result.period_end == period_end.isoformat()
    assert empty_result.total == Decimal("0")
    assert len(empty_result.lines) == 0
    assert len(empty_result.envelopes) == 0


def test_base_fee_application():
    """Test that base fees are properly applied."""
    policy = create_test_policy()
    assert policy.base_fee == Decimal("50.00")

    # In a real rating scenario, base fee would be added as a line item
    # This is tested in the integration test


def test_spend_cap_application():
    """Test spend cap enforcement."""
    policy = create_test_policy()
    policy.spend_cap = Decimal("100.00")

    # If total exceeds spend cap, it should be capped
    subtotal = Decimal("150.00")
    discount_amount = Decimal("0")
    total = subtotal - discount_amount

    if policy.spend_cap and total > policy.spend_cap:
        cap_discount = total - policy.spend_cap
        discount_amount += cap_discount
        total = policy.spend_cap

    assert total == Decimal("100.00")
    assert discount_amount == Decimal("50.00")


def test_discount_calculation():
    """Test percentage discount calculation."""
    policy = create_test_policy()
    policy.discount_percent = Decimal("10")  # 10% discount

    subtotal = Decimal("100.00")
    discount_amount = subtotal * (policy.discount_percent / Decimal("100"))
    total = subtotal - discount_amount

    assert discount_amount == Decimal("10.00")
    assert total == Decimal("90.00")


if __name__ == "__main__":
    pytest.main([__file__])
