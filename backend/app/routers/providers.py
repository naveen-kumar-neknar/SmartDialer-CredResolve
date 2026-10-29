from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas import (
    ProviderHealthResponse,
    ProviderConfigRequest,
    ProviderEventWebhook,
)
from app.services.telecom_provider import provider_manager, ProviderB
from app.services.event_processor import EventProcessor

router = APIRouter(prefix="/api/providers", tags=["Providers"])


@router.get("/health", response_model=ProviderHealthResponse)
def get_provider_health():
    """Returns real-time health metrics of telecom providers."""
    prov_a = provider_manager.provider_a
    prov_b = provider_manager.provider_b
    active = provider_manager.get_active_provider()

    b_settings = {}
    if isinstance(prov_b, ProviderB):
        b_settings = {
            "simulate_failure": prov_b.simulate_failure,
            "simulate_timeout": prov_b.simulate_timeout,
            "simulate_duplicate": prov_b.simulate_duplicate,
            "simulate_out_of_order": prov_b.simulate_out_of_order,
            "configured_failure_rate": prov_b.failure_rate,
        }

    return ProviderHealthResponse(
        active_provider=provider_manager.active_provider_name,
        provider_a_health=prov_a.get_health(),
        provider_b_health=prov_b.get_health(),
        overall_health=active.get_health(),
        stats={
            "provider_a": {
                "requests": prov_a.total_requests,
                "failures": prov_a.total_failures,
                "force_outage": prov_a.force_outage,
            },
            "provider_b": {
                "requests": prov_b.total_requests,
                "failures": prov_b.total_failures,
                "timeouts": prov_b.total_timeouts,
                "force_outage": prov_b.force_outage,
                "settings": b_settings,
            },
        },
    )


@router.post("/config")
def update_provider_config(config: ProviderConfigRequest):
    """
    Switch active telecom provider and configure failure simulation parameters.
    """
    if config.active_provider:
        if config.active_provider not in {"ProviderA", "ProviderB"}:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Provider must be either ProviderA or ProviderB",
            )
        provider_manager.set_active_provider(config.active_provider)

    prov_b = provider_manager.provider_b
    if isinstance(prov_b, ProviderB):
        if config.simulate_failure is not None:
            prov_b.simulate_failure = config.simulate_failure
        if config.simulate_timeout is not None:
            prov_b.simulate_timeout = config.simulate_timeout
        if config.simulate_duplicate is not None:
            prov_b.simulate_duplicate = config.simulate_duplicate
        if config.simulate_out_of_order is not None:
            prov_b.simulate_out_of_order = config.simulate_out_of_order
        if config.failure_rate is not None:
            prov_b.failure_rate = config.failure_rate

    return {
        "status": "UPDATED",
        "active_provider": provider_manager.active_provider_name,
        "message": f"Switched to {provider_manager.active_provider_name} with updated simulation parameters.",
    }


@router.post("/outage")
def toggle_outage(provider_name: str, enable_outage: bool):
    """Toggle simulated provider total outage for testing."""
    provider = provider_manager.get_provider_by_name(provider_name)
    provider.force_outage = enable_outage
    return {
        "provider": provider.name,
        "force_outage": provider.force_outage,
        "health": provider.get_health(),
    }


@router.post("/events/webhook")
def receive_provider_event(
    event: ProviderEventWebhook,
    db: Session = Depends(get_db),
):
    """
    Telecom provider webhook endpoint with idempotent processing,
    duplicate rejection, and sequence validation.
    """
    result = EventProcessor.process_event(
        db=db,
        event_id=event.event_id,
        call_id=event.call_id,
        provider=event.provider,
        event_type=event.event_type,
        sequence_number=event.sequence_number,
        payload=event.payload,
    )
    return result
