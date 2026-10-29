from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.orm import relationship

from app.database import Base
from app.models.enums import BorrowerCallStatus

BORROWER_VALID_TRANSITIONS = {
    BorrowerCallStatus.UNPROCESSED: {
        BorrowerCallStatus.CALLING,
        BorrowerCallStatus.DO_NOT_CALL,
    },
    BorrowerCallStatus.CALLING: {
        BorrowerCallStatus.CONNECTED,
        BorrowerCallStatus.FAILED,
        BorrowerCallStatus.UNPROCESSED,  # on reservation release / rollback
    },
    BorrowerCallStatus.CONNECTED: {
        BorrowerCallStatus.COMPLETED,
        BorrowerCallStatus.FAILED,
    },
    BorrowerCallStatus.FAILED: {
        BorrowerCallStatus.UNPROCESSED,  # retry eligible
        BorrowerCallStatus.DO_NOT_CALL,
        BorrowerCallStatus.CALLING,
    },
    BorrowerCallStatus.COMPLETED: set(),  # terminal state
    BorrowerCallStatus.DO_NOT_CALL: set(),  # terminal state
}


class Borrower(Base):
    __tablename__ = "borrowers"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    name = Column(String(100), nullable=False)
    # Stored masked (e.g. +1 (555) ***-9281) to strictly protect PII
    phone_number = Column(String(50), nullable=False)
    priority = Column(Integer, default=1, index=True)  # 1 is highest priority
    call_status = Column(
        String(30),
        nullable=False,
        default=BorrowerCallStatus.UNPROCESSED.value,
        index=True,
    )
    attempt_count = Column(Integer, default=0, nullable=False)
    last_called_at = Column(DateTime, nullable=True)
    created_at = Column(
        DateTime, default=lambda: datetime.now(timezone.utc), nullable=False
    )

    calls = relationship("Call", back_populates="borrower")

    def can_transition_to(self, target_status: BorrowerCallStatus) -> bool:
        curr = BorrowerCallStatus(self.call_status)
        if curr == target_status:
            return True
        allowed = BORROWER_VALID_TRANSITIONS.get(curr, set())
        return target_status in allowed

    def transition_to(self, target_status: BorrowerCallStatus):
        if not self.can_transition_to(target_status):
            raise ValueError(
                f"Invalid borrower transition from {self.call_status} to {target_status}"
            )
        self.call_status = target_status.value
        if target_status == BorrowerCallStatus.CALLING:
            self.attempt_count += 1
            self.last_called_at = datetime.now(timezone.utc)
