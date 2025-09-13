"""Metrics collection service for external data sources."""

from datetime import datetime, timedelta
from decimal import Decimal
from typing import Any
from uuid import UUID

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from kachi.lib.db import get_session
from kachi.lib.metrics_connectors import (
    MetricCollectionResult,
    MetricDataPoint,
    MetricMapping,
    MetricQuery,
    MetricsConnector,
    metrics_registry,
)
from kachi.lib.models import Customer, MeterReading

logger = structlog.get_logger()


class MetricsCollectionService:
    """Service for orchestrating metrics collection from external sources."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def collect_all_metrics(self) -> dict[str, Any]:
        """Collect metrics from all enabled connectors."""
        results = {}
        connectors = metrics_registry.get_enabled()

        for connector in connectors:
            try:
                result = await self.collect_connector_metrics(connector)
                results[connector.name] = result
            except Exception as e:
                await logger.aerror(
                    "Failed to collect metrics from connector",
                    connector=connector.name,
                    error=str(e),
                    exc_info=True,
                )
                results[connector.name] = {
                    "success": False,
                    "error": str(e),
                    "collected_at": datetime.utcnow().isoformat(),
                }

        return results

    async def collect_connector_metrics(
        self, connector: MetricsConnector
    ) -> dict[str, Any]:
        """Collect metrics from a specific connector."""
        collection_results = []
        total_data_points = 0
        total_meter_readings = 0

        # Test connection first
        if not await connector.test_connection():
            return {
                "success": False,
                "error": "Connection test failed",
                "collected_at": datetime.utcnow().isoformat(),
            }

        # Collect metrics for each mapping
        for mapping in connector.config.metric_mappings:
            try:
                result = await self._collect_mapping_metrics(connector, mapping)
                collection_results.append(result)
                total_data_points += len(result.data_points)

                # Transform and store metrics
                meter_readings = await self._transform_and_store_metrics(
                    result, mapping
                )
                total_meter_readings += len(meter_readings)

            except Exception as e:
                await logger.aerror(
                    "Failed to collect metrics for mapping",
                    connector=connector.name,
                    mapping=mapping.external_metric_name,
                    error=str(e),
                    exc_info=True,
                )
                collection_results.append(
                    {
                        "mapping": mapping.external_metric_name,
                        "success": False,
                        "error": str(e),
                    }
                )

        return {
            "success": True,
            "connector": connector.name,
            "mappings_processed": len(connector.config.metric_mappings),
            "total_data_points": total_data_points,
            "total_meter_readings": total_meter_readings,
            "collected_at": datetime.utcnow().isoformat(),
            "results": collection_results,
        }

    async def _collect_mapping_metrics(
        self, connector: MetricsConnector, mapping: MetricMapping
    ) -> MetricCollectionResult:
        """Collect metrics for a specific mapping."""
        # Calculate time range (last collection interval)
        end_time = datetime.utcnow()
        start_time = end_time - timedelta(seconds=connector.config.collection_interval)

        # Build query based on mapping
        query = MetricQuery(
            query=self._build_prometheus_query(mapping),
            start_time=start_time,
            end_time=end_time,
            step="1m",  # 1-minute resolution
            labels=mapping.label_filters,
        )

        return await connector.query_metrics(query)

    def _build_prometheus_query(self, mapping: MetricMapping) -> str:
        """Build PromQL query from mapping configuration."""
        query = mapping.external_metric_name

        # Add label filters
        if mapping.label_filters:
            filters = []
            for key, value in mapping.label_filters.items():
                filters.append(f'{key}="{value}"')
            query = f'{query}{{{",".join(filters)}}}'

        # Apply transformation function
        if mapping.transformation_function == "rate":
            query = f"rate({query}[5m])"
        elif mapping.transformation_function == "sum":
            query = f"sum({query}) by ({mapping.customer_id_label})"
        elif mapping.transformation_function == "avg":
            query = f"avg({query}) by ({mapping.customer_id_label})"

        return query

    async def _transform_and_store_metrics(
        self, result: MetricCollectionResult, mapping: MetricMapping
    ) -> list[MeterReading]:
        """Transform external metrics to Kachi meter readings and store them."""
        meter_readings = []

        if not result.success:
            return meter_readings

        # Group data points by customer and time window
        customer_windows = {}

        for data_point in result.data_points:
            # Extract customer ID from labels
            customer_id = self._extract_customer_id(data_point, mapping)
            if not customer_id:
                continue

            # Verify customer exists
            if not await self._customer_exists(customer_id):
                await logger.awarn(
                    "Skipping metric for non-existent customer",
                    customer_id=str(customer_id),
                    metric=mapping.external_metric_name,
                )
                continue

            # Round timestamp to minute for aggregation
            window_start = data_point.timestamp.replace(second=0, microsecond=0)

            key = (customer_id, window_start)
            if key not in customer_windows:
                customer_windows[key] = []

            # Apply transformation
            transformed_value = self._apply_transformation(data_point.value, mapping)
            customer_windows[key].append(transformed_value)

        # Create meter readings for each customer/window
        for (customer_id, window_start), values in customer_windows.items():
            # Aggregate values (sum by default)
            total_value = sum(values)

            # Check for existing meter reading to avoid duplicates
            existing = await self._get_existing_meter_reading(
                customer_id, mapping.kachi_meter_key, window_start
            )

            if existing:
                # Update existing reading
                existing.value += total_value
                meter_readings.append(existing)
            else:
                # Create new meter reading
                meter_reading = MeterReading(
                    customer_id=customer_id,
                    meter_key=mapping.kachi_meter_key,
                    value=total_value,
                    window_start=window_start,
                    window_end=window_start + timedelta(minutes=1),
                    source="external_metrics",
                    metadata={
                        "external_metric": mapping.external_metric_name,
                        "source_system": result.source_system,
                        "collection_timestamp": result.collection_timestamp.isoformat(),
                        "data_points_count": len(values),
                    },
                )
                self.session.add(meter_reading)
                meter_readings.append(meter_reading)

        # Commit all meter readings
        if meter_readings:
            await self.session.commit()
            await logger.ainfo(
                "Stored meter readings from external metrics",
                mapping=mapping.external_metric_name,
                meter_key=mapping.kachi_meter_key,
                readings_count=len(meter_readings),
            )

        return meter_readings

    def _extract_customer_id(
        self, data_point: MetricDataPoint, mapping: MetricMapping
    ) -> UUID | None:
        """Extract customer ID from metric labels."""
        customer_id_str = data_point.labels.get(mapping.customer_id_label)
        if not customer_id_str:
            return None

        try:
            return UUID(customer_id_str)
        except (ValueError, TypeError):
            return None

    def _apply_transformation(self, value: Decimal, mapping: MetricMapping) -> Decimal:
        """Apply transformation to metric value."""
        return value * mapping.scaling_factor

    async def _customer_exists(self, customer_id: UUID) -> bool:
        """Check if customer exists in the database."""
        result = await self.session.execute(
            select(Customer.id).where(Customer.id == customer_id)  # type: ignore[arg-type]
        )
        return result.scalar() is not None

    async def _get_existing_meter_reading(
        self, customer_id: UUID, meter_key: str, window_start: datetime
    ) -> MeterReading | None:
        """Get existing meter reading for deduplication."""
        result = await self.session.execute(
            select(MeterReading)
            .where(MeterReading.customer_id == customer_id)  # type: ignore[arg-type]
            .where(MeterReading.meter_key == meter_key)  # type: ignore[arg-type]
            .where(MeterReading.window_start == window_start)  # type: ignore[arg-type]
        )
        return result.scalar_one_or_none()


def setup_default_connectors() -> None:
    """Set up default metrics connectors from configuration."""
    # This would typically load from environment variables or config files
    # For now, we'll set up a basic structure
    return None


async def create_metrics_collection_service() -> MetricsCollectionService:
    """Factory function to create metrics collection service."""
    async with get_session() as session:
        return MetricsCollectionService(session)
