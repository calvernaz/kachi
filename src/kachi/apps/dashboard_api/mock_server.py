"""Mock Dashboard API server for testing without database."""

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


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8002)
