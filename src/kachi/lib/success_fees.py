"""Success fee billing and outcome verification system."""

import logging
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from kachi.lib.models import OutcomeVerification, WorkflowRun

logger = logging.getLogger(__name__)


class SuccessFeeConfig:
    """Configuration for success fee billing."""

    def __init__(
        self,
        meter_key: str,
        price_per_unit: Decimal,
        conditions: dict[str, Any] | None = None,
        settlement_days: int = 7,
        external_verification: bool = False,
        external_system: str | None = None,
    ):
        self.meter_key = meter_key
        self.price_per_unit = price_per_unit
        self.conditions = conditions or {}
        self.settlement_days = settlement_days
        self.external_verification = external_verification
        self.external_system = external_system


class OutcomeVerificationManager:
    """Manage outcome verification for success fee billing."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_outcome_verification(
        self,
        workflow_run_id: UUID,
        outcome_key: str,
        external_system: str | None = None,
        external_ref: str | None = None,
        settlement_days: int = 7,
        outcome_metadata: dict[str, Any] | None = None,
    ) -> OutcomeVerification:
        """Create a new outcome verification record."""
        holdback_until = datetime.utcnow() + timedelta(days=settlement_days)

        verification = OutcomeVerification(
            workflow_run_id=workflow_run_id,
            outcome_key=outcome_key,
            external_system=external_system or "internal",
            external_ref=external_ref or str(workflow_run_id),
            status="pending",
            holdback_until=holdback_until,
            settlement_days=settlement_days,
            outcome_metadata=outcome_metadata,
        )

        self.session.add(verification)
        await self.session.commit()
        await self.session.refresh(verification)

        logger.info(
            f"Created outcome verification {verification.id} for {outcome_key} "
            f"with {settlement_days} day holdback"
        )
        return verification

    async def verify_outcome(
        self,
        verification_id: int,
        verified: bool = True,
        reversal_reason: str | None = None,
    ) -> OutcomeVerification:
        """Mark an outcome as verified or reversed."""
        status = "verified" if verified else "reversed"
        verified_at = datetime.utcnow() if verified else None

        await self.session.execute(
            update(OutcomeVerification)
            .where(OutcomeVerification.id == verification_id)
            .values(
                status=status,
                verified_at=verified_at,
                reversal_reason=reversal_reason,
            )
        )
        await self.session.commit()

        # Fetch updated record
        result = await self.session.execute(
            select(OutcomeVerification).where(OutcomeVerification.id == verification_id)
        )
        verification = result.scalar_one()

        logger.info(
            f"Outcome verification {verification_id} marked as {status}"
            + (f": {reversal_reason}" if reversal_reason else "")
        )
        return verification

    async def get_settled_outcomes(
        self,
        customer_id: UUID,
        outcome_key: str,
        period_start: datetime,
        period_end: datetime,
        conditions: dict[str, Any] | None = None,
    ) -> list[OutcomeVerification]:
        """Get outcomes that have passed their settlement window and are verified."""
        now = datetime.utcnow()

        query = (
            select(OutcomeVerification)
            .join(WorkflowRun, OutcomeVerification.workflow_run_id == WorkflowRun.id)
            .where(
                WorkflowRun.customer_id == customer_id,
                OutcomeVerification.outcome_key == outcome_key,
                OutcomeVerification.status == "verified",
                OutcomeVerification.holdback_until <= now,
                WorkflowRun.started_at >= period_start,
                WorkflowRun.started_at <= period_end,
            )
        )

        result = await self.session.execute(query)
        verifications = result.scalars().all()

        # Apply conditions if specified
        if conditions:
            filtered_verifications = []
            for verification in verifications:
                if self._matches_conditions(verification, conditions):
                    filtered_verifications.append(verification)
            return filtered_verifications

        return verifications

    async def get_pending_outcomes(
        self, external_system: str | None = None
    ) -> list[OutcomeVerification]:
        """Get outcomes pending verification."""
        query = select(OutcomeVerification).where(
            OutcomeVerification.status == "pending"
        )

        if external_system:
            query = query.where(OutcomeVerification.external_system == external_system)

        result = await self.session.execute(query)
        return result.scalars().all()

    def _matches_conditions(
        self, verification: OutcomeVerification, conditions: dict[str, Any]
    ) -> bool:
        """Check if outcome verification matches the specified conditions."""
        if not verification.outcome_metadata:
            return False

        for key, expected_value in conditions.items():
            actual_value = verification.outcome_metadata.get(key)
            if actual_value != expected_value:
                return False

        return True


class SuccessFeeBilling:
    """Handle success fee billing calculations."""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.verification_manager = OutcomeVerificationManager(session)

    async def calculate_success_fees(
        self,
        customer_id: UUID,
        period_start: datetime,
        period_end: datetime,
        success_fee_configs: list[SuccessFeeConfig],
    ) -> list[dict[str, Any]]:
        """Calculate success fees for a billing period."""
        success_fee_lines = []

        for config in success_fee_configs:
            settled_outcomes = await self.verification_manager.get_settled_outcomes(
                customer_id=customer_id,
                outcome_key=config.meter_key,
                period_start=period_start,
                period_end=period_end,
                conditions=config.conditions,
            )

            if settled_outcomes:
                quantity = len(settled_outcomes)
                amount = Decimal(quantity) * config.price_per_unit

                success_fee_lines.append(
                    {
                        "meter_key": config.meter_key,
                        "line_type": "success_fee",
                        "quantity": quantity,
                        "unit_price": config.price_per_unit,
                        "amount": amount,
                        "description": f"Success fee for {config.meter_key}",
                        "settlement_days": config.settlement_days,
                        "conditions": config.conditions,
                        "outcome_ids": [v.id for v in settled_outcomes],
                    }
                )

                logger.info(
                    f"Calculated success fee: {quantity} x {config.price_per_unit} = {amount} "
                    f"for {config.meter_key}"
                )

        return success_fee_lines

    async def record_outcome_event(
        self,
        workflow_run_id: UUID,
        outcome_key: str,
        outcome_metadata: dict[str, Any] | None = None,
        success_fee_config: SuccessFeeConfig | None = None,
    ) -> OutcomeVerification:
        """Record an outcome event for potential success fee billing."""
        external_system = None
        settlement_days = 0

        if success_fee_config:
            external_system = success_fee_config.external_system
            settlement_days = success_fee_config.settlement_days

        verification = await self.verification_manager.create_outcome_verification(
            workflow_run_id=workflow_run_id,
            outcome_key=outcome_key,
            external_system=external_system,
            settlement_days=settlement_days,
            outcome_metadata=outcome_metadata,
        )

        # If no external verification required, auto-verify
        if not success_fee_config or not success_fee_config.external_verification:
            await self.verification_manager.verify_outcome(
                verification.id, verified=True
            )

        return verification

    async def process_external_verification(
        self,
        external_ref: str,
        external_system: str,
        verified: bool,
        verification_data: dict[str, Any] | None = None,
    ) -> OutcomeVerification | None:
        """Process verification from external system."""
        # Find the outcome verification
        result = await self.session.execute(
            select(OutcomeVerification).where(
                OutcomeVerification.external_ref == external_ref,
                OutcomeVerification.external_system == external_system,
                OutcomeVerification.status == "pending",
            )
        )
        verification = result.scalar_one_or_none()

        if not verification:
            logger.warning(
                f"No pending verification found for {external_ref} in {external_system}"
            )
            return None

        # Update metadata if provided
        if verification_data and verification.outcome_metadata:
            verification.outcome_metadata.update(verification_data)

        # Mark as verified or reversed
        reversal_reason = None
        if not verified and verification_data:
            reversal_reason = verification_data.get(
                "reason", "External verification failed"
            )

        return await self.verification_manager.verify_outcome(
            verification.id, verified=verified, reversal_reason=reversal_reason
        )
