from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.borrower import Borrower
from app.models.enums import BorrowerCallStatus
from app.schemas import BorrowerCreate, BorrowerResponse

router = APIRouter(prefix="/api/borrowers", tags=["Borrowers"])


@router.get("", response_model=List[BorrowerResponse])
def list_borrowers(db: Session = Depends(get_db)):
    """List all borrowers ordered by priority and ID."""
    return db.query(Borrower).order_by(Borrower.priority.asc(), Borrower.id.asc()).all()


@router.post("", response_model=BorrowerResponse, status_code=status.HTTP_201_CREATED)
def create_borrower(borrower_in: BorrowerCreate, db: Session = Depends(get_db)):
    """Create a borrower with masked phone number to ensure zero real PII."""
    # Ensure phone number masking
    masked_phone = borrower_in.phone_number
    if "***" not in masked_phone and len(masked_phone) >= 10:
        masked_phone = masked_phone[:6] + "***-" + masked_phone[-4:]

    borrower = Borrower(
        name=borrower_in.name,
        phone_number=masked_phone,
        priority=borrower_in.priority,
        call_status=BorrowerCallStatus.UNPROCESSED.value,
    )
    db.add(borrower)
    db.commit()
    db.refresh(borrower)
    return borrower
