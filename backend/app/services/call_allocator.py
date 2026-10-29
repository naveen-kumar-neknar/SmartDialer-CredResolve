import logging
import threading
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy import text

from app.models.agent import Agent
from app.models.borrower import Borrower
from app.models.call import Call
from app.models.enums import (
    AgentStatus,
    BorrowerCallStatus,
    CallStatus,
    ProviderHealthStatus,
)
from app.services.safety_controller import SafetyController
from app.services.telecom_provider import provider_manager
from app.services.event_processor import EventProcessor

logger = logging.getLogger(__name__)

# Reentrant lock to serialize atomic allocation steps in multithreaded/concurrent environments
_allocation_lock = threading.RLock()


class CallAllocator:
    """
    Call Allocator & Progressive Dialer Service:
    - Atomically pairs eligible borrowers with available agents
    - Strictly enforces 1:1 reservation before call dispatch
    - Conditional database updates ensure zero race conditions on concurrent requests
    - Clean rollback/release on telecom setup failures
    """

    @classmethod
    def execute_progressive_dialing_batch(
        cls,
        db: Session,
        max_batch_size: int = 1,
    ) -> Dict[str, Any]:
        """
        Executes a safe progressive dialing batch.
        Guarantees:
        1. Passes through SafetyController first.
        2. Reserves 1 available agent per call before dispatch.
        3. Never dials more calls than unreserved agents.
        4. Releases reservations if provider setup fails.
        """
        with _allocation_lock:
            # Query current agent & pipeline metrics
            available_agents = (
                db.query(Agent).filter(Agent.status == AgentStatus.AVAILABLE.value).count()
            )
            reserved_agents = (
                db.query(Agent).filter(Agent.status == AgentStatus.RESERVED.value).count()
            )
            active_calls = (
                db.query(Call)
                .filter(
                    Call.status.in_([
                        CallStatus.CONNECTED.value,
                    ])
                )
                .count()
            )
            calls_ringing = (
                db.query(Call)
                .filter(
                    Call.status.in_([
                        CallStatus.INITIATED.value,
                        CallStatus.RINGING.value,
                    ])
                )
                .count()
            )

            provider = provider_manager.get_active_provider()
            provider_health = provider.get_health()

            # Safety Controller check
            approved_calls, safety_decision = SafetyController.evaluate_and_enforce(
                db=db,
                dialer_mode="PROGRESSIVE",
                proposed_calls=max_batch_size,
                available_agents=available_agents,
                reserved_agents=reserved_agents,
                active_calls=active_calls,
                calls_ringing=calls_ringing,
                provider_health=provider_health,
            )

            if approved_calls == 0:
                return {
                    "status": "HALTED",
                    "message": f"Safety controller prevented dialing: {safety_decision.reason}",
                    "calls_initiated": 0,
                    "calls": [],
                    "safety_decision": safety_decision.decision,
                }

            initiated_calls: List[Call] = []

            for _ in range(approved_calls):
                call = cls._allocate_single_call(db, provider_name=provider.name)
                if call:
                    initiated_calls.append(call)
                else:
                    # No more matching agent or borrower available
                    break

            return {
                "status": "SUCCESS" if initiated_calls else "NO_ELIGIBLE_PAIRS",
                "message": (
                    f"Successfully initiated {len(initiated_calls)} progressive call(s)."
                    if initiated_calls
                    else "No available agents or unprocessed borrowers found."
                ),
                "calls_initiated": len(initiated_calls),
                "calls": initiated_calls,
                "safety_decision": safety_decision.decision,
            }

    @classmethod
    def _allocate_single_call(
        cls,
        db: Session,
        provider_name: str = "ProviderA",
    ) -> Optional[Call]:
        """
        Atomically selects and reserves an available agent and an unprocessed borrower,
        then dispatches the call through the active provider gateway.
        """
        now = datetime.now(timezone.utc)

        # 1. ATOMIC AGENT RESERVATION (Conditional update prevents double-allocation)
        # Find candidate available agent
        candidate_agent = (
            db.query(Agent)
            .filter(Agent.status == AgentStatus.AVAILABLE.value)
            .order_by(Agent.id.asc())
            .first()
        )
        if not candidate_agent:
            logger.info("[Allocation] No available agent found.")
            return None

        # Execute conditional update to reserve agent atomically
        agent_stmt = text(
            "UPDATE agents SET status = :target_status, reserved_at = :now "
            "WHERE id = :agent_id AND status = :expected_status"
        )
        result = db.execute(
            agent_stmt,
            {
                "target_status": AgentStatus.RESERVED.value,
                "now": now,
                "agent_id": candidate_agent.id,
                "expected_status": AgentStatus.AVAILABLE.value,
            },
        )
        if result.rowcount == 0:
            logger.warning(f"[Race Condition Prevented] Agent {candidate_agent.id} already reserved by another thread.")
            db.rollback()
            return None

        # 2. ATOMIC BORROWER RESERVATION (Conditional update prevents double-allocation)
        candidate_borrower = (
            db.query(Borrower)
            .filter(Borrower.call_status == BorrowerCallStatus.UNPROCESSED.value)
            .order_by(Borrower.priority.asc(), Borrower.id.asc())
            .first()
        )
        if not candidate_borrower:
            logger.info("[Allocation] No unprocessed borrower found. Rolling back agent reservation.")
            # Rollback reserved agent
            db.execute(
                text("UPDATE agents SET status = :status, reserved_at = NULL WHERE id = :agent_id"),
                {"status": AgentStatus.AVAILABLE.value, "agent_id": candidate_agent.id},
            )
            db.commit()
            return None

        borrower_stmt = text(
            "UPDATE borrowers SET call_status = :target_status, attempt_count = attempt_count + 1, "
            "last_called_at = :now WHERE id = :borrower_id AND call_status = :expected_status"
        )
        borrower_result = db.execute(
            borrower_stmt,
            {
                "target_status": BorrowerCallStatus.CALLING.value,
                "now": now,
                "borrower_id": candidate_borrower.id,
                "expected_status": BorrowerCallStatus.UNPROCESSED.value,
            },
        )
        if borrower_result.rowcount == 0:
            logger.warning(
                f"[Race Condition Prevented] Borrower {candidate_borrower.id} already allocated. Rolling back agent."
            )
            # Release agent
            db.execute(
                text("UPDATE agents SET status = :status, reserved_at = NULL WHERE id = :agent_id"),
                {"status": AgentStatus.AVAILABLE.value, "agent_id": candidate_agent.id},
            )
            db.commit()
            return None

        # 3. CREATE CALL RECORD (in RESERVED state)
        call = Call(
            borrower_id=candidate_borrower.id,
            agent_id=candidate_agent.id,
            provider=provider_name,
            status=CallStatus.RESERVED.value,
            initiated_at=now,
        )
        db.add(call)
        db.commit()
        db.refresh(call)

        # Link agent current_call_id
        candidate_agent.current_call_id = call.id
        db.commit()

        # 4. INITIATE TELECOM DISPATCH
        provider = provider_manager.get_provider_by_name(provider_name)
        dispatch_result = provider.initiate_call(call.id, candidate_borrower.phone_number)

        if not dispatch_result.success:
            logger.error(
                f"[Dispatch Failure] Call {call.id} failed to initiate with {provider_name}: {dispatch_result.error}. "
                f"Releasing agent {candidate_agent.id} and updating borrower {candidate_borrower.id}."
            )
            # Safe rollback of agent and borrower
            call.transition_to(CallStatus.FAILED, failure_reason=dispatch_result.error)

            # Release reserved agent back to AVAILABLE immediately
            candidate_agent.transition_to(AgentStatus.AVAILABLE)

            # Mark borrower as FAILED
            candidate_borrower.call_status = BorrowerCallStatus.FAILED.value
            db.commit()
            db.refresh(call)
            return call

        # Call successfully initiated with provider
        call.provider_call_id = dispatch_result.provider_call_id
        call.transition_to(CallStatus.INITIATED)
        candidate_agent.transition_to(AgentStatus.DIALING)
        db.commit()
        db.refresh(call)

        logger.info(
            f"[Call Dispatched] Call {call.id} initiated for Borrower {candidate_borrower.id} "
            f"with Agent {candidate_agent.id} via {provider_name}."
        )

        return call
