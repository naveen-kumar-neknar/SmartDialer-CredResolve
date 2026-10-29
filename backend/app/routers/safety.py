from typing import List
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.safety_decision import SafetyDecision
from app.schemas import SafetyDecisionResponse

router = APIRouter(prefix="/api/safety", tags=["Safety"])


@router.get("/decisions", response_model=List[SafetyDecisionResponse])
def list_safety_decisions(
    limit: int = 50,
    db: Session = Depends(get_db),
):
    """Retrieve audit history of Safety Controller decisions."""
    return (
        db.query(SafetyDecision)
        .order_by(SafetyDecision.id.desc())
        .limit(limit)
        .all()
    )
