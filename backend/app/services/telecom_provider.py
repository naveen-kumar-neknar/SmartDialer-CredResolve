import uuid
import time
import random
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from app.models.enums import ProviderHealthStatus


@dataclass
class ProviderCallResult:
    success: bool
    provider_call_id: str
    error: Optional[str] = None
    latency_ms: int = 0
    is_timeout: bool = False


@dataclass
class ProviderEventPayload:
    event_id: str
    call_id: int
    provider: str
    event_type: str
    sequence_number: int
    payload: Dict[str, Any] = field(default_factory=dict)
    is_duplicate: bool = False
    is_out_of_order: bool = False


class BaseTelecomProvider(ABC):
    """
    Abstract Base Telecom Provider Interface.
    Both Provider A and Provider B adhere strictly to this contract.
    """

    def __init__(self, name: str):
        self.name = name
        self.total_requests = 0
        self.total_failures = 0
        self.total_timeouts = 0
        self.force_outage = False
        self.simulate_sleep = False

    @abstractmethod
    def initiate_call(self, call_id: int, phone_number: str) -> ProviderCallResult:
        """Initiate call through telephony gateway."""
        pass

    @abstractmethod
    def generate_events_for_call(
        self, call_id: int, outcome: str = "CONNECTED"
    ) -> List[ProviderEventPayload]:
        """Generate sequence of simulated provider webhook events for a call."""
        pass

    def get_health(self) -> ProviderHealthStatus:
        """Calculates provider health based on recent failure and timeout rates."""
        if self.force_outage:
            return ProviderHealthStatus.OUTAGE
        if self.total_requests == 0:
            return ProviderHealthStatus.HEALTHY

        failure_rate = (self.total_failures + self.total_timeouts) / self.total_requests
        if failure_rate > 0.5:
            return ProviderHealthStatus.OUTAGE
        elif failure_rate > 0.15:
            return ProviderHealthStatus.DEGRADED
        return ProviderHealthStatus.HEALTHY


class ProviderA(BaseTelecomProvider):
    """
    Provider A:
    - High reliability (>98% success)
    - Fast responses (low simulated latency: 20-50ms)
    - Low failure rate (<2%)
    - Strict in-order events
    """

    def __init__(self):
        super().__init__(name="ProviderA")
        self.failure_rate = 0.02

    def initiate_call(self, call_id: int, phone_number: str) -> ProviderCallResult:
        self.total_requests += 1

        if self.force_outage:
            self.total_failures += 1
            return ProviderCallResult(
                success=False,
                provider_call_id="",
                error="Provider A is experiencing a total outage",
                latency_ms=10,
            )

        latency = random.randint(10, 40)
        if self.simulate_sleep:
            time.sleep(latency / 1000.0)

        # Rare random failure
        if random.random() < self.failure_rate:
            self.total_failures += 1
            return ProviderCallResult(
                success=False,
                provider_call_id="",
                error="Provider A line busy or trunk unavailable",
                latency_ms=latency,
            )

        provider_call_id = f"provA-{uuid.uuid4().hex[:12]}"
        return ProviderCallResult(
            success=True,
            provider_call_id=provider_call_id,
            latency_ms=latency,
        )

    def generate_events_for_call(
        self, call_id: int, outcome: str = "CONNECTED"
    ) -> List[ProviderEventPayload]:
        events = []
        seq = 1

        # Event 1: INITIATED
        events.append(
            ProviderEventPayload(
                event_id=f"evt-{uuid.uuid4().hex[:16]}",
                call_id=call_id,
                provider=self.name,
                event_type="INITIATED",
                sequence_number=seq,
            )
        )
        seq += 1

        # Event 2: RINGING
        events.append(
            ProviderEventPayload(
                event_id=f"evt-{uuid.uuid4().hex[:16]}",
                call_id=call_id,
                provider=self.name,
                event_type="RINGING",
                sequence_number=seq,
            )
        )
        seq += 1

        if outcome == "CONNECTED":
            # Event 3: ANSWERED
            events.append(
                ProviderEventPayload(
                    event_id=f"evt-{uuid.uuid4().hex[:16]}",
                    call_id=call_id,
                    provider=self.name,
                    event_type="ANSWERED",
                    sequence_number=seq,
                )
            )
            seq += 1

            # Event 4: CONNECTED
            events.append(
                ProviderEventPayload(
                    event_id=f"evt-{uuid.uuid4().hex[:16]}",
                    call_id=call_id,
                    provider=self.name,
                    event_type="CONNECTED",
                    sequence_number=seq,
                )
            )
        else:
            # Event: FAILED
            events.append(
                ProviderEventPayload(
                    event_id=f"evt-{uuid.uuid4().hex[:16]}",
                    call_id=call_id,
                    provider=self.name,
                    event_type="FAILED",
                    sequence_number=seq,
                    payload={"reason": "User unanswered or line rejected"},
                )
            )

        return events


class ProviderB(BaseTelecomProvider):
    """
    Provider B:
    - Simulated higher latency (200-500ms)
    - Configurable failures (default 25%)
    - Occasional timeouts
    - Ability to simulate duplicate events and out-of-order events
    """

    def __init__(self):
        super().__init__(name="ProviderB")
        self.failure_rate = 0.25
        self.simulate_timeout = False
        self.simulate_failure = False
        self.simulate_duplicate = False
        self.simulate_out_of_order = False

    def initiate_call(self, call_id: int, phone_number: str) -> ProviderCallResult:
        self.total_requests += 1

        if self.force_outage:
            self.total_failures += 1
            return ProviderCallResult(
                success=False,
                provider_call_id="",
                error="Provider B is in full outage mode",
                latency_ms=10,
            )

        latency = random.randint(100, 250)
        if self.simulate_sleep:
            time.sleep(latency / 1000.0)

        if self.simulate_timeout:
            self.total_timeouts += 1
            return ProviderCallResult(
                success=False,
                provider_call_id="",
                error="Provider B gateway timeout (504)",
                latency_ms=latency,
                is_timeout=True,
            )

        if self.simulate_failure or (random.random() < self.failure_rate):
            self.total_failures += 1
            return ProviderCallResult(
                success=False,
                provider_call_id="",
                error="Provider B carrier circuit congestion (503)",
                latency_ms=latency,
            )

        provider_call_id = f"provB-{uuid.uuid4().hex[:12]}"
        return ProviderCallResult(
            success=True,
            provider_call_id=provider_call_id,
            latency_ms=latency,
        )

    def generate_events_for_call(
        self, call_id: int, outcome: str = "CONNECTED"
    ) -> List[ProviderEventPayload]:
        events = []
        seq = 1

        init_evt = ProviderEventPayload(
            event_id=f"evt-{uuid.uuid4().hex[:16]}",
            call_id=call_id,
            provider=self.name,
            event_type="INITIATED",
            sequence_number=seq,
        )
        events.append(init_evt)
        seq += 1

        ring_evt = ProviderEventPayload(
            event_id=f"evt-{uuid.uuid4().hex[:16]}",
            call_id=call_id,
            provider=self.name,
            event_type="RINGING",
            sequence_number=seq,
        )
        events.append(ring_evt)
        seq += 1

        if outcome == "CONNECTED":
            ans_evt = ProviderEventPayload(
                event_id=f"evt-{uuid.uuid4().hex[:16]}",
                call_id=call_id,
                provider=self.name,
                event_type="ANSWERED",
                sequence_number=seq,
            )
            events.append(ans_evt)
            seq += 1

            conn_evt = ProviderEventPayload(
                event_id=f"evt-{uuid.uuid4().hex[:16]}",
                call_id=call_id,
                provider=self.name,
                event_type="CONNECTED",
                sequence_number=seq,
            )
            events.append(conn_evt)
        else:
            fail_evt = ProviderEventPayload(
                event_id=f"evt-{uuid.uuid4().hex[:16]}",
                call_id=call_id,
                provider=self.name,
                event_type="FAILED",
                sequence_number=seq,
                payload={"reason": "Telephony line error / unallocated number"},
            )
            events.append(fail_evt)

        # If duplicate simulation is enabled, duplicate the RINGING or ANSWERED event with the exact same event_id
        if self.simulate_duplicate and len(events) >= 2:
            dup_target = events[1]
            duplicate = ProviderEventPayload(
                event_id=dup_target.event_id,  # same unique event_id
                call_id=dup_target.call_id,
                provider=dup_target.provider,
                event_type=dup_target.event_type,
                sequence_number=dup_target.sequence_number,
                payload=dup_target.payload,
                is_duplicate=True,
            )
            events.append(duplicate)

        # If out-of-order simulation is enabled, swap sequence or place late event
        if self.simulate_out_of_order and len(events) >= 3:
            # E.g., swap RINGING and ANSWERED, or put an old INITIATED event at the end
            late_init = ProviderEventPayload(
                event_id=f"evt-late-{uuid.uuid4().hex[:12]}",
                call_id=call_id,
                provider=self.name,
                event_type="RINGING",
                sequence_number=1,  # Old sequence arriving late!
                is_out_of_order=True,
            )
            events.append(late_init)

        return events


class TelecomProviderManager:
    """Singleton/central manager holding references to Provider A and Provider B."""

    def __init__(self):
        self.provider_a = ProviderA()
        self.provider_b = ProviderB()
        self.active_provider_name = "ProviderA"

    def get_active_provider(self) -> BaseTelecomProvider:
        if self.active_provider_name == "ProviderB":
            return self.provider_b
        return self.provider_a

    def set_active_provider(self, name: str):
        if name in {"ProviderA", "ProviderB"}:
            self.active_provider_name = name

    def get_provider_by_name(self, name: str) -> BaseTelecomProvider:
        if name == "ProviderB":
            return self.provider_b
        return self.provider_a

    def get_overall_health(self) -> ProviderHealthStatus:
        active = self.get_active_provider()
        return active.get_health()


# Central singleton instance
provider_manager = TelecomProviderManager()
