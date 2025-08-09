# File: /app/core/permissions.py | Version: 1.1
from __future__ import annotations

from enum import Enum
from typing import Optional, Callable, Any

from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.security import get_current_user
from app.models.core_entities import WorkspaceMember, User  # type: ignore


class Role(str, Enum):
    OWNER = "Owner"
    ADMIN = "Admin"
    MEMBER = "Member"
    GUEST = "Guest"


# Lowest → Highest
ROLE_ORDER = [Role.GUEST, Role.MEMBER, Role.ADMIN, Role.OWNER]
ROLE_RANK = {r: i for i, r in enumerate(ROLE_ORDER)}


def _normalize_role(value: str | Role | None) -> Optional[Role]:
    if value is None:
        return None
    if isinstance(value, Role):
        return value
    try:
        normalized = value.strip().lower()
    except AttributeError:
        return None
    for r in Role:
        if r.value.lower() == normalized:
            return r
    return None


def get_workspace_role(
    db: Session, *, user_id: Any, workspace_id: Any
) -> Optional[Role]:
    """
    Return the user's Role in a workspace, or None if not a member.
    """
    wm = (
        db.query(WorkspaceMember)
        .filter(
            WorkspaceMember.user_id == user_id,
            WorkspaceMember.workspace_id == workspace_id,
        )
        .first()
    )
    return _normalize_role(getattr(wm, "role", None))


def has_min_role(
    db: Session,
    *,
    user_id: Any,
    workspace_id: Any,
    minimum: Role,
) -> bool:
    """
    True iff the user has membership in the workspace AND their role rank >= minimum.
    """
    current = get_workspace_role(db, user_id=user_id, workspace_id=workspace_id)
    if current is None:
        return False
    return ROLE_RANK[current] >= ROLE_RANK[minimum]


def require_role(
    db: Session,
    *,
    user_id: Any,
    workspace_id: Any,
    minimum: Role,
    message: Optional[str] = None,
) -> Role:
    """
    Enforce that the user has at least `minimum` role. Raises 403 if not.
    Returns the resolved Role on success.
    """
    resolved = get_workspace_role(db, user_id=user_id, workspace_id=workspace_id)
    if resolved is None or ROLE_RANK[resolved] < ROLE_RANK[minimum]:
        detail = message or (
            f"Requires role '{minimum.value}' or higher in workspace {workspace_id}."
        )
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=detail)
    return resolved


# ----- Convenience checks aligned with the role matrix -----

def can_manage_workspace(db: Session, *, user_id: Any, workspace_id: Any) -> bool:
    # Admin+ can manage workspace-level settings and members
    return has_min_role(db, user_id=user_id, workspace_id=workspace_id, minimum=Role.ADMIN)


def can_edit_content(db: Session, *, user_id: Any, workspace_id: Any) -> bool:
    # Member+ can create/edit content within accessible spaces/lists
    return has_min_role(db, user_id=user_id, workspace_id=workspace_id, minimum=Role.MEMBER)


def can_view_workspace(db: Session, *, user_id: Any, workspace_id: Any) -> bool:
    # Any membership grants view; guests via explicit shares (handled elsewhere)
    role = get_workspace_role(db, user_id=user_id, workspace_id=workspace_id)
    return role is not None


# ----- FastAPI dependency factory -----
def require_workspace_role_dependency(minimum: Role) -> Callable:
    """
    Example:
      @router.post("/workspaces/{workspace_id}/spaces",
                   dependencies=[Depends(require_workspace_role_dependency(Role.MEMBER))])
    """
    def _dep(
        workspace_id: int,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user),
    ) -> None:
        require_role(
            db,
            user_id=current_user.id,
            workspace_id=workspace_id,
            minimum=minimum,
        )

    return _dep


# ===== Back-compat shims (used by existing routers) =====
# These keep older imports working while we migrate.
# Prefer the newer helpers above in new code.

def get_user_role_for_workspace(db: Session, user_id: Any, workspace_id: Any) -> Optional[str]:
    """
    OLD NAME — use get_workspace_role() instead.
    Returns the role as a string (e.g., 'Owner') or None if not a member.
    """
    r = get_workspace_role(db, user_id=user_id, workspace_id=workspace_id)
    return r.value if r else None


def check_permission(
    db: Session,
    *,
    user_id: Any,
    workspace_id: Any,
    action: str,
) -> bool:
    """
    OLD API — returns bool. Newer code should use require_role()/dependency.
    Supported actions (case-insensitive):
      - 'manage_workspace', 'manage_members', 'workspace_settings' -> Admin+
      - 'edit', 'create', 'update', 'delete', 'edit_content', 'write' -> Member+
      - 'view', 'read', 'view_workspace' -> any member
    Unknown actions -> False (conservative).
    """
    a = (action or "").strip().lower()
    if a in {"manage_workspace", "manage_members", "workspace_settings"}:
        return can_manage_workspace(db, user_id=user_id, workspace_id=workspace_id)
    if a in {"edit", "create", "update", "delete", "edit_content", "write"}:
        return can_edit_content(db, user_id=user_id, workspace_id=workspace_id)
    if a in {"view", "read", "view_workspace"}:
        return can_view_workspace(db, user_id=user_id, workspace_id=workspace_id)
    return False
