"""Abstract interfaces and base classes for external metrics collection."""

from abc import ABC, abstractmethod
from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class MetricDataPoint(BaseModel):
    """A single metric data point from an external source."""

    timestamp: datetime
    value: Decimal
    labels: dict[str, str] = Field(default_factory=dict)
    metric_name: str
    source_system: str


class MetricQuery(BaseModel):
    """Configuration for querying metrics from external sources."""

    query: str  # PromQL, SQL, or other query language
    start_time: datetime
    end_time: datetime
    step: str | None = None  # For range queries (e.g., "5m", "1h")
    labels: dict[str, str] = Field(default_factory=dict)


class MetricCollectionResult(BaseModel):
    """Result of a metric collection operation."""

    success: bool
    data_points: list[MetricDataPoint] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)
    collection_timestamp: datetime
    source_system: str
    query_info: dict[str, Any] = Field(default_factory=dict)


class MetricMapping(BaseModel):
    """Configuration for mapping external metrics to Kachi meters."""

    external_metric_name: str
    kachi_meter_key: str
    transformation_function: str | None = None  # e.g., "sum", "avg", "rate"
    label_filters: dict[str, str] = Field(default_factory=dict)
    customer_id_label: str = "customer_id"  # Label that contains customer ID
    scaling_factor: Decimal = Decimal("1.0")


class DataSourceConfig(BaseModel):
    """Configuration for an external data source."""

    name: str
    type: str  # "prometheus", "influxdb", "datadog", etc.
    endpoint: str
    credentials: dict[str, str] = Field(default_factory=dict)
    timeout: int = 30
    enabled: bool = True
    collection_interval: int = 300  # seconds
    metric_mappings: list[MetricMapping] = Field(default_factory=list)


class MetricsConnector(ABC):
    """Abstract base class for external metrics connectors."""

    def __init__(self, config: DataSourceConfig):
        self.config = config
        self.name = config.name
        self.type = config.type

    @abstractmethod
    async def test_connection(self) -> bool:
        """Test if the connection to the external system is working."""
        raise NotImplementedError

    @abstractmethod
    async def query_metrics(self, query: MetricQuery) -> MetricCollectionResult:
        """Query metrics from the external system."""
        raise NotImplementedError

    @abstractmethod
    async def get_available_metrics(self) -> list[str]:
        """Get list of available metrics from the external system."""
        raise NotImplementedError

    @abstractmethod
    async def get_metric_metadata(self, metric_name: str) -> dict[str, Any]:
        """Get metadata for a specific metric (labels, type, description, etc.)."""
        raise NotImplementedError

    def get_customer_id_from_labels(
        self, labels: dict[str, str], mapping: MetricMapping
    ) -> UUID | None:
        """Extract customer ID from metric labels."""
        customer_id_str = labels.get(mapping.customer_id_label)
        if not customer_id_str:
            return None

        try:
            return UUID(customer_id_str)
        except (ValueError, TypeError):
            return None

    def apply_transformation(self, value: Decimal, mapping: MetricMapping) -> Decimal:
        """Apply transformation function to metric value."""
        transformed_value = value * mapping.scaling_factor

        if mapping.transformation_function in ("rate", "sum", "avg"):
            # For rate calculations, we might need additional context
            # This is a simplified implementation
            return transformed_value
        else:
            return transformed_value

    def matches_label_filters(
        self, labels: dict[str, str], mapping: MetricMapping
    ) -> bool:
        """Check if metric labels match the configured filters."""
        for filter_key, filter_value in mapping.label_filters.items():
            if labels.get(filter_key) != filter_value:
                return False
        return True


class MetricsConnectorRegistry:
    """Registry for managing multiple metrics connectors."""

    def __init__(self):
        self._connectors: dict[str, MetricsConnector] = {}

    def register(self, connector: MetricsConnector) -> None:
        """Register a metrics connector."""
        self._connectors[connector.name] = connector

    def unregister(self, name: str) -> None:
        """Unregister a metrics connector."""
        self._connectors.pop(name, None)

    def get(self, name: str) -> MetricsConnector | None:
        """Get a metrics connector by name."""
        return self._connectors.get(name)

    def get_all(self) -> list[MetricsConnector]:
        """Get all registered connectors."""
        return list(self._connectors.values())

    def get_enabled(self) -> list[MetricsConnector]:
        """Get all enabled connectors."""
        return [conn for conn in self._connectors.values() if conn.config.enabled]


# Global registry instance
metrics_registry = MetricsConnectorRegistry()
