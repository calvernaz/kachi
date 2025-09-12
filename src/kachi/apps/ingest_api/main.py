"""FastAPI application for OpenTelemetry ingestion."""

from datetime import datetime
from typing import Any
from uuid import UUID

import structlog
from fastapi import Depends, FastAPI, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from kachi.apps.ingest_api.processors import EventProcessor
from kachi.lib.db import get_session
from kachi.lib.otel_schemas import (
    OTelExportRequest,
    OutcomeEventRequest,
    UsagePreviewResponse,
)

# Configure structured logging
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.processors.JSONRenderer(),
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    wrapper_class=structlog.stdlib.BoundLogger,
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger()

app = FastAPI(
    title="Kachi Ingestion API",
    description="OpenTelemetry data ingestion for billing platform",
    version="0.1.0",
)


@app.get("/health")
async def health_check() -> dict[str, str]:
    """Health check endpoint."""
    return {"status": "healthy", "timestamp": datetime.utcnow().isoformat()}


@app.post("/v1/otel")
async def ingest_otel_data(
    request: OTelExportRequest,
    session: AsyncSession = Depends(get_session),
) -> dict[str, Any]:
    """Ingest OpenTelemetry export data."""
    try:
        processor = EventProcessor(session)
        result = await processor.process_otel_export(request)

        await logger.ainfo(
            "Processed OTel export",
            spans_processed=result.get("spans_processed", 0),
            events_processed=result.get("events_processed", 0),
            errors=result.get("errors", []),
        )

        return {
            "status": "success",
            "processed": result,
            "timestamp": datetime.utcnow().isoformat(),
        }

    except Exception as e:
        await logger.aerror(
            "Failed to process OTel export", error=str(e), exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process OTel data: {e!s}",
        ) from e


@app.post("/v1/events/outcome")
async def submit_outcome_event(
    request: OutcomeEventRequest,
    session: AsyncSession = Depends(get_session),
) -> dict[str, Any]:
    """Submit a direct outcome event."""
    try:
        processor = EventProcessor(session)
        event_id = await processor.process_outcome_event(request)

        await logger.ainfo(
            "Processed outcome event",
            event_id=event_id,
            customer_id=str(request.customer_id),
            event_name=request.event_name,
        )

        return {
            "status": "success",
            "event_id": event_id,
            "timestamp": datetime.utcnow().isoformat(),
        }

    except Exception as e:
        await logger.aerror(
            "Failed to process outcome event", error=str(e), exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process outcome event: {e!s}",
        ) from e


@app.get("/v1/usage/preview")
async def preview_usage(
    customer_id: UUID,
    from_date: datetime,
    to_date: datetime,
    include_breakdown: bool = False,
    session: AsyncSession = Depends(get_session),
) -> UsagePreviewResponse:
    """Preview usage for a customer in a date range."""
    try:
        processor = EventProcessor(session)
        preview = await processor.generate_usage_preview(
            customer_id, from_date, to_date, include_breakdown
        )

        await logger.ainfo(
            "Generated usage preview",
            customer_id=str(customer_id),
            from_date=from_date.isoformat(),
            to_date=to_date.isoformat(),
        )

        return preview

    except Exception as e:
        await logger.aerror(
            "Failed to generate usage preview", error=str(e), exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate usage preview: {e!s}",
        ) from e


@app.post("/v1/adjustments")
async def create_adjustment(
    adjustment_data: dict[str, Any],
    session: AsyncSession = Depends(get_session),
) -> dict[str, Any]:
    """Create a billing adjustment."""
    try:
        processor = EventProcessor(session)
        adjustment_id = await processor.create_adjustment(adjustment_data)

        await logger.ainfo(
            "Created billing adjustment",
            adjustment_id=adjustment_id,
            adjustment_data=adjustment_data,
        )

        return {
            "status": "success",
            "adjustment_id": adjustment_id,
            "timestamp": datetime.utcnow().isoformat(),
        }

    except Exception as e:
        await logger.aerror("Failed to create adjustment", error=str(e), exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create adjustment: {e!s}",
        ) from e


@app.post("/lago/webhooks")
async def handle_lago_webhook(
    request: dict[str, Any],
) -> dict[str, str]:
    """Handle incoming Lago webhook events."""
    try:
        event_type = request.get("webhook_type")
        event_data = request.get("data", {})

        if not event_type:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Missing webhook_type in request",
            )

        # Queue the webhook processing as a background task
        from kachi.apps.lago_adapter.tasks import handle_lago_webhook

        handle_lago_webhook.delay(event_type, event_data)

        await logger.ainfo(
            "Queued Lago webhook processing",
            event_type=event_type,
            has_data=bool(event_data),
        )

        return {
            "status": "accepted",
            "timestamp": datetime.utcnow().isoformat(),
        }

    except Exception as e:
        await logger.aerror(
            "Failed to handle Lago webhook", error=str(e), exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to handle webhook: {e!s}",
        ) from e


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "kachi.apps.ingest_api.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_config=None,  # Use structlog configuration
    )
