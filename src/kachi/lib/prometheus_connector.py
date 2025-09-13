"""Prometheus metrics connector implementation."""

from datetime import datetime
from decimal import Decimal
from typing import Any

import httpx
import structlog

from kachi.lib.metrics_connectors import (
    DataSourceConfig,
    MetricCollectionResult,
    MetricDataPoint,
    MetricQuery,
    MetricsConnector,
)

logger = structlog.get_logger()


class PrometheusConnector(MetricsConnector):
    """Connector for Prometheus metrics collection."""

    def __init__(self, config: DataSourceConfig):
        super().__init__(config)
        self.base_url = config.endpoint.rstrip("/")
        self.timeout = config.timeout
        self.headers = self._build_headers()

    def _build_headers(self) -> dict[str, str]:
        """Build HTTP headers for Prometheus API requests."""
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
        }

        # Add authentication if configured
        if "bearer_token" in self.config.credentials:
            headers[
                "Authorization"
            ] = f"Bearer {self.config.credentials['bearer_token']}"
        elif (
            "username" in self.config.credentials
            and "password" in self.config.credentials
        ):
            # Basic auth will be handled by httpx
            pass

        return headers

    async def test_connection(self) -> bool:
        """Test connection to Prometheus."""
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                auth = self._get_auth()
                response = await client.get(
                    f"{self.base_url}/api/v1/query",
                    params={"query": "up"},
                    headers=self.headers,
                    auth=auth,
                )
                response.raise_for_status()
                data = response.json()
                return data.get("status") == "success"
        except Exception as e:
            await logger.aerror(
                "Prometheus connection test failed",
                connector=self.name,
                error=str(e),
                exc_info=True,
            )
            return False

    async def query_metrics(self, query: MetricQuery) -> MetricCollectionResult:
        """Query metrics from Prometheus."""
        try:
            if query.step:
                # Range query
                return await self._query_range(query)
            else:
                # Instant query
                return await self._query_instant(query)
        except Exception as e:
            await logger.aerror(
                "Prometheus query failed",
                connector=self.name,
                query=query.query,
                error=str(e),
                exc_info=True,
            )
            return MetricCollectionResult(
                success=False,
                errors=[f"Query failed: {e!s}"],
                collection_timestamp=datetime.utcnow(),
                source_system="prometheus",
                query_info={"query": query.query},
            )

    async def _query_instant(self, query: MetricQuery) -> MetricCollectionResult:
        """Execute instant query against Prometheus."""
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            auth = self._get_auth()
            params = {
                "query": query.query,
                "time": query.end_time.isoformat(),
            }

            response = await client.get(
                f"{self.base_url}/api/v1/query",
                params=params,
                headers=self.headers,
                auth=auth,
            )
            response.raise_for_status()

            data = response.json()
            if data.get("status") != "success":
                return MetricCollectionResult(
                    success=False,
                    errors=[data.get("error", "Unknown error")],
                    collection_timestamp=datetime.utcnow(),
                    source_system="prometheus",
                    query_info={"query": query.query, "type": "instant"},
                )

            data_points = []
            result_data = data.get("data", {}).get("result", [])

            for result in result_data:
                metric_name = result.get("metric", {}).get("__name__", "unknown")
                labels = result.get("metric", {})
                value_data = result.get("value", [])

                if len(value_data) >= 2:
                    timestamp = datetime.fromtimestamp(float(value_data[0]))
                    value = Decimal(str(value_data[1]))

                    data_points.append(
                        MetricDataPoint(
                            timestamp=timestamp,
                            value=value,
                            labels=labels,
                            metric_name=metric_name,
                            source_system="prometheus",
                        )
                    )

            return MetricCollectionResult(
                success=True,
                data_points=data_points,
                collection_timestamp=datetime.utcnow(),
                source_system="prometheus",
                query_info={
                    "query": query.query,
                    "type": "instant",
                    "results": len(data_points),
                },
            )

    async def _query_range(self, query: MetricQuery) -> MetricCollectionResult:
        """Execute range query against Prometheus."""
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            auth = self._get_auth()
            params = {
                "query": query.query,
                "start": query.start_time.isoformat(),
                "end": query.end_time.isoformat(),
                "step": query.step,
            }

            response = await client.get(
                f"{self.base_url}/api/v1/query_range",
                params=params,
                headers=self.headers,
                auth=auth,
            )
            response.raise_for_status()

            data = response.json()
            if data.get("status") != "success":
                return MetricCollectionResult(
                    success=False,
                    errors=[data.get("error", "Unknown error")],
                    collection_timestamp=datetime.utcnow(),
                    source_system="prometheus",
                    query_info={"query": query.query, "type": "range"},
                )

            data_points = []
            result_data = data.get("data", {}).get("result", [])

            for result in result_data:
                metric_name = result.get("metric", {}).get("__name__", "unknown")
                labels = result.get("metric", {})
                values = result.get("values", [])

                for value_data in values:
                    if len(value_data) >= 2:
                        timestamp = datetime.fromtimestamp(float(value_data[0]))
                        value = Decimal(str(value_data[1]))

                        data_points.append(
                            MetricDataPoint(
                                timestamp=timestamp,
                                value=value,
                                labels=labels,
                                metric_name=metric_name,
                                source_system="prometheus",
                            )
                        )

            return MetricCollectionResult(
                success=True,
                data_points=data_points,
                collection_timestamp=datetime.utcnow(),
                source_system="prometheus",
                query_info={
                    "query": query.query,
                    "type": "range",
                    "results": len(data_points),
                },
            )

    async def get_available_metrics(self) -> list[str]:
        """Get list of available metrics from Prometheus."""
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                auth = self._get_auth()
                response = await client.get(
                    f"{self.base_url}/api/v1/label/__name__/values",
                    headers=self.headers,
                    auth=auth,
                )
                response.raise_for_status()

                data = response.json()
                if data.get("status") == "success":
                    return data.get("data", [])
                else:
                    await logger.aerror(
                        "Failed to get available metrics",
                        connector=self.name,
                        error=data.get("error"),
                    )
                    return []
        except Exception as e:
            await logger.aerror(
                "Failed to get available metrics",
                connector=self.name,
                error=str(e),
                exc_info=True,
            )
            return []

    async def get_metric_metadata(self, metric_name: str) -> dict[str, Any]:
        """Get metadata for a specific metric."""
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                auth = self._get_auth()
                response = await client.get(
                    f"{self.base_url}/api/v1/metadata",
                    params={"metric": metric_name},
                    headers=self.headers,
                    auth=auth,
                )
                response.raise_for_status()

                data = response.json()
                if data.get("status") == "success":
                    return data.get("data", {}).get(metric_name, [{}])[0]
                else:
                    return {}
        except Exception as e:
            await logger.aerror(
                "Failed to get metric metadata",
                connector=self.name,
                metric=metric_name,
                error=str(e),
                exc_info=True,
            )
            return {}

    def _get_auth(self) -> httpx.Auth | None:
        """Get authentication for HTTP requests."""
        if (
            "username" in self.config.credentials
            and "password" in self.config.credentials
        ):
            return httpx.BasicAuth(
                self.config.credentials["username"],
                self.config.credentials["password"],
            )
        return None


def create_prometheus_connector(config: DataSourceConfig) -> PrometheusConnector:
    """Factory function to create a Prometheus connector."""
    if config.type != "prometheus":
        raise ValueError(f"Invalid config type for Prometheus connector: {config.type}")

    return PrometheusConnector(config)
