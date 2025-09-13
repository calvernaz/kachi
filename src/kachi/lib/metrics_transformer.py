"""Metric transformation pipeline for converting external metrics to Kachi format."""

import hashlib
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Any
from uuid import UUID

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from kachi.lib.metrics_connectors import (
    MetricCollectionResult,
    MetricDataPoint,
    MetricMapping,
)
from kachi.lib.models import Customer, MeterReading

logger = structlog.get_logger()


class MetricValidationError(Exception):
    """Exception raised when metric validation fails."""


class MetricTransformationResult:
    """Result of metric transformation operation."""

    def __init__(self):
        self.success = True
        self.meter_readings: list[MeterReading] = []
        self.errors: list[str] = []
        self.warnings: list[str] = []
        self.skipped_count = 0
        self.processed_count = 0
        self.duplicate_count = 0

    def add_error(self, error: str) -> None:
        """Add an error to the result."""
        self.errors.append(error)
        self.success = False

    def add_warning(self, warning: str) -> None:
        """Add a warning to the result."""
        self.warnings.append(warning)

    def to_dict(self) -> dict[str, Any]:
        """Convert result to dictionary."""
        return {
            "success": self.success,
            "meter_readings_count": len(self.meter_readings),
            "processed_count": self.processed_count,
            "skipped_count": self.skipped_count,
            "duplicate_count": self.duplicate_count,
            "errors": self.errors,
            "warnings": self.warnings,
        }


class MetricsTransformer:
    """Pipeline for transforming external metrics to Kachi meter readings."""

    def __init__(self, session: AsyncSession):
        self.session = session
        self._customer_cache: dict[UUID, bool] = {}
        self._processed_hashes: set[str] = set()

    async def transform_metrics(
        self,
        collection_result: MetricCollectionResult,
        mapping: MetricMapping,
    ) -> MetricTransformationResult:
        """Transform external metrics to Kachi meter readings."""
        result = MetricTransformationResult()

        if not collection_result.success:
            result.add_error(
                f"Collection failed: {', '.join(collection_result.errors)}"
            )
            return result

        # Validate mapping
        try:
            self._validate_mapping(mapping)
        except MetricValidationError as e:
            result.add_error(f"Invalid mapping: {e!s}")
            return result

        # Group data points by customer and time window
        customer_windows = await self._group_by_customer_and_window(
            collection_result.data_points, mapping, result
        )

        # Transform each customer/window group
        for (customer_id, window_start), data_points in customer_windows.items():
            try:
                meter_reading = await self._create_meter_reading(
                    customer_id, window_start, data_points, mapping, collection_result
                )

                if meter_reading:
                    result.meter_readings.append(meter_reading)
                    result.processed_count += 1
                else:
                    result.skipped_count += 1

            except Exception as e:
                result.add_error(
                    f"Failed to create meter reading for customer {customer_id}: {e!s}"
                )
                result.skipped_count += 1

        return result

    def _validate_mapping(self, mapping: MetricMapping) -> None:
        """Validate metric mapping configuration."""
        if not mapping.external_metric_name:
            raise MetricValidationError("External metric name is required")

        if not mapping.kachi_meter_key:
            raise MetricValidationError("Kachi meter key is required")

        if not mapping.customer_id_label:
            raise MetricValidationError("Customer ID label is required")

        if mapping.scaling_factor <= 0:
            raise MetricValidationError("Scaling factor must be positive")

    async def _group_by_customer_and_window(
        self,
        data_points: list[MetricDataPoint],
        mapping: MetricMapping,
        result: MetricTransformationResult,
    ) -> dict[tuple[UUID, datetime], list[MetricDataPoint]]:
        """Group data points by customer ID and time window."""
        customer_windows = {}

        for data_point in data_points:
            # Extract customer ID
            customer_id = await self._extract_customer_id(data_point, mapping)
            if not customer_id:
                result.add_warning(
                    f"No customer ID found in labels: {data_point.labels}"
                )
                result.skipped_count += 1
                continue

            # Validate customer exists
            if not await self._validate_customer(customer_id):
                result.add_warning(f"Customer {customer_id} not found in database")
                result.skipped_count += 1
                continue

            # Check label filters
            if not self._matches_label_filters(data_point.labels, mapping):
                result.skipped_count += 1
                continue

            # Round timestamp to minute for aggregation
            window_start = data_point.timestamp.replace(second=0, microsecond=0)

            # Check for duplicates
            if self._is_duplicate(data_point, customer_id, window_start):
                result.duplicate_count += 1
                continue

            key = (customer_id, window_start)
            if key not in customer_windows:
                customer_windows[key] = []

            customer_windows[key].append(data_point)

        return customer_windows

    async def _extract_customer_id(
        self, data_point: MetricDataPoint, mapping: MetricMapping
    ) -> UUID | None:
        """Extract customer ID from metric labels."""
        customer_id_str = data_point.labels.get(mapping.customer_id_label)
        if not customer_id_str:
            return None

        try:
            return UUID(customer_id_str)
        except (ValueError, TypeError):
            await logger.awarn(
                "Invalid customer ID format",
                customer_id_str=customer_id_str,
                metric=mapping.external_metric_name,
            )
            return None

    async def _validate_customer(self, customer_id: UUID) -> bool:
        """Validate that customer exists in database."""
        # Use cache to avoid repeated database queries
        if customer_id in self._customer_cache:
            return self._customer_cache[customer_id]

        result = await self.session.execute(
            select(Customer.id).where(Customer.id == customer_id)  # type: ignore[arg-type]
        )
        exists = result.scalar() is not None

        # Cache result
        self._customer_cache[customer_id] = exists
        return exists

    def _matches_label_filters(
        self, labels: dict[str, str], mapping: MetricMapping
    ) -> bool:
        """Check if metric labels match the configured filters."""
        for filter_key, filter_value in mapping.label_filters.items():
            if labels.get(filter_key) != filter_value:
                return False
        return True

    def _is_duplicate(
        self, data_point: MetricDataPoint, customer_id: UUID, window_start: datetime
    ) -> bool:
        """Check if this data point is a duplicate."""
        # Create hash of unique identifiers
        hash_input = f"{customer_id}:{window_start.isoformat()}:{data_point.metric_name}:{data_point.value}"
        data_hash = hashlib.md5(hash_input.encode()).hexdigest()

        if data_hash in self._processed_hashes:
            return True

        self._processed_hashes.add(data_hash)
        return False

    async def _create_meter_reading(
        self,
        customer_id: UUID,
        window_start: datetime,
        data_points: list[MetricDataPoint],
        mapping: MetricMapping,
        collection_result: MetricCollectionResult,
    ) -> MeterReading | None:
        """Create a meter reading from grouped data points."""
        if not data_points:
            return None

        # Apply aggregation based on transformation function
        aggregated_value = self._aggregate_values(data_points, mapping)

        # Apply scaling factor
        final_value = aggregated_value * mapping.scaling_factor

        # Check for existing meter reading to handle updates
        existing_reading = await self._get_existing_meter_reading(
            customer_id, mapping.kachi_meter_key, window_start
        )

        if existing_reading:
            # Update existing reading (additive)
            existing_reading.value += final_value
            existing_reading.metadata = self._update_metadata(
                existing_reading.metadata or {}, data_points, collection_result
            )
            return existing_reading
        else:
            # Create new meter reading
            window_end = window_start + timedelta(minutes=1)

            meter_reading = MeterReading(
                customer_id=customer_id,
                meter_key=mapping.kachi_meter_key,
                value=final_value,
                window_start=window_start,
                window_end=window_end,
                source="external_metrics",
                metadata=self._create_metadata(data_points, mapping, collection_result),
            )

            self.session.add(meter_reading)
            return meter_reading

    def _aggregate_values(
        self, data_points: list[MetricDataPoint], mapping: MetricMapping
    ) -> Decimal:
        """Aggregate values based on transformation function."""
        values = [dp.value for dp in data_points]

        if mapping.transformation_function == "sum":
            return sum(values)
        elif mapping.transformation_function == "avg":
            return sum(values) / len(values) if values else Decimal("0")
        elif mapping.transformation_function == "max":
            return max(values) if values else Decimal("0")
        elif mapping.transformation_function == "min":
            return min(values) if values else Decimal("0")
        elif mapping.transformation_function == "rate":
            # For rate calculations, sum the values (assuming they're already rates)
            return sum(values)
        else:
            # Default to sum
            return sum(values)

    async def _get_existing_meter_reading(
        self, customer_id: UUID, meter_key: str, window_start: datetime
    ) -> MeterReading | None:
        """Get existing meter reading for the same customer/meter/window."""
        result = await self.session.execute(
            select(MeterReading)
            .where(MeterReading.customer_id == customer_id)  # type: ignore[arg-type]
            .where(MeterReading.meter_key == meter_key)  # type: ignore[arg-type]
            .where(MeterReading.window_start == window_start)  # type: ignore[arg-type]
        )
        return result.scalar_one_or_none()

    def _create_metadata(
        self,
        data_points: list[MetricDataPoint],
        mapping: MetricMapping,
        collection_result: MetricCollectionResult,
    ) -> dict[str, Any]:
        """Create metadata for meter reading."""
        return {
            "external_metric": mapping.external_metric_name,
            "source_system": collection_result.source_system,
            "collection_timestamp": collection_result.collection_timestamp.isoformat(),
            "data_points_count": len(data_points),
            "transformation_function": mapping.transformation_function,
            "scaling_factor": str(mapping.scaling_factor),
            "original_values": [
                str(dp.value) for dp in data_points[:10]
            ],  # Limit to first 10
        }

    def _update_metadata(
        self,
        existing_metadata: dict[str, Any],
        data_points: list[MetricDataPoint],
        collection_result: MetricCollectionResult,
    ) -> dict[str, Any]:
        """Update metadata for existing meter reading."""
        existing_metadata[
            "last_update"
        ] = collection_result.collection_timestamp.isoformat()
        existing_metadata["total_updates"] = (
            existing_metadata.get("total_updates", 0) + 1
        )
        existing_metadata["latest_data_points_count"] = len(data_points)
        return existing_metadata
