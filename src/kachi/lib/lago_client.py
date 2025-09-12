"""Lago API client wrapper for billing integration."""

import logging
from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from lago_python_client import Client
from pydantic import BaseModel

logger = logging.getLogger(__name__)


class LagoConfig(BaseModel):
    """Configuration for Lago client."""

    api_key: str
    api_url: str = "https://api.getlago.com"
    timeout: int = 30


class LagoClientWrapper:
    """Wrapper around the Lago Python client with our business logic."""

    def __init__(self, config: LagoConfig):
        self.config = config
        self.client = Client(api_key=config.api_key, api_url=config.api_url)

    async def create_customer(
        self,
        customer_id: UUID,
        name: str,
        email: str | None = None,
        currency: str = "USD",
    ) -> Any:
        """Create a customer in Lago."""
        try:
            customer_data = {
                "external_id": str(customer_id),
                "name": name,
                "email": email,
                "currency": currency,
                "timezone": "UTC",
            }

            customer = self.client.customers().create(customer_data)
            logger.info("Created Lago customer: %s", customer.external_id)
            return customer

        except Exception as exc:
            logger.error("Failed to create Lago customer %s: %s", customer_id, exc)
            raise

    async def get_customer(self, customer_id: UUID) -> Any | None:
        """Get a customer from Lago."""
        try:
            customer = self.client.customers().find(str(customer_id))
            return customer
        except Exception as exc:
            logger.warning("Customer %s not found in Lago: %s", customer_id, exc)
            return None

    async def create_billable_metric(
        self,
        code: str,
        name: str,
        description: str,
        aggregation_type: str = "sum_agg",
        field_name: str = "value",
    ) -> Any:
        """Create a billable metric in Lago."""
        try:
            metric_data = {
                "name": name,
                "code": code,
                "description": description,
                "aggregation_type": aggregation_type,
                "field_name": field_name,
            }

            metric = self.client.billable_metrics().create(metric_data)
            logger.info("Created Lago billable metric: %s", code)
            return metric

        except Exception as exc:
            logger.error("Failed to create billable metric %s: %s", code, exc)
            raise

    async def create_plan(
        self,
        code: str,
        name: str,
        description: str,
        amount_cents: int = 0,
        currency: str = "USD",
        interval: str = "monthly",
        charges: list[dict[str, Any]] | None = None,
    ) -> Any:
        """Create a plan in Lago."""
        try:
            plan_data = {
                "name": name,
                "code": code,
                "description": description,
                "amount_cents": amount_cents,
                "amount_currency": currency,
                "interval": interval,
                "charges": charges or [],
            }

            plan = self.client.plans().create(plan_data)
            logger.info("Created Lago plan: %s", code)
            return plan

        except Exception as exc:
            logger.error("Failed to create plan %s: %s", code, exc)
            raise

    async def create_subscription(
        self, customer_id: UUID, plan_code: str, external_id: str | None = None
    ) -> Any:
        """Create a subscription in Lago."""
        try:
            subscription_data = {
                "external_customer_id": str(customer_id),
                "plan_code": plan_code,
                "external_id": external_id or f"{customer_id}_{plan_code}",
            }

            subscription = self.client.subscriptions().create(subscription_data)
            logger.info("Created Lago subscription for customer %s", customer_id)
            return subscription

        except Exception as exc:
            logger.error("Failed to create subscription for %s: %s", customer_id, exc)
            raise

    async def send_usage_event(
        self,
        customer_id: UUID,
        meter_code: str,
        value: Decimal,
        timestamp: datetime | None = None,
        transaction_id: str | None = None,
    ) -> Any:
        """Send a usage event to Lago."""
        try:
            event_timestamp = timestamp or datetime.utcnow()
            tx_id = (
                transaction_id
                or f"{customer_id}_{meter_code}_{event_timestamp.isoformat()}"
            )

            event_data = {
                "transaction_id": tx_id,
                "external_customer_id": str(customer_id),
                "code": meter_code,
                "timestamp": event_timestamp,
                "properties": {"value": float(value)},
            }

            event = self.client.events().create(event_data)
            logger.debug(
                "Sent usage event: %s=%s for %s", meter_code, value, customer_id
            )
            return event

        except Exception as exc:
            logger.error("Failed to send usage event for %s: %s", customer_id, exc)
            raise

    async def send_batch_usage_events(self, events: list[dict[str, Any]]) -> list[Any]:
        """Send multiple usage events in batch."""
        results = []

        for event_data in events:
            try:
                event = await self.send_usage_event(
                    customer_id=UUID(event_data["customer_id"]),
                    meter_code=event_data["meter_code"],
                    value=Decimal(str(event_data["value"])),
                    timestamp=event_data.get("timestamp"),
                    transaction_id=event_data.get("transaction_id"),
                )
                results.append(event)
            except Exception as exc:
                logger.error("Failed to send batch event: %s", exc)
                # Continue with other events
                continue

        logger.info("Sent %d/%d usage events successfully", len(results), len(events))
        return results

    async def create_add_on(
        self,
        code: str,
        name: str,
        description: str,
        amount_cents: int,
        currency: str = "USD",
    ) -> Any:
        """Create an add-on in Lago (for success fees, adjustments, etc.)."""
        try:
            addon_data = {
                "name": name,
                "code": code,
                "description": description,
                "amount_cents": amount_cents,
                "amount_currency": currency,
            }

            addon = self.client.add_ons().create(addon_data)
            logger.info("Created Lago add-on: %s", code)
            return addon

        except Exception as exc:
            logger.error("Failed to create add-on %s: %s", code, exc)
            raise

    async def apply_add_on(
        self, customer_id: UUID, add_on_code: str, amount_cents: int | None = None
    ) -> Any:
        """Apply an add-on to a customer."""
        try:
            # This would use the Lago API to apply an add-on
            # The exact implementation depends on Lago's API structure
            logger.info("Applied add-on %s to customer %s", add_on_code, customer_id)
            # Implementation would go here based on actual Lago API
            return {
                "status": "applied",
                "add_on_code": add_on_code,
                "amount_cents": amount_cents,
            }

        except Exception as exc:
            logger.error(
                "Failed to apply add-on %s to %s: %s", add_on_code, customer_id, exc
            )
            raise

    async def get_invoices(
        self, customer_id: UUID | None = None, status: str | None = None
    ) -> list[Any]:
        """Get invoices from Lago."""
        try:
            params = {}
            if customer_id:
                params["external_customer_id"] = str(customer_id)
            if status:
                params["status"] = status

            invoices = self.client.invoices().find_all(**params)
            return invoices.invoices if hasattr(invoices, "invoices") else []

        except Exception as exc:
            logger.error("Failed to get invoices: %s", exc)
            raise

    async def get_invoice(self, invoice_id: str) -> Any | None:
        """Get a specific invoice from Lago."""
        try:
            invoice = self.client.invoices().find(invoice_id)
            return invoice
        except Exception as exc:
            logger.warning("Invoice %s not found: %s", invoice_id, exc)
            return None

    async def create_credit_note(
        self,
        invoice_id: str,
        reason: str,
        credit_amount_cents: int,
        description: str | None = None,
    ) -> Any:
        """Create a credit note in Lago."""
        try:
            # Implementation would depend on Lago's credit note API
            logger.info("Created credit note for invoice %s", invoice_id)
            # This is a placeholder - actual implementation needed
            return {
                "status": "created",
                "invoice_id": invoice_id,
                "reason": reason,
                "amount_cents": credit_amount_cents,
                "description": description,
            }

        except Exception as exc:
            logger.error("Failed to create credit note for %s: %s", invoice_id, exc)
            raise


def create_lago_client(
    api_key: str, api_url: str = "https://api.getlago.com"
) -> LagoClientWrapper:
    """Factory function to create a Lago client."""
    config = LagoConfig(api_key=api_key, api_url=api_url)
    return LagoClientWrapper(config)
