# File: app/routers/auth.py | Version: 1.2 | Path: /app/routers/auth.py
from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models import User, Workspace, WorkspaceMember
from app.schemas.auth import TokenResponse  # response model only
from app.security import (
    create_access_token,
    get_current_user,
    get_password_hash,
    verify_password,
)

router = APIRouter(prefix="/auth", tags=["auth"])


async def _read_payload(req: Request) -> dict:
    """
    Accepts JSON or form (x-www-form-urlencoded / multipart) and returns a dict.
    Also tolerates clients that send 'username' instead of 'email'.
    """
    ct = req.headers.get("content-type", "")
    data: dict
    try:
        if "application/json" in ct:
            data = await req.json()
        elif "application/x-www-form-urlencoded" in ct or "multipart/form-data" in ct:
            form = await req.form()
            data = dict(form)
        else:
            # Try JSON first, fall back to form
            try:
                data = await req.json()
            except Exception:
                form = await req.form()
                data = dict(form)
    except Exception:
        data = {}

    # Normalize common auth field names
    if "email" not in data and "username" in data:
        data["email"] = data.get("username")
    return data


@router.post("/register", response_model=TokenResponse)
async def register(req: Request, db: Session = Depends(get_db)):
    payload = await _read_payload(req)
    email = (payload.get("email") or "").strip().lower()
    password = payload.get("password")
    full_name = payload.get("full_name")

    if not email or not password:
        raise HTTPException(status_code=422, detail="email and password are required")

    existing = db.query(User).filter(User.email == email).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")

    user = User(
        email=email,
        hashed_password=get_password_hash(password),
        full_name=full_name,
        is_active=True,
    )
    db.add(user)
    db.flush()  # get user.id

    ws_name = f"{email.split('@')[0]}'s workspace" if "@" in email else f"{email}'s workspace"
    workspace = Workspace(name=ws_name, owner_id=user.id)
    db.add(workspace)
    db.flush()

    membership = WorkspaceMember(
        workspace_id=workspace.id, user_id=user.id, role="owner", is_active=True
    )
    db.add(membership)
    db.commit()

    token = create_access_token({"sub": user.id}, expires_delta=timedelta(minutes=60))
    return TokenResponse(access_token=token, token_type="bearer")


@router.post("/login", response_model=TokenResponse)
async def login(req: Request, db: Session = Depends(get_db)):
    payload = await _read_payload(req)
    email = (payload.get("email") or "").strip().lower()
    password = payload.get("password")

    if not email or not password:
        raise HTTPException(status_code=422, detail="email/username and password are required")

    user = db.query(User).filter(User.email == email).first()
    if not user or not verify_password(password, user.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    token = create_access_token({"sub": user.id}, expires_delta=timedelta(minutes=60))
    return TokenResponse(access_token=token, token_type="bearer")


@router.post("/token", response_model=TokenResponse)
def token(form: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    # OAuth2 form uses "username" as the identifier; here we treat it as email
    email = form.username.strip().lower()
    user = db.query(User).filter(User.email == email).first()
    if not user or not verify_password(form.password, user.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    token = create_access_token({"sub": user.id}, expires_delta=timedelta(minutes=60))
    return TokenResponse(access_token=token, token_type="bearer")


@router.get("/protected")
def protected(current_user: User = Depends(get_current_user)):
    return {"ok": True, "user": {"id": current_user.id, "email": current_user.email}}
