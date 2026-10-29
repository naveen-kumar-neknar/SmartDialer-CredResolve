import uuid
from datetime import datetime, timezone, timedelta
import concurrent.futures
from app.models.agent import Agent
from app.models.borrower import Borrower
from app.models.call import Call
from app.models.enums import (
    AgentStatus,
    BorrowerCallStatus,
    CallStatus,
    ProviderHealthStatus,
)
from app.services.call_allocator import CallAllocator
from app.services.event_processor import EventProcessor
from app.services.pacing_engine import PredictivePacingEngine
from app.services.safety_controller import SafetyController
from app.services.telecom_provider import provider_manager, ProviderB


def test_health_endpoint(client):
    """Test health check endpoint."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["app"] == "SmartDialer"


def test_agent_creation_and_state_transitions(client, db_session):
    """Test agent creation and state machine transition enforcement."""
    # Create agent
    resp = client.post("/api/agents", json={"name": "Alice Agent", "status": "AVAILABLE"})
    assert resp.status_code == 201
    agent_id = resp.json()["id"]
    assert resp.json()["status"] == "AVAILABLE"

    # Valid transition: AVAILABLE -> PAUSED
    patch_resp = client.patch(f"/api/agents/{agent_id}/status", json={"status": "PAUSED"})
    assert patch_resp.status_code == 200
    assert patch_resp.json()["status"] == "PAUSED"

    # Invalid transition: PAUSED directly to CONNECTED
    bad_resp = client.patch(f"/api/agents/{agent_id}/status", json={"status": "CONNECTED"})
    assert bad_resp.status_code == 400
    assert "Invalid agent status transition" in bad_resp.json()["detail"]


def test_borrower_creation_and_pii_masking(client, db_session):
    """Test borrower creation and phone number masking."""
    resp = client.post(
        "/api/borrowers",
        json={
            "name": "Jane Doe",
            "phone_number": "+15551234567",
            "priority": 1,
        },
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "Jane Doe"
    # Verify masked phone number
    assert "***" in data["phone_number"]
    assert data["call_status"] == "UNPROCESSED"


def test_successful_progressive_dialing(client, db_session):
    """Test progressive dialer allocates available agent and borrower."""
    # Seed 1 agent and 1 borrower
    agent = Agent(name="John Doe", status=AgentStatus.AVAILABLE.value)
    borrower = Borrower(
        name="Bob Smith",
        phone_number="+1 (555) ***-9999",
        priority=1,
        call_status=BorrowerCallStatus.UNPROCESSED.value,
    )
    db_session.add_all([agent, borrower])
    db_session.commit()

    resp = client.post("/api/dialer/progressive", json={"batch_size": 1})
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "SUCCESS"
    assert data["calls_initiated"] == 1

    # Verify agent is moved to DIALING or RESERVED
    db_session.refresh(agent)
    assert agent.status in [AgentStatus.DIALING.value, AgentStatus.RESERVED.value]

    # Verify borrower is moved to CALLING
    db_session.refresh(borrower)
    assert borrower.call_status == BorrowerCallStatus.CALLING.value
    assert borrower.attempt_count == 1


def test_no_available_agent(client, db_session):
    """Progressive dialer must not initiate calls if no agents are available."""
    # Seed borrower only
    borrower = Borrower(
        name="Bob Smith",
        phone_number="+1 (555) ***-9999",
        priority=1,
        call_status=BorrowerCallStatus.UNPROCESSED.value,
    )
    db_session.add(borrower)
    db_session.commit()

    resp = client.post("/api/dialer/progressive", json={"batch_size": 1})
    assert resp.status_code == 200
    data = resp.json()
    assert data["calls_initiated"] == 0
    assert data["status"] == "HALTED"
    assert "ZERO_AGENT_CAPACITY" in data["message"] or "No unreserved agents" in data["message"]


def test_concurrent_allocation_attempts(db_session):
    """
    Simulate concurrent progressive allocation requests.
    With 1 available agent and 5 concurrent attempts, exactly 1 call should succeed.
    Zero duplicate agent or borrower allocations.
    """
    agent = Agent(name="Shared Agent", status=AgentStatus.AVAILABLE.value)
    borrowers = [
        Borrower(
            name=f"Borrower {i}",
            phone_number=f"+1 (555) ***-{1000+i}",
            priority=1,
            call_status=BorrowerCallStatus.UNPROCESSED.value,
        )
        for i in range(5)
    ]
    db_session.add(agent)
    db_session.add_all(borrowers)
    db_session.commit()

    results = []

    def attempt_allocation():
        # Call allocator in separate session
        return CallAllocator.execute_progressive_dialing_batch(db_session, max_batch_size=1)

    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        futures = [executor.submit(attempt_allocation) for _ in range(5)]
        for f in concurrent.futures.as_completed(futures):
            results.append(f.result())

    total_initiated = sum(r["calls_initiated"] for r in results)
    assert total_initiated == 1, f"Expected exactly 1 call initiated, but got {total_initiated}"

    # Verify database has exactly 1 call
    calls = db_session.query(Call).all()
    assert len(calls) == 1
    assert calls[0].agent_id == agent.id


def test_duplicate_provider_events(client, db_session):
    """Idempotency test: duplicate events must not cause duplicate state transitions."""
    agent = Agent(name="Agent Bob", status=AgentStatus.AVAILABLE.value)
    borrower = Borrower(name="Borrower A", phone_number="+1 (555) ***-1111", priority=1)
    db_session.add_all([agent, borrower])
    db_session.commit()

    # Initiate call
    call = Call(
        borrower_id=borrower.id,
        agent_id=agent.id,
        provider="ProviderA",
        status=CallStatus.INITIATED.value,
    )
    db_session.add(call)
    db_session.commit()
    db_session.refresh(call)

    event_id = f"evt-unique-{uuid.uuid4().hex[:8]}"

    # Event 1: RINGING
    evt1 = {
        "event_id": event_id,
        "call_id": call.id,
        "provider": "ProviderA",
        "event_type": "RINGING",
        "sequence_number": 2,
    }
    r1 = client.post("/api/providers/events/webhook", json=evt1)
    assert r1.status_code == 200
    assert r1.json()["status"] == "PROCESSED"

    # Event 2: Duplicate exact event_id
    r2 = client.post("/api/providers/events/webhook", json=evt1)
    assert r2.status_code == 200
    assert r2.json()["status"] == "IGNORED_DUPLICATE"

    # Verify call status is still RINGING
    db_session.refresh(call)
    assert call.status == CallStatus.RINGING.value


def test_out_of_order_provider_events(client, db_session):
    """Out-of-order protection: a late event must not move a connected call backwards."""
    agent = Agent(name="Agent Bob", status=AgentStatus.AVAILABLE.value)
    borrower = Borrower(name="Borrower A", phone_number="+1 (555) ***-1111", priority=1)
    db_session.add_all([agent, borrower])
    db_session.commit()

    call = Call(
        borrower_id=borrower.id,
        agent_id=agent.id,
        provider="ProviderA",
        status=CallStatus.CONNECTED.value,  # Already connected!
    )
    db_session.add(call)
    db_session.commit()
    db_session.refresh(call)

    # Late RINGING event arriving after call is already CONNECTED
    late_evt = {
        "event_id": f"evt-late-{uuid.uuid4().hex[:8]}",
        "call_id": call.id,
        "provider": "ProviderA",
        "event_type": "RINGING",
        "sequence_number": 2,
    }
    resp = client.post("/api/providers/events/webhook", json=late_evt)
    assert resp.status_code == 200
    assert resp.json()["status"] == "IGNORED_OUT_OF_ORDER"

    # Call remains CONNECTED
    db_session.refresh(call)
    assert call.status == CallStatus.CONNECTED.value


def test_terminal_call_protection(client, db_session):
    """Never automatically move a completed call back to an active state."""
    agent = Agent(name="Agent Bob", status=AgentStatus.AVAILABLE.value)
    borrower = Borrower(name="Borrower A", phone_number="+1 (555) ***-1111", priority=1)
    db_session.add_all([agent, borrower])
    db_session.commit()

    call = Call(
        borrower_id=borrower.id,
        agent_id=agent.id,
        provider="ProviderA",
        status=CallStatus.COMPLETED.value,  # Already completed
    )
    db_session.add(call)
    db_session.commit()
    db_session.refresh(call)

    # Late event trying to ring or connect
    late_evt = {
        "event_id": f"evt-after-complete-{uuid.uuid4().hex[:8]}",
        "call_id": call.id,
        "provider": "ProviderA",
        "event_type": "CONNECTED",
        "sequence_number": 5,
    }
    resp = client.post("/api/providers/events/webhook", json=late_evt)
    assert resp.status_code == 200
    assert resp.json()["status"] == "IGNORED_CALL_TERMINAL"

    db_session.refresh(call)
    assert call.status == CallStatus.COMPLETED.value


def test_provider_timeout_handling(client, db_session):
    """Provider timeout during dispatch must fail call and release agent reservation."""
    # Switch to Provider B with timeout simulation
    provider_manager.set_active_provider("ProviderB")
    prov_b = provider_manager.provider_b
    if isinstance(prov_b, ProviderB):
        prov_b.simulate_timeout = True

    agent = Agent(name="Agent Fast", status=AgentStatus.AVAILABLE.value)
    borrower = Borrower(name="Borrower Timeout", phone_number="+1 (555) ***-8888", priority=1)
    db_session.add_all([agent, borrower])
    db_session.commit()

    result = CallAllocator.execute_progressive_dialing_batch(db_session, max_batch_size=1)
    assert result["calls_initiated"] == 1
    call = result["calls"][0]
    assert call.status == CallStatus.FAILED.value
    assert "timeout" in call.failure_reason.lower()

    # Verify agent was released back to AVAILABLE
    db_session.refresh(agent)
    assert agent.status == AgentStatus.AVAILABLE.value


def test_provider_outage_stops_dialing(client, db_session):
    """Safety Controller must immediately halt all dialing during provider outage."""
    agent = Agent(name="Agent Outage", status=AgentStatus.AVAILABLE.value)
    borrower = Borrower(name="Borrower Outage", phone_number="+1 (555) ***-7777", priority=1)
    db_session.add_all([agent, borrower])
    db_session.commit()

    # Trigger provider outage
    provider_manager.provider_a.force_outage = True

    resp = client.post("/api/dialer/progressive", json={"batch_size": 1})
    assert resp.status_code == 200
    data = resp.json()
    assert data["calls_initiated"] == 0
    assert data["status"] == "HALTED"
    assert "OUTAGE" in data["message"]


def test_safety_controller_limits_and_decisions(db_session):
    """Test safety controller reduces or rejects unsafe proposals and records decisions."""
    # Case 1: Proposed 10 calls with only 2 available agents in progressive mode
    approved, decision = SafetyController.evaluate_and_enforce(
        db=db_session,
        dialer_mode="PROGRESSIVE",
        proposed_calls=10,
        available_agents=2,
        reserved_agents=0,
        active_calls=0,
        calls_ringing=0,
        provider_health=ProviderHealthStatus.HEALTHY,
    )
    assert approved == 2
    assert decision.decision == "REDUCED"
    assert "PROGRESSIVE_AGENT_CAP" in decision.rule_triggered

    # Case 2: Ringing calls saturate agents
    approved_ring, dec_ring = SafetyController.evaluate_and_enforce(
        db=db_session,
        dialer_mode="PROGRESSIVE",
        proposed_calls=2,
        available_agents=2,
        reserved_agents=0,
        active_calls=0,
        calls_ringing=2,  # Already 2 calls ringing
        provider_health=ProviderHealthStatus.HEALTHY,
    )
    assert approved_ring == 0
    assert dec_ring.decision == "REJECTED"
    assert "RINGING_PIPELINE_SATURATED" in dec_ring.rule_triggered


def test_predictive_pacing_different_answer_rates():
    """Test predictive pacing engine with 20%, 50%, and 70% answer rates."""
    # 20% answer rate: needs more dials per desired connect
    calc_20 = PredictivePacingEngine.calculate_proposed_calls(
        available_agents=5,
        reserved_agents=0,
        active_calls=2,
        calls_ringing=0,
        historical_answer_rate=0.20,
        average_call_duration=120,
        provider_health=ProviderHealthStatus.HEALTHY,
    )
    # Expected: raw dials = 5 / 0.20 = 25, clamped to ceiling 5*3 = 15
    assert calc_20["proposed_calls"] == 15

    # 50% answer rate: 5 / 0.50 = 10 calls
    calc_50 = PredictivePacingEngine.calculate_proposed_calls(
        available_agents=5,
        reserved_agents=0,
        active_calls=2,
        calls_ringing=0,
        historical_answer_rate=0.50,
        average_call_duration=90,
        provider_health=ProviderHealthStatus.HEALTHY,
    )
    assert calc_50["proposed_calls"] == 10

    # 70% answer rate: 5 / 0.70 = 7 calls
    calc_70 = PredictivePacingEngine.calculate_proposed_calls(
        available_agents=5,
        reserved_agents=0,
        active_calls=2,
        calls_ringing=0,
        historical_answer_rate=0.70,
        average_call_duration=180,
        provider_health=ProviderHealthStatus.HEALTHY,
    )
    assert calc_70["proposed_calls"] == 7


def test_reservation_expiry_and_recovery(db_session):
    """Test background recovery clears stale agent reservations caused by crashes."""
    # Agent stuck in RESERVED for 120 seconds with no active call
    old_time = datetime.now(timezone.utc) - timedelta(seconds=120)
    agent = Agent(name="Stale Agent", status=AgentStatus.RESERVED.value, reserved_at=old_time)
    borrower = Borrower(
        name="Stale Borrower",
        phone_number="+1 (555) ***-6666",
        priority=1,
        call_status=BorrowerCallStatus.CALLING.value,
        last_called_at=old_time,
    )
    db_session.add_all([agent, borrower])
    db_session.commit()

    recovery_stats = EventProcessor.recover_stale_reservations(db_session, timeout_seconds=45)
    assert recovery_stats["recovered_agents"] == 1
    assert recovery_stats["recovered_borrowers"] == 1

    # Verify agent is back to AVAILABLE
    db_session.refresh(agent)
    assert agent.status == AgentStatus.AVAILABLE.value

    # Verify borrower is back to UNPROCESSED (so they can be safely retried)
    db_session.refresh(borrower)
    assert borrower.call_status == BorrowerCallStatus.UNPROCESSED.value


def test_concurrent_borrower_allocation(db_session):
    """
    Simulate multiple simultaneous requests competing for a single unprocessed borrower.
    Guarantees the same borrower can NEVER be allocated to multiple concurrent calls.
    """
    agents = [
        Agent(name=f"Agent {i}", status=AgentStatus.AVAILABLE.value)
        for i in range(5)
    ]
    single_borrower = Borrower(
        name="Target Borrower",
        phone_number="+1 (555) ***-9999",
        priority=1,
        call_status=BorrowerCallStatus.UNPROCESSED.value,
    )
    db_session.add_all(agents)
    db_session.add(single_borrower)
    db_session.commit()

    results = []
    def attempt_dial():
        return CallAllocator.execute_progressive_dialing_batch(db_session, max_batch_size=1)

    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        futures = [executor.submit(attempt_dial) for _ in range(5)]
        for f in concurrent.futures.as_completed(futures):
            results.append(f.result())

    total_initiated = sum(r["calls_initiated"] for r in results)
    assert total_initiated == 1, f"Expected exactly 1 call for borrower, got {total_initiated}"

    calls = db_session.query(Call).filter(Call.borrower_id == single_borrower.id).all()
    assert len(calls) == 1


def test_failed_call_simulation_releases_resources(client, db_session):
    """
    When an active call fails or is simulated as failed, the linked agent must
    be immediately released back to AVAILABLE and borrower marked FAILED.
    """
    agent = Agent(name="In-Call Agent", status=AgentStatus.CONNECTED.value)
    borrower = Borrower(name="In-Call Borrower", phone_number="+1 (555) ***-3333", priority=1, call_status=BorrowerCallStatus.CONNECTED.value)
    db_session.add_all([agent, borrower])
    db_session.commit()

    call = Call(
        borrower_id=borrower.id,
        agent_id=agent.id,
        status=CallStatus.CONNECTED.value,
        provider="ProviderA",
    )
    db_session.add(call)
    db_session.commit()
    db_session.refresh(call)
    agent.current_call_id = call.id
    db_session.commit()

    # Simulate call failure
    resp = client.post(f"/api/calls/{call.id}/simulate", json={
        "target_status": "FAILED",
        "failure_reason": "Carrier network drop",
    })
    assert resp.status_code == 200
    assert resp.json()["status"] == "FAILED"

    # Verify agent is released to AVAILABLE
    db_session.refresh(agent)
    assert agent.status == AgentStatus.AVAILABLE.value
    assert agent.current_call_id is None

    # Verify borrower is marked FAILED
    db_session.refresh(borrower)
    assert borrower.call_status == BorrowerCallStatus.FAILED.value


def test_sudden_agent_drop_reflected_in_safety_decisions(db_session):
    """
    A sudden drop in available agents (e.g. from 10 to 0) must immediately be
    reflected in new dialing decisions, resulting in ZERO approved calls.
    """
    # 0 agents available
    approved, decision = SafetyController.evaluate_and_enforce(
        db=db_session,
        dialer_mode="PREDICTIVE",
        proposed_calls=5,
        available_agents=0,
        reserved_agents=0,
        active_calls=10,
        calls_ringing=0,
        provider_health=ProviderHealthStatus.HEALTHY,
    )
    assert approved == 0
    assert decision.decision == "REJECTED"
    assert "ZERO_AGENT_CAPACITY" in decision.rule_triggered

    # Agent count drops below 3 -> progressive fallback
    approved_few, decision_few = SafetyController.evaluate_and_enforce(
        db=db_session,
        dialer_mode="PREDICTIVE",
        proposed_calls=5,
        available_agents=2,
        reserved_agents=0,
        active_calls=8,
        calls_ringing=0,
        provider_health=ProviderHealthStatus.HEALTHY,
    )
    assert approved_few == 2
    assert decision_few.decision == "FALLBACK_PROGRESSIVE"
    assert "SMALL_AGENT_POOL_FALLBACK" in decision_few.rule_triggered


def test_invalid_call_state_transitions_rejected(client, db_session):
    """
    Invalid state machine jumps must be rejected with HTTP 400 Bad Request.
    """
    borrower = Borrower(name="Borrower Test", phone_number="+1 (555) ***-4444", priority=1)
    db_session.add(borrower)
    db_session.commit()

    call = Call(
        borrower_id=borrower.id,
        status=CallStatus.QUEUED.value,
        provider="ProviderA",
    )
    db_session.add(call)
    db_session.commit()
    db_session.refresh(call)

    # Invalid jump: QUEUED directly to CONNECTED
    resp = client.post(f"/api/calls/{call.id}/simulate", json={
        "target_status": "CONNECTED",
    })
    assert resp.status_code == 400
    assert "Invalid" in resp.json()["detail"]


def test_auth_signup_and_login(client, db_session):
    """Test user registration, login, and profile retrieval."""
    # 1. Signup new operator
    signup_payload = {
        "name": "Sarah Connor",
        "email": "sarah@credresolve.com",
        "password": "securepassword123",
        "role": "SUPERVISOR",
    }
    signup_resp = client.post("/api/auth/signup", json=signup_payload)
    assert signup_resp.status_code == 201
    signup_data = signup_resp.json()
    assert signup_data["user"]["email"] == "sarah@credresolve.com"
    assert "access_token" in signup_data

    # 2. Login with valid credentials
    login_payload = {
        "email": "sarah@credresolve.com",
        "password": "securepassword123",
    }
    login_resp = client.post("/api/auth/login", json=login_payload)
    assert login_resp.status_code == 200
    assert login_resp.json()["user"]["name"] == "Sarah Connor"


def test_auth_invalid_credentials(client, db_session):
    """Test login rejection on wrong password."""
    signup_payload = {
        "name": "John Doe",
        "email": "john@credresolve.com",
        "password": "correctpassword",
        "role": "AGENT",
    }
    client.post("/api/auth/signup", json=signup_payload)

    # Wrong password
    bad_login = client.post("/api/auth/login", json={
        "email": "john@credresolve.com",
        "password": "wrongpassword",
    })
    assert bad_login.status_code == 401
    assert "Invalid email or password" in bad_login.json()["detail"]

