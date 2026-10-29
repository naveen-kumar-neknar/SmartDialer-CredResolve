from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.agent import Agent
from app.models.call import Call
from app.models.enums import AgentStatus, CallStatus
from app.schemas import (
    ProgressiveDialRequest,
    ProgressiveDialResponse,
    PredictiveSimulateRequest,
    PredictiveSimulateResponse,
)
from app.services.call_allocator import CallAllocator
from app.services.pacing_engine import PredictivePacingEngine
from app.services.safety_controller import SafetyController
from app.services.telecom_provider import provider_manager

router = APIRouter(prefix="/api/dialer", tags=["Dialer"])


@router.post("/progressive", response_model=ProgressiveDialResponse)
def run_progressive_dialing(
    req: ProgressiveDialRequest,
    db: Session = Depends(get_db),
):
    """
    Triggers a Progressive Dialing batch.
    - Safety Controller evaluates available agents and limits
    - Reserves agents and borrowers before call dispatch
    - Dispatches calls via active telecom provider
    """
    result = CallAllocator.execute_progressive_dialing_batch(
        db=db,
        max_batch_size=req.batch_size or 1,
    )
    return ProgressiveDialResponse(
        status=result["status"],
        message=result["message"],
        calls_initiated=result["calls_initiated"],
        calls=result["calls"],
        safety_decision=result.get("safety_decision"),
    )


@router.post("/predictive/simulate", response_model=PredictiveSimulateResponse)
def simulate_predictive_pacing(
    req: PredictiveSimulateRequest,
    db: Session = Depends(get_db),
):
    """
    Simulates the Predictive Pacing Engine recommendations.
    CRITICAL: This endpoint NEVER directly initiates calls.
    It calculates proposed calls based on queue dynamics, passes the proposal
    to the Safety Controller, records the decision, and returns the full explainable breakdown.
    """
    # 1. Fetch live telephony state
    available_agents = db.query(Agent).filter(Agent.status == AgentStatus.AVAILABLE.value).count()
    reserved_agents = db.query(Agent).filter(Agent.status == AgentStatus.RESERVED.value).count()
    active_calls = db.query(Call).filter(Call.status == CallStatus.CONNECTED.value).count()
    calls_ringing = (
        db.query(Call)
        .filter(Call.status.in_([CallStatus.INITIATED.value, CallStatus.RINGING.value]))
        .count()
    )

    provider = (
        provider_manager.get_provider_by_name(req.provider_override)
        if req.provider_override
        else provider_manager.get_active_provider()
    )
    provider_health = provider.get_health()

    # 2. Predictive Pacing Engine calculation
    pacing_result = PredictivePacingEngine.calculate_proposed_calls(
        available_agents=available_agents,
        reserved_agents=reserved_agents,
        active_calls=active_calls,
        calls_ringing=calls_ringing,
        historical_answer_rate=req.historical_answer_rate,
        average_call_duration=req.average_call_duration,
        provider_health=provider_health,
    )

    proposed_calls = pacing_result["proposed_calls"]

    # 3. Pass through Safety Controller
    approved_calls, safety_record = SafetyController.evaluate_and_enforce(
        db=db,
        dialer_mode="PREDICTIVE",
        proposed_calls=proposed_calls,
        available_agents=available_agents,
        reserved_agents=reserved_agents,
        active_calls=active_calls,
        calls_ringing=calls_ringing,
        provider_health=provider_health,
        historical_answer_rate=req.historical_answer_rate,
    )

    return PredictiveSimulateResponse(
        mode="PREDICTIVE_SIMULATION",
        engine_proposed_calls=proposed_calls,
        approved_calls=approved_calls,
        decision=safety_record.decision,
        rule_triggered=safety_record.rule_triggered,
        reason=safety_record.reason,
        metrics={
            "available_agents": available_agents,
            "reserved_agents": reserved_agents,
            "active_calls": active_calls,
            "calls_ringing": calls_ringing,
            "provider_name": provider.name,
            "provider_health": provider_health.value,
            "effective_idle_agents": pacing_result["effective_idle_agents"],
            "expected_inflight_answers": pacing_result["expected_inflight_answers"],
            "net_connections_needed": pacing_result["net_connections_needed"],
            "health_throttle_factor": pacing_result["health_throttle_factor"],
            "answer_rate_used": pacing_result["answer_rate_used"],
        },
        formula_explanation=pacing_result["explanation"],
    )
