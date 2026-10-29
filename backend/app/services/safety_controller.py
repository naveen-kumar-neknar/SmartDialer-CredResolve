import logging
from typing import Dict, Any, Tuple
from sqlalchemy.orm import Session

from app.models.safety_decision import SafetyDecision
from app.models.enums import ProviderHealthStatus, SafetyDecisionType

logger = logging.getLogger(__name__)


class SafetyController:
    """
    Safety Controller:
    Acts as the authoritative gateway between dialing recommendations (Pacing Engine)
    and execution (Call Allocator).

    Guarantees:
    - Never dials during telecom outages
    - Enforces zero-abandonment protection
    - Automatically falls back to progressive 1:1 dialing when predictive conditions are volatile
    - Audits every safety verdict into the database
    """

    @staticmethod
    def evaluate_and_enforce(
        db: Session,
        dialer_mode: str,  # "PROGRESSIVE" or "PREDICTIVE"
        proposed_calls: int,
        available_agents: int,
        reserved_agents: int,
        active_calls: int,
        calls_ringing: int,
        provider_health: ProviderHealthStatus,
        historical_answer_rate: float = 0.35,
    ) -> Tuple[int, SafetyDecision]:
        """
        Evaluates proposed dials against hard safety boundaries and returns (approved_calls, decision_record).
        """
        net_available_agents = max(0, available_agents - reserved_agents)

        decision_type = SafetyDecisionType.APPROVED
        rule_triggered = "NORMAL_PASS"
        reason = ""
        approved_calls = proposed_calls

        # RULE 1: Provider Outage Hard Stop
        if provider_health == ProviderHealthStatus.OUTAGE:
            approved_calls = 0
            decision_type = SafetyDecisionType.REJECTED
            rule_triggered = "PROVIDER_OUTAGE_SHUTDOWN"
            reason = "Telecom provider reported OUTAGE. All outbound dialing halted immediately for customer safety."

        # RULE 2: Zero Available Agent Capacity
        elif net_available_agents <= 0:
            approved_calls = 0
            decision_type = SafetyDecisionType.REJECTED
            rule_triggered = "ZERO_AGENT_CAPACITY"
            reason = f"No unreserved agents available (Available: {available_agents}, Reserved: {reserved_agents})."

        # RULE 3: Ringing Calls Already Saturate Available Agents
        elif calls_ringing >= net_available_agents:
            approved_calls = 0
            decision_type = SafetyDecisionType.REJECTED
            rule_triggered = "RINGING_PIPELINE_SATURATED"
            reason = (
                f"{calls_ringing} call(s) currently ringing, which already satisfies or exceeds "
                f"the {net_available_agents} idle agent(s). Additional dialing risks abandoned connects."
            )

        # RULE 4: Progressive Mode 1:1 Strict Upper Bound
        elif dialer_mode == "PROGRESSIVE":
            if proposed_calls > net_available_agents:
                approved_calls = net_available_agents
                decision_type = SafetyDecisionType.REDUCED
                rule_triggered = "PROGRESSIVE_AGENT_CAP"
                reason = (
                    f"Progressive dialing strictly capped at 1 call per idle agent. "
                    f"Proposed {proposed_calls} reduced to {net_available_agents}."
                )
            else:
                approved_calls = proposed_calls
                decision_type = SafetyDecisionType.APPROVED
                rule_triggered = "PROGRESSIVE_SAFE"
                reason = f"Approved {approved_calls} progressive call(s) for {net_available_agents} available agent(s)."

        # RULE 5: Predictive Fallback to Progressive under Unsafe Conditions
        elif dialer_mode == "PREDICTIVE":
            # Condition 5a: Small agent pool (< 3 agents) cannot absorb Poisson arrival variance
            if net_available_agents < 3:
                approved_calls = min(proposed_calls, net_available_agents)
                decision_type = SafetyDecisionType.FALLBACK_PROGRESSIVE
                rule_triggered = "SMALL_AGENT_POOL_FALLBACK"
                reason = (
                    f"Predictive dialing is unsafe with fewer than 3 idle agents ({net_available_agents}). "
                    f"Statistical smoothing fails; falling back to 1:1 progressive cap ({approved_calls})."
                )

            # Condition 5b: High answer rate (> 60%) creates high risk of multi-connect collision
            elif historical_answer_rate > 0.60:
                approved_calls = min(proposed_calls, net_available_agents)
                decision_type = SafetyDecisionType.FALLBACK_PROGRESSIVE
                rule_triggered = "HIGH_ANSWER_RATE_VOLATILITY"
                reason = (
                    f"Historical answer rate is high ({historical_answer_rate*100:.1f}% > 60%). "
                    f"Overdialing poses high risk of abandoned borrower calls; fallback to progressive cap ({approved_calls})."
                )

            # Condition 5c: Provider Degraded Health Throttling
            elif provider_health == ProviderHealthStatus.DEGRADED:
                # Clamp to at most idle agents
                max_safe = max(1, net_available_agents // 2)
                approved_calls = min(proposed_calls, max_safe)
                decision_type = SafetyDecisionType.REDUCED
                rule_triggered = "DEGRADED_PROVIDER_THROTTLE"
                reason = (
                    f"Provider health is DEGRADED. Dialing throttled to 50% capacity "
                    f"({approved_calls} approved vs {proposed_calls} proposed)."
                )

            # Condition 5d: Standard predictive check - clamp to max safe overdial limit (max 2x agents)
            else:
                safe_ceiling = net_available_agents * 2
                if proposed_calls > safe_ceiling:
                    approved_calls = safe_ceiling
                    decision_type = SafetyDecisionType.REDUCED
                    rule_triggered = "PREDICTIVE_CEILING_ENFORCED"
                    reason = (
                        f"Proposed {proposed_calls} calls exceeded safety ceiling of {safe_ceiling} "
                        f"(2x idle agents). Clamped to {safe_ceiling}."
                    )
                else:
                    approved_calls = proposed_calls
                    decision_type = SafetyDecisionType.APPROVED
                    rule_triggered = "PREDICTIVE_APPROVED"
                    reason = f"Proposed {proposed_calls} dials approved within safety boundaries."

        # Safety catch-all: Never allow negative approved calls
        approved_calls = max(0, approved_calls)

        # Audit decision to database
        decision_record = SafetyDecision(
            dialer_mode=dialer_mode,
            engine_proposed_calls=proposed_calls,
            approved_calls=approved_calls,
            available_agents=available_agents,
            reserved_agents=reserved_agents,
            active_calls=active_calls,
            calls_ringing=calls_ringing,
            provider_health=provider_health.value,
            decision=decision_type.value,
            rule_triggered=rule_triggered,
            reason=reason,
        )
        db.add(decision_record)
        db.commit()
        db.refresh(decision_record)

        logger.info(
            f"[SafetyController] Mode: {dialer_mode} | Proposed: {proposed_calls} -> Approved: {approved_calls} | "
            f"Verdict: {decision_type.value} | Reason: {reason}"
        )

        return approved_calls, decision_record
