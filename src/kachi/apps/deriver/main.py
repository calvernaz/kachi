"""Event processing pipeline for deriving meter readings from raw events."""

import argparse
import asyncio
from datetime import datetime, timedelta
from typing import Any
from uuid import UUID

import structlog
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from kachi.apps.deriver.processors import EdgeDeriver, WorkDeriver
from kachi.lib.db import get_session
from kachi.lib.models import MeterReading, RawEvent

logger = structlog.get_logger()


class EventProcessor:
    """Main event processing pipeline."""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.edge_deriver = EdgeDeriver(session)
        self.work_deriver = WorkDeriver(session)

    async def process_events_batch(
        self,
        customer_id: UUID | None = None,
        from_time: datetime | None = None,
        to_time: datetime | None = None,
        batch_size: int = 1000,
    ) -> dict[str, Any]:
        """Process a batch of raw events into meter readings."""
        # Build query for unprocessed events
        query = select(RawEvent).order_by(RawEvent.ts)

        if customer_id:
            query = query.where(RawEvent.customer_id == customer_id)

        if from_time:
            query = query.where(RawEvent.ts >= from_time)

        if to_time:
            query = query.where(RawEvent.ts <= to_time)

        query = query.limit(batch_size)

        result = await self.session.execute(query)
        events = result.scalars().all()

        if not events:
            return {"processed": 0, "edge_readings": 0, "work_readings": 0}

        edge_readings = 0
        work_readings = 0

        # Group events by customer and time window for efficient processing
        customer_windows = self._group_events_by_window(events)

        for (
            customer_id,
            window_start,
            window_end,
        ), window_events in customer_windows.items():
            # Process edge events (tokens, compute, etc.)
            edge_count = await self.edge_deriver.process_window(
                customer_id, window_start, window_end, window_events
            )
            edge_readings += edge_count

            # Process work events (workflows, outcomes, etc.)
            work_count = await self.work_deriver.process_window(
                customer_id, window_start, window_end, window_events
            )
            work_readings += work_count

        await self.session.commit()

        await logger.ainfo(
            "Processed event batch",
            events_processed=len(events),
            edge_readings=edge_readings,
            work_readings=work_readings,
            customers=len({e.customer_id for e in events}),
        )

        return {
            "processed": len(events),
            "edge_readings": edge_readings,
            "work_readings": work_readings,
        }

    def _group_events_by_window(
        self, events: list[RawEvent], window_minutes: int = 5
    ) -> dict[tuple[UUID, datetime, datetime], list[RawEvent]]:
        """Group events by customer and time window."""
        windows = {}

        for event in events:
            # Round down to window boundary
            window_start = event.ts.replace(
                minute=(event.ts.minute // window_minutes) * window_minutes,
                second=0,
                microsecond=0,
            )
            window_end = window_start + timedelta(minutes=window_minutes)

            key = (event.customer_id, window_start, window_end)
            if key not in windows:
                windows[key] = []
            windows[key].append(event)

        return windows

    async def process_continuous(self, interval_seconds: int = 30) -> None:
        """Run continuous event processing."""
        await logger.ainfo(
            "Starting continuous event processing", interval=interval_seconds
        )

        while True:
            try:
                # Process events from the last hour that might not have been processed
                cutoff_time = datetime.utcnow() - timedelta(hours=1)
                result = await self.process_events_batch(from_time=cutoff_time)

                if result["processed"] > 0:
                    await logger.ainfo("Continuous processing batch", **result)

                await asyncio.sleep(interval_seconds)

            except Exception as e:
                await logger.aerror(
                    "Error in continuous processing", error=str(e), exc_info=True
                )
                await asyncio.sleep(interval_seconds * 2)  # Back off on error

    async def reprocess_customer_period(
        self, customer_id: UUID, start_date: datetime, end_date: datetime
    ) -> dict[str, Any]:
        """Reprocess all events for a customer in a specific period."""
        await logger.ainfo(
            "Reprocessing customer period",
            customer_id=str(customer_id),
            start_date=start_date.isoformat(),
            end_date=end_date.isoformat(),
        )

        # Delete existing meter readings for this period
        await self._delete_existing_readings(customer_id, start_date, end_date)

        # Reprocess all events in the period
        total_processed = 0
        total_edge = 0
        total_work = 0

        current_time = start_date
        batch_hours = 6  # Process in 6-hour batches

        while current_time < end_date:
            batch_end = min(current_time + timedelta(hours=batch_hours), end_date)

            result = await self.process_events_batch(
                customer_id=customer_id, from_time=current_time, to_time=batch_end
            )

            total_processed += result["processed"]
            total_edge += result["edge_readings"]
            total_work += result["work_readings"]

            current_time = batch_end

        await self.session.commit()

        return {
            "customer_id": str(customer_id),
            "period": f"{start_date.isoformat()} to {end_date.isoformat()}",
            "total_processed": total_processed,
            "total_edge_readings": total_edge,
            "total_work_readings": total_work,
        }

    async def _delete_existing_readings(
        self, customer_id: UUID, start_date: datetime, end_date: datetime
    ) -> None:
        """Delete existing meter readings for reprocessing."""
        stmt = delete(MeterReading).where(
            MeterReading.customer_id == customer_id,
            MeterReading.window_start >= start_date,
            MeterReading.window_end <= end_date,
        )

        await self.session.execute(stmt)


async def main():
    """CLI entry point for event processing."""
    parser = argparse.ArgumentParser(
        description="Process raw events into meter readings"
    )
    parser.add_argument(
        "--continuous", action="store_true", help="Run continuous processing"
    )
    parser.add_argument("--customer-id", type=str, help="Process specific customer")
    parser.add_argument("--from-time", type=str, help="Start time (ISO format)")
    parser.add_argument("--to-time", type=str, help="End time (ISO format)")
    parser.add_argument("--batch-size", type=int, default=1000, help="Batch size")

    args = parser.parse_args()

    async with get_session() as session:
        processor = EventProcessor(session)

        if args.continuous:
            await processor.process_continuous()
        else:
            customer_id = UUID(args.customer_id) if args.customer_id else None
            from_time = (
                datetime.fromisoformat(args.from_time) if args.from_time else None
            )
            to_time = datetime.fromisoformat(args.to_time) if args.to_time else None

            result = await processor.process_events_batch(
                customer_id=customer_id,
                from_time=from_time,
                to_time=to_time,
                batch_size=args.batch_size,
            )

            print(f"Processed {result['processed']} events")
            print(f"Created {result['edge_readings']} edge readings")
            print(f"Created {result['work_readings']} work readings")


if __name__ == "__main__":
    asyncio.run(main())
