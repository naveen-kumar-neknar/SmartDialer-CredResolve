import math
from typing import Dict, Any
from app.models.enums import ProviderHealthStatus


class PredictivePacingEngine:
    """
    Predictive Pacing Engine:
    Calculates the mathematically optimized number of calls to initiate
    based on agent availability, telephony pipeline, answer rate, and provider health.

    CRITICAL SAFETY CONSTRAINT:
    This engine NEVER initiates calls directly. It only produces recommendation proposals.
    All proposals must pass through the Safety Controller before execution.
    """

    @staticmethod
    def calculate_proposed_calls(
        available_agents: int,
        reserved_agents: int,
        active_calls: int,
        calls_ringing: int,
        historical_answer_rate: float,
        average_call_duration: int,
        provider_health: ProviderHealthStatus,
    ) -> Dict[str, Any]:
        """
        Rule-based pacing calculation:

        Inputs:
        - available_agents (A_avail): Agents ready to take a call
        - reserved_agents (A_res): Agents already held for in-flight setup
        - active_calls (N_active): Calls currently in CONNECTED status with agents
        - calls_ringing (N_ring): Calls dispatched but not yet answered
        - historical_answer_rate (r_ans): Historical ratio (0.01 - 1.0) of dialed calls that are answered
        - average_call_duration (T_dur): Average duration of connected call in seconds
        - provider_health (H_prov): Telephony provider operational status

        Algorithm Steps:
        1. Effective Idle Agents (A_idle) = max(0, available_agents - reserved_agents)
           If no agents are idle, proposed calls is 0.

        2. Expected In-Flight Answers (C_inflight) = calls_ringing * answer_rate
           Represents calls already ringing that are expected to connect and consume an agent.

        3. Net Connections Needed (C_needed) = max(0.0, A_idle - C_inflight)
           We only want as many connections as we have uncommitted idle agents.

        4. Theoretical Pacing Target (Calls_raw) = C_needed / max(0.10, answer_rate)
           Since each dial has probability r_ans of connecting, to achieve C_needed connections,
           we need (C_needed / r_ans) dials.

        5. Provider Health Factor:
           - HEALTHY: 1.0
           - DEGRADED: 0.5 (throttled due to circuit errors)
           - OUTAGE: 0.0 (telecom gateway down)

        6. Safety Clamp:
           Raw calls are throttled and clamped to an upper pacing ceiling of (A_idle * 3)
           to avoid dangerous spikes if answer rate suddenly surges.
        """

        # Step 1: Effective idle agents
        effective_idle_agents = max(0, available_agents - reserved_agents)

        # Step 2: In-flight expected connections
        safe_answer_rate = max(0.01, min(1.0, float(historical_answer_rate)))
        expected_inflight_answers = float(calls_ringing) * safe_answer_rate

        # Step 3: Net connections needed
        net_connections_needed = max(0.0, float(effective_idle_agents) - expected_inflight_answers)

        # Step 4: Raw calls calculation
        if effective_idle_agents == 0 or net_connections_needed <= 0.05:
            raw_proposed = 0.0
        else:
            raw_proposed = net_connections_needed / safe_answer_rate

        # Step 5: Provider health throttle
        if provider_health == ProviderHealthStatus.OUTAGE:
            health_factor = 0.0
        elif provider_health == ProviderHealthStatus.DEGRADED:
            health_factor = 0.5
        else:
            health_factor = 1.0

        throttled_calls = raw_proposed * health_factor

        # Step 6: Pacing ceiling (max 3x idle agents, or 0 if 0 agents)
        max_ceiling = effective_idle_agents * 3
        clamped_calls = min(int(math.floor(throttled_calls)), max_ceiling)
        final_proposed = max(0, clamped_calls)

        explanation = (
            f"Idle agents: {effective_idle_agents}. Ringing: {calls_ringing} "
            f"(expected to yield {expected_inflight_answers:.2f} connects at {safe_answer_rate*100:.1f}% answer rate). "
            f"Net connections required: {net_connections_needed:.2f}. "
            f"Provider status: {provider_health.value} (throttle: {health_factor*100}%). "
            f"Raw dials: {raw_proposed:.1f} -> Proposed: {final_proposed} call(s)."
        )

        return {
            "proposed_calls": final_proposed,
            "effective_idle_agents": effective_idle_agents,
            "expected_inflight_answers": round(expected_inflight_answers, 2),
            "net_connections_needed": round(net_connections_needed, 2),
            "health_throttle_factor": health_factor,
            "answer_rate_used": safe_answer_rate,
            "explanation": explanation,
        }
