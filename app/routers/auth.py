# File: /app/routers/auth.py | Version: 2.8 | Title: Auth Router (JSON+form tolerant) + Default Workspace (owner_id set) + Access & Refresh Tokens
from __future__ import annotations

from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, Form, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.core_entities import User, Workspace
from app.security import (
    create_access_token,
    create_refresh_token,
    get_current_user,
    get_password_hash,
    verify_password,
)

# Membership model used to list workspaces for a user in tests
try:
    from app.models.core_entities import WorkspaceMember
except Exception:  # pragma: no cover
    WorkspaceMember = None  # type: ignore

router = APIRouter(prefix="/auth", tags=["Auth"])


# ---------------------------
# Utilities
# ---------------------------


async def _read_json_or_form(request: Request) -> Dict[str, Any]:
    """Accept JSON or form-encoded bodies and normalize keys."""
    ctype = (request.headers.get("content-type") or "").lower()
    data: Dict[str, Any] = {}
    if "application/json" in ctype:
        try:
            body = await request.json()
            if isinstance(body, dict):
                data = body
        except Exception:
            data = {}
    else:
        form = await request.form()
        data = dict(form)

    # alias: username -> email (OAuth-style)
    if "username" in data and "email" not in data:
        data["email"] = data["username"]
    return data


def _ensure_default_workspace(db: Session, user: User) -> None:
    """
    Ensure the user has at least one workspace and a membership row.
    Tests assume registration yields a first workspace immediately.
    """
    if WorkspaceMember is None:
        # If membership model import fails, still create a workspace so owner_id constraint is satisfied.
        pass
    else:
        existing = (
            db.query(Workspace)
            .join(WorkspaceMember, WorkspaceMember.workspace_id == Workspace.id)
            .filter(WorkspaceMember.user_id == str(user.id))
            .first()
        )
        if existing:
            return

    # Create workspace with REQUIRED owner_id set (fixes NOT NULL constraint)
    name = f"{(user.email or 'user').split('@', 1)[0]}'s Workspace"
    ws = Workspace(name=name, owner_id=str(user.id))
    db.add(ws)
    db.flush()  # ws.id available

    # Create membership so GET /workspaces/ includes it for the user
    if WorkspaceMember is not None:
        membership = WorkspaceMember(
            workspace_id=str(ws.id), user_id=str(user.id), role="Owner"
        )
        db.add(membership)

    db.commit()


def _issue_tokens_for_user(user: User) -> Dict[str, str]:
    sub = {"sub": str(user.id)}
    return {
        "access_token": create_access_token(sub),
        "refresh_token": create_refresh_token(sub),
        "token_type": "bearer",
    }


# ---------------------------
# Endpoints
# ---------------------------


@router.post("/register")
async def register(request: Request, db: Session = Depends(get_db)):
    """
    Register a user. Idempotent:
      - If new: create user, bootstrap default workspace + Owner membership.
      - If exists: ensure workspace exists and return 200.
    Accepts JSON or form {email, password, [full_name]}.
    Returns minimal user info; clients/tests then call /auth/login.
    """
    payload = await _read_json_or_form(request)
    email = (payload.get("email") or "").strip().lower()
    password = payload.get("password")
    full_name: Optional[str] = payload.get("full_name")

    if not email or not password:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Email and password required",
        )

    user = db.query(User).filter(User.email == email).first()
    if not user:
        user = User(
            email=email,
            full_name=full_name,
            hashed_password=get_password_hash(password),
            is_active=True,
        )
        db.add(user)
        db.commit()
        db.refresh(user)

    _ensure_default_workspace(db, user)
    return {"id": str(user.id), "email": user.email}


@router.post("/login")
async def login(request: Request, db: Session = Depends(get_db)):
    """
    Login with JSON or form {email/username, password}.
    Returns both access and refresh tokens for later /auth/refresh use.
    """
    payload = await _read_json_or_form(request)
    email = (payload.get("email") or "").strip().lower()
    password = payload.get("password")

    if not email or not password:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Email and password required",
        )

    user = db.query(User).filter(User.email == email).first()
    if not user or not verify_password(password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
        )

    return _issue_tokens_for_user(user)


@router.post("/token")
def login_oauth_form(
    db: Session = Depends(get_db),
    username: str = Form(...),
    password: str = Form(...),
):
    """
    OAuth2 form variant (used by some tests/tools). Returns access + refresh tokens.
    """
    email = (username or "").strip().lower()
    user = db.query(User).filter(User.email == email).first()
    if not user or not verify_password(password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
        )

    return _issue_tokens_for_user(user)


@router.get("/protected")
def protected(current_user: User = Depends(get_current_user)):
    return {"ok": True, "user_id": str(current_user.id)}
