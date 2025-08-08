# File: app/core/permissions.py | Version: 1.0 | Path: /app/core/permissions.py
from fastapi import HTTPException, status

# This is temporary; in Phase 4 we’ll extract real role from JWT
def get_user_role_for_workspace(user_id: str, workspace_id: str):
    # Mock logic for now (just return role based on user ID)
    if user_id == "user-123":
        return "Owner"
    elif user_id == "admin-001":
        return "Admin"
    elif user_id == "guest-001":
        return "Guest"
    else:
        return "Member"

def check_permission(user_role: str, required_roles: list[str]):
    if user_role not in required_roles:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Access denied: requires one of {required_roles}, but user has role '{user_role}'"
        )
