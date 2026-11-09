from uuid import UUID

from fastapi import APIRouter, Depends, Query

from app.dependencies import get_environment_service
from app.schemas.environment import EnvironmentCreate, EnvironmentRead
from app.services.catalog_service import EnvironmentService

router = APIRouter(prefix="/environment", tags=["environment"])


@router.post("", response_model=EnvironmentRead, status_code=201)
def create_environment(
    payload: EnvironmentCreate,
    service: EnvironmentService = Depends(get_environment_service),
) -> EnvironmentRead:
    return service.create(payload)


@router.get("", response_model=list[EnvironmentRead])
def list_environment(
    location_id: UUID | None = None,
    crop_id: UUID | None = None,
    limit: int = Query(default=50, ge=1, le=200),
    service: EnvironmentService = Depends(get_environment_service),
) -> list[EnvironmentRead]:
    return service.list(location_id, crop_id, limit)
