from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.enums import IncidentStatus


class StatusHistoryRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    incident_id: int
    from_status: IncidentStatus | None
    to_status: IncidentStatus
    changed_by: str | None
    comment: str | None
    changed_at: datetime
