# File: /app/schemas/user.py | Version: 2.0 | Path: /app/schemas/user.py
from __future__ import annotations

from pydantic import BaseModel, EmailStr
from pydantic import ConfigDict


class UserCreate(BaseModel):
    email: EmailStr
    full_name: str | None = None
    password: str


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserResponse(BaseModel):
    id: str
    email: EmailStr
    full_name: str | None = None

    # Pydantic v2 style
    model_config = ConfigDict(from_attributes=True)
