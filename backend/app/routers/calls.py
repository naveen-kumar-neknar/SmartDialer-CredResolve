import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.call import Call
from app.models.enums import CallStatus
from app.schemas import (
    CallResponse,
    CallDetailResponse,
    CallInitiateRequest,
    CallSimulateRequest,
)
from app.services.call_allocator import CallAllocator
from app.services.event_processor import EventProcessor
from app.services.telecom_provider import provider_manager

router = APIRouter(prefix="/api/calls", tags=["Calls"])


@router.get("", response_model=List[CallResponse])
def list_calls(
    status_filter: Optional[str] = None,
    limit: int = 100,
    db: Session = Depends(get_db),
):
    """List calls ordered by recency."""
    query = db.query(Call)
    if status_filter:
        query = query.filter(Call.status == status_filter)
    return query.order_by(Call.id.desc()).limit(limit).all()


@router.get("/{call_id}", response_model=CallDetailResponse)
def get_call_detail(call_id: int, db: Session = Depends(get_db)):
    """View detailed call record including associated borrower and agent."""
    call = db.query(Call).filter(Call.id == call_id).first()
    if not call:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Call {call_id} not found",
        )
    return call


@router.post("/initiate", response_model=CallResponse, status_code=status.HTTP_201_CREATED)
def initiate_call(call_in: CallInitiateRequest, db: Session = Depends(get_db)):
    """Initiate a single progressive call allocation safely."""
    batch_result = CallAllocator.execute_progressive_dialing_batch(db, max_batch_size=1)
    if batch_result["calls_initiated"] == 0 or not batch_result["calls"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=batch_result["message"],
        )
    return batch_result["calls"][0]


@router.post("/{call_id}/simulate", response_model=CallResponse)
def simulate_call_progression(
    call_id: int,
    req: CallSimulateRequest,
    db: Session = Depends(get_db),
):
    """
    Simulate a call progression to target status (e.g., CONNECTED, COMPLETED, FAILED).
    Uses the EventProcessor to enforce state machine validity and cascade updates.
    """
    call = db.query(Call).filter(Call.id == call_id).first()
    if not call:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Call {call_id} not found",
        )

    event_id = f"sim-{uuid.uuid4().hex[:12]}"
    provider = call.provider or provider_manager.get_active_provider().name

    result = EventProcessor.process_event(
        db=db,
        event_id=event_id,
        call_id=call_id,
        provider=provider,
        event_type=req.target_status.value,
        payload={"reason": req.failure_reason} if req.failure_reason else None,
    )

    if not result.get("success"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result.get("message", "Failed to update call state"),
        )

    db.refresh(call)
    return call
