from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, DateTime, Text

from app.database import Base


class SafetyDecision(Base):
    __tablename__ = "safety_decisions"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    dialer_mode = Column(String(30), nullable=False, default="PREDICTIVE")
    engine_proposed_calls = Column(Integer, nullable=False, default=0)
    approved_calls = Column(Integer, nullable=False, default=0)
    available_agents = Column(Integer, nullable=False, default=0)
    reserved_agents = Column(Integer, nullable=False, default=0)
    active_calls = Column(Integer, nullable=False, default=0)
    calls_ringing = Column(Integer, nullable=False, default=0)
    provider_health = Column(String(30), nullable=False, default="HEALTHY")
    decision = Column(String(30), nullable=False)  # APPROVED, REDUCED, REJECTED, FALLBACK_PROGRESSIVE
    rule_triggered = Column(String(100), nullable=False)
    reason = Column(Text, nullable=False)
