"""Customer usage alerts and spend cap system."""

import logging
from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from kachi.lib.models import MeterReading, RatedUsage

logger = logging.getLogger(__name__)


class AlertType(str, Enum):
    """Types of usage alerts."""

    USAGE_THRESHOLD = "usage_threshold"
    SPEND_THRESHOLD = "spend_threshold"
    SPEND_CAP = "spend_cap"
    ANOMALY = "anomaly"


class AlertSeverity(str, Enum):
    """Alert severity levels."""

    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


class AlertConfig:
    """Configuration for usage alerts."""

    def __init__(
        self,
        customer_id: UUID,
        meter_key: str | None = None,
        alert_type: AlertType = AlertType.USAGE_THRESHOLD,
        threshold_percentage: Decimal | None = None,
        threshold_amount: Decimal | None = None,
        spend_cap: Decimal | None = None,
        enabled: bool = True,
        notification_channels: list[str] | None = None,
    ):
        self.customer_id = customer_id
        self.meter_key = meter_key
        self.alert_type = alert_type
        self.threshold_percentage = threshold_percentage
        self.threshold_amount = threshold_amount
        self.spend_cap = spend_cap
        self.enabled = enabled
        self.notification_channels = notification_channels or ["email"]


class UsageAlert:
    """A usage alert instance."""

    def __init__(
        self,
        customer_id: UUID,
        alert_type: AlertType,
        severity: AlertSeverity,
        message: str,
        meter_key: str | None = None,
        current_usage: Decimal | None = None,
        threshold: Decimal | None = None,
        spend_cap: Decimal | None = None,
        metadata: dict[str, Any] | None = None,
        triggered_at: datetime | None = None,
    ):
        self.customer_id = customer_id
        self.alert_type = alert_type
        self.severity = severity
        self.message = message
        self.meter_key = meter_key
        self.current_usage = current_usage
        self.threshold = threshold
        self.spend_cap = spend_cap
        self.metadata = metadata or {}
        self.triggered_at = triggered_at or datetime.utcnow()


class UsageMonitor:
    """Monitor customer usage and trigger alerts."""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.alert_configs: dict[UUID, list[AlertConfig]] = {}

    def add_alert_config(self, config: AlertConfig) -> None:
        """Add an alert configuration for a customer."""
        if config.customer_id not in self.alert_configs:
            self.alert_configs[config.customer_id] = []
        self.alert_configs[config.customer_id].append(config)

    async def check_usage_alerts(
        self, customer_id: UUID, period_start: datetime | None = None
    ) -> list[UsageAlert]:
        """Check for usage alerts for a customer."""
        if customer_id not in self.alert_configs:
            return []

        alerts = []
        period_start = period_start or datetime.utcnow().replace(
            day=1, hour=0, minute=0, second=0, microsecond=0
        )
        period_end = datetime.utcnow()

        for config in self.alert_configs[customer_id]:
            if not config.enabled:
                continue

            if config.alert_type == AlertType.USAGE_THRESHOLD:
                alert = await self._check_usage_threshold(
                    config, period_start, period_end
                )
                if alert:
                    alerts.append(alert)

            elif config.alert_type == AlertType.SPEND_THRESHOLD:
                alert = await self._check_spend_threshold(
                    config, period_start, period_end
                )
                if alert:
                    alerts.append(alert)

            elif config.alert_type == AlertType.SPEND_CAP:
                alert = await self._check_spend_cap(config, period_start, period_end)
                if alert:
                    alerts.append(alert)

        return alerts

    async def _check_usage_threshold(
        self, config: AlertConfig, period_start: datetime, period_end: datetime
    ) -> UsageAlert | None:
        """Check usage threshold alerts."""
        if not config.meter_key or not config.threshold_percentage:
            return None

        # Get current usage for the meter
        current_usage = await self._get_meter_usage(
            config.customer_id, config.meter_key, period_start, period_end
        )

        # Get the usage limit (from pricing plan or configuration)
        usage_limit = await self._get_usage_limit(config.customer_id, config.meter_key)

        if not usage_limit or usage_limit == 0:
            return None

        usage_percentage = (current_usage / usage_limit) * 100

        if usage_percentage >= config.threshold_percentage:
            severity = self._determine_severity(usage_percentage)
            message = (
                f"Usage alert: {config.meter_key} is at {usage_percentage:.1f}% "
                f"({current_usage} of {usage_limit} limit)"
            )

            return UsageAlert(
                customer_id=config.customer_id,
                alert_type=config.alert_type,
                severity=severity,
                message=message,
                meter_key=config.meter_key,
                current_usage=current_usage,
                threshold=config.threshold_percentage,
                metadata={
                    "usage_limit": usage_limit,
                    "usage_percentage": usage_percentage,
                },
            )

        return None

    async def _check_spend_threshold(
        self, config: AlertConfig, period_start: datetime, period_end: datetime
    ) -> UsageAlert | None:
        """Check spend threshold alerts."""
        if not config.threshold_amount:
            return None

        # Get current spend for the period
        current_spend = await self._get_period_spend(
            config.customer_id, period_start, period_end
        )

        if current_spend >= config.threshold_amount:
            severity = AlertSeverity.WARNING
            if config.spend_cap and current_spend >= config.spend_cap * Decimal("0.9"):
                severity = AlertSeverity.CRITICAL

            message = (
                f"Spend alert: Current spend ${current_spend} has reached "
                f"threshold of ${config.threshold_amount}"
            )

            return UsageAlert(
                customer_id=config.customer_id,
                alert_type=config.alert_type,
                severity=severity,
                message=message,
                current_usage=current_spend,
                threshold=config.threshold_amount,
                spend_cap=config.spend_cap,
            )

        return None

    async def _check_spend_cap(
        self, config: AlertConfig, period_start: datetime, period_end: datetime
    ) -> UsageAlert | None:
        """Check spend cap alerts."""
        if not config.spend_cap:
            return None

        current_spend = await self._get_period_spend(
            config.customer_id, period_start, period_end
        )

        if current_spend >= config.spend_cap:
            message = (
                f"SPEND CAP REACHED: Current spend ${current_spend} has reached "
                f"the cap of ${config.spend_cap}. Usage may be throttled."
            )

            return UsageAlert(
                customer_id=config.customer_id,
                alert_type=config.alert_type,
                severity=AlertSeverity.CRITICAL,
                message=message,
                current_usage=current_spend,
                spend_cap=config.spend_cap,
                metadata={"cap_exceeded": True},
            )

        return None

    async def _get_meter_usage(
        self,
        customer_id: UUID,
        meter_key: str,
        period_start: datetime,
        period_end: datetime,
    ) -> Decimal:
        """Get total usage for a meter in the period."""
        result = await self.session.execute(
            select(MeterReading).where(
                MeterReading.customer_id == customer_id,
                MeterReading.meter_key == meter_key,
                MeterReading.window_start >= period_start,
                MeterReading.window_end <= period_end,
            )
        )
        readings = result.scalars().all()
        return sum(reading.value for reading in readings)

    async def _get_period_spend(
        self, customer_id: UUID, period_start: datetime, period_end: datetime
    ) -> Decimal:
        """Get total spend for a customer in the period."""
        result = await self.session.execute(
            select(RatedUsage).where(
                RatedUsage.customer_id == customer_id,
                RatedUsage.period_start >= period_start.isoformat(),
                RatedUsage.period_end <= period_end.isoformat(),
            )
        )
        rated_usage_records = result.scalars().all()
        return sum(record.subtotal for record in rated_usage_records)

    async def _get_usage_limit(self, customer_id: UUID, meter_key: str) -> Decimal:
        """Get usage limit for a meter (from pricing plan)."""
        # This would typically come from the customer's pricing plan
        # For now, return a default limit based on meter type
        default_limits = {
            "api.calls": Decimal("10000"),
            "llm.tokens": Decimal("1000000"),
            "compute.seconds": Decimal("3600"),
            "storage.gb": Decimal("100"),
            "workflow.runs": Decimal("1000"),
        }
        return default_limits.get(meter_key, Decimal("1000"))

    def _determine_severity(self, usage_percentage: Decimal) -> AlertSeverity:
        """Determine alert severity based on usage percentage."""
        if usage_percentage >= 100:
            return AlertSeverity.CRITICAL
        elif usage_percentage >= 90:
            return AlertSeverity.WARNING
        else:
            return AlertSeverity.INFO


class AlertNotificationService:
    """Service for sending alert notifications."""

    def __init__(self):
        self.notification_handlers = {
            "email": self._send_email_notification,
            "webhook": self._send_webhook_notification,
            "slack": self._send_slack_notification,
        }

    async def send_alert(
        self, alert: UsageAlert, channels: list[str] | None = None
    ) -> dict[str, bool]:
        """Send alert through specified channels."""
        channels = channels or ["email"]
        results = {}

        for channel in channels:
            if channel in self.notification_handlers:
                try:
                    success = await self.notification_handlers[channel](alert)
                    results[channel] = success
                    logger.info(f"Alert sent via {channel}: {alert.message}")
                except Exception as e:
                    logger.error(f"Failed to send alert via {channel}: {e}")
                    results[channel] = False
            else:
                logger.warning(f"Unknown notification channel: {channel}")
                results[channel] = False

        return results

    async def _send_email_notification(self, alert: UsageAlert) -> bool:
        """Send email notification (mock implementation)."""
        # In a real implementation, this would integrate with an email service
        logger.info(f"EMAIL: {alert.message}")
        return True

    async def _send_webhook_notification(self, alert: UsageAlert) -> bool:
        """Send webhook notification (mock implementation)."""
        # In a real implementation, this would make HTTP requests to configured webhooks
        logger.info(f"WEBHOOK: {alert.message}")
        return True

    async def _send_slack_notification(self, alert: UsageAlert) -> bool:
        """Send Slack notification (mock implementation)."""
        # In a real implementation, this would use Slack API
        logger.info(f"SLACK: {alert.message}")
        return True


class UsageAlertsManager:
    """Main manager for usage alerts system."""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.monitor = UsageMonitor(session)
        self.notification_service = AlertNotificationService()

    def configure_customer_alerts(
        self, customer_id: UUID, alert_configs: list[dict[str, Any]]
    ) -> None:
        """Configure alerts for a customer."""
        for config_data in alert_configs:
            config = AlertConfig(
                customer_id=customer_id,
                meter_key=config_data.get("meter_key"),
                alert_type=AlertType(config_data.get("alert_type", "usage_threshold")),
                threshold_percentage=Decimal(
                    str(config_data.get("threshold_percentage", 80))
                ),
                threshold_amount=Decimal(str(config_data.get("threshold_amount", 0)))
                if config_data.get("threshold_amount")
                else None,
                spend_cap=Decimal(str(config_data.get("spend_cap", 0)))
                if config_data.get("spend_cap")
                else None,
                enabled=config_data.get("enabled", True),
                notification_channels=config_data.get(
                    "notification_channels", ["email"]
                ),
            )
            self.monitor.add_alert_config(config)

    async def check_and_send_alerts(self, customer_id: UUID) -> list[UsageAlert]:
        """Check for alerts and send notifications."""
        alerts = await self.monitor.check_usage_alerts(customer_id)

        for alert in alerts:
            # Get notification channels for this customer/alert type
            channels = ["email"]  # Default, would come from customer preferences
            await self.notification_service.send_alert(alert, channels)

        return alerts

    async def get_customer_usage_summary(self, customer_id: UUID) -> dict[str, Any]:
        """Get usage summary for alert dashboard."""
        period_start = datetime.utcnow().replace(
            day=1, hour=0, minute=0, second=0, microsecond=0
        )
        period_end = datetime.utcnow()

        # Get current spend
        current_spend = await self.monitor._get_period_spend(
            customer_id, period_start, period_end
        )

        # Get usage by meter
        meter_usage = {}
        common_meters = ["api.calls", "llm.tokens", "compute.seconds", "workflow.runs"]

        for meter_key in common_meters:
            usage = await self.monitor._get_meter_usage(
                customer_id, meter_key, period_start, period_end
            )
            limit = await self.monitor._get_usage_limit(customer_id, meter_key)
            percentage = (usage / limit * 100) if limit > 0 else 0

            meter_usage[meter_key] = {
                "current_usage": usage,
                "limit": limit,
                "percentage": percentage,
                "status": "normal"
                if percentage < 80
                else "warning"
                if percentage < 100
                else "critical",
            }

        return {
            "customer_id": str(customer_id),
            "period_start": period_start.isoformat(),
            "period_end": period_end.isoformat(),
            "current_spend": current_spend,
            "meter_usage": meter_usage,
            "alerts_enabled": len(self.monitor.alert_configs.get(customer_id, [])),
        }
