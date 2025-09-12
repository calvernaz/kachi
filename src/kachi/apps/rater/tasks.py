"""Celery tasks for rating engine operations."""

import logging
from datetime import datetime, timedelta
from typing import Any
from uuid import UUID

from celery import Celery
from sqlalchemy import select

from kachi.apps.rater.main import RatingService
from kachi.lib.db import get_session
from kachi.lib.models import Customer, RatedUsage

logger = logging.getLogger(__name__)

# Celery configuration
celery_app = Celery(
    "kachi_rater", broker="redis://localhost:6379/1", backend="redis://localhost:6379/1"
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
    "rate-daily-usage": {
        "task": "kachi.apps.rater.tasks.rate_daily_usage",
        "schedule": 3600.0,  # Every hour
    },
    "rate-monthly-usage": {
        "task": "kachi.apps.rater.tasks.rate_monthly_usage",
        "schedule": 86400.0,  # Daily
    },
    "cleanup-old-rated-usage": {
        "task": "kachi.apps.rater.tasks.cleanup_old_rated_usage",
        "schedule": 86400.0,  # Daily
    },
}


@celery_app.task(bind=True, autoretry_for=(Exception,), retry_kwargs={"max_retries": 3})
def rate_customer_period(
    self,
    customer_id: str,
    period_start: str,
    period_end: str,
    force_reprocess: bool = False,
) -> dict[str, Any]:
    """Rate a specific customer for a specific period."""
    try:
        return _rate_customer_period_impl(
            UUID(customer_id),
            datetime.fromisoformat(period_start),
            datetime.fromisoformat(period_end),
            force_reprocess,
        )
    except Exception as exc:
        logger.error(f"Failed to rate customer {customer_id}: {exc}")
        raise self.retry(exc=exc, countdown=60 * (self.request.retries + 1))


async def _rate_customer_period_impl(
    customer_id: UUID,
    period_start: datetime,
    period_end: datetime,
    force_reprocess: bool = False,
) -> dict[str, Any]:
    """Implementation of customer period rating."""
    async with get_session() as session:
        # Check if already processed
        if not force_reprocess:
            existing_query = select(RatedUsage).where(
                RatedUsage.customer_id == customer_id,
                RatedUsage.period_start == period_start,
                RatedUsage.period_end == period_end,
            )

            result = await session.execute(existing_query)
            existing = result.scalar_one_or_none()

            if existing:
                logger.info(
                    f"Usage already rated for customer {customer_id}, period {period_start}"
                )
                return {
                    "customer_id": str(customer_id),
                    "period_start": period_start.isoformat(),
                    "period_end": period_end.isoformat(),
                    "total_amount": str(existing.total_amount),
                    "status": "already_processed",
                }

        # Rate the period
        rating_service = RatingService(session)
        result = await rating_service.rate_and_store(
            customer_id, period_start, period_end
        )

        logger.info(
            f"Rated customer {customer_id} for period {period_start} to {period_end}: "
            f"${result.total}"
        )

        return {
            "customer_id": str(customer_id),
            "period_start": result.period_start,
            "period_end": result.period_end,
            "total_amount": str(result.total),
            "line_count": len(result.lines),
            "status": "processed",
        }


@celery_app.task(bind=True, autoretry_for=(Exception,), retry_kwargs={"max_retries": 3})
def rate_daily_usage(self) -> dict[str, Any]:
    """Rate daily usage for all active customers."""
    try:
        return _rate_daily_usage_impl()
    except Exception as exc:
        logger.error(f"Failed to rate daily usage: {exc}")
        raise self.retry(exc=exc, countdown=300)  # 5 minute delay


async def _rate_daily_usage_impl() -> dict[str, Any]:
    """Implementation of daily usage rating."""
    # Rate usage for yesterday
    yesterday = datetime.utcnow().date() - timedelta(days=1)
    period_start = datetime.combine(yesterday, datetime.min.time())
    period_end = datetime.combine(yesterday, datetime.max.time())

    async with get_session() as session:
        # Get all active customers
        result = await session.execute(select(Customer).where(Customer.active))
        customers = result.scalars().all()

        processed_count = 0
        total_amount = 0.0
        errors = []

        for customer in customers:
            try:
                rating_service = RatingService(session)
                result = await rating_service.rate_and_store(
                    customer.id, period_start, period_end
                )
                processed_count += 1
                total_amount += float(result.total)

            except Exception as e:
                logger.error(f"Failed to rate customer {customer.id}: {e}")
                errors.append({"customer_id": str(customer.id), "error": str(e)})

        logger.info(
            f"Daily rating complete: {processed_count} customers, "
            f"${total_amount:.2f} total"
        )

        return {
            "period_start": period_start.isoformat(),
            "period_end": period_end.isoformat(),
            "customers_processed": processed_count,
            "total_amount": total_amount,
            "errors": errors,
        }


@celery_app.task(bind=True, autoretry_for=(Exception,), retry_kwargs={"max_retries": 3})
def rate_monthly_usage(self) -> dict[str, Any]:
    """Rate monthly usage for all active customers."""
    try:
        return _rate_monthly_usage_impl()
    except Exception as exc:
        logger.error(f"Failed to rate monthly usage: {exc}")
        raise self.retry(exc=exc, countdown=600)  # 10 minute delay


async def _rate_monthly_usage_impl() -> dict[str, Any]:
    """Implementation of monthly usage rating."""
    # Rate usage for last month
    today = datetime.utcnow().date()
    first_of_this_month = today.replace(day=1)
    last_month_end = first_of_this_month - timedelta(days=1)
    last_month_start = last_month_end.replace(day=1)

    period_start = datetime.combine(last_month_start, datetime.min.time())
    period_end = datetime.combine(last_month_end, datetime.max.time())

    async with get_session() as session:
        # Get all active customers
        result = await session.execute(select(Customer).where(Customer.active))
        customers = result.scalars().all()

        processed_count = 0
        total_amount = 0.0
        errors = []

        for customer in customers:
            try:
                rating_service = RatingService(session)
                result = await rating_service.rate_and_store(
                    customer.id, period_start, period_end
                )
                processed_count += 1
                total_amount += float(result.total)

            except Exception as e:
                logger.error(f"Failed to rate customer {customer.id}: {e}")
                errors.append({"customer_id": str(customer.id), "error": str(e)})

        logger.info(
            f"Monthly rating complete: {processed_count} customers, "
            f"${total_amount:.2f} total"
        )

        return {
            "period_start": period_start.isoformat(),
            "period_end": period_end.isoformat(),
            "customers_processed": processed_count,
            "total_amount": total_amount,
            "errors": errors,
        }


@celery_app.task(bind=True, autoretry_for=(Exception,), retry_kwargs={"max_retries": 2})
def cleanup_old_rated_usage(self, retention_days: int = 365) -> dict[str, Any]:
    """Clean up old rated usage records."""
    try:
        return _cleanup_old_rated_usage_impl(retention_days)
    except Exception as exc:
        logger.error(f"Failed to cleanup old rated usage: {exc}")
        raise self.retry(exc=exc, countdown=300)


async def _cleanup_old_rated_usage_impl(retention_days: int) -> dict[str, Any]:
    """Implementation of rated usage cleanup."""
    cutoff_date = datetime.utcnow() - timedelta(days=retention_days)

    async with get_session() as session:
        # Count records to be deleted
        count_query = select(RatedUsage).where(RatedUsage.period_end < cutoff_date)
        result = await session.execute(count_query)
        records_to_delete = len(result.scalars().all())

        if records_to_delete == 0:
            return {
                "cutoff_date": cutoff_date.isoformat(),
                "records_deleted": 0,
                "status": "no_records_to_delete",
            }

        # Delete old records
        delete_query = select(RatedUsage).where(RatedUsage.period_end < cutoff_date)
        result = await session.execute(delete_query)
        old_records = result.scalars().all()

        for record in old_records:
            await session.delete(record)

        await session.commit()

        logger.info(f"Cleaned up {records_to_delete} old rated usage records")

        return {
            "cutoff_date": cutoff_date.isoformat(),
            "records_deleted": records_to_delete,
            "status": "completed",
        }


@celery_app.task
def health_check() -> dict[str, Any]:
    """Health check task for monitoring."""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "service": "rating_engine",
    }


if __name__ == "__main__":
    celery_app.start()
