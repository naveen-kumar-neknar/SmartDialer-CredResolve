from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.agent import Agent
from app.models.enums import AgentStatus
from app.schemas import AgentCreate, AgentResponse, AgentStatusUpdate

router = APIRouter(prefix="/api/agents", tags=["Agents"])


@router.get("", response_model=List[AgentResponse])
def list_agents(db: Session = Depends(get_db)):
    """List all agents ordered by ID."""
    return db.query(Agent).order_by(Agent.id.asc()).all()


@router.post("", response_model=AgentResponse, status_code=status.HTTP_201_CREATED)
def create_agent(agent_in: AgentCreate, db: Session = Depends(get_db)):
    """Create a new agent."""
    agent = Agent(
        name=agent_in.name,
        status=agent_in.status.value,
    )
    db.add(agent)
    db.commit()
    db.refresh(agent)
    return agent


@router.patch("/{agent_id}/status", response_model=AgentResponse)
def update_agent_status(
    agent_id: int,
    status_update: AgentStatusUpdate,
    db: Session = Depends(get_db),
):
    """
    Safely update agent status with state machine transition validation.
    Prevents invalid transitions (e.g. CONNECTED directly to OFFLINE).
    """
    agent = db.query(Agent).filter(Agent.id == agent_id).first()
    if not agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Agent with id {agent_id} not found",
        )

    target_status = status_update.status
    if not agent.can_transition_to(target_status):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid agent status transition from {agent.status} to {target_status.value}",
        )

    agent.transition_to(target_status)
    db.commit()
    db.refresh(agent)
    return agent
