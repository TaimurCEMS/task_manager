# File: tests/test_permissions_unit.py | Version: 1.0 | Path: /tests/test_permissions_unit.py
import pytest
from fastapi import HTTPException

# Import the permission helpers we just added
from app.core.permissions import (
    Role,
    has_min_role,
    require_role,
)

# We will monkeypatch app.core.permissions.get_workspace_role
# so these tests don't depend on DB models or fixtures.


def test_has_min_role_true_when_admin_meets_member(monkeypatch):
    # Arrange: pretend the user is ADMIN in this workspace
    def fake_get_workspace_role(db, *, user_id, workspace_id):
        return Role.ADMIN

    import app.core.permissions as perms
    monkeypatch.setattr(perms, "get_workspace_role", fake_get_workspace_role)

    # Act + Assert
    assert has_min_role(db=None, user_id="U1", workspace_id="W1", minimum=Role.MEMBER) is True


def test_has_min_role_false_when_guest_does_not_meet_member(monkeypatch):
    def fake_get_workspace_role(db, *, user_id, workspace_id):
        return Role.GUEST

    import app.core.permissions as perms
    monkeypatch.setattr(perms, "get_workspace_role", fake_get_workspace_role)

    assert has_min_role(db=None, user_id="U1", workspace_id="W1", minimum=Role.MEMBER) is False


def test_require_role_allows_owner_when_min_admin(monkeypatch):
    def fake_get_workspace_role(db, *, user_id, workspace_id):
        return Role.OWNER

    import app.core.permissions as perms
    monkeypatch.setattr(perms, "get_workspace_role", fake_get_workspace_role)

    resolved = require_role(db=None, user_id="U1", workspace_id="W1", minimum=Role.ADMIN)
    assert resolved is Role.OWNER


def test_require_role_denies_non_member(monkeypatch):
    # User has no membership in the workspace
    def fake_get_workspace_role(db, *, user_id, workspace_id):
        return None

    import app.core.permissions as perms
    monkeypatch.setattr(perms, "get_workspace_role", fake_get_workspace_role)

    with pytest.raises(HTTPException) as excinfo:
        require_role(db=None, user_id="U1", workspace_id="W1", minimum=Role.GUEST)

    err = excinfo.value
    assert err.status_code == 403
    assert "Requires role" in str(err.detail)


def test_require_role_denies_member_when_min_admin(monkeypatch):
    # Member tries an Admin+ action
    def fake_get_workspace_role(db, *, user_id, workspace_id):
        return Role.MEMBER

    import app.core.permissions as perms
    monkeypatch.setattr(perms, "get_workspace_role", fake_get_workspace_role)

    with pytest.raises(HTTPException) as excinfo:
        require_role(db=None, user_id="U1", workspace_id="W1", minimum=Role.ADMIN)

    assert excinfo.value.status_code == 403
