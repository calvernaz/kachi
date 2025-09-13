"""Mock Dashboard API server for testing without database."""

import math
import random
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Any

from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

app = FastAPI(
    title="Kachi Dashboard API (Mock)",
    description="Mock customer usage dashboard for testing",
    version="1.0.0",
)

# CORS middleware for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://localhost:5174",
        "http://localhost:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class TimeSeriesPoint(BaseModel):
    """Time series data point."""

    timestamp: datetime
    value: Decimal
    meter_key: str


class UsageTrend(BaseModel):
    """Usage trend data for charts."""

    period: str
    data_points: list[TimeSeriesPoint]
    total_usage: Decimal
    average_usage: Decimal
    peak_usage: Decimal
    growth_rate: float


class DashboardMetrics(BaseModel):
    """Real-time dashboard metrics."""

    total_customers: int
    active_customers: int
    monthly_revenue: Decimal
    daily_revenue: Decimal
    total_api_calls_today: int
    total_workflows_today: int
    average_response_time: float
    system_health_score: float


@app.get("/health")
async def health_check() -> dict[str, str]:
    """Health check endpoint."""
    return {"status": "healthy", "service": "dashboard_api_mock"}


@app.get("/api/metrics/dashboard", response_model=DashboardMetrics)
async def get_dashboard_metrics() -> DashboardMetrics:
    """Get real-time dashboard metrics (mock data)."""
    return DashboardMetrics(
        total_customers=42 + random.randint(-5, 5),
        active_customers=38 + random.randint(-3, 3),
        monthly_revenue=Decimal(str(125000 + random.randint(-10000, 15000))),
        daily_revenue=Decimal(str(4200 + random.randint(-500, 800))),
        total_api_calls_today=45000 + random.randint(-5000, 8000),
        total_workflows_today=1250 + random.randint(-100, 200),
        average_response_time=125.5 + random.uniform(-20, 30),
        system_health_score=98.5 + random.uniform(-3, 1.5),
    )


@app.get("/api/usage/trends", response_model=UsageTrend)
async def get_usage_trends(
    period: str = Query("daily", description="Period: daily, weekly, monthly"),
    meter_key: str = Query(None, description="Specific meter key (optional)"),
) -> UsageTrend:
    """Get usage trends for charts (mock data)."""

    # Generate mock time series data
    now = datetime.utcnow()
    data_points = []

    if period == "daily":
        # Last 30 days
        for i in range(30):
            date = now - timedelta(days=29 - i)
            base_value = 1000 + (i * 50)  # Growing trend
            noise = random.randint(-200, 300)
            value = max(0, base_value + noise)

            data_points.append(
                TimeSeriesPoint(
                    timestamp=date,
                    value=Decimal(str(value)),
                    meter_key=meter_key or "all",
                )
            )

    elif period == "weekly":
        # Last 12 weeks
        for i in range(12):
            date = now - timedelta(weeks=11 - i)
            base_value = 7000 + (i * 300)  # Growing trend
            noise = random.randint(-1000, 1500)
            value = max(0, base_value + noise)

            data_points.append(
                TimeSeriesPoint(
                    timestamp=date,
                    value=Decimal(str(value)),
                    meter_key=meter_key or "all",
                )
            )

    elif period == "monthly":
        # Last 12 months
        for i in range(12):
            date = now - timedelta(days=30 * (11 - i))
            base_value = 30000 + (i * 2000)  # Growing trend
            noise = random.randint(-5000, 8000)
            value = max(0, base_value + noise)

            data_points.append(
                TimeSeriesPoint(
                    timestamp=date,
                    value=Decimal(str(value)),
                    meter_key=meter_key or "all",
                )
            )

    # Calculate statistics
    values = [float(point.value) for point in data_points]
    total_usage = sum(values)
    average_usage = total_usage / len(values) if values else 0
    peak_usage = max(values) if values else 0

    # Calculate growth rate
    growth_rate = 0.0
    if len(values) >= 2 and values[0] > 0:
        growth_rate = ((values[-1] - values[0]) / values[0]) * 100

    return UsageTrend(
        period=period,
        data_points=data_points,
        total_usage=Decimal(str(total_usage)),
        average_usage=Decimal(str(average_usage)),
        peak_usage=Decimal(str(peak_usage)),
        growth_rate=growth_rate,
    )


@app.get("/api/customers")
async def list_customers() -> list[dict[str, Any]]:
    """List customers (mock data)."""
    customers = []
    for i in range(5):
        customers.append(
            {
                "id": f"customer-{i + 1}",
                "name": f"Customer {i + 1}",
                "currency": "EUR",
                "created_at": (
                    datetime.utcnow() - timedelta(days=random.randint(30, 365))
                ).isoformat(),
            }
        )
    return customers


@app.get("/api/analytics/segmentation")
async def get_customer_segmentation(
    metric: str = "revenue",  # noqa: ARG001
) -> dict[str, Any]:
    """Get customer segmentation data (mock)."""

    # Generate mock customer data
    customers = []
    for i in range(42):
        customers.append(
            {
                "id": f"customer-{i + 1}",
                "name": f"Customer {i + 1}",
                "revenue": random.randint(1000, 50000),
                "usage": random.randint(5000, 100000),
                "growth": random.uniform(-20, 50),
                "riskScore": random.randint(10, 90),
            }
        )

    # Segment customers
    segments = [
        {
            "name": "Enterprise",
            "count": 8,
            "percentage": 19,
            "icon": "office-building",
            "gradient": "from-blue-500 to-blue-600",
            "customers": customers[:8],
        },
        {
            "name": "Growth",
            "count": 15,
            "percentage": 36,
            "icon": "trending-up",
            "gradient": "from-green-500 to-green-600",
            "customers": customers[8:23],
        },
        {
            "name": "Stable",
            "count": 12,
            "percentage": 29,
            "icon": "scale",
            "gradient": "from-yellow-500 to-yellow-600",
            "customers": customers[23:35],
        },
        {
            "name": "At Risk",
            "count": 7,
            "percentage": 17,
            "icon": "exclamation-triangle",
            "gradient": "from-red-500 to-red-600",
            "customers": customers[35:],
        },
    ]

    return {"segments": segments}


@app.get("/api/analytics/forecast")
async def get_usage_forecast(
    period: str = "30",
    meter_key: str = "all",  # noqa: ARG001
) -> dict[str, Any]:
    """Get usage forecasting data (mock)."""

    period_days = int(period)
    now = datetime.utcnow()

    # Generate historical data (last 30 days)
    historical = []
    for i in range(30):
        date = now - timedelta(days=29 - i)
        base_value = 1000 + (i * 30)
        noise = random.randint(-200, 300)
        value = max(0, base_value + noise)

        historical.append({"date": date.strftime("%Y-%m-%d"), "value": value})

    # Generate forecast data
    forecast = []
    last_value = historical[-1]["value"]
    growth_rate = random.uniform(0.02, 0.08)  # 2-8% daily growth

    for i in range(period_days):
        date = now + timedelta(days=i + 1)
        predicted_value = last_value * (1 + growth_rate) ** (i + 1)
        noise = random.randint(-100, 150)
        value = max(0, predicted_value + noise)

        # Confidence bands (±20%)
        upper = value * 1.2
        lower = value * 0.8

        forecast.append(
            {
                "date": date.strftime("%Y-%m-%d"),
                "value": int(value),
                "upper": int(upper),
                "lower": int(lower),
            }
        )

    peak_day = max(forecast, key=lambda x: x["value"])
    total_predicted = sum(f["value"] for f in forecast)

    return {
        "predictedUsage": total_predicted,
        "confidence": random.randint(85, 95),
        "growthRate": round(growth_rate * 100, 1),
        "peakDay": peak_day["date"],
        "historical": historical,
        "forecast": forecast,
        "insights": [
            f"Usage is trending upward with {growth_rate * 100:.1f}% daily growth",
            f"Peak usage expected on {peak_day['date']}",
            "Weekend usage typically 30% lower than weekdays",
            "API calls show strongest growth pattern",
        ],
        "recommendations": [
            "Consider scaling infrastructure for peak periods",
            "Monitor customer usage patterns for optimization",
            "Set up alerts for unusual spikes",
            "Review pricing tiers for high-growth customers",
        ],
    }


@app.get("/api/analytics/anomalies")
async def get_anomaly_detection(
    time_range: str = "24h",  # noqa: ARG001
    sensitivity: str = "medium",  # noqa: ARG001
) -> dict[str, Any]:
    """Get anomaly detection data (mock)."""

    # Generate mock anomalies
    anomalies = []
    severities = ["critical", "warning", "info"]

    for i in range(random.randint(5, 15)):
        severity = random.choice(severities)
        timestamp = datetime.utcnow() - timedelta(hours=random.randint(1, 24))

        anomalies.append(
            {
                "id": f"anomaly-{i + 1}",
                "title": f"Unusual {random.choice(['API', 'Usage', 'Response Time', 'Error Rate'])} Pattern",
                "description": f"Detected {random.randint(150, 500)}% deviation from normal baseline",
                "severity": severity,
                "customer": f"Customer {random.randint(1, 10)}",
                "meter": random.choice(
                    ["api.calls", "workflows", "llm.tokens", "storage"]
                ),
                "timestamp": timestamp.isoformat(),
                "deviation": f"+{random.randint(150, 500)}%",
            }
        )

    # Generate timeline data
    timeline = []
    for i in range(24):  # Last 24 hours
        timestamp = datetime.utcnow() - timedelta(hours=23 - i)
        severity = random.choice(severities)
        count = random.randint(0, 5)

        timeline.append(
            {"timestamp": timestamp.isoformat(), "count": count, "severity": severity}
        )

    critical_count = len([a for a in anomalies if a["severity"] == "critical"])
    warning_count = len([a for a in anomalies if a["severity"] == "warning"])
    info_count = len([a for a in anomalies if a["severity"] == "info"])

    health_score = max(
        0, 100 - (critical_count * 20) - (warning_count * 10) - (info_count * 5)
    )

    return {
        "critical": critical_count,
        "warning": warning_count,
        "info": info_count,
        "healthScore": health_score,
        "recent": sorted(anomalies, key=lambda x: x["timestamp"], reverse=True)[:10],
        "timeline": timeline,
        "patterns": [
            "Spike in API calls during business hours",
            "Increased error rates on weekends",
            "Storage usage growing faster than expected",
            "Response times degrading for large customers",
        ],
        "actions": [
            "Investigate high-usage customers",
            "Review error logs for patterns",
            "Scale storage infrastructure",
            "Optimize API response times",
        ],
    }


@app.get("/api/customers/{customer_id}/usage/detailed")
async def get_customer_detailed_usage(
    customer_id: str,
    start_date: str = Query(..., description="Start date (YYYY-MM-DD)"),
    end_date: str = Query(..., description="End date (YYYY-MM-DD)"),
    granularity: str = Query("daily", description="Granularity: hourly, daily, weekly"),
    meter_keys: str = Query(None, description="Comma-separated meter keys"),
) -> dict[str, Any]:
    """Get detailed usage data for a specific customer."""

    start = datetime.fromisoformat(start_date)
    end = datetime.fromisoformat(end_date)

    # Generate time series based on granularity
    data_points = []
    if granularity == "hourly":
        current = start
        while current <= end:
            for meter in ["api.calls", "workflows", "llm.tokens", "storage"]:
                if not meter_keys or meter in meter_keys.split(","):
                    data_points.append(
                        {
                            "timestamp": current.isoformat(),
                            "meter_key": meter,
                            "value": random.randint(10, 500),
                            "unit": "count" if meter != "storage" else "GB",
                        }
                    )
            current += timedelta(hours=1)

    elif granularity == "daily":
        current = start
        while current <= end:
            for meter in ["api.calls", "workflows", "llm.tokens", "storage"]:
                if not meter_keys or meter in meter_keys.split(","):
                    data_points.append(
                        {
                            "timestamp": current.isoformat(),
                            "meter_key": meter,
                            "value": random.randint(1000, 10000),
                            "unit": "count" if meter != "storage" else "GB",
                        }
                    )
            current += timedelta(days=1)

    # Calculate aggregations
    total_usage = sum(point["value"] for point in data_points)
    avg_usage = total_usage / len(data_points) if data_points else 0

    return {
        "customer_id": customer_id,
        "period": {"start": start_date, "end": end_date},
        "granularity": granularity,
        "data_points": data_points,
        "summary": {
            "total_usage": total_usage,
            "average_usage": round(avg_usage, 2),
            "peak_usage": max((p["value"] for p in data_points), default=0),
            "unique_meters": len({p["meter_key"] for p in data_points}),
        },
    }


@app.get("/api/usage/comparison")
async def get_usage_comparison(
    customer_ids: str = Query(..., description="Comma-separated customer IDs"),
    period: str = Query("30d", description="Period: 7d, 30d, 90d"),
    metric: str = Query("total", description="Metric: total, average, peak"),
) -> dict[str, Any]:
    """Compare usage across multiple customers."""

    customer_list = customer_ids.split(",")
    period_days = int(period.replace("d", ""))

    comparison_data = []
    for customer_id in customer_list:
        # Generate mock usage data
        daily_usage = []
        for i in range(period_days):
            date = datetime.utcnow() - timedelta(days=period_days - 1 - i)
            usage = random.randint(500, 5000)
            daily_usage.append({"date": date.strftime("%Y-%m-%d"), "value": usage})

        total = sum(d["value"] for d in daily_usage)
        average = total / len(daily_usage)
        peak = max(d["value"] for d in daily_usage)

        comparison_data.append(
            {
                "customer_id": customer_id,
                "customer_name": f"Customer {customer_id}",
                "daily_usage": daily_usage,
                "metrics": {
                    "total": total,
                    "average": round(average, 2),
                    "peak": peak,
                    "growth_rate": random.uniform(-10, 25),
                },
            }
        )

    return {
        "period": period,
        "metric": metric,
        "customers": comparison_data,
        "insights": [
            f"Top performer: {max(comparison_data, key=lambda x: x['metrics']['total'])['customer_name']}",
            f"Fastest growing: {max(comparison_data, key=lambda x: x['metrics']['growth_rate'])['customer_name']}",
            f"Average usage across all customers: {sum(c['metrics']['total'] for c in comparison_data) / len(comparison_data):.0f}",
        ],
    }


@app.get("/api/billing/preview")
async def get_billing_preview(
    customer_id: str,
    usage_scenario: str = Query(
        "current", description="Scenario: current, optimistic, pessimistic"
    ),
    period_start: str = Query("2024-01-01", description="Period start (YYYY-MM-DD)"),
    period_end: str = Query("2024-01-31", description="Period end (YYYY-MM-DD)"),
) -> dict[str, Any]:
    """Generate billing preview for a customer."""

    # Mock pricing tiers
    pricing_tiers = {
        "api.calls": [
            {"from": 0, "to": 10000, "price": 0.001},
            {"from": 10000, "to": 100000, "price": 0.0008},
            {"from": 100000, "to": None, "price": 0.0005},
        ],
        "workflows": [
            {"from": 0, "to": 1000, "price": 0.01},
            {"from": 1000, "to": 10000, "price": 0.008},
            {"from": 10000, "to": None, "price": 0.005},
        ],
    }

    # Generate usage based on scenario
    multiplier = {"current": 1.0, "optimistic": 1.3, "pessimistic": 0.7}[usage_scenario]

    usage_data = {
        "api.calls": int(45000 * multiplier),
        "workflows": int(2500 * multiplier),
        "llm.tokens": int(150000 * multiplier),
        "storage": int(50 * multiplier),
    }

    # Calculate costs
    line_items = []
    total_cost = 0

    for meter, usage in usage_data.items():
        if meter in pricing_tiers:
            cost = 0
            remaining = usage

            for tier in pricing_tiers[meter]:
                tier_usage = min(remaining, (tier["to"] or float("inf")) - tier["from"])
                tier_cost = tier_usage * tier["price"]
                cost += tier_cost
                remaining -= tier_usage

                if remaining <= 0:
                    break

            line_items.append(
                {
                    "meter_key": meter,
                    "usage": usage,
                    "unit_price": pricing_tiers[meter][0]["price"],
                    "cost": round(cost, 2),
                    "tier_breakdown": [
                        {
                            "tier": f"{tier['from']:,} - {tier['to'] or '∞'}",
                            "price": tier["price"],
                            "usage_in_tier": min(
                                usage - tier["from"],
                                (tier["to"] or usage) - tier["from"],
                            )
                            if usage > tier["from"]
                            else 0,
                        }
                        for tier in pricing_tiers[meter]
                    ],
                }
            )
            total_cost += cost
        else:
            # Flat rate for other meters
            flat_rate = 0.002
            cost = usage * flat_rate
            line_items.append(
                {
                    "meter_key": meter,
                    "usage": usage,
                    "unit_price": flat_rate,
                    "cost": round(cost, 2),
                }
            )
            total_cost += cost

    return {
        "customer_id": customer_id,
        "scenario": usage_scenario,
        "period": {"start": period_start, "end": period_end},
        "usage_data": usage_data,
        "line_items": line_items,
        "summary": {
            "subtotal": round(total_cost, 2),
            "tax": round(total_cost * 0.08, 2),  # 8% tax
            "total": round(total_cost * 1.08, 2),
            "currency": "USD",
        },
        "recommendations": [
            "Consider upgrading to volume discount tier",
            "API usage is approaching next pricing tier",
            "Storage optimization could reduce costs by 15%",
        ],
    }


@app.get("/api/analytics/revenue")
async def get_revenue_analytics(
    period: str = Query("30d", description="Period: 7d, 30d, 90d, 1y"),
    breakdown: str = Query("daily", description="Breakdown: daily, weekly, monthly"),
    customer_segment: str = Query(
        "all", description="Segment: all, enterprise, growth, stable, at_risk"
    ),
) -> dict[str, Any]:
    """Get revenue analytics with various breakdowns."""

    period_days = {"7d": 7, "30d": 30, "90d": 90, "1y": 365}[period]

    # Generate revenue data
    revenue_data = []
    total_revenue = 0

    if breakdown == "daily":
        for i in range(period_days):
            date = datetime.utcnow() - timedelta(days=period_days - 1 - i)
            revenue = random.randint(1000, 8000)
            total_revenue += revenue
            revenue_data.append(
                {
                    "date": date.strftime("%Y-%m-%d"),
                    "revenue": revenue,
                    "customers": random.randint(20, 50),
                    "avg_revenue_per_customer": round(
                        revenue / random.randint(20, 50), 2
                    ),
                }
            )

    # Calculate metrics
    avg_daily_revenue = total_revenue / len(revenue_data)
    growth_rate = random.uniform(-5, 15)

    return {
        "period": period,
        "breakdown": breakdown,
        "customer_segment": customer_segment,
        "revenue_data": revenue_data,
        "metrics": {
            "total_revenue": total_revenue,
            "average_daily_revenue": round(avg_daily_revenue, 2),
            "growth_rate": round(growth_rate, 2),
            "highest_day": max(revenue_data, key=lambda x: x["revenue"]),
            "lowest_day": min(revenue_data, key=lambda x: x["revenue"]),
        },
        "insights": [
            f"Revenue grew by {growth_rate:.1f}% compared to previous period",
            f"Average daily revenue: ${avg_daily_revenue:.0f}",
            "Weekend revenue typically 20% lower than weekdays",
            "Enterprise customers contribute 60% of total revenue",
        ],
    }


@app.get("/api/alerts")
async def get_alerts(
    severity: str = Query("all", description="Severity: all, critical, warning, info"),
    status: str = Query("active", description="Status: all, active, resolved"),
    limit: int = Query(50, description="Maximum number of alerts"),
) -> dict[str, Any]:
    """Get system alerts and notifications."""

    alert_types = [
        "Usage spike detected",
        "API rate limit approaching",
        "Storage quota exceeded",
        "Billing threshold reached",
        "Customer churn risk",
        "System performance degraded",
        "Integration failure",
        "Anomaly detected",
    ]

    severities = ["critical", "warning", "info"]
    statuses = ["active", "resolved"]

    alerts = []
    for i in range(min(limit, random.randint(10, 30))):
        alert_severity = random.choice(severities)
        alert_status = random.choice(statuses)

        if severity not in ("all", alert_severity):
            continue
        if status not in ("all", alert_status):
            continue

        alerts.append(
            {
                "id": f"alert-{i + 1}",
                "title": random.choice(alert_types),
                "description": f"Alert description for {random.choice(alert_types).lower()}",
                "severity": alert_severity,
                "status": alert_status,
                "customer_id": f"customer-{random.randint(1, 20)}"
                if random.random() > 0.3
                else None,
                "meter_key": random.choice(
                    ["api.calls", "workflows", "llm.tokens", "storage"]
                )
                if random.random() > 0.5
                else None,
                "created_at": (
                    datetime.utcnow() - timedelta(hours=random.randint(1, 72))
                ).isoformat(),
                "resolved_at": (
                    datetime.utcnow() - timedelta(hours=random.randint(1, 24))
                ).isoformat()
                if alert_status == "resolved"
                else None,
                "actions": [
                    "Investigate customer usage patterns",
                    "Check system performance metrics",
                    "Review billing configuration",
                ],
            }
        )

    # Sort by creation time (newest first)
    alerts.sort(key=lambda x: x["created_at"], reverse=True)

    return {
        "alerts": alerts[:limit],
        "summary": {
            "total": len(alerts),
            "critical": len([a for a in alerts if a["severity"] == "critical"]),
            "warning": len([a for a in alerts if a["severity"] == "warning"]),
            "info": len([a for a in alerts if a["severity"] == "info"]),
            "active": len([a for a in alerts if a["status"] == "active"]),
            "resolved": len([a for a in alerts if a["status"] == "resolved"]),
        },
    }


@app.get("/api/system/health")
async def get_system_health() -> dict[str, Any]:
    """Get comprehensive system health metrics."""

    components = [
        {
            "name": "API Gateway",
            "status": "healthy",
            "response_time": random.randint(50, 150),
        },
        {
            "name": "Database",
            "status": "healthy",
            "response_time": random.randint(10, 50),
        },
        {
            "name": "Redis Cache",
            "status": "healthy",
            "response_time": random.randint(1, 10),
        },
        {
            "name": "Billing Service",
            "status": "healthy",
            "response_time": random.randint(100, 300),
        },
        {
            "name": "Analytics Engine",
            "status": "degraded" if random.random() > 0.8 else "healthy",
            "response_time": random.randint(200, 500),
        },
        {
            "name": "Notification Service",
            "status": "healthy",
            "response_time": random.randint(50, 200),
        },
    ]

    # Calculate overall health score
    healthy_components = len([c for c in components if c["status"] == "healthy"])
    health_score = (healthy_components / len(components)) * 100

    return {
        "overall_status": "healthy"
        if health_score > 90
        else "degraded"
        if health_score > 70
        else "unhealthy",
        "health_score": round(health_score, 1),
        "components": components,
        "metrics": {
            "uptime": "99.9%",
            "avg_response_time": round(
                sum(c["response_time"] for c in components) / len(components), 1
            ),
            "requests_per_minute": random.randint(1000, 5000),
            "error_rate": round(random.uniform(0.01, 0.5), 3),
            "active_connections": random.randint(100, 500),
        },
        "recent_incidents": [
            {
                "id": "inc-001",
                "title": "Database connection timeout",
                "status": "resolved",
                "duration": "5 minutes",
                "impact": "low",
            }
        ],
    }


@app.get("/api/analytics/predictive-billing")
async def get_predictive_billing(
    timeframe: str = Query("6m", description="Timeframe: 3m, 6m, 12m"),
    customer_id: str = Query("123", description="Customer ID"),
) -> dict[str, Any]:
    """Get predictive billing forecast with ML insights."""

    # Generate forecast data based on timeframe
    periods = {"3m": 12, "6m": 24, "12m": 48}[timeframe]

    forecast_data = []
    for i in range(periods):
        date = datetime.utcnow() - timedelta(days=30 * (periods - i))

        # Generate realistic cost progression with seasonality
        base_cost = 1000 + (i * 50)  # Growth trend
        seasonal_factor = 1 + 0.2 * math.sin(i * 0.5)  # Seasonal variation
        noise = random.uniform(-50, 50)  # Random variation

        cost = base_cost * seasonal_factor + noise

        forecast_data.append(
            {
                "date": date.strftime("%Y-%m-%d"),
                "actual_cost": cost if i < periods * 0.6 else None,
                "predicted_cost": cost if i >= periods * 0.6 else None,
                "confidence_upper": cost * 1.15 if i >= periods * 0.6 else None,
                "confidence_lower": cost * 0.85 if i >= periods * 0.6 else None,
            }
        )

    return {
        "timeframe": timeframe,
        "customer_id": customer_id,
        "forecast_data": forecast_data,
        "model_metrics": {
            "accuracy": random.uniform(90, 96),
            "mape": random.uniform(3, 8),
            "confidence": random.uniform(88, 95),
            "r_squared": random.uniform(0.85, 0.92),
        },
        "seasonal_patterns": [
            {"period": "Q1", "impact": 15, "description": "High usage period"},
            {"period": "Q2", "impact": 8, "description": "Moderate growth"},
            {"period": "Q3", "impact": -5, "description": "Summer slowdown"},
            {"period": "Q4", "impact": 22, "description": "Year-end surge"},
        ],
        "ai_insights": [
            {
                "priority": "high",
                "message": "API usage trending 25% above seasonal norms",
                "recommendation": "Consider volume discount tier for cost reduction",
            },
            {
                "priority": "medium",
                "message": "LLM token consumption correlates with business hours",
                "recommendation": "Implement caching during peak hours",
            },
        ],
    }


@app.get("/api/analytics/cost-forecasting")
async def get_cost_forecasting(
    model_type: str = Query(
        "seasonal", description="Model: linear, polynomial, seasonal, neural"
    ),
    horizon: int = Query(6, description="Forecast horizon in months"),
) -> dict[str, Any]:
    """Get advanced cost forecasting with multiple ML models."""

    # Model performance varies by type
    model_performance = {
        "linear": {"accuracy": 87.3, "mape": 12.7, "confidence": 78, "r2": 0.76},
        "polynomial": {"accuracy": 91.8, "mape": 8.2, "confidence": 85, "r2": 0.84},
        "seasonal": {"accuracy": 94.2, "mape": 5.8, "confidence": 92, "r2": 0.89},
        "neural": {"accuracy": 96.1, "mape": 3.9, "confidence": 95, "r2": 0.92},
    }

    performance = model_performance.get(model_type, model_performance["seasonal"])

    # Generate forecast scenarios
    base_cost = 1350.00
    scenarios = {
        "conservative": {
            "probability": 75,
            "next_month": base_cost * 0.85,
            "next_quarter": base_cost * 0.85 * 3,
            "annual": base_cost * 0.85 * 12,
            "description": "Based on current patterns with minimal growth",
        },
        "most_likely": {
            "probability": 85,
            "next_month": base_cost,
            "next_quarter": base_cost * 3.1,
            "annual": base_cost * 12.5,
            "description": "Expected scenario with seasonal trends",
        },
        "aggressive": {
            "probability": 45,
            "next_month": base_cost * 1.22,
            "next_quarter": base_cost * 1.22 * 3.2,
            "annual": base_cost * 1.22 * 13,
            "description": "High growth with increased adoption",
        },
    }

    return {
        "model_type": model_type,
        "horizon_months": horizon,
        "performance_metrics": performance,
        "forecast_scenarios": scenarios,
        "optimization_recommendations": [
            {
                "title": "API Response Caching",
                "description": "Cache frequent responses to reduce calls by 30%",
                "savings": 450.00,
                "effort": "Medium",
                "impact": "high",
            },
            {
                "title": "LLM Token Optimization",
                "description": "Use prompt engineering to reduce consumption",
                "savings": 320.00,
                "effort": "Low",
                "impact": "high",
            },
            {
                "title": "Storage Lifecycle Management",
                "description": "Archive older data automatically",
                "savings": 180.00,
                "effort": "High",
                "impact": "medium",
            },
        ],
    }


@app.get("/api/analytics/smart-alerts")
async def get_smart_alerts() -> dict[str, Any]:
    """Get intelligent alerts and anomaly detection results."""

    return {
        "active_alerts": [
            {
                "id": 1,
                "title": "Budget Threshold Exceeded",
                "message": "Monthly costs 15% above budget. Consider optimization.",
                "severity": "high",
                "timestamp": datetime.utcnow() - timedelta(hours=2),
                "category": "budget",
            },
            {
                "id": 2,
                "title": "Unusual API Usage Pattern",
                "message": "API calls increased 45% vs last week.",
                "severity": "medium",
                "timestamp": datetime.utcnow() - timedelta(hours=6),
                "category": "usage_anomaly",
            },
            {
                "id": 3,
                "title": "Optimization Opportunity",
                "message": "Caching could save $450/month based on patterns.",
                "severity": "low",
                "timestamp": datetime.utcnow() - timedelta(days=1),
                "category": "optimization",
            },
        ],
        "alert_configuration": [
            {
                "type": "budget_overrun",
                "enabled": True,
                "threshold": 90,
                "frequency": "immediate",
            },
            {
                "type": "usage_anomaly",
                "enabled": True,
                "threshold": 150,
                "frequency": "hourly",
            },
            {
                "type": "cost_spike",
                "enabled": False,
                "threshold": 200,
                "frequency": "immediate",
            },
        ],
        "anomaly_detection": {
            "model_accuracy": 94.5,
            "false_positive_rate": 2.1,
            "detection_latency": "< 5 minutes",
            "last_training": datetime.utcnow() - timedelta(days=7),
        },
    }


@app.get("/api/analytics/ai-insights")
async def get_ai_insights() -> dict[str, Any]:
    """Get comprehensive AI-powered insights and recommendations."""

    return {
        "insight_categories": {
            "cost_optimization": {
                "count": 5,
                "insights": [
                    {
                        "title": "API Response Caching",
                        "description": "Reduce redundant calls by 30%",
                        "impact": "high",
                        "confidence": 92,
                    },
                    {
                        "title": "Storage Compression",
                        "description": "Compress older data for savings",
                        "impact": "medium",
                        "confidence": 78,
                    },
                ],
            },
            "usage_trends": {
                "count": 3,
                "insights": [
                    {
                        "title": "Peak Hour Analysis",
                        "description": "Usage concentrated in business hours",
                        "impact": "medium",
                        "confidence": 89,
                    },
                    {
                        "title": "Seasonal Patterns",
                        "description": "Q4 shows 22% increase",
                        "impact": "high",
                        "confidence": 95,
                    },
                ],
            },
            "risk_factors": {
                "count": 2,
                "insights": [
                    {
                        "title": "Budget Overrun Risk",
                        "description": "Projected to exceed budget by 12%",
                        "impact": "high",
                        "confidence": 87,
                    },
                ],
            },
        },
        "comprehensive_analysis": {
            "key_findings": [
                "API usage correlates strongly with business hours (9 AM - 6 PM)",
                "LLM token consumption peaks on Tuesdays and Wednesdays",
                "Storage growth is linear at 12% monthly rate",
                "Workflow efficiency improved 23% over last quarter",
            ],
            "recommendations": [
                "Implement request batching during peak hours for 15% cost reduction",
                "Consider reserved capacity for predictable workloads",
                "Enable intelligent caching for frequently accessed data",
                "Optimize LLM prompts to reduce token usage by 20%",
            ],
            "confidence_score": 91.5,
            "last_analysis": datetime.utcnow() - timedelta(hours=1),
        },
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8002)
