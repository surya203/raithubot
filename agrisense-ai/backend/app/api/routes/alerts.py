from uuid import UUID

from fastapi import APIRouter, Depends, Query

from app.dependencies import get_alert_service
from app.schemas.alerts import AlertEvaluateRequest, AlertRead
from app.services.alert_service import AlertService

router = APIRouter(prefix="/alerts", tags=["alerts"])


@router.get("", response_model=list[AlertRead])
def list_alerts(
    crop_id: UUID | None = None,
    location_id: UUID | None = None,
    unread_only: bool = False,
    limit: int = Query(default=50, ge=1, le=200),
    service: AlertService = Depends(get_alert_service),
) -> list[AlertRead]:
    return service.list(crop_id, location_id, unread_only, limit)


@router.post("/evaluate", response_model=list[AlertRead])
def evaluate_alerts(
    payload: AlertEvaluateRequest,
    service: AlertService = Depends(get_alert_service),
) -> list[AlertRead]:
    return service.evaluate(payload)


@router.patch("/{alert_id}/read", response_model=AlertRead)
def mark_alert_read(
    alert_id: UUID,
    service: AlertService = Depends(get_alert_service),
) -> AlertRead:
    return service.mark_read(alert_id)
