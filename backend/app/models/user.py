import os
import hashlib
from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, DateTime
from app.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    email = Column(String(150), unique=True, index=True, nullable=False)
    name = Column(String(100), nullable=False)
    hashed_password = Column(String(256), nullable=False)
    salt = Column(String(64), nullable=False)
    role = Column(String(50), default="SUPERVISOR", nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    @classmethod
    def create(cls, email: str, name: str, password: str, role: str = "SUPERVISOR") -> "User":
        salt = os.urandom(16).hex()
        hashed = cls._hash_password(password, salt)
        return cls(
            email=email.strip().lower(),
            name=name.strip(),
            hashed_password=hashed,
            salt=salt,
            role=role.upper(),
        )

    def verify_password(self, password: str) -> bool:
        return self.hashed_password == self._hash_password(password, self.salt)

    @staticmethod
    def _hash_password(password: str, salt: str) -> str:
        return hashlib.sha256((salt + password).encode("utf-8")).hexdigest()
