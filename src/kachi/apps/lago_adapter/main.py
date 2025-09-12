"""Main Lago adapter for billing integration."""

import contextlib
import logging
from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from kachi.lib.lago_client import LagoClientWrapper, create_lago_client
from kachi.lib.models import Customer
from kachi.lib.rating_policies import RatingResult

logger = logging.getLogger(__name__)


class LagoAdapter:
    """Adapter for integrating with Lago billing platform."""

    def __init__(self, session: AsyncSession, lago_client: LagoClientWrapper):
        self.session = session
        self.lago_client = lago_client

    async def sync_customer(self, customer_id: UUID) -> bool:
        """Sync a customer to Lago."""
        try:
            # Get customer from our database
            result = await self.session.execute(
                select(Customer).where(Customer.id == customer_id)
            )
            customer = result.scalar_one_or_none()

            if not customer:
                logger.error("Customer %s not found in database", customer_id)
                return False

            # Check if customer exists in Lago
            lago_customer = await self.lago_client.get_customer(customer_id)

            if not lago_customer:
                # Create customer in Lago
                lago_customer = await self.lago_client.create_customer(
                    customer_id=customer.id,
                    name=customer.name,
                    email=getattr(customer, "email", None),
                    currency=customer.currency,
                )

                # Update our customer record with Lago customer ID
                customer.lago_customer_id = lago_customer.external_id
                await self.session.commit()

            logger.info("Customer %s synced to Lago", customer_id)
            return True

        except Exception as e:
            logger.error("Failed to sync customer %s to Lago: %s", customer_id, e)
            return False

    async def setup_billing_metrics(self) -> bool:
        """Set up billable metrics in Lago for our meters."""
        try:
            # Define our standard meters
            metrics = [
                {
                    "code": "workflow_completed",
                    "name": "Workflows Completed",
                    "description": "Number of completed workflows",
                    "aggregation_type": "sum_agg",
                },
                {
                    "code": "llm_tokens",
                    "name": "LLM Tokens",
                    "description": "Total LLM tokens consumed",
                    "aggregation_type": "sum_agg",
                },
                {
                    "code": "api_calls",
                    "name": "API Calls",
                    "description": "Number of API calls made",
                    "aggregation_type": "sum_agg",
                },
                {
                    "code": "compute_ms",
                    "name": "Compute Time",
                    "description": "Compute time in milliseconds",
                    "aggregation_type": "sum_agg",
                },
                {
                    "code": "storage_gbh",
                    "name": "Storage GB-Hours",
                    "description": "Storage usage in GB-hours",
                    "aggregation_type": "sum_agg",
                },
                {
                    "code": "outcome_ticket_resolved",
                    "name": "Tickets Resolved",
                    "description": "Number of support tickets resolved",
                    "aggregation_type": "sum_agg",
                },
            ]

            for metric_config in metrics:
                try:
                    await self.lago_client.create_billable_metric(
                        code=metric_config["code"],
                        name=metric_config["name"],
                        description=metric_config["description"],
                        aggregation_type=metric_config["aggregation_type"],
                    )
                except Exception as e:
                    # Metric might already exist
                    logger.warning(
                        f"Metric {metric_config['code']} may already exist: {e}"
                    )

            logger.info("Billing metrics setup completed")
            return True

        except Exception as e:
            logger.error(f"Failed to setup billing metrics: {e}")
            return False

    async def create_default_plan(self) -> bool:
        """Create a default plan in Lago."""
        try:
            # Define charges for each meter
            charges = [
                {
                    "billable_metric_code": "workflow_completed",
                    "charge_model": "standard",
                    "properties": {"amount": "0.50"},  # $0.50 per workflow
                },
                {
                    "billable_metric_code": "llm_tokens",
                    "charge_model": "graduated",
                    "properties": {
                        "graduated_ranges": [
                            {
                                "from_value": 0,
                                "to_value": 1000000,
                                "per_unit_amount": "0.000015",  # $0.015 per 1K tokens
                                "flat_amount": "0",
                            },
                            {
                                "from_value": 1000001,
                                "to_value": None,
                                "per_unit_amount": "0.000010",  # $0.010 per 1K tokens for higher usage
                                "flat_amount": "0",
                            },
                        ]
                    },
                },
                {
                    "billable_metric_code": "api_calls",
                    "charge_model": "standard",
                    "properties": {"amount": "0.001"},  # $0.001 per API call
                },
            ]

            await self.lago_client.create_plan(
                code="kachi_default",
                name="Kachi Default Plan",
                description="Default dual-rail billing plan",
                amount_cents=9900,  # $99 base fee
                currency="USD",
                interval="monthly",
                charges=charges,
            )

            logger.info("Default plan created in Lago")
            return True

        except Exception as e:
            logger.error(f"Failed to create default plan: {e}")
            return False

    async def push_rated_usage(self, rating_result: RatingResult) -> bool:
        """Push rated usage to Lago as usage events."""
        try:
            customer_id = rating_result.customer_id
            if isinstance(customer_id, str):
                customer_id = UUID(customer_id)

            # Ensure customer exists in Lago
            await self.sync_customer(customer_id)

            # Convert our rated lines to Lago usage events
            events = []

            for line in rating_result.lines:
                if line.line_type == "base_fee":
                    # Base fees are handled by the plan, skip
                    continue

                if line.billable_quantity > 0:
                    # Only send billable quantities to Lago
                    # This implements "Pattern A" from the plan
                    events.append(
                        {
                            "customer_id": str(customer_id),
                            "meter_code": self._map_meter_to_lago_code(line.meter_key),
                            "value": line.billable_quantity,
                            "timestamp": datetime.fromisoformat(
                                rating_result.period_start
                            ),
                            "transaction_id": f"{customer_id!s}_{line.meter_key}_{rating_result.period_start}",
                        }
                    )

            if events:
                await self.lago_client.send_batch_usage_events(events)
                logger.info(
                    "Pushed %d usage events to Lago for customer %s",
                    len(events),
                    customer_id,
                )
            else:
                logger.info("No billable usage to push for customer %s", customer_id)

            return True

        except Exception as e:
            logger.error(f"Failed to push rated usage to Lago: {e}")
            return False

    async def push_success_fee(
        self, customer_id: UUID, outcome_type: str, amount: Decimal, description: str
    ) -> bool:
        """Push a success fee as an add-on to Lago."""
        try:
            # Create or get the success fee add-on
            addon_code = f"success_fee_{outcome_type}"

            with contextlib.suppress(Exception):
                # Add-on might already exist, ignore creation errors
                await self.lago_client.create_add_on(
                    code=addon_code,
                    name=f"Success Fee - {outcome_type.title()}",
                    description=description or f"Success fee for {outcome_type}",
                    amount_cents=int(amount * 100),  # Convert to cents
                )

            # Apply the add-on to the customer
            await self.lago_client.apply_add_on(
                customer_id=customer_id,
                add_on_code=addon_code,
                amount_cents=int(amount * 100),
            )

            logger.info(f"Applied success fee ${amount} to customer {customer_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to push success fee: {e}")
            return False

    def _map_meter_to_lago_code(self, meter_key: str) -> str:
        """Map our internal meter keys to Lago billable metric codes."""
        # Convert dots to underscores for Lago compatibility
        return meter_key.replace(".", "_")

    async def handle_webhook_event(
        self, event_type: str, event_data: dict[str, Any]
    ) -> bool:
        """Handle incoming webhook events from Lago."""
        try:
            if event_type == "invoice.created":
                return await self._handle_invoice_created(event_data)
            elif event_type == "invoice.finalized":
                return await self._handle_invoice_finalized(event_data)
            elif event_type == "credit_note.created":
                return await self._handle_credit_note_created(event_data)
            else:
                logger.warning(f"Unknown webhook event type: {event_type}")
                return False

        except Exception as e:
            logger.error(f"Failed to handle webhook event {event_type}: {e}")
            return False

    async def _handle_invoice_created(self, event_data: dict[str, Any]) -> bool:
        """Handle invoice.created webhook."""
        invoice = event_data.get("invoice", {})
        customer_id = invoice.get("external_customer_id")

        if customer_id:
            logger.info(f"Invoice created for customer {customer_id}")
            # Update our records, send notifications, etc.

        return True

    async def _handle_invoice_finalized(self, event_data: dict[str, Any]) -> bool:
        """Handle invoice.finalized webhook."""
        invoice = event_data.get("invoice", {})
        customer_id = invoice.get("external_customer_id")

        if customer_id:
            logger.info(f"Invoice finalized for customer {customer_id}")
            # Trigger payment collection, send final invoice, etc.

        return True

    async def _handle_credit_note_created(self, event_data: dict[str, Any]) -> bool:
        """Handle credit_note.created webhook."""
        credit_note = event_data.get("credit_note", {})
        customer_id = credit_note.get("external_customer_id")

        if customer_id:
            logger.info(f"Credit note created for customer {customer_id}")
            # Update customer balance, send notification, etc.

        return True


def create_lago_adapter(
    session: AsyncSession, api_key: str, api_url: str = "https://api.getlago.com"
) -> LagoAdapter:
    """Factory function to create a Lago adapter."""
    lago_client = create_lago_client(api_key, api_url)
    return LagoAdapter(session, lago_client)
