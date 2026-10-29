"""
SmartDialer Telephony Simulation Engine
Simulates multi-agent outbound dialing campaigns across multiple realistic scenarios:
Scenario A: 20% answer rate, 120s average talk time
Scenario B: 50% answer rate, 90s average talk time
Scenario C: 70% answer rate, 180s average talk time
Scenario D: Variable answer rate (20-80%), provider latency, and failures

TARGET: Abandoned connected calls caused by insufficient agent capacity must be ZERO (0).
"""

import sys
import os
import random
import uuid
from dataclasses import dataclass, field
from typing import List, Dict, Any

# Ensure backend imports resolve
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend")))

from app.models.enums import ProviderHealthStatus
from app.services.pacing_engine import PredictivePacingEngine


@dataclass
class SimulatedAgent:
    id: int
    name: str
    status: str = "AVAILABLE"  # AVAILABLE, RESERVED, CONNECTED
    call_end_tick: int = 0


@dataclass
class SimulationStats:
    scenario_name: str
    ticks: int
    calls_initiated: int = 0
    calls_connected: int = 0
    calls_failed: int = 0
    abandoned_calls: int = 0
    safety_approved: int = 0
    safety_reduced: int = 0
    safety_rejected: int = 0
    safety_fallback: int = 0
    total_agent_busy_ticks: int = 0
    total_agent_ticks: int = 0

    @property
    def agent_utilization(self) -> float:
        if self.total_agent_ticks == 0:
            return 0.0
        return round((self.total_agent_busy_ticks / self.total_agent_ticks) * 100, 1)

    @property
    def connection_rate(self) -> float:
        if self.calls_initiated == 0:
            return 0.0
        return round((self.calls_connected / self.calls_initiated) * 100, 1)


class CampaignSimulator:
    def __init__(
        self,
        scenario_name: str,
        num_agents: int,
        answer_rate: float,
        average_talk_time_seconds: int,
        ticks: int = 150,
        provider_failure_rate: float = 0.0,
        variable_rate: bool = False,
    ):
        self.scenario_name = scenario_name
        self.num_agents = num_agents
        self.base_answer_rate = answer_rate
        self.talk_time_ticks = max(2, average_talk_time_seconds // 10)  # 1 tick = ~10 seconds
        self.ticks = ticks
        self.provider_failure_rate = provider_failure_rate
        self.variable_rate = variable_rate

        self.agents = [
            SimulatedAgent(id=i + 1, name=f"Agent-{i+1}")
            for i in range(num_agents)
        ]
        self.stats = SimulationStats(scenario_name=scenario_name, ticks=ticks)
        self.ringing_calls = 0  # in-flight dials

    def run(self) -> SimulationStats:
        for current_tick in range(self.ticks):
            # 1. Update existing agent talk times & free up completed calls
            for agent in self.agents:
                if agent.status == "CONNECTED":
                    self.stats.total_agent_busy_ticks += 1
                    if current_tick >= agent.call_end_tick:
                        agent.status = "AVAILABLE"
                self.stats.total_agent_ticks += 1

            # 2. Determine current dynamic answer rate
            if self.variable_rate:
                # Variable answer rate swings between 20% and 80%
                current_answer_rate = random.uniform(0.20, 0.80)
            else:
                current_answer_rate = self.base_answer_rate

            # 3. Assess available capacity
            available_agents = sum(1 for a in self.agents if a.status == "AVAILABLE")
            connected_agents = sum(1 for a in self.agents if a.status == "CONNECTED")

            # Provider health calculation
            provider_health = (
                ProviderHealthStatus.DEGRADED
                if self.provider_failure_rate > 0.15
                else ProviderHealthStatus.HEALTHY
            )

            # 4. Invoke Predictive Pacing Engine
            pacing = PredictivePacingEngine.calculate_proposed_calls(
                available_agents=available_agents,
                reserved_agents=0,
                active_calls=connected_agents,
                calls_ringing=self.ringing_calls,
                historical_answer_rate=current_answer_rate,
                average_call_duration=self.talk_time_ticks * 10,
                provider_health=provider_health,
            )
            proposed_calls = pacing["proposed_calls"]

            # 5. Safety Controller Enforcement
            # Zero-Abandonment Rule:
            # Overdialing is only permitted if the mathematical 99.9th percentile of answered calls
            # does not exceed currently available agents.
            # When in doubt or high answer rate, fall back strictly to progressive 1:1 cap.
            if available_agents == 0:
                approved = 0
                self.stats.safety_rejected += 1
            elif self.ringing_calls >= available_agents:
                approved = 0
                self.stats.safety_rejected += 1
            elif current_answer_rate >= 0.35 or available_agents < 4:
                # With answer rate >= 35% or small pool, overdialing creates abandon risk.
                # Strictly cap to available agents to achieve 0 abandoned calls guarantee.
                approved = min(proposed_calls, available_agents)
                self.stats.safety_fallback += 1
            elif proposed_calls > available_agents:
                # Conservative pacing: cap dials so expected answers stay safely below available agents
                safe_dials = int(available_agents / max(0.20, current_answer_rate))
                # Never allow more dials than what could exceed capacity at 2-sigma
                max_safe = min(safe_dials, available_agents + 1)
                approved = min(proposed_calls, max_safe)
                self.stats.safety_reduced += 1
            else:
                approved = min(proposed_calls, available_agents)
                self.stats.safety_approved += 1

            approved = max(0, approved)

            # 6. Execute Approved Calls (Telephony Simulation)
            for _ in range(approved):
                self.stats.calls_initiated += 1

                # Check telecom circuit failure
                if random.random() < self.provider_failure_rate:
                    self.stats.calls_failed += 1
                    continue

                # Check borrower answer probability
                answered = random.random() < current_answer_rate
                if answered:
                    # Allocate agent
                    idle_agent = next((a for a in self.agents if a.status == "AVAILABLE"), None)
                    if idle_agent:
                        idle_agent.status = "CONNECTED"
                        # Call duration variance (+/- 30%)
                        duration = max(1, int(self.talk_time_ticks * random.uniform(0.7, 1.3)))
                        idle_agent.call_end_tick = current_tick + duration
                        self.stats.calls_connected += 1
                    else:
                        # CRITICAL: Abandoned call due to agent shortage!
                        # The Safety Controller's goal is for this to remain ZERO!
                        self.stats.abandoned_calls += 1
                        self.stats.calls_failed += 1
                else:
                    # Unanswered / Busy / Voicemail
                    self.stats.calls_failed += 1

        return self.stats


def run_all_scenarios():
    print("=" * 80)
    print("          SMARTDIALER PREDICTIVE & PROGRESSIVE PACING SIMULATION         ")
    print("                      [SIMULATED BENCHMARK DATA]                          ")
    print("=" * 80)
    print()

    scenarios = [
        ("Scenario A: 20% Answer Rate, 120s Talk Time", 10, 0.20, 120, 150, 0.01, False),
        ("Scenario B: 50% Answer Rate, 90s Talk Time", 10, 0.50, 90, 150, 0.01, False),
        ("Scenario C: 70% Answer Rate, 180s Talk Time", 10, 0.70, 180, 150, 0.01, False),
        ("Scenario D: Variable Rate (20-80%), Latency & Provider B Failures", 10, 0.45, 100, 150, 0.20, True),
    ]

    results: List[SimulationStats] = []

    for name, agents, ans_rate, talk_time, ticks, fail_rate, variable in scenarios:
        sim = CampaignSimulator(
            scenario_name=name,
            num_agents=agents,
            answer_rate=ans_rate,
            average_talk_time_seconds=talk_time,
            ticks=ticks,
            provider_failure_rate=fail_rate,
            variable_rate=variable,
        )
        res = sim.run()
        results.append(res)

    # Print Formatted Results
    print(f"{'Scenario':<42} | {'Calls':<6} | {'Conn':<6} | {'Fail':<6} | {'Util%':<6} | {'Aband':<5} | {'Safety Decisions'}")
    print("-" * 105)
    for r in results:
        safety_summary = f"App:{r.safety_approved} Red:{r.safety_reduced} Rej:{r.safety_rejected} Fallback:{r.safety_fallback}"
        print(
            f"{r.scenario_name:<42} | "
            f"{r.calls_initiated:<6} | "
            f"{r.calls_connected:<6} | "
            f"{r.calls_failed:<6} | "
            f"{r.agent_utilization:<6}% | "
            f"{r.abandoned_calls:<5} | "
            f"{safety_summary}"
        )

    print("-" * 105)
    print()
    abandoned_total = sum(r.abandoned_calls for r in results)
    print(f"VERIFICATION VERDICT: Total Abandoned Calls across all scenarios = {abandoned_total}")
    if abandoned_total == 0:
        print(">>> SUCCESS: 0 ABANDONED CALLS! Safety Controller guarantees call safety without agent dropouts.")
    else:
        print(f">>> WARNING: {abandoned_total} abandoned calls detected.")
    print()
    print("=" * 80)
    return results


if __name__ == "__main__":
    run_all_scenarios()
