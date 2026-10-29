from datetime import datetime, timezone, timedelta
import json
import logging
from typing import Dict, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.models.call import Call, TERMINAL_CALL_STATES
from app.models.agent import Agent
from app.models.borrower import Borrower
from app.models.provider_event import ProviderEvent
from app.models.enums import (
    CallStatus,
    AgentStatus,
    BorrowerCallStatus,
)

logger = logging.getLogger(__name__)

# Map provider event_type strings to CallStatus enum
EVENT_TYPE_TO_CALL_STATUS = {
    "INITIATED": CallStatus.INITIATED,
    "RINGING": CallStatus.RINGING,
    "ANSWERED": CallStatus.ANSWERED,
    "CONNECTED": CallStatus.CONNECTED,
    "COMPLETED": CallStatus.COMPLETED,
    "CALL_ENDED": CallStatus.COMPLETED,
    "FAILED": CallStatus.FAILED,
    "CANCELLED": CallStatus.CANCELLED,
}

# Define logical ordering of call statuses for out-of-order detection
CALL_STATUS_ORDER = {
    CallStatus.QUEUED: 0,
    CallStatus.RESERVED: 1,
    CallStatus.INITIATED: 2,
    CallStatus.RINGING: 3,
    CallStatus.ANSWERED: 4,
    CallStatus.CONNECTED: 5,
    CallStatus.COMPLETED: 6,
    CallStatus.FAILED: 6,
    CallStatus.CANCELLED: 6,
}


class EventProcessor:
    """
    Idempotent, fault-tolerant event processing engine with:
    - Unique provider event ID deduplication
    - Strict state machine validation
    - Stale & out-of-order event rejection
    - Preservation of terminal states (completed/failed calls cannot be reopened)
    - Cascade synchronization to Agent and Borrower states
    """

    @staticmethod
    def process_event(
        db: Session,
        event_id: str,
        call_id: int,
        provider: str,
        event_type: str,
        sequence_number: int = 0,
        payload: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        payload_str = json.dumps(payload or {})

        # 1. IDEMPOTENCY CHECK: Unique provider event ID
        existing_event = (
            db.query(ProviderEvent).filter(ProviderEvent.event_id == event_id).first()
        )
        if existing_event:
            logger.warning(
                f"[Idempotency] Duplicate event detected: {event_id} for call {call_id}. Ignored."
            )
            return {
                "success": True,
                "status": "IGNORED_DUPLICATE",
                "message": f"Event {event_id} already processed",
                "call_id": call_id,
            }

        # 2. CALL EXISTENCE CHECK
        call = db.query(Call).filter(Call.id == call_id).first()
        if not call:
            # Record orphan event log
            event_log = ProviderEvent(
                event_id=event_id,
                call_id=call_id,
                provider=provider,
                event_type=event_type,
                sequence_number=sequence_number,
                payload=payload_str,
                status="CALL_NOT_FOUND",
            )
            db.add(event_log)
            db.commit()
            return {
                "success": False,
                "status": "CALL_NOT_FOUND",
                "message": f"Call {call_id} does not exist",
            }

        # Determine target call status
        target_status = EVENT_TYPE_TO_CALL_STATUS.get(event_type.upper())
        if not target_status:
            event_log = ProviderEvent(
                event_id=event_id,
                call_id=call_id,
                provider=provider,
                event_type=event_type,
                sequence_number=sequence_number,
                payload=payload_str,
                status="UNKNOWN_EVENT_TYPE",
            )
            db.add(event_log)
            db.commit()
            return {
                "success": False,
                "status": "UNKNOWN_EVENT_TYPE",
                "message": f"Unknown event type: {event_type}",
            }

        current_call_status = CallStatus(call.status)

        # 3. TERMINAL STATE PROTECTION:
        # Never automatically move a completed/failed call back to an active state!
        if current_call_status in TERMINAL_CALL_STATES:
            event_log = ProviderEvent(
                event_id=event_id,
                call_id=call_id,
                provider=provider,
                event_type=event_type,
                sequence_number=sequence_number,
                payload=payload_str,
                status="IGNORED_CALL_TERMINAL",
            )
            db.add(event_log)
            db.commit()
            logger.info(
                f"[Terminal State Protection] Call {call_id} already terminal ({call.status}). "
                f"Ignoring late event {event_type} ({event_id})."
            )
            return {
                "success": True,
                "status": "IGNORED_CALL_TERMINAL",
                "message": f"Call is already in terminal state {call.status}",
                "call_id": call_id,
            }

        # 4. OUT-OF-ORDER EVENT PROTECTION:
        # Check if incoming event status logically precedes current status
        current_rank = CALL_STATUS_ORDER.get(current_call_status, 0)
        target_rank = CALL_STATUS_ORDER.get(target_status, 0)

        if target_rank < current_rank:
            event_log = ProviderEvent(
                event_id=event_id,
                call_id=call_id,
                provider=provider,
                event_type=event_type,
                sequence_number=sequence_number,
                payload=payload_str,
                status="IGNORED_OUT_OF_ORDER",
            )
            db.add(event_log)
            db.commit()
            logger.warning(
                f"[Out-of-Order Protection] Call {call_id} status is {call.status} (rank {current_rank}). "
                f"Received out-of-order event {event_type} (rank {target_rank}). Ignored."
            )
            return {
                "success": True,
                "status": "IGNORED_OUT_OF_ORDER",
                "message": f"Out-of-order event rejected: cannot go backwards from {call.status} to {target_status}",
                "call_id": call_id,
            }

        # 5. STATE MACHINE TRANSITION VALIDATION
        if not call.can_transition_to(target_status):
            # Check if this is an idempotent re-send of the same status
            if current_call_status == target_status:
                event_log = ProviderEvent(
                    event_id=event_id,
                    call_id=call_id,
                    provider=provider,
                    event_type=event_type,
                    sequence_number=sequence_number,
                    payload=payload_str,
                    status="IGNORED_SAME_STATE",
                )
                db.add(event_log)
                db.commit()
                return {
                    "success": True,
                    "status": "IGNORED_SAME_STATE",
                    "message": f"Call is already in state {target_status}",
                    "call_id": call_id,
                }

            event_log = ProviderEvent(
                event_id=event_id,
                call_id=call_id,
                provider=provider,
                event_type=event_type,
                sequence_number=sequence_number,
                payload=payload_str,
                status="INVALID_TRANSITION",
            )
            db.add(event_log)
            db.commit()
            return {
                "success": False,
                "status": "INVALID_TRANSITION",
                "message": f"Invalid state transition from {call.status} to {target_status}",
                "call_id": call_id,
            }

        # 6. APPLY CALL TRANSITION & CASCADE TO AGENT AND BORROWER
        fail_reason = payload.get("reason") if payload else None
        call.transition_to(target_status, failure_reason=fail_reason)

        agent = db.query(Agent).filter(Agent.id == call.agent_id).first() if call.agent_id else None
        borrower = db.query(Borrower).filter(Borrower.id == call.borrower_id).first()

        if target_status == CallStatus.INITIATED:
            if agent and agent.can_transition_to(AgentStatus.DIALING):
                agent.transition_to(AgentStatus.DIALING)
            if borrower and borrower.can_transition_to(BorrowerCallStatus.CALLING):
                borrower.transition_to(BorrowerCallStatus.CALLING)

        elif target_status == CallStatus.RINGING:
            if agent and agent.status == AgentStatus.RESERVED.value and agent.can_transition_to(AgentStatus.DIALING):
                agent.transition_to(AgentStatus.DIALING)

        elif target_status == CallStatus.CONNECTED:
            if agent and agent.can_transition_to(AgentStatus.CONNECTED):
                agent.transition_to(AgentStatus.CONNECTED)
                agent.current_call_id = call.id
            if borrower and borrower.can_transition_to(BorrowerCallStatus.CONNECTED):
                borrower.transition_to(BorrowerCallStatus.CONNECTED)

        elif target_status == CallStatus.COMPLETED:
            if agent:
                if agent.can_transition_to(AgentStatus.WRAP_UP):
                    agent.transition_to(AgentStatus.WRAP_UP)
                elif agent.can_transition_to(AgentStatus.AVAILABLE):
                    agent.transition_to(AgentStatus.AVAILABLE)
            if borrower and borrower.can_transition_to(BorrowerCallStatus.COMPLETED):
                borrower.transition_to(BorrowerCallStatus.COMPLETED)

        elif target_status in {CallStatus.FAILED, CallStatus.CANCELLED}:
            # Call failed/cancelled: release agent immediately back to AVAILABLE
            if agent:
                if agent.can_transition_to(AgentStatus.AVAILABLE):
                    agent.transition_to(AgentStatus.AVAILABLE)
            if borrower:
                if borrower.can_transition_to(BorrowerCallStatus.FAILED):
                    borrower.transition_to(BorrowerCallStatus.FAILED)

        # 7. LOG PROCESSED EVENT IN AUDIT TABLE
        event_log = ProviderEvent(
            event_id=event_id,
            call_id=call_id,
            provider=provider,
            event_type=event_type,
            sequence_number=sequence_number,
            payload=payload_str,
            status="PROCESSED",
        )
        db.add(event_log)
        db.commit()

        return {
            "success": True,
            "status": "PROCESSED",
            "call_id": call.id,
            "new_call_status": call.status,
            "agent_status": agent.status if agent else None,
            "borrower_status": borrower.call_status if borrower else None,
        }

    @staticmethod
    def recover_stale_reservations(db: Session, timeout_seconds: int = 45) -> Dict[str, int]:
        """
        Failure Recovery:
        A worker crash or network drop must not permanently lock an agent or borrower.
        Recovers agents & borrowers reserved for > timeout_seconds with no active call.
        """
        threshold = datetime.now(timezone.utc) - timedelta(seconds=timeout_seconds)
        recovered_agents = 0
        recovered_borrowers = 0

        # 1. Recover stale reserved agents
        stale_agents = (
            db.query(Agent)
            .filter(
                Agent.status == AgentStatus.RESERVED.value,
                Agent.reserved_at != None,
                Agent.reserved_at < threshold,
            )
            .all()
        )

        for agent in stale_agents:
            # Verify if there is an active ongoing call
            active_call = (
                db.query(Call)
                .filter(
                    Call.agent_id == agent.id,
                    Call.status.in_([
                        CallStatus.RESERVED.value,
                        CallStatus.INITIATED.value,
                        CallStatus.RINGING.value,
                        CallStatus.ANSWERED.value,
                        CallStatus.CONNECTED.value,
                    ]),
                )
                .first()
            )
            if not active_call:
                logger.info(f"[Recovery] Agent {agent.id} ({agent.name}) timed out in RESERVED. Releasing to AVAILABLE.")
                agent.transition_to(AgentStatus.AVAILABLE)
                recovered_agents += 1

        # 2. Recover stale borrowers stuck in CALLING without active call
        stale_borrowers = (
            db.query(Borrower)
            .filter(
                Borrower.call_status == BorrowerCallStatus.CALLING.value,
                Borrower.last_called_at != None,
                Borrower.last_called_at < threshold,
            )
            .all()
        )

        for borrower in stale_borrowers:
            active_call = (
                db.query(Call)
                .filter(
                    Call.borrower_id == borrower.id,
                    Call.status.in_([
                        CallStatus.RESERVED.value,
                        CallStatus.INITIATED.value,
                        CallStatus.RINGING.value,
                        CallStatus.ANSWERED.value,
                        CallStatus.CONNECTED.value,
                    ]),
                )
                .first()
            )
            if not active_call:
                logger.info(f"[Recovery] Borrower {borrower.id} ({borrower.name}) timed out in CALLING. Resetting to UNPROCESSED.")
                borrower.call_status = BorrowerCallStatus.UNPROCESSED.value
                recovered_borrowers += 1

        if recovered_agents or recovered_borrowers:
            db.commit()

        return {
            "recovered_agents": recovered_agents,
            "recovered_borrowers": recovered_borrowers,
        }
