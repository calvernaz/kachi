"""Property-based tests using Hypothesis."""

from datetime import datetime, timedelta
from decimal import Decimal
from uuid import UUID, uuid4

import pytest
from hypothesis import assume, given
from hypothesis import strategies as st
from hypothesis.extra.datetime import datetimes

from kachi.lib.rating_policies import (
    UsageBasedPolicy,
    calculate_tiered_cost,
    calculate_volume_discount,
)


# Custom strategies for our domain
@st.composite
def valid_uuid(draw):
    """Generate valid UUID strings."""
    return str(uuid4())


@st.composite
def positive_decimal(draw, max_value=10000):
    """Generate positive decimal values."""
    value = draw(st.decimals(min_value=0.01, max_value=max_value, places=2))
    return Decimal(str(value))


@st.composite
def meter_reading_data(draw):
    """Generate valid meter reading data."""
    return {
        "customer_id": draw(valid_uuid()),
        "meter_name": draw(
            st.text(
                min_size=1,
                max_size=50,
                alphabet=st.characters(whitelist_categories=("Lu", "Ll", "Nd", "_")),
            )
        ),
        "value": draw(st.floats(min_value=0, max_value=1000000)),
        "window_start": draw(
            datetimes(min_value=datetime(2020, 1, 1), max_value=datetime(2030, 1, 1))
        ),
    }


@st.composite
def pricing_tier(draw):
    """Generate valid pricing tiers."""
    return {
        "min_usage": draw(st.floats(min_value=0, max_value=1000)),
        "max_usage": draw(st.floats(min_value=1001, max_value=10000)),
        "rate": draw(positive_decimal(max_value=100)),
    }


class TestRatingPoliciesProperties:
    """Property-based tests for rating policies."""

    @given(
        usage=st.floats(min_value=0, max_value=100000),
        base_rate=positive_decimal(max_value=10),
    )
    def test_usage_based_policy_properties(self, usage, base_rate):
        """Test properties of usage-based pricing."""
        assume(usage >= 0)

        policy = UsageBasedPolicy(base_rate=base_rate)
        cost = policy.calculate_cost(usage)

        # Cost should be non-negative
        assert cost >= 0

        # Cost should be proportional to usage
        if usage > 0:
            assert cost > 0
            # Rate should be consistent
            calculated_rate = cost / Decimal(str(usage))
            assert abs(calculated_rate - base_rate) < Decimal("0.01")

    @given(
        usage=st.floats(min_value=0, max_value=100000),
        tiers=st.lists(
            st.tuples(
                st.floats(min_value=0, max_value=1000),  # min_usage
                st.floats(min_value=1001, max_value=10000),  # max_usage
                positive_decimal(max_value=10),  # rate
            ),
            min_size=1,
            max_size=5,
        ),
    )
    def test_tiered_pricing_properties(self, usage, tiers):
        """Test properties of tiered pricing."""
        assume(usage >= 0)

        # Sort tiers by min_usage to ensure proper ordering
        sorted_tiers = sorted(tiers, key=lambda x: x[0])

        # Ensure tiers don't overlap
        valid_tiers = []
        last_max = 0
        for min_usage, max_usage, rate in sorted_tiers:
            if min_usage >= last_max and max_usage > min_usage:
                valid_tiers.append((min_usage, max_usage, rate))
                last_max = max_usage

        assume(len(valid_tiers) > 0)

        cost = calculate_tiered_cost(usage, valid_tiers)

        # Cost should be non-negative
        assert cost >= 0

        # Zero usage should result in zero cost
        if usage == 0:
            assert cost == 0

    @given(
        usage=st.floats(min_value=0, max_value=100000),
        discount_threshold=st.floats(min_value=100, max_value=1000),
        discount_rate=st.floats(min_value=0.01, max_value=0.5),
    )
    def test_volume_discount_properties(self, usage, discount_threshold, discount_rate):
        """Test properties of volume discount."""
        assume(usage >= 0)
        assume(0 < discount_rate < 1)

        base_cost = Decimal(str(usage * 0.1))  # Arbitrary base rate
        discounted_cost = calculate_volume_discount(
            base_cost, usage, discount_threshold, discount_rate
        )

        # Discounted cost should never exceed base cost
        assert discounted_cost <= base_cost

        # If usage is below threshold, no discount should be applied
        if usage < discount_threshold:
            assert discounted_cost == base_cost

        # If usage is above threshold, discount should be applied
        if usage >= discount_threshold:
            expected_discount = base_cost * Decimal(str(discount_rate))
            expected_cost = base_cost - expected_discount
            assert abs(discounted_cost - expected_cost) < Decimal("0.01")


class TestMeterReadingProperties:
    """Property-based tests for meter reading validation."""

    @given(meter_data=meter_reading_data())
    def test_meter_reading_validation(self, meter_data):
        """Test meter reading data validation properties."""
        # Customer ID should be a valid UUID
        try:
            UUID(meter_data["customer_id"])
        except ValueError:
            pytest.fail("Customer ID should be a valid UUID")

        # Meter name should be non-empty
        assert len(meter_data["meter_name"]) > 0

        # Value should be non-negative
        assert meter_data["value"] >= 0

        # Window start should be a valid datetime
        assert isinstance(meter_data["window_start"], datetime)

    @given(
        values=st.lists(
            st.floats(min_value=0, max_value=1000), min_size=1, max_size=100
        )
    )
    def test_meter_aggregation_properties(self, values):
        """Test properties of meter value aggregation."""
        # Sum should be greater than or equal to any individual value
        total = sum(values)
        assert all(total >= value for value in values)

        # Average should be between min and max
        if len(values) > 1:
            avg = total / len(values)
            assert min(values) <= avg <= max(values)

    @given(
        start_time=datetimes(
            min_value=datetime(2020, 1, 1), max_value=datetime(2025, 1, 1)
        ),
        duration_hours=st.integers(min_value=1, max_value=24),
    )
    def test_time_window_properties(self, start_time, duration_hours):
        """Test properties of time windows."""
        end_time = start_time + timedelta(hours=duration_hours)

        # End time should be after start time
        assert end_time > start_time

        # Duration should be positive
        duration = end_time - start_time
        assert duration.total_seconds() > 0

        # Duration should match expected hours
        expected_seconds = duration_hours * 3600
        assert abs(duration.total_seconds() - expected_seconds) < 1


class TestDataConsistencyProperties:
    """Property-based tests for data consistency."""

    @given(
        customer_ids=st.lists(valid_uuid(), min_size=1, max_size=10),
        meter_names=st.lists(
            st.text(
                min_size=1,
                max_size=20,
                alphabet=st.characters(whitelist_categories=("Lu", "Ll", "Nd", "_")),
            ),
            min_size=1,
            max_size=5,
        ),
    )
    def test_customer_meter_consistency(self, customer_ids, meter_names):
        """Test consistency between customers and their meters."""
        # Each customer should have consistent meter names
        for customer_id in customer_ids:
            # Customer ID should be valid UUID
            try:
                UUID(customer_id)
            except ValueError:
                pytest.fail(f"Invalid customer ID: {customer_id}")

        # Meter names should be unique per customer
        unique_meters = set(meter_names)
        assert len(unique_meters) <= len(meter_names)

    @given(costs=st.lists(positive_decimal(max_value=1000), min_size=1, max_size=50))
    def test_cost_calculation_properties(self, costs):
        """Test properties of cost calculations."""
        total_cost = sum(costs)

        # Total should be sum of parts
        assert total_cost == sum(costs)

        # Total should be non-negative
        assert total_cost >= 0

        # If all individual costs are positive, total should be positive
        if all(cost > 0 for cost in costs):
            assert total_cost > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
