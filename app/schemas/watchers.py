from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict


class WatcherOut(BaseModel):
    id: str
    task_id: str
    user_id: str
    created_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)
