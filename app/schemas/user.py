# File: app/schemas/user.py | Version: 1.0 | Path: /app/schemas/user.py

from pydantic import BaseModel, EmailStr

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

    class Config:
        orm_mode = True
