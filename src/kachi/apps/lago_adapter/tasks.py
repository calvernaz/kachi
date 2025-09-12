"""Celery tasks for Lago integration."""

import asyncio
import logging
import os
from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from celery import Celery
from sqlalchemy import select

from kachi.apps.lago_adapter.main import create_lago_adapter
from kachi.lib.db import get_session
from kachi.lib.models import Customer, RatedUsage
from kachi.lib.rating_policies import RatedLine, RatingResult

logger = logging.getLogger(__name__)

# Celery configuration
celery_app = Celery(
    "lago_adapter",
    broker=os.getenv("REDIS_URL", "redis://localhost:6379/0"),
    backend=os.getenv("REDIS_URL", "redis://localhost:6379/0"),
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=30 * 60,  # 30 minutes
    task_soft_time_limit=25 * 60,  # 25 minutes
    worker_prefetch_multiplier=1,
    task_acks_late=True,
    worker_disable_rate_limits=False,
    task_compression="gzip",
    result_compression="gzip",
)

# Periodic tasks
celery_app.conf.beat_schedule = {
    "sync-invoices-hourly": {
        "task": "lago_adapter.sync_invoices",
        "schedule": 3600.0,  # Every hour
    },
    "push-pending-usage-every-15min": {
        "task": "lago_adapter.push_pending_usage",
        "schedule": 900.0,  # Every 15 minutes
    },
    "setup-new-customers-daily": {
        "task": "lago_adapter.setup_new_customers",
        "schedule": 86400.0,  # Daily
    },
}


@celery_app.task(
    autoretry_for=(Exception,),
    retry_kwargs={"max_retries": 3, "countdown": 60},
)
def sync_customer_to_lago(customer_id: str) -> dict[str, Any]:
    """Sync a customer to Lago."""
    try:

        async def _sync():
            async with get_session() as session:
                lago_adapter = create_lago_adapter(
                    session,
                    api_key=os.getenv("LAGO_API_KEY"),
                    api_url=os.getenv("LAGO_API_URL", "https://api.getlago.com"),
                )

                success = await lago_adapter.sync_customer(UUID(customer_id))
                return {"success": success, "customer_id": customer_id}

        return asyncio.run(_sync())

    except Exception as e:
        logger.error(f"Failed to sync customer {customer_id} to Lago: {e}")
        raise


@celery_app.task(
    autoretry_for=(Exception,),
    retry_kwargs={"max_retries": 3, "countdown": 60},
)
def push_rated_usage_to_lago(rated_usage_id: int) -> dict[str, Any]:
    """Push rated usage to Lago."""
    try:

        async def _push():
            async with get_session() as session:
                # Get the rated usage
                result = await session.execute(
                    select(RatedUsage).where(RatedUsage.id == rated_usage_id)
                )
                rated_usage = result.scalar_one_or_none()

                if not rated_usage:
                    return {"success": False, "error": "Rated usage not found"}

                if rated_usage.lago_pushed_at:
                    return {"success": True, "message": "Already pushed to Lago"}

                # Convert to rating result format
                rating_result = RatingResult(
                    customer_id=str(rated_usage.customer_id),
                    period_start=rated_usage.period_start.isoformat(),
                    period_end=rated_usage.period_end.isoformat(),
                    lines=[
                        RatedLine(
                            meter_key=line["meter_key"],
                            usage_quantity=line["usage_quantity"],
                            billable_quantity=line["billable_quantity"],
                            unit_price=line["unit_price"],
                            amount=line["amount"],
                            line_type=line["line_type"],
                            description=line["description"],
                        )
                        for line in rated_usage.usage_lines
                    ],
                    total_amount=rated_usage.total_amount,
                    base_fee=rated_usage.base_fee,
                    discount_amount=rated_usage.discount_amount,
                    final_amount=rated_usage.final_amount,
                )

                lago_adapter = create_lago_adapter(
                    session,
                    api_key=os.getenv("LAGO_API_KEY"),
                    api_url=os.getenv("LAGO_API_URL", "https://api.getlago.com"),
                )

                success = await lago_adapter.push_rated_usage(rating_result)

                if success:
                    # Mark as pushed
                    rated_usage.lago_pushed_at = datetime.utcnow()
                    await session.commit()

                return {"success": success, "rated_usage_id": rated_usage_id}

        return asyncio.run(_push())

    except Exception as e:
        logger.error(f"Failed to push rated usage {rated_usage_id} to Lago: {e}")
        raise


@celery_app.task(
    autoretry_for=(Exception,),
    retry_kwargs={"max_retries": 2, "countdown": 300},
)
def sync_invoices() -> dict[str, Any]:
    """Sync invoice status from Lago."""
    try:

        async def _sync():
            async with get_session() as session:
                lago_adapter = create_lago_adapter(
                    session,
                    api_key=os.getenv("LAGO_API_KEY"),
                    api_url=os.getenv("LAGO_API_URL", "https://api.getlago.com"),
                )

                synced_invoices = await lago_adapter.sync_invoices()
                return {
                    "success": True,
                    "synced_count": len(synced_invoices),
                    "invoices": synced_invoices,
                }

        return asyncio.run(_sync())

    except Exception as e:
        logger.error(f"Failed to sync invoices: {e}")
        raise


@celery_app.task(
    autoretry_for=(Exception,),
    retry_kwargs={"max_retries": 2, "countdown": 300},
)
def push_pending_usage() -> dict[str, Any]:
    """Push any pending rated usage to Lago."""
    try:

        async def _push():
            async with get_session() as session:
                # Find rated usage that hasn't been pushed to Lago
                result = await session.execute(
                    select(RatedUsage)
                    .where(RatedUsage.lago_pushed_at.is_(None))
                    .limit(100)  # Process in batches
                )
                pending_usage = result.scalars().all()

                pushed_count = 0
                for usage in pending_usage:
                    try:
                        # Queue individual push tasks
                        push_rated_usage_to_lago.delay(usage.id)
                        pushed_count += 1
                    except Exception as e:
                        logger.error(f"Failed to queue push for usage {usage.id}: {e}")

                return {
                    "success": True,
                    "queued_count": pushed_count,
                    "total_pending": len(pending_usage),
                }

        return asyncio.run(_push())

    except Exception as e:
        logger.error(f"Failed to push pending usage: {e}")
        raise


@celery_app.task(
    autoretry_for=(Exception,),
    retry_kwargs={"max_retries": 2, "countdown": 300},
)
def setup_new_customers() -> dict[str, Any]:
    """Set up any new customers in Lago."""
    try:

        async def _setup():
            async with get_session() as session:
                # Find customers without Lago customer IDs
                result = await session.execute(
                    select(Customer)
                    .where(Customer.lago_customer_id.is_(None))
                    .limit(50)  # Process in batches
                )
                new_customers = result.scalars().all()

                setup_count = 0
                for customer in new_customers:
                    try:
                        # Queue individual sync tasks
                        sync_customer_to_lago.delay(str(customer.id))
                        setup_count += 1
                    except Exception as e:
                        logger.error(
                            f"Failed to queue setup for customer {customer.id}: {e}"
                        )

                return {
                    "success": True,
                    "queued_count": setup_count,
                    "total_new": len(new_customers),
                }

        return asyncio.run(_setup())

    except Exception as e:
        logger.error(f"Failed to setup new customers: {e}")
        raise


@celery_app.task(
    autoretry_for=(Exception,),
    retry_kwargs={"max_retries": 3, "countdown": 60},
)
def handle_lago_webhook(event_type: str, event_data: dict[str, Any]) -> dict[str, Any]:
    """Handle incoming Lago webhook events."""
    try:

        async def _handle():
            async with get_session() as session:
                lago_adapter = create_lago_adapter(
                    session,
                    api_key=os.getenv("LAGO_API_KEY"),
                    api_url=os.getenv("LAGO_API_URL", "https://api.getlago.com"),
                )

                success = await lago_adapter.handle_webhook_event(
                    event_type, event_data
                )
                return {
                    "success": success,
                    "event_type": event_type,
                    "processed_at": datetime.utcnow().isoformat(),
                }

        return asyncio.run(_handle())

    except Exception as e:
        logger.error(f"Failed to handle webhook {event_type}: {e}")
        raise


@celery_app.task(
    autoretry_for=(Exception,),
    retry_kwargs={"max_retries": 3, "countdown": 60},
)
def push_success_fee(
    customer_id: str, outcome_type: str, amount: float, description: str
) -> dict[str, Any]:
    """Push a success fee to Lago."""
    try:

        async def _push():
            async with get_session() as session:
                lago_adapter = create_lago_adapter(
                    session,
                    api_key=os.getenv("LAGO_API_KEY"),
                    api_url=os.getenv("LAGO_API_URL", "https://api.getlago.com"),
                )

                success = await lago_adapter.push_success_fee(
                    customer_id=UUID(customer_id),
                    outcome_type=outcome_type,
                    amount=Decimal(str(amount)),
                    description=description,
                )

                return {
                    "success": success,
                    "customer_id": customer_id,
                    "outcome_type": outcome_type,
                    "amount": amount,
                }

        return asyncio.run(_push())

    except Exception as e:
        logger.error(f"Failed to push success fee: {e}")
        raise


@celery_app.task(
    autoretry_for=(Exception,),
    retry_kwargs={"max_retries": 1, "countdown": 60},
)
def setup_lago_catalog() -> dict[str, Any]:
    """Set up the Lago catalog (metrics, plans, etc.)."""
    try:

        async def _setup():
            async with get_session() as session:
                lago_adapter = create_lago_adapter(
                    session,
                    api_key=os.getenv("LAGO_API_KEY"),
                    api_url=os.getenv("LAGO_API_URL", "https://api.getlago.com"),
                )

                # Setup billing metrics
                metrics_success = await lago_adapter.setup_billing_metrics()

                # Create default plan
                plan_success = await lago_adapter.create_default_plan()

                return {
                    "success": metrics_success and plan_success,
                    "metrics_setup": metrics_success,
                    "plan_setup": plan_success,
                }

        return asyncio.run(_setup())

    except Exception as e:
        logger.error(f"Failed to setup Lago catalog: {e}")
        raise


@celery_app.task
def health_check() -> dict[str, Any]:
    """Health check task for monitoring."""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "service": "lago_adapter",
    }
