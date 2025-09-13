"""Tests for usage alerts system."""

from datetime import datetime, timedelta
from decimal import Decimal
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from kachi.lib.models import Customer, MeterReading, RatedUsage
from kachi.lib.usage_alerts import (
    AlertConfig,
    AlertNotificationService,
    AlertSeverity,
    AlertType,
    UsageAlert,
    UsageAlertsManager,
    UsageMonitor,
)


@pytest.fixture
async def sample_customer(db_session: AsyncSession):
    """Create a sample customer for testing."""
    customer = Customer(
        lago_customer_id="test-alerts-customer",
        name="Alerts Test Customer",
        currency="USD",
    )
    db_session.add(customer)
    await db_session.commit()
    await db_session.refresh(customer)
    return customer


@pytest.fixture
async def sample_usage_data(db_session: AsyncSession, sample_customer):
    """Create sample usage data."""
    customer = sample_customer
    now = datetime.utcnow()
    period_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    # Create meter readings
    meter_readings = [
        MeterReading(
            customer_id=customer.id,
            meter_key="api.calls",
            window_start=period_start,
            window_end=period_start + timedelta(hours=1),
            value=Decimal("8500"),  # 85% of 10,000 limit
            src_event_ids=[],
        ),
        MeterReading(
            customer_id=customer.id,
            meter_key="llm.tokens",
            window_start=period_start,
            window_end=period_start + timedelta(hours=1),
            value=Decimal("950000"),  # 95% of 1,000,000 limit
            src_event_ids=[],
        ),
    ]

    for reading in meter_readings:
        db_session.add(reading)

    # Create rated usage (spend data)
    rated_usage = RatedUsage(
        customer_id=customer.id,
        period_start=period_start,
        period_end=now,
        items_json={"lines": []},
        subtotal=Decimal("450.00"),  # Current spend
        cogs=Decimal("135.00"),
        margin=Decimal("315.00"),
    )
    db_session.add(rated_usage)

    await db_session.commit()
    return {
        "customer": customer,
        "meter_readings": meter_readings,
        "rated_usage": rated_usage,
    }


class TestUsageMonitor:
    """Test usage monitoring functionality."""

    async def test_usage_threshold_alert(
        self, db_session: AsyncSession, sample_usage_data
    ):
        """Test usage threshold alerts."""
        monitor = UsageMonitor(db_session)
        customer = sample_usage_data["customer"]

        # Configure 80% threshold alert for API calls
        config = AlertConfig(
            customer_id=customer.id,
            meter_key="api.calls",
            alert_type=AlertType.USAGE_THRESHOLD,
            threshold_percentage=Decimal("80"),
        )
        monitor.add_alert_config(config)

        # Check alerts
        alerts = await monitor.check_usage_alerts(customer.id)

        assert len(alerts) == 1
        alert = alerts[0]
        assert alert.alert_type == AlertType.USAGE_THRESHOLD
        assert alert.meter_key == "api.calls"
        assert alert.severity == AlertSeverity.INFO  # 85% usage
        assert "85.0%" in alert.message

    async def test_critical_usage_alert(
        self, db_session: AsyncSession, sample_usage_data
    ):
        """Test critical usage alerts (>100%)."""
        monitor = UsageMonitor(db_session)
        customer = sample_usage_data["customer"]

        # Configure 90% threshold alert for LLM tokens (which is at 95%)
        config = AlertConfig(
            customer_id=customer.id,
            meter_key="llm.tokens",
            alert_type=AlertType.USAGE_THRESHOLD,
            threshold_percentage=Decimal("90"),
        )
        monitor.add_alert_config(config)

        alerts = await monitor.check_usage_alerts(customer.id)

        assert len(alerts) == 1
        alert = alerts[0]
        assert alert.severity == AlertSeverity.WARNING  # 95% usage
        assert "95.0%" in alert.message

    async def test_spend_threshold_alert(
        self, db_session: AsyncSession, sample_usage_data
    ):
        """Test spend threshold alerts."""
        monitor = UsageMonitor(db_session)
        customer = sample_usage_data["customer"]

        # Configure spend threshold at $400 (current spend is $450)
        config = AlertConfig(
            customer_id=customer.id,
            alert_type=AlertType.SPEND_THRESHOLD,
            threshold_amount=Decimal("400.00"),
        )
        monitor.add_alert_config(config)

        alerts = await monitor.check_usage_alerts(customer.id)

        assert len(alerts) == 1
        alert = alerts[0]
        assert alert.alert_type == AlertType.SPEND_THRESHOLD
        assert alert.current_usage == Decimal("450.00")
        assert alert.threshold == Decimal("400.00")

    async def test_spend_cap_alert(self, db_session: AsyncSession, sample_usage_data):
        """Test spend cap alerts."""
        monitor = UsageMonitor(db_session)
        customer = sample_usage_data["customer"]

        # Configure spend cap at $400 (current spend is $450, so cap exceeded)
        config = AlertConfig(
            customer_id=customer.id,
            alert_type=AlertType.SPEND_CAP,
            spend_cap=Decimal("400.00"),
        )
        monitor.add_alert_config(config)

        alerts = await monitor.check_usage_alerts(customer.id)

        assert len(alerts) == 1
        alert = alerts[0]
        assert alert.alert_type == AlertType.SPEND_CAP
        assert alert.severity == AlertSeverity.CRITICAL
        assert "SPEND CAP REACHED" in alert.message
        assert alert.metadata["cap_exceeded"] is True

    async def test_disabled_alerts(self, db_session: AsyncSession, sample_usage_data):
        """Test that disabled alerts are not triggered."""
        monitor = UsageMonitor(db_session)
        customer = sample_usage_data["customer"]

        # Configure disabled alert
        config = AlertConfig(
            customer_id=customer.id,
            meter_key="api.calls",
            alert_type=AlertType.USAGE_THRESHOLD,
            threshold_percentage=Decimal("80"),
            enabled=False,  # Disabled
        )
        monitor.add_alert_config(config)

        alerts = await monitor.check_usage_alerts(customer.id)
        assert len(alerts) == 0

    async def test_multiple_alerts(self, db_session: AsyncSession, sample_usage_data):
        """Test multiple alerts for the same customer."""
        monitor = UsageMonitor(db_session)
        customer = sample_usage_data["customer"]

        # Configure multiple alerts
        configs = [
            AlertConfig(
                customer_id=customer.id,
                meter_key="api.calls",
                alert_type=AlertType.USAGE_THRESHOLD,
                threshold_percentage=Decimal("80"),
            ),
            AlertConfig(
                customer_id=customer.id,
                alert_type=AlertType.SPEND_THRESHOLD,
                threshold_amount=Decimal("400.00"),
            ),
        ]

        for config in configs:
            monitor.add_alert_config(config)

        alerts = await monitor.check_usage_alerts(customer.id)

        assert len(alerts) == 2
        alert_types = {alert.alert_type for alert in alerts}
        assert AlertType.USAGE_THRESHOLD in alert_types
        assert AlertType.SPEND_THRESHOLD in alert_types


class TestAlertNotificationService:
    """Test alert notification functionality."""

    async def test_send_email_notification(self):
        """Test email notification sending."""
        service = AlertNotificationService()

        alert = UsageAlert(
            customer_id=uuid4(),
            alert_type=AlertType.USAGE_THRESHOLD,
            severity=AlertSeverity.WARNING,
            message="Test alert message",
            meter_key="api.calls",
        )

        results = await service.send_alert(alert, ["email"])
        assert results["email"] is True

    async def test_send_multiple_channels(self):
        """Test sending to multiple notification channels."""
        service = AlertNotificationService()

        alert = UsageAlert(
            customer_id=uuid4(),
            alert_type=AlertType.SPEND_CAP,
            severity=AlertSeverity.CRITICAL,
            message="Spend cap exceeded",
        )

        results = await service.send_alert(alert, ["email", "webhook", "slack"])
        assert all(results.values())
        assert len(results) == 3

    async def test_unknown_channel(self):
        """Test handling of unknown notification channels."""
        service = AlertNotificationService()

        alert = UsageAlert(
            customer_id=uuid4(),
            alert_type=AlertType.USAGE_THRESHOLD,
            severity=AlertSeverity.INFO,
            message="Test alert",
        )

        results = await service.send_alert(alert, ["unknown_channel"])
        assert results["unknown_channel"] is False


class TestUsageAlertsManager:
    """Test the main usage alerts manager."""

    async def test_configure_customer_alerts(
        self, db_session: AsyncSession, sample_customer
    ):
        """Test configuring customer alerts."""
        manager = UsageAlertsManager(db_session)
        customer = sample_customer

        alert_configs = [
            {
                "meter_key": "api.calls",
                "alert_type": "usage_threshold",
                "threshold_percentage": 80,
                "enabled": True,
            },
            {
                "alert_type": "spend_threshold",
                "threshold_amount": 500,
                "notification_channels": ["email", "slack"],
            },
        ]

        manager.configure_customer_alerts(customer.id, alert_configs)

        # Check that configs were added
        assert customer.id in manager.monitor.alert_configs
        assert len(manager.monitor.alert_configs[customer.id]) == 2

    async def test_check_and_send_alerts(
        self, db_session: AsyncSession, sample_usage_data
    ):
        """Test checking and sending alerts."""
        manager = UsageAlertsManager(db_session)
        customer = sample_usage_data["customer"]

        # Configure alerts
        alert_configs = [
            {
                "meter_key": "api.calls",
                "alert_type": "usage_threshold",
                "threshold_percentage": 80,
            }
        ]
        manager.configure_customer_alerts(customer.id, alert_configs)

        # Check and send alerts
        alerts = await manager.check_and_send_alerts(customer.id)

        assert len(alerts) == 1
        assert alerts[0].meter_key == "api.calls"

    async def test_get_usage_summary(self, db_session: AsyncSession, sample_usage_data):
        """Test getting usage summary."""
        manager = UsageAlertsManager(db_session)
        customer = sample_usage_data["customer"]

        summary = await manager.get_customer_usage_summary(customer.id)

        assert summary["customer_id"] == str(customer.id)
        assert summary["current_spend"] == Decimal("450.00")
        assert "meter_usage" in summary
        assert "api.calls" in summary["meter_usage"]

        # Check API calls usage
        api_usage = summary["meter_usage"]["api.calls"]
        assert api_usage["current_usage"] == Decimal("8500")
        assert api_usage["limit"] == Decimal("10000")
        assert api_usage["percentage"] == 85
        assert api_usage["status"] == "warning"  # 85% is warning level
