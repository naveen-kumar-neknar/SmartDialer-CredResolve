import pytest
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient

from app.database import Base, get_db
from app.main import app
from app.services.telecom_provider import provider_manager

test_engine = create_engine(
    "sqlite://",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)


@pytest.fixture(autouse=True)
def reset_provider_state():
    """Automatically reset provider state before and after every test."""
    provider_manager.set_active_provider("ProviderA")
    provider_manager.provider_a.force_outage = False
    provider_manager.provider_a.failure_rate = 0.0
    provider_manager.provider_a.total_requests = 0
    provider_manager.provider_a.total_failures = 0
    provider_manager.provider_b.force_outage = False
    provider_manager.provider_b.simulate_failure = False
    provider_manager.provider_b.simulate_timeout = False
    provider_manager.provider_b.simulate_duplicate = False
    provider_manager.provider_b.simulate_out_of_order = False
    yield
    provider_manager.set_active_provider("ProviderA")
    provider_manager.provider_a.force_outage = False
    provider_manager.provider_a.failure_rate = 0.0


@pytest.fixture(scope="function")
def db_session():
    """Create fresh in-memory database schema for each test."""
    Base.metadata.create_all(bind=test_engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=test_engine)


@pytest.fixture(scope="function")
def client(db_session):
    """Override database dependency with test database session."""
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    test_client = TestClient(app)
    yield test_client
    app.dependency_overrides.clear()
