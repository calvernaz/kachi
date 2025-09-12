"""Celery tasks for background event processing."""

import asyncio
from datetime import datetime, timedelta
from typing import Any
from uuid import UUID

import structlog
from celery import Celery

from kachi.apps.deriver.main import EventProcessor
from kachi.lib.db import get_session

logger = structlog.get_logger()

# Configure Celery
celery_app = Celery(
    "kachi_deriver",
    broker="redis://localhost:6379/0",
    backend="redis://localhost:6379/0",
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

# Periodic task schedule
celery_app.conf.beat_schedule = {
    "process-events-every-5-minutes": {
        "task": "kachi.apps.deriver.tasks.process_recent_events",
        "schedule": 300.0,  # 5 minutes
    },
    "detect-anomalies-hourly": {
        "task": "kachi.apps.deriver.tasks.detect_anomalies",
        "schedule": 3600.0,  # 1 hour
    },
    "cleanup-old-events-daily": {
        "task": "kachi.apps.deriver.tasks.cleanup_old_events",
        "schedule": 86400.0,  # 24 hours
        "kwargs": {"days_to_keep": 90},
    },
}


def run_async_task(coro):
    """Helper to run async functions in Celery tasks."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


@celery_app.task(bind=True, max_retries=3)
def process_recent_events(self, hours_back: int = 2) -> dict[str, Any]:
    """Process recent events into meter readings."""
    try:

        async def _process():
            async with get_session() as session:
                processor = EventProcessor(session)
                cutoff_time = datetime.utcnow() - timedelta(hours=hours_back)
                return await processor.process_events_batch(from_time=cutoff_time)

        result = run_async_task(_process())

        logger.info("Processed recent events", task_id=self.request.id, **result)

        return result

    except Exception as exc:
        logger.error(
            "Failed to process recent events",
            task_id=self.request.id,
            error=str(exc),
            exc_info=True,
        )

        # Retry with exponential backoff
        countdown = 2**self.request.retries * 60  # 1, 2, 4 minutes
        raise self.retry(exc=exc, countdown=countdown)


@celery_app.task(bind=True, max_retries=2)
def process_customer_events(
    self, customer_id: str, from_time: str, to_time: str
) -> dict[str, Any]:
    """Process events for a specific customer and time range."""
    try:

        async def _process():
            async with get_session() as session:
                processor = EventProcessor(session)
                return await processor.process_events_batch(
                    customer_id=UUID(customer_id),
                    from_time=datetime.fromisoformat(from_time),
                    to_time=datetime.fromisoformat(to_time),
                )

        result = run_async_task(_process())

        logger.info(
            "Processed customer events",
            task_id=self.request.id,
            customer_id=customer_id,
            **result,
        )

        return result

    except Exception as exc:
        logger.error(
            "Failed to process customer events",
            task_id=self.request.id,
            customer_id=customer_id,
            error=str(exc),
            exc_info=True,
        )

        countdown = 2**self.request.retries * 120  # 2, 4 minutes
        raise self.retry(exc=exc, countdown=countdown)


@celery_app.task(bind=True, max_retries=2)
def reprocess_customer_period(
    self, customer_id: str, start_date: str, end_date: str
) -> dict[str, Any]:
    """Reprocess all events for a customer in a specific period."""
    try:

        async def _reprocess():
            async with get_session() as session:
                processor = EventProcessor(session)
                return await processor.reprocess_customer_period(
                    customer_id=UUID(customer_id),
                    start_date=datetime.fromisoformat(start_date),
                    end_date=datetime.fromisoformat(end_date),
                )

        result = run_async_task(_reprocess())

        logger.info(
            "Reprocessed customer period",
            task_id=self.request.id,
            customer_id=customer_id,
            **result,
        )

        return result

    except Exception as exc:
        logger.error(
            "Failed to reprocess customer period",
            task_id=self.request.id,
            customer_id=customer_id,
            error=str(exc),
            exc_info=True,
        )

        countdown = 2**self.request.retries * 300  # 5, 10 minutes
        raise self.retry(exc=exc, countdown=countdown)


@celery_app.task(bind=True)
def detect_anomalies(self) -> dict[str, Any]:
    """Detect usage anomalies across all customers."""
    try:

        async def _detect():
            from sqlalchemy import select

            from kachi.apps.deriver.processors import AnomalyDetector
            from kachi.lib.models import Customer

            async with get_session() as session:
                detector = AnomalyDetector(session)

                # Get all active customers
                result = await session.execute(select(Customer).where(Customer.active))
                customers = result.scalars().all()

                all_anomalies = []

                for customer in customers:
                    # Check for spikes in key meters
                    for meter_key in ["api.calls", "llm.tokens", "workflow.completed"]:
                        spikes = await detector.detect_usage_spikes(
                            customer.id, meter_key
                        )
                        all_anomalies.extend(spikes)

                    # Check for zero usage
                    zero_usage = await detector.detect_zero_usage(customer.id)
                    all_anomalies.extend(zero_usage)

                return {
                    "anomalies_detected": len(all_anomalies),
                    "details": all_anomalies,
                }

        result = run_async_task(_detect())

        if result["anomalies_detected"] > 0:
            logger.warning(
                "Usage anomalies detected", task_id=self.request.id, **result
            )

        return result

    except Exception as exc:
        logger.error(
            "Failed to detect anomalies",
            task_id=self.request.id,
            error=str(exc),
            exc_info=True,
        )
        raise


@celery_app.task(bind=True)
def cleanup_old_events(self, days_to_keep: int = 90) -> dict[str, Any]:
    """Clean up old raw events to manage database size."""
    try:

        async def _cleanup():
            from sqlalchemy import delete

            from kachi.lib.models import RawEvent

            cutoff_date = datetime.utcnow() - timedelta(days=days_to_keep)

            async with get_session() as session:
                # Delete old events
                stmt = delete(RawEvent).where(RawEvent.ts < cutoff_date)
                result = await session.execute(stmt)
                deleted_count = result.rowcount

                await session.commit()

                return {
                    "deleted_events": deleted_count,
                    "cutoff_date": cutoff_date.isoformat(),
                }

        result = run_async_task(_cleanup())

        logger.info("Cleaned up old events", task_id=self.request.id, **result)

        return result

    except Exception as exc:
        logger.error(
            "Failed to cleanup old events",
            task_id=self.request.id,
            error=str(exc),
            exc_info=True,
        )
        raise


# Health check task
@celery_app.task
def health_check() -> dict[str, str]:
    """Health check for Celery workers."""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "worker": "deriver",
    }
