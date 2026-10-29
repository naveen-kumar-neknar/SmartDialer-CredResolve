from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.orm import relationship

from app.database import Base
from app.models.enums import AgentStatus

# Allowed transitions matrix for agents
AGENT_VALID_TRANSITIONS = {
    AgentStatus.OFFLINE: {AgentStatus.AVAILABLE, AgentStatus.PAUSED},
    AgentStatus.AVAILABLE: {AgentStatus.RESERVED, AgentStatus.PAUSED, AgentStatus.OFFLINE},
    AgentStatus.RESERVED: {AgentStatus.DIALING, AgentStatus.AVAILABLE, AgentStatus.OFFLINE},
    AgentStatus.DIALING: {AgentStatus.CONNECTED, AgentStatus.WRAP_UP, AgentStatus.AVAILABLE, AgentStatus.OFFLINE},
    AgentStatus.CONNECTED: {AgentStatus.WRAP_UP, AgentStatus.AVAILABLE, AgentStatus.OFFLINE},
    AgentStatus.WRAP_UP: {AgentStatus.AVAILABLE, AgentStatus.PAUSED, AgentStatus.OFFLINE},
    AgentStatus.PAUSED: {AgentStatus.AVAILABLE, AgentStatus.OFFLINE},
}


class Agent(Base):
    __tablename__ = "agents"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    name = Column(String(100), nullable=False)
    status = Column(String(30), nullable=False, default=AgentStatus.AVAILABLE.value, index=True)
    current_call_id = Column(Integer, nullable=True)
    reserved_at = Column(DateTime, nullable=True)
    last_status_change = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    calls = relationship("Call", back_populates="agent", foreign_keys="Call.agent_id")

    def can_transition_to(self, new_status: AgentStatus) -> bool:
        """Validate if current agent status can transition to new_status."""
        curr = AgentStatus(self.status)
        if curr == new_status:
            return True
        allowed = AGENT_VALID_TRANSITIONS.get(curr, set())
        return new_status in allowed

    def transition_to(self, new_status: AgentStatus):
        """Perform transition with validation."""
        if not self.can_transition_to(new_status):
            raise ValueError(f"Invalid agent state transition from {self.status} to {new_status}")
        self.status = new_status.value
        self.last_status_change = datetime.now(timezone.utc)
        if new_status == AgentStatus.RESERVED:
            self.reserved_at = datetime.now(timezone.utc)
        elif new_status in {AgentStatus.AVAILABLE, AgentStatus.OFFLINE, AgentStatus.PAUSED}:
            self.reserved_at = None
            self.current_call_id = None
