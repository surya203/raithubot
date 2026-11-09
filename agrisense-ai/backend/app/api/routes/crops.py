from uuid import UUID

from fastapi import APIRouter, Depends, Response

from app.dependencies import get_crop_service, get_location_service
from app.schemas.crops import CropCreate, CropRead, LocationCreate, LocationRead
from app.services.catalog_service import CropService, LocationService

router = APIRouter(tags=["crops"])


@router.post("/locations", response_model=LocationRead, status_code=201)
def create_location(
    payload: LocationCreate,
    service: LocationService = Depends(get_location_service),
) -> LocationRead:
    return service.create(payload)


@router.get("/locations", response_model=list[LocationRead])
def list_locations(service: LocationService = Depends(get_location_service)) -> list[LocationRead]:
    return service.list()


@router.get("/locations/{location_id}", response_model=LocationRead)
def get_location(
    location_id: UUID,
    service: LocationService = Depends(get_location_service),
) -> LocationRead:
    return service.get(location_id)


@router.post("/crops", response_model=CropRead, status_code=201)
def create_crop(
    payload: CropCreate,
    service: CropService = Depends(get_crop_service),
) -> CropRead:
    return service.create(payload)


@router.get("/crops", response_model=list[CropRead])
def list_crops(
    location_id: UUID | None = None,
    service: CropService = Depends(get_crop_service),
) -> list[CropRead]:
    return service.list(location_id)


@router.get("/crops/{crop_id}", response_model=CropRead)
def get_crop(crop_id: UUID, service: CropService = Depends(get_crop_service)) -> CropRead:
    return service.get(crop_id)


@router.put("/crops/{crop_id}", response_model=CropRead)
def update_crop(
    crop_id: UUID,
    payload: CropCreate,
    service: CropService = Depends(get_crop_service),
) -> CropRead:
    return service.update(crop_id, payload)


@router.delete("/crops/{crop_id}", status_code=204)
def delete_crop(crop_id: UUID, service: CropService = Depends(get_crop_service)) -> Response:
    service.delete(crop_id)
    return Response(status_code=204)
