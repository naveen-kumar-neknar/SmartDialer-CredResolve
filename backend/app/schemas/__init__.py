from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, ConfigDict

from app.models.enums import (
    AgentStatus,
    BorrowerCallStatus,
    CallStatus,
    ProviderHealthStatus,
    SafetyDecisionType,
)


# --- Agent Schemas ---
class AgentCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100, description="Name of the agent")
    status: AgentStatus = Field(default=AgentStatus.AVAILABLE, description="Initial status")


class AgentStatusUpdate(BaseModel):
    status: AgentStatus = Field(..., description="Target status")


class AgentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    status: AgentStatus
    current_call_id: Optional[int] = None
    reserved_at: Optional[datetime] = None
    last_status_change: datetime
    created_at: datetime


# --- Borrower Schemas ---
class BorrowerCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    phone_number: str = Field(..., description="Masked phone number e.g. +1 (555) ***-1234")
    priority: int = Field(default=1, ge=1, le=5, description="1 is highest priority")


class BorrowerResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    phone_number: str
    priority: int
    call_status: BorrowerCallStatus
    attempt_count: int
    last_called_at: Optional[datetime] = None
    created_at: datetime


# --- Call Schemas ---
class CallInitiateRequest(BaseModel):
    borrower_id: int
    agent_id: Optional[int] = None
    provider: Optional[str] = "ProviderA"


class CallResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    borrower_id: int
    agent_id: Optional[int] = None
    provider: str
    provider_call_id: Optional[str] = None
    status: CallStatus
    failure_reason: Optional[str] = None
    duration_seconds: int
    initiated_at: Optional[datetime] = None
    ringing_at: Optional[datetime] = None
    answered_at: Optional[datetime] = None
    connected_at: Optional[datetime] = None
    ended_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime


class CallDetailResponse(CallResponse):
    borrower: Optional[BorrowerResponse] = None
    agent: Optional[AgentResponse] = None


class CallSimulateRequest(BaseModel):
    target_status: CallStatus = Field(..., description="Desired status: CONNECTED, COMPLETED, FAILED, etc.")
    failure_reason: Optional[str] = None


# --- Dialer Schemas ---
class ProgressiveDialRequest(BaseModel):
    batch_size: Optional[int] = Field(default=1, ge=1, le=10, description="Max calls to attempt in this progressive batch")


class ProgressiveDialResponse(BaseModel):
    status: str
    message: str
    calls_initiated: int
    calls: List[CallResponse]
    safety_decision: Optional[str] = None


class PredictiveSimulateRequest(BaseModel):
    historical_answer_rate: float = Field(default=0.35, ge=0.01, le=1.0, description="Historical answer rate (0.0 - 1.0)")
    average_call_duration: int = Field(default=120, ge=10, le=600, description="Average call duration in seconds")
    provider_override: Optional[str] = None


class PredictiveSimulateResponse(BaseModel):
    mode: str = "PREDICTIVE_SIMULATION"
    engine_proposed_calls: int
    approved_calls: int
    decision: SafetyDecisionType
    rule_triggered: str
    reason: str
    metrics: Dict[str, Any]
    formula_explanation: str


# --- Provider Schemas ---
class ProviderHealthResponse(BaseModel):
    active_provider: str
    provider_a_health: ProviderHealthStatus
    provider_b_health: ProviderHealthStatus
    overall_health: ProviderHealthStatus
    stats: Dict[str, Any]


class ProviderConfigRequest(BaseModel):
    active_provider: Optional[str] = None
    simulate_failure: Optional[bool] = None
    simulate_timeout: Optional[bool] = None
    simulate_duplicate: Optional[bool] = None
    simulate_out_of_order: Optional[bool] = None
    failure_rate: Optional[float] = Field(default=None, ge=0.0, le=1.0)


class ProviderEventWebhook(BaseModel):
    event_id: str
    call_id: int
    provider: str
    event_type: str
    sequence_number: int = 0
    payload: Optional[Dict[str, Any]] = None


# --- Safety Schemas ---
class SafetyDecisionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    timestamp: datetime
    dialer_mode: str
    engine_proposed_calls: int
    approved_calls: int
    available_agents: int
    reserved_agents: int
    active_calls: int
    calls_ringing: int
    provider_health: str
    decision: str
    rule_triggered: str
    reason: str


# --- Seed & Dashboard Schemas ---
class SeedResponse(BaseModel):
    status: str
    message: str
    agents_count: int
    borrowers_count: int


class DashboardStatsResponse(BaseModel):
    total_agents: int
    available_agents: int
    reserved_agents: int
    active_calls: int
    completed_calls: int
    failed_calls: int
    agent_utilization_rate: float
    call_connection_rate: float
    provider_health: ProviderHealthStatus
    active_provider: str


# --- Auth Schemas ---
class UserSignupRequest(BaseModel):
    name: str = Field(min_length=2, max_length=100)
    email: str = Field(min_length=5, max_length=150)
    password: str = Field(min_length=6, max_length=100)
    role: Optional[str] = "SUPERVISOR"


class UserLoginRequest(BaseModel):
    email: str
    password: str


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    email: str
    role: str
    created_at: datetime


class AuthResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse

