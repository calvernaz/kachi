"""Configuration management for external metrics collection."""

import os
from decimal import Decimal

from pydantic import BaseModel

from kachi.lib.metrics_connectors import DataSourceConfig, MetricMapping


class MetricsCollectionConfig(BaseModel):
    """Global configuration for metrics collection."""

    enabled: bool = True
    default_collection_interval: int = 300  # 5 minutes
    max_concurrent_collections: int = 5
    retry_attempts: int = 3
    retry_delay: int = 60  # seconds


class PrometheusConfig(BaseModel):
    """Configuration for Prometheus data source."""

    enabled: bool = True
    endpoint: str = "http://localhost:9090"
    bearer_token: str | None = None
    username: str | None = None
    password: str | None = None
    timeout: int = 30
    collection_interval: int = 300


class InfluxDBConfig(BaseModel):
    """Configuration for InfluxDB data source."""

    enabled: bool = False
    endpoint: str = "http://localhost:8086"
    token: str | None = None
    org: str | None = None
    bucket: str | None = None
    timeout: int = 30
    collection_interval: int = 300


class DataDogConfig(BaseModel):
    """Configuration for DataDog data source."""

    enabled: bool = False
    api_key: str | None = None
    app_key: str | None = None
    site: str = "datadoghq.com"
    timeout: int = 30
    collection_interval: int = 300


def load_metrics_config() -> MetricsCollectionConfig:
    """Load metrics collection configuration from environment variables."""
    return MetricsCollectionConfig(
        enabled=os.getenv("METRICS_COLLECTION_ENABLED", "true").lower() == "true",
        default_collection_interval=int(
            os.getenv("METRICS_COLLECTION_INTERVAL", "300")
        ),
        max_concurrent_collections=int(os.getenv("METRICS_MAX_CONCURRENT", "5")),
        retry_attempts=int(os.getenv("METRICS_RETRY_ATTEMPTS", "3")),
        retry_delay=int(os.getenv("METRICS_RETRY_DELAY", "60")),
    )


def load_prometheus_config() -> PrometheusConfig:
    """Load Prometheus configuration from environment variables."""
    return PrometheusConfig(
        enabled=os.getenv("PROMETHEUS_ENABLED", "true").lower() == "true",
        endpoint=os.getenv("PROMETHEUS_ENDPOINT", "http://localhost:9090"),
        bearer_token=os.getenv("PROMETHEUS_BEARER_TOKEN"),
        username=os.getenv("PROMETHEUS_USERNAME"),
        password=os.getenv("PROMETHEUS_PASSWORD"),
        timeout=int(os.getenv("PROMETHEUS_TIMEOUT", "30")),
        collection_interval=int(os.getenv("PROMETHEUS_COLLECTION_INTERVAL", "300")),
    )


def load_influxdb_config() -> InfluxDBConfig:
    """Load InfluxDB configuration from environment variables."""
    return InfluxDBConfig(
        enabled=os.getenv("INFLUXDB_ENABLED", "false").lower() == "true",
        endpoint=os.getenv("INFLUXDB_ENDPOINT", "http://localhost:8086"),
        token=os.getenv("INFLUXDB_TOKEN"),
        org=os.getenv("INFLUXDB_ORG"),
        bucket=os.getenv("INFLUXDB_BUCKET"),
        timeout=int(os.getenv("INFLUXDB_TIMEOUT", "30")),
        collection_interval=int(os.getenv("INFLUXDB_COLLECTION_INTERVAL", "300")),
    )


def load_datadog_config() -> DataDogConfig:
    """Load DataDog configuration from environment variables."""
    return DataDogConfig(
        enabled=os.getenv("DATADOG_ENABLED", "false").lower() == "true",
        api_key=os.getenv("DATADOG_API_KEY"),
        app_key=os.getenv("DATADOG_APP_KEY"),
        site=os.getenv("DATADOG_SITE", "datadoghq.com"),
        timeout=int(os.getenv("DATADOG_TIMEOUT", "30")),
        collection_interval=int(os.getenv("DATADOG_COLLECTION_INTERVAL", "300")),
    )


def create_prometheus_data_source_config() -> DataSourceConfig | None:
    """Create DataSourceConfig for Prometheus from environment variables."""
    config = load_prometheus_config()

    if not config.enabled:
        return None

    credentials = {}
    if config.bearer_token:
        credentials["bearer_token"] = config.bearer_token
    elif config.username and config.password:
        credentials["username"] = config.username
        credentials["password"] = config.password

    # Default metric mappings for common Prometheus metrics
    default_mappings = [
        MetricMapping(
            external_metric_name="http_requests_total",
            kachi_meter_key="api.calls",
            transformation_function="rate",
            customer_id_label="customer_id",
            scaling_factor=Decimal("1.0"),
        ),
        MetricMapping(
            external_metric_name="cpu_usage_seconds_total",
            kachi_meter_key="compute.ms",
            transformation_function="rate",
            customer_id_label="customer_id",
            scaling_factor=Decimal("1000.0"),  # Convert seconds to milliseconds
        ),
        MetricMapping(
            external_metric_name="memory_usage_bytes",
            kachi_meter_key="storage.gbh",
            transformation_function="avg",
            customer_id_label="customer_id",
            scaling_factor=Decimal("0.000000000931323"),  # Convert bytes to GB
        ),
    ]

    return DataSourceConfig(
        name="prometheus",
        type="prometheus",
        endpoint=config.endpoint,
        credentials=credentials,
        timeout=config.timeout,
        enabled=config.enabled,
        collection_interval=config.collection_interval,
        metric_mappings=default_mappings,
    )


def get_all_data_source_configs() -> list[DataSourceConfig]:
    """Get all configured data source configurations."""
    configs = []

    # Prometheus
    prometheus_config = create_prometheus_data_source_config()
    if prometheus_config:
        configs.append(prometheus_config)

    # Future: InfluxDB, DataDog, etc.

    return configs


def load_custom_metric_mappings() -> dict[str, list[MetricMapping]]:
    """Load custom metric mappings from configuration."""
    # This could be extended to load from JSON files, database, etc.
    # For now, return empty dict - mappings are defined in data source configs
    return {}


class MetricsConfigManager:
    """Manager for metrics collection configuration."""

    def __init__(self) -> None:
        self.global_config = load_metrics_config()
        self.data_source_configs = get_all_data_source_configs()
        self.custom_mappings = load_custom_metric_mappings()

    def get_enabled_data_sources(self) -> list[DataSourceConfig]:
        """Get all enabled data source configurations."""
        return [config for config in self.data_source_configs if config.enabled]

    def get_data_source_config(self, name: str) -> DataSourceConfig | None:
        """Get configuration for a specific data source."""
        for config in self.data_source_configs:
            if config.name == name:
                return config
        return None

    def add_custom_mapping(self, data_source: str, mapping: MetricMapping) -> None:
        """Add a custom metric mapping for a data source."""
        if data_source not in self.custom_mappings:
            self.custom_mappings[data_source] = []
        self.custom_mappings[data_source].append(mapping)

    def get_custom_mappings(self, data_source: str) -> list[MetricMapping]:
        """Get custom mappings for a data source."""
        return self.custom_mappings.get(data_source, [])


# Global configuration manager instance
config_manager = MetricsConfigManager()
