from datetime import datetime
from typing import Literal
from pydantic import BaseModel

class HealthResponse(BaseModel):
    status: Literal["ok"]
    service: str
    version: str
    timestamp_utc: datetime
    uptime_seconds: float