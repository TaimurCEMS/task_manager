# File: /app/routers/auth_extras.py | Version: 1.0 | Title: Auth Extras (/auth/me, /auth/refresh)
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.models.core_entities import User
from app.security import create_access_token, decode_refresh_token, get_current_user

router = APIRouter(prefix="/auth", tags=["Auth"])


class RefreshIn(BaseModel):
    refresh_token: str


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"


@router.get("/me", response_model=dict)
def me(current_user: User = Depends(get_current_user)):
    return {
        "id": str(current_user.id),
        "email": current_user.email,
        "full_name": getattr(current_user, "full_name", None),
        "is_active": getattr(current_user, "is_active", True),
    }


@router.post("/refresh", response_model=TokenOut)
def refresh(body: RefreshIn):
    payload = decode_refresh_token(body.refresh_token)
    sub = payload.get("sub")
    if not sub:
        raise HTTPException(status_code=401, detail="Invalid refresh token")
    token = create_access_token({"sub": sub})
    return TokenOut(access_token=token)
