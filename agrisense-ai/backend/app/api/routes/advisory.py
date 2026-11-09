from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, Query

from app.dependencies import get_advisory_service
from app.schemas.advisory import (
    AdvisoryRead,
    AdvisoryType,
    CropAdvisoryRequest,
    DiseaseAdvisoryRequest,
)
from app.services.advisory_service import AdvisoryService

router = APIRouter(prefix="/advisory", tags=["advisory"])


@router.post("/crop", response_model=AdvisoryRead, status_code=201)
def crop_advisory(
    payload: CropAdvisoryRequest,
    service: AdvisoryService = Depends(get_advisory_service),
) -> AdvisoryRead:
    return service.crop_advisory(payload.crop_id)


@router.post("/disease", response_model=AdvisoryRead, status_code=201)
def disease_advisory(
    payload: DiseaseAdvisoryRequest,
    service: AdvisoryService = Depends(get_advisory_service),
) -> AdvisoryRead:
    return service.disease_advisory(payload.crop_id, payload.symptoms)


@router.get("/history", response_model=list[AdvisoryRead])
def advisory_history(
    crop_id: UUID | None = None,
    advisory_type: AdvisoryType | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    limit: int = Query(default=50, ge=1, le=200),
    service: AdvisoryService = Depends(get_advisory_service),
) -> list[AdvisoryRead]:
    return service.history(crop_id, advisory_type, date_from, date_to, limit)


@router.get("/{advisory_id}", response_model=AdvisoryRead)
def get_advisory(
    advisory_id: UUID,
    service: AdvisoryService = Depends(get_advisory_service),
) -> AdvisoryRead:
    return service.get(advisory_id)
