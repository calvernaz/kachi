"""API endpoints for metrics collection management."""

from datetime import datetime
from decimal import Decimal
from typing import Any

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from kachi.apps.metrics_collector.tasks import (
    collect_all_external_metrics,
    collect_connector_metrics,
    health_check_all_connectors,
    manual_metrics_collection,
)
from kachi.lib.metrics_config import config_manager
from kachi.lib.metrics_connectors import (
    MetricMapping,
    metrics_registry,
)

router = APIRouter(prefix="/api/metrics", tags=["External Metrics"])


class CollectionTriggerResponse(BaseModel):
    """Response for collection trigger requests."""

    success: bool
    task_id: str
    message: str
    triggered_at: datetime


class ConnectorStatusResponse(BaseModel):
    """Response for connector status requests."""

    name: str
    type: str
    enabled: bool
    healthy: bool
    endpoint: str
    last_collection: datetime | None = None
    error: str | None = None


class MetricMappingRequest(BaseModel):
    """Request to add a custom metric mapping."""

    external_metric_name: str
    kachi_meter_key: str
    transformation_function: str | None = None
    customer_id_label: str = "customer_id"
    scaling_factor: float = 1.0
    label_filters: dict[str, str] = {}


@router.get("/connectors", response_model=list[ConnectorStatusResponse])
async def get_connectors_status() -> list[ConnectorStatusResponse]:
    """Get status of all configured metrics connectors."""
    connectors = metrics_registry.get_all()
    status_list = []

    for connector in connectors:
        try:
            # Test connection
            is_healthy = await connector.test_connection()

            status_list.append(
                ConnectorStatusResponse(
                    name=connector.name,
                    type=connector.type,
                    enabled=connector.config.enabled,
                    healthy=is_healthy,
                    endpoint=connector.config.endpoint,
                )
            )
        except Exception as e:
            status_list.append(
                ConnectorStatusResponse(
                    name=connector.name,
                    type=connector.type,
                    enabled=connector.config.enabled,
                    healthy=False,
                    endpoint=connector.config.endpoint,
                    error=str(e),
                )
            )

    return status_list


@router.get("/connectors/{connector_name}")
async def get_connector_details(connector_name: str) -> dict[str, Any]:
    """Get detailed information about a specific connector."""
    connector = metrics_registry.get(connector_name)
    if not connector:
        raise HTTPException(
            status_code=404, detail=f"Connector '{connector_name}' not found"
        )

    try:
        # Test connection
        is_healthy = await connector.test_connection()

        # Get available metrics
        available_metrics = await connector.get_available_metrics()

        return {
            "name": connector.name,
            "type": connector.type,
            "enabled": connector.config.enabled,
            "healthy": is_healthy,
            "endpoint": connector.config.endpoint,
            "timeout": connector.config.timeout,
            "collection_interval": connector.config.collection_interval,
            "metric_mappings": [
                mapping.dict() for mapping in connector.config.metric_mappings
            ],
            "available_metrics": available_metrics[:50],  # Limit to first 50
            "total_available_metrics": len(available_metrics),
        }
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to get connector details: {e!s}"
        ) from e


@router.post("/collect", response_model=CollectionTriggerResponse)
async def trigger_collection(
    connector_name: str
    | None = Query(None, description="Specific connector to collect from"),
) -> CollectionTriggerResponse:
    """Trigger manual metrics collection."""
    try:
        if connector_name:
            # Collect from specific connector
            task = collect_connector_metrics.delay(connector_name)
            message = f"Started collection from connector '{connector_name}'"
        else:
            # Collect from all connectors
            task = collect_all_external_metrics.delay()
            message = "Started collection from all enabled connectors"

        return CollectionTriggerResponse(
            success=True,
            task_id=task.id,
            message=message,
            triggered_at=datetime.utcnow(),
        )
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to trigger collection: {e!s}"
        ) from e


@router.post("/collect/manual", response_model=CollectionTriggerResponse)
async def trigger_manual_collection(
    connector_name: str | None = None,
    metric_mapping: str | None = None,
) -> CollectionTriggerResponse:
    """Trigger manual metrics collection with optional filtering."""
    try:
        task = manual_metrics_collection.delay(connector_name, metric_mapping)

        message = "Started manual collection"
        if connector_name:
            message += f" from connector '{connector_name}'"
        if metric_mapping:
            message += f" for metric '{metric_mapping}'"

        return CollectionTriggerResponse(
            success=True,
            task_id=task.id,
            message=message,
            triggered_at=datetime.utcnow(),
        )
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to trigger manual collection: {e!s}"
        ) from e


@router.get("/health-check")
async def trigger_health_check() -> dict[str, Any]:
    """Trigger health check for all connectors."""
    try:
        task = health_check_all_connectors.delay()

        return {
            "success": True,
            "task_id": task.id,
            "message": "Started health check for all connectors",
            "triggered_at": datetime.utcnow().isoformat(),
        }
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to trigger health check: {e!s}"
        ) from e


@router.get("/available-metrics/{connector_name}")
async def get_available_metrics(connector_name: str) -> dict[str, Any]:
    """Get available metrics from a specific connector."""
    connector = metrics_registry.get(connector_name)
    if not connector:
        raise HTTPException(
            status_code=404, detail=f"Connector '{connector_name}' not found"
        )

    try:
        metrics = await connector.get_available_metrics()

        return {
            "connector": connector_name,
            "total_metrics": len(metrics),
            "metrics": metrics,
            "retrieved_at": datetime.utcnow().isoformat(),
        }
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to get available metrics: {e!s}"
        ) from e


@router.get("/metric-metadata/{connector_name}/{metric_name}")
async def get_metric_metadata(connector_name: str, metric_name: str) -> dict[str, Any]:
    """Get metadata for a specific metric from a connector."""
    connector = metrics_registry.get(connector_name)
    if not connector:
        raise HTTPException(
            status_code=404, detail=f"Connector '{connector_name}' not found"
        )

    try:
        metadata = await connector.get_metric_metadata(metric_name)

        return {
            "connector": connector_name,
            "metric": metric_name,
            "metadata": metadata,
            "retrieved_at": datetime.utcnow().isoformat(),
        }
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to get metric metadata: {e!s}"
        ) from e


@router.post("/mappings/{connector_name}")
async def add_metric_mapping(
    connector_name: str,
    mapping_request: MetricMappingRequest,
) -> dict[str, Any]:
    """Add a custom metric mapping to a connector."""
    connector = metrics_registry.get(connector_name)
    if not connector:
        raise HTTPException(
            status_code=404, detail=f"Connector '{connector_name}' not found"
        )

    try:
        # Create metric mapping
        mapping = MetricMapping(
            external_metric_name=mapping_request.external_metric_name,
            kachi_meter_key=mapping_request.kachi_meter_key,
            transformation_function=mapping_request.transformation_function,
            customer_id_label=mapping_request.customer_id_label,
            scaling_factor=Decimal(str(mapping_request.scaling_factor)),
            label_filters=mapping_request.label_filters,
        )

        # Add to connector configuration
        connector.config.metric_mappings.append(mapping)

        # Also add to config manager for persistence
        config_manager.add_custom_mapping(connector_name, mapping)

        return {
            "success": True,
            "message": f"Added metric mapping for '{mapping_request.external_metric_name}'",
            "mapping": mapping.dict(),
            "added_at": datetime.utcnow().isoformat(),
        }
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to add metric mapping: {e!s}"
        ) from e


@router.get("/mappings/{connector_name}")
async def get_metric_mappings(connector_name: str) -> dict[str, Any]:
    """Get all metric mappings for a connector."""
    connector = metrics_registry.get(connector_name)
    if not connector:
        raise HTTPException(
            status_code=404, detail=f"Connector '{connector_name}' not found"
        )

    try:
        mappings = connector.config.metric_mappings
        custom_mappings = config_manager.get_custom_mappings(connector_name)

        return {
            "connector": connector_name,
            "default_mappings": [mapping.dict() for mapping in mappings],
            "custom_mappings": [mapping.dict() for mapping in custom_mappings],
            "total_mappings": len(mappings) + len(custom_mappings),
            "retrieved_at": datetime.utcnow().isoformat(),
        }
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to get metric mappings: {e!s}"
        ) from e


@router.get("/config")
async def get_metrics_config() -> dict[str, Any]:
    """Get current metrics collection configuration."""
    try:
        return {
            "global_config": config_manager.global_config.dict(),
            "enabled_data_sources": [
                {
                    "name": config.name,
                    "type": config.type,
                    "endpoint": config.endpoint,
                    "enabled": config.enabled,
                    "collection_interval": config.collection_interval,
                    "mappings_count": len(config.metric_mappings),
                }
                for config in config_manager.get_enabled_data_sources()
            ],
            "total_connectors": len(metrics_registry.get_all()),
            "enabled_connectors": len(metrics_registry.get_enabled()),
            "retrieved_at": datetime.utcnow().isoformat(),
        }
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to get metrics config: {e!s}"
        ) from e


@router.get("/status")
async def get_collection_status() -> dict[str, Any]:
    """Get overall metrics collection status."""
    try:
        # Get basic stats
        connectors = metrics_registry.get_all()
        enabled_connectors = metrics_registry.get_enabled()

        # Test connections
        healthy_connectors = []
        for connector in enabled_connectors:
            try:
                if await connector.test_connection():
                    healthy_connectors.append(connector.name)
            except Exception:
                pass

        return {
            "collection_enabled": config_manager.global_config.enabled,
            "total_connectors": len(connectors),
            "enabled_connectors": len(enabled_connectors),
            "healthy_connectors": len(healthy_connectors),
            "healthy_connector_names": healthy_connectors,
            "default_collection_interval": config_manager.global_config.default_collection_interval,
            "last_status_check": datetime.utcnow().isoformat(),
        }
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to get collection status: {e!s}"
        ) from e
