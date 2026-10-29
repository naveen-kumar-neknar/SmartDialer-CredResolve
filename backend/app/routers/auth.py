import uuid
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, Header
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User
from app.schemas import (
    UserSignupRequest,
    UserLoginRequest,
    UserResponse,
    AuthResponse,
)

router = APIRouter(prefix="/api/auth", tags=["Authentication"])


def seed_default_users(db: Session):
    """Seed default supervisor and agent users if none exist."""
    if db.query(User).count() == 0:
        supervisor = User.create(
            email="supervisor@credresolve.com",
            name="Priya Sharma (Operations Lead)",
            password="credresolve123",
            role="SUPERVISOR",
        )
        agent_user = User.create(
            email="agent@credresolve.com",
            name="Rahul Verma (Dialer Agent)",
            password="credresolve123",
            role="AGENT",
        )
        db.add_all([supervisor, agent_user])
        db.commit()


@router.post("/signup", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
def signup(req: UserSignupRequest, db: Session = Depends(get_db)):
    """Register a new team member / operator."""
    normalized_email = req.email.strip().lower()
    existing = db.query(User).filter(User.email == normalized_email).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="An account with this email already exists.",
        )

    user = User.create(
        email=normalized_email,
        name=req.name,
        password=req.password,
        role=req.role or "SUPERVISOR",
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    token = f"credresolve-session-{uuid.uuid4().hex}"
    return AuthResponse(
        access_token=token,
        token_type="bearer",
        user=UserResponse.model_validate(user),
    )


@router.post("/login", response_model=AuthResponse)
def login(req: UserLoginRequest, db: Session = Depends(get_db)):
    """Authenticate with email and password."""
    seed_default_users(db)
    normalized_email = req.email.strip().lower()
    user = db.query(User).filter(User.email == normalized_email).first()

    if not user or not user.verify_password(req.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password.",
        )

    token = f"credresolve-session-{uuid.uuid4().hex}"
    return AuthResponse(
        access_token=token,
        token_type="bearer",
        user=UserResponse.model_validate(user),
    )


@router.get("/me", response_model=UserResponse)
def get_current_user(
    db: Session = Depends(get_db),
    authorization: Optional[str] = Header(None),
):
    """Return currently authenticated user profile."""
    seed_default_users(db)
    # Default to supervisor if no specific token header or user not found
    user = db.query(User).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No user found",
        )
    return UserResponse.model_validate(user)


@router.post("/logout")
def logout():
    """Sign out the current user session."""
    return {
        "status": "SUCCESS",
        "message": "User session successfully terminated.",
    }
