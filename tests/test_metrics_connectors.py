"""Tests for external metrics connectors."""

from datetime import datetime, timedelta
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from kachi.lib.metrics_connectors import (
    DataSourceConfig,
    MetricDataPoint,
    MetricMapping,
    MetricQuery,
    MetricsConnectorRegistry,
)
from kachi.lib.prometheus_connector import PrometheusConnector


class TestMetricsConnectorRegistry:
    """Test the metrics connector registry."""

    def test_register_and_get_connector(self):
        """Test registering and retrieving connectors."""
        registry = MetricsConnectorRegistry()

        # Create mock connector
        config = DataSourceConfig(
            name="test_prometheus",
            type="prometheus",
            endpoint="http://localhost:9090",
            enabled=True,
        )
        connector = PrometheusConnector(config)

        # Register connector
        registry.register(connector)

        # Retrieve connector
        retrieved = registry.get("test_prometheus")
        assert retrieved is not None
        assert retrieved.name == "test_prometheus"
        assert retrieved.type == "prometheus"

    def test_get_enabled_connectors(self):
        """Test getting only enabled connectors."""
        registry = MetricsConnectorRegistry()

        # Create enabled connector
        enabled_config = DataSourceConfig(
            name="enabled_prometheus",
            type="prometheus",
            endpoint="http://localhost:9090",
            enabled=True,
        )
        enabled_connector = PrometheusConnector(enabled_config)

        # Create disabled connector
        disabled_config = DataSourceConfig(
            name="disabled_prometheus",
            type="prometheus",
            endpoint="http://localhost:9091",
            enabled=False,
        )
        disabled_connector = PrometheusConnector(disabled_config)

        # Register both
        registry.register(enabled_connector)
        registry.register(disabled_connector)

        # Get enabled connectors
        enabled = registry.get_enabled()
        assert len(enabled) == 1
        assert enabled[0].name == "enabled_prometheus"

    def test_unregister_connector(self):
        """Test unregistering connectors."""
        registry = MetricsConnectorRegistry()

        config = DataSourceConfig(
            name="test_connector",
            type="prometheus",
            endpoint="http://localhost:9090",
            enabled=True,
        )
        connector = PrometheusConnector(config)

        # Register and verify
        registry.register(connector)
        assert registry.get("test_connector") is not None

        # Unregister and verify
        registry.unregister("test_connector")
        assert registry.get("test_connector") is None


class TestPrometheusConnector:
    """Test the Prometheus connector implementation."""

    def setup_method(self):
        """Set up test fixtures."""
        self.config = DataSourceConfig(
            name="test_prometheus",
            type="prometheus",
            endpoint="http://localhost:9090",
            credentials={"bearer_token": "test_token"},
            timeout=30,
            enabled=True,
            metric_mappings=[
                MetricMapping(
                    external_metric_name="http_requests_total",
                    kachi_meter_key="api.calls",
                    customer_id_label="customer_id",
                    scaling_factor=Decimal("1.0"),
                )
            ],
        )
        self.connector = PrometheusConnector(self.config)

    @pytest.mark.asyncio
    async def test_test_connection_success(self):
        """Test successful connection test."""
        mock_response = MagicMock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = {"status": "success"}

        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(
                return_value=mock_response
            )

            result = await self.connector.test_connection()
            assert result is True

    @pytest.mark.asyncio
    async def test_test_connection_failure(self):
        """Test failed connection test."""
        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(
                side_effect=Exception("Connection failed")
            )

            result = await self.connector.test_connection()
            assert result is False

    @pytest.mark.asyncio
    async def test_query_instant_metrics(self):
        """Test instant query execution."""
        mock_response = MagicMock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = {
            "status": "success",
            "data": {
                "result": [
                    {
                        "metric": {
                            "__name__": "http_requests_total",
                            "customer_id": str(uuid4()),
                            "method": "GET",
                        },
                        "value": [1640995200, "100"],
                    }
                ]
            },
        }

        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(
                return_value=mock_response
            )

            query = MetricQuery(
                query="http_requests_total",
                start_time=datetime.utcnow() - timedelta(hours=1),
                end_time=datetime.utcnow(),
            )

            result = await self.connector.query_metrics(query)

            assert result.success is True
            assert len(result.data_points) == 1
            assert result.data_points[0].metric_name == "http_requests_total"
            assert result.data_points[0].value == Decimal("100")

    @pytest.mark.asyncio
    async def test_query_range_metrics(self):
        """Test range query execution."""
        mock_response = MagicMock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = {
            "status": "success",
            "data": {
                "result": [
                    {
                        "metric": {
                            "__name__": "http_requests_total",
                            "customer_id": str(uuid4()),
                        },
                        "values": [
                            [1640995200, "100"],
                            [1640995260, "105"],
                        ],
                    }
                ]
            },
        }

        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(
                return_value=mock_response
            )

            query = MetricQuery(
                query="http_requests_total",
                start_time=datetime.utcnow() - timedelta(hours=1),
                end_time=datetime.utcnow(),
                step="1m",
            )

            result = await self.connector.query_metrics(query)

            assert result.success is True
            assert len(result.data_points) == 2
            assert result.data_points[0].value == Decimal("100")
            assert result.data_points[1].value == Decimal("105")

    @pytest.mark.asyncio
    async def test_get_available_metrics(self):
        """Test getting available metrics."""
        mock_response = MagicMock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = {
            "status": "success",
            "data": [
                "http_requests_total",
                "cpu_usage_seconds_total",
                "memory_usage_bytes",
            ],
        }

        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(
                return_value=mock_response
            )

            metrics = await self.connector.get_available_metrics()

            assert len(metrics) == 3
            assert "http_requests_total" in metrics
            assert "cpu_usage_seconds_total" in metrics
            assert "memory_usage_bytes" in metrics

    def test_get_customer_id_from_labels(self):
        """Test customer ID extraction from labels."""
        mapping = MetricMapping(
            external_metric_name="test_metric",
            kachi_meter_key="test.meter",
            customer_id_label="customer_id",
        )

        customer_id = uuid4()
        labels = {"customer_id": str(customer_id), "method": "GET"}

        extracted_id = self.connector.get_customer_id_from_labels(labels, mapping)
        assert extracted_id == customer_id

    def test_get_customer_id_from_labels_invalid(self):
        """Test customer ID extraction with invalid UUID."""
        mapping = MetricMapping(
            external_metric_name="test_metric",
            kachi_meter_key="test.meter",
            customer_id_label="customer_id",
        )

        labels = {"customer_id": "invalid-uuid", "method": "GET"}

        extracted_id = self.connector.get_customer_id_from_labels(labels, mapping)
        assert extracted_id is None

    def test_apply_transformation(self):
        """Test value transformation."""
        mapping = MetricMapping(
            external_metric_name="test_metric",
            kachi_meter_key="test.meter",
            scaling_factor=Decimal("2.5"),
        )

        original_value = Decimal("100")
        transformed = self.connector.apply_transformation(original_value, mapping)

        assert transformed == Decimal("250")

    def test_matches_label_filters(self):
        """Test label filter matching."""
        mapping = MetricMapping(
            external_metric_name="test_metric",
            kachi_meter_key="test.meter",
            label_filters={"method": "GET", "status": "200"},
        )

        # Matching labels
        matching_labels = {"method": "GET", "status": "200", "path": "/api/test"}
        assert self.connector.matches_label_filters(matching_labels, mapping) is True

        # Non-matching labels
        non_matching_labels = {"method": "POST", "status": "200", "path": "/api/test"}
        assert (
            self.connector.matches_label_filters(non_matching_labels, mapping) is False
        )


class TestMetricDataPoint:
    """Test the MetricDataPoint model."""

    def test_metric_data_point_creation(self):
        """Test creating a metric data point."""
        timestamp = datetime.utcnow()
        data_point = MetricDataPoint(
            timestamp=timestamp,
            value=Decimal("123.45"),
            labels={"customer_id": str(uuid4()), "method": "GET"},
            metric_name="http_requests_total",
            source_system="prometheus",
        )

        assert data_point.timestamp == timestamp
        assert data_point.value == Decimal("123.45")
        assert data_point.metric_name == "http_requests_total"
        assert data_point.source_system == "prometheus"
        assert "customer_id" in data_point.labels
        assert "method" in data_point.labels


class TestMetricMapping:
    """Test the MetricMapping model."""

    def test_metric_mapping_creation(self):
        """Test creating a metric mapping."""
        mapping = MetricMapping(
            external_metric_name="http_requests_total",
            kachi_meter_key="api.calls",
            transformation_function="rate",
            customer_id_label="customer_id",
            scaling_factor=Decimal("1.5"),
            label_filters={"method": "GET"},
        )

        assert mapping.external_metric_name == "http_requests_total"
        assert mapping.kachi_meter_key == "api.calls"
        assert mapping.transformation_function == "rate"
        assert mapping.customer_id_label == "customer_id"
        assert mapping.scaling_factor == Decimal("1.5")
        assert mapping.label_filters == {"method": "GET"}

    def test_metric_mapping_defaults(self):
        """Test metric mapping with default values."""
        mapping = MetricMapping(
            external_metric_name="test_metric",
            kachi_meter_key="test.meter",
        )

        assert mapping.transformation_function is None
        assert mapping.customer_id_label == "customer_id"
        assert mapping.scaling_factor == Decimal("1.0")
        assert mapping.label_filters == {}


if __name__ == "__main__":
    pytest.main([__file__])
