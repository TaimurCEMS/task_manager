# File: app/routers/auth_dependencies.py | Version: 1.0 | Path: /app/routers/auth_dependencies.py
from fastapi import Depends

# We assume you already have a dependency that reads the JWT and returns the current user.
# If it's elsewhere, update the import below to match your project.
from app.security import get_current_user


def get_me(current_user=Depends(get_current_user)):
    """
    Wrapper dependency so other routers can just Depends(get_me)
    to fetch the authenticated user object (whatever your get_current_user returns).
    """
    return current_user
