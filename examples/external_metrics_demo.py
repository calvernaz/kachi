#!/usr/bin/env python3
"""
Demo script for external metrics collection with Kachi.

This script demonstrates how to:
1. Configure external data sources (Prometheus)
2. Set up metric mappings
3. Collect metrics from external systems
4. Transform and store them as Kachi meter readings

Prerequisites:
- Prometheus running on localhost:9090 (or configure endpoint)
- Kachi database set up
- Environment variables configured
"""

import asyncio
import os
from datetime import datetime, timedelta
from decimal import Decimal
from uuid import uuid4

from kachi.apps.metrics_collector.main import MetricsCollectionService
from kachi.lib.db import get_session
from kachi.lib.metrics_config import create_prometheus_data_source_config
from kachi.lib.metrics_connectors import (
    MetricMapping,
    MetricQuery,
    metrics_registry,
)
from kachi.lib.models import Customer
from kachi.lib.prometheus_connector import create_prometheus_connector


async def setup_demo_data():
    """Set up demo customers for testing."""
    print("🔧 Setting up demo data...")

    async with get_session() as session:
        # Create demo customers
        customers = [
            Customer(
                id=uuid4(),
                name="Acme Corp",
                email="billing@acme.com",
                active=True,
            ),
            Customer(
                id=uuid4(),
                name="TechStart Inc",
                email="finance@techstart.com",
                active=True,
            ),
        ]

        for customer in customers:
            session.add(customer)

        await session.commit()

        print(f"✅ Created {len(customers)} demo customers")
        return [str(c.id) for c in customers]


async def configure_prometheus_connector():
    """Configure and register Prometheus connector."""
    print("🔌 Configuring Prometheus connector...")

    # Create configuration
    config = create_prometheus_data_source_config()
    if not config:
        print("❌ Prometheus not enabled in configuration")
        return None

    # Override with demo settings
    config.endpoint = os.getenv("PROMETHEUS_ENDPOINT", "http://localhost:9090")
    config.enabled = True

    # Add demo metric mappings
    demo_mappings = [
        MetricMapping(
            external_metric_name="prometheus_http_requests_total",
            kachi_meter_key="api.calls",
            transformation_function="rate",
            customer_id_label="customer_id",
            scaling_factor=Decimal("1.0"),
        ),
        MetricMapping(
            external_metric_name="process_cpu_seconds_total",
            kachi_meter_key="compute.ms",
            transformation_function="rate",
            customer_id_label="customer_id",
            scaling_factor=Decimal("1000.0"),  # Convert seconds to milliseconds
        ),
        MetricMapping(
            external_metric_name="process_resident_memory_bytes",
            kachi_meter_key="storage.gbh",
            transformation_function="avg",
            customer_id_label="customer_id",
            scaling_factor=Decimal("0.000000000931323"),  # Convert bytes to GB
        ),
    ]

    config.metric_mappings = demo_mappings

    # Create and register connector
    connector = create_prometheus_connector(config)
    metrics_registry.register(connector)

    print(f"✅ Registered Prometheus connector: {config.endpoint}")
    print(f"📊 Configured {len(demo_mappings)} metric mappings")

    return connector


async def test_prometheus_connection(connector):
    """Test connection to Prometheus."""
    print("🔍 Testing Prometheus connection...")

    try:
        is_healthy = await connector.test_connection()
        if is_healthy:
            print("✅ Prometheus connection successful")

            # Get available metrics
            metrics = await connector.get_available_metrics()
            print(f"📈 Found {len(metrics)} available metrics")

            # Show first few metrics
            if metrics:
                print("📋 Sample metrics:")
                for metric in metrics[:5]:
                    print(f"   - {metric}")
                if len(metrics) > 5:
                    print(f"   ... and {len(metrics) - 5} more")

            return True
        else:
            print("❌ Prometheus connection failed")
            return False
    except Exception as e:
        print(f"❌ Connection test error: {e}")
        return False


async def demonstrate_metric_query(connector):
    """Demonstrate querying metrics from Prometheus."""
    print("\n🔍 Demonstrating metric queries...")

    # Query Prometheus internal metrics as examples
    sample_queries = [
        "prometheus_http_requests_total",
        "prometheus_config_last_reload_successful",
        "up",
    ]

    for query_str in sample_queries:
        try:
            print(f"\n📊 Querying: {query_str}")

            query = MetricQuery(
                query=query_str,
                start_time=datetime.utcnow() - timedelta(minutes=5),
                end_time=datetime.utcnow(),
                step="1m",
            )

            result = await connector.query_metrics(query)

            if result.success:
                print(f"✅ Query successful: {len(result.data_points)} data points")

                # Show sample data points
                for i, dp in enumerate(result.data_points[:3]):
                    print(
                        f"   [{i+1}] {dp.timestamp}: {dp.value} (labels: {list(dp.labels.keys())})"
                    )

                if len(result.data_points) > 3:
                    print(f"   ... and {len(result.data_points) - 3} more data points")
            else:
                print(f"❌ Query failed: {result.errors}")

        except Exception as e:
            print(f"❌ Query error: {e}")


async def demonstrate_metrics_collection():
    """Demonstrate full metrics collection pipeline."""
    print("\n🚀 Demonstrating metrics collection pipeline...")

    async with get_session() as session:
        service = MetricsCollectionService(session)

        try:
            # Collect from all connectors
            results = await service.collect_all_metrics()

            print("📊 Collection Results:")
            for connector_name, result in results.items():
                if result.get("success"):
                    print(f"✅ {connector_name}:")
                    print(
                        f"   - Mappings processed: {result.get('mappings_processed', 0)}"
                    )
                    print(f"   - Data points: {result.get('total_data_points', 0)}")
                    print(
                        f"   - Meter readings: {result.get('total_meter_readings', 0)}"
                    )
                else:
                    print(f"❌ {connector_name}: {result.get('error', 'Unknown error')}")

        except Exception as e:
            print(f"❌ Collection failed: {e}")


async def show_api_endpoints():
    """Show available API endpoints for metrics collection."""
    print("\n🌐 Available API Endpoints:")
    print("GET  /api/metrics/connectors              - List all connectors")
    print("GET  /api/metrics/connectors/{name}       - Get connector details")
    print("POST /api/metrics/collect                 - Trigger collection")
    print("GET  /api/metrics/available-metrics/{name} - Get available metrics")
    print("POST /api/metrics/mappings/{name}         - Add metric mapping")
    print("GET  /api/metrics/config                  - Get configuration")
    print("GET  /api/metrics/status                  - Get collection status")

    print("\n📝 Example API calls:")
    print("curl http://localhost:8002/api/metrics/connectors")
    print("curl -X POST http://localhost:8002/api/metrics/collect")
    print("curl http://localhost:8002/api/metrics/available-metrics/prometheus")


async def main():
    """Main demo function."""
    print("🎯 Kachi External Metrics Collection Demo")
    print("=" * 50)

    # Setup demo data
    await setup_demo_data()

    # Configure Prometheus connector
    connector = await configure_prometheus_connector()
    if not connector:
        print("❌ Failed to configure Prometheus connector")
        return

    # Test connection
    if not await test_prometheus_connection(connector):
        print("⚠️  Prometheus not available, but configuration is ready")
        print("💡 Start Prometheus on localhost:9090 to see live data")
    else:
        # Demonstrate queries
        await demonstrate_metric_query(connector)

        # Demonstrate collection
        await demonstrate_metrics_collection()

    # Show API endpoints
    await show_api_endpoints()

    print("\n🎉 Demo completed!")
    print("💡 Next steps:")
    print("   1. Configure your Prometheus endpoint in .env")
    print("   2. Add customer_id labels to your metrics")
    print("   3. Customize metric mappings for your use case")
    print("   4. Set up scheduled collection with Celery")


if __name__ == "__main__":
    asyncio.run(main())
