from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text

from app.database import Base


class ProviderEvent(Base):
    __tablename__ = "provider_events"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    event_id = Column(String(100), unique=True, nullable=False, index=True)
    call_id = Column(Integer, ForeignKey("calls.id"), nullable=True, index=True)
    provider = Column(String(50), nullable=False)
    event_type = Column(String(50), nullable=False)
    sequence_number = Column(Integer, default=0, nullable=False)
    payload = Column(Text, nullable=True)
    status = Column(String(30), nullable=False, default="PROCESSED")
    received_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
