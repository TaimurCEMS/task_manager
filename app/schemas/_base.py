# File: /app/schemas/_base.py | Version: 1.1 | Title: Pydantic Base Schema (V2-ready)
from pydantic import BaseModel, ConfigDict


class BaseSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)
