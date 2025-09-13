"""Tests for success fee billing system."""

from datetime import datetime, timedelta
from decimal import Decimal

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from kachi.lib.models import (
    Customer,
    WorkflowDefinition,
    WorkflowRun,
)
from kachi.lib.success_fees import (
    OutcomeVerificationManager,
    SuccessFeeBilling,
    SuccessFeeConfig,
)


@pytest.fixture
async def sample_data(db_session: AsyncSession):
    """Create sample data for success fee testing."""
    # Create customer
    customer = Customer(
        lago_customer_id="test-customer-002",
        name="Success Fee Customer",
        currency="USD",
    )
    db_session.add(customer)
    await db_session.commit()
    await db_session.refresh(customer)

    # Create workflow definition
    workflow_def = WorkflowDefinition(
        key="support-workflow",
        version=1,
        definition_schema={"steps": ["receive", "process", "resolve"]},
    )
    db_session.add(workflow_def)
    await db_session.commit()
    await db_session.refresh(workflow_def)

    # Create workflow runs
    now = datetime.utcnow()
    runs = []
    for i in range(5):
        run = WorkflowRun(
            customer_id=customer.id,
            definition_id=workflow_def.id,
            started_at=now - timedelta(hours=i),
            ended_at=now - timedelta(hours=i) + timedelta(minutes=45),
            status="completed",
            metadata_json={"ticket_id": f"TICKET-{i + 1}", "priority": "high"},
        )
        db_session.add(run)
        runs.append(run)

    await db_session.commit()
    for run in runs:
        await db_session.refresh(run)

    return {
        "customer": customer,
        "workflow_def": workflow_def,
        "runs": runs,
    }


class TestOutcomeVerificationManager:
    """Test outcome verification functionality."""

    async def test_create_outcome_verification(
        self, db_session: AsyncSession, sample_data
    ):
        """Test creating outcome verification records."""
        manager = OutcomeVerificationManager(db_session)
        run = sample_data["runs"][0]

        verification = await manager.create_outcome_verification(
            workflow_run_id=run.id,
            outcome_key="ticket_resolved",
            external_system="zendesk",
            external_ref="TICKET-1",
            settlement_days=7,
            outcome_metadata={"resolution_time": 45, "satisfaction_score": 5},
        )

        assert verification.workflow_run_id == run.id
        assert verification.outcome_key == "ticket_resolved"
        assert verification.external_system == "zendesk"
        assert verification.external_ref == "TICKET-1"
        assert verification.status == "pending"
        assert verification.settlement_days == 7
        assert verification.holdback_until is not None
        assert verification.outcome_metadata["satisfaction_score"] == 5

    async def test_verify_outcome(self, db_session: AsyncSession, sample_data):
        """Test verifying outcomes."""
        manager = OutcomeVerificationManager(db_session)
        run = sample_data["runs"][0]

        # Create verification
        verification = await manager.create_outcome_verification(
            workflow_run_id=run.id,
            outcome_key="ticket_resolved",
            settlement_days=0,  # No holdback for testing
        )

        # Verify the outcome
        verified_outcome = await manager.verify_outcome(
            verification_id=verification.id,
            verified=True,
        )

        assert verified_outcome.status == "verified"
        assert verified_outcome.verified_at is not None
        assert verified_outcome.reversal_reason is None

    async def test_reverse_outcome(self, db_session: AsyncSession, sample_data):
        """Test reversing outcomes."""
        manager = OutcomeVerificationManager(db_session)
        run = sample_data["runs"][0]

        # Create verification
        verification = await manager.create_outcome_verification(
            workflow_run_id=run.id,
            outcome_key="ticket_resolved",
        )

        # Reverse the outcome
        reversed_outcome = await manager.verify_outcome(
            verification_id=verification.id,
            verified=False,
            reversal_reason="Customer disputed resolution",
        )

        assert reversed_outcome.status == "reversed"
        assert reversed_outcome.verified_at is None
        assert reversed_outcome.reversal_reason == "Customer disputed resolution"

    async def test_get_settled_outcomes(self, db_session: AsyncSession, sample_data):
        """Test getting settled outcomes."""
        manager = OutcomeVerificationManager(db_session)
        customer = sample_data["customer"]
        runs = sample_data["runs"]

        # Create multiple verifications with different settlement periods
        past_time = datetime.utcnow() - timedelta(days=10)

        # This one should be settled (past holdback period)
        verification1 = await manager.create_outcome_verification(
            workflow_run_id=runs[0].id,
            outcome_key="ticket_resolved",
            settlement_days=0,
        )
        # Manually set holdback to past
        verification1.holdback_until = past_time
        db_session.add(verification1)

        # This one should not be settled (future holdback)
        verification2 = await manager.create_outcome_verification(
            workflow_run_id=runs[1].id,
            outcome_key="ticket_resolved",
            settlement_days=30,
        )

        await db_session.commit()

        # Verify both
        await manager.verify_outcome(verification1.id, verified=True)
        await manager.verify_outcome(verification2.id, verified=True)

        # Get settled outcomes
        period_start = datetime.utcnow() - timedelta(days=1)
        period_end = datetime.utcnow()

        settled_outcomes = await manager.get_settled_outcomes(
            customer_id=customer.id,
            outcome_key="ticket_resolved",
            period_start=period_start,
            period_end=period_end,
        )

        # Only verification1 should be settled
        assert len(settled_outcomes) == 1
        assert settled_outcomes[0].id == verification1.id


class TestSuccessFeeBilling:
    """Test success fee billing functionality."""

    async def test_calculate_success_fees(self, db_session: AsyncSession, sample_data):
        """Test calculating success fees."""
        billing = SuccessFeeBilling(db_session)
        customer = sample_data["customer"]
        runs = sample_data["runs"]

        # Create settled outcome verifications
        manager = OutcomeVerificationManager(db_session)
        past_time = datetime.utcnow() - timedelta(days=1)

        for i, run in enumerate(runs[:3]):  # Create 3 settled outcomes
            verification = await manager.create_outcome_verification(
                workflow_run_id=run.id,
                outcome_key="ticket_resolved",
                settlement_days=0,
                outcome_metadata={"satisfaction_score": 5},
            )
            # Set to past for settlement
            verification.holdback_until = past_time
            db_session.add(verification)
            await manager.verify_outcome(verification.id, verified=True)

        await db_session.commit()

        # Configure success fee
        success_fee_config = SuccessFeeConfig(
            meter_key="ticket_resolved",
            price_per_unit=Decimal("25.00"),
            settlement_days=0,
        )

        period_start = datetime.utcnow() - timedelta(days=1)
        period_end = datetime.utcnow()

        success_fees = await billing.calculate_success_fees(
            customer_id=customer.id,
            period_start=period_start,
            period_end=period_end,
            success_fee_configs=[success_fee_config],
        )

        assert len(success_fees) == 1
        fee_line = success_fees[0]
        assert fee_line["meter_key"] == "ticket_resolved"
        assert fee_line["line_type"] == "success_fee"
        assert fee_line["quantity"] == 3
        assert fee_line["unit_price"] == Decimal("25.00")
        assert fee_line["amount"] == Decimal("75.00")

    async def test_record_outcome_event(self, db_session: AsyncSession, sample_data):
        """Test recording outcome events."""
        billing = SuccessFeeBilling(db_session)
        run = sample_data["runs"][0]

        # Test auto-verification (no external verification required)
        verification = await billing.record_outcome_event(
            workflow_run_id=run.id,
            outcome_key="meeting_booked",
            outcome_metadata={"meeting_type": "demo", "attendees": 3},
        )

        assert verification.outcome_key == "meeting_booked"
        assert verification.status == "verified"  # Auto-verified
        assert verification.outcome_metadata["meeting_type"] == "demo"

    async def test_external_verification_required(
        self, db_session: AsyncSession, sample_data
    ):
        """Test outcome events requiring external verification."""
        billing = SuccessFeeBilling(db_session)
        run = sample_data["runs"][0]

        # Configure for external verification
        config = SuccessFeeConfig(
            meter_key="payment_received",
            price_per_unit=Decimal("50.00"),
            external_verification=True,
            external_system="stripe",
            settlement_days=7,
        )

        verification = await billing.record_outcome_event(
            workflow_run_id=run.id,
            outcome_key="payment_received",
            outcome_metadata={"amount": 100.00, "currency": "USD"},
            success_fee_config=config,
        )

        assert verification.outcome_key == "payment_received"
        assert verification.status == "pending"  # Not auto-verified
        assert verification.external_system == "stripe"
        assert verification.settlement_days == 7

    async def test_process_external_verification(
        self, db_session: AsyncSession, sample_data
    ):
        """Test processing external verification."""
        billing = SuccessFeeBilling(db_session)
        run = sample_data["runs"][0]

        # Create pending verification
        verification = await billing.record_outcome_event(
            workflow_run_id=run.id,
            outcome_key="payment_received",
            outcome_metadata={"invoice_id": "INV-123"},
            success_fee_config=SuccessFeeConfig(
                meter_key="payment_received",
                price_per_unit=Decimal("50.00"),
                external_verification=True,
                external_system="stripe",
            ),
        )

        external_ref = verification.external_ref

        # Process external verification (success)
        verified_outcome = await billing.process_external_verification(
            external_ref=external_ref,
            external_system="stripe",
            verified=True,
            verification_data={"payment_id": "pi_123", "amount": 100.00},
        )

        assert verified_outcome is not None
        assert verified_outcome.status == "verified"
        assert verified_outcome.outcome_metadata["payment_id"] == "pi_123"

    async def test_conditional_success_fees(
        self, db_session: AsyncSession, sample_data
    ):
        """Test success fees with conditions."""
        billing = SuccessFeeBilling(db_session)
        customer = sample_data["customer"]
        runs = sample_data["runs"]

        # Create outcomes with different satisfaction scores
        manager = OutcomeVerificationManager(db_session)
        past_time = datetime.utcnow() - timedelta(days=1)

        # High satisfaction (should qualify)
        verification1 = await manager.create_outcome_verification(
            workflow_run_id=runs[0].id,
            outcome_key="ticket_resolved",
            settlement_days=0,
            outcome_metadata={"satisfaction_score": 5},
        )
        verification1.holdback_until = past_time
        db_session.add(verification1)
        await manager.verify_outcome(verification1.id, verified=True)

        # Low satisfaction (should not qualify)
        verification2 = await manager.create_outcome_verification(
            workflow_run_id=runs[1].id,
            outcome_key="ticket_resolved",
            settlement_days=0,
            outcome_metadata={"satisfaction_score": 2},
        )
        verification2.holdback_until = past_time
        db_session.add(verification2)
        await manager.verify_outcome(verification2.id, verified=True)

        await db_session.commit()

        # Configure success fee with condition
        success_fee_config = SuccessFeeConfig(
            meter_key="ticket_resolved",
            price_per_unit=Decimal("25.00"),
            conditions={"satisfaction_score": 5},  # Only high satisfaction
            settlement_days=0,
        )

        period_start = datetime.utcnow() - timedelta(days=1)
        period_end = datetime.utcnow()

        success_fees = await billing.calculate_success_fees(
            customer_id=customer.id,
            period_start=period_start,
            period_end=period_end,
            success_fee_configs=[success_fee_config],
        )

        # Only 1 outcome should qualify (satisfaction_score = 5)
        assert len(success_fees) == 1
        fee_line = success_fees[0]
        assert fee_line["quantity"] == 1
        assert fee_line["amount"] == Decimal("25.00")
