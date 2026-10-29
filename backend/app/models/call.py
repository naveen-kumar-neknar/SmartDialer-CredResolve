from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship

from app.database import Base
from app.models.enums import CallStatus

CALL_VALID_TRANSITIONS = {
    CallStatus.QUEUED: {CallStatus.RESERVED, CallStatus.CANCELLED},
    CallStatus.RESERVED: {CallStatus.INITIATED, CallStatus.CANCELLED, CallStatus.FAILED},
    CallStatus.INITIATED: {CallStatus.RINGING, CallStatus.FAILED, CallStatus.CANCELLED},
    CallStatus.RINGING: {CallStatus.ANSWERED, CallStatus.FAILED, CallStatus.CANCELLED},
    CallStatus.ANSWERED: {CallStatus.CONNECTED, CallStatus.FAILED, CallStatus.CANCELLED},
    CallStatus.CONNECTED: {CallStatus.COMPLETED, CallStatus.FAILED},
    CallStatus.COMPLETED: set(),  # Terminal
    CallStatus.FAILED: set(),     # Terminal
    CallStatus.CANCELLED: set(),  # Terminal
}

TERMINAL_CALL_STATES = {CallStatus.COMPLETED, CallStatus.FAILED, CallStatus.CANCELLED}


class Call(Base):
    __tablename__ = "calls"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    borrower_id = Column(Integer, ForeignKey("borrowers.id"), nullable=False, index=True)
    agent_id = Column(Integer, ForeignKey("agents.id"), nullable=True, index=True)
    provider = Column(String(50), nullable=False, default="ProviderA")
    provider_call_id = Column(String(100), nullable=True, index=True)
    status = Column(String(30), nullable=False, default=CallStatus.QUEUED.value, index=True)
    failure_reason = Column(Text, nullable=True)
    duration_seconds = Column(Integer, default=0, nullable=False)

    initiated_at = Column(DateTime, nullable=True)
    ringing_at = Column(DateTime, nullable=True)
    answered_at = Column(DateTime, nullable=True)
    connected_at = Column(DateTime, nullable=True)
    ended_at = Column(DateTime, nullable=True)

    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    borrower = relationship("Borrower", back_populates="calls")
    agent = relationship("Agent", back_populates="calls", foreign_keys=[agent_id])

    @property
    def is_terminal(self) -> bool:
        return CallStatus(self.status) in TERMINAL_CALL_STATES

    def can_transition_to(self, new_status: CallStatus) -> bool:
        curr = CallStatus(self.status)
        if curr == new_status:
            return True
        # If currently in a terminal state, never allow moving to another state
        if curr in TERMINAL_CALL_STATES:
            return False
        allowed = CALL_VALID_TRANSITIONS.get(curr, set())
        return new_status in allowed

    def transition_to(self, new_status: CallStatus, failure_reason: str = None):
        if not self.can_transition_to(new_status):
            raise ValueError(
                f"Invalid call state transition: cannot transition from {self.status} to {new_status}"
            )

        now = datetime.now(timezone.utc)
        self.status = new_status.value
        self.updated_at = now

        if failure_reason:
            self.failure_reason = failure_reason

        if new_status == CallStatus.INITIATED and not self.initiated_at:
            self.initiated_at = now
        elif new_status == CallStatus.RINGING and not self.ringing_at:
            self.ringing_at = now
        elif new_status == CallStatus.ANSWERED and not self.answered_at:
            self.answered_at = now
        elif new_status == CallStatus.CONNECTED and not self.connected_at:
            self.connected_at = now
        elif new_status in TERMINAL_CALL_STATES:
            self.ended_at = now
            if self.connected_at:
                conn_time = self.connected_at if self.connected_at.tzinfo else self.connected_at.replace(tzinfo=timezone.utc)
                delta = (now - conn_time).total_seconds()
                self.duration_seconds = max(0, int(delta))
