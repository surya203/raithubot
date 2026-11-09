from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, computed_field

from app.utils.time import to_ist_iso


class Timestamped(BaseModel):
    created_at: datetime

    @computed_field
    @property
    def created_at_ist(self) -> str | None:
        return to_ist_iso(self.created_at)


class Message(BaseModel):
    detail: str


class IdPath(BaseModel):
    id: UUID
