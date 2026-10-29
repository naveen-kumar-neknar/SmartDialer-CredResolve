from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.agent import Agent
from app.models.borrower import Borrower
from app.models.call import Call
from app.models.enums import (
    AgentStatus,
    BorrowerCallStatus,
    CallStatus,
)
from app.schemas import SeedResponse, DashboardStatsResponse
from app.services.telecom_provider import provider_manager
from app.services.event_processor import EventProcessor

router = APIRouter(prefix="/api", tags=["Demo & System"])

# Fictional agent seeds
FICTIONAL_AGENTS = [
    {"name": "Agent Sarah Jenkins", "status": AgentStatus.AVAILABLE},
    {"name": "Agent Michael Chang", "status": AgentStatus.AVAILABLE},
    {"name": "Agent Priya Sharma", "status": AgentStatus.AVAILABLE},
    {"name": "Agent David Rodriguez", "status": AgentStatus.AVAILABLE},
    {"name": "Agent Emily Watson", "status": AgentStatus.PAUSED},
    {"name": "Agent Marcus Vance", "status": AgentStatus.OFFLINE},
]

# 25 Fictional borrowers with strictly masked telephone numbers
FICTIONAL_BORROWERS = [
    {"name": "Avery Thompson", "phone_number": "+1 (555) ***-2184", "priority": 1},
    {"name": "Jordan Morales", "phone_number": "+1 (555) ***-9402", "priority": 1},
    {"name": "Taylor Reynolds", "phone_number": "+1 (555) ***-3819", "priority": 1},
    {"name": "Morgan Hayes", "phone_number": "+1 (555) ***-7731", "priority": 2},
    {"name": "Casey Bennett", "phone_number": "+1 (555) ***-4428", "priority": 2},
    {"name": "Riley Campbell", "phone_number": "+1 (555) ***-1156", "priority": 2},
    {"name": "Alex Montgomery", "phone_number": "+1 (555) ***-8890", "priority": 2},
    {"name": "Samira Patel", "phone_number": "+1 (555) ***-5563", "priority": 2},
    {"name": "Logan Mitchell", "phone_number": "+1 (555) ***-3342", "priority": 3},
    {"name": "Quinn Sullivan", "phone_number": "+1 (555) ***-6721", "priority": 3},
    {"name": "Dakota Foster", "phone_number": "+1 (555) ***-9984", "priority": 3},
    {"name": "Reese Chapman", "phone_number": "+1 (555) ***-2315", "priority": 3},
    {"name": "Skyler Brooks", "phone_number": "+1 (555) ***-4609", "priority": 3},
    {"name": "Kendall Bailey", "phone_number": "+1 (555) ***-8742", "priority": 3},
    {"name": "Harper Ross", "phone_number": "+1 (555) ***-1289", "priority": 4},
    {"name": "Cameron Powell", "phone_number": "+1 (555) ***-6634", "priority": 4},
    {"name": "Emerson Wood", "phone_number": "+1 (555) ***-9120", "priority": 4},
    {"name": "Finley Clark", "phone_number": "+1 (555) ***-3745", "priority": 4},
    {"name": "Rowan Lewis", "phone_number": "+1 (555) ***-5091", "priority": 4},
    {"name": "Hayden Hughes", "phone_number": "+1 (555) ***-8236", "priority": 5},
    {"name": "Peyton Price", "phone_number": "+1 (555) ***-2947", "priority": 5},
    {"name": "Sawyer Jenkins", "phone_number": "+1 (555) ***-7410", "priority": 5},
    {"name": "Eden Coleman", "phone_number": "+1 (555) ***-4853", "priority": 5},
    {"name": "Kai Rivera", "phone_number": "+1 (555) ***-1598", "priority": 5},
    {"name": "Elliott Barnes", "phone_number": "+1 (555) ***-9632", "priority": 5},
]


@router.post("/demo/seed", response_model=SeedResponse)
def seed_demo_data(db: Session = Depends(get_db)):
    """
    Populate database with sample agents and at least 25 fictional borrowers.
    Zero real PII is used. Existing records are preserved or supplemented.
    """
    existing_agents = {a.name for a in db.query(Agent).all()}
    agents_added = 0
    for agent_data in FICTIONAL_AGENTS:
        if agent_data["name"] not in existing_agents:
            agent = Agent(name=agent_data["name"], status=agent_data["status"].value)
            db.add(agent)
            agents_added += 1

    existing_borrowers = {b.name for b in db.query(Borrower).all()}
    borrowers_added = 0
    for b_data in FICTIONAL_BORROWERS:
        if b_data["name"] not in existing_borrowers:
            borrower = Borrower(
                name=b_data["name"],
                phone_number=b_data["phone_number"],
                priority=b_data["priority"],
                call_status=BorrowerCallStatus.UNPROCESSED.value,
            )
            db.add(borrower)
            borrowers_added += 1

    db.commit()

    total_agents = db.query(Agent).count()
    total_borrowers = db.query(Borrower).count()

    return SeedResponse(
        status="SEEDED",
        message=f"Seeded demo dataset: {agents_added} agents and {borrowers_added} borrowers added.",
        agents_count=total_agents,
        borrowers_count=total_borrowers,
    )


@router.get("/dashboard/stats", response_model=DashboardStatsResponse)
def get_dashboard_stats(db: Session = Depends(get_db)):
    """Computes comprehensive live system metrics."""
    total_agents = db.query(Agent).count()
    available_agents = db.query(Agent).filter(Agent.status == AgentStatus.AVAILABLE.value).count()
    reserved_agents = db.query(Agent).filter(Agent.status == AgentStatus.RESERVED.value).count()
    connected_agents = db.query(Agent).filter(Agent.status == AgentStatus.CONNECTED.value).count()
    dialing_agents = db.query(Agent).filter(Agent.status == AgentStatus.DIALING.value).count()

    active_calls = db.query(Call).filter(
        Call.status.in_([
            CallStatus.INITIATED.value,
            CallStatus.RINGING.value,
            CallStatus.ANSWERED.value,
            CallStatus.CONNECTED.value,
        ])
    ).count()

    completed_calls = db.query(Call).filter(Call.status == CallStatus.COMPLETED.value).count()
    failed_calls = db.query(Call).filter(
        Call.status.in_([CallStatus.FAILED.value, CallStatus.CANCELLED.value])
    ).count()

    # Agent utilization: (Agents in call / non-offline agents)
    active_agent_pool = total_agents - db.query(Agent).filter(Agent.status == AgentStatus.OFFLINE.value).count()
    utilization_rate = (
        round(((connected_agents + dialing_agents) / active_agent_pool) * 100, 1)
        if active_agent_pool > 0
        else 0.0
    )

    # Call connection rate
    total_resolved_calls = completed_calls + failed_calls
    connection_rate = (
        round((completed_calls / total_resolved_calls) * 100, 1)
        if total_resolved_calls > 0
        else 0.0
    )

    return DashboardStatsResponse(
        total_agents=total_agents,
        available_agents=available_agents,
        reserved_agents=reserved_agents,
        active_calls=active_calls,
        completed_calls=completed_calls,
        failed_calls=failed_calls,
        agent_utilization_rate=utilization_rate,
        call_connection_rate=connection_rate,
        provider_health=provider_manager.get_overall_health(),
        active_provider=provider_manager.active_provider_name,
    )


@router.post("/recovery/run")
def trigger_recovery(db: Session = Depends(get_db)):
    """Manual or cron trigger to reclaim stale agent and borrower reservations."""
    result = EventProcessor.recover_stale_reservations(db=db, timeout_seconds=30)
    return {
        "status": "RECOVERED",
        "result": result,
    }
