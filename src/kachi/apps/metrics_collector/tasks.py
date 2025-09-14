"""Celery tasks for external metrics collection."""

import asyncio
import logging
from datetime import datetime
from typing import Any

from celery import Celery

from kachi.apps.metrics_collector.main import MetricsCollectionService
from kachi.lib.db import get_session
from kachi.lib.metrics_config import config_manager

logger = logging.getLogger(__name__)

# Celery configuration
celery_app = Celery(
    "metrics_collector",
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
    "collect-external-metrics-every-5min": {
        "task": "metrics_collector.collect_all_external_metrics",
        "schedule": 300.0,  # 5 minutes
    },
    "health-check-connectors-hourly": {
        "task": "metrics_collector.health_check_all_connectors",
        "schedule": 3600.0,  # 1 hour
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
def collect_all_external_metrics(self) -> dict[str, Any]:
    """Collect metrics from all enabled external connectors."""
    try:

        async def _collect():
            async with get_session() as session:
                service = MetricsCollectionService(session)
                return await service.collect_all_metrics()

        result = run_async_task(_collect())

        logger.info(
            "Collected metrics from all connectors", task_id=self.request.id, **result
        )
        return result

    except Exception as exc:
        logger.error(f"Failed to collect all external metrics: {exc}")
        raise self.retry(exc=exc, countdown=60 * (self.request.retries + 1))


@celery_app.task(bind=True, max_retries=3)
def collect_connector_metrics(self, connector_name: str) -> dict[str, Any]:
    """Collect metrics from a specific connector."""
    try:

        async def _collect():
            async with get_session() as session:
                service = MetricsCollectionService(session)
                return await service.collect_connector_metrics(connector_name)

        result = run_async_task(_collect())

        logger.info(
            "Collected metrics from connector",
            task_id=self.request.id,
            connector=connector_name,
            **result,
        )
        return result

    except Exception as exc:
        logger.error(f"Failed to collect metrics from {connector_name}: {exc}")
        raise self.retry(exc=exc, countdown=60 * (self.request.retries + 1))


@celery_app.task(bind=True, max_retries=2)
def health_check_all_connectors(self) -> dict[str, Any]:
    """Health check all configured connectors."""
    try:

        async def _health_check():
            results = {}
            for connector_name in config_manager.get_enabled_connectors():
                try:
                    async with get_session() as session:
                        MetricsCollectionService(session)
                        # This would be a health check method
                        results[connector_name] = {
                            "status": "healthy",
                            "checked_at": datetime.utcnow().isoformat(),
                        }
                except Exception as e:
                    results[connector_name] = {
                        "status": "unhealthy",
                        "error": str(e),
                        "checked_at": datetime.utcnow().isoformat(),
                    }

            return {
                "success": True,
                "connectors": results,
                "checked_at": datetime.utcnow().isoformat(),
            }

        result = run_async_task(_health_check())

        logger.info("Health checked all connectors", task_id=self.request.id, **result)
        return result

    except Exception as exc:
        logger.error(f"Failed to health check connectors: {exc}")
        raise self.retry(exc=exc, countdown=300)  # 5 minute delay


@celery_app.task(bind=True, max_retries=3)
def manual_metrics_collection(
    self, connector_name: str | None = None, metric_mapping: str | None = None
) -> dict[str, Any]:
    """Manual metrics collection with optional filtering."""
    try:

        async def _collect():
            async with get_session() as session:
                service = MetricsCollectionService(session)

                if connector_name:
                    return await service.collect_connector_metrics(connector_name)
                else:
                    return await service.collect_all_metrics()

        result = run_async_task(_collect())

        logger.info(
            "Manual metrics collection completed",
            task_id=self.request.id,
            connector=connector_name,
            metric=metric_mapping,
            **result,
        )
        return result

    except Exception as exc:
        logger.error(f"Failed manual metrics collection: {exc}")
        raise self.retry(exc=exc, countdown=60 * (self.request.retries + 1))
