"""Dashboard API for customer usage visibility and billing transparency."""

import logging
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Any
from uuid import UUID

from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from kachi.lib.db import get_session
from kachi.lib.models import Customer, MeterReading, RatedUsage

logger = logging.getLogger(__name__)

app = FastAPI(
    title="Kachi Dashboard API",
    description="Customer usage dashboard and billing transparency",
    version="1.0.0",
)

# CORS middleware for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],  # Vite dev server
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Pydantic models for API responses


class UsageSummary(BaseModel):
    """Customer usage summary."""

    customer_id: UUID
    customer_name: str
    period_start: datetime
    period_end: datetime
    total_amount: Decimal
    cogs: Decimal
    margin: Decimal
    meters: dict[str, Decimal]


class MeterUsage(BaseModel):
    """Usage for a specific meter."""

    meter_key: str
    current_value: Decimal
    included_allowance: Decimal
    consumed_percentage: float
    overage_amount: Decimal
    unit_price: Decimal


class UsageForecast(BaseModel):
    """End-of-period usage forecast."""

    customer_id: UUID
    forecast_date: datetime
    estimated_total: Decimal
    confidence_level: float
    meters_forecast: dict[str, Decimal]


class DrillDownItem(BaseModel):
    """Drill-down item for usage transparency."""

    meter_key: str
    reading_id: int
    window_start: datetime
    window_end: datetime
    value: Decimal
    source_event_ids: list[int]


class TimeSeriesPoint(BaseModel):
    """Time series data point."""

    timestamp: datetime
    value: Decimal
    meter_key: str


class UsageTrend(BaseModel):
    """Usage trend data for charts."""

    period: str  # 'daily', 'weekly', 'monthly'
    data_points: list[TimeSeriesPoint]
    total_usage: Decimal
    average_usage: Decimal
    peak_usage: Decimal
    growth_rate: float  # percentage change from previous period


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
    return {"status": "healthy", "service": "dashboard_api"}


@app.get("/api/customers", response_model=list[dict[str, Any]])
async def list_customers(
    session: AsyncSession = Depends(get_session),
) -> list[dict[str, Any]]:
    """List all customers."""
    result = await session.execute(select(Customer).where(Customer.active))  # type: ignore[arg-type]
    customers = result.scalars().all()

    return [
        {
            "id": str(customer.id),
            "name": customer.name,
            "lago_customer_id": customer.lago_customer_id,
            "currency": customer.currency,
            "created_at": customer.created_at.isoformat()
            if customer.created_at
            else None,
        }
        for customer in customers
    ]


@app.get("/api/customers/{customer_id}/usage", response_model=UsageSummary)
async def get_customer_usage(
    customer_id: UUID,
    period_start: datetime = Query(..., description="Period start date"),
    period_end: datetime = Query(..., description="Period end date"),
    session: AsyncSession = Depends(get_session),
) -> UsageSummary:
    """Get customer usage summary for a period."""
    # Get customer
    customer_result = await session.execute(
        select(Customer).where(Customer.id == customer_id)  # type: ignore[arg-type]
    )
    customer = customer_result.scalar_one_or_none()
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")

    # Get meter readings for the period
    readings_result = await session.execute(
        select(MeterReading)
        .where(MeterReading.customer_id == customer_id)  # type: ignore[arg-type]
        .where(MeterReading.window_start >= period_start)  # type: ignore[arg-type]
        .where(MeterReading.window_end <= period_end)  # type: ignore[arg-type]
    )
    readings = readings_result.scalars().all()

    # Aggregate by meter
    meters = {}
    for reading in readings:
        if reading.meter_key not in meters:
            meters[reading.meter_key] = Decimal("0")
        meters[reading.meter_key] += reading.value

    # Get rated usage if available
    rated_result = await session.execute(
        select(RatedUsage)
        .where(RatedUsage.customer_id == customer_id)  # type: ignore[arg-type]
        .where(RatedUsage.period_start == period_start.date())  # type: ignore[arg-type]
        .where(RatedUsage.period_end == period_end.date())  # type: ignore[arg-type]
    )
    rated_usage = rated_result.scalar_one_or_none()

    total_amount = rated_usage.subtotal if rated_usage else Decimal("0")
    cogs = rated_usage.cogs if rated_usage else Decimal("0")
    margin = rated_usage.margin if rated_usage else Decimal("0")

    return UsageSummary(
        customer_id=customer_id,
        customer_name=customer.name,
        period_start=period_start,
        period_end=period_end,
        total_amount=total_amount,
        cogs=cogs,
        margin=margin,
        meters=meters,
    )


@app.get("/api/customers/{customer_id}/meters", response_model=list[MeterUsage])
async def get_customer_meters(
    customer_id: UUID,
    period_start: datetime = Query(..., description="Period start date"),
    period_end: datetime = Query(..., description="Period end date"),
    session: AsyncSession = Depends(get_session),
) -> list[MeterUsage]:
    """Get detailed meter usage for a customer."""
    # Get meter readings
    readings_result = await session.execute(
        select(
            MeterReading.meter_key, func.sum(MeterReading.value).label("total_value")
        )  # type: ignore[call-overload]
        .where(MeterReading.customer_id == customer_id)  # type: ignore[arg-type]
        .where(MeterReading.window_start >= period_start)  # type: ignore[arg-type]
        .where(MeterReading.window_end <= period_end)  # type: ignore[arg-type]
        .group_by(MeterReading.meter_key)
    )
    readings = readings_result.all()

    # Mock plan data - in production this would come from customer's plan
    mock_plan: dict[str, Any] = {
        "included": {
            "workflow.completed": 1000,
            "llm.tokens": 5000000,
            "api.calls": 100000,
            "storage.gbh": 1000,
        },
        "overage_prices": {
            "workflow.completed": Decimal("0.10"),
            "llm.tokens": Decimal("0.00000025"),
            "api.calls": Decimal("0.0002"),
            "storage.gbh": Decimal("0.0006"),
        },
    }

    meters = []
    for meter_key, total_value in readings:
        included = Decimal(str(mock_plan["included"].get(meter_key, 0)))
        unit_price = mock_plan["overage_prices"].get(meter_key, Decimal("0"))

        consumed_pct = float(total_value / included * 100) if included > 0 else 0
        overage = max(Decimal("0"), total_value - included)
        overage_amount = overage * unit_price

        meters.append(
            MeterUsage(
                meter_key=meter_key,
                current_value=total_value,
                included_allowance=included,
                consumed_percentage=min(100.0, consumed_pct),
                overage_amount=overage_amount,
                unit_price=unit_price,
            )
        )

    return meters


@app.get("/api/customers/{customer_id}/forecast", response_model=UsageForecast)
async def get_usage_forecast(
    customer_id: UUID,
    session: AsyncSession = Depends(get_session),
) -> UsageForecast:
    """Get end-of-period usage forecast for a customer."""
    # Simple forecast based on last 7 days trend
    now = datetime.utcnow()
    week_ago = now - timedelta(days=7)

    # Get recent readings
    readings_result = await session.execute(
        select(
            MeterReading.meter_key, func.sum(MeterReading.value).label("weekly_value")
        )  # type: ignore[call-overload]
        .where(MeterReading.customer_id == customer_id)  # type: ignore[arg-type]
        .where(MeterReading.window_start >= week_ago)  # type: ignore[arg-type]
        .group_by(MeterReading.meter_key)
    )
    readings = readings_result.all()

    # Project to end of month (simple linear extrapolation)
    days_in_week = 7
    days_remaining_in_month = 30 - now.day  # Simplified

    meters_forecast = {}
    total_forecast = Decimal("0")

    for meter_key, weekly_value in readings:
        daily_rate = weekly_value / days_in_week
        month_forecast = weekly_value + (daily_rate * days_remaining_in_month)
        meters_forecast[meter_key] = month_forecast

        # Mock pricing for total
        unit_price = Decimal("0.10") if "workflow" in meter_key else Decimal("0.0001")
        total_forecast += month_forecast * unit_price

    return UsageForecast(
        customer_id=customer_id,
        forecast_date=now,
        estimated_total=total_forecast,
        confidence_level=0.75,  # Mock confidence
        meters_forecast=meters_forecast,
    )


@app.get("/api/customers/{customer_id}/drill-down", response_model=list[DrillDownItem])
async def get_usage_drill_down(
    customer_id: UUID,
    meter_key: str = Query(..., description="Meter key to drill down"),
    period_start: datetime = Query(..., description="Period start date"),
    period_end: datetime = Query(..., description="Period end date"),
    session: AsyncSession = Depends(get_session),
) -> list[DrillDownItem]:
    """Get drill-down details for a specific meter."""
    readings_result = await session.execute(
        select(MeterReading)
        .where(MeterReading.customer_id == customer_id)  # type: ignore[arg-type]
        .where(MeterReading.meter_key == meter_key)  # type: ignore[arg-type]
        .where(MeterReading.window_start >= period_start)  # type: ignore[arg-type]
        .where(MeterReading.window_end <= period_end)  # type: ignore[arg-type]
        .order_by(MeterReading.window_start.desc())  # type: ignore[attr-defined]
    )
    readings = readings_result.scalars().all()

    return [
        DrillDownItem(
            meter_key=reading.meter_key,
            reading_id=reading.id,
            window_start=reading.window_start,
            window_end=reading.window_end,
            value=reading.value,
            source_event_ids=reading.src_event_ids or [],
        )
        for reading in readings
    ]


@app.get("/api/metrics/dashboard", response_model=DashboardMetrics)
async def get_dashboard_metrics(
    session: AsyncSession = Depends(get_session),
) -> DashboardMetrics:
    """Get real-time dashboard metrics."""
    # Get total customers
    total_customers_result = await session.execute(
        select(func.count(Customer.id)).where(Customer.active)  # type: ignore[arg-type]
    )
    total_customers = total_customers_result.scalar() or 0

    # Get active customers (customers with usage in last 30 days)
    thirty_days_ago = datetime.utcnow() - timedelta(days=30)
    active_customers_result = await session.execute(
        select(func.count(func.distinct(MeterReading.customer_id))).where(
            MeterReading.window_start >= thirty_days_ago
        )  # type: ignore[arg-type]
    )
    active_customers = active_customers_result.scalar() or 0

    # Get monthly revenue (current month)
    current_month_start = datetime.utcnow().replace(
        day=1, hour=0, minute=0, second=0, microsecond=0
    )
    monthly_revenue_result = await session.execute(
        select(func.sum(RatedUsage.subtotal)).where(
            RatedUsage.period_start >= current_month_start.date()
        )  # type: ignore[arg-type]
    )
    monthly_revenue = monthly_revenue_result.scalar() or Decimal("0")

    # Get daily revenue (today)
    today = datetime.utcnow().date()
    daily_revenue_result = await session.execute(
        select(func.sum(RatedUsage.subtotal)).where(RatedUsage.period_start == today)  # type: ignore[arg-type]
    )
    daily_revenue = daily_revenue_result.scalar() or Decimal("0")

    # Get API calls today (sum of all meter readings for today)
    api_calls_result = await session.execute(
        select(func.sum(MeterReading.value))
        .where(MeterReading.meter_key == "api.calls")  # type: ignore[arg-type]
        .where(
            MeterReading.window_start
            >= datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        )  # type: ignore[arg-type]
    )
    api_calls_today = int(api_calls_result.scalar() or 0)

    # Get workflows today
    workflows_result = await session.execute(
        select(func.sum(MeterReading.value))
        .where(MeterReading.meter_key == "workflow.completed")  # type: ignore[arg-type]
        .where(
            MeterReading.window_start
            >= datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        )  # type: ignore[arg-type]
    )
    workflows_today = int(workflows_result.scalar() or 0)

    return DashboardMetrics(
        total_customers=total_customers,
        active_customers=active_customers,
        monthly_revenue=monthly_revenue,
        daily_revenue=daily_revenue,
        total_api_calls_today=api_calls_today,
        total_workflows_today=workflows_today,
        average_response_time=125.5,  # Mock data - would come from monitoring
        system_health_score=98.5,  # Mock data - would come from health checks
    )


@app.get("/api/usage/trends", response_model=UsageTrend)
async def get_usage_trends(
    period: str = Query("daily", description="Period: daily, weekly, monthly"),
    meter_key: str = Query(None, description="Specific meter key (optional)"),
    customer_id: UUID = Query(None, description="Specific customer (optional)"),
    session: AsyncSession = Depends(get_session),
) -> UsageTrend:
    """Get usage trends for charts."""
    # Determine time range based on period
    now = datetime.utcnow()
    if period == "daily":
        start_date = now - timedelta(days=30)  # Last 30 days
        date_trunc = "day"
    elif period == "weekly":
        start_date = now - timedelta(weeks=12)  # Last 12 weeks
        date_trunc = "week"
    elif period == "monthly":
        start_date = now - timedelta(days=365)  # Last 12 months
        date_trunc = "month"
    else:
        raise HTTPException(
            status_code=400, detail="Invalid period. Use: daily, weekly, monthly"
        )

    # Build query
    query = (
        select(
            func.date_trunc(date_trunc, MeterReading.window_start).label("period"),
            func.sum(MeterReading.value).label("total_value"),
        )
        .where(MeterReading.window_start >= start_date)  # type: ignore[arg-type]
        .group_by(func.date_trunc(date_trunc, MeterReading.window_start))
        .order_by(func.date_trunc(date_trunc, MeterReading.window_start))
    )

    if meter_key:
        query = query.where(MeterReading.meter_key == meter_key)  # type: ignore[arg-type]
    if customer_id:
        query = query.where(MeterReading.customer_id == customer_id)  # type: ignore[arg-type]

    result = await session.execute(query)
    rows = result.all()

    # Convert to time series points
    data_points = []
    total_usage = Decimal("0")
    values = []

    for row in rows:
        timestamp = row.period
        value = Decimal(str(row.total_value or 0))
        total_usage += value
        values.append(float(value))

        data_points.append(
            TimeSeriesPoint(
                timestamp=timestamp,
                value=value,
                meter_key=meter_key or "all",
            )
        )

    # Calculate statistics
    average_usage = total_usage / len(data_points) if data_points else Decimal("0")
    peak_usage = Decimal(str(max(values))) if values else Decimal("0")

    # Calculate growth rate (compare first and last periods)
    growth_rate = 0.0
    if len(values) >= 2 and values[0] > 0:
        growth_rate = ((values[-1] - values[0]) / values[0]) * 100

    return UsageTrend(
        period=period,
        data_points=data_points,
        total_usage=total_usage,
        average_usage=average_usage,
        peak_usage=peak_usage,
        growth_rate=growth_rate,
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8002)
